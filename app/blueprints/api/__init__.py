from flask import Blueprint

bp = Blueprint('api', __name__)

# Import routes so that the decorators register with the blueprint
from . import routes  # noqa: E402 