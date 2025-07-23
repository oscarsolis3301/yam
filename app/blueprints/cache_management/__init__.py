from flask import Blueprint

bp = Blueprint('cache_management', __name__, url_prefix='/api/cache')

from . import routes 