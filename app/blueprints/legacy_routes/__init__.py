from flask import Blueprint

bp = Blueprint('legacy_routes', __name__)

from . import routes 