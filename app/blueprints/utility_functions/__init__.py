from flask import Blueprint

bp = Blueprint('utility_functions', __name__)

from . import routes 