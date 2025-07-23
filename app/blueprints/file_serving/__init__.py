from flask import Blueprint

bp = Blueprint('file_serving', __name__)

from . import routes 