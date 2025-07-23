from flask import Blueprint

# Blueprint for API endpoints related to user settings (notifications, privacy, etc.)
# This is separate from the UI-oriented *settings* blueprint so that the REST
# routes live under the canonical ``/api/settings`` prefix while the UI pages
# remain under ``/settings``.

bp = Blueprint('settings_api', __name__, url_prefix='/api/settings')

# Import the route definitions so they get registered when the blueprint is
# imported.  The import is placed at the end to avoid circular-import issues.
from . import routes  # noqa: E402 