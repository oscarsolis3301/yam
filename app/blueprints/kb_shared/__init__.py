from flask import Blueprint

# Blueprint under /kb to host shared article routes
bp = Blueprint('kb_shared', __name__, url_prefix='/kb')

from . import routes  # noqa: E402

__all__ = ['bp'] 