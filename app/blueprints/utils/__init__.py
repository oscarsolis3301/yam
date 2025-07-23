from flask import Blueprint

bp = Blueprint('utils', __name__)

from . import db 