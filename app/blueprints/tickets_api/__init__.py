from flask import Blueprint

tickets_api_bp = Blueprint('tickets_api', __name__)

from . import routes