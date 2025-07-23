from flask import Blueprint

bp = Blueprint('unified', __name__, url_prefix='/unified')

# Import routes to ensure they are registered when the blueprint is initialised
from . import routes  # noqa: E402  (import after blueprint definition is intentional)

def init_unified_blueprint(app):
    """Register the unified blueprint with the main Flask app."""
    app.register_blueprint(bp)