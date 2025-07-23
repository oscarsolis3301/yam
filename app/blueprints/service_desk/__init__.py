from flask import Blueprint

# Blueprint for service desk dashboard with cyberpunk theme
bp = Blueprint('service_desk', __name__, url_prefix='/service-desk')

# Import the routes to register them on blueprint creation
from . import routes  # noqa: E402

__all__ = [
    'bp',
] 