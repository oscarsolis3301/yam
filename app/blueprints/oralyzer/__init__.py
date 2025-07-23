from flask import Blueprint

bp = Blueprint('oralyzer', __name__, url_prefix='/oralyzer')

from . import routes  # noqa: E402

__all__ = ['bp'] 