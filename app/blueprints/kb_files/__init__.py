from flask import Blueprint

# Blueprint registered under '/static' to provide customised file-serving routes
bp = Blueprint('kb_files', __name__, url_prefix='/static')

from . import routes  # noqa: E402

__all__ = ['bp'] 