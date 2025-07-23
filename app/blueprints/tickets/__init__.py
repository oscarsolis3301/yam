from flask import Blueprint

# Blueprint for ticket-related routes (Freshdesk integration, etc.)
# No url_prefix so existing routes like "/create_ticket" keep working unchanged.
bp = Blueprint('tickets', __name__)

# Import the routes to register them on blueprint creation
from . import routes  # noqa: E402

__all__ = [
    'bp',
] 