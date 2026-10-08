import os
import re
from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory, current_app, Response
from database.connection import get_db
from utils.decorators import login_required
from utils.helpers import save_uploaded_file, allowed_file

resources_bp = Blueprint('resources', __name__, url_prefix='/resources')

@resources_bp.route('', methods=['GET'])
@resources_bp.route('/', methods=['GET'])
def list_resources():
    """
    Advanced discovery and multi-parameter filtering catalog.
    Processes keyword search and multi-facet filters using MongoDB
    query operators ($regex, $or, $and, $gte) and sorting.
    """
    db = get_db()
    
    # 1. Extract GET query parameters
    q = request.args.get('q', '').strip()
    department = request.args.get('department', '').strip()
    semester = request.args.get('semester', '').strip()
    category = request.args.get('category', '').strip()
    resource_type = request.args.get('type', request.args.get('resource_type', '')).strip().lower()
    availability = request.args.get('availability', '').strip().lower()
    min_rating = request.args.get('min_rating', '').strip()
    sort_by = request.args.get('sort', 'newest').strip().lower()

    # 2. Build MongoDB query conditions
    conditions = [{"status": "approved"}]

    # Keyword Search across Title, Description, Subject, and Embedded Tags array
    if q:
        safe_q = re.escape(q)
        regex_pattern = {"$regex": safe_q, "$options": "i"}
        conditions.append({
            "$or": [
                {"title": regex_pattern},
                {"description": regex_pattern},
                {"subject": regex_pattern},
                {"tags": regex_pattern}
            ]
        })

    # Exact filter conditions
    if department:
        conditions.append({"department": department})

    if semester and semester != 'All':
        conditions.append({"semester": semester})

    if category:
        conditions.append({"category": category})

    if resource_type in ['academic', 'physical', 'campus']:
        conditions.append({"resource_type": resource_type})

    if availability in ['available', 'borrowed', 'reserved', 'unavailable']:
        conditions.append({"availability": availability})

    # Minimum Rating filter using $gte operator
    if min_rating:
        try:
            rating_val = float(min_rating)
            conditions.append({"rating": {"$gte": rating_val}})
        except ValueError:
            pass

    # Combine into top-level $and query for NoSQL demonstration
    mongo_query = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    # 3. Determine Sort Order
    sort_mapping = {
        'newest': ("created_at", -1),
        'downloads': ("downloads", -1),
        'rating': ("rating", -1),
        'views': ("views", -1)
    }
    sort_field, sort_dir = sort_mapping.get(sort_by, ("created_at", -1))

    # Execute MongoDB find query with sorting
    resources = list(db['resources'].find(mongo_query).sort(sort_field, sort_dir))
    categories = list(db['categories'].find({}))

    # Count active filters for badge display
    active_filters_count = sum(bool(x) for x in [
        q, department, semester and semester != 'All', 
        category, resource_type, availability, min_rating
    ])

    return render_template(
        'resources/list.html',
        active_page='resources',
        resources=resources,
        categories=categories,
        current_filters={
            'q': q,
            'department': department,
            'semester': semester,
            'category': category,
            'resource_type': resource_type,
            'availability': availability,
            'min_rating': min_rating,
            'sort': sort_by
        },
        active_filters_count=active_filters_count
    )

@resources_bp.route('/view/<resource_id>')
def view_resource(resource_id):
    """
    Displays full details of a specific resource and increments its view count.
    Demonstrates MongoDB $inc operator.
    """
    db = get_db()
    try:
        obj_id = ObjectId(resource_id)
    except Exception:
        flash("Invalid resource identifier.", "danger")
        return redirect(url_for('resources.list_resources'))

    # Increment views counter atomically
    db['resources'].update_one({"_id": obj_id}, {"$inc": {"views": 1}})
    resource = db['resources'].find_one({"_id": obj_id})

    if not resource:
        flash("Resource not found.", "warning")
        return redirect(url_for('resources.list_resources'))

    reviews = list(db['reviews'].find({"resource_id": str(obj_id)}).sort("created_at", -1)) if 'reviews' in db.list_collection_names() else []

    is_owner_or_admin = (
        session.get('user_id') == resource.get('owner_id') or 
        session.get('role') == 'admin'
    )

    return render_template(
        'resources/view.html',
        active_page='resources',
        resource=resource,
        reviews=reviews,
        is_owner_or_admin=is_owner_or_admin
    )

@resources_bp.route('/download/<resource_id>')
def download_resource(resource_id):
    """
    Handles file download, increments downloads counter via $inc,
    and safely streams the file.
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

    # Atomic increment of download count
    db['resources'].update_one({"_id": obj_id}, {"$inc": {"downloads": 1}})

    saved_file = resource.get('file_path')
    original_name = resource.get('file_name', 'resource_material.pdf')
    upload_folder = current_app.config['UPLOAD_FOLDER']

    if saved_file and os.path.exists(os.path.join(upload_folder, saved_file)):
        return send_from_directory(
            upload_folder,
            saved_file,
            as_attachment=True,
            download_name=original_name
        )

    # Viva Demonstration Fallback: generate dynamic academic notes file
    fallback_content = f"""CAMPUSSHARE ACADEMIC RESOURCE REPOSITORY
==================================================
Title: {resource.get('title')}
Subject: {resource.get('subject')}
Department: {resource.get('department')}
Semester: {resource.get('semester')}
Contributor: {resource.get('owner_name', 'Faculty/Student')}
Category: {resource.get('category')}
Tags: {', '.join(resource.get('tags', []))}
==================================================
Summary & Overview:
{resource.get('description')}
==================================================
Verified by CAMPUSSHARE Academic Moderation Board.
"""
    return Response(
        fallback_content,
        mimetype="text/plain",
        headers={"Content-disposition": f"attachment; filename={resource.get('title', 'notes')[:20].replace(' ', '_')}.txt"}
    )

@resources_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_resource():
    """
    Handles resource creation and file uploading.
    Supports Academic notes, Physical lab kits, and Campus facilities.
    Demonstrates embedded array documents in MongoDB for tags.
    """
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        resource_type = request.form.get('resource_type', 'academic').strip().lower()
        subject = request.form.get('subject', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '1').strip()
        tags_raw = request.form.get('tags', '').strip()
        location = request.form.get('location', '').strip()

        if not title or not category or not department:
            flash("Title, Category, and Department are required fields.", "danger")
            categories = list(db['categories'].find({}))
            return render_template('resources/upload.html', categories=categories, form=request.form)

        tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []

        saved_filename = None
        original_filename = None
        if 'resource_file' in request.files:
            file = request.files['resource_file']
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    flash("File extension not permitted. Allowed: PDF, DOCX, PPTX, TXT, ZIP, Images.", "danger")
                    categories = list(db['categories'].find({}))
                    return render_template('resources/upload.html', categories=categories, form=request.form)
                saved_filename, original_filename = save_uploaded_file(file)

        new_resource = {
            "title": title,
            "description": description,
            "category": category,
            "resource_type": resource_type,
            "subject": subject or "General",
            "department": department,
            "semester": semester,
            "tags": tags,
            "owner_id": session.get('user_id'),
            "owner_name": session.get('full_name') or session.get('username'),
            "owner_role": session.get('role'),
            "availability": "available",
            "file_path": saved_filename,
            "file_name": original_filename or (f"{title[:15]}.pdf" if resource_type == 'academic' else None),
            "location": location if resource_type in ['physical', 'campus'] else None,
            "downloads": 0,
            "views": 0,
            "rating": 5.0,
            "review_count": 0,
            "status": "approved",
            "created_at": datetime.now(timezone.utc)
        }

        inserted_id = db['resources'].insert_one(new_resource).inserted_id

        db['activities'].insert_one({
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "action": "UPLOADED_RESOURCE",
            "description": f"Uploaded '{title}' in {category}",
            "created_at": datetime.now(timezone.utc)
        })

        flash(f"Resource '{title}' published successfully to the campus catalog!", "success")
        return redirect(url_for('resources.view_resource', resource_id=str(inserted_id)))

    categories = list(db['categories'].find({}))
    return render_template('resources/upload.html', active_page='my_uploads', categories=categories, form={})

@resources_bp.route('/edit/<resource_id>', methods=['GET', 'POST'])
@login_required
def edit_resource(resource_id):
    """
    Edits an existing resource document. Only authorized for owner or administrator.
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

    if session.get('user_id') != resource.get('owner_id') and session.get('role') != 'admin':
        flash("Unauthorized: You can only edit your own uploads.", "danger")
        return redirect(url_for('resources.view_resource', resource_id=resource_id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        subject = request.form.get('subject', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '1').strip()
        tags_raw = request.form.get('tags', '').strip()
        location = request.form.get('location', '').strip()
        availability = request.form.get('availability', 'available').strip()

        tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []

        update_fields = {
            "title": title,
            "description": description,
            "category": category,
            "subject": subject,
            "department": department,
            "semester": semester,
            "tags": tags,
            "availability": availability
        }
        if location:
            update_fields["location"] = location

        if 'resource_file' in request.files:
            file = request.files['resource_file']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    saved_filename, original_filename = save_uploaded_file(file)
                    update_fields["file_path"] = saved_filename
                    update_fields["file_name"] = original_filename

        db['resources'].update_one({"_id": obj_id}, {"$set": update_fields})
        flash(f"Resource '{title}' updated successfully.", "success")
        return redirect(url_for('resources.view_resource', resource_id=resource_id))

    categories = list(db['categories'].find({}))
    return render_template('resources/edit.html', resource=resource, categories=categories)

@resources_bp.route('/delete/<resource_id>', methods=['POST'])
@login_required
def delete_resource(resource_id):
    """
    Deletes a resource document from MongoDB and deletes the attached local file.
    Only authorized for owner or admin.
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

    if session.get('user_id') != resource.get('owner_id') and session.get('role') != 'admin':
        flash("Unauthorized: You can only delete resources uploaded by yourself.", "danger")
        return redirect(url_for('resources.view_resource', resource_id=resource_id))

    saved_file = resource.get('file_path')
    if saved_file:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[File Delete Warning] Could not remove file {file_path}: {e}")

    db['resources'].delete_one({"_id": obj_id})
    flash(f"Resource '{resource.get('title')}' deleted successfully.", "info")

    return redirect(url_for('resources.my_uploads'))

@resources_bp.route('/my-uploads')
@login_required
def my_uploads():
    """
    Lists all resources uploaded by the logged-in student or faculty user.
    """
    db = get_db()
    user_id = session.get('user_id')
    uploads = list(db['resources'].find({"owner_id": user_id}).sort("created_at", -1))

    return render_template('resources/my_uploads.html', active_page='my_uploads', uploads=uploads)
