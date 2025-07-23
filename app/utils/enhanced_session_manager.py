"""
Enhanced Session Manager for YAM Application
Provides robust session management with conflict resolution and hydration
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import session, request, current_app, g, redirect, url_for
from flask_login import current_user
from sqlalchemy import inspect, text
from sqlalchemy.exc import InvalidRequestError

logger = logging.getLogger(__name__)

class EnhancedSessionManager:
    """
    Enhanced session management with automatic cleanup, monitoring, and client-side integration.
    """
    
    def __init__(self, app=None):
        self.app = app
        self.session_lifetime = timedelta(minutes=30)  # 30 minutes as requested
        self.cleanup_interval = timedelta(minutes=5)   # Clean up every 5 minutes
        self.last_cleanup = datetime.utcnow()
        self.background_thread = None
        self.running = False
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the session manager with the Flask app."""
        self.app = app
        
        # Set session configuration
        app.config.setdefault('PERMANENT_SESSION_LIFETIME', self.session_lifetime)
        app.config.setdefault('SESSION_REFRESH_EACH_REQUEST', True)
        app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
        app.config.setdefault('SESSION_COOKIE_SECURE', False)
        app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
        
        # Ensure session directory exists
        session_dir = Path(app.root_path).parent / 'sessions'
        session_dir.mkdir(exist_ok=True)
        app.config.setdefault('SESSION_FILE_DIR', str(session_dir))
        
        # Register before_request handler
        app.before_request(self._before_request)
        
        # Start background cleanup thread
        self._start_background_cleanup()
        
        logger.info(f"Enhanced Session Manager initialized with {self.session_lifetime} lifetime")
    
    def _before_request(self):
        """Handle session management before each request."""
        try:
            # Check if app is initialized
            if self.app is None:
                logger.warning("Enhanced session manager app not initialized in before_request")
                return
                
            # Clean up stale sessions periodically
            if datetime.utcnow() - self.last_cleanup > self.cleanup_interval:
                self._cleanup_stale_sessions()
                self.last_cleanup = datetime.utcnow()
            
            # Check session health for authenticated users
            if session.get('user_id'):
                if not self._check_session_health():
                    # Session is stale, clear it
                    session.clear()
                    logger.info(f"Cleared stale session for user {session.get('user_id')}")
                    return redirect(url_for('auth.login'))
                
                # Update session activity
                session['last_activity'] = datetime.utcnow().isoformat()
                session['request_count'] = session.get('request_count', 0) + 1
                
        except Exception as e:
            logger.error(f"Error in session before_request handler: {e}")
    
    def _check_session_health(self):
        """Check if the current session is healthy and not stale."""
        try:
            if not session.get('user_id'):
                return False
            
            last_activity = session.get('last_activity')
            if not last_activity:
                return False
            
            # Parse last activity time
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            
            # Check if session is within 30 minutes (as requested)
            time_diff = datetime.utcnow() - last_activity
            if time_diff > self.session_lifetime:
                logger.warning(f"Session expired for user {session.get('user_id')}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking session health: {e}")
            return False
    
    def get_session_time_remaining(self):
        """Get the time remaining in the current session in seconds."""
        try:
            if not session.get('user_id'):
                return 0
            
            last_activity = session.get('last_activity')
            if not last_activity:
                return 0
            
            # Parse last activity time
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            
            # Calculate time remaining
            time_diff = datetime.utcnow() - last_activity
            remaining = self.session_lifetime - time_diff
            
            return max(0, int(remaining.total_seconds()))
        except Exception as e:
            logger.error(f"Error calculating session time remaining: {e}")
            return 0
    
    def extend_session(self):
        """Extend the current session by updating last activity."""
        try:
            if session.get('user_id'):
                session['last_activity'] = datetime.utcnow().isoformat()
                session['request_count'] = session.get('request_count', 0) + 1
                session['extended_count'] = session.get('extended_count', 0) + 1
                return True
            return False
        except Exception as e:
            logger.error(f"Error extending session: {e}")
            return False
    
    def _cleanup_stale_sessions(self):
        """Clean up stale sessions from the filesystem."""
        try:
            # Check if app is initialized
            if self.app is None:
                logger.warning("Enhanced session manager app not initialized, skipping cleanup")
                return
                
            session_dir = Path(self.app.config.get('SESSION_FILE_DIR', 'sessions'))
            if not session_dir.exists():
                return
            
            session_files = list(session_dir.glob('user_*.json'))
            current_time = datetime.utcnow()
            cleaned_count = 0
            
            for session_file in session_files:
                try:
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if current_time - file_mtime > self.session_lifetime:
                        session_file.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up stale session file: {session_file.name}")
                except Exception as e:
                    logger.warning(f"Error cleaning up session file {session_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} stale session files")
                
        except Exception as e:
            logger.error(f"Error in session cleanup: {e}")
    
    def _start_background_cleanup(self):
        """Start background thread for session cleanup."""
        if self.background_thread and self.background_thread.is_alive():
            return
        
        self.running = True
        self.background_thread = threading.Thread(target=self._background_cleanup_worker, daemon=True)
        self.background_thread.start()
        logger.info("Background session cleanup thread started")
    
    def _background_cleanup_worker(self):
        """Background worker for session cleanup."""
        while self.running:
            try:
                time.sleep(300)  # Sleep for 5 minutes
                # Check if app is initialized before cleanup
                if self.app is not None:
                    self._cleanup_stale_sessions()
                else:
                    logger.warning("Enhanced session manager app not initialized in background worker")
            except Exception as e:
                logger.error(f"Error in background cleanup worker: {e}")
    
    def stop_background_cleanup(self):
        """Stop the background cleanup thread."""
        self.running = False
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join(timeout=5)
        logger.info("Background session cleanup thread stopped")
    
    def get_session_status(self):
        """Get comprehensive session status information."""
        try:
            return {
                'session_active': session.get('user_id') is not None,
                'user_authenticated': session.get('user_id') is not None,
                'session_healthy': self._check_session_health(),
                'time_remaining_seconds': self.get_session_time_remaining(),
                'time_remaining_minutes': self.get_session_time_remaining() // 60,
                'session_lifetime_minutes': int(self.session_lifetime.total_seconds() // 60),
                'last_activity': session.get('last_activity'),
                'request_count': session.get('request_count', 0),
                'extended_count': session.get('extended_count', 0),
                'user_id': session.get('user_id'),
                'background_cleanup_active': self.running,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return {
                'session_active': False,
                'session_healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def force_logout(self):
        """Force logout the current user."""
        try:
            user_id = session.get('user_id')
            session.clear()
            logger.info(f"Force logout for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error in force logout: {e}")
            return False

# Global session manager instance
enhanced_session_manager = EnhancedSessionManager()

def init_enhanced_session_manager(app):
    """Initialize the enhanced session manager with the Flask app"""
    enhanced_session_manager.init_app(app)
    return enhanced_session_manager 