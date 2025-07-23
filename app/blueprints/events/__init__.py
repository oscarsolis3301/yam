from flask import Blueprint

# Blueprint for event-related endpoints such as /ad_event
bp = Blueprint('events', __name__)

# Import routes after blueprint definition to avoid circular imports
from . import routes  # noqa: E402

def init_events_blueprint(app):
    """Register the events blueprint with the main Flask app."""
    app.register_blueprint(bp) 