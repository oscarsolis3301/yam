from flask import Blueprint

bp = Blueprint('freshworks_linking', __name__, url_prefix='/freshworks-linking')

from . import routes 