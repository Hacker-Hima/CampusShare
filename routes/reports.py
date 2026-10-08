from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/create/<resource_id>', methods=['POST'])
@login_required
def create_report(resource_id):
    """
    Submits a community moderation flag against a resource
    (e.g., copyright violation, spam, inaccurate solutions).
    """
    db = get_db()
    try:
        obj_id = ObjectId(resource_id)
    except Exception:
        flash("Invalid resource ID.", "danger")
        return redirect(url_for('resources.list_resources'))

    resource = db['resources'].find_one({"_id": obj_id})
    if not resource:
        flash("Resource not found.", "warning")
        return redirect(url_for('resources.list_resources'))

    reason = request.form.get('reason', 'Other').strip()
    details = request.form.get('details', '').strip()

    new_report = {
        "resource_id": str(obj_id),
        "resource_title": resource.get('title'),
        "resource_owner_id": resource.get('owner_id'),
        "target_type": "resource",
        "user_id": session.get('user_id'),
        "username": session.get('username'),
        "reason": reason,
        "details": details,
        "status": "pending",  # pending, resolved, dismissed
        "created_at": datetime.now(timezone.utc)
    }

    db['reports'].insert_one(new_report)

    # Log user activity
    db['activities'].insert_one({
        "user_id": session.get('user_id'),
        "username": session.get('username'),
        "action": "REPORTED_RESOURCE",
        "description": f"Reported '{resource.get('title')}' for {reason}",
        "created_at": datetime.now(timezone.utc)
    })

    # Notify administrator accounts
    admins = list(db['users'].find({"role": "admin"}))
    for adm in admins:
        db['notifications'].insert_one({
            "user_id": str(adm['_id']),
            "title": "New Resource Report Flagged",
            "message": f"User {session.get('username')} flagged '{resource.get('title')}' for: {reason}.",
            "category": "admin",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    flash("Resource report submitted for review by the academic administration board.", "info")
    return redirect(url_for('resources.view_resource', resource_id=resource_id))


@reports_bp.route('/marketplace/<item_id>', methods=['POST'])
@login_required
def report_marketplace_item(item_id):
    """
    Flags an inappropriate or fraudulent marketplace listing.
    """
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        flash("Invalid item ID.", "danger")
        return redirect(url_for('marketplace.list_items'))

    item = db['marketplace'].find_one({"_id": obj_id})
    if not item:
        flash("Marketplace listing not found.", "warning")
        return redirect(url_for('marketplace.list_items'))

    reason = request.form.get('reason', 'Fake / Inappropriate listing').strip()
    details = request.form.get('details', '').strip()

    new_report = {
        "resource_id": str(obj_id),
        "resource_title": item.get('title'),
        "resource_owner_id": item.get('seller_id'),
        "target_type": "marketplace",
        "user_id": session.get('user_id'),
        "username": session.get('username'),
        "reason": reason,
        "details": details,
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }

    db['reports'].insert_one(new_report)
    flash("Marketplace listing flagged for administrative moderation.", "info")
    return redirect(url_for('marketplace.view_item', item_id=item_id))


@reports_bp.route('/dispute/create', methods=['POST'])
@login_required
def create_dispute():
    """
    Opens an official transaction dispute for marketplace or hardware borrowings.
    Workflow: Problem reported -> Dispute opened -> Admin review -> Resolution.
    Statuses: OPEN, UNDER REVIEW, RESOLVED, REJECTED.
    """
    db = get_db()
    transaction_type = request.form.get('transaction_type', 'marketplace').strip()
    transaction_id = request.form.get('transaction_id', '').strip()
    respondent_id = request.form.get('respondent_id', '').strip()
    reason = request.form.get('reason', 'Item not delivered / condition mismatch').strip()
    details = request.form.get('details', '').strip()

    if not transaction_id or not details:
        flash("Transaction identifier and problem details are required.", "warning")
        return redirect(url_for('profile.view_profile'))

    new_dispute = {
        "transaction_type": transaction_type,
        "transaction_id": transaction_id,
        "complainant_id": session.get('user_id'),
        "complainant_name": session.get('full_name') or session.get('username'),
        "respondent_id": respondent_id,
        "reason": reason,
        "details": details,
        "status": "OPEN",  # OPEN, UNDER REVIEW, RESOLVED, REJECTED
        "admin_resolution": None,
        "created_at": datetime.now(timezone.utc)
    }

    db['disputes'].insert_one(new_dispute)

    # Notify administrators
    admins = list(db['users'].find({"role": "admin"}))
    for adm in admins:
        db['notifications'].insert_one({
            "user_id": str(adm['_id']),
            "title": "🚨 New Transaction Dispute Opened",
            "message": f"Student {session.get('full_name')} opened a dispute: {reason}.",
            "category": "admin",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    flash("Transaction dispute opened. Campus Administration will mediate and review within 24 hours.", "success")
    return redirect(url_for('profile.view_profile'))
