import os
import sys
import signal
from pathlib import Path

# Clean up problematic environment variables that can cause reload issues
problematic_vars = [
    'WERKZEUG_SERVER_FD', 'WERKZEUG_RUN_FD', 'FLASK_RUN_FD',
    'EVENTLET_THREADPOOL_SIZE', 'GEVENT_THREADPOOL_SIZE'
]
for var in problematic_vars:
    if var in os.environ:
        os.environ.pop(var, None)

# Clean up ALL Werkzeug environment variables
werkzeug_vars = [k for k in os.environ.keys() if k.startswith('WERKZEUG_')]
for var in werkzeug_vars:
    os.environ.pop(var, None)

# Set environment for development mode
# Only disable reloader if explicitly requested
if os.getenv('WERKZEUG_DISABLE_RELOADER') != '1':
    os.environ['FLASK_ENV'] = 'development'

# Ensure the parent directory (containing both YAM and app) is in sys.path
current_dir = Path(__file__).parent.resolve()
project_root = current_dir.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, jsonify, request, render_template, send_from_directory, redirect, url_for, session
from flask_cors import CORS
from datetime import datetime, timedelta
import time
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up paths for static and template folders
current_dir = Path(__file__).parent.resolve()
app_dir = (current_dir.parent / 'app').resolve()

yam_app = Flask(__name__,
            template_folder=str(app_dir / 'templates'),
            static_folder=str(app_dir / 'static'))

# Enhanced Configuration with robust session management
yam_app.config['SECRET_KEY'] = 'server-key-2025'
yam_app.config['JSON_AS_ASCII'] = False
yam_app.config['SESSION_TYPE'] = 'filesystem'
yam_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30 minutes as requested
yam_app.config['SESSION_FILE_THRESHOLD'] = 1000
yam_app.config['SESSION_REFRESH_EACH_REQUEST'] = True
yam_app.config['SESSION_COOKIE_HTTPONLY'] = True
yam_app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
yam_app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
yam_app.config['SESSION_COOKIE_NAME'] = 'yam_session'  # Custom session cookie name

# Configure auto-reload based on debug mode
debug_mode = os.getenv('FLASK_DEBUG', '0') == '1' or os.getenv('FLASK_ENV') == 'development'
yam_app.config['TEMPLATES_AUTO_RELOAD'] = debug_mode
yam_app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 if debug_mode else 31536000  # 1 year for production
yam_app.jinja_env.auto_reload = debug_mode
yam_app.jinja_env.cache_size = 0 if debug_mode else 50

# Ensure session directory exists
session_dir = Path(app_dir.parent / 'sessions')
session_dir.mkdir(exist_ok=True)
yam_app.config['SESSION_FILE_DIR'] = str(session_dir)

# Enable CORS
CORS(yam_app)

# Import config and extensions
from app.config import Config
from extensions import db, login_manager, socketio, migrate
from app.models import User

yam_app.config.from_object(Config)

# Override session lifetime to 2 hours for better stability
yam_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Initialize extensions
db.init_app(yam_app)
login_manager.init_app(yam_app)
socketio.init_app(yam_app)
migrate.init_app(yam_app, db)

# Add template context processor to make hasattr available in templates
@yam_app.context_processor
def inject_template_globals():
    """Inject global functions and variables into template context."""
    return {
        'hasattr': hasattr,
        'getattr': getattr,
        'isinstance': isinstance,
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'set': set,
        'bool': bool,
        'type': type,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sorted': sorted,
        'reversed': reversed,
        'min': min,
        'max': max,
        'sum': sum,
        'abs': abs,
        'round': round,
        'divmod': divmod,
        'pow': pow,
        'all': all,
        'any': any,
        'chr': chr,
        'ord': ord,
        'hex': hex,
        'oct': oct,
        'bin': bin,
        'format': format,
        'repr': repr,
        'ascii': ascii,
        'hash': hash,
        'id': id,
        'callable': callable,
        'issubclass': issubclass,
        'super': super,
        'property': property,
        'staticmethod': staticmethod,
        'classmethod': classmethod,
        'vars': vars,
        'dir': dir,
        'globals': globals,
        'locals': locals,
        'breakpoint': breakpoint,
        'compile': compile,
        'eval': eval,
        'exec': exec,
        'open': open,
        'print': print,
        'input': input,
        'help': help,
        'copyright': copyright,
        'credits': credits,
        'license': license,
        'exit': exit,
        'quit': quit
    }

# Setup authentication middleware
try:
    from app.utils.auth_middleware import setup_auth_middleware
    setup_auth_middleware(yam_app)
    logger.info("Authentication middleware setup completed")
except Exception as e:
    logger.error(f"Failed to setup authentication middleware: {e}")

# Enhanced model registration with conflict resolution
def ensure_model_registration_safe():
    """Safely ensure all models are properly registered with conflict resolution."""
    try:
        with yam_app.app_context():
            # Clear any existing model registrations that might cause conflicts
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            # Force re-registration of all models
            db.Model.metadata.create_all(db.engine, checkfirst=True)
            
            # Specifically handle SearchHistory conflicts
            try:
                from app.models import resolve_searchhistory_conflicts
                resolve_searchhistory_conflicts()
            except Exception as e:
                logger.warning(f"SearchHistory table creation warning: {e}")
            
            logger.info("Model registration completed successfully")
            return True
    except Exception as e:
        logger.error(f"Model registration failed: {e}")
        return False

# Initialize models safely
try:
    with yam_app.app_context():
        from app.models import cleanup_model_registry, ensure_model_registration, resolve_searchhistory_conflicts
        cleanup_model_registry()
        ensure_model_registration()
        resolve_searchhistory_conflicts()
        logger.info("YAM Server: Model registration verified")
except Exception as e:
    logger.error(f"YAM Server: Model registration check failed: {e}")

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize SocketIO properly with enhanced session handling
socketio.init_app(
    yam_app, 
    cors_allowed_origins="*", 
    async_mode='threading', 
    logger=False, 
    engineio_logger=False,
    ping_interval=120000,  # Increased to 2 minutes for better stability
    ping_timeout=30000,   # Increased to 30 seconds to prevent premature disconnects
    max_http_buffer_size=1e6,  # 1MB
    transports=['polling', 'websocket'],  # Allow both transports
    cookie='yam_session',  # Use same cookie name as Flask session
    always_connect=True,   # Always allow connections
    reconnection=True,     # Enable reconnection
    reconnection_attempts=10,  # Allow 10 reconnection attempts
    reconnection_delay=2000,  # 2 second initial delay
    reconnection_delay_max=30000,  # Max 30 second delay
)

# Connection deduplication to prevent multiple connections from same user
active_connections = {}

@login_manager.user_loader
def load_user(user_id):
    """Load user with session hydration and connection error handling."""
    try:
        # Add connection retry logic
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                user = db.session.get(User, int(user_id))
                if user:
                    # Hydrate session with user data
                    session['user_id'] = user.id
                    session['username'] = user.username
                    session['last_activity'] = datetime.utcnow().isoformat()
                    session.permanent = True
                return user
            except Exception as db_error:
                if "QueuePool limit" in str(db_error) and attempt < max_retries - 1:
                    # Database connection pool exhausted, wait and retry
                    import time
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    # Re-raise the error if it's not a connection issue or we've exhausted retries
                    raise db_error
                    
    except Exception as e:
        # Only log the error once per minute to prevent spam
        current_time = datetime.utcnow()
        last_error_time = getattr(load_user, '_last_error_time', None)
        
        if not last_error_time or (current_time - last_error_time).total_seconds() > 60:
            logger.error(f"Error loading user {user_id}: {e}")
            load_user._last_error_time = current_time
        
        return None

# Session management utilities
def hydrate_session(user):
    """Hydrate session with user data and ensure it stays active."""
    try:
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['last_activity'] = datetime.utcnow().isoformat()
        session['session_start'] = datetime.utcnow().isoformat()
        session['request_count'] = session.get('request_count', 0) + 1
        return True
    except Exception as e:
        logger.error(f"Error hydrating session: {e}")
        return False

def check_session_health():
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
        if time_diff > timedelta(minutes=30):
            logger.warning(f"Session expired for user {session.get('user_id')}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking session health: {e}")
        return False

def get_session_time_remaining():
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
        
        # Calculate time remaining (2 hours)
        time_diff = datetime.utcnow() - last_activity
        remaining = timedelta(hours=2) - time_diff
        
        return max(0, int(remaining.total_seconds()))
    except Exception as e:
        logger.error(f"Error calculating session time remaining: {e}")
        return 0

def cleanup_stale_sessions():
    """Clean up stale sessions and mark inactive users offline."""
    try:
        from app.services.user_presence import presence_service
        
        # Clean up stale sessions using presence service
        cleaned_count = presence_service.cleanup_stale_users()
        
        # Clean up session files
        session_dir = Path(app_dir.parent / 'sessions')
        if session_dir.exists():
            current_time = datetime.utcnow()
            session_files = list(session_dir.glob('user_*.json'))
            
            for session_file in session_files:
                try:
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if current_time - file_mtime > timedelta(minutes=30):
                        session_file.unlink()
                        logger.debug(f"Cleaned up stale session file: {session_file.name}")
                except Exception as e:
                    logger.warning(f"Error cleaning up session file {session_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale sessions")
            
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")

# Socket.IO event handlers for better session management
@socketio.on('connect')
def handle_socket_connect():
    """Handle Socket.IO connection with session validation and presence tracking."""
    try:
        # Get connection metadata
        connection_id = request.args.get('connection_id', 'unknown')
        timestamp = request.args.get('timestamp', 'unknown')
        
        # Log connection attempt
        logger.info(f"Socket.IO connection attempt - SID: {request.sid}, Connection ID: {connection_id}")
        
        # Check for duplicate connections from same user
        user_id = session.get('user_id')
        if user_id and user_id in active_connections:
            # Disconnect existing connection to prevent duplicates
            old_sid = active_connections[user_id]
            try:
                socketio.disconnect(old_sid)
                logger.info(f"Disconnected duplicate connection for user {user_id} (old SID: {old_sid})")
            except Exception as e:
                logger.warning(f"Failed to disconnect duplicate connection: {e}")
        
        # Always allow connections - don't reject based on session state
        # This prevents random disconnections due to session validation issues
        
        # Update session activity if user is authenticated
        if session.get('user_id'):
            session['last_activity'] = datetime.utcnow().isoformat()
            session['socket_connected'] = True
            session['socket_id'] = request.sid
            session['connection_count'] = session.get('connection_count', 0) + 1
            session['connection_id'] = connection_id
            
            # Track active connection
            active_connections[user_id] = request.sid
            
            # Mark user as online using presence service
            try:
                from app.services.user_presence import presence_service
                from app.utils.user_activity import emit_online_users
                
                user_id = session.get('user_id')
                if user_id:
                    # Gather session metadata
                    session_data = {
                        'ip_address': request.environ.get('REMOTE_ADDR', 'unknown'),
                        'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
                        'connection_time': datetime.utcnow().isoformat(),
                        'socket_id': request.sid,
                        'connection_id': connection_id,
                        'login_method': 'socket_connect'
                    }
                    
                    # Mark user as online
                    success = presence_service.handle_socket_connect(user_id, session_data)
                    if success:
                        logger.info(f"Socket.IO connected for user {user_id} (SID: {request.sid}, Connection ID: {connection_id})")
                        # Emit updated online users list
                        emit_online_users()
                    else:
                        logger.warning(f"Failed to mark user {user_id} online via socket connect")
                else:
                    logger.info(f"Socket.IO connected for user {session.get('user_id')} (SID: {request.sid}, Connection ID: {connection_id})")
                    
            except Exception as e:
                logger.error(f"Error in presence service during socket connect: {e}")
                # Continue with basic session update even if presence service fails
        else:
            # Anonymous connection - still log it but don't reject
            logger.info(f"Socket.IO anonymous connection (SID: {request.sid}, Connection ID: {connection_id})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in Socket.IO connect handler: {e}")
        # Don't reject connection on error, just log it and allow connection
        return True

@socketio.on('disconnect')
def handle_socket_disconnect():
    """Handle Socket.IO disconnection with presence tracking."""
    try:
        # Always log disconnect but handle gracefully
        disconnect_reason = getattr(request, 'disconnect_reason', 'unknown')
        logger.info(f"Socket.IO disconnect (SID: {request.sid}, Reason: {disconnect_reason})")
        
        # Clean up active connections tracking
        user_id = session.get('user_id')
        if user_id and user_id in active_connections:
            if active_connections[user_id] == request.sid:
                del active_connections[user_id]
                logger.info(f"Cleaned up active connection for user {user_id}")
        
        if session.get('user_id'):
            session['socket_connected'] = False
            session['last_activity'] = datetime.utcnow().isoformat()
            session['disconnect_time'] = datetime.utcnow().isoformat()
            session['disconnect_reason'] = disconnect_reason
            
            # Mark user as offline using presence service with extended grace period
            try:
                from app.services.user_presence import presence_service
                from app.utils.user_activity import emit_online_users
                
                user_id = session.get('user_id')
                if user_id:
                    # Use extended grace period to prevent premature offline marking
                    # This helps with temporary network issues or page refreshes
                    success = presence_service.handle_socket_disconnect(user_id)
                    if success:
                        logger.info(f"Socket.IO disconnected for user {user_id} (SID: {request.sid})")
                        # Emit updated online users list
                        emit_online_users()
                    else:
                        logger.warning(f"Failed to mark user {user_id} offline via socket disconnect")
                else:
                    logger.info(f"Socket.IO disconnected for user {session.get('user_id')} (SID: {request.sid})")
                    
            except Exception as e:
                logger.error(f"Error in presence service during socket disconnect: {e}")
                # Continue with basic session update even if presence service fails
        else:
            # Anonymous disconnect - just log it
            logger.info(f"Socket.IO anonymous disconnect (SID: {request.sid})")
        
    except Exception as e:
        logger.error(f"Error in Socket.IO disconnect handler: {e}")
        # Don't crash on disconnect errors

@socketio.on('heartbeat')
def handle_heartbeat(data=None):
    """Handle heartbeat to keep session alive and update presence."""
    try:
        if session.get('user_id'):
            session['last_activity'] = datetime.utcnow().isoformat()
            session['heartbeat_count'] = session.get('heartbeat_count', 0) + 1
            
            # Update presence heartbeat
            try:
                from app.services.user_presence import presence_service
                from app.utils.user_activity import emit_online_users
                
                user_id = session.get('user_id')
                if user_id:
                    success = presence_service.update_heartbeat(user_id)
                    if success:
                        # Emit updated online users list periodically
                        if session.get('heartbeat_count', 0) % 10 == 0:  # Every 10 heartbeats
                            emit_online_users()
                    else:
                        logger.warning(f"Failed to update heartbeat for user {user_id}")
                        
            except Exception as e:
                logger.error(f"Error in presence service during heartbeat: {e}")
                # Continue with basic session update even if presence service fails
            
            from flask_socketio import emit
            emit('heartbeat_ack', {'timestamp': datetime.utcnow().isoformat()})
        else:
            # Allow heartbeat for anonymous connections too
            from flask_socketio import emit
            emit('heartbeat_ack', {'timestamp': datetime.utcnow().isoformat(), 'anonymous': True})
    except Exception as e:
        logger.error(f"Error in heartbeat handler: {e}")

# Add presence-related Socket.IO events
@socketio.on('get_online_users')
def handle_get_online_users():
    """Return current online users list."""
    try:
        from app.services.user_presence import presence_service
        from flask_socketio import emit
        
        users_list = presence_service.get_online_users(include_details=True)
        presence_stats = presence_service.get_presence_stats()
        
        response_data = {
            "users": users_list,
            "stats": {
                "total_online": presence_stats.get('online_users', 0),
                "total_users": presence_stats.get('total_users', 0),
                "last_cleanup": presence_stats.get('last_cleanup', datetime.utcnow().isoformat())
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        emit("online_users_update", users_list)
        emit("presence_stats", response_data)
        
        logger.debug(f"Sent online users list: {len(users_list)} users")
        
    except Exception as e:
        logger.error(f"Error getting online users: {e}")
        from flask_socketio import emit
        emit("error", {"message": "Error loading online users"})

@socketio.on('admin_dashboard_request')
def handle_admin_dashboard_request():
    """Return an aggregated admin-dashboard payload and mark caller online."""
    try:
        from app.services.user_presence import presence_service
        from app.models import Outage
        from flask_socketio import emit
        
        # Mark the requesting user online (if authenticated)
        if session.get('user_id'):
            success = presence_service.update_heartbeat(session.get('user_id'))
            if not success:
                logger.warning(f"Failed to update heartbeat for user {session.get('user_id')} in dashboard request")

        # Gather stats for the dashboard using presence service
        users_list = presence_service.get_online_users(include_details=True)
        presence_stats = presence_service.get_presence_stats()
        
        active_sessions = presence_stats.get('online_users', 0)
        total_users = presence_stats.get('total_users', 0)
        
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
                "last_cleanup": presence_stats.get('last_cleanup', datetime.utcnow().isoformat()),
                "stale_threshold": presence_service.ACTIVITY_TIMEOUT,
                "heartbeat_interval": presence_service.HEARTBEAT_INTERVAL,
                "average_session_duration": presence_stats.get('average_session_duration', 0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        emit("admin_dashboard_response", dashboard_data)
        logger.debug(f"Sent admin dashboard data: {len(users_list)} users, {active_sessions} active")
        
    except Exception as e:
        logger.error(f"Error in admin dashboard request: {e}")
        from flask_socketio import emit
        emit("error", {"message": "Error loading dashboard data"})

@socketio.on('request_dashboard_data')
def handle_dashboard_data_request(data):
    """Handle real-time dashboard data requests."""
    try:
        from flask_login import current_user
        from flask_socketio import emit
        
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        components = data.get('components', [])
        response_data = {}
        
        # Gather data for requested components
        if 'quick_stats' in components:
            response_data['quick_stats'] = get_quick_stats_data()
            
        if 'user_analytics' in components:
            response_data['user_analytics'] = get_user_analytics_data(current_user)
            
        if 'system_health' in components:
            response_data['system_health'] = get_system_health_data()
            
        if 'notifications' in components:
            response_data['notifications'] = get_notifications_data(current_user)
        
        # Emit dashboard data
        emit('dashboard_update', {
            'components': response_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in dashboard data request handler: {e}")
        emit('error', {'message': 'Failed to gather dashboard data'})

@socketio.on('heartbeat_ack')
def handle_heartbeat_ack(data):
    """Handle heartbeat acknowledgment."""
    try:
        from flask_login import current_user
        if current_user.is_authenticated:
            # Update session activity
            session['last_activity'] = datetime.utcnow().isoformat()
            
            # Update user presence
            try:
                from app.services.user_presence import presence_service
                presence_service.update_heartbeat(current_user.id)
            except Exception as e:
                logger.debug(f"Could not update user presence: {e}")
                
    except Exception as e:
        logger.error(f"Error in heartbeat ack handler: {e}")

def get_quick_stats_data():
    """Get quick stats data for real-time updates."""
    try:
        from app.models import User
        from app.services.user_presence import presence_service
        
        online_users = presence_service.get_online_users()
        
        return {
            'online_users': len(online_users),
            'total_users': User.query.count(),
            'system_uptime': get_system_uptime(),
            'active_sessions': len(active_connections)
        }
    except Exception as e:
        logger.error(f"Error getting quick stats data: {e}")
        return {}

def get_user_analytics_data(user):
    """Get user analytics data for real-time updates."""
    try:
        return {
            'user_id': user.id,
            'username': user.username,
            'last_seen': user.last_seen.isoformat() if user.last_seen else None,
            'session_healthy': check_session_health(),
            'time_remaining': get_session_time_remaining()
        }
    except Exception as e:
        logger.error(f"Error getting user analytics data: {e}")
        return {}

def get_system_health_data():
    """Get system health data for real-time updates."""
    try:
        import psutil
        
        return {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_status': 'online',
            'database_status': 'connected'
        }
    except Exception as e:
        logger.error(f"Error getting system health data: {e}")
        return {}

def get_notifications_data(user):
    """Get notifications data for real-time updates."""
    try:
        # This would typically come from a notifications service
        return {
            'count': 0,
            'notifications': []
        }
    except Exception as e:
        logger.error(f"Error getting notifications data: {e}")
        return {}

def get_system_uptime():
    """Get system uptime."""
    try:
        import psutil
        uptime_seconds = time.time() - psutil.boot_time()
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    except Exception as e:
        logger.error(f"Error getting system uptime: {e}")
        return "Unknown"

# Service worker route
@yam_app.route('/sw.js')
def service_worker():
    """Serve the service worker file."""
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# Before request handler for session management
@yam_app.before_request
def before_request_handler():
    """Handle session management before each request."""
    try:
        # Clean up stale sessions periodically
        if not hasattr(yam_app, '_last_cleanup') or time.time() - yam_app._last_cleanup > 300:  # Every 5 minutes
            cleanup_stale_sessions()
            yam_app._last_cleanup = time.time()
        
        # Check session health for authenticated users
        if session.get('user_id'):
            if not check_session_health():
                # Session is stale, clear it
                session.clear()
                logger.info(f"Cleared stale session for user {session.get('user_id')}")
                return redirect(url_for('auth.login'))
            
            # Update session activity
            session['last_activity'] = datetime.utcnow().isoformat()
            session['request_count'] = session.get('request_count', 0) + 1
            
    except Exception as e:
        logger.error(f"Error in before_request handler: {e}")

def detect_client_type():
    """Detect if the request is from YAM client or web browser."""
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # Check for YAM client indicators
    yam_indicators = [
        'yam',
        'electron',
        'python-requests',
        'aiohttp',
        'requests',
        'yam-test-client'
    ]
    
    # Check for browser indicators
    browser_indicators = [
        'mozilla',
        'chrome',
        'safari',
        'firefox',
        'edge',
        'opera'
    ]
    
    # Check if it's a YAM client request
    for indicator in yam_indicators:
        if indicator in user_agent:
            return 'yam_client'
    
    # Check if it's a browser request
    for indicator in browser_indicators:
        if indicator in user_agent:
            return 'web_browser'
    
    # Check for API requests (Accept header)
    accept_header = request.headers.get('Accept', '')
    if 'application/json' in accept_header:
        return 'yam_client'
    
    # Check for specific test headers
    if request.headers.get('X-Test-Client') == 'true':
        return 'yam_client'
    
    # Check if the request path starts with /api/
    if request.path.startswith('/api/'):
        return 'yam_client'
    
    # Default to web browser for unknown clients
    return 'web_browser'

def is_yam_client_request():
    """Check if the current request is from the YAM client."""
    return detect_client_type() == 'yam_client'

def is_web_browser_request():
    """Check if the current request is from a web browser."""
    return detect_client_type() == 'web_browser'

# Root route is now handled by the main blueprint to prevent conflicts
# The main blueprint's index route handles both authenticated and unauthenticated users

@yam_app.route('/api/server-info')
def server_info():
    """Server information endpoint."""
    client_type = detect_client_type()
    
    response_data = {
        'success': True,
        'server': {
            'name': 'YAM Server',
            'version': '1.0.0',
            'type': 'yam',
            'startup_time': datetime.now().isoformat(),
            'status': 'running',
            'client_type': client_type,
            'dual_mode': True,
            'session_lifetime_minutes': 30
        },
        'timestamp': datetime.now().isoformat()
    }
    
    # Add client-specific information
    if client_type == 'yam_client':
        response_data['server']['mode'] = 'client_mode'
        response_data['server']['features'] = [
            'real_time_updates',
            'socket_io_support',
            'windows_auth',
            'auto_login',
            'session_hydration'
        ]
    else:
        response_data['server']['mode'] = 'web_mode'
        response_data['server']['features'] = [
            'web_interface',
            'responsive_design',
            'browser_compatibility',
            'session_management'
        ]
    
    return jsonify(response_data)

@yam_app.route('/auto-login')
def auto_login():
    """Auto-login endpoint for YAM client with enhanced session management."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        # YAM client auto-login logic
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                # Hydrate session for authenticated user
                hydrate_session(current_user)
                return jsonify({
                    'status': 'already_logged_in',
                    'user': current_user.username,
                    'client_type': 'yam_client',
                    'session_healthy': True,
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            # Check for existing session
            user_id = session.get('user_id')
            if user_id and check_session_health():
                try:
                    user = db.session.get(User, user_id)
                    if user:
                        from flask_login import login_user
                        login_user(user, remember=True)
                        hydrate_session(user)
                        return jsonify({
                            'status': 'auto_login_success',
                            'user': user.username,
                            'client_type': 'yam_client',
                            'redirect': url_for('main.index'),
                            'session_healthy': True,
                            'timestamp': datetime.now().isoformat()
                        }), 200
                except Exception as e:
                    logger.error(f"Auto-login failed for user {user_id}: {e}")
            
            return jsonify({
                'status': 'no_session',
                'client_type': 'yam_client',
                'redirect': url_for('auth.login'),
                'session_healthy': False,
                'timestamp': datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            logger.error(f"Auto-login error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to login page
        return redirect(url_for('auth.login'))

@yam_app.route('/quick-login-check')
def quick_login_check():
    """Quick login check endpoint with session health verification."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        session_healthy = check_session_health()
        return jsonify({
            'ready': True,
            'client_type': 'yam_client',
            'session_healthy': session_healthy,
            'timestamp': datetime.now().isoformat()
        }), 200
    else:
        # For web browsers, redirect to login
        return redirect(url_for('auth.login'))

@yam_app.route('/force-logout', methods=['GET', 'POST'])
def force_logout():
    """Force logout all users and redirect to login page."""
    try:
        from flask_login import current_user, logout_user
        from flask import make_response, redirect, url_for
        
        # Clear all session data
        session.clear()
        
        # Logout user if authenticated
        if current_user.is_authenticated:
            logout_user()
        
        # Clear all cookies
        response = make_response(redirect(url_for('auth.login', shutdown='true')))
        response.delete_cookie('session')
        response.delete_cookie('yam_session')
        response.delete_cookie('csrf_token')
        
        logger.info("[SECURITY] Force logout executed - all users logged out")
        return response
        
    except Exception as e:
        logger.error(f"Error in force logout: {e}")
        return redirect(url_for('auth.login', shutdown='true'))

@yam_app.route('/login-ready')
def login_ready_check():
    """Login ready check endpoint."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        return jsonify({
            'status': 'ready',
            'message': 'Login page is ready',
            'client_type': 'yam_client',
            'timestamp': int(time.time())
        }), 200
    else:
        # For web browsers, redirect to login
        return redirect(url_for('auth.login'))

@yam_app.route('/api/health')
def health_check():
    """Health check endpoint with session status."""
    client_type = detect_client_type()
    
    response_data = {
        'status': 'ok',
        'client_type': client_type,
        'session_healthy': check_session_health(),
        'timestamp': datetime.now().isoformat()
    }
    
    if client_type == 'yam_client':
        response_data['server_info'] = {
            'name': 'YAM Server',
            'version': '1.0.0',
            'type': 'yam',
            'dual_mode': True
        }
    
    return jsonify(response_data), 200

@yam_app.route('/api/system-status')
def system_status():
    """System status endpoint with enhanced session information."""
    client_type = detect_client_type()
    
    response_data = {
        'status': 'ok',
        'timestamp': time.time(),
        'server': {
            'name': 'YAM Server',
            'version': '1.0.0',
            'type': 'yam',
            'client_type': client_type,
            'dual_mode': True
        },
        'uptime_seconds': int(time.time() - getattr(yam_app, 'startup_time', time.time())),
        'electron_mode': client_type == 'yam_client',
        'flask_port': os.getenv('FLASK_PORT', '5000'),
        'session_info': {
            'lifetime_minutes': 30,
            'healthy': check_session_health(),
            'user_id': session.get('user_id'),
            'last_activity': session.get('last_activity')
        }
    }
    
    return jsonify(response_data), 200

@yam_app.route('/session-status')
def session_status():
    """Enhanced session status endpoint."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        session_healthy = check_session_health()
        return jsonify({
            'session_active': session.get('user_id') is not None,
            'user_authenticated': session.get('user_id') is not None,
            'session_healthy': session_healthy,
            'session_manager_active': True,
            'server_ready': True,
            'client_type': 'yam_client',
            'session_lifetime_minutes': 30,
            'last_activity': session.get('last_activity'),
            'timestamp': datetime.now().isoformat()
        }), 200
    else:
        # For web browsers, redirect to login if not authenticated
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                return redirect(url_for('main.index'))
            else:
                return redirect(url_for('auth.login'))
        except Exception as e:
            return redirect(url_for('auth.login'))

# Note: Root route (/) is handled by the main blueprint
# This prevents conflicts with the main blueprint's @login_required route

@yam_app.route('/app')
def app_route():
    """App route that handles both YAM client and web browser access with session management."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        # YAM client - return JSON response
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                hydrate_session(current_user)
                return jsonify({
                    'status': 'authenticated',
                    'user': current_user.username,
                    'redirect': url_for('main.index'),
                    'client_type': 'yam_client',
                    'session_healthy': True,
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'status': 'unauthenticated',
                    'redirect': url_for('auth.login'),
                    'client_type': 'yam_client',
                    'session_healthy': False,
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"App route error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'redirect': url_for('auth.login'),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to appropriate page
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                # User is authenticated, redirect to main page
                return redirect(url_for('main.index'))
            else:
                # User is not authenticated, redirect to login page
                return redirect(url_for('auth.login'))
        except Exception as e:
            # If there's any error, redirect to login page as fallback
            logger.error(f"Error in app route: {e}")
            return redirect(url_for('auth.login'))

@yam_app.route('/api/auth/windows-auth-status')
def windows_auth_status():
    """Windows authentication status endpoint for YAM client."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            import getpass
            import platform
            
            # Get Windows username
            windows_username = getpass.getuser().lower()
            
            # Check if user exists in database
            user = User.query.filter(db.func.lower(User.windows_username) == windows_username).first()
            
            if user:
                return jsonify({
                    'success': True,
                    'status': {
                        'is_authorized': True,
                        'status': 'authorized',
                        'message': f'User {windows_username} is authorized',
                        'windows_username': windows_username,
                        'user_id': user.id,
                        'username': user.username,
                        'email': user.email
                    },
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'status': {
                        'is_authorized': False,
                        'status': 'unauthorized',
                        'message': f'User {windows_username} is not authorized',
                        'windows_username': windows_username
                    },
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 200
                
        except Exception as e:
            logger.error(f"Windows auth status error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to login
        return redirect(url_for('auth.login'))

@yam_app.route('/api/user/offline', methods=['POST'])
def user_offline():
    """Endpoint for marking user as offline when app closes or user disconnects."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            
            if user_id:
                # Use the user presence service to mark user offline
                try:
                    from app.services.user_presence import presence_service
                    success = presence_service.mark_user_offline(user_id, immediate=True)
                    if success:
                        logger.info(f"User {user_id} marked offline via API")
                    else:
                        logger.warning(f"Failed to mark user {user_id} offline via API")
                except Exception as e:
                    logger.error(f"Error marking user {user_id} offline: {e}")
            
            return jsonify({
                "status": "success", 
                "message": "User offline status updated",
                "client_type": "yam_client",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in user offline endpoint: {e}")
            return jsonify({
                "status": "error", 
                "message": str(e),
                "client_type": "yam_client",
                "timestamp": datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to login
        return redirect(url_for('auth.login'))

@yam_app.route('/api/auth/windows-login', methods=['POST'])
def windows_login():
    """Windows login endpoint for YAM client with enhanced session management."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            import getpass
            from flask_login import login_user
            from app.utils.user_activity import update_user_status, emit_online_users
            from app.models import Activity
            
            # Get Windows username
            windows_username = getpass.getuser().lower()
            
            # Find user by Windows username
            user = User.query.filter(db.func.lower(User.windows_username) == windows_username).first()
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': f'User {windows_username} is not authorized',
                    'error': 'unauthorized_user',
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 401
            
            # Log in the user
            login_user(user, remember=True)
            
            # Hydrate session
            hydrate_session(user)
            
            # Mark user as online
            try:
                update_user_status(user.id, online=True)
                emit_online_users()
            except Exception as e:
                logger.error(f"Error marking user online: {e}")
            
            # Update last login
            user.last_login = datetime.utcnow()
            
            # Log activity
            try:
                act = Activity(
                    user_id=user.id,
                    action='windows_login',
                    details=f'Windows login from {request.remote_addr} - User: {windows_username}'
                )
                db.session.add(act)
                db.session.commit()
            except Exception as e:
                logger.error(f"Error logging Windows login activity: {e}")
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'message': 'Windows authentication successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'windows_username': user.windows_username
                },
                'redirect': url_for('main.index'),
                'client_type': 'yam_client',
                'session_healthy': True,
                'timestamp': datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            logger.error(f"Windows login error: {e}")
            return jsonify({
                'success': False,
                'message': f'Windows authentication failed: {str(e)}',
                'error': 'authentication_error',
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to login
        return redirect(url_for('auth.login'))

# Add proxy routes for notes API compatibility
@yam_app.route('/notes/api/notes', methods=['GET', 'POST'])
def notes_api_proxy():
    """Proxy requests to the collab_notes API for backward compatibility."""
    from app.blueprints.collab_notes.routes import notes_collection
    return notes_collection()

@yam_app.route('/notes/api/notes/<int:note_id>', methods=['GET', 'PUT', 'DELETE'])
def notes_detail_proxy(note_id):
    """Proxy requests to the collab_notes detail API for backward compatibility."""
    from app.blueprints.collab_notes.routes import note_detail
    return note_detail(note_id)

# Add test route for PDF serving
@yam_app.route('/test-pdf/<filename>')
def test_pdf_serving(filename):
    """Test route to verify PDF serving is working."""
    try:
        from flask import send_from_directory
        # Get the correct path to the docs directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        docs_dir = os.path.join(current_dir, '..', 'app', 'static', 'docs')
        docs_dir = os.path.abspath(docs_dir)
        return send_from_directory(docs_dir, filename)
    except Exception as e:
        return jsonify({'error': str(e), 'filename': filename}), 404

# Add debug route to list available PDFs
@yam_app.route('/debug/pdfs')
def debug_pdfs():
    """Debug route to list available PDFs."""
    try:
        # Get the correct path to the docs directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        docs_dir = os.path.join(current_dir, '..', 'app', 'static', 'docs')
        docs_dir = os.path.abspath(docs_dir)
        
        pdfs = []
        if os.path.exists(docs_dir):
            for file in os.listdir(docs_dir):
                if file.lower().endswith('.pdf'):
                    pdfs.append(file)
        return jsonify({
            'docs_dir': docs_dir,
            'exists': os.path.exists(docs_dir),
            'pdfs': pdfs,
            'count': len(pdfs)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Import and register blueprints
from app.blueprints.admin import init_admin_blueprint
from app.blueprints.offices import init_offices_blueprint
from app.blueprints.devices import bp as devices_bp
from app.blueprints.main import bp as main_bp
from app.blueprints.unified import bp as unified_bp
from app.blueprints.workstations import bp as workstations_bp
from app.blueprints.admin_outages import bp as admin_outages_bp
from app.blueprints.lab import bp as lab_bp
from app.blueprints.team import bp as team_bp
from app.blueprints.events import bp as events_bp
from app.blueprints.oralyzer import bp as oralyzer_bp
from app.blueprints.kb_api import bp as kb_api_bp
from app.blueprints.api import bp as api_bp
from app.blueprints.unified_search import bp as unified_search_bp
from app.blueprints.universal_search import bp as universal_search_bp
from app.blueprints.kb_files import bp as kb_files_bp
from app.blueprints.kb_shared import bp as kb_shared_bp
from app.blueprints.admin_api import bp as admin_api_bp
from app.blueprints.jarvis import bp as jarvis_bp
from app.blueprints.outages import bp as outages_bp
from app.blueprints.patterson import bp as patterson_bp
from app.blueprints.kb import bp as kb_bp
from app.blueprints.system import bp as system_bp
from app.blueprints.collab_notes import bp as collab_notes_bp
from app.blueprints.dameware import bp as dameware_bp
from app.blueprints.system_management import bp as system_management_bp
from app.blueprints.cache_management import bp as cache_management_bp
from app.blueprints.admin_management import bp as admin_management_bp
from app.blueprints.profile_management import bp as profile_management_bp
from app.blueprints.legacy_routes import bp as legacy_routes_bp
from app.blueprints.file_serving import bp as file_serving_bp
from app.blueprints.core import bp as core_bp
from app.blueprints.socket_handlers import bp as socket_handlers_bp
from app.blueprints.error_handlers import bp as error_handlers_bp
from app.blueprints.utility_functions import bp as utility_functions_bp
from app.blueprints.initialization import bp as initialization_bp
from app.blueprints.settings_api import bp as settings_api_bp
from app.blueprints.settings import bp as settings_bp
from app.blueprints.users import bp as users_bp
from app.blueprints.users.clock_id_routes import bp as clock_id_cache_bp
from app.blueprints.service_desk import bp as service_desk_bp
from app.blueprints.modal_api import bp as modal_api_bp
from app.blueprints.api.private_messages import private_messages_bp

def register_all_blueprints(yam_app):
    # Register blueprints (order matters for some)
    try:
        from app.blueprints.auth import init_auth_blueprint
        init_auth_blueprint(yam_app)
        logger.info("Auth blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register auth blueprint: {e}")
        # Don't fail completely, but log the error
        pass
    yam_app.register_blueprint(system_management_bp)
    yam_app.register_blueprint(cache_management_bp)
    yam_app.register_blueprint(admin_management_bp)
    yam_app.register_blueprint(profile_management_bp)
    yam_app.register_blueprint(legacy_routes_bp)
    yam_app.register_blueprint(file_serving_bp)
    yam_app.register_blueprint(core_bp)
    yam_app.register_blueprint(socket_handlers_bp)
    yam_app.register_blueprint(error_handlers_bp)
    yam_app.register_blueprint(utility_functions_bp)
    yam_app.register_blueprint(initialization_bp)
    yam_app.register_blueprint(main_bp)
    yam_app.register_blueprint(api_bp, url_prefix='/api')
    yam_app.register_blueprint(devices_bp, url_prefix='/devices')
    yam_app.register_blueprint(unified_bp, url_prefix='/unified')
    yam_app.register_blueprint(workstations_bp, url_prefix='/workstations')
    yam_app.register_blueprint(admin_outages_bp, url_prefix='/api/admin/outages')
    yam_app.register_blueprint(lab_bp, url_prefix='/lab')
    yam_app.register_blueprint(team_bp, url_prefix='/team')
    yam_app.register_blueprint(events_bp, url_prefix='/events')
    yam_app.register_blueprint(oralyzer_bp, url_prefix='/oralyzer')
    yam_app.register_blueprint(kb_api_bp)
    yam_app.register_blueprint(unified_search_bp)
    yam_app.register_blueprint(universal_search_bp, url_prefix='/api/universal-search')
    yam_app.register_blueprint(kb_files_bp, url_prefix='/kb/files')
    yam_app.register_blueprint(users_bp)
    yam_app.register_blueprint(clock_id_cache_bp)
    yam_app.register_blueprint(kb_shared_bp, url_prefix='/kb/shared')
    yam_app.register_blueprint(jarvis_bp, url_prefix='/jarvis')
    yam_app.register_blueprint(outages_bp, url_prefix='/api/outages')
    yam_app.register_blueprint(patterson_bp, url_prefix='/patterson')
    yam_app.register_blueprint(kb_bp, url_prefix='/kb')
    yam_app.register_blueprint(system_bp, url_prefix='/system')
    yam_app.register_blueprint(collab_notes_bp, url_prefix='/collab-notes')
    yam_app.register_blueprint(settings_bp, url_prefix='/settings')
    yam_app.register_blueprint(settings_api_bp, url_prefix='/api/settings')
    yam_app.register_blueprint(dameware_bp)
    yam_app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
    yam_app.register_blueprint(service_desk_bp, url_prefix='/service-desk')
    yam_app.register_blueprint(modal_api_bp)
    yam_app.register_blueprint(private_messages_bp, url_prefix='/api/private-messages')
    # Add any additional blueprints as needed
    try:
        from app.blueprints.tracking import init_tracking_blueprint
        init_tracking_blueprint(yam_app)
        logger.info("Tracking blueprint registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register tracking blueprint: {e}")
    try:
        init_admin_blueprint(yam_app)
        logger.info("Admin blueprint registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register admin blueprint: {e}")
    try:
        init_offices_blueprint(yam_app)
        logger.info("Offices blueprint registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register offices blueprint: {e}")

register_all_blueprints(yam_app)
logger.info("All blueprints registered successfully")

# Add test route for hot reloading (always available)
@yam_app.route('/test-hot-reload')
def test_hot_reload_page():
    """Test page to verify hot reloading is working."""
    from datetime import datetime
    return render_template('test_simple.html', 
        user=session.get('username', 'Test User'),
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        server_uptime='Running',
        config=yam_app.config
    )

# Set startup time
yam_app.startup_time = time.time()

# Add error handlers
@yam_app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    try:
        return render_template('404.html'), 404
    except Exception as e:
        logger.error(f"Error rendering 404 template: {e}")
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found',
            'server_info': {
                'name': 'YAM Server',
                'version': '1.0.0',
                'type': 'yam'
            }
        }), 404

@yam_app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with better error handling."""
    client_type = detect_client_type()
    
    try:
        logger.error(f"500 error occurred: {error}")
        
        if client_type == 'yam_client':
            # YAM client - return JSON response
            return jsonify({
                'error': 'Internal server error',
                'message': 'An internal server error occurred. Please try again.',
                'redirect': url_for('auth.login'),
                'client_type': 'yam_client',
                'server_info': {
                    'name': 'YAM Server',
                    'version': '1.0.0',
                    'type': 'yam'
                },
                'timestamp': datetime.now().isoformat()
            }), 500
        else:
            # Web browser - try to render error template, fallback to login
            try:
                return render_template('500.html'), 500
            except Exception as template_error:
                logger.error(f"Error rendering 500 template: {template_error}")
                # Fallback to login page for web browsers
                return redirect(url_for('auth.login'))
                
    except Exception as e:
        logger.error(f"Error in 500 handler: {e}")
        # Ultimate fallback
        if client_type == 'yam_client':
            return jsonify({
                'error': 'Server error',
                'message': 'Please try logging in again',
                'redirect': url_for('auth.login'),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
        else:
            return redirect(url_for('auth.login'))

@yam_app.errorhandler(401)
def unauthorized_error(error):
    """Handle 401 unauthorized errors by redirecting to login."""
    client_type = detect_client_type()
    
    try:
        logger.info(f"401 unauthorized error - client type: {client_type}")
        
        if client_type == 'yam_client':
            # YAM client - return JSON response
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Please log in to access this resource',
                'redirect': url_for('auth.login'),
                'client_type': 'yam_client',
                'server_info': {
                    'name': 'YAM Server',
                    'version': '1.0.0',
                    'type': 'yam',
                    'dual_mode': True
                },
                'timestamp': datetime.now().isoformat()
            }), 401
        else:
            # Web browser - redirect to login page
            logger.info(f"Redirecting web browser to login page")
            return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"Error in 401 handler: {e}")
        # Fallback to login redirect
        try:
            return redirect(url_for('auth.login'))
        except Exception as redirect_error:
            logger.error(f"Error in 401 fallback redirect: {redirect_error}")
            # Ultimate fallback - return simple JSON
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Please log in',
                'timestamp': datetime.now().isoformat()
            }), 401

@yam_app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 forbidden errors."""
    client_type = detect_client_type()
    
    try:
        if client_type == 'yam_client':
            # YAM client - return JSON response
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource',
                'client_type': 'yam_client',
                'server_info': {
                    'name': 'YAM Server',
                    'version': '1.0.0',
                    'type': 'yam',
                    'dual_mode': True
                },
                'timestamp': datetime.now().isoformat()
            }), 403
        else:
            # Web browser - redirect to login page
            return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"Error in 403 handler: {e}")
        # Fallback to login redirect
        return redirect(url_for('auth.login'))

@yam_app.route('/api/socketio-test')
def socketio_test():
    """Test Socket.IO connection and presence service."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                # Test presence service
                try:
                    from app.services.user_presence import presence_service
                    from app.utils.user_activity import emit_online_users
                    
                    # Get current user status
                    user_status = presence_service.get_user_status(current_user.id)
                    presence_stats = presence_service.get_presence_stats()
                    
                    # Force emit online users
                    emit_online_users()
                    
                    return jsonify({
                        'success': True,
                        'message': 'Socket.IO and presence service test successful',
                        'user_status': user_status,
                        'presence_stats': presence_stats,
                        'socket_connected': session.get('socket_connected', False),
                        'client_type': 'yam_client',
                        'timestamp': datetime.now().isoformat()
                    }), 200
                except Exception as e:
                    logger.error(f"Presence service test failed: {e}")
                    return jsonify({
                        'success': False,
                        'message': f'Presence service test failed: {str(e)}',
                        'client_type': 'yam_client',
                        'timestamp': datetime.now().isoformat()
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'message': 'User not authenticated',
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"Socket.IO test error: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to login
        return redirect(url_for('auth.login'))

@yam_app.route('/api/test-presence')
def test_presence():
    """Test endpoint to manually trigger presence updates."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                # Test presence service
                try:
                    from app.services.user_presence import presence_service
                    from app.utils.user_activity import emit_online_users
                    
                    # Mark current user as online
                    session_data = {
                        'ip_address': request.environ.get('REMOTE_ADDR', 'unknown'),
                        'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
                        'test_time': datetime.utcnow().isoformat(),
                        'test_method': 'manual_test'
                    }
                    
                    success = presence_service.mark_user_online(current_user.id, session_data)
                    
                    if success:
                        # Emit updated online users
                        emit_online_users()
                        
                        # Get updated stats
                        user_status = presence_service.get_user_status(current_user.id)
                        presence_stats = presence_service.get_presence_stats()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Presence test successful - user marked online',
                            'user_status': user_status,
                            'presence_stats': presence_stats,
                            'client_type': 'yam_client',
                            'timestamp': datetime.now().isoformat()
                        }), 200
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Failed to mark user online',
                            'client_type': 'yam_client',
                            'timestamp': datetime.now().isoformat()
                        }), 500
                        
                except Exception as e:
                    logger.error(f"Presence test failed: {e}")
                    return jsonify({
                        'success': False,
                        'message': f'Presence test failed: {str(e)}',
                        'client_type': 'yam_client',
                        'timestamp': datetime.now().isoformat()
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'message': 'User not authenticated',
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"Presence test error: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to login
        return redirect(url_for('auth.login'))

@yam_app.route('/api/session/activity', methods=['POST'])
def update_session_activity():
    """Update session activity timestamp - FIXED VERSION"""
    try:
        from flask_login import current_user
        if current_user.is_authenticated:
            # Update session activity
            session['last_activity'] = datetime.utcnow().isoformat()
            session['request_count'] = session.get('request_count', 0) + 1
            
            # Update user's last_seen in database
            try:
                from app.models import User
                user = db.session.get(User, current_user.id)
                if user:
                    user.last_seen = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.warning(f"Error updating user last_seen: {e}")
                db.session.rollback()
            
            # Update user presence if available
            try:
                from app.services.user_presence import presence_service
                presence_service.update_heartbeat(current_user.id)
            except Exception as e:
                logger.debug(f"Could not update user presence: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Activity updated',
                'user_id': current_user.id,
                'username': current_user.username,
                'client_type': 'web_browser',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'User not authenticated',
                'client_type': 'web_browser',
                'timestamp': datetime.now().isoformat()
            }), 401
    except Exception as e:
        logger.error(f"Error updating session activity: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'client_type': 'web_browser',
            'timestamp': datetime.now().isoformat()
        }), 500

@yam_app.route('/api/session/extend', methods=['POST'])
def extend_session():
    """Extend the current session by updating last activity."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                # Get extension reason from request
                request_data = request.get_json() or {}
                extend_reason = request_data.get('extend_reason', 'manual')
                
                # Update session activity
                session['last_activity'] = datetime.utcnow().isoformat()
                session['request_count'] = session.get('request_count', 0) + 1
                session['extend_count'] = session.get('extend_count', 0) + 1
                session['last_extend_reason'] = extend_reason
                
                # Update user's last_seen in database
                try:
                    from app.models import User
                    user = db.session.get(User, current_user.id)
                    if user:
                        user.last_seen = datetime.utcnow()
                        db.session.commit()
                except Exception as e:
                    logger.warning(f"Error updating user last_seen: {e}")
                    db.session.rollback()
                
                # Mark user as online using presence service
                try:
                    from app.services.user_presence import presence_service
                    presence_service.mark_user_online(current_user.id)
                except Exception as e:
                    logger.warning(f"Error marking user online: {e}")
                
                return jsonify({
                    'success': True,
                    'message': 'Session extended successfully',
                    'extend_reason': extend_reason,
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'session_healthy': True,
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'User not authenticated',
                    'redirect': url_for('auth.login'),
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"Error in session extension: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - check authentication and extend session
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                # Update session activity
                session['last_activity'] = datetime.utcnow().isoformat()
                session['request_count'] = session.get('request_count', 0) + 1
                
                return jsonify({
                    'success': True,
                    'message': 'Session extended successfully',
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'session_healthy': True,
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                # Return JSON response instead of redirect for API calls
                return jsonify({
                    'success': False,
                    'message': 'User not authenticated',
                    'redirect': url_for('auth.login'),
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"Error in session extension: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

@yam_app.route('/api/session/time-remaining')
def session_time_remaining():
    """Get the time remaining in the current session."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                time_remaining = get_session_time_remaining()
                
                return jsonify({
                    'success': True,
                    'time_remaining_seconds': time_remaining,
                    'time_remaining_minutes': time_remaining // 60,
                    'session_healthy': time_remaining > 0,
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'last_activity': session.get('last_activity'),
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'User not authenticated',
                    'redirect': url_for('auth.login'),
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"Error getting session time remaining: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'time_remaining_seconds': 0,
                'session_healthy': False,
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - check authentication and return session info
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                time_remaining = get_session_time_remaining()
                
                return jsonify({
                    'success': True,
                    'time_remaining_seconds': time_remaining,
                    'time_remaining_minutes': time_remaining // 60,
                    'session_healthy': time_remaining > 0,
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'last_activity': session.get('last_activity'),
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                # Return JSON response instead of redirect for API calls
                return jsonify({
                    'success': False,
                    'message': 'User not authenticated',
                    'redirect': url_for('auth.login'),
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"Error getting session time remaining: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'time_remaining_seconds': 0,
                'session_healthy': False,
                'timestamp': datetime.now().isoformat()
            }), 500

@yam_app.route('/api/session/logout', methods=['POST'])
def api_logout():
    """API endpoint for logging out the current user."""
    client_type = detect_client_type()
    
    if client_type == 'yam_client':
        try:
            from flask_login import current_user, logout_user
            from app.models import Activity
            
            if current_user.is_authenticated:
                # Log activity
                try:
                    act = Activity(
                        user_id=current_user.id,
                        action='api_logout',
                        details=f'API logout from {request.remote_addr}'
                    )
                    db.session.add(act)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Error logging logout activity: {e}")
                    db.session.rollback()
                
                # Mark user offline
                try:
                    from app.utils.user_activity import update_user_status, emit_online_users
                    update_user_status(current_user.id, online=False)
                    emit_online_users()
                except Exception as e:
                    logger.error(f"Error marking user offline: {e}")
                
                # Clear session
                session.clear()
                logout_user()
                
                return jsonify({
                    'success': True,
                    'message': 'Logged out successfully',
                    'redirect': url_for('auth.login'),
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'User not authenticated',
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 401
        except Exception as e:
            logger.error(f"Error in API logout: {e}")
            return jsonify({
                'success': False,
                'message': str(e),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
    else:
        # Web browser - redirect to logout
        return redirect(url_for('auth.logout'))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='YAM Standalone Server')
    parser.add_argument('--host', default=os.getenv('YAM_SERVER_HOST', '127.0.0.1'), help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=int(os.getenv('YAM_SERVER_PORT', '5000')), help='Port to bind to (default: 5000)')
    parser.add_argument('--mode', choices=['auto', 'desktop', 'web', 'electron'], default='web', help='Server mode (default: web)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-reloader', action='store_true', help='Disable auto-reloader for better stability')
    parser.add_argument('--debugger-mode', action='store_true', help='Enable debugger mode with real-time file monitoring')
    args = parser.parse_args()

    # Signal handler for instant termination
    def signal_handler(signum, frame):
        print('\n[SHUTDOWN] Received termination signal, shutting down immediately...')
        print('[SHUTDOWN] Cleaning up resources...')
        
        # Close database connections
        try:
            with yam_app.app_context():
                db.session.close()
                db.engine.dispose()
                print('[SHUTDOWN] Database connections closed')
        except Exception as e:
            print(f'[SHUTDOWN] Error closing database: {e}')
        
        # Close SocketIO connections
        try:
            socketio.stop()
            print('[SHUTDOWN] SocketIO connections closed')
        except Exception as e:
            print(f'[SHUTDOWN] Error closing SocketIO: {e}')
        
        # Force exit
        print('[SHUTDOWN] Server terminated')
        os._exit(0)
    
    # Register signal handlers for instant termination
    signal.signal(signal.SIGINT, signal_handler)   # CTRL+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    # Clean up any existing processes on the same port (but not our own process)
    try:
        import psutil
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                # Skip our own process
                if proc.info['pid'] == current_pid:
                    continue
                    
                for conn in proc.info['connections']:
                    if conn.laddr.port == args.port:
                        print(f'[CLEANUP] Terminating process {proc.info["pid"]} using port {args.port}')
                        psutil.Process(proc.info['pid']).terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        print('[INFO] psutil not available, skipping process cleanup')
    except Exception as e:
        print(f'[WARNING] Error during process cleanup: {e}')

    # Initialize presence service and socket handlers
    with yam_app.app_context():
        try:
            # Initialize presence service
            from app.utils.user_activity import initialize_presence_service
            initialize_presence_service(yam_app)
            logger.info("Presence service initialized successfully")
            
            # Set app context for socket handlers
            from app.socket_handlers.connection import set_flask_app, schedule_periodic_cleanup
            set_flask_app(yam_app)
            
            # Import socket handlers to register them (this triggers the @socketio.on decorators)
            import app.socket_handlers.connection  # noqa: F401
            import app.socket_handlers.admin_presence  # noqa: F401
            
            # Start periodic cleanup task
            schedule_periodic_cleanup()
            
            logger.info("User presence system initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing presence system: {e}")
            # Don't fail server startup, but log the error

    # Initialize debugger mode if requested
    if args.debugger_mode:
        try:
            from debugger_server import DebuggerFileMonitor
            
            # Initialize file monitor
            app_dir = (current_dir.parent / 'app').resolve()
            file_monitor = DebuggerFileMonitor(app_dir)
            
            # Add file change callback for browser refresh
            def on_file_change(file_path, file_type):
                """Handle file changes and trigger browser refresh."""
                try:
                    logger.info(f"File change detected: {file_path} ({file_type})")
                    
                    # Send real-time update to all connected clients
                    if socketio:
                        socketio.emit('file_changed', {
                            'file_path': str(file_path),
                            'file_type': file_type,
                            'timestamp': datetime.now().isoformat(),
                            'action': 'refresh' if file_type in ['template', 'static'] else 'notify'
                        })
                        
                        # For templates and static files, trigger browser refresh
                        if file_type in ['template', 'static']:
                            socketio.emit('browser_refresh', {
                                'file_path': str(file_path),
                                'file_type': file_type,
                                'timestamp': datetime.now().isoformat()
                            })
                            
                except Exception as e:
                    logger.error(f"Error handling file change: {e}")
            
            # Register the callback
            file_monitor.add_change_callback(on_file_change)
            # Add debugger routes
            @yam_app.route('/debugger/status')
            def debugger_status():
                """Get debugger server status."""
                return jsonify({
                    'status': 'running',
                    'mode': 'debugger',
                    'real_time_updates': True,
                    'file_monitoring': file_monitor.monitoring if file_monitor else False,
                    'browser_auto_refresh': True,
                    'template_hot_reload': True,
                    'static_hot_reload': True,
                    'timestamp': datetime.now().isoformat()
                })
                
            @yam_app.route('/debugger/files')
            def debugger_files():
                """Get list of monitored files."""
                if not file_monitor:
                    return jsonify({'error': 'File monitor not initialized'})
                    
                files = []
                for file_key, file_hash in file_monitor.file_hashes.items():
                    files.append({
                        'path': file_key,
                        'hash': file_hash[:8],  # Short hash for display
                        'type': file_monitor._get_file_type(Path(file_key))
                    })
                    
                return jsonify({
                    'files': files,
                    'count': len(files),
                    'timestamp': datetime.now().isoformat()
                })
                
            @yam_app.route('/debugger/reload/<file_type>')
            def debugger_reload(file_type):
                """Manually trigger reload of specific file type."""
                if file_type == 'templates':
                    try:
                        yam_app.jinja_env.cache.clear()
                        logger.info("Template cache cleared")
                        # Notify clients
                        if socketio:
                            socketio.emit('template_reloaded', {
                                'timestamp': datetime.now().isoformat()
                            })
                    except Exception as e:
                        logger.error(f"Error clearing template cache: {e}")
                elif file_type == 'static':
                    logger.info("Static files reloaded")
                    # Notify clients
                    if socketio:
                        socketio.emit('static_reloaded', {
                            'timestamp': datetime.now().isoformat()
                        })
                elif file_type == 'python':
                    logger.info("Python modules reloaded (limited)")
                    # Notify clients
                    if socketio:
                        socketio.emit('python_reloaded', {
                            'timestamp': datetime.now().isoformat()
                        })
                else:
                    return jsonify({'error': f'Unknown file type: {file_type}'})
                    
                return jsonify({
                    'success': True,
                    'message': f'Reloaded {file_type}',
                    'timestamp': datetime.now().isoformat()
                })
                
            @yam_app.route('/debugger/console')
            def debugger_console():
                """Debugger console interface."""
                return render_template('debugger/console.html')
            
<<<<<<< HEAD
            @yam_app.route('/debugger/clear-cache')
            def debugger_clear_cache():
                """Clear template and static file cache."""
                try:
                    # Clear Jinja2 template cache
                    yam_app.jinja_env.cache.clear()
                    
                    # Clear Flask template cache
                    if hasattr(yam_app, 'template_cache'):
                        yam_app.template_cache.clear()
                    
                    # Notify clients about cache clear
                    if socketio:
                        socketio.emit('cache_cleared', {
                            'timestamp': datetime.now().isoformat(),
                            'message': 'Template and static file cache cleared'
                        })
                    
                    return jsonify({
                        'success': True,
                        'message': 'Cache cleared successfully',
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error clearing cache: {e}")
                    return jsonify({
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }), 500
            
            @yam_app.route('/debugger/test-hot-reload')
            def debugger_test_hot_reload():
                """Test route to verify hot reloading is working."""
                return jsonify({
                    'hot_reload_test': True,
                    'debug_mode': args.debug,
                    'template_auto_reload': yam_app.config.get('TEMPLATES_AUTO_RELOAD', False),
                    'jinja_auto_reload': yam_app.jinja_env.auto_reload,
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Hot reload test endpoint - modify this route to test hot reloading'
                })
            

            
            # Add SocketIO events for real-time updates
            @socketio.on('debugger_connect')
            def handle_debugger_connect():
                """Handle debugger client connection."""
                from flask_socketio import emit
                logger.info(f"Debugger client connected: {request.sid}")
                emit('debugger_status', {
                    'status': 'connected',
                    'mode': 'debugger',
                    'real_time_updates': True,
                    'file_monitoring': file_monitor.monitoring if file_monitor else False
                })
            
            @socketio.on('request_file_update')
            def handle_file_update_request(data):
                """Handle client requests for file updates."""
                from flask_socketio import emit
                file_path = data.get('file_path')
                if file_path:
                    try:
                        path = Path(file_path)
                        if path.exists():
                            with open(path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                            emit('file_content', {
                                'file_path': file_path,
                                'content': content,
                                'timestamp': datetime.now().isoformat()
                            })
                    except Exception as e:
                        logger.error(f"Error sending file update: {e}")
            
            # Start file monitoring
            file_monitor.start_monitoring()
            logger.info("Debugger mode initialized with file monitoring and browser auto-refresh")
            
        except ImportError as e:
            logger.error(f"Could not initialize debugger mode: {e}")
        except Exception as e:
            logger.error(f"Error initializing debugger mode: {e}")

    print('=' * 60)
    if args.debugger_mode:
        print('🔧 YAM DEBUGGER SERVER (REAL-TIME DEVELOPMENT MODE)')
    else:
        print('🚀 YAM SERVER (DUAL-MODE: CLIENT + WEB)')
    print('=' * 60)
    print(f'Host: {args.host}')
    print(f'Port: {args.port}')
    print(f'Debug: {args.debug}')
    print(f'Debugger Mode: {args.debugger_mode}')
    print(f'Template folder: {yam_app.template_folder}')
    print(f'Static folder: {yam_app.static_folder}')
    print(f'Session lifetime: 2 hours')
    print(f'Session directory: {session_dir}')
    print('=' * 60)
    print('✅ Enhanced Session Management:')
    print('   🔄 Session hydration on every request')
    print('   ⏰ 2-hour session lifetime')
    print('   🧹 Automatic stale session cleanup')
    print('   💾 Persistent session storage')
    print('   🔍 Session health monitoring')
    print('   ⏱️  Client-side session monitoring')
    print('   🔔 Session expiration warnings')
    print('   🔌 Socket.IO session validation')
    print('   👥 Real-time user presence tracking')
    print('=' * 60)
    print('✅ Dual-Mode Endpoints Available:')
    print('   📱 YAM Client Mode:')
    print('      • /api/server-info - Server information')
    print('      • /auto-login - Auto-login endpoint')
    print('      • /api/auth/windows-auth-status - Windows auth status')
    print('      • /api/auth/windows-login - Windows login')
    print('      • /session-status - Session status')
    print('      • /socket.io/ - SocketIO (real-time features)')
    print('   🌐 Web Browser Mode:')
    print('      • / - Main page (handled by main blueprint)')
    print('      • /auth/login - Login page')
    print('      • /app - App route with redirects')
    print('   🔧 Shared Features:')
    print('      • /api/health - Health check')
    print('      • /api/system-status - System status')
    print('      • /universal-search - Universal search')
    print('      • /unified_search - Unified search')
    print('      • /api/admin/active_users - Online users')
    print('=' * 60)
    print('💡 Access Methods:')
    print('   • YAM Client: python client.py')
    print('   • Web Browser: http://127.0.0.1:5000')
    print('=' * 60)

    # Use socketio.run() instead of yam_app.run() for proper SocketIO support
    # Enable reloader in debug mode for hot reloading (but disable when using debugger mode)
    use_reloader = args.debug and not args.no_reloader and os.getenv('WERKZEUG_DISABLE_RELOADER') != '1' and not args.debugger_mode
    
    if args.debugger_mode:
        print('🔄 Hot reloading: ENABLED via debugger mode (templates and static files will auto-reload)')
    elif use_reloader:
        print('🔄 Hot reloading: ENABLED via Werkzeug reloader (templates and static files will auto-reload)')
    else:
        print('🔄 Hot reloading: DISABLED (use --debug to enable)')
    
    socketio.run(
        yam_app,
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=use_reloader,  # Enable reloader in debug mode
        allow_unsafe_werkzeug=True  # Allow unsafe werkzeug for development
    ) 