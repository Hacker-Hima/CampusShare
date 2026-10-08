from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required
from utils.trust import calculate_trust_score, find_smart_matches, award_user_points

requests_bp = Blueprint('requests', __name__, url_prefix='/requests')

@requests_bp.route('', methods=['GET'])
@requests_bp.route('/', methods=['GET'])
def list_requests():
    """
    Campus Wanted Board & Community Requests:
    Students post materials, kits, notes, or equipment they need.
    Statuses: OPEN, MATCHED, FULFILLED, CANCELLED.
    """
    db = get_db()
    filter_type = request.args.get('filter', 'all').strip().lower()
    user_id = session.get('user_id')

    query = {}
    if filter_type in ['open', 'pending']:
        query["status"] = {"$in": ["open", "pending", "matched"]}
    elif filter_type == 'fulfilled':
        query["status"] = "fulfilled"
    elif filter_type == 'my' and user_id:
        query["user_id"] = user_id

    requests_list = list(db['resource_requests'].find(query).sort("created_at", -1))
    categories = list(db['categories'].find({}))

    # Decorate with requester trust score
    for req_item in requests_list:
        req_uid = req_item.get('user_id')
        req_item['trust_score'] = calculate_trust_score(req_uid, db) if req_uid else 70

    # Count statistics for header pills
    total_requests = db['resource_requests'].count_documents({})
    open_count = db['resource_requests'].count_documents({"status": {"$in": ["open", "pending", "matched"]}})
    fulfilled_count = db['resource_requests'].count_documents({"status": "fulfilled"})
    my_count = db['resource_requests'].count_documents({"user_id": user_id}) if user_id else 0

    return render_template(
        'requests/list.html',
        active_page='requests',
        requests=requests_list,
        categories=categories,
        filter_type=filter_type,
        stats={
            'total': total_requests,
            'open': open_count,
            'pending': open_count,
            'fulfilled': fulfilled_count,
            'my': my_count
        }
    )


@requests_bp.route('/view/<request_id>')
def view_request(request_id):
    """
    Detailed Wanted Board post view with Smart Resource Matching:
    Searches available items across Campus Marketplace and Academic Library
    matching the requested item keywords and category.
    """
    db = get_db()
    try:
        obj_id = ObjectId(request_id)
    except Exception:
        flash("Invalid request ID.", "danger")
        return redirect(url_for('requests.list_requests'))

    req_doc = db['resource_requests'].find_one({"_id": obj_id})
    if not req_doc:
        flash("Wanted post not found.", "warning")
        return redirect(url_for('requests.list_requests'))

    requester_id = req_doc.get('user_id')
    requester = None
    requester_trust = 75
    if requester_id:
        try:
            requester = db['users'].find_one({"_id": ObjectId(requester_id)})
            requester_trust = calculate_trust_score(requester_id, db)
        except Exception:
            pass

    # Execute Smart Resource Matching
    smart_matches = find_smart_matches(
        query_text=req_doc.get('resource_name'),
        category=req_doc.get('category'),
        department=req_doc.get('department'),
        db=db
    )

    # If matches exist and status was open, update status to 'matched'
    if (smart_matches['marketplace'] or smart_matches['academic']) and req_doc.get('status') in ['open', 'pending']:
        db['resource_requests'].update_one({"_id": obj_id}, {"$set": {"status": "matched"}})
        req_doc['status'] = "matched"

    return render_template(
        'requests/view.html',
        active_page='requests',
        request_item=req_doc,
        requester=requester,
        requester_trust=requester_trust,
        smart_matches=smart_matches
    )


@requests_bp.route('/create', methods=['GET', 'POST'])
@requests_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_request():
    """
    Post a new Wanted Board listing for needed textbooks, kits, notes, or equipment.
    """
    db = get_db()
    if request.method == 'POST':
        resource_name = request.form.get('resource_name', '').strip() or request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip() or request.form.get('subject', '').strip() or 'Notes'
        department = request.form.get('department', '').strip() or session.get('department', 'CSE')
        semester = request.form.get('semester', 'All').strip()
        urgency = request.form.get('urgency', 'medium').strip().lower()
        required_date = request.form.get('required_date', '').strip()

        if not resource_name or not category or not department:
            flash("Resource Name, Category, and Department are required.", "danger")
            categories = list(db['categories'].find({}))
            return render_template('requests/create.html', categories=categories, form=request.form)

        new_req = {
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "user_name": session.get('full_name') or session.get('username'),
            "user_email": session.get('email', ''),
            "resource_name": resource_name,
            "description": description,
            "category": category,
            "department": department,
            "semester": semester,
            "urgency": urgency,
            "required_date": required_date,
            "status": "open",  # open, matched, fulfilled, cancelled
            "response_note": None,
            "fulfilled_by": None,
            "created_at": datetime.now(timezone.utc)
        }

        inserted_id = db['resource_requests'].insert_one(new_req).inserted_id

        # Log Activity
        db['activities'].insert_one({
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "action": "CREATED_REQUEST",
            "description": f"Posted Wanted notice: '{resource_name}' ({category})",
            "created_at": datetime.now(timezone.utc)
        })

        flash(f"Wanted Board notice for '{resource_name}' posted successfully!", "success")
        return redirect(url_for('requests.view_request', request_id=str(inserted_id)))

    categories = list(db['categories'].find({}))
    return render_template('requests/create.html', active_page='requests', categories=categories, form={})


@requests_bp.route('/fulfill/<request_id>', methods=['POST'])
@login_required
def fulfill_request(request_id):
    """
    Marks a Wanted request as fulfilled.
    Awards +15 contribution points to the fulfilling student or faculty member.
    """
    db = get_db()
    try:
        obj_id = ObjectId(request_id)
    except Exception:
        flash("Invalid request identifier.", "danger")
        return redirect(url_for('requests.list_requests'))

    req_doc = db['resource_requests'].find_one({"_id": obj_id})
    if not req_doc:
        flash("Request not found.", "warning")
        return redirect(url_for('requests.list_requests'))

    fulfiller_id = session.get('user_id')
    fulfiller_name = session.get('full_name') or session.get('username')
    response_note = request.form.get('response_note', 'Provided requested resource to peer.').strip()

    db['resource_requests'].update_one(
        {"_id": obj_id},
        {"$set": {
            "status": "fulfilled",
            "fulfilled_by": fulfiller_id,
            "fulfiller_name": fulfiller_name,
            "response_note": response_note,
            "fulfilled_at": datetime.now(timezone.utc)
        }}
    )

    # Award points to the fulfiller (+15 points)
    award_user_points(fulfiller_id, 15, f"Fulfilled Wanted request '{req_doc.get('resource_name')}'", db)

    # Notify requester
    if req_doc.get('user_id'):
        db['notifications'].insert_one({
            "user_id": req_doc.get('user_id'),
            "title": f"Wanted Request Fulfilled: '{req_doc.get('resource_name')}'",
            "message": f"{fulfiller_name} responded to fulfill your request: '{response_note}'",
            "category": "requests",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    flash(f"Thank you! You fulfilled '{req_doc.get('resource_name')}' (+15 contribution points awarded)!", "success")
    return redirect(url_for('requests.view_request', request_id=request_id))


@requests_bp.route('/update-status/<request_id>', methods=['POST'])
@login_required
def update_status(request_id):
    """
    Allows Faculty and Administrators to respond to or update request status.
    """
    db = get_db()
    try:
        obj_id = ObjectId(request_id)
    except Exception:
        flash("Invalid request identifier.", "danger")
        return redirect(url_for('requests.list_requests'))

    req_doc = db['resource_requests'].find_one({"_id": obj_id})
    if not req_doc:
        flash("Request not found.", "warning")
        return redirect(url_for('requests.list_requests'))

    new_status = request.form.get('status', '').strip().lower()
    response_note = request.form.get('response_note', '').strip()

    if new_status not in ['accepted', 'fulfilled', 'rejected', 'cancelled', 'matched']:
        flash("Invalid status transition.", "danger")
        return redirect(url_for('requests.list_requests'))

    db['resource_requests'].update_one(
        {"_id": obj_id},
        {"$set": {
            "status": new_status,
            "response_note": response_note,
            "fulfilled_by": session.get('user_id'),
            "fulfiller_name": session.get('full_name') or session.get('username'),
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    if new_status == 'fulfilled':
        award_user_points(session.get('user_id'), 15, f"Fulfilled request '{req_doc.get('resource_name')}'", db)

    # Notify requesting student
    if req_doc.get('user_id'):
        db['notifications'].insert_one({
            "user_id": req_doc.get('user_id'),
            "title": f"Request Status: {new_status.title()}",
            "message": f"Your request for '{req_doc.get('resource_name')}' was marked as {new_status}.",
            "category": "requests",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    flash(f"Request status successfully updated to {new_status.upper()}.", "success")
    return redirect(url_for('requests.list_requests'))


@requests_bp.route('/cancel/<request_id>', methods=['POST'])
@login_required
def cancel_request(request_id):
    """
    Allows a student to cancel their own pending or open wanted request.
    """
    db = get_db()
    try:
        obj_id = ObjectId(request_id)
    except Exception:
        flash("Invalid request identifier.", "danger")
        return redirect(url_for('requests.list_requests'))

    req_doc = db['resource_requests'].find_one({"_id": obj_id})
    if not req_doc:
        flash("Request not found.", "warning")
        return redirect(url_for('requests.list_requests'))

    user_id = session.get('user_id')
    role = session.get('role')
    if req_doc.get('user_id') != user_id and role != 'admin':
        flash("Unauthorized to cancel this request.", "danger")
        return redirect(url_for('requests.list_requests'))

    db['resource_requests'].update_one(
        {"_id": obj_id},
        {"$set": {
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    flash(f"Your request for '{req_doc.get('resource_name')}' has been cancelled.", "info")
    return redirect(url_for('requests.list_requests'))

