from flask import Blueprint

bp = Blueprint('profile_management', __name__)

from . import routes 