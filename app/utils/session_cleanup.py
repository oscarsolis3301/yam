"""
Session Cleanup Utilities for YAM Application
Handles clearing all user sessions during server shutdown
"""

import os
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from flask import current_app
from flask_login import logout_user

logger = logging.getLogger(__name__)

def clear_all_user_sessions():
    """
    Clear all user sessions from all sources during server shutdown.
    This ensures all users must re-authenticate when the server restarts.
    """
    logger.info("=" * 60)
    logger.info("[SHUTDOWN] CLEARING ALL USER SESSIONS")
    logger.info("=" * 60)
    
    cleared_count = 0
    
    try:
        # Phase 0: Clear Flask session data immediately
        logger.info("[STEP] Phase 0: Clearing Flask session data...")
        try:
            from flask import session
            session.clear()
            logger.info("  [OK] Flask session data cleared")
        except Exception as e:
            logger.warning(f"  [WARN] Flask session clear: {e}")
        
        # Phase 1: Clear session files
        logger.info("[STEP] Phase 1: Clearing session files...")
        session_dirs = [
            'sessions',
            'app/sessions',
            'YAM/sessions',
            'yam_workspace/sessions'
        ]
        
        for session_dir in session_dirs:
            session_path = Path(session_dir)
            if session_path.exists():
                try:
                    # Count files before deletion
                    session_files = list(session_path.glob('*'))
                    file_count = len([f for f in session_files if f.is_file()])
                    
                    # Remove all files and directories
                    shutil.rmtree(session_path)
                    session_path.mkdir(exist_ok=True)
                    
                    cleared_count += file_count
                    logger.info(f"  [OK] Cleared {file_count} session files from {session_dir}")
                except Exception as e:
                    logger.warning(f"  [WARN] Error clearing {session_dir}: {e}")
        
        # Phase 2: Clear enhanced session manager data
        logger.info("[STEP] Phase 2: Clearing enhanced session manager data...")
        try:
            from app.utils.enhanced_session_manager import EnhancedSessionManager
            enhanced_manager = EnhancedSessionManager()
            enhanced_manager.force_logout()
            logger.info("  [OK] Enhanced session manager data cleared")
        except Exception as e:
            logger.warning(f"  [WARN] Enhanced session manager: {e}")
        
        # Phase 3: Clear user presence data
        logger.info("[STEP] Phase 3: Clearing user presence data...")
        try:
            from app.services.user_presence import UserPresenceService
            presence_service = UserPresenceService()
            
            # Get all online users and mark them offline
            online_users = presence_service.get_online_users(include_details=True)
            for user_info in online_users:
                try:
                    presence_service._mark_offline_immediately(user_info['user_id'])
                except Exception as e:
                    logger.warning(f"  [WARN] Could not mark user {user_info['user_id']} offline: {e}")
            
            # Clear all active sessions
            presence_service._active_sessions.clear()
            logger.info(f"  [OK] Cleared presence data for {len(online_users)} users")
            
        except Exception as e:
            logger.warning(f"  [WARN] User presence service: {e}")
        
        # Phase 4: Clear database session data
        logger.info("[STEP] Phase 4: Clearing database session data...")
        try:
            from extensions import db
            from app.models import User
            
            with current_app.app_context():
                # Mark all users as offline
                User.query.update({User.is_online: False})
                db.session.commit()
                logger.info("  [OK] All users marked as offline in database")
        except Exception as e:
            logger.warning(f"  [WARN] Database session cleanup: {e}")
        
        # Phase 5: Clear cache directories
        logger.info("[STEP] Phase 5: Clearing cache directories...")
        cache_dirs = [
            'cache',
            'app/cache',
            'YAM/cache',
            'yam_workspace/cache',
            'temp_build',
            'temp_dist_*'
        ]
        
        for cache_pattern in cache_dirs:
            try:
                if '*' in cache_pattern:
                    # Handle glob patterns
                    for cache_path in Path('.').glob(cache_pattern):
                        if cache_path.is_dir():
                            shutil.rmtree(cache_path)
                            cache_path.mkdir(exist_ok=True)
                            logger.info(f"  [OK] Cleared cache directory: {cache_path}")
                else:
                    cache_path = Path(cache_pattern)
                    if cache_path.exists():
                        shutil.rmtree(cache_path)
                        cache_path.mkdir(exist_ok=True)
                        logger.info(f"  [OK] Cleared cache directory: {cache_pattern}")
            except Exception as e:
                logger.warning(f"  [WARN] Error clearing cache {cache_pattern}: {e}")
        
        # Phase 6: Clear temporary session data
        logger.info("[STEP] Phase 6: Clearing temporary session data...")
        temp_dirs = [
            'temp',
            'app/temp',
            'YAM/temp',
            'yam_workspace/temp'
        ]
        
        for temp_dir in temp_dirs:
            temp_path = Path(temp_dir)
            if temp_path.exists():
                try:
                    shutil.rmtree(temp_path)
                    temp_path.mkdir(exist_ok=True)
                    logger.info(f"  [OK] Cleared temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"  [WARN] Error clearing temp {temp_dir}: {e}")
        
        # Phase 7: Broadcast logout to all connected clients
        logger.info("[STEP] Phase 7: Broadcasting logout to all clients...")
        try:
            from flask_socketio import emit
            from extensions import socketio
            
            # Emit logout event to all connected clients
            socketio.emit('server_shutdown', {
                'message': 'Server is shutting down. All users must re-authenticate.',
                'timestamp': datetime.utcnow().isoformat(),
                'require_relogin': True
            }, broadcast=True)
            
            logger.info("  [OK] Logout broadcast sent to all clients")
        except Exception as e:
            logger.warning(f"  [WARN] SocketIO broadcast: {e}")
        
        # Phase 8: Clear session cookies
        logger.info("[STEP] Phase 8: Clearing session cookies...")
        try:
            # Set session cookie to expire immediately
            from flask import make_response
            response = make_response()
            response.delete_cookie('session')
            response.delete_cookie('yam_session')
            response.delete_cookie('csrf_token')
            logger.info("  [OK] Session cookies cleared")
        except Exception as e:
            logger.warning(f"  [WARN] Cookie clearing: {e}")
        
        # Summary
        logger.info("=" * 60)
        logger.info("[OK] ALL USER SESSIONS CLEARED SUCCESSFULLY")
        logger.info(f"[COUNT] Total session files cleared: {cleared_count}")
        logger.info("[INFO] All users will need to re-authenticate on next server start")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Critical error during session cleanup: {e}")
        logger.error("[FATAL] Session cleanup failed - users may retain sessions")
        return False

def force_logout_all_users():
    """
    Force logout all currently authenticated users.
    This is called during server shutdown to ensure all sessions are invalidated.
    """
    logger.info("[SHUTDOWN] Force logging out all users...")
    
    try:
        # Clear all session files
        clear_all_user_sessions()
        
        # Additional cleanup for any remaining session data
        try:
            from app.utils.session_manager import SessionManager
            session_manager = SessionManager()
            session_manager.cleanup_old_sessions(max_age_days=0)  # Clear all sessions
        except Exception as e:
            logger.warning(f"Session manager cleanup: {e}")
        
        logger.info("[OK] All users have been force logged out")
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Error during force logout: {e}")
        return False

def create_shutdown_marker():
    """
    Create a marker file indicating the server was shut down.
    This can be used to detect if users need to re-authenticate.
    """
    try:
        shutdown_marker = Path('server_shutdown_marker.txt')
        with open(shutdown_marker, 'w') as f:
            f.write(f"Server shutdown at: {datetime.utcnow().isoformat()}\n")
            f.write("All users must re-authenticate on next startup.\n")
        
        logger.info("[OK] Server shutdown marker created")
        return True
    except Exception as e:
        logger.warning(f"[WARN] Could not create shutdown marker: {e}")
        return False

def check_shutdown_marker():
    """
    Check if server was shut down and clear the marker.
    Returns True if server was shut down, False otherwise.
    """
    try:
        shutdown_marker = Path('server_shutdown_marker.txt')
        if shutdown_marker.exists():
            shutdown_marker.unlink()
            logger.info("[INFO] Server shutdown marker detected and cleared")
            return True
        return False
    except Exception as e:
        logger.warning(f"[WARN] Error checking shutdown marker: {e}")
        return False 