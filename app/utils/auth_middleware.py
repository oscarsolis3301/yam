"""
Authentication Middleware for YAM Application
Handles authentication redirects and session management
"""

import logging
from functools import wraps
from datetime import datetime, timedelta
from flask import request, redirect, url_for, jsonify, session, current_app
from flask_login import current_user, login_required

logger = logging.getLogger(__name__)

# Routes that don't require authentication
PUBLIC_ROUTES = {
    '/login',
    '/windows-login',
    '/unauthorized',
    '/auth-check',
    '/static/',
    '/favicon.ico',
    '/robots.txt',
    '/health',
    '/api/health',
    '/api/socketio-status',
    '/socket.io/',
    '/auto-login',
    '/api/session/time-remaining',
    '/api/session/extend'
}

# API routes that should return JSON instead of redirects
API_ROUTES = {
    '/api/',
    '/socket.io/',
    '/notes/api/',
    '/unified_search',
    '/tracking',
    '/collab-notes/api/',
    '/universal-search'
}

def is_public_route(path):
    """Check if a route is public (doesn't require authentication)."""
    for public_route in PUBLIC_ROUTES:
        if path.startswith(public_route):
            return True
    return False

def is_api_route(path):
    """Check if a route is an API route."""
    for api_route in API_ROUTES:
        if path.startswith(api_route):
            return True
    return False

def handle_unauthorized_access():
    """Centralized handler for unauthorized access."""
    path = request.path
    
    # For API routes, return JSON response
    if is_api_route(path):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'redirect': url_for('auth.login'),
            'path': path
        }), 401
    
    # For web routes, redirect to login with next parameter
    next_url = request.url if request.url != request.url_root else None
    if next_url and next_url != url_for('auth.login', _external=True):
        return redirect(url_for('auth.login', next=next_url))
    else:
        return redirect(url_for('auth.login'))

def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not current_user.is_authenticated:
            logger.warning(f"Unauthorized access attempt to {request.path} from {request.remote_addr}")
            return handle_unauthorized_access()
        
        # Check if session is healthy
        if not is_session_healthy():
            logger.warning(f"Unhealthy session for user {current_user.id} accessing {request.path}")
            return handle_unauthorized_access()
        
        return f(*args, **kwargs)
    return decorated_function

def is_session_healthy():
    """Check if the current session is healthy."""
    try:
        # If user is authenticated via Flask-Login, we should allow the request
        # even if session data is incomplete (it will be fixed by update_session_activity)
        if current_user.is_authenticated:
            # Check if we have basic session data
            if not session.get('user_id'):
                # Try to initialize session data if missing
                try:
                    session['user_id'] = current_user.id
                    session['username'] = current_user.username
                    session['last_activity'] = datetime.utcnow().isoformat()
                    session['session_start'] = datetime.utcnow().isoformat()
                    logger.info(f"Initialized missing session data for user {current_user.id}")
                except Exception as e:
                    logger.warning(f"Could not initialize session data: {e}")
                    # Still allow the request if user is authenticated
                    return True
            
            # Check last activity
            last_activity = session.get('last_activity')
            if not last_activity:
                # Initialize last activity if missing
                session['last_activity'] = datetime.utcnow().isoformat()
                logger.info(f"Initialized missing last_activity for user {current_user.id}")
                return True
            
            # Parse last activity time
            if isinstance(last_activity, str):
                try:
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                except ValueError:
                    # If parsing fails, reset the timestamp
                    session['last_activity'] = datetime.utcnow().isoformat()
                    logger.info(f"Reset invalid last_activity timestamp for user {current_user.id}")
                    return True
            
            # Check if session is within 2 hours (more lenient for API calls)
            time_diff = datetime.utcnow() - last_activity
            if time_diff > timedelta(hours=2):
                logger.warning(f"Session expired for user {session.get('user_id')}")
                return False
            
            # Check if user has been marked offline in the database
            if current_user.is_authenticated and hasattr(current_user, 'is_online') and not current_user.is_online:
                logger.warning(f"User {current_user.id} is authenticated but marked offline – forcing re-login")
                return False
            
            return True
        else:
            # User is not authenticated, session should not be healthy
            return False
            
    except Exception as e:
        logger.error(f"Error checking session health: {e}")
        # If there's an error checking session health, but user is authenticated,
        # allow the request to proceed (session will be fixed by update_session_activity)
        return current_user.is_authenticated

def update_session_activity():
    """Update session activity timestamp."""
    try:
        session['last_activity'] = datetime.utcnow().isoformat()
        session['request_count'] = session.get('request_count', 0) + 1
    except Exception as e:
        logger.error(f"Error updating session activity: {e}")

def setup_auth_middleware(app):
    """Setup authentication middleware for the Flask app."""
    
    @app.before_request
    def auth_middleware():
        """Authentication middleware that runs before each request."""
        try:
            path = request.path
            
            # Skip authentication for public routes
            if is_public_route(path):
                return None
            
            # Check if user is authenticated
            if not current_user.is_authenticated:
                logger.warning(f"Unauthorized access attempt to {path} from {request.remote_addr}")
                return handle_unauthorized_access()
            
            # Update session activity for authenticated users
            update_session_activity()
            
            # For API routes, be more lenient with session health checks
            if is_api_route(path):
                # Only check basic authentication for API routes
                # Don't enforce strict session health for API calls
                return None
            
            # Check session health for web routes
            if not is_session_healthy():
                logger.warning(f"Unhealthy session for user {current_user.id} accessing {path}")
                # Clear session and redirect to login
                session.clear()
                return handle_unauthorized_access()
            
        except Exception as e:
            logger.error(f"Error in auth middleware: {e}")
            # On error, redirect to login as fallback
            return handle_unauthorized_access()
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors."""
        return handle_unauthorized_access()
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        return handle_unauthorized_access()
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        # Always redirect unauthenticated users to login
        if not current_user.is_authenticated:
            logger.warning(f"Unauthenticated user accessing 404 page: {request.path}")
            return handle_unauthorized_access()
        
        # For authenticated users, show 404 page but ensure it doesn't have navigation to protected areas
        try:
            from flask import render_template
            return render_template('404.html', year=datetime.utcnow().year), 404
        except Exception as e:
            logger.error(f"Error rendering 404 template: {e}")
            # Fallback: redirect to login if template fails
            return handle_unauthorized_access()
    
    logger.info("Authentication middleware setup completed")

def clear_user_sessions(user_id):
    """Clear all sessions for a specific user."""
    try:
        # Clear session files
        from pathlib import Path
        session_dir = Path(current_app.config.get('SESSION_FILE_DIR', 'sessions'))
        if session_dir.exists():
            session_file = session_dir / f"user_{user_id}.json"
            if session_file.exists():
                session_file.unlink()
                logger.info(f"Cleared session file for user {user_id}")
        
        # Clear enhanced session manager data
        try:
            from app.utils.enhanced_session_manager import EnhancedSessionManager
            enhanced_manager = EnhancedSessionManager()
            enhanced_manager.force_logout()
        except Exception as e:
            logger.warning(f"Error clearing enhanced session data: {e}")
        
        # Clear user presence
        try:
            from app.services.user_presence import presence_service
            presence_service.force_user_offline(user_id)
        except Exception as e:
            logger.warning(f"Error clearing user presence: {e}")
        
        logger.info(f"Cleared all sessions for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing sessions for user {user_id}: {e}")
        return False 