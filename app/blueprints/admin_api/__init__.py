from flask import Blueprint

# Blueprint dedicated to **REST** endpoints under the canonical `/api/admin/*` prefix.
# This keeps the API surface consistent regardless of where the main application
# is mounted and avoids clashes with the existing *admin* blueprint that serves
# HTML pages under `/admin/*`.
bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

from . import routes


def init_admin_api_blueprint(app):  # pragma: no cover
    """Helper to register the blueprint from the application factory.

    Mirrors the pattern used by the other blueprints so callers can simply do::

        from app.blueprints.admin_api import init_admin_api_blueprint
        init_admin_api_blueprint(app)
    """
    app.register_blueprint(bp) 