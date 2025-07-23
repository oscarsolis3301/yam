"""
Session Management Utilities

Basic session management initialization for fast startup mode
"""

import logging
import os
from datetime import timedelta
from flask import current_app, session

logger = logging.getLogger(__name__)

def init_session_management():
    """Initialize basic session management for fast startup"""
    try:
        app = current_app
        
        # Configure session settings for performance
        app.config.update({
            'PERMANENT_SESSION_LIFETIME': timedelta(days=1),
            'SESSION_COOKIE_HTTPONLY': True, 
            'SESSION_COOKIE_SECURE': False,  # Set to True in production with HTTPS
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'SESSION_REFRESH_EACH_REQUEST': True
        })
        
        # Set secret key if not already set
        if not app.config.get('SECRET_KEY'):
            # Generate a temporary secret key for development
            app.config['SECRET_KEY'] = os.urandom(24)
            logger.warning("Using temporary secret key - set SECRET_KEY in production")
        
        logger.info("Session management initialized")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize session management: {e}")
        return False 