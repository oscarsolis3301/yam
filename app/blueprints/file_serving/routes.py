import os
import logging
from pathlib import Path
from flask import send_file, current_app, Response
from . import bp

logger = logging.getLogger(__name__)

@bp.route('/static/uploads/profile_pictures/<path:filename>')
def serve_profile_picture_or_default(filename: str):
    """Serve a profile picture or fall back to a default image if missing.

    Some user records still point to legacy image names that are no longer on
    disk (e.g. ``1_atom.png``). Trying to access them produces repeated 404
    errors.  This helper first checks whether the requested file actually
    exists; if not, it returns a generic placeholder picture so the browser can
    render something and we avoid noisy log entries.
    """
    # Resolve the *absolute* uploads directory (works even when the current
    # working directory is ``app/`` rather than the project root).  We build
    # the path relative to ``app.root_path`` which always points at the
    # *app* package directory, and then step one level up to the repository
    # root before appending the configured uploads folder.

    uploads_dir = Path(current_app.config['UPLOAD_FOLDER'])
    if not uploads_dir.is_absolute():
        uploads_dir = Path(current_app.root_path).parent / uploads_dir

    # For profile pictures, we need to look in the profile_pictures subdirectory
    profile_pictures_dir = uploads_dir / 'profile_pictures'
    
    # Guarantee the directory exists so we never raise an *ENOENT* at runtime
    profile_pictures_dir.mkdir(parents=True, exist_ok=True)

    requested_path = profile_pictures_dir / filename

    if requested_path.exists():
        return send_file(str(requested_path))

    # Fallback – first try the generic default avatar placed inside the profile_pictures directory
    default_avatar = profile_pictures_dir / 'default.png'

    # If that file is missing as well, fall back to the legacy placeholder that ships
    # with the repository so we *always* return a valid image instead of a 500 error.
    if not default_avatar.exists():
        default_avatar = Path(current_app.static_folder) / 'images' / 'PFP' / 'boy.png'

    return send_file(str(default_avatar))

@bp.route('/static/uploads/files/<path:filename>')
def serve_uploaded_file_or_placeholder(filename: str):
    """Serve uploaded files (e.g. CSV used by the front-end). If the requested
    file doesn't exist on disk we return an empty placeholder so the front-end
    logic can continue without raising *404* errors.
    """
    base_dir = os.path.join(current_app.static_folder, 'uploads', 'files')
    os.makedirs(base_dir, exist_ok=True)
    full_path = os.path.join(base_dir, filename)

    if os.path.exists(full_path):
        return send_file(full_path)

    placeholder_csv = 'department,name,start,end,workDays,notes\n'
    return Response(placeholder_csv, mimetype='text/csv') 