from flask import Blueprint

# Blueprint for modal API endpoints
bp = Blueprint('modal_api', __name__, url_prefix='/api/modals')

from . import routes 