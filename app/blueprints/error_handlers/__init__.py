from flask import Blueprint

bp = Blueprint('error_handlers', __name__)

from . import routes 