from flask import Blueprint

bp = Blueprint('unified_search', __name__)

# Import routes to register them with the blueprint
from . import routes  # noqa: E402 (import after blueprint definition is intentional) 