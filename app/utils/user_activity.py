from flask import request
from flask_login import current_user
from app.models.base import Activity, User, db
from extensions import socketio
from datetime import datetime
import logging

# Import the UserPresenceService
from app.services.user_presence import UserPresenceService

logger = logging.getLogger(__name__)

# Global presence service instance
_presence_service = None

def get_presence_service():
    """Get or create the presence service instance."""
    global _presence_service
    if _presence_service is None:
        _presence_service = UserPresenceService()
    return _presence_service

def update_user_status(user_id, online: bool = True):
    """Update a user's online status using the comprehensive presence service."""
    try:
        presence_service = get_presence_service()
        
        if online:
            # Gather session metadata for login
            session_data = {
                'ip_address': request.environ.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
                'login_time': datetime.utcnow().isoformat(),
                'login_method': 'web'
            }
            
            success = presence_service.mark_user_online(user_id, session_data)
            if success:
                logger.info(f"Successfully marked user {user_id} online via auth login")
            else:
                logger.warning(f"Failed to mark user {user_id} online via auth login")
                # Fallback to basic database update
                _fallback_user_status_update(user_id, online=True)
        else:
            # Mark user offline immediately for logout
            success = presence_service.mark_user_offline(user_id, immediate=True)
            if success:
                logger.info(f"Successfully marked user {user_id} offline via auth logout")
            else:
                logger.warning(f"Failed to mark user {user_id} offline via auth logout")
                # Fallback to basic database update
                _fallback_user_status_update(user_id, online=False)
                
        # Always emit updated user list
        emit_online_users()
        
    except Exception as e:
        logger.error(f"Error updating user status via presence service: {e}")
        # Fallback to basic database update
        _fallback_user_status_update(user_id, online)

def _fallback_user_status_update(user_id, online: bool):
    """Fallback function for basic database user status update."""
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for fallback status update")
            return

        user.is_online = online
        if online:
            user.last_seen = datetime.utcnow()

        db.session.commit()
        logger.info(f"Fallback: Updated user {user_id} status to {'online' if online else 'offline'}")
        
    except Exception as e:
        logger.error(f"Error in fallback user status update: {e}")
        db.session.rollback()

def emit_online_users():
    """Emit list of online users using the presence service."""
    try:
        presence_service = get_presence_service()
        
        # Get comprehensive user list from presence service
        user_list = presence_service.get_online_users(include_details=True)
        
        # Also get presence statistics
        stats = presence_service.get_presence_stats()
        
        # Emit both the user list and stats
        socketio.emit('online_users_update', user_list)
        socketio.emit('presence_stats_update', {
            'active_users': stats.get('online_users', 0),  # Fix: use 'online_users' key from stats
            'total_users': stats.get('total_users', 0),
            'last_cleanup': stats.get('last_cleanup', datetime.utcnow().isoformat()),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.debug(f"Emitted online users list: {len(user_list)} users, {stats.get('online_users', 0)} active")
        
    except Exception as e:
        logger.error(f"Error emitting online users via presence service: {e}")
        # Fallback to basic database query
        _fallback_emit_online_users()

def _fallback_emit_online_users():
    """Fallback function for basic online users emission."""
    try:
        online_users = User.query.filter_by(is_online=True).all()
        user_list = [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_online': user.is_online,
            'last_seen': user.last_seen.isoformat() if user.last_seen else None,
            'role': user.role if hasattr(user, 'role') else 'user',
            'profile_picture': user.profile_picture if hasattr(user, 'profile_picture') else None,
            'last_seen_human': _format_last_seen_human(user.last_seen) if user.last_seen else 'Never'
        } for user in online_users]
        
        socketio.emit('online_users_update', user_list)
        logger.info(f"Fallback: Emitted {len(user_list)} online users")
        
    except Exception as e:
        logger.error(f"Error in fallback online users emission: {e}")

def _format_last_seen_human(last_seen):
    """Format last seen timestamp in human-readable format."""
    if not last_seen:
        return "Never"
    
    try:
        now = datetime.utcnow()
        diff = now - last_seen
        
        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(diff.total_seconds() / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception:
        return "Unknown"

def log_user_activity():
    """Log user activity and update heartbeat (enhanced with comprehensive tracking)."""
    if current_user.is_authenticated:
        try:
            # Skip logging for static files and API endpoints
            if request.path.startswith(('/static/', '/api/', '/assets/')):
                return
                
            # Update heartbeat via presence service for activity tracking
            presence_service = get_presence_service()
            heartbeat_success = presence_service.update_heartbeat(current_user.id)
            
            if not heartbeat_success:
                logger.warning(f"Failed to update heartbeat for user {current_user.id} during activity logging")
            
            # Enhanced activity tracking based on request path and method
            action = determine_activity_action(request)
            details = determine_activity_details(request)
            
            # Log activity
            activity = Activity(
                user_id=current_user.id,
                action=action,
                details=details
            )
            db.session.add(activity)
            db.session.commit()
            
            # Emit real-time update for admin dashboard
            try:
                from extensions import socketio
                socketio.emit('activity_update', {
                    'id': activity.id,
                    'type': action,
                    'description': details,
                    'timestamp': activity.timestamp.isoformat(),
                    'user': {
                        'id': current_user.id,
                        'name': current_user.username,
                        'profile_picture': current_user.profile_picture or 'boy.png'
                    }
                }, namespace='/')
            except Exception as emit_error:
                logger.debug(f"Could not emit activity update: {emit_error}")
            
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
            db.session.rollback()

def determine_activity_action(request):
    """Determine the appropriate action type based on the request."""
    path = request.path.lower()
    method = request.method.upper()
    
    # Page views
    if method == 'GET' and not path.startswith('/api/'):
        return 'page_view'
    
    # API actions
    if path.startswith('/api/'):
        if 'outage' in path:
            if method == 'POST':
                return 'outage_created'
            elif method == 'PUT':
                return 'outage_updated'
            elif method == 'DELETE':
                return 'outage_deleted'
        elif 'user' in path:
            return 'user_management'
        elif 'search' in path:
            return 'search'
        elif 'upload' in path:
            return 'file_upload'
        elif 'settings' in path:
            return 'settings_changed'
    
    # Form submissions
    if method == 'POST':
        if 'login' in path:
            return 'login'
        elif 'logout' in path:
            return 'logout'
        elif 'search' in path:
            return 'search'
        elif 'upload' in path:
            return 'file_upload'
    
    # Default action
    return 'page_view'

def determine_activity_details(request):
    """Determine detailed description of the activity."""
    path = request.path
    method = request.method.upper()
    
    # Enhanced path descriptions
    path_descriptions = {
        '/': 'Visited Home Dashboard',
        '/offices': 'Viewed Offices Directory',
        '/workstations': 'Viewed Workstations',
        '/users': 'Viewed Users Management',
        '/notes': 'Viewed Notes',
        '/kb': 'Viewed Knowledge Base',
        '/unified': 'Used Unified Search',
        '/outages': 'Viewed Outages',
        '/menu': 'Viewed Menu',
        '/tracking': 'Viewed Tracking',
        '/fax2mail': 'Viewed Fax2Mail',
        '/scan': 'Used Network Scanner',
        '/agent': 'Viewed Agent',
        '/lab': 'Viewed Lab',
        '/oralyzer': 'Viewed Oralyzer',
        '/profile': 'Viewed Profile',
        '/settings': 'Viewed Settings',
        '/api/admin/dashboard': 'Viewed Admin Dashboard',
        '/api/admin/outages': 'Viewed Outage Management',
        '/api/admin/users': 'Viewed User Management',
        '/api/admin/activity': 'Viewed Activity Log',
    }
    
    # Return friendly description if available
    if path in path_descriptions:
        return path_descriptions[path]
    
    # For API calls, provide more specific details
    if path.startswith('/api/'):
        if 'outage' in path:
            if method == 'POST':
                return 'Created new outage'
            elif method == 'PUT':
                return 'Updated outage'
            elif method == 'DELETE':
                return 'Deleted outage'
        elif 'search' in path:
            return 'Performed search'
        elif 'upload' in path:
            return 'Uploaded file'
        elif 'settings' in path:
            return 'Changed settings'
    
    # For form submissions
    if method == 'POST':
        if 'login' in path:
            return 'Logged in'
        elif 'logout' in path:
            return 'Logged out'
        elif 'search' in path:
            return 'Performed search'
        elif 'upload' in path:
            return 'Uploaded file'
    
    # Default fallback
    return f"Visited {path}"

def track_specific_activity(user_id, action, details=None):
    """Track a specific user activity."""
    try:
        activity = Activity(
            user_id=user_id,
            action=action,
            details=details or '',
            timestamp=datetime.utcnow()
        )
        
        db.session.add(activity)
        db.session.commit()
        
        # Emit real-time update
        try:
            from extensions import socketio
            from app.models import User
            
            user = User.query.get(user_id)
            if user:
                socketio.emit('activity_update', {
                    'id': activity.id,
                    'type': action,
                    'description': details or '',
                    'timestamp': activity.timestamp.isoformat(),
                    'user': {
                        'id': user.id,
                        'name': user.username,
                        'profile_picture': user.profile_picture or 'boy.png'
                    }
                }, namespace='/')
        except Exception as emit_error:
            logger.debug(f"Could not emit activity update: {emit_error}")
        
        return activity
        
    except Exception as e:
        logger.error(f"Error tracking specific activity: {e}")
        db.session.rollback()
        return None

def force_user_offline(user_id: int) -> bool:
    """Admin function to force a user offline immediately."""
    try:
        presence_service = get_presence_service()
        success = presence_service.force_user_offline(user_id)
        
        if success:
            emit_online_users()  # Broadcast updated list
            logger.info(f"Successfully forced user {user_id} offline")
        else:
            logger.warning(f"Failed to force user {user_id} offline")
            
        return success
        
    except Exception as e:
        logger.error(f"Error forcing user {user_id} offline: {e}")
        return False

def cleanup_stale_users() -> int:
    """Admin function to cleanup stale user presence."""
    try:
        presence_service = get_presence_service()
        cleaned_count = presence_service.cleanup_stale_users()
        
        if cleaned_count > 0:
            emit_online_users()  # Broadcast updated list
            logger.info(f"Cleaned up {cleaned_count} stale users")
            
        return cleaned_count
        
    except Exception as e:
        logger.error(f"Error during stale user cleanup: {e}")
        return 0

def get_user_presence_status(user_id: int) -> dict:
    """Get detailed presence status for a specific user."""
    try:
        presence_service = get_presence_service()
        return presence_service.get_user_status(user_id)
        
    except Exception as e:
        logger.error(f"Error getting presence status for user {user_id}: {e}")
        return {}

def get_presence_statistics() -> dict:
    """Get comprehensive presence statistics."""
    try:
        presence_service = get_presence_service()
        return presence_service.get_presence_stats()
        
    except Exception as e:
        logger.error(f"Error getting presence statistics: {e}")
        return {
            'active_users': 0,
            'total_users': 0,
            'last_cleanup': datetime.utcnow().isoformat()
        }

def initialize_presence_service(app):
    """Initialize the presence service with Flask app context."""
    try:
        presence_service = get_presence_service()
        presence_service.set_app_context(app)
        logger.info("Presence service initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing presence service: {e}") 