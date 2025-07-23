from flask import Blueprint

# Blueprint without a url_prefix so existing routes stay exactly the same
bp = Blueprint('agent', __name__)

# Import routes to register them with the blueprint
from . import routes  # noqa: E402 