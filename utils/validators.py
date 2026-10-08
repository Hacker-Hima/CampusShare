import re

def validate_registration_data(form_data):
    """
    Validates user registration input.
    Returns tuple (is_valid: bool, error_message: str or None).
    """
    username = form_data.get('username', '').strip()
    email = form_data.get('email', '').strip().lower()
    full_name = form_data.get('full_name', '').strip()
    role = form_data.get('role', '').strip().lower()
    password = form_data.get('password', '')
    confirm_password = form_data.get('confirm_password', '')
    department = form_data.get('department', '').strip()

    if not username or len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters."

    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return False, "Username may only contain letters, numbers, underscores, and hyphens."

    if not full_name or len(full_name) < 2:
        return False, "Please provide your full name."

    # Email basic RFC-compliant regex
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not email or not re.match(email_regex, email):
        return False, "Please provide a valid college or institutional email address."

    if role not in ['student', 'faculty']:
        return False, "Role must be either 'student' or 'faculty'."

    if not department:
        return False, "Department is required."

    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."

    if password != confirm_password:
        return False, "Passwords do not match."

    return True, None
