from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required

reviews_bp = Blueprint('reviews', __name__, url_prefix='/reviews')

def recalculate_resource_rating(db, resource_id_str, resource_obj_id):
    """
    Recalculates average rating and review count using a MongoDB aggregation pipeline
    and updates the denormalized summary fields on the parent resource document.
    """
    agg = list(db['reviews'].aggregate([
        {"$match": {"resource_id": resource_id_str}},
        {"$group": {
            "_id": "$resource_id",
            "avg_rating": {"$avg": "$rating"},
            "count": {"$sum": 1}
        }}
    ]))

    if agg:
        new_avg = round(float(agg[0]['avg_rating']), 1)
        new_count = int(agg[0]['count'])
    else:
        new_avg = 5.0
        new_count = 0

    db['resources'].update_one(
        {"_id": resource_obj_id},
        {"$set": {"rating": new_avg, "review_count": new_count}}
    )
    return new_avg, new_count

@reviews_bp.route('/add/<resource_id>', methods=['POST'])
@login_required
def add_review(resource_id):
    """
    Adds a peer rating and text feedback for a campus resource.
    Demonstrates Referencing Pattern and Aggregation Pipeline for average calculation.
    """
    db = get_db()
    try:
        obj_id = ObjectId(resource_id)
    except Exception:
        flash("Invalid resource ID.", "danger")
        return redirect(url_for('resources.list_resources'))

    resource = db['resources'].find_one({"_id": obj_id})
    if not resource:
        flash("Resource not found.", "danger")
        return redirect(url_for('resources.list_resources'))

    try:
        rating = int(request.form.get('rating', '5'))
        if rating < 1 or rating > 5:
            rating = 5
    except ValueError:
        rating = 5

    comment = request.form.get('comment', '').strip()
    if not comment:
        flash("Please provide comments or feedback on the resource.", "warning")
        return redirect(url_for('resources.view_resource', resource_id=resource_id))

    # Check if user already reviewed this item - allow updating or new insert
    existing_review = db['reviews'].find_one({
        "resource_id": str(obj_id),
        "user_id": session.get('user_id')
    })

    if existing_review:
        db['reviews'].update_one(
            {"_id": existing_review['_id']},
            {"$set": {
                "rating": rating,
                "comment": comment,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        flash("Your review has been updated.", "success")
    else:
        new_review = {
            "resource_id": str(obj_id),
            "resource_title": resource.get('title'),
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "user_name": session.get('full_name') or session.get('username'),
            "rating": rating,
            "comment": comment,
            "created_at": datetime.now(timezone.utc)
        }
        db['reviews'].insert_one(new_review)
        flash("Thank you for your rating and review!", "success")

    # Recalculate average rating via MongoDB aggregation pipeline
    recalculate_resource_rating(db, str(obj_id), obj_id)

    # Notify resource owner (if not reviewing own upload)
    if resource.get('owner_id') and resource.get('owner_id') != session.get('user_id'):
        db['notifications'].insert_one({
            "user_id": resource.get('owner_id'),
            "title": "New Resource Review",
            "message": f"{session.get('full_name')} rated '{resource.get('title')}' with {rating} stars: \"{comment[:80]}...\"",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    # Log user activity
    db['activities'].insert_one({
        "user_id": session.get('user_id'),
        "username": session.get('username'),
        "action": "REVIEWED_RESOURCE",
        "description": f"Reviewed '{resource.get('title')}' ({rating}/5 stars)",
        "created_at": datetime.now(timezone.utc)
    })

    return redirect(url_for('resources.view_resource', resource_id=resource_id))

@reviews_bp.route('/delete/<review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    """
    Deletes a user's review and recalculates the resource's average rating.
    """
    db = get_db()
    try:
        obj_id = ObjectId(review_id)
    except Exception:
        flash("Invalid review ID.", "danger")
        return redirect(url_for('resources.list_resources'))

    review = db['reviews'].find_one({"_id": obj_id})
    if not review:
        flash("Review not found.", "warning")
        return redirect(url_for('resources.list_resources'))

    if review.get('user_id') != session.get('user_id') and session.get('role') != 'admin':
        flash("Unauthorized: You can only delete your own reviews.", "danger")
        return redirect(url_for('resources.view_resource', resource_id=review.get('resource_id')))

    resource_id_str = review.get('resource_id')
    db['reviews'].delete_one({"_id": obj_id})

    # Recalculate average rating
    try:
        res_obj_id = ObjectId(resource_id_str)
        recalculate_resource_rating(db, resource_id_str, res_obj_id)
    except Exception:
        pass

    flash("Review removed successfully.", "info")
    return redirect(url_for('resources.view_resource', resource_id=resource_id_str))

@reviews_bp.route('/user/<target_user_id>', methods=['POST'])
@login_required
def add_user_review(target_user_id):
    """
    Peer reputation review: Allows students to rate sellers, borrowers, and lenders.
    Feeds into the recipient's Trust Score calculation.
    """
    from utils.trust import calculate_trust_score, award_user_points
    db = get_db()
    reviewer_id = session.get('user_id')

    if reviewer_id == target_user_id:
        flash("You cannot review yourself.", "warning")
        return redirect(url_for('profile.public_profile', target_user_id=target_user_id))

    try:
        rating = int(request.form.get('rating', '5'))
        rating = max(1, min(5, rating))
    except ValueError:
        rating = 5

    comment = request.form.get('comment', '').strip()
    transaction_type = request.form.get('transaction_type', 'general').strip()

    if not comment:
        flash("Please provide comments or feedback on your campus interaction.", "warning")
        return redirect(url_for('profile.public_profile', target_user_id=target_user_id))

    target_user = db['users'].find_one({"_id": ObjectId(target_user_id)})
    if not target_user:
        flash("User not found.", "warning")
        return redirect(url_for('marketplace.list_items'))

    new_user_review = {
        "reviewee_id": target_user_id,
        "reviewee_name": target_user.get('full_name'),
        "reviewer_id": reviewer_id,
        "reviewer_name": session.get('full_name') or session.get('username'),
        "reviewer_username": session.get('username'),
        "rating": rating,
        "comment": comment,
        "transaction_type": transaction_type,
        "created_at": datetime.now(timezone.utc)
    }

    db['user_reviews'].insert_one(new_user_review)

    # Award points for positive peer review
    if rating >= 4:
        award_user_points(target_user_id, 5, f"Received {rating}-star peer review from {session.get('full_name')}", db)

    # Recalculate recipient's trust score
    calculate_trust_score(target_user_id, db)

    # Notify recipient
    db['notifications'].insert_one({
        "user_id": target_user_id,
        "title": f"New {rating}-Star Peer Review Received",
        "message": f"{session.get('full_name')} reviewed you: \"{comment[:80]}...\"",
        "category": "reviews",
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    })

    flash("Your peer review has been submitted. Thank you for strengthening campus trust!", "success")
    return redirect(url_for('profile.public_profile', target_user_id=target_user_id))

