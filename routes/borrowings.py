from datetime import datetime, timezone, date
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required

borrowings_bp = Blueprint('borrowings', __name__, url_prefix='/borrowings')

@borrowings_bp.route('', methods=['GET'])
@borrowings_bp.route('/my', methods=['GET'])
@login_required
def my_borrowings():
    """
    Displays the logged-in user's active borrowings and completed transaction history.
    Detects and flags overdue physical items dynamically.
    """
    db = get_db()
    user_id = session.get('user_id')
    today_str = date.today().isoformat()

    borrowings_list = list(db['borrowings'].find({"user_id": user_id}).sort("request_date", -1))

    # Evaluate dynamic overdue status without mutating historical records
    active_count = 0
    overdue_count = 0
    for b in borrowings_list:
        if b.get('status') in ['approved', 'borrowed']:
            active_count += 1
            if b.get('expected_return_date') and b.get('expected_return_date') < today_str:
                b['is_overdue'] = True
                overdue_count += 1
            else:
                b['is_overdue'] = False
        else:
            b['is_overdue'] = False

    return render_template(
        'borrowings/my_borrowings.html',
        active_page='borrowings',
        borrowings=borrowings_list,
        stats={
            'total': len(borrowings_list),
            'active': active_count,
            'overdue': overdue_count
        }
    )

@borrowings_bp.route('/manage', methods=['GET'])
@login_required
def manage_borrowings():
    """
    Hardware owner and Admin control panel for approving requests,
    confirming equipment handovers, and logging physical item returns.
    """
    db = get_db()
    user_id = session.get('user_id')
    role = session.get('role')

    # Admin oversees all; faculty/students manage hardware they own
    if role == 'admin':
        borrowings_list = list(db['borrowings'].find({}).sort("request_date", -1))
    else:
        borrowings_list = list(db['borrowings'].find({"owner_id": user_id}).sort("request_date", -1))

    today_str = date.today().isoformat()
    for b in borrowings_list:
        if b.get('status') in ['approved', 'borrowed'] and b.get('expected_return_date') and b.get('expected_return_date') < today_str:
            b['is_overdue'] = True
        else:
            b['is_overdue'] = False

    return render_template(
        'borrowings/manage.html',
        active_page='borrowings',
        borrowings=borrowings_list,
        is_admin=(role == 'admin')
    )

@borrowings_bp.route('/request/<resource_id>', methods=['GET', 'POST'])
@login_required
def request_borrow(resource_id):
    """
    Initiates a physical equipment borrow request (e.g. Arduino kits, sensors, tools).
    """
    db = get_db()
    try:
        obj_id = ObjectId(resource_id)
    except Exception:
        flash("Invalid resource identifier.", "danger")
        return redirect(url_for('resources.list_resources'))

    resource = db['resources'].find_one({"_id": obj_id})
    if not resource:
        flash("Resource not found.", "danger")
        return redirect(url_for('resources.list_resources'))

    if resource.get('resource_type') != 'physical':
        flash("Only physical hardware and lab equipment can be borrowed.", "warning")
        return redirect(url_for('resources.view_resource', resource_id=resource_id))

    if request.method == 'POST':
        expected_return_date = request.form.get('expected_return_date', '').strip()
        purpose = request.form.get('purpose', '').strip()

        if not expected_return_date:
            flash("Please specify an expected return date.", "danger")
            return render_template('borrowings/request.html', resource=resource)

        # Check if already currently checked out
        if resource.get('availability') == 'borrowed':
            flash("This hardware kit is currently checked out by another student.", "warning")
            return redirect(url_for('resources.view_resource', resource_id=resource_id))

        new_borrowing = {
            "resource_id": str(resource['_id']),
            "resource_title": resource.get('title'),
            "resource_category": resource.get('category'),
            "owner_id": resource.get('owner_id'),
            "owner_name": resource.get('owner_name'),
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "user_name": session.get('full_name') or session.get('username'),
            "request_date": datetime.now(timezone.utc),
            "expected_return_date": expected_return_date,
            "actual_return_date": None,
            "purpose": purpose,
            "status": "requested",  # requested -> approved -> borrowed -> returned (or rejected)
            "created_at": datetime.now(timezone.utc)
        }

        db['borrowings'].insert_one(new_borrowing)

        # Notify Owner or Admin
        if resource.get('owner_id'):
            db['notifications'].insert_one({
                "user_id": resource.get('owner_id'),
                "title": "Hardware Borrow Request",
                "message": f"{session.get('full_name')} requested to borrow '{resource.get('title')}' until {expected_return_date}.",
                "is_read": False,
                "created_at": datetime.now(timezone.utc)
            })

        # Log Activity
        db['activities'].insert_one({
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "action": "BORROW_REQUEST",
            "description": f"Requested to borrow '{resource.get('title')}'",
            "created_at": datetime.now(timezone.utc)
        })

        flash(f"Borrow request submitted for '{resource.get('title')}'. Awaiting owner/admin approval.", "success")
        return redirect(url_for('borrowings.my_borrowings'))

    return render_template('borrowings/request.html', resource=resource)

@borrowings_bp.route('/action/<borrowing_id>', methods=['POST'])
@login_required
def update_borrowing_status(borrowing_id):
    """
    Executes physical equipment lifecycle transitions:
    approve -> handover (borrowed) -> return -> reject
    """
    db = get_db()
    try:
        obj_id = ObjectId(borrowing_id)
    except Exception:
        flash("Invalid transaction ID.", "danger")
        return redirect(url_for('borrowings.my_borrowings'))

    borrowing = db['borrowings'].find_one({"_id": obj_id})
    if not borrowing:
        flash("Transaction record not found.", "warning")
        return redirect(url_for('borrowings.my_borrowings'))

    action = request.form.get('action', '').strip().lower()
    user_id = session.get('user_id')
    role = session.get('role')

    # Security: Only owner or admin can approve, handover, or close transactions
    if borrowing.get('owner_id') != user_id and role != 'admin':
        flash("Unauthorized: Only the hardware owner or administrator can approve or close borrowings.", "danger")
        return redirect(url_for('borrowings.my_borrowings'))

    res_obj_id = ObjectId(borrowing.get('resource_id'))

    if action == 'approve':
        db['borrowings'].update_one({"_id": obj_id}, {"$set": {"status": "approved"}})
        msg = f"Borrow request approved for '{borrowing.get('resource_title')}'. Ready for lab handover."
        flash(msg, "success")
        notif_msg = f"Your borrow request for '{borrowing.get('resource_title')}' was approved. Please collect the kit from the lab."

    elif action == 'handover':
        db['borrowings'].update_one({"_id": obj_id}, {"$set": {"status": "borrowed"}})
        db['resources'].update_one({"_id": res_obj_id}, {"$set": {"availability": "borrowed"}})
        msg = f"Hardware marked as borrowed by {borrowing.get('user_name')}."
        flash(msg, "success")
        notif_msg = f"Hardware '{borrowing.get('resource_title')}' handed over. Due date: {borrowing.get('expected_return_date')}."

    elif action == 'return':
        today_str = date.today().isoformat()
        db['borrowings'].update_one({"_id": obj_id}, {"$set": {
            "status": "returned",
            "actual_return_date": today_str
        }})
        db['resources'].update_one({"_id": res_obj_id}, {"$set": {"availability": "available"}})
        msg = f"Hardware returned and logged successfully. Item is marked available."
        flash(msg, "success")
        notif_msg = f"Thank you! Return of '{borrowing.get('resource_title')}' confirmed on {today_str}."

    elif action == 'reject':
        db['borrowings'].update_one({"_id": obj_id}, {"$set": {"status": "rejected"}})
        db['resources'].update_one({"_id": res_obj_id}, {"$set": {"availability": "available"}})
        msg = f"Borrow request rejected."
        flash(msg, "warning")
        notif_msg = f"Your borrow request for '{borrowing.get('resource_title')}' was declined."

    else:
        flash("Unknown transaction action.", "danger")
        return redirect(url_for('borrowings.manage_borrowings'))

    # Dispatch notification to borrower
    db['notifications'].insert_one({
        "user_id": borrowing.get('user_id'),
        "title": f"Borrowing Status: {action.capitalize()}",
        "message": notif_msg,
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    })

    return redirect(url_for('borrowings.manage_borrowings'))
