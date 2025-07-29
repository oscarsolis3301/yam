from flask import Blueprint
import logging
from app.utils.models import initialize_models
from app.extensions import db

logger = logging.getLogger('spark')

bp = Blueprint('ai', __name__, url_prefix='/ai')

def init_ai_blueprint(app):
    """Initialize the AI blueprint with the Flask app"""
    # Initialize models when blueprint is created
    model_status = initialize_models()
    if not model_status:
        logger.error("Failed to initialize AI models in blueprint. Some features may not work properly.")
    else:
        logger.info("AI models initialized successfully in blueprint")
    
    # Ensure database tables exist
    try:
        with app.app_context():
            # Use the existing db instance
            db.create_all()
            logger.info("AI database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating AI database tables: {str(e)}")

from . import routes 