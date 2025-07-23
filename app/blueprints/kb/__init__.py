from flask import Blueprint

# Create blueprint first
bp = Blueprint('kb', __name__, url_prefix='/kb')

# Import routes after creating blueprint
from . import routes 