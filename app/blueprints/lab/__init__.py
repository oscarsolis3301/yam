from flask import Blueprint

bp = Blueprint('lab', __name__, url_prefix='/lab')

from . import routes  # noqa: E402 (import after blueprint definition is intentional)

__all__ = ['bp']