from flask import Blueprint

# Create blueprint first
bp = Blueprint('settings', __name__, url_prefix='/settings')

# Import routes after creating blueprint to avoid circular imports
from . import routes 