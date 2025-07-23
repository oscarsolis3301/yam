"""
Session Middleware for YAM Application
Ensures proper session initialization and maintenance
"""

import logging
from datetime import datetime, timedelta
from flask import request, session, current_app, g
from flask_login import current_user

logger = logging.getLogger(__name__)

class SessionMiddleware:
    """Middleware to handle session initialization and maintenance"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the session middleware with the Flask app"""
        self.app = app
        
        # Register before_request handler
        app.before_request(self._before_request)
        
        # Register after_request handler
        app.after_request(self._after_request)
        
        logger.info("Session middleware initialized")
    
    def _before_request(self):
        """Handle session initialization before each request"""
        try:
            # Initialize session if not already done
            if '_created' not in session:
                session['_created'] = datetime.utcnow()
                session['last_activity'] = datetime.utcnow().isoformat()
                session.permanent = True
                logger.debug("Session initialized for new user")
            
            # Update last activity for authenticated users
            if current_user.is_authenticated:
                session['last_activity'] = datetime.utcnow().isoformat()
                session['user_id'] = current_user.id
                session['username'] = current_user.username
                
                # Store session info in g for use in request
                g.session_info = {
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'session_created': session.get('_created'),
                    'last_activity': session.get('last_activity')
                }
            
            # Check session expiry
            self._check_session_expiry()
            
        except Exception as e:
            logger.error(f"Error in session middleware before_request: {e}")
    
    def _after_request(self, response):
        """Handle session cleanup after each request"""
        try:
            # Update session activity timestamp
            if current_user.is_authenticated:
                session['last_activity'] = datetime.utcnow().isoformat()
            
            # Add session headers for debugging
            if current_app.debug:
                session_lifetime = current_app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(hours=2))
                session_created = session.get('_created')
                if session_created:
                    if isinstance(session_created, str):
                        session_created = datetime.fromisoformat(session_created)
                    session_expiry = session_created + session_lifetime
                    time_remaining = (session_expiry - datetime.utcnow()).total_seconds()
                    
                    response.headers['X-Session-Expires'] = session_expiry.isoformat()
                    response.headers['X-Session-Remaining'] = str(int(time_remaining))
            
        except Exception as e:
            logger.error(f"Error in session middleware after_request: {e}")
        
        return response
    
    def _check_session_expiry(self):
        """Check if session is about to expire and handle accordingly"""
        try:
            session_lifetime = current_app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(hours=2))
            session_created = session.get('_created')
            
            if session_created:
                if isinstance(session_created, str):
                    session_created = datetime.fromisoformat(session_created)
                
                session_expiry = session_created + session_lifetime
                now = datetime.utcnow()
                time_remaining = (session_expiry - now).total_seconds()
                
                # If session has expired, clear it
                if time_remaining <= 0:
                    logger.warning("Session expired, clearing session data")
                    session.clear()
                    return
                
                # If session is about to expire (within 5 minutes), log warning
                if time_remaining < 300:  # 5 minutes
                    logger.warning(f"Session expiring soon: {int(time_remaining)} seconds remaining")
                
        except Exception as e:
            logger.error(f"Error checking session expiry: {e}")
    
    def extend_session(self, user_id=None):
        """Manually extend the current session"""
        try:
            session['_created'] = datetime.utcnow()
            session['last_activity'] = datetime.utcnow().isoformat()
            session.permanent = True
            
            if user_id:
                session['user_id'] = user_id
            
            logger.info(f"Session extended for user {user_id or 'unknown'}")
            return True
            
        except Exception as e:
            logger.error(f"Error extending session: {e}")
            return False
    
    def get_session_info(self):
        """Get current session information"""
        try:
            session_lifetime = current_app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(hours=2))
            session_created = session.get('_created')
            
            if session_created:
                if isinstance(session_created, str):
                    session_created = datetime.fromisoformat(session_created)
                
                session_expiry = session_created + session_lifetime
                now = datetime.utcnow()
                time_remaining = (session_expiry - now).total_seconds()
                
                return {
                    'session_created': session_created.isoformat(),
                    'session_expiry': session_expiry.isoformat(),
                    'time_remaining_seconds': max(0, int(time_remaining)),
                    'session_lifetime_seconds': int(session_lifetime.total_seconds()),
                    'last_activity': session.get('last_activity'),
                    'user_id': session.get('user_id'),
                    'username': session.get('username')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None

# Global instance
session_middleware = SessionMiddleware()

def init_session_middleware(app):
    """Initialize session middleware with the Flask app"""
    session_middleware.init_app(app)
    return session_middleware 