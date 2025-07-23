"""
Session Manager for YAM Application
Handles session persistence and recovery
"""

import os
import json
import pickle
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import session, request, current_app
from flask_login import current_user

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages user sessions with persistence and recovery"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the session manager with the Flask app"""
        self.app = app
        
        # Ensure session directory exists
        session_dir = Path(app.root_path).parent / 'sessions'
        session_dir.mkdir(exist_ok=True)
        
        # Configure session settings
        app.config.setdefault('SESSION_TYPE', 'filesystem')
        app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(days=30))
        app.config.setdefault('SESSION_FILE_THRESHOLD', 1000)
        app.config.setdefault('SESSION_FILE_DIR', str(session_dir))
        
        # Enhanced session configuration for production
        app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP for local development
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['SESSION_REFRESH_EACH_REQUEST'] = True
        
        # Register session handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Initialize Flask-Session if available
        try:
            from flask_session import Session
            Session(app)
            logger.info("Flask-Session initialized")
        except ImportError:
            logger.info("Flask-Session not available, using built-in sessions")
        
        # Clean up old sessions on startup
        self.cleanup_old_sessions()
        
        logger.info("Session manager initialized successfully")
    
    def _before_request(self):
        """Handle session before each request"""
        try:
            # Check if app is initialized
            if self.app is None:
                logger.warning("Session manager app not initialized in before_request")
                return
                
            # Make session permanent for authenticated users
            if current_user.is_authenticated:
                session.permanent = True
                
                # Store user info in session
                session['user_id'] = current_user.id
                session['username'] = current_user.username
                session['last_activity'] = datetime.utcnow().isoformat()
                
                # Store user preferences
                if hasattr(current_user, 'settings'):
                    session['user_settings'] = current_user.settings.to_dict() if hasattr(current_user.settings, 'to_dict') else {}
            
            # Track session activity
            session['last_request'] = datetime.utcnow().isoformat()
            session['request_count'] = session.get('request_count', 0) + 1
            
        except Exception as e:
            logger.warning(f"Error in session before_request: {e}")
    
    def _after_request(self, response):
        """Handle session after each request"""
        try:
            # Check if app is initialized
            if self.app is None:
                logger.warning("Session manager app not initialized in after_request")
                return response
                
            # Update session with response info
            session['last_response'] = datetime.utcnow().isoformat()
            
            # Store session data
            if current_user.is_authenticated:
                self._save_user_session()
                
        except Exception as e:
            logger.warning(f"Error in session after_request: {e}")
        
        return response
    
    def _save_user_session(self):
        """Save user session data to persistent storage"""
        try:
            if not current_user.is_authenticated:
                return
            
            # Check if app is initialized
            if self.app is None:
                logger.warning("Session manager app not initialized, cannot save user session")
                return
                
            user_id = current_user.id
            session_file = Path(self.app.config['SESSION_FILE_DIR']) / f"user_{user_id}.json"
            
            session_data = {
                'user_id': user_id,
                'username': current_user.username,
                'last_activity': session.get('last_activity'),
                'last_request': session.get('last_request'),
                'last_response': session.get('last_response'),
                'request_count': session.get('request_count', 0),
                'user_settings': session.get('user_settings', {}),
                'saved_at': datetime.utcnow().isoformat()
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Error saving user session: {e}")
    
    def load_user_session(self, user_id):
        """Load user session data from persistent storage"""
        try:
            # Check if app is initialized
            if self.app is None:
                logger.warning("Session manager app not initialized, cannot load user session")
                return False
                
            session_file = Path(self.app.config['SESSION_FILE_DIR']) / f"user_{user_id}.json"
            
            if session_file.exists():
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                # Restore session data
                for key, value in session_data.items():
                    if key not in ['saved_at']:  # Skip metadata
                        session[key] = value
                
                logger.info(f"Loaded session for user {user_id}")
                return True
                
        except Exception as e:
            logger.warning(f"Error loading user session: {e}")
        
        return False
    
    def cleanup_old_sessions(self, max_age_days=7):
        """Clean up old session files"""
        try:
            # Check if app is initialized
            if self.app is None:
                logger.warning("Session manager app not initialized, skipping cleanup")
                return
                
            session_dir = Path(self.app.config['SESSION_FILE_DIR'])
            cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
            
            cleaned_count = 0
            for session_file in session_dir.glob("user_*.json"):
                try:
                    file_time = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        session_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Error cleaning session file {session_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old session files")
                
        except Exception as e:
            logger.warning(f"Error during session cleanup: {e}")
    
    def get_session_stats(self):
        """Get session statistics"""
        try:
            # Check if app is initialized
            if self.app is None:
                logger.warning("Session manager app not initialized, returning empty stats")
                return {}
                
            session_dir = Path(self.app.config['SESSION_FILE_DIR'])
            session_files = list(session_dir.glob("user_*.json"))
            
            stats = {
                'total_sessions': len(session_files),
                'session_dir': str(session_dir),
                'last_cleanup': None
            }
            
            # Check for cleanup file
            cleanup_file = session_dir / 'last_cleanup.txt'
            if cleanup_file.exists():
                stats['last_cleanup'] = cleanup_file.read_text().strip()
            
            return stats
            
        except Exception as e:
            logger.warning(f"Error getting session stats: {e}")
            return {}

# Global session manager instance
session_manager = SessionManager()

def init_session_manager(app):
    """Initialize the session manager with the Flask app"""
    session_manager.init_app(app)
    return session_manager 