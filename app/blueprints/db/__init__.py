from flask import Blueprint

bp = Blueprint('db', __name__)

from . import routes 