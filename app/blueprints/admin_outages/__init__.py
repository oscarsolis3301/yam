from flask import Blueprint

bp = Blueprint('admin_outages', __name__, url_prefix='/api/admin/outages')

# Import routes after blueprint definition to avoid circular imports
from . import routes 