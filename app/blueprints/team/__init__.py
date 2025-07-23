from flask import Blueprint

bp = Blueprint('team', __name__, url_prefix='/team')

# Import routes after blueprint definition to avoid circular imports
from . import routes  # noqa: E402

__all__ = ['bp'] 