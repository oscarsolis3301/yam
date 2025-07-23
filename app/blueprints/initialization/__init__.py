from flask import Blueprint

bp = Blueprint('initialization', __name__)

from . import routes 