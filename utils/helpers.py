import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

def allowed_file(filename):
    """
    Checks if a file extension is in the allowed whitelist.
    """
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file_storage):
    """
    Saves an uploaded file safely to the uploads folder with a unique prefix.
    Returns tuple: (saved_filename, original_filename) or (None, None).
    """
    if not file_storage or file_storage.filename == '':
        return None, None

    original_filename = secure_filename(file_storage.filename)
    if not allowed_file(original_filename):
        return None, None

    # Generate unique filename to avoid collision
    unique_id = uuid.uuid4().hex[:10]
    saved_filename = f"{unique_id}_{original_filename}"
    file_path = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
    
    file_storage.save(file_path)
    return saved_filename, original_filename
