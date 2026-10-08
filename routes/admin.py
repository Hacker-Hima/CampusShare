import os
from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, current_app
from database.connection import get_db
from utils.decorators import login_required, admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    Administrator Dashboard with server-rendered system analytics,
    user breakdown, borrowing metrics, and MongoDB aggregation pipelines.
    """
    db = get_db()

    total_users = db['users'].count_documents({})
    total_students = db['users'].count_documents({"role": "student"})
    total_faculty = db['users'].count_documents({"role": "faculty"})
    total_resources = db['resources'].count_documents({})
    pending_approvals = db['resources'].count_documents({"status": "pending"})
    pending_requests = db['resource_requests'].count_documents({"status": "pending"})
    active_borrowings = db['borrowings'].count_documents({"status": {"$in": ["approved", "borrowed"]}})
    total_reservations = db['reservations'].count_documents({})
    total_reports = db['reports'].count_documents({"status": "pending"})
    total_marketplace = db['marketplace'].count_documents({})
    total_disputes = db['disputes'].count_documents({"status": "OPEN"})
    total_lostfound = db['lost_found'].count_documents({"status": {"$in": ["lost", "found"]}})

    dept_pipeline = [
        {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    resources_by_dept = list(db['resources'].aggregate(dept_pipeline))

    type_pipeline = [
        {"$group": {"_id": "$resource_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    resources_by_type = list(db['resources'].aggregate(type_pipeline))

    popular_resources = list(db['resources'].find({}).sort("downloads", -1).limit(5))
    recent_activities = list(db['activities'].find({}).sort("created_at", -1).limit(8))

    return render_template(
        'admin/dashboard.html',
        active_page='dashboard',
        stats={
            'total_users': total_users,
            'total_students': total_students,
            'total_faculty': total_faculty,
            'total_resources': total_resources,
            'pending_approvals': pending_approvals,
            'pending_requests': pending_requests,
            'active_borrowings': active_borrowings,
            'total_reservations': total_reservations,
            'total_reports': total_reports,
            'total_marketplace': total_marketplace,
            'total_disputes': total_disputes,
            'total_lostfound': total_lostfound
        },
        resources_by_dept=resources_by_dept,
        resources_by_type=resources_by_type,
        popular_resources=popular_resources,
        recent_activities=recent_activities
    )

# ==============================================================================
# USER MANAGEMENT & ACCOUNT STATUS
# ==============================================================================

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    db = get_db()
    users = list(db['users'].find({}).sort("created_at", -1))
    return render_template('admin/users.html', active_page='users', users=users)

@admin_bp.route('/users/toggle-status/<user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """
    Activates or deactivates a user account. Deactivated accounts cannot sign in.
    """
    db = get_db()
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        flash("Invalid user ID.", "danger")
        return redirect(url_for('admin.manage_users'))

    user = db['users'].find_one({"_id": obj_id})
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for('admin.manage_users'))

    if user.get('username') == 'admin':
        flash("Root administrator account cannot be deactivated.", "danger")
        return redirect(url_for('admin.manage_users'))

    new_status = not user.get('is_active', True)
    db['users'].update_one({"_id": obj_id}, {"$set": {"is_active": new_status}})

    status_str = "activated" if new_status else "suspended"
    flash(f"Account for @{user['username']} has been {status_str}.", "info")
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/change-role/<user_id>', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """
    Changes a user's role (student, faculty, admin).
    """
    db = get_db()
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        flash("Invalid user ID.", "danger")
        return redirect(url_for('admin.manage_users'))

    new_role = request.form.get('role', '').strip().lower()
    if new_role not in ['student', 'faculty', 'admin']:
        flash("Invalid role assignment.", "danger")
        return redirect(url_for('admin.manage_users'))

    db['users'].update_one({"_id": obj_id}, {"$set": {"role": new_role}})
    flash("User role updated successfully.", "success")
    return redirect(url_for('admin.manage_users'))

# ==============================================================================
# RESOURCE MODERATION & APPROVALS
# ==============================================================================

@admin_bp.route('/resources')
@login_required
@admin_required
def manage_resources():
    db = get_db()
    resources = list(db['resources'].find({}).sort("created_at", -1))
    return render_template('admin/resources.html', active_page='resources', resources=resources)

@admin_bp.route('/resources/toggle-status/<resource_id>', methods=['POST'])
@login_required
@admin_required
def toggle_resource_status(resource_id):
    """
    Approves or rejects an uploaded resource document.
    """
    db = get_db()
    try:
        obj_id = ObjectId(resource_id)
    except Exception:
        flash("Invalid resource ID.", "danger")
        return redirect(url_for('admin.manage_resources'))

    target_status = request.form.get('status', 'approved').strip().lower()
    if target_status not in ['approved', 'rejected', 'pending']:
        target_status = 'approved'

    db['resources'].update_one({"_id": obj_id}, {"$set": {"status": target_status}})
    flash(f"Resource status updated to '{target_status}'.", "success")
    return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resources/delete/<resource_id>', methods=['POST'])
@login_required
@admin_required
def delete_resource_admin(resource_id):
    """
    Administrator force-deletion of inappropriate or copyright-violating resources.
    """
    db = get_db()
    try:
        obj_id = ObjectId(resource_id)
    except Exception:
        flash("Invalid resource ID.", "danger")
        return redirect(url_for('admin.manage_resources'))

    res_doc = db['resources'].find_one({"_id": obj_id})
    if res_doc:
        # Delete disk file
        saved_file = res_doc.get('file_path')
        if saved_file:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_file)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        db['resources'].delete_one({"_id": obj_id})
        flash(f"Resource '{res_doc.get('title')}' permanently purged from catalog.", "info")

    return redirect(url_for('admin.manage_resources'))

# ==============================================================================
# CATEGORY MANAGEMENT
# ==============================================================================

@admin_bp.route('/categories')
@login_required
@admin_required
def manage_categories():
    db = get_db()
    categories = list(db['categories'].find({}))
    return render_template('admin/categories.html', active_page='categories', categories=categories)

@admin_bp.route('/categories/create', methods=['POST'])
@login_required
@admin_required
def create_category():
    name = request.form.get('name', '').strip()
    cat_type = request.form.get('type', 'academic').strip().lower()
    description = request.form.get('description', '').strip()

    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for('admin.manage_categories'))

    db = get_db()
    db['categories'].insert_one({
        "name": name,
        "type": cat_type,
        "description": description
    })
    flash(f"Category '{name}' added successfully.", "success")
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/categories/delete/<category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    db = get_db()
    try:
        obj_id = ObjectId(category_id)
    except Exception:
        flash("Invalid category ID.", "danger")
        return redirect(url_for('admin.manage_categories'))

    db['categories'].delete_one({"_id": obj_id})
    flash("Category deleted.", "info")
    return redirect(url_for('admin.manage_categories'))

# ==============================================================================
# REPORT MODERATION
# ==============================================================================

@admin_bp.route('/reports')
@login_required
@admin_required
def manage_reports():
    db = get_db()
    filter_val = request.args.get('filter', 'all').strip().lower()
    
    query = {}
    if filter_val == 'pending':
        query["status"] = "pending"
    elif filter_val == 'resolved':
        query["status"] = "resolved"

    reports = list(db['reports'].find(query).sort("created_at", -1)) if 'reports' in db.list_collection_names() else []
    return render_template('admin/reports.html', active_page='reports', reports=reports, filter_val=filter_val)

@admin_bp.route('/reports/resolve/<report_id>', methods=['POST'])
@login_required
@admin_required
def resolve_report(report_id):
    """
    Moderation action: dismiss, resolve, or remove offending resource.
    """
    db = get_db()
    try:
        obj_id = ObjectId(report_id)
    except Exception:
        flash("Invalid report ID.", "danger")
        return redirect(url_for('admin.manage_reports'))

    report = db['reports'].find_one({"_id": obj_id})
    if not report:
        flash("Report not found.", "warning")
        return redirect(url_for('admin.manage_reports'))

    action = request.form.get('action', 'resolve').strip().lower()

    if action == 'dismiss':
        db['reports'].update_one({"_id": obj_id}, {"$set": {"status": "dismissed"}})
        flash("Report dismissed as false flag.", "info")

    elif action == 'resolve':
        db['reports'].update_one({"_id": obj_id}, {"$set": {"status": "resolved"}})
        flash("Report marked as resolved.", "success")

    elif action == 'remove_resource':
        res_id_str = report.get('resource_id')
        try:
            res_obj_id = ObjectId(res_id_str)
            res_doc = db['resources'].find_one({"_id": res_obj_id})
            if res_doc:
                # Remove file
                saved_file = res_doc.get('file_path')
                if saved_file:
                    path = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_file)
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                db['resources'].delete_one({"_id": res_obj_id})

                # Notify owner of moderation removal
                if res_doc.get('owner_id'):
                    db['notifications'].insert_one({
                        "user_id": res_doc.get('owner_id'),
                        "title": "Resource Removed By Moderator",
                        "message": f"Your upload '{res_doc.get('title')}' was removed by platform administration due to report flag: {report.get('reason')}.",
                        "is_read": False,
                        "created_at": datetime.now(timezone.utc)
                    })
        except Exception:
            pass

        # Mark all reports for this resource as resolved
        db['reports'].update_many({"resource_id": res_id_str}, {"$set": {"status": "resolved"}})
        flash(f"Reported resource removed and all related reports resolved.", "success")

    return redirect(url_for('admin.manage_reports'))

# ==============================================================================
# SUBVIEWS
# ==============================================================================

@admin_bp.route('/requests')
@login_required
@admin_required
def manage_requests():
    db = get_db()
    requests = list(db['resource_requests'].find({}).sort("created_at", -1))
    return render_template('admin/requests.html', active_page='requests', requests=requests)

@admin_bp.route('/borrowings')
@login_required
@admin_required
def manage_borrowings():
    db = get_db()
    borrowings = list(db['borrowings'].find({}).sort("request_date", -1))
    return render_template('admin/borrowings.html', active_page='borrowings', borrowings=borrowings)

@admin_bp.route('/reservations')
@login_required
@admin_required
def manage_reservations():
    db = get_db()
    reservations = list(db['reservations'].find({}).sort("date", -1))
    return render_template('admin/reservations.html', active_page='reservations', reservations=reservations)

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """
    Dedicated Analytics Dashboard powered by multi-stage MongoDB Aggregation Pipelines.
    Calculates departmental metrics, contributor rankings, rating distributions,
    and campus facility utilization using $group, $sort, $project, and $sum.
    """
    db = get_db()

    total_resources = db['resources'].count_documents({})
    download_agg = list(db['resources'].aggregate([{"$group": {"_id": None, "total": {"$sum": "$downloads"}}}]))
    total_downloads = download_agg[0]['total'] if download_agg else 0
    total_borrowings = db['borrowings'].count_documents({})
    total_reservations = db['reservations'].count_documents({})

    # 1. Department Breakdown Pipeline
    dept_pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$department", "Unassigned"]},
                "count": {"$sum": 1},
                "total_downloads": {"$sum": {"$ifNull": ["$downloads", 0]}},
                "avg_views": {"$avg": {"$ifNull": ["$views", 0]}}
            }
        },
        {"$sort": {"count": -1}}
    ]
    department_analytics = list(db['resources'].aggregate(dept_pipeline))
    max_dept_count = max([d['count'] for d in department_analytics], default=1) or 1

    # 2. Category Breakdown Pipeline
    cat_pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$category", "General"]},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ]
    category_analytics = list(db['resources'].aggregate(cat_pipeline))

    # 3. Top Student & Faculty Contributors
    contributor_pipeline = [
        {
            "$group": {
                "_id": "$owner_id",
                "upload_count": {"$sum": 1},
                "total_downloads": {"$sum": {"$ifNull": ["$downloads", 0]}}
            }
        },
        {"$sort": {"upload_count": -1, "total_downloads": -1}},
        {"$limit": 6}
    ]
    raw_contributors = list(db['resources'].aggregate(contributor_pipeline))
    top_contributors = []
    for c in raw_contributors:
        owner_id = c.get('_id')
        user_info = None
        if owner_id:
            try:
                user_info = db['users'].find_one({"_id": ObjectId(owner_id)})
            except Exception:
                pass
        top_contributors.append({
            "user_id": owner_id,
            "username": user_info.get('username', 'Unknown') if user_info else 'Unknown',
            "full_name": user_info.get('full_name', 'Campus Member') if user_info else 'Campus Member',
            "role": user_info.get('role', 'student') if user_info else 'student',
            "department": user_info.get('department', 'CSE') if user_info else 'CSE',
            "upload_count": c.get('upload_count', 0),
            "total_downloads": c.get('total_downloads', 0)
        })

    # 4. Review Ratings Distribution
    rating_pipeline = [
        {
            "$group": {
                "_id": "$rating",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": -1}}
    ]
    rating_breakdown = list(db['reviews'].aggregate(rating_pipeline))
    rating_dict = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rb in rating_breakdown:
        if rb['_id'] in rating_dict:
            rating_dict[rb['_id']] = rb['count']
    total_reviews = sum(rating_dict.values()) or 1

    # 5. Equipment Borrowing Status Breakdown
    borrow_status_pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ]
    borrow_stats = list(db['borrowings'].aggregate(borrow_status_pipeline))

    # 6. Facility Utilization Pipeline
    facility_pipeline = [
        {
            "$group": {
                "_id": "$resource_title",
                "bookings": {"$sum": 1}
            }
        },
        {"$sort": {"bookings": -1}},
        {"$limit": 5}
    ]
    facility_stats = list(db['reservations'].aggregate(facility_pipeline))

    # 8. Campus Marketplace Analytics
    marketplace_pipeline = [
        {
            "$group": {
                "_id": "$category",
                "count": {"$sum": 1},
                "avg_price": {"$avg": "$price"}
            }
        },
        {"$sort": {"count": -1}}
    ]
    marketplace_stats = list(db['marketplace'].aggregate(marketplace_pipeline))
    completed_sales = db['marketplace'].count_documents({"status": "sold"})
    total_marketplace_items = db['marketplace'].count_documents({})

    # 9. Campus Impact Calculations
    # Resources reused: downloads + returned borrowings + completed sales
    total_reused = total_downloads + db['borrowings'].count_documents({"status": "returned"}) + completed_sales
    # Successful exchanges: returned borrowings + completed marketplace sales + fulfilled requests
    successful_exchanges = db['borrowings'].count_documents({"status": "returned"}) + completed_sales + db['resource_requests'].count_documents({"status": "fulfilled"})
    # Estimated student savings (₹): downloads * ₹150 estimated book savings + completed sales * ₹350
    estimated_savings = (total_downloads * 150) + (completed_sales * 350)
    # Items kept in circulation: active marketplace items + active physical borrowings
    items_in_circulation = db['marketplace'].count_documents({"status": "available"}) + db['borrowings'].count_documents({"status": "borrowed"})

    return render_template(
        'admin/analytics.html',
        active_page='analytics',
        department_analytics=department_analytics,
        max_dept_count=max_dept_count,
        category_analytics=category_analytics,
        top_contributors=top_contributors,
        rating_dict=rating_dict,
        total_reviews=sum(rating_dict.values()),
        borrow_stats=borrow_stats,
        facility_stats=facility_stats,
        total_resources=total_resources,
        total_downloads=total_downloads,
        total_borrowings=total_borrowings,
        total_reservations=total_reservations,
        marketplace_stats=marketplace_stats,
        completed_sales=completed_sales,
        total_marketplace_items=total_marketplace_items,
        impact={
            'reused': total_reused,
            'exchanges': successful_exchanges,
            'savings': estimated_savings,
            'circulation': items_in_circulation
        }
    )

# ==============================================================================
# USER VERIFICATION & PROFILE MODERATION
# ==============================================================================

@admin_bp.route('/users/verify/<user_id>', methods=['POST'])
@login_required
@admin_required
def verify_user(user_id):
    """
    Approves and verifies a student or faculty account, boosting trust score and adding badge.
    """
    db = get_db()
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        flash("Invalid user identifier.", "danger")
        return redirect(url_for('admin.manage_users'))

    db['users'].update_one(
        {"_id": obj_id},
        {"$set": {
            "is_verified": True,
            "verification_status": "verified",
            "verified_at": datetime.now(timezone.utc)
        }}
    )

    # Recalculate trust score
    from utils.trust import calculate_trust_score, calculate_user_badges
    calculate_trust_score(user_id, db)
    calculate_user_badges(user_id, db)

    # Notify user
    db['notifications'].insert_one({
        "user_id": user_id,
        "title": "Account Verified! ✓",
        "message": "Your campus student/faculty credentials have been officially verified by Administration.",
        "category": "admin",
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    })

    flash("User account verified successfully. Trust score and verified status updated.", "success")
    return redirect(url_for('admin.manage_users'))

# ==============================================================================
# MARKETPLACE & LOST-FOUND MODERATION
# ==============================================================================

@admin_bp.route('/marketplace')
@login_required
@admin_required
def manage_marketplace():
    """Admin moderation view for all campus marketplace listings."""
    db = get_db()
    listings = list(db['marketplace'].find({}).sort("created_at", -1))
    return render_template('admin/marketplace.html', active_page='marketplace', listings=listings)

@admin_bp.route('/marketplace/delete/<item_id>', methods=['POST'])
@login_required
@admin_required
def delete_marketplace_item(item_id):
    """Deletes an inappropriate marketplace listing."""
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
        db['marketplace'].delete_one({"_id": obj_id})
        flash("Marketplace listing removed.", "info")
    except Exception as e:
        flash(f"Error removing item: {e}", "danger")
    return redirect(url_for('admin.manage_marketplace'))

@admin_bp.route('/lost-found')
@login_required
@admin_required
def manage_lost_found():
    """Admin moderation for Lost & Found items."""
    db = get_db()
    items = list(db['lost_found'].find({}).sort("created_at", -1))
    return render_template('admin/lost_found.html', active_page='lost_found', items=items)

# ==============================================================================
# DISPUTES RESOLUTION PANEL
# ==============================================================================

@admin_bp.route('/disputes')
@login_required
@admin_required
def manage_disputes():
    """View and resolve transaction disputes."""
    db = get_db()
    disputes = list(db['disputes'].find({}).sort("created_at", -1))
    return render_template('admin/disputes.html', active_page='disputes', disputes=disputes)

@admin_bp.route('/disputes/resolve/<dispute_id>', methods=['POST'])
@login_required
@admin_required
def resolve_dispute(dispute_id):
    """Updates dispute status (RESOLVED or REJECTED) with admin notes."""
    db = get_db()
    try:
        obj_id = ObjectId(dispute_id)
    except Exception:
        flash("Invalid dispute ID.", "danger")
        return redirect(url_for('admin.manage_disputes'))

    status = request.form.get('status', 'RESOLVED').strip()
    admin_notes = request.form.get('admin_resolution', '').strip()

    dispute = db['disputes'].find_one({"_id": obj_id})
    if not dispute:
        flash("Dispute not found.", "warning")
        return redirect(url_for('admin.manage_disputes'))

    db['disputes'].update_one(
        {"_id": obj_id},
        {"$set": {
            "status": status,
            "admin_resolution": admin_notes,
            "resolved_at": datetime.now(timezone.utc)
        }}
    )

    # Notify complainant
    if dispute.get('complainant_id'):
        db['notifications'].insert_one({
            "user_id": dispute.get('complainant_id'),
            "title": f"Dispute Status Update: {status}",
            "message": f"Administration has resolved your dispute: {admin_notes}",
            "category": "admin",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

    flash(f"Dispute marked as {status}.", "success")
    return redirect(url_for('admin.manage_disputes'))

# ==============================================================================
# CAMPUS ANNOUNCEMENTS
# ==============================================================================

@admin_bp.route('/announcements', methods=['GET', 'POST'])
@admin_bp.route('/announcements/create', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_announcements():
    """Allows administrators to broadcast campus notices to all dashboards."""
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        priority = request.form.get('priority', 'medium').strip()

        if title and content:
            db['announcements'].insert_one({
                "title": title,
                "content": content,
                "priority": priority,
                "author_id": session.get('user_id'),
                "author_name": session.get('full_name') or 'Administrator',
                "is_active": True,
                "created_at": datetime.now(timezone.utc)
            })
            flash("Campus announcement published successfully!", "success")
        else:
            flash("Title and message are required for announcements.", "warning")
        return redirect(url_for('admin.manage_announcements'))

    announcements = list(db['announcements'].find({}).sort("created_at", -1))
    return render_template('admin/announcements.html', active_page='announcements', announcements=announcements)

@admin_bp.route('/announcements/toggle/<ann_id>', methods=['POST'])
@login_required
@admin_required
def toggle_announcement(ann_id):
    """Toggles active state of an announcement."""
    db = get_db()
    try:
        obj_id = ObjectId(ann_id)
        ann = db['announcements'].find_one({"_id": obj_id})
        if ann:
            new_state = not ann.get('is_active', True)
            db['announcements'].update_one({"_id": obj_id}, {"$set": {"is_active": new_state}})
            flash(f"Announcement {'activated' if new_state else 'deactivated'}.", "info")
    except Exception as e:
        flash(f"Error toggling announcement: {e}", "danger")
    return redirect(url_for('admin.manage_announcements'))

