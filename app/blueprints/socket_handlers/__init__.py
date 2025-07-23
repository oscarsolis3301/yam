from flask import Blueprint

bp = Blueprint('socket_handlers', __name__)

from . import routes 