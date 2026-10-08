from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.connection import get_db
from utils.decorators import login_required
from utils.trust import calculate_trust_score, calculate_user_badges

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('')
@profile_bp.route('/')
@login_required
def view_profile():
    """
    Displays the authenticated user's profile, verification status,
    trust score (e.g. 94/100), badges, contribution stats, and activity history.
    """
    db = get_db()
    user_id = session.get('user_id')

    try:
        user = db['users'].find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None

    if not user:
        flash("User profile not found.", "danger")
        return redirect(url_for('index'))

    # Trust Score & Badges
    trust_score = calculate_trust_score(user_id, db)
    badges = calculate_user_badges(user_id, db)

    # Calculate user contributions and engagement metrics
    upload_count = db['resources'].count_documents({"owner_id": user_id})
    borrow_count = db['borrowings'].count_documents({"user_id": user_id})
    reservation_count = db['reservations'].count_documents({"user_id": user_id})
    review_count = db['reviews'].count_documents({"user_id": user_id})
    request_count = db['resource_requests'].count_documents({"user_id": user_id})
    marketplace_count = db['marketplace'].count_documents({"seller_id": user_id})
    sold_count = db['marketplace'].count_documents({"seller_id": user_id, "status": "sold"})

    # Fetch Peer Reviews received
    user_reviews = list(db['user_reviews'].find({"reviewee_id": user_id}).sort("created_at", -1).limit(5))
    rev_agg = list(db['user_reviews'].aggregate([
        {"$match": {"reviewee_id": user_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]))
    avg_rating = round(float(rev_agg[0]['avg']), 1) if rev_agg else 4.8

    # Fetch recent personal activity audit logs
    recent_activities = list(db['activities'].find({"user_id": user_id}).sort("created_at", -1).limit(10))

    # Active marketplace listings
    my_listings = list(db['marketplace'].find({"seller_id": user_id, "status": "available"}).limit(4))

    return render_template(
        'profile/view.html',
        active_page='profile',
        user=user,
        trust_score=trust_score,
        badges=badges,
        avg_rating=avg_rating,
        user_reviews=user_reviews,
        my_listings=my_listings,
        stats={
            'uploads': upload_count,
            'shared': upload_count + marketplace_count,
            'borrowings': borrow_count,
            'borrowed': borrow_count,
            'transactions': sold_count + borrow_count,
            'reservations': reservation_count,
            'reviews': review_count,
            'requests': request_count,
            'marketplace': marketplace_count
        },
        recent_activities=recent_activities
    )


@profile_bp.route('/user/<target_user_id>')
@login_required
def public_profile(target_user_id):
    """
    Public student/faculty reputation card.
    Allows campus peers to inspect trust score, verified status, badges,
    reviews, and active listings before initiating a borrow or purchase.
    """
    db = get_db()
    try:
        user = db['users'].find_one({"_id": ObjectId(target_user_id)})
    except Exception:
        user = None

    if not user:
        flash("User not found.", "warning")
        return redirect(url_for('marketplace.list_items'))

    trust_score = calculate_trust_score(target_user_id, db)
    badges = calculate_user_badges(target_user_id, db)

    # Stats
    upload_count = db['resources'].count_documents({"owner_id": target_user_id})
    borrow_count = db['borrowings'].count_documents({"user_id": target_user_id})
    sold_count = db['marketplace'].count_documents({"seller_id": target_user_id, "status": "sold"})
    marketplace_count = db['marketplace'].count_documents({"seller_id": target_user_id, "status": "available"})

    # Reviews received
    user_reviews = list(db['user_reviews'].find({"reviewee_id": target_user_id}).sort("created_at", -1))
    rev_agg = list(db['user_reviews'].aggregate([
        {"$match": {"reviewee_id": target_user_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]))
    avg_rating = round(float(rev_agg[0]['avg']), 1) if rev_agg else 5.0

    # Active listings
    active_listings = list(db['marketplace'].find({"seller_id": target_user_id, "status": "available"}))

    return render_template(
        'profile/public_profile.html',
        active_page='profile',
        user=user,
        trust_score=trust_score,
        badges=badges,
        avg_rating=avg_rating,
        user_reviews=user_reviews,
        active_listings=active_listings,
        stats={
            'shared': upload_count + marketplace_count,
            'borrowed': borrow_count,
            'transactions': sold_count + borrow_count
        }
    )


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Allows user to update profile details like full name, department, phone, bio,
    student ID, skills/interests, year, and section.
    """
    db = get_db()
    user_id = session.get('user_id')

    try:
        user = db['users'].find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None

    if not user:
        flash("User profile not found.", "danger")
        return redirect(url_for('profile.view_profile'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()
        bio = request.form.get('bio', '').strip()
        skills = request.form.get('skills', '').strip()
        student_id = request.form.get('student_id', '').strip()
        year = request.form.get('year', '').strip()
        section = request.form.get('section', '').strip()

        if not full_name:
            flash("Full name cannot be empty.", "warning")
            return render_template('profile/edit.html', user=user, active_page='profile')

        update_fields = {
            "full_name": full_name,
            "department": department,
            "phone": phone,
            "bio": bio,
            "skills": skills,
            "updated_at": datetime.now(timezone.utc)
        }

        if student_id:
            update_fields["student_id"] = student_id

        if user.get('role') == 'student':
            update_fields["year"] = year
            update_fields["section"] = section

        db['users'].update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

        # Update active session values
        session['full_name'] = full_name
        session['department'] = department

        flash("Profile information updated successfully.", "success")
        return redirect(url_for('profile.view_profile'))

    return render_template('profile/edit.html', user=user, active_page='profile')


@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    Allows user to change account password securely with Werkzeug hashing.
    """
    db = get_db()
    user_id = session.get('user_id')

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        user = db['users'].find_one({"_id": ObjectId(user_id)})
        if not user or not check_password_hash(user.get('password_hash', ''), current_password):
            flash("Incorrect current password.", "danger")
            return render_template('profile/change_password.html', active_page='profile')

        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "warning")
            return render_template('profile/change_password.html', active_page='profile')

        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "warning")
            return render_template('profile/change_password.html', active_page='profile')

        db['users'].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": generate_password_hash(new_password)}}
        )

        flash("Your password has been changed successfully.", "success")
        return redirect(url_for('profile.view_profile'))

    return render_template('profile/change_password.html', active_page='profile')


@profile_bp.route('/request-verification', methods=['POST'])
@login_required
def request_verification():
    """
    Submits a profile verification request with student/faculty ID.
    """
    db = get_db()
    user_id = session.get('user_id')
    student_id = request.form.get('student_id', '').strip()

    update_doc = {"verification_status": "pending_verification"}
    if student_id:
        update_doc["student_id"] = student_id

    db['users'].update_one({"_id": ObjectId(user_id)}, {"$set": update_doc})

    # Notify admins
    admins = list(db['users'].find({"role": "admin"}))
    for adm in admins:
        db['notifications'].insert_one({
            "user_id": str(adm['_id']),
            "title": "New Profile Verification Request",
            "message": f"User {session.get('full_name')} (@{session.get('username')}) requested student/faculty verification.",
            "category": "admin",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    flash("Verification request submitted to Campus Administration for review.", "success")
    return redirect(url_for('profile.view_profile'))
