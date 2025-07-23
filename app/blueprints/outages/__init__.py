from flask import Blueprint

# Create blueprint first
bp = Blueprint('outages', __name__, url_prefix='/outages')

# Import routes after creating blueprint to avoid circular imports
from . import routes 