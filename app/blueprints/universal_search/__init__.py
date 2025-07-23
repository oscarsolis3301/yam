from flask import Blueprint

bp = Blueprint('universal_search', __name__)

from . import routes 