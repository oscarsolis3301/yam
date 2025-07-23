from flask import Blueprint

# Blueprint to expose KB-related API endpoints under /api
bp = Blueprint('kb_api', __name__, url_prefix='/api')

from . import routes  # noqa: E402

__all__ = ['bp'] 