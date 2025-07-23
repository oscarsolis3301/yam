from flask import Blueprint

bp = Blueprint('time', __name__, url_prefix='/time')

from . import routes 