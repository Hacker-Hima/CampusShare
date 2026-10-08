from flask import Blueprint, render_template, session, redirect, url_for, flash
from database.connection import get_db
from utils.decorators import login_required, role_required

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

@faculty_bp.route('/dashboard')
@login_required
@role_required('faculty', 'admin')
def dashboard():
    """
    Faculty dashboard displaying uploaded materials, pending peer reviews,
    student academic requests, and material usage analytics.
    """
    user_id = session.get('user_id')
    user_dept = session.get('department', 'CSE')
    db = get_db()

    # 1. Statistics
    my_uploads_count = db['resources'].count_documents({"owner_id": user_id})
    pending_approvals_count = db['resources'].count_documents({"status": "pending"})
    open_requests_count = db['resource_requests'].count_documents({"status": "pending"})

    download_agg = list(db['resources'].aggregate([
        {"$match": {"owner_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$downloads"}}}
    ]))
    total_downloads = download_agg[0]['total'] if download_agg else 0

    # 2. Lists for Dashboard
    # Faculty's top downloaded resources
    top_resources = list(db['resources'].find({
        "owner_id": user_id
    }).sort("downloads", -1).limit(5))

    # Academic requests needing faculty attention (in same department)
    open_requests = list(db['resource_requests'].find({
        "status": "pending"
    }).sort("created_at", -1).limit(5))

    # Pending submissions waiting for review
    pending_submissions = list(db['resources'].find({
        "status": "pending"
    }).sort("created_at", -1).limit(5))

    # Recent activities in the department
    activities = list(db['activities'].find({}).sort("created_at", -1).limit(6))

    notifications = list(db['notifications'].find({
        "user_id": user_id
    }).sort("created_at", -1).limit(5))

    return render_template(
        'faculty/dashboard.html',
        active_page='dashboard',
        stats={
            'uploads': my_uploads_count,
            'downloads': total_downloads,
            'pending_approvals': pending_approvals_count,
            'open_requests': open_requests_count
        },
        top_resources=top_resources,
        open_requests=open_requests,
        pending_submissions=pending_submissions,
        activities=activities,
        notifications=notifications
    )

@faculty_bp.route('/notifications')
@login_required
@role_required('faculty', 'admin')
def notifications():
    """Renders all notifications for the faculty user."""
    user_id = session.get('user_id')
    db = get_db()
    all_notifs = list(db['notifications'].find({"user_id": user_id}).sort("created_at", -1))
    db['notifications'].update_many({"user_id": user_id}, {"$set": {"is_read": True}})
    return render_template('faculty/notifications.html', active_page='notifications', notifications=all_notifs)
