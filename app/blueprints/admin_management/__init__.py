from flask import Blueprint

bp = Blueprint('admin_management', __name__, url_prefix='/api/admin')

from . import routes 