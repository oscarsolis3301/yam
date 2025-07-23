from __future__ import annotations

"""Socket.IO connection lifecycle handlers (connect / disconnect).

Importing this module registers the event handlers with the global
``socketio`` instance (see ``extensions``).  It is automatically imported
from :pymod:`app.socket_handlers` so no explicit import is required
elsewhere.
"""

from datetime import datetime, timedelta
from threading import Timer
import logging

from flask import request
from flask_login import current_user
from flask_socketio import emit

from extensions import db, socketio
from app.services.user_presence import UserPresenceService

# Import for backward compatibility
import app.socket_handlers.admin_presence as admin_presence  # noqa: F401

from app.models import User

logger = logging.getLogger("spark")

# ---------------------------------------------------------------------------
# Service instance and app context
# ---------------------------------------------------------------------------

# Global presence service instance
presence_service = UserPresenceService()

def set_flask_app(app):
    """Store the Flask app instance for use in background threads."""
    presence_service.set_app_context(app)

def cleanup_timers():
    """Cancel all pending disconnect timers - handled by presence service."""
    logger.info("Timer cleanup handled by UserPresenceService")

def get_online_users_data():
    """Get list of all users with their online status - using presence service."""
    return presence_service.get_online_users(include_details=True)

def mark_user_online(user_id):
    """Mark a user as online - using presence service."""
    return presence_service.mark_user_online(user_id)

def cleanup_stale_online_status():
    """Clean up users who haven't been seen recently - using presence service."""
    return presence_service.cleanup_stale_users()

# ---------------------------------------------------------------------------
# Event: connect
# ---------------------------------------------------------------------------

@socketio.on("connect")
def handle_connect(auth=None):  # noqa: D401 (imperative mood)
    """Handle Socket.IO connection with enhanced stability and error handling."""
    try:
        # Always allow connections - never reject based on authentication status
        # This prevents random disconnections due to session validation issues
        
        # Get connection metadata
        connection_id = request.args.get('connection_id', 'unknown')
        connection_time = request.args.get('timestamp', str(int(datetime.utcnow().timestamp() * 1000)))
        
        logger.info(f"[socketio] CONNECT; current_user=%r, connection_id=%s", current_user, connection_id)
        
        # Update session activity if user is authenticated
        if current_user.is_authenticated:
            user_id = current_user.id
            logger.info(f"[socketio] marking user {user_id} online")
            
            # Gather session metadata
            session_data = {
                'ip_address': request.environ.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
                'connection_time': datetime.utcnow().isoformat(),
                'socket_id': request.sid,
                'connection_id': connection_id
            }
            
            # Use presence service to handle connection
            success = presence_service.handle_socket_connect(user_id, session_data)
            
            if success:
                logger.info(f"[socketio] Successfully connected user {user_id} ({current_user.username})")
                # Send initial presence data to the connecting client
                emit("presence_connected", {
                    "user_id": user_id,
                    "username": current_user.username,
                    "connected_at": datetime.utcnow().isoformat(),
                    "connection_id": connection_id
                })
            else:
                logger.warning(f"[socketio] Issues with presence tracking for user {user_id}, but connection allowed")
                # Still allow the connection even if presence tracking fails
                emit("presence_connected", {
                    "user_id": user_id,
                    "username": current_user.username,
                    "connected_at": datetime.utcnow().isoformat(),
                    "connection_id": connection_id,
                    "warning": "Presence tracking unavailable"
                })
        else:
            # Anonymous connection - log but don't reject
            logger.info(f"[socketio] Anonymous connection allowed (connection_id: {connection_id})")
            emit("presence_connected", {
                "anonymous": True,
                "connected_at": datetime.utcnow().isoformat(),
                "connection_id": connection_id
            })
            
    except Exception as e:
        logger.error(f"[socketio] Error during connect: {e}")
        # Don't reject connection on error, just log it
        # This prevents disconnections due to unexpected errors
        emit("error", {"message": "Connection established with warnings"})

# ---------------------------------------------------------------------------
# Event: disconnect
# ---------------------------------------------------------------------------

@socketio.on("disconnect")
def handle_disconnect() -> None:  # noqa: D401
    """Handle user disconnect with graceful offline marking."""
    if not current_user.is_authenticated:
        logger.debug("[socketio] Anonymous disconnect, skipping presence tracking")
        return
        
    user_id = current_user.id
    logger.info(f"[socketio] DISCONNECT; user_id={user_id}")
    
    try:
        # Use presence service to handle disconnect (with grace period)
        success = presence_service.handle_socket_disconnect(user_id)
        
        if success:
            logger.info(f"[socketio] Successfully handled disconnect for user {user_id}")
        else:
            logger.warning(f"[socketio] Issues handling disconnect for user {user_id}")
            
    except Exception as e:
        logger.error(f"[socketio] Error during disconnect for user {user_id}: {e}")

# ---------------------------------------------------------------------------
# Event: heartbeat
# ---------------------------------------------------------------------------

# Note: Heartbeat handler moved to admin_presence.py to avoid conflicts
# This handler is now handled by the more comprehensive version in admin_presence.py

# ---------------------------------------------------------------------------
# Event: force_offline
# ---------------------------------------------------------------------------

@socketio.on("force_offline")
def handle_force_offline(data=None):  # noqa: D401
    """Admin-only: Force a user offline immediately."""
    if not current_user.is_authenticated:
        emit("error", {"message": "Not authenticated"})
        return
        
    # Check if user has admin privileges
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        emit("error", {"message": "Admin privileges required"})
        return
        
    if not data or 'user_id' not in data:
        emit("error", {"message": "User ID required"})
        return
        
    try:
        target_user_id = int(data['user_id'])
        success = presence_service.force_user_offline(target_user_id)
        
        if success:
            emit("force_offline_success", {
                "user_id": target_user_id,
                "forced_by": current_user.id,
                "timestamp": datetime.utcnow().isoformat()
            })
            logger.info(f"[socketio] Admin {current_user.id} forced user {target_user_id} offline")
        else:
            emit("error", {"message": "Failed to force user offline"})
            
    except (ValueError, TypeError) as e:
        emit("error", {"message": "Invalid user ID"})
    except Exception as e:
        logger.error(f"[socketio] Error forcing user offline: {e}")
        emit("error", {"message": "Error processing force offline request"})

# ---------------------------------------------------------------------------
# Event: cleanup_stale
# ---------------------------------------------------------------------------

@socketio.on("cleanup_stale_users")
def handle_cleanup_stale(data=None):  # noqa: D401
    """Admin-only: Manually trigger stale user cleanup."""
    if not current_user.is_authenticated:
        emit("error", {"message": "Not authenticated"})
        return
        
    # Check if user has admin privileges
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        emit("error", {"message": "Admin privileges required"})
        return
        
    try:
        cleaned_count = presence_service.cleanup_stale_users()
        
        emit("cleanup_complete", {
            "cleaned_count": cleaned_count,
            "timestamp": datetime.utcnow().isoformat(),
            "requested_by": current_user.id
        })
        
        logger.info(f"[socketio] Admin {current_user.id} triggered cleanup, {cleaned_count} users cleaned")
        
    except Exception as e:
        logger.error(f"[socketio] Error during manual cleanup: {e}")
        emit("error", {"message": "Error during cleanup process"})

# ---------------------------------------------------------------------------
# Periodic cleanup task
# ---------------------------------------------------------------------------

def schedule_periodic_cleanup():
    """Schedule periodic cleanup of stale users."""
    def cleanup_task():
        try:
            # Only run cleanup if we have an app context
            if presence_service._app_context:
                with presence_service._app_context.app_context():
                    cleaned_count = presence_service.cleanup_stale_users()
                    if cleaned_count > 0:
                        logger.info(f"Periodic cleanup: removed {cleaned_count} stale users")
        except Exception as e:
            logger.error(f"Error in periodic cleanup task: {e}")
        finally:
            # Schedule next cleanup
            Timer(UserPresenceService.STALE_CLEANUP_INTERVAL, cleanup_task).start()
    
    # Start the cleanup cycle
    Timer(UserPresenceService.STALE_CLEANUP_INTERVAL, cleanup_task).start()
    logger.info("Scheduled periodic presence cleanup task") 