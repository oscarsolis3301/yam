from flask import Blueprint

bp = Blueprint('workstations', __name__, url_prefix='/workstations')

from . import routes 