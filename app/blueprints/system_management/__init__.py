from flask import Blueprint

bp = Blueprint('system_management', __name__)

from . import routes 