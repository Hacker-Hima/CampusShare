import re
from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required
from utils.helpers import save_uploaded_file
from utils.trust import award_user_points

lost_found_bp = Blueprint('lost_found', __name__, url_prefix='/lost-found')

LF_CATEGORIES = [
    "Calculators", "Electronics", "Books & Notebooks", 
    "ID Cards & Wallets", "Keys", "Clothing & Accessories", "Other"
]

@lost_found_bp.route('', methods=['GET'])
@lost_found_bp.route('/', methods=['GET'])
def list_items():
    """
    Campus Lost & Found community board with type filters (Lost / Found / Recovered)
    and full-text keyword search across campus locations.
    """
    db = get_db()
    
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    item_type = request.args.get('type', 'all').strip().lower()

    query = {}

    if item_type in ['lost', 'found', 'recovered']:
        if item_type == 'recovered':
            query["status"] = "recovered"
        else:
            query["item_type"] = item_type
            query["status"] = {"$in": ["lost", "found"]}

    if q:
        safe_q = re.escape(q)
        regex = {"$regex": safe_q, "$options": "i"}
        query["$or"] = [
            {"title": regex},
            {"description": regex},
            {"location": regex}
        ]

    if category and category in LF_CATEGORIES:
        query["category"] = category

    items = list(db['lost_found'].find(query).sort("created_at", -1))

    # Metric counts for header badges
    lost_count = db['lost_found'].count_documents({"item_type": "lost", "status": "lost"})
    found_count = db['lost_found'].count_documents({"item_type": "found", "status": "found"})
    recovered_count = db['lost_found'].count_documents({"status": "recovered"})

    return render_template(
        'lost_found/list.html',
        active_page='lost_found',
        items=items,
        categories=LF_CATEGORIES,
        current_filters={
            'q': q,
            'category': category,
            'type': item_type
        },
        stats={
            'lost': lost_count,
            'found': found_count,
            'recovered': recovered_count
        }
    )


@lost_found_bp.route('/item/<item_id>')
def view_item(item_id):
    """
    Detailed incident report for a lost or found campus possession,
    with verification claim workflow and finder contact links.
    """
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        flash("Invalid item identifier.", "danger")
        return redirect(url_for('lost_found.list_items'))

    item = db['lost_found'].find_one({"_id": obj_id})
    if not item:
        flash("Lost & Found report not found.", "warning")
        return redirect(url_for('lost_found.list_items'))

    # Fetch existing claims if reporter is viewing
    user_id = session.get('user_id')
    claims = list(db['lost_found_claims'].find({"item_id": str(obj_id)}).sort("created_at", -1))

    return render_template(
        'lost_found/detail.html',
        active_page='lost_found',
        item=item,
        claims=claims,
        is_reporter=(user_id and user_id == item.get('reporter_id'))
    )


@lost_found_bp.route('/report-lost', methods=['GET', 'POST'])
@login_required
def report_lost():
    """
    Submits a new Lost Item notification.
    """
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        location = request.form.get('location', '').strip()
        incident_date = request.form.get('incident_date', '').strip()
        contact_info = request.form.get('contact_info', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not category or not location:
            flash("Item Title, Category, and Last Seen Location are required.", "danger")
            return render_template('lost_found/report_lost.html', categories=LF_CATEGORIES, form=request.form)

        saved_file, _ = save_uploaded_file(request.files.get('photo'))

        user_id = session.get('user_id')
        new_entry = {
            "item_type": "lost",
            "title": title,
            "category": category,
            "location": location,
            "incident_date": incident_date,
            "contact_info": contact_info or session.get('email', ''),
            "description": description,
            "image_path": saved_file,
            "reporter_id": user_id,
            "reporter_name": session.get('full_name') or session.get('username'),
            "status": "lost",
            "created_at": datetime.now(timezone.utc)
        }

        inserted_id = db['lost_found'].insert_one(new_entry).inserted_id
        flash(f"Lost item report for '{title}' posted. Campus security and community have been alerted.", "success")
        return redirect(url_for('lost_found.view_item', item_id=str(inserted_id)))

    return render_template('lost_found/report_lost.html', active_page='lost_found', categories=LF_CATEGORIES, form={})


@lost_found_bp.route('/report-found', methods=['GET', 'POST'])
@login_required
def report_found():
    """
    Submits a new Found Item notice and logs custody details.
    """
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        location = request.form.get('location', '').strip()
        incident_date = request.form.get('incident_date', '').strip()
        storage_location = request.form.get('storage_location', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not category or not location:
            flash("Item Title, Category, and Location Found are required.", "danger")
            return render_template('lost_found/report_found.html', categories=LF_CATEGORIES, form=request.form)

        saved_file, _ = save_uploaded_file(request.files.get('photo'))

        user_id = session.get('user_id')
        new_entry = {
            "item_type": "found",
            "title": title,
            "category": category,
            "location": location,
            "incident_date": incident_date,
            "storage_location": storage_location or "Deposited at Department Reception / Security",
            "description": description,
            "image_path": saved_file,
            "reporter_id": user_id,
            "reporter_name": session.get('full_name') or session.get('username'),
            "status": "found",
            "created_at": datetime.now(timezone.utc)
        }

        inserted_id = db['lost_found'].insert_one(new_entry).inserted_id
        # Award points for good campus citizenship!
        award_user_points(user_id, 10, f"Reported found possession '{title}'", db)

        flash(f"Thank you! Found item report for '{title}' submitted (+10 points).", "success")
        return redirect(url_for('lost_found.view_item', item_id=str(inserted_id)))

    return render_template('lost_found/report_found.html', active_page='lost_found', categories=LF_CATEGORIES, form={})


@lost_found_bp.route('/item/<item_id>/claim', methods=['POST'])
@login_required
def claim_item(item_id):
    """
    Submits an ownership claim with identifying proof for a found item.
    """
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        flash("Invalid item identifier.", "danger")
        return redirect(url_for('lost_found.list_items'))

    item = db['lost_found'].find_one({"_id": obj_id})
    if not item:
        flash("Item not found.", "warning")
        return redirect(url_for('lost_found.list_items'))

    proof_details = request.form.get('proof_details', '').strip()
    if not proof_details:
        flash("Please describe details proving your ownership.", "warning")
        return redirect(url_for('lost_found.view_item', item_id=item_id))

    user_id = session.get('user_id')
    new_claim = {
        "item_id": str(obj_id),
        "claimant_id": user_id,
        "claimant_name": session.get('full_name') or session.get('username'),
        "claimant_email": session.get('email', ''),
        "proof_details": proof_details,
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }

    db['lost_found_claims'].insert_one(new_claim)

    # Notify finder
    if item.get('reporter_id'):
        db['notifications'].insert_one({
            "user_id": item.get('reporter_id'),
            "title": f"Ownership Claim Submitted for '{item.get('title')}'",
            "message": f"{session.get('full_name')} submitted an ownership claim with verification proof.",
            "category": "requests",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    flash("Your ownership claim has been submitted to the finder and campus security.", "success")
    return redirect(url_for('lost_found.view_item', item_id=item_id))


@lost_found_bp.route('/item/<item_id>/resolve', methods=['POST'])
@login_required
def resolve_item(item_id):
    """
    Marks an item as safely recovered / returned to owner.
    """
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        flash("Invalid item identifier.", "danger")
        return redirect(url_for('lost_found.list_items'))

    item = db['lost_found'].find_one({"_id": obj_id})
    user_id = session.get('user_id')
    role = session.get('role')

    if not item or (item.get('reporter_id') != user_id and role != 'admin'):
        flash("Unauthorized to resolve this item.", "danger")
        return redirect(url_for('lost_found.view_item', item_id=item_id))

    db['lost_found'].update_one(
        {"_id": obj_id},
        {"$set": {"status": "recovered", "recovered_at": datetime.now(timezone.utc)}}
    )

    flash(f"'{item.get('title')}' has been marked as RECOVERED! Thank you for keeping the campus secure.", "success")
    return redirect(url_for('lost_found.view_item', item_id=item_id))
