from flask import Blueprint

# Create blueprint first
bp = Blueprint('profile', __name__, url_prefix='/profile')

# Import routes after creating blueprint to avoid circular imports
from . import routes 