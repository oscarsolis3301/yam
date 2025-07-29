import logging
import time
from datetime import datetime, timedelta

import psutil

# Import shared extensions (singletons)
from app.extensions import db, socketio

# Import the SQLAlchemy models – delayed import avoids circular deps
from app.models import User, SearchHistory, Activity

logger = logging.getLogger(__name__)


def background_status_emitter():
    """Continuously gather server & application metrics and push them via
    Socket.IO to all connected admin dashboard clients.

    This is the exact implementation that previously lived inside
    ``app/spark.py`` – extracted into a standalone module so it can be reused
    and unit-tested in isolation.
    
    Enhanced with memory management to prevent leaks.
    """

    # Import *app* lazily to avoid circular-import issues.  By the time this
    # function is FIRST executed the Flask application will already be fully
    # initialised, so this works fine.
    from app.YAM_refactored import app
    import gc
    import threading
    
    logger.info(f"Background status emitter starting on thread: {threading.current_thread().name}")
    
    # Memory management counters
    iteration_count = 0
    last_gc_time = time.time()
    
    while True:
        try:
            with app.app_context():
                # ---------------- System metrics ----------------
                cpu = psutil.cpu_percent()
                memory = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                net = psutil.net_io_counters()
                network = (
                    f"{net.bytes_sent/1024/1024:.1f}MB/s ↑ "
                    f"{net.bytes_recv/1024/1024:.1f}MB/s ↓" if net.bytes_sent > 0 else 'Disconnected'
                )

                system_status = {
                    'CPU Usage': f'{cpu}%',
                    'Memory Usage': f'{memory}%',
                    'Disk Usage': f'{disk}%',
                    'Network': network,
                }

                # ---------------- Jarvis (AI model) health -------------
                try:
                    from app.utils.models import get_model, FallbackModel  # inline import to avoid circular deps
                    model_instance = get_model()

                    # Consider the assistant online as long as *some* model is
                    # loaded. Distinguish between *remote* (full LLM) and *local*
                    # (fallback) modes so the UI can surface this detail.
                    jarvis_online = model_instance is not None
                    jarvis_mode = (
                        'remote' if model_instance is not None and not isinstance(model_instance, FallbackModel)
                        else 'local'
                    )
                except Exception as model_err:
                    logger.warning(f"Failed to get model status: {model_err}")
                    jarvis_online = False
                    jarvis_mode = 'unknown'

                # ---------------- Dashboard metrics -------------
                try:
                    # Check if database is ready before attempting queries
                    from sqlalchemy import text
                    try:
                        db.session.execute(text('SELECT 1'))
                    except Exception as db_test_err:
                        logger.debug(f"Database not ready for metrics collection: {db_test_err}")
                        raise db_test_err
                    
                    total_users = User.query.count()
                    active_sessions = User.query.filter_by(is_online=True).count()
                    total_searches = db.session.query(SearchHistory).count()

                    # Online users (last 5 min) - limit to prevent memory issues
                    now = datetime.utcnow()
                    online_users = (
                        User.query
                        .filter(User.is_online.is_(True), User.last_seen >= now - timedelta(seconds=300))
                        .limit(50)  # Limit to 50 users to prevent memory issues
                        .all()
                    )
                    online_users_data = [
                        {
                            'id': user.id,
                            'name': user.username,
                            'email': user.email,
                            'role': user.role,
                            'profile_picture': user.profile_picture or 'default.png',
                        }
                        for user in online_users
                    ]

                    # Recent activity (latest 10 rows) - keep limited
                    recent_activity = (
                        Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()
                    )
                    activity_data = [
                        {
                            'type': activity.action,
                            'description': activity.details,
                            'timestamp': activity.timestamp.isoformat(),
                        }
                        for activity in recent_activity
                    ]
                except Exception as db_err:
                    logger.debug(f"Failed to get database metrics: {db_err}")
                    total_users = 0
                    active_sessions = 0
                    total_searches = 0
                    online_users_data = []
                    activity_data = []

                # Only emit if we have socketio available and there are connected clients
                try:
                    if socketio and hasattr(socketio, 'server') and socketio.server:
                        # Check if there are any connected clients before emitting
                        client_count = len(socketio.server.manager.rooms.get('/', {}))
                        
                        if client_count > 0:
                            # Emit everything to the front-end via Socket.IO
                            socketio.emit(
                                'admin_dashboard_data',
                                {
                                    'total_users': total_users,
                                    'active_sessions': active_sessions,
                                    'total_searches': total_searches,
                                    'online_users': online_users_data,
                                    'system_status': system_status,
                                    'recent_activity': activity_data,
                                    'jarvis_online': jarvis_online,
                                    'jarvis_mode': jarvis_mode,
                                },
                            )
                        else:
                            # No clients connected, skip emission to save resources
                            pass
                except Exception as emit_err:
                    logger.warning(f"Failed to emit status data: {emit_err}")

                # Memory management - force garbage collection every 20 iterations (100 seconds)
                iteration_count += 1
                current_time = time.time()
                if iteration_count % 20 == 0 or (current_time - last_gc_time) > 300:  # Every 20 iterations or 5 minutes
                    gc.collect()
                    last_gc_time = current_time
                    logger.debug(f"Status emitter: Performed garbage collection (iteration {iteration_count})")

                # Longer sleep time to reduce CPU usage and memory pressure
                time.sleep(10)  # Increased from 5 to 10 seconds to reduce load
                
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error in background status emitter: %s", exc)
            # Force garbage collection on error to clean up any leaked objects
            gc.collect()
            time.sleep(10)  # Wait longer on error to prevent spam 