import logging
from datetime import datetime
from flask import current_app
from flask_login import current_user
from flask_socketio import emit
from app import socketio, db
from app.models import User
from . import bp

# Import private messages socket handlers
from app.socket_handlers.private_messages import *

logger = logging.getLogger(__name__)

def emit_online_users():
    try:
        online_users = User.query.filter_by(is_online=True).all()
        user_data = [{
            'id': user.id,
            'name': user.username,
            'email': user.email,
            'role': user.role,
            'last_seen': user.last_seen.isoformat() if user.last_seen else None,
            'profile_picture': user.profile_picture or 'boy.png'
        } for user in online_users]
        socketio.emit('online_users_update', user_data)
    except Exception as e:
        logger.error(f"Error emitting online users: {str(e)}")

# Note: Heartbeat handler moved to admin_presence.py to avoid conflicts
# This handler is now handled by the more comprehensive version in admin_presence.py

@socketio.on('app_status')
def handle_app_status(data):
    """Handle app status updates"""
    try:
        if current_user.is_authenticated and current_user.is_admin:
            logger.debug(f"Admin status update: {data}")
        else:
            logger.warning("Unauthorized status update attempt")
    except Exception as e:
        logger.warning(f"App status handler error: {e}")

def background_status_emitter():
    """Wrapper that delegates to the relocated implementation in utils."""
    from app.utils.status_emitter import background_status_emitter as _background_status_emitter
    return _background_status_emitter() 