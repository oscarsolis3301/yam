"""
User System Utilities

Basic user system initialization for fast startup mode
"""

import logging
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

def init_user_system_basic():
    """Initialize basic user system components for fast startup"""
    try:
        # Import within function to avoid circular imports
        from flask import current_app
        
        # Ensure we're in app context
        if not current_app:
            logger.warning("No Flask app context available")
            return False
            
        # Ensure User model is available
        try:
            from app.models import User
            logger.info("User model imported successfully")
        except ImportError as e:
            logger.warning(f"User model not available: {e}")
            return False
        
        # Basic check for database availability
        try:
            from extensions import db
            # Simple check - don't actually query yet
            if db:
                logger.info("Database connection available")
            else:
                logger.warning("Database not initialized")
        except Exception as e:
            logger.warning(f"Database check failed: {e}")
        
        logger.info("Basic user system initialized")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize basic user system: {e}")
        return False 