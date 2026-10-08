from datetime import datetime, timezone
import re
from bson import ObjectId

def calculate_trust_score(user_id, db):
    """
    Computes a realistic campus trust score (0 - 100) using a multi-factor formula:
    - Base Verified Status: +20 points
    - Peer Reviews (Rating out of 5): up to +35 points
    - Successful Transactions (Marketplace sales, returns, fulfilled requests): up to +30 points
    - Active Contributor Activity (Uploaded notes, active listings): up to +15 points
    - Penalties for verified reports / lost disputes: -15 points each
    Result is clamped between 20 and 100.
    """
    if not user_id:
        return 70

    try:
        user = db['users'].find_one({"_id": ObjectId(user_id) if isinstance(user_id, str) else user_id})
    except Exception:
        user = None

    if not user:
        return 70

    score = 40.0  # Base starting score for registered campus members

    # 1. Verification status (+20 points)
    if user.get('is_verified', False) or user.get('role') in ['faculty', 'admin']:
        score += 20.0

    # 2. Peer Reviews Calculation (up to +30 points)
    user_id_str = str(user['_id'])
    reviews_agg = list(db['user_reviews'].aggregate([
        {"$match": {"reviewee_id": user_id_str}},
        {"$group": {
            "_id": None,
            "avg_rating": {"$avg": "$rating"},
            "count": {"$sum": 1}
        }}
    ]))

    if reviews_agg and reviews_agg[0]['count'] > 0:
        avg_rating = float(reviews_agg[0]['avg_rating'])
        # Scale 5-star rating to 30 points
        score += (avg_rating / 5.0) * 30.0
    else:
        # Default neutral rating contribution for unreviewed members
        score += 20.0

    # 3. Successful Transactions (up to +25 points)
    # Count marketplace sold items
    sold_count = db['marketplace'].count_documents({"seller_id": user_id_str, "status": "sold"})
    # Count completed borrowings returned
    returned_borrowings = db['borrowings'].count_documents({"user_id": user_id_str, "status": "returned"})
    # Count fulfilled wanted requests
    fulfilled_reqs = db['resource_requests'].count_documents({"fulfilled_by": user_id_str, "status": "fulfilled"})

    total_successful = sold_count + returned_borrowings + fulfilled_reqs
    score += min(25.0, total_successful * 5.0)

    # 4. Academic uploads contribution (up to +10 points)
    uploads_count = db['resources'].count_documents({"owner_id": user_id_str})
    score += min(10.0, uploads_count * 3.0)

    # 5. Penalties for disputes or reports
    reports_count = db['reports'].count_documents({"resource_owner_id": user_id_str, "status": "resolved"})
    score -= (reports_count * 15.0)

    # Clamp score between 25 and 100
    final_score = int(round(max(25.0, min(100.0, score))))

    # Cache on user document
    db['users'].update_one({"_id": user['_id']}, {"$set": {"trust_score": final_score}})
    return final_score


def calculate_user_badges(user_id, db):
    """
    Evaluates and returns user recognition badges based on activities:
    - '📚 Resource Contributor': Uploaded 2+ academic resources
    - '🤝 Helpful Student': Fulfilled >= 1 wanted request
    - '⭐ Trusted Member': Trust score >= 85 and verified
    - '♻ Campus Reuser': Completed >= 2 marketplace or borrowing transactions
    - '🏆 Campus Champion': Trust score >= 90 and points >= 30
    """
    if not user_id:
        return []

    try:
        user = db['users'].find_one({"_id": ObjectId(user_id) if isinstance(user_id, str) else user_id})
    except Exception:
        user = None

    if not user:
        return []

    user_id_str = str(user['_id'])
    badges = []

    # 1. Resource Contributor
    uploads_count = db['resources'].count_documents({"owner_id": user_id_str})
    if uploads_count >= 2:
        badges.append({
            "name": "Resource Contributor",
            "icon": "bi-journal-bookmark-fill",
            "color": "primary",
            "desc": f"Uploaded {uploads_count} verified academic resources"
        })

    # 2. Helpful Student
    fulfilled_reqs = db['resource_requests'].count_documents({"fulfilled_by": user_id_str, "status": "fulfilled"})
    if fulfilled_reqs >= 1:
        badges.append({
            "name": "Helpful Student",
            "icon": "bi-heart-fill",
            "color": "danger",
            "desc": f"Fulfilled {fulfilled_reqs} student wanted requests"
        })

    # 3. Trusted Member
    trust_score = user.get('trust_score', calculate_trust_score(user_id_str, db))
    if trust_score >= 85 and user.get('is_verified', False):
        badges.append({
            "name": "Trusted Member",
            "icon": "bi-patch-check-fill",
            "color": "success",
            "desc": f"High trust score ({trust_score}/100) & verified student"
        })

    # 4. Campus Reuser
    sold_items = db['marketplace'].count_documents({"seller_id": user_id_str, "status": "sold"})
    borrowed_items = db['borrowings'].count_documents({"user_id": user_id_str, "status": "returned"})
    if (sold_items + borrowed_items) >= 2:
        badges.append({
            "name": "Campus Reuser",
            "icon": "bi-recycle",
            "color": "info",
            "desc": "Active participant in campus marketplace and hardware reuse"
        })

    # 5. Campus Champion
    points = user.get('points', 0)
    if trust_score >= 90 and points >= 30:
        badges.append({
            "name": "Campus Champion",
            "icon": "bi-trophy-fill",
            "color": "warning",
            "desc": f"Top platform contributor with {points} points and 90+ trust"
        })

    # Save badges array on user
    badge_names = [b['name'] for b in badges]
    db['users'].update_one({"_id": user['_id']}, {"$set": {"badges": badge_names}})
    return badges


def award_user_points(user_id, points, reason, db):
    """
    Increments contribution points, logs activity, and sends notification to user.
    """
    if not user_id or points <= 0:
        return

    try:
        user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
        db['users'].update_one(
            {"_id": user_obj_id},
            {"$inc": {"points": points}}
        )
        user = db['users'].find_one({"_id": user_obj_id})

        # Activity log
        db['activities'].insert_one({
            "user_id": str(user_obj_id),
            "username": user.get('username') if user else 'user',
            "action": "EARNED_POINTS",
            "description": f"+{points} points: {reason}",
            "created_at": datetime.now(timezone.utc)
        })

        # Notification
        db['notifications'].insert_one({
            "user_id": str(user_obj_id),
            "title": f"+{points} Contribution Points Earned!",
            "message": f"You earned {points} campus contribution points for: {reason}.",
            "category": "reputation",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

        # Recalculate badges
        calculate_user_badges(user_obj_id, db)
    except Exception as e:
        print(f"[Points Warning] Could not award points: {e}")


def find_smart_matches(query_text, category, department, db):
    """
    Smart Resource Matching:
    Searches available items across Marketplace and Academic Library
    matching the query keyword, category, or department.
    Demonstrates MongoDB regex and multi-collection search.
    """
    matches = {
        "marketplace": [],
        "academic": []
    }

    if not query_text and not category:
        return matches

    # Extract keywords
    words = [re.escape(w.strip()) for w in (query_text or '').split() if len(w.strip()) >= 3]
    regex_conditions = []
    for word in words:
        regex_conditions.append({"title": {"$regex": word, "$options": "i"}})
        regex_conditions.append({"description": {"$regex": word, "$options": "i"}})

    # 1. Search Marketplace
    marketplace_query = {"status": "available"}
    m_or = []
    if regex_conditions:
        m_or.extend(regex_conditions)
    if category:
        m_or.append({"category": category})

    if m_or:
        marketplace_query["$or"] = m_or

    matches["marketplace"] = list(db['marketplace'].find(marketplace_query).limit(4))

    # 2. Search Academic Resources Library
    academic_query = {"status": "approved", "availability": "available"}
    a_or = []
    if regex_conditions:
        a_or.extend(regex_conditions)
    if category:
        a_or.append({"category": category})
    if department:
        a_or.append({"department": department})

    if a_or:
        academic_query["$or"] = a_or

    matches["academic"] = list(db['resources'].find(academic_query).limit(4))

    return matches
