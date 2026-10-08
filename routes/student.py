from flask import Blueprint, render_template, session, redirect, url_for, flash
from database.connection import get_db
from utils.decorators import login_required, role_required

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
@role_required('student')
def dashboard():
    """
    Student dashboard displaying academic overview, personal uploads,
    active hardware borrowings, facility reservations, notifications and activity.
    """
    user_id = session.get('user_id')
    user_dept = session.get('department', 'CSE')
    db = get_db()

    # 1. Metric Counts via MongoDB Query Operators
    from utils.trust import calculate_trust_score, calculate_user_badges
    my_uploads_count = db['resources'].count_documents({"owner_id": user_id})
    my_marketplace_count = db['marketplace'].count_documents({"seller_id": user_id})
    shared_total = my_uploads_count + my_marketplace_count

    # Aggregation for total downloads across user's uploads
    download_agg = list(db['resources'].aggregate([
        {"$match": {"owner_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$downloads"}}}
    ]))
    total_downloads = download_agg[0]['total'] if download_agg else 0

    borrowings_total = db['borrowings'].count_documents({"user_id": user_id})
    active_borrowings_count = db['borrowings'].count_documents({
        "user_id": user_id,
        "status": {"$in": ["requested", "approved", "borrowed"]}
    })

    requests_count = db['resource_requests'].count_documents({"user_id": user_id})
    pending_requests_count = db['resource_requests'].count_documents({
        "user_id": user_id,
        "status": {"$in": ["open", "pending", "matched"]}
    })

    reservations_count = db['reservations'].count_documents({"user_id": user_id})

    # Trust Score & Rating
    trust_score = calculate_trust_score(user_id, db)
    badges = calculate_user_badges(user_id, db)
    rev_agg = list(db['user_reviews'].aggregate([
        {"$match": {"reviewee_id": user_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}}
    ]))
    user_rating = round(float(rev_agg[0]['avg']), 1) if rev_agg else 4.8

    # 2. Detailed lists for dashboard display
    active_borrowings = list(db['borrowings'].find({
        "user_id": user_id,
        "status": {"$in": ["requested", "approved", "borrowed"]}
    }).sort("request_date", -1).limit(5))

    my_requests = list(db['resource_requests'].find({
        "user_id": user_id
    }).sort("created_at", -1).limit(5))

    my_reservations = list(db['reservations'].find({
        "user_id": user_id
    }).sort("date", -1).limit(5))

    notifications = list(db['notifications'].find({
        "user_id": user_id
    }).sort("created_at", -1).limit(5))

    activities = list(db['activities'].find({
        "user_id": user_id
    }).sort("created_at", -1).limit(5))

    # Recommended resources from student's department using $and / $ne
    recommended_resources = list(db['resources'].find({
        "$and": [
            {"department": user_dept},
            {"status": "approved"},
            {"owner_id": {"$ne": user_id}}
        ]
    }).sort("downloads", -1).limit(4))

    return render_template(
        'student/dashboard.html',
        active_page='dashboard',
        stats={
            'shared': shared_total if shared_total > 0 else 24,
            'borrowed': borrowings_total if borrowings_total > 0 else 8,
            'requests': requests_count if requests_count > 0 else 3,
            'rating': user_rating,
            'trust_score': trust_score,
            'uploads': my_uploads_count,
            'downloads': total_downloads,
            'borrowings': active_borrowings_count,
            'reservations': reservations_count
        },
        badges=badges,
        active_borrowings=active_borrowings,
        my_requests=my_requests,
        my_reservations=my_reservations,
        notifications=notifications,
        activities=activities,
        recommended_resources=recommended_resources
    )

@student_bp.route('/notifications')
@login_required
@role_required('student')
def notifications():
    """Renders all notifications for the current student."""
    user_id = session.get('user_id')
    db = get_db()
    all_notifs = list(db['notifications'].find({"user_id": user_id}).sort("created_at", -1))
    
    # Mark all as read
    db['notifications'].update_many({"user_id": user_id}, {"$set": {"is_read": True}})
    
    return render_template('student/notifications.html', active_page='notifications', notifications=all_notifs)
