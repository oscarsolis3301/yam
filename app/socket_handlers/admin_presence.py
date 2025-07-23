"""User presence & admin dashboard Socket.IO handlers extracted from app/spark.py.

Importing this module registers the event handlers with the global ``socketio``
instance (see ``extensions.py``) so no explicit calls are required elsewhere.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta

from flask_login import current_user
from flask_socketio import emit

from extensions import db, socketio
from app.models import User, Outage
from app.services.user_presence import UserPresenceService

# Import the presence service instance from connection module
from .connection import presence_service

__all__ = [
    "handle_admin_dashboard_request",
    "handle_heartbeat",
    "handle_get_online_users",
    "handle_user_status_request",
]

logger = logging.getLogger("spark")

# ---------------------------------------------------------------------------
# Event: admin_dashboard_request
# ---------------------------------------------------------------------------

@socketio.on("admin_dashboard_request")
def handle_admin_dashboard_request() -> None:  # noqa: D401 (imperative mood)
    """Return an aggregated admin-dashboard payload and mark caller online."""
    try:
        # 1) Mark the requesting user online (if authenticated)
        if current_user.is_authenticated:
            success = presence_service.update_heartbeat(current_user.id)
            if not success:
                logger.warning(f"Failed to update heartbeat for user {current_user.id} in dashboard request")

        # 2) Gather stats for the dashboard using presence service
        users_list = presence_service.get_online_users(include_details=True)
        presence_stats = presence_service.get_presence_stats()
        
        active_sessions = presence_stats['online_users']
        total_users = presence_stats['total_users']
        
        # Get other system stats
        try:
            active_outages = Outage.query.filter_by(status="active").count()
        except Exception as e:
            logger.error(f"Error getting active outages: {e}")
            active_outages = 0
            
        open_tickets = 0  # TODO: hook into ticketing system when available

        dashboard_data = {
            "total_users": total_users,
            "active_sessions": active_sessions,
            "active_outages": active_outages,
            "open_tickets": open_tickets,
            "online_users": users_list,
            "presence_stats": {
                "last_cleanup": presence_stats['last_cleanup'],
                "stale_threshold": UserPresenceService.ACTIVITY_TIMEOUT,
                "heartbeat_interval": UserPresenceService.HEARTBEAT_INTERVAL,
                "average_session_duration": presence_stats.get('average_session_duration', 0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        emit("admin_dashboard_data", dashboard_data)
        emit("online_users_update", users_list)
        
        logger.debug(f"Sent dashboard data with {active_sessions} active users")

    except Exception as exc:  # pragma: no cover – log & swallow
        logger.error("Error handling admin dashboard request: %s", exc)
        emit("error", {"message": "Error loading dashboard data"})

# ---------------------------------------------------------------------------
# Event: heartbeat
# ---------------------------------------------------------------------------

@socketio.on("heartbeat")
def handle_heartbeat(data=None) -> None:  # noqa: D401
    """Mark the user online & broadcast the refreshed online-user list."""
    if not current_user.is_authenticated:
        emit("error", {"message": "Not authenticated"})
        return

    try:
        user_id = current_user.id
        
        # Update heartbeat using presence service
        success = presence_service.update_heartbeat(user_id)
        
        if success:
            # Get updated users list and broadcast
            users_list = presence_service.get_online_users(include_details=True)
            emit("online_users_update", users_list, broadcast=True)
            
            # Send heartbeat acknowledgment to sender
            emit("heartbeat_ack", {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "username": current_user.username
            })
            
            logger.debug(f"Processed heartbeat for user {user_id} ({current_user.username})")
        else:
            logger.warning(f"Failed to process heartbeat for user {user_id}")
            emit("error", {"message": "Heartbeat processing failed"})
            
    except Exception as e:
        logger.error(f"Error in heartbeat handler: {e}")
        emit("error", {"message": "Heartbeat error occurred"})

# ---------------------------------------------------------------------------
# Event: get_online_users
# ---------------------------------------------------------------------------

@socketio.on("get_online_users")
def handle_get_online_users() -> None:
    """Return current online users list."""
    try:
        users_list = presence_service.get_online_users(include_details=True)
        presence_stats = presence_service.get_presence_stats()
        
        response_data = {
            "users": users_list,
            "stats": {
                "total_online": presence_stats['online_users'],
                "total_users": presence_stats['total_users'],
                "last_cleanup": presence_stats['last_cleanup']
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        emit("online_users_update", users_list)
        emit("presence_stats", response_data)
        
        logger.debug(f"Sent online users list: {len(users_list)} users")
        
    except Exception as e:
        logger.error(f"Error getting online users: {e}")
        emit("error", {"message": "Error loading online users"})

# ---------------------------------------------------------------------------
# Event: user_status_request
# ---------------------------------------------------------------------------

@socketio.on("user_status_request")
def handle_user_status_request(data=None) -> None:
    """Return status of specific user(s)."""
    try:
        if not data or 'user_ids' not in data:
            emit("error", {"message": "No user IDs provided"})
            return
        
        user_ids = data['user_ids']
        if not isinstance(user_ids, list):
            user_ids = [user_ids]
        
        # Get status for each requested user
        user_statuses = []
        for user_id in user_ids:
            try:
                status = presence_service.get_user_status(user_id)
                if status:
                    user_statuses.append(status)
                else:
                    logger.warning(f"No status found for user {user_id}")
            except Exception as e:
                logger.error(f"Error getting status for user {user_id}: {e}")
        
        response_data = {
            "users": user_statuses,
            "requested_ids": user_ids,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        emit("user_status_response", response_data)
        
        logger.debug(f"Sent status for {len(user_statuses)} users")
        
    except Exception as e:
        logger.error(f"Error handling user status request: {e}")
        emit("error", {"message": "Error getting user status"})

# ---------------------------------------------------------------------------
# Event: presence_stats
# ---------------------------------------------------------------------------

@socketio.on("get_presence_stats")
def handle_presence_stats_request() -> None:
    """Return detailed presence statistics."""
    try:
        # Check if user has admin privileges for detailed stats
        is_admin = (current_user.is_authenticated and 
                   hasattr(current_user, 'role') and 
                   current_user.role == 'admin')
        
        stats = presence_service.get_presence_stats()
        
        # Basic stats for all authenticated users
        response_data = {
            "active_users": stats['online_users'],
            "total_users": stats['total_users'],
            "last_cleanup": stats['last_cleanup'],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Detailed stats only for admins
        if is_admin:
            response_data.update({
                "average_session_duration": stats.get('average_session_duration', 0),
                "longest_session": stats.get('longest_session', 0),
                "cleanup_intervals": UserPresenceService.STALE_CLEANUP_INTERVAL,
                "activity_timeout": UserPresenceService.ACTIVITY_TIMEOUT,
                "heartbeat_interval": UserPresenceService.HEARTBEAT_INTERVAL,
                "grace_period": UserPresenceService.DISCONNECT_GRACE_PERIOD
            })
        
        emit("presence_stats_response", response_data)
        
        logger.debug(f"Sent presence stats to user {current_user.id if current_user.is_authenticated else 'anonymous'}")
        
    except Exception as e:
        logger.error(f"Error getting presence stats: {e}")
        emit("error", {"message": "Error loading presence statistics"})

# ---------------------------------------------------------------------------
# Event: manual_cleanup
# ---------------------------------------------------------------------------

@socketio.on("manual_presence_cleanup")
def handle_manual_cleanup() -> None:
    """Admin-only: Manually trigger presence cleanup."""
    if not current_user.is_authenticated:
        emit("error", {"message": "Authentication required"})
        return
        
    # Check admin privileges
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        emit("error", {"message": "Admin privileges required"})
        return
        
    try:
        cleaned_count = presence_service.cleanup_stale_users()
        
        # Get updated stats after cleanup
        updated_stats = presence_service.get_presence_stats()
        users_list = presence_service.get_online_users(include_details=True)
        
        response_data = {
            "cleaned_count": cleaned_count,
            "new_active_count": updated_stats['online_users'],
            "timestamp": datetime.utcnow().isoformat(),
            "requested_by": current_user.id
        }
        
        emit("manual_cleanup_complete", response_data)
        emit("online_users_update", users_list, broadcast=True)
        
        logger.info(f"Manual cleanup completed by admin {current_user.id}: {cleaned_count} users cleaned")
        
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
        emit("error", {"message": "Cleanup operation failed"})

# ---------------------------------------------------------------------------
# Event: ping_user
# ---------------------------------------------------------------------------

@socketio.on("ping_user")
def handle_ping_user(data=None) -> None:
    """Admin-only: Send a ping to a specific user to test connectivity."""
    if not current_user.is_authenticated:
        emit("error", {"message": "Authentication required"})
        return
        
    # Check admin privileges
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        emit("error", {"message": "Admin privileges required"})
        return
        
    if not data or 'user_id' not in data:
        emit("error", {"message": "User ID required"})
        return
        
    try:
        target_user_id = int(data['user_id'])
        
        # Get user status first
        user_status = presence_service.get_user_status(target_user_id)
        
        if not user_status or not user_status.get('is_online'):
            emit("ping_result", {
                "user_id": target_user_id,
                "success": False,
                "message": "User is not online",
                "timestamp": datetime.utcnow().isoformat()
            })
            return
        
        # Send ping to specific user (by user rooms if implemented)
        # For now, just log the ping attempt
        ping_data = {
            "type": "admin_ping",
            "from_admin": current_user.id,
            "message": data.get('message', 'Admin connectivity test'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # TODO: Implement user-specific room targeting
        # emit("admin_ping", ping_data, room=f"user_{target_user_id}")
        
        emit("ping_result", {
            "user_id": target_user_id,
            "success": True,
            "message": "Ping sent successfully",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Admin {current_user.id} pinged user {target_user_id}")
        
    except (ValueError, TypeError):
        emit("error", {"message": "Invalid user ID"})
    except Exception as e:
        logger.error(f"Error pinging user: {e}")
        emit("error", {"message": "Ping operation failed"}) 

@socketio.on("ping")
def handle_ping(data=None) -> None:
    """Handle ping for latency testing."""
    emit("pong", {
        "timestamp": datetime.utcnow().isoformat(),
        "received": True
    })

# ---------------------------------------------------------------------------
# Chat Events
# ---------------------------------------------------------------------------

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle chat messages"""
    try:
        user = get_current_user_from_socket()
        if not user:
            return
        
        message_data = {
            'id': str(uuid.uuid4()),
            'text': data.get('text', ''),
            'username': user.get('username', 'Unknown'),
            'timestamp': data.get('timestamp', int(time.time() * 1000)),
            'user_id': user.get('id')
        }
        
        # Broadcast to all connected clients
        emit('chat_message', message_data, broadcast=True)
        logger.info(f"Chat message from {user.get('username')}: {data.get('text', '')[:50]}...")
        
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        emit('error', {'message': 'Failed to send message'})

@socketio.on('user_typing')
def handle_user_typing(data):
    """Handle user typing indicator"""
    try:
        user = get_current_user_from_socket()
        if not user:
            return
        
        typing_data = {
            'username': user.get('username', 'Unknown'),
            'user_id': user.get('id')
        }
        
        # Broadcast to all other clients
        emit('user_typing', typing_data, broadcast=True, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling user typing: {e}")

@socketio.on('user_stopped_typing')
def handle_user_stopped_typing(data):
    """Handle user stopped typing indicator"""
    try:
        user = get_current_user_from_socket()
        if not user:
            return
        
        typing_data = {
            'username': user.get('username', 'Unknown'),
            'user_id': user.get('id')
        }
        
        # Broadcast to all other clients
        emit('user_stopped_typing', typing_data, broadcast=True, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling user stopped typing: {e}") 