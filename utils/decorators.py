from functools import wraps
from flask import session, redirect, url_for, flash, abort, request

def login_required(f):
    """
    Decorator to ensure user is logged in before accessing a route.
    Stores target URL for post-login redirect if applicable.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def guest_only(f):
    """
    Decorator to prevent authenticated users from accessing login/registration pages.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            role = session.get('role', 'student')
            if role == 'admin':
                return redirect(url_for('admin.dashboard') if 'admin' in request.blueprint else '/admin/dashboard')
            elif role == 'faculty':
                return redirect(url_for('faculty.dashboard') if 'faculty' in request.blueprint else '/faculty/dashboard')
            return redirect(url_for('student.dashboard') if 'student' in request.blueprint else '/student/dashboard')
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator restricting route access to specified roles.
    Example: @role_required('admin') or @role_required('faculty', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Authentication required.", "warning")
                return redirect(url_for('auth.login', next=request.path))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash(f"Access restricted. Role '{user_role}' does not have sufficient permission.", "danger")
                # Redirect to appropriate home based on current role
                if user_role == 'admin':
                    return redirect('/admin/dashboard')
                elif user_role == 'faculty':
                    return redirect('/faculty/dashboard')
                return redirect('/student/dashboard')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Convenience decorator specifically for administrator-only routes."""
    return role_required('admin')(f)

def faculty_or_admin_required(f):
    """Convenience decorator for routes accessible to faculty and admin."""
    return role_required('faculty', 'admin')(f)
