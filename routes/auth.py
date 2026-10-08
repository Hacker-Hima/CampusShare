from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.connection import get_db
from utils.validators import validate_registration_data
from utils.decorators import guest_only

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
@guest_only
def register():
    """
    Handles student and faculty registration.
    Uses normal HTML POST form submission, server-side validation,
    and Werkzeug password hashing before inserting into MongoDB.
    """
    if request.method == 'POST':
        form_data = request.form
        is_valid, error_msg = validate_registration_data(form_data)
        if not is_valid:
            flash(error_msg, "danger")
            return render_template('auth/register.html', form=form_data)

        db = get_db()
        users_col = db['users']

        username = form_data.get('username').strip()
        email = form_data.get('email').strip().lower()

        # Check for existing user in MongoDB
        existing_user = users_col.find_one({
            "$or": [{"username": username}, {"email": email}]
        })

        if existing_user:
            if existing_user.get('username') == username:
                flash("Username is already taken. Please choose another.", "warning")
            else:
                flash("An account with this email address already exists.", "warning")
            return render_template('auth/register.html', form=form_data)

        # Prepare new user document
        new_user = {
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(form_data.get('password')),
            "full_name": form_data.get('full_name').strip(),
            "role": form_data.get('role').strip().lower(),
            "department": form_data.get('department').strip(),
            "phone": form_data.get('phone', '').strip(),
            "year": form_data.get('year', '').strip() if form_data.get('role') == 'student' else None,
            "section": form_data.get('section', '').strip() if form_data.get('role') == 'student' else None,
            "bio": form_data.get('bio', '').strip(),
            "profile_image": "default_avatar.png",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }

        # MongoDB insert operation
        users_col.insert_one(new_user)
        flash("Registration successful! You may now sign in with your credentials.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form={})


@auth_bp.route('/login', methods=['GET', 'POST'])
@guest_only
def login():
    """
    Handles user login using Flask sessions and Werkzeug password verification.
    """
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template('auth/login.html', identifier=identifier)

        db = get_db()
        users_col = db['users']

        # Find user document by either username or email using MongoDB $or operator
        user = users_col.find_one({
            "$or": [
                {"username": identifier},
                {"email": identifier.lower()}
            ]
        })

        if not user or not check_password_hash(user.get('password_hash', ''), password):
            flash("Invalid username/email or password.", "danger")
            return render_template('auth/login.html', identifier=identifier)

        if not user.get('is_active', True):
            flash("Your account has been deactivated by the administrator.", "danger")
            return render_template('auth/login.html', identifier=identifier)

        # Establish Flask Session
        session.clear()
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        session['full_name'] = user.get('full_name', user['username'])
        session['role'] = user['role']
        session['department'] = user.get('department', '')

        flash(f"Welcome back, {session['full_name']}!", "success")

        # Next redirection or role-based dashboard landing
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        if user['role'] == 'admin':
            return redirect('/admin/dashboard')
        elif user['role'] == 'faculty':
            return redirect('/faculty/dashboard')
        return redirect('/student/dashboard')

    return render_template('auth/login.html', identifier='')


@auth_bp.route('/logout')
def logout():
    """
    Clears the Flask user session and redirects to the login screen.
    """
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))
