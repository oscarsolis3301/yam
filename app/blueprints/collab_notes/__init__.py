from flask import Blueprint

bp = Blueprint('collab_notes', __name__, url_prefix='/notes', template_folder='templates')

from app.blueprints.collab_notes import routes  # noqa: E402 