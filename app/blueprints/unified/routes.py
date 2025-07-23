from flask import jsonify
from flask import current_app
from flask import request
from flask import url_for
from flask import redirect
from flask import abort
from flask import session
from flask import g
from flask import flash
from flask import render_template
from flask import send_file
from flask_login import login_required

# Import the blueprint defined in __init__.py
from . import bp

# Import the root-level extensions.py
from extensions import db


# ---------------------------------------------------------------------------
# UI Route – Unified Search/Home
# ---------------------------------------------------------------------------

@bp.route('/', methods=['GET'])
@login_required
def unified():
    """Render the main Unified Search page.

    This endpoint was previously implemented directly on the Flask *app* inside
    `app/spark.py`.  It now lives in the dedicated *unified* blueprint while
    preserving the original URL (`/unified`).
    """
    return render_template('unified.html', active_page='unified')