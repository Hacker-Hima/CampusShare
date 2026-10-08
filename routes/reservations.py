from datetime import datetime, timezone, date
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required

reservations_bp = Blueprint('reservations', __name__, url_prefix='/reservations')

@reservations_bp.route('', methods=['GET'])
@reservations_bp.route('/my', methods=['GET'])
@login_required
def my_reservations():
    """
    Displays the user's campus facility bookings (seminar halls, labs, projectors).
    """
    db = get_db()
    user_id = session.get('user_id')
    
    reservations_list = list(db['reservations'].find({"user_id": user_id}).sort("date", -1))
    campus_resources = list(db['resources'].find({"resource_type": "campus", "status": "approved"}))

    return render_template(
        'reservations/my_reservations.html',
        active_page='reservations',
        reservations=reservations_list,
        campus_resources=campus_resources
    )

@reservations_bp.route('/schedule', methods=['GET'])
def view_schedule():
    """
    Public / Campus-wide reservation calendar schedule showing upcoming confirmed bookings.
    """
    db = get_db()
    selected_date = request.args.get('date', date.today().isoformat()).strip()
    
    # Query confirmed bookings for selected date
    bookings = list(db['reservations'].find({
        "date": selected_date,
        "status": "confirmed"
    }).sort("start_time", 1))

    campus_resources = list(db['resources'].find({"resource_type": "campus", "status": "approved"}))

    return render_template(
        'reservations/schedule.html',
        active_page='reservations',
        bookings=bookings,
        selected_date=selected_date,
        campus_resources=campus_resources
    )

@reservations_bp.route('/new/<resource_id>', methods=['GET', 'POST'])
@login_required
def book_resource(resource_id):
    """
    Books an eligible campus facility with server-side time slot conflict detection.
    Demonstrates MongoDB compound comparison operators ($and, $lt, $gt).
    """
    db = get_db()
    try:
        obj_id = ObjectId(resource_id)
    except Exception:
        flash("Invalid facility ID.", "danger")
        return redirect(url_for('resources.list_resources'))

    resource = db['resources'].find_one({"_id": obj_id})
    if not resource:
        flash("Resource not found.", "danger")
        return redirect(url_for('resources.list_resources'))

    # Only campus facilities or eligible kits can be booked
    if resource.get('resource_type') not in ['campus', 'physical']:
        flash("Only campus facilities, rooms, or equipment can be reserved.", "warning")
        return redirect(url_for('resources.view_resource', resource_id=resource_id))

    if request.method == 'POST':
        booking_date = request.form.get('date', '').strip()
        start_time = request.form.get('start_time', '').strip()
        end_time = request.form.get('end_time', '').strip()
        purpose = request.form.get('purpose', '').strip()

        # 1. Basic time boundary validation
        if not booking_date or not start_time or not end_time or not purpose:
            flash("All fields (Date, Start Time, End Time, Purpose) are required.", "danger")
            return render_template('reservations/book.html', resource=resource)

        if start_time >= end_time:
            flash("Reservation End Time must be later than Start Time.", "danger")
            return render_template('reservations/book.html', resource=resource)

        # 2. Server-Side Conflict Detection Query
        # Two intervals [start_time, end_time) and [ex_start, ex_end) overlap iff:
        # start_time < ex_end AND end_time > ex_start
        conflict = db['reservations'].find_one({
            "resource_id": str(resource['_id']),
            "date": booking_date,
            "status": "confirmed",
            "$and": [
                {"start_time": {"$lt": end_time}},
                {"end_time": {"$gt": start_time}}
            ]
        })

        if conflict:
            flash(
                f"Booking Conflict! This facility is already booked on {booking_date} "
                f"from {conflict.get('start_time')} to {conflict.get('end_time')} "
                f"for '{conflict.get('purpose')}'. Please choose another slot.",
                "danger"
            )
            return render_template('reservations/book.html', resource=resource)

        # 3. Create confirmed reservation document
        new_reservation = {
            "resource_id": str(resource['_id']),
            "resource_title": resource.get('title'),
            "resource_location": resource.get('location', 'Campus Facility'),
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "user_name": session.get('full_name') or session.get('username'),
            "user_department": session.get('department', 'General'),
            "date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
            "purpose": purpose,
            "status": "confirmed",  # confirmed, cancelled, completed
            "created_at": datetime.now(timezone.utc)
        }

        db['reservations'].insert_one(new_reservation)

        # Dispatch Notification to booking user
        db['notifications'].insert_one({
            "user_id": session.get('user_id'),
            "title": "Facility Reservation Confirmed",
            "message": f"Your reservation for '{resource.get('title')}' on {booking_date} ({start_time} - {end_time}) has been confirmed.",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })

        # Log Activity
        db['activities'].insert_one({
            "user_id": session.get('user_id'),
            "username": session.get('username'),
            "action": "FACILITY_RESERVED",
            "description": f"Reserved '{resource.get('title')}' on {booking_date} ({start_time}-{end_time})",
            "created_at": datetime.now(timezone.utc)
        })

        flash(f"Facility '{resource.get('title')}' successfully reserved for {booking_date} ({start_time} - {end_time})!", "success")
        return redirect(url_for('reservations.my_reservations'))

    # GET request: Show existing bookings on today's date for reference
    today_str = date.today().isoformat()
    existing_slots = list(db['reservations'].find({
        "resource_id": str(resource['_id']),
        "date": today_str,
        "status": "confirmed"
    }).sort("start_time", 1))

    return render_template('reservations/book.html', resource=resource, today_str=today_str, existing_slots=existing_slots)

@reservations_bp.route('/cancel/<reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    """
    Cancels an active facility booking, releasing the time slot for other users.
    """
    db = get_db()
    try:
        obj_id = ObjectId(reservation_id)
    except Exception:
        flash("Invalid reservation ID.", "danger")
        return redirect(url_for('reservations.my_reservations'))

    res_doc = db['reservations'].find_one({"_id": obj_id})
    if not res_doc:
        flash("Reservation record not found.", "warning")
        return redirect(url_for('reservations.my_reservations'))

    if res_doc.get('user_id') != session.get('user_id') and session.get('role') != 'admin':
        flash("Unauthorized: You can only cancel your own facility reservations.", "danger")
        return redirect(url_for('reservations.my_reservations'))

    db['reservations'].update_one(
        {"_id": obj_id},
        {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
    )

    flash(f"Reservation for '{res_doc.get('resource_title')}' cancelled. Time slot is now open.", "info")
    return redirect(url_for('reservations.my_reservations'))
