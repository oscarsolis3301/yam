from flask import Blueprint

bp = Blueprint('dameware', __name__)

from . import routes 