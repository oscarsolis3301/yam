from flask import Blueprint

# Create blueprint first
bp = Blueprint('users', __name__, url_prefix='/users')

# Import routes after creating blueprint to avoid circular imports
from . import routes 