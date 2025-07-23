from flask import Blueprint

# Blueprint for Patterson technician dispatch system
bp = Blueprint('patterson', __name__, url_prefix='/patterson')

# Import the routes to register them on blueprint creation
from . import routes  # noqa: E402

__all__ = [
    'bp',
] 