from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('', methods=['GET'])
@notifications_bp.route('/', methods=['GET'])
@login_required
def list_notifications():
    """
    Displays the user's notifications with read/unread filtering.
    """
    db = get_db()
    user_id = session.get('user_id')
    filter_status = request.args.get('filter', 'all').strip().lower()

    query = {"user_id": user_id}
    if filter_status == 'unread':
        query["is_read"] = False
    elif filter_status == 'read':
        query["is_read"] = True

    notifications_list = list(db['notifications'].find(query).sort("created_at", -1))

    total_count = db['notifications'].count_documents({"user_id": user_id})
    unread_count = db['notifications'].count_documents({"user_id": user_id, "is_read": False})
    read_count = db['notifications'].count_documents({"user_id": user_id, "is_read": True})

    return render_template(
        'notifications/index.html',
        active_page='notifications',
        notifications=notifications_list,
        filter_status=filter_status,
        stats={
            'total': total_count,
            'unread': unread_count,
            'read': read_count
        }
    )

@notifications_bp.route('/mark-read/<notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    """
    Marks an individual notification as read.
    """
    db = get_db()
    try:
        obj_id = ObjectId(notification_id)
    except Exception:
        flash("Invalid notification ID.", "danger")
        return redirect(url_for('notifications.list_notifications'))

    db['notifications'].update_one(
        {"_id": obj_id, "user_id": session.get('user_id')},
        {"$set": {"is_read": True}}
    )
    return redirect(url_for('notifications.list_notifications'))

@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """
    Marks all notifications for the current user as read.
    """
    db = get_db()
    user_id = session.get('user_id')
    db['notifications'].update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    flash("All notifications marked as read.", "success")
    return redirect(url_for('notifications.list_notifications'))

@notifications_bp.route('/delete/<notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    """
    Deletes an individual notification document from MongoDB.
    """
    db = get_db()
    try:
        obj_id = ObjectId(notification_id)
    except Exception:
        flash("Invalid notification ID.", "danger")
        return redirect(url_for('notifications.list_notifications'))

    db['notifications'].delete_one({"_id": obj_id, "user_id": session.get('user_id')})
    flash("Notification deleted.", "info")
    return redirect(url_for('notifications.list_notifications'))

@notifications_bp.route('/clear-read', methods=['POST'])
@login_required
def clear_read():
    """
    Clears all read notifications for the current user.
    """
    db = get_db()
    user_id = session.get('user_id')
    result = db['notifications'].delete_many({"user_id": user_id, "is_read": True})
    flash(f"Cleared {result.deleted_count} read notifications.", "info")
    return redirect(url_for('notifications.list_notifications'))
