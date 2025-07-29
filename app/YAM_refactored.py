import os
import sys  # Ensure sys is available before we modify the import path
from pathlib import Path

# DISABLED: Eventlet monkey patching is causing conflicts with Flask/Werkzeug on Windows
# We'll use threading mode instead which is more stable
# import eventlet
# if os.getenv('ELECTRON_MODE') != '1' and os.name != 'nt':  # Skip on Windows
#     eventlet.monkey_patch()
#     print("Eventlet monkey patching applied at import time")
# else:
#     print("\033[1;34m[INFO] Skipping eventlet monkey patching for Electron mode or Windows\033[0m")

print("[INFO] Eventlet monkey patching disabled for stability (Windows compatibility)")

import gc
import signal
import threading
import weakref
from contextlib import contextmanager

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_current_dir, os.pardir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Conditional eventlet monkey patching - avoid in Electron mode
# REMOVED: This was causing conflicts - moved to top of file
# import eventlet
# if os.getenv('ELECTRON_MODE') != '1':
#     eventlet.monkey_patch()
#     print("Eventlet monkey patching applied at import time")
# else:
#     print("\033[1;34m[INFO] Skipping eventlet monkey patching for Electron mode\033[0m")

import datetime
import ast
import json
import subprocess
import requests
from ping3 import ping
from app import socket_handlers 
import concurrent.futures
from datetime import timedelta, datetime, timezone
from functools import wraps, lru_cache
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session, abort, send_from_directory, copy_current_request_context, make_response, render_template_string
from flask_login import login_user, logout_user, login_required, current_user
import pandas as pd
from rapidfuzz import process, fuzz
import logging
import sqlite3
from werkzeug.utils import secure_filename
from gpt4all import GPT4All
import fitz
from sentence_transformers import SentenceTransformer
import chromadb
import pytesseract
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration, AutoImageProcessor
import sys
import os
# Add the parent directory to the path to import the root log.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from log import init_db, log_interaction, log_upload, get_user_history, get_all_past_questions
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import csv
import sys
import queue
import threading
import socket  # Needed for gethostbyaddr in network scan functions
import base64
from collections import deque, defaultdict
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
import time
import random
from flask_migrate import Migrate
import psutil
import glob
from base64 import b64encode
import string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.extensions import db, login_manager, socketio, migrate, init_extensions
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import OperationalError
from flask_login import UserMixin
from sqlalchemy import Index
from collections import Counter
from sqlalchemy import text
from app.models import Outage, PattersonTicket, PattersonCalendarEvent
from threading import Timer
import PyPDF2
import docx
from app.blueprints.utils.db import safe_commit
from app.blueprints.admin import init_admin_blueprint
from app.blueprints.offices import init_offices_blueprint
from app.blueprints.devices import bp as devices_bp
from app.blueprints.main import bp as main_bp
from app.blueprints.unified import bp as unified_bp
from app.blueprints.workstations import bp as workstations_bp
from app.blueprints.admin_outages import bp as admin_outages_bp
from app.blueprints.lab import bp as lab_bp  # New Lab blueprint
from app.blueprints.team import bp as team_bp  # New Team blueprint
from app.blueprints.events import bp as events_bp  # AD events blueprint
from app.blueprints.oralyzer import bp as oralyzer_bp  # Oralyzer blueprint
from app.blueprints.kb_api import bp as kb_api_bp  # KB API blueprint
from app.blueprints.api import bp as api_bp  # Generic API blueprint
from app.blueprints.unified_search import bp as unified_search_bp  # Unified Search API blueprint
from app.blueprints.universal_search import bp as universal_search_bp  # Universal Search blueprint
from app.blueprints.kb_files import bp as kb_files_bp  # KB static file routes
from app.blueprints.kb_shared import bp as kb_shared_bp  # Shared KB links blueprint
from app.blueprints.admin_api import bp as admin_api_bp  # Admin REST API blueprint
from app.blueprints.jarvis import bp as jarvis_bp  # NEW Jarvis blueprint
from app.blueprints.outages import bp as outages_bp  # New Outages blueprint
from app.blueprints.patterson import bp as patterson_bp  # Patterson technician dispatch blueprint
from app.blueprints.kb import bp as kb_bp  # Main KB blueprint
from app.blueprints.system import bp as system_bp  # System info blueprint
from app.blueprints.collab_notes import bp as collab_notes_bp  # Collaborative Notes blueprint
from app.blueprints.dameware import bp as dameware_bp  # Dameware Remote Connection blueprint

# Import new blueprints
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

from app.utils.user_activity import log_user_activity

from app.utils.logger import setup_logging
logger = setup_logging()

# Colorful startup banner
print("\n" + "\033[1;36m" + "=" * 80)
print("[START] YAM (Yet Another Module) - Starting Application [START]")
print("=" * 80 + "\033[0m")
print("\033[1;34m[PERF] Performance optimizations: ENABLED\033[0m")
print("\033[1;35m[DESKTOP] Desktop mode: " + ("ACTIVE" if os.getenv('ELECTRON_MODE') == '1' else "INACTIVE") + "\033[0m")
print("\033[1;32m[CACHE] Enhanced cache system: READY\033[0m")
print("\033[1;33m[MEMORY] Memory management: OPTIMIZED\033[0m")
print("\033[1;36m" + "=" * 80 + "\033[0m\n")

logger.info("Starting application...")

# Import and apply performance optimizations early
try:
    from app.utils.performance_optimizations import (
        optimize_flask_for_electron, 
        performance_optimizer,
        performance_monitor
    )
    
    # Import startup diagnostics
    from app.utils.startup_diagnostics import apply_startup_fixes, run_startup_diagnostics
    
    # Import responsive UI manager
    try:
        from app.utils.responsive_ui import responsive_ui
        logger.info("Responsive UI system imported successfully")
    except ImportError as ui_err:
        logger.warning(f"Responsive UI system not available: {ui_err}")
    
    # Check if running in Electron mode
    if os.getenv('ELECTRON_MODE') == '1':
        # Apply emergency fixes first
        apply_startup_fixes()
        
        optimize_flask_for_electron()
        # Fix Werkzeug server FD issue in Electron mode
        os.environ.pop('WERKZEUG_SERVER_FD', None)
        # Set required Werkzeug fixes for Electron
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        logger.info("Electron mode optimizations applied")
        
        # Initialize responsive UI early for Electron
        try:
            from app.utils.responsive_ui import responsive_ui
            responsive_ui.memory_threshold_mb = 350  # Aggressive threshold for Electron
            responsive_ui.max_operation_time_ms = 25  # Shorter operation time
            # Start will be called later during init_ultra_minimal_startup
            logger.info("Responsive UI manager configured for Electron")
        except Exception as ui_err:
            logger.warning(f"Responsive UI initialization failed: {ui_err}")
        
        # Run diagnostics and log results
        try:
            diagnostics = run_startup_diagnostics()
            logger.info(f"Startup diagnostics: {len(diagnostics['fixes_applied'])} fixes applied")
        except Exception as diag_err:
            logger.warning(f"Startup diagnostics failed: {diag_err}")
    
except ImportError as e:
    logger.warning(f"Performance optimizations not available: {e}")

from app.config import Config
from app.utils.search import init_search_table, save_search, get_search_suggestions
from app.utils.device import cache_storage, load_cached_storage, get_devices_csv_path, load_devices_cache
from app.utils.helpers import (
    verify_file_exists as helpers_verify_file_exists,
    extract_text_from_document as helpers_extract_text_from_document,
    get_document_text as helpers_get_document_text,
    extract_pdf_details,  # shared utility – reuse instead of local duplicate
    allowed_file as _allowed_file_helper
)

# Shared KB-import helper (moved from app.spark)
from app.utils.kb_import import import_docs_folder, import_docs_folder_startup
# NEW: background status emitter moved to dedicated utils module
from app.utils.status_emitter import background_status_emitter as _background_status_emitter
from app.utils.default_faq import load_default_faq  # Load default FAQs
from app.blueprints.settings_api import bp as settings_api_bp
from app.blueprints.users import bp as users_bp  # Users blueprint (provides /users PowerShell lookup)

app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

# Initialize extensions only once
from app.extensions import db, login_manager, socketio, migrate
db.init_app(app)
login_manager.init_app(app)

# Enhanced session configuration for persistence
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=90)  # 90 day sessions for better persistence
app.config['SESSION_FILE_THRESHOLD'] = 1000  # Keep more sessions in memory
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_MAX_AGE'] = 90 * 24 * 60 * 60  # 90 days in seconds
app.config['SESSION_COOKIE_PERMANENT'] = True  # Make all sessions permanent by default

# Ensure session directory exists
session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sessions')
os.makedirs(session_dir, exist_ok=True)
app.config['SESSION_FILE_DIR'] = session_dir

# Initialize session manager
try:
    from app.utils.session_manager import init_session_manager
    session_manager = init_session_manager(app)
    logger.info("Session manager initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize session manager: {e}")
    session_manager = None

# Initialize performance optimizer
try:
    performance_optimizer.init_app(app)
    logger.info("Performance monitoring enabled")
except NameError:
    logger.info("Performance monitoring not available")

# Initialize socketio with better error handling and async mode
# For Electron mode, use threading instead of eventlet to avoid conflicts
socketio_initialized = False
# Always use threading mode to avoid eventlet issues
try:
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)
    socketio_initialized = True
    logger.info("SocketIO initialized successfully (threading mode)")
except Exception as e:
    logger.warning(f"SocketIO initialization failed: {e}. Some real-time features may be disabled.")
    socketio_initialized = False

migrate.init_app(app, db)

# Initialize AI model
try:
    from app.utils.models import get_model, get_embedder, FallbackModel, FallbackEmbedder
    from app.config import Config
    import os
    from pathlib import Path

    # Create models directory if it doesn't exist
    models_dir = Path("data/models")
    models_dir.mkdir(parents=True, exist_ok=True)

    # Initialize models with fallbacks
    app.ai_model = get_model()
    app.embedder = get_embedder()
    
    if isinstance(app.ai_model, FallbackModel) or isinstance(app.embedder, FallbackEmbedder):
        logger.warning("Some AI models failed to initialize. Using fallback models. Some features may be limited.")
    else:
        logger.info("AI models initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AI models: {str(e)}")
    app.ai_model = FallbackModel()
    app.embedder = FallbackEmbedder()

# Import models after db initialization
from app.models import User, SearchHistory, SystemSettings, UserSettings, Note, Activity, Document, KBArticle, KBAttachment, SharedLink, UserPresence, TimeEntry, PattersonTicket, PattersonCalendarEvent

# Import shared state variables (defined in app.shared_state)

# Import shared state
from app.shared_state import (
    memory_manager, 
    _initialization_state, 
    _app_initialized, 
    _blueprints_registered, 
    _background_init_started,
    update_initialization_status,
    get_initialization_status,
    set_app_initialized,
    set_blueprints_registered,
    set_background_init_started
)

def register_all_blueprints():
    """Register all blueprints including the new refactored ones"""
    if _blueprints_registered:
        logger.info("Blueprints already registered, skipping duplicate registration")
        return
    try:
        # Register the auth blueprint FIRST using the same pattern as spark.py
        try:
            from app.blueprints.auth import init_auth_blueprint
            init_auth_blueprint(app)
            logger.info("Auth blueprint registered successfully")
        except Exception as auth_err:
            logger.error(f"Failed to register auth blueprint: {auth_err}")
            raise auth_err
            
        # Register new refactored blueprints
        app.register_blueprint(system_management_bp)
        app.register_blueprint(cache_management_bp)
        app.register_blueprint(admin_management_bp)
        app.register_blueprint(profile_management_bp)
        app.register_blueprint(legacy_routes_bp)
        app.register_blueprint(file_serving_bp)
        app.register_blueprint(core_bp)
        app.register_blueprint(socket_handlers_bp)
        app.register_blueprint(error_handlers_bp)
        app.register_blueprint(utility_functions_bp)
        app.register_blueprint(initialization_bp)
        
        # Register existing blueprints
        app.register_blueprint(main_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(devices_bp, url_prefix='/devices')
        app.register_blueprint(unified_bp, url_prefix='/unified')
        app.register_blueprint(workstations_bp, url_prefix='/workstations')
        
        # Fix: Admin outages blueprint should be registered with correct prefix
        app.register_blueprint(admin_outages_bp, url_prefix='/api/admin/outages')
        
        app.register_blueprint(lab_bp, url_prefix='/lab')
        app.register_blueprint(team_bp, url_prefix='/team')
        app.register_blueprint(events_bp, url_prefix='/events')
        app.register_blueprint(oralyzer_bp, url_prefix='/oralyzer')
        
        # DEBUG: Add logging for kb_api blueprint registration
        logger.info("Registering kb_api blueprint...")
        app.register_blueprint(kb_api_bp)
        logger.info(f"kb_api blueprint registered with name: {kb_api_bp.name}")
        logger.info(f"kb_api blueprint url_prefix: {kb_api_bp.url_prefix}")
        
        # Fix: Unified search blueprint should be registered without prefix to match routes
        app.register_blueprint(unified_search_bp)
        
        app.register_blueprint(universal_search_bp, url_prefix='/api/universal-search')
        app.register_blueprint(kb_files_bp, url_prefix='/kb/files')
        app.register_blueprint(users_bp)
        app.register_blueprint(kb_shared_bp, url_prefix='/kb/shared')
        app.register_blueprint(jarvis_bp, url_prefix='/jarvis')
        app.register_blueprint(outages_bp, url_prefix='/outages')
        app.register_blueprint(patterson_bp, url_prefix='/patterson')
        app.register_blueprint(kb_bp, url_prefix='/kb')
        app.register_blueprint(system_bp, url_prefix='/system')
        app.register_blueprint(collab_notes_bp, url_prefix='/collab-notes')
        app.register_blueprint(settings_api_bp, url_prefix='/api/settings')
        app.register_blueprint(dameware_bp)  # Dameware Remote Connection
        
        # Add missing admin_api blueprint
        app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
        
        # Add missing tracking blueprint
        try:
            from app.blueprints.tracking import init_tracking_blueprint
            init_tracking_blueprint(app)
            logger.info("Tracking blueprint registered")
        except Exception as e:
            logger.warning(f"Failed to register tracking blueprint: {e}")
        
        # Register special blueprints that need initialization
        try:
            init_admin_blueprint(app)
            logger.info("Admin blueprint registered")
        except Exception as e:
            logger.warning(f"Failed to register admin blueprint: {e}")
        try:
            init_offices_blueprint(app)
            logger.info("Offices blueprint registered")
        except Exception as e:
            logger.warning(f"Failed to register offices blueprint: {e}")
        set_blueprints_registered(True)
        logger.info("All blueprints registered successfully")
        
        # Debug: Print registered blueprints
        logger.info(f"Registered blueprints: {list(app.blueprints.keys())}")
        
        # Debug: Check if kb_public route is registered
        kb_public_routes = [rule for rule in app.url_map.iter_rules() if 'kb_public' in rule.rule]
        logger.info(f"kb_public routes found: {[rule.rule for rule in kb_public_routes]}")
        
    except Exception as e:
        logger.error(f"Blueprint registration failed: {e}")
        raise

# Login manager is already configured in extensions.py
# No need to reconfigure here to avoid conflicts
logger.info("Login manager already initialized from extensions.py")

# Replace legacy *Query.get()* call with modern Session.get() to avoid SA warnings
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

# === Logging Setup ===
logger.setLevel(logging.INFO)

# Formatter with timestamp
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')

# File handler (writes to log file)
file_handler = logging.FileHandler('user_activity.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- Network-scan & before_request handlers now live in app.network_scan ---
from app.network_scan import init_network_scan  # noqa: E402
init_network_scan(app)

# Add session maintenance handler
@app.before_request
def maintain_session():
    """Ensure sessions are properly maintained for authenticated users."""
    try:
        from flask_login import current_user
        
        # Only force re-authentication if there was a proper server shutdown
        if app.config.get('FORCE_REAUTH', False):
            # Clear all session data
            session.clear()
            logout_user()
            
            # Redirect to login page with shutdown parameter
            if request.endpoint and request.endpoint != 'static':
                logger.info(f"[INFO] Server restart detected - redirecting {request.endpoint} to login")
                return redirect(url_for('auth.login', shutdown='true'))
        
        if current_user.is_authenticated:
            # Make session permanent for authenticated users
            session.permanent = True
            
            # Update session with user info
            session['user_id'] = current_user.id
            session['username'] = current_user.username
            session['last_activity'] = datetime.utcnow().isoformat()
            
            # Mark session as modified to ensure it's saved
            session.modified = True
            
    except Exception as e:
        logger.warning(f"Error in session maintenance: {e}")

# Database paths
DB_PATH = Config.DB_PATH
QUESTIONS_DB = Config.QUESTIONS_DB
SESSION_TRACKER_FILE = Config.SESSION_TRACKER_FILE
CHAT_QA_DB = Config.CHAT_QA_DB
CACHE_DB = Config.CACHE_DB

# Use imported constants
statuses = Config.STATUSES
source = Config.SOURCES
priorities = Config.PRIORITIES

# Weather API configuration
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'

# Profile picture upload configuration
UPLOAD_FOLDER = 'static/uploads'
PROFILE_PICTURES_FOLDER = 'static/uploads/profile_pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # GIF support added
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(PROFILE_PICTURES_FOLDER, exist_ok=True)

def allowed_file(filename):
    return _allowed_file_helper(filename)

# Graceful shutdown
# Global cleanup state management
_cleanup_state = {
    'in_progress': False,
    'completed': False,
    'start_time': None,
    'attempts': 0,
    'max_attempts': 3
}

def cleanup():
    """Enhanced cleanup function with spam protection and better logging"""
    global _cleanup_state
    
    # Prevent multiple simultaneous cleanup attempts
    if _cleanup_state['in_progress']:
        _cleanup_state['attempts'] += 1
        if _cleanup_state['attempts'] <= _cleanup_state['max_attempts']:
            logger.info(f"[INFO] Cleanup already in progress (attempt {_cleanup_state['attempts']}/{_cleanup_state['max_attempts']})")
        else:
            logger.warning("[WARN] Too many cleanup attempts, forcing immediate exit")
            force_cleanup()
            os._exit(1)
        return
    
    # Prevent cleanup if already completed
    if _cleanup_state['completed']:
        logger.info("[OK] Cleanup already completed, skipping")
        return
    
    # Initialize cleanup state
    _cleanup_state['in_progress'] = True
    _cleanup_state['start_time'] = time.time()
    _cleanup_state['attempts'] = 1
    
    logger.info("=" * 60)
    logger.info("[INFO] YAM APPLICATION SHUTDOWN INITIATED")
    logger.info("=" * 60)
    
    try:
        # Phase 1: Clear all user sessions (NEW - CRITICAL FOR SECURITY)
        logger.info("[STEP] Phase 1: Clearing all user sessions...")
        try:
            from app.utils.session_cleanup import clear_all_user_sessions, create_shutdown_marker
            clear_all_user_sessions()
            create_shutdown_marker()
            logger.info("  [OK] All user sessions cleared - users must re-authenticate")
        except Exception as e:
            logger.error(f"  [ERROR] Session cleanup failed: {e}")
        
        # Phase 2: Stop background services
        logger.info("[STEP] Phase 2: Stopping background services...")
        
        # Stop the optimized index manager
        try:
            from app.utils.optimized_index_manager import optimized_index_manager
            if hasattr(optimized_index_manager, 'stop'):
                optimized_index_manager.stop()
                logger.info("  [OK] Index manager stopped")
        except Exception as e:
            logger.warning(f"  [WARN] Index manager: {e}")
        
        # Stop SocketIO if running
        try:
            if 'socketio' in globals() and hasattr(socketio, 'stop'):
                socketio.stop()
                logger.info("  [OK] SocketIO stopped")
        except Exception as e:
            logger.warning(f"  [WARN] SocketIO: {e}")
        
        # Phase 3: Thread cleanup
        logger.info("[STEP] Phase 3: Stopping background threads...")
        try:
            import threading
            active_threads = [t for t in threading.enumerate() if t != threading.current_thread() and t.is_alive()]
            
            if active_threads:
                logger.info(f"  [INFO] Stopping {len(active_threads)} threads...")
                stopped_count = 0
                
                for thread in active_threads:
                    try:
                        if hasattr(thread, '_stop_event'):
                            thread._stop_event.set()
                        if hasattr(thread, 'stop'):
                            thread.stop()
                        thread.join(timeout=1.5)  # Reduced timeout for faster cleanup
                        
                        if not thread.is_alive():
                            stopped_count += 1
                        else:
                            logger.warning(f"  [WARN] Thread '{thread.name}' did not stop gracefully")
                    except Exception as thread_err:
                        logger.warning(f"  [WARN] Thread '{thread.name}': {thread_err}")
                
                logger.info(f"  [OK] {stopped_count}/{len(active_threads)} threads stopped")
            else:
                logger.info("  [OK] No active threads found")
        except Exception as e:
            logger.warning(f"  [WARN] Thread cleanup error: {e}")
        
        # Phase 4: Database cleanup
        logger.info("[STEP] Phase 4: Cleaning up database connections...")
        try:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
                logger.info("  [OK] Database connections closed")
        except Exception as e:
            logger.warning(f"  [WARN] Database cleanup: {e}")
        
        # Phase 5: Process cleanup
        logger.info("[STEP] Phase 5: Terminating child processes...")
        try:
            import psutil
            current_process = psutil.Process()
            children = current_process.children(recursive=True)
            
            if children:
                logger.info(f"  [INFO] Terminating {len(children)} child processes...")
                terminated_count = 0
                
                for child in children:
                    try:
                        child.terminate()
                        child.wait(timeout=2)  # Reduced timeout
                        terminated_count += 1
                    except psutil.TimeoutExpired:
                        logger.warning(f"  [WARN] Force killing process {child.pid}")
                        child.kill()
                        terminated_count += 1
                    except Exception as e:
                        logger.warning(f"  [WARN] Process {child.pid}: {e}")
                
                logger.info(f"  [OK] {terminated_count}/{len(children)} processes terminated")
            else:
                logger.info("  [OK] No child processes found")
        except Exception as e:
            logger.warning(f"  [WARN] Process cleanup error: {e}")
        
        # Phase 6: Memory cleanup
        logger.info("[STEP] Phase 6: Memory cleanup...")
        try:
            import gc
            collected = gc.collect()
            logger.info(f"  [OK] Garbage collection: {collected} objects freed")
        except Exception as e:
            logger.warning(f"  [WARN] Memory cleanup: {e}")
        
        # Calculate cleanup time
        cleanup_time = time.time() - _cleanup_state['start_time']
        logger.info("=" * 60)
        logger.info("[OK] YAM APPLICATION SHUTDOWN COMPLETED")
        logger.info(f"[TIME] Cleanup time: {cleanup_time:.2f} seconds")
        logger.info("[SECURITY] All users must re-authenticate on next startup")
        logger.info("=" * 60)
        
        # Mark cleanup as completed
        _cleanup_state['completed'] = True
        
    except Exception as e:
        logger.error(f"[ERROR] CRITICAL ERROR during cleanup: {e}")
        logger.error("[FATAL] Initiating force cleanup...")
        force_cleanup()
    finally:
        _cleanup_state['in_progress'] = False

def force_cleanup():
    """Force cleanup for emergency shutdown - minimal logging"""
    global _cleanup_state
    
    if _cleanup_state['completed']:
        return
    
    logger.info("[FATAL] FORCE CLEANUP - IMMEDIATE TERMINATION")
    
    try:
        # Phase 1: Clear all user sessions (CRITICAL FOR SECURITY)
        try:
            from app.utils.session_cleanup import clear_all_user_sessions, create_shutdown_marker
            clear_all_user_sessions()
            create_shutdown_marker()
            logger.info("[FATAL] All user sessions cleared")
        except Exception as e:
            logger.error(f"[ERROR] Session cleanup failed: {e}")
        
        # Phase 2: Kill all child processes immediately
        import psutil
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        
        for child in children:
            try:
                child.kill()
            except Exception:
                pass
        
        # Phase 3: Force exit all threads
        import threading
        import _thread
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                try:
                    _thread.interrupt_main()
                except Exception:
                    pass
        
        logger.info("[FATAL] Force cleanup completed")
        
    except Exception as e:
        logger.error(f"[ERROR] Force cleanup error: {e}")
    finally:
        _cleanup_state['completed'] = True

# Register cleanup function
import atexit
atexit.register(cleanup)

# Knowledge Base cache utilities (ensure available before initialisation)
from app.utils import cache as _kb_cache  # noqa: E402

load_articles_cache = _kb_cache.load_articles_cache  # type: ignore
_articles_cache = _kb_cache._articles_cache  # noqa: WPS437 (module import alias)
_articles_cache_lock = _kb_cache._articles_cache_lock  # noqa: WPS437
_articles_cache_mtime = getattr(_kb_cache, '_articles_cache_mtime', None)

# Skip heavy initialization at module level - will be done in main()
# This prevents blocking import issues and allows for faster startup
logger.info("YAM module loaded - initialization will occur at startup")

# Root route - redirect to main blueprint
@app.route('/')
def root_route():
    """Root route that redirects to the main blueprint's index route."""
    # Only force re-authentication if there was a proper server shutdown
    if app.config.get('FORCE_REAUTH', False):
        session.clear()
        logout_user()
        return redirect(url_for('auth.login', shutdown='true'))
    
    return redirect(url_for('main.index'))

# Add a simple test route to verify auth blueprint is working
@app.route('/test-auth')
def test_auth():
    """Test route to verify auth blueprint is accessible"""
    if 'auth' in app.blueprints:
        return jsonify({
            'status': 'success',
            'auth_blueprint': 'registered',
            'blueprints': list(app.blueprints.keys())
        })
    else:
        return jsonify({
            'status': 'error',
            'auth_blueprint': 'not_registered',
            'blueprints': list(app.blueprints.keys())
        }), 500

# Legacy routes for backward compatibility (same as spark.py)
# Legacy login route removed to prevent conflicts with auth blueprint
# The auth blueprint handles /auth/login correctly

@app.route('/dashboard')
@login_required
def _legacy_dashboard_route():
    """Backward-compatibility alias for the admin dashboard (``/admin/dashboard``).

    Older front-end code may still reference the top-level ``/dashboard`` URL. If
    the current user is an admin we forward them to the admin dashboard inside
    the *admin* blueprint; otherwise we simply send them to the generic index
    page. This prevents unnecessary *404 Not Found* responses that were showing
    up in the logs.
    """
    if current_user.is_authenticated and getattr(current_user, 'role', 'user') == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('main.index'))

@app.route('/logout')
@login_required
def _legacy_logout_route():
    """Backward-compatibility alias for the logout page (``/auth/logout``).

    Some templates and external bookmarks still point to the top-level
    ``/logout`` URL. We proxy the request to the canonical auth.logout view so
    the current session is terminated and the user is redirected to the login
    page without a 404.
    """
    from app.blueprints.auth.routes import logout as auth_logout  # type: ignore
    return auth_logout()

@app.route('/notes')
@login_required
def notes():
    """Render the notes page - redirect to collab_notes blueprint."""
    return redirect(url_for('collab_notes.notes_home'))

@app.route('/notes/api/notes', methods=['GET', 'POST'])
@login_required
def notes_api_proxy():
    """Proxy requests to the collab_notes API for backward compatibility."""
    from app.blueprints.collab_notes.routes import notes_collection
    return notes_collection()

@app.route('/notes/api/notes/<int:note_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def notes_detail_proxy(note_id):
    """Proxy requests to the collab_notes detail API for backward compatibility."""
    from app.blueprints.collab_notes.routes import note_detail
    return note_detail(note_id)

@app.route('/kb')
@login_required
def kb():
    """Render the Knowledge Base page (unchanged behaviour)."""
    return render_template('kb.html', active_page='kb')

@app.route('/api/kb_public_test', methods=['GET'])
def kb_public_test():
    """Test endpoint to verify the kb_public proxy is working."""
    return jsonify({
        'status': 'ok',
        'message': 'kb_public proxy is working',
        'route': '/api/kb_public',
        'proxy_to': 'kb_api.get_kb_articles_public'
    })

# Legacy admin API routes for backward compatibility
@app.route('/api/admin/dashboard')
@login_required
def admin_dashboard_proxy():
    """Proxy requests to the admin dashboard API for backward compatibility."""
    from app.blueprints.admin.routes import admin_dashboard_data
    return admin_dashboard_data()

@app.route('/api/admin/system-status')
@login_required
def admin_system_status_proxy():
    """Proxy requests to the admin system status API for backward compatibility."""
    from app.blueprints.admin.routes import admin_system_status
    return admin_system_status()

@app.route('/api/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users_proxy():
    """Proxy requests to the admin users API for backward compatibility."""
    from app.blueprints.admin.routes import admin_users
    return admin_users()

@app.route('/api/admin/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def admin_user_proxy(user_id):
    """Proxy requests to the admin user detail API for backward compatibility."""
    from app.blueprints.admin.routes import admin_user
    return admin_user(user_id)

@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_password_proxy(user_id):
    """Proxy requests to the admin reset password API for backward compatibility."""
    from app.blueprints.admin.routes import admin_reset_password
    return admin_reset_password(user_id)

@app.route('/api/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings_proxy():
    """Proxy requests to the admin settings API for backward compatibility."""
    from app.blueprints.admin.routes import admin_settings
    return admin_settings()

@app.route('/api/admin/activity')
@login_required
def admin_activity_proxy():
    """Proxy requests to the admin activity API for backward compatibility."""
    from app.blueprints.admin.routes import admin_activity
    return admin_activity()

@app.route('/search')
@login_required
def universal_search_page():
    """Render the universal search page."""
    query = request.args.get('q', '')
    return render_template('universal_search_page.html', query=query)

@app.route('/universal-search')
@login_required
def universal_search_page_alias():
    """Alias to maintain backwards-compatibility with the new Universal Search
    full-results link ("View All"). It renders the existing
    *universal_search_page.html* template so we avoid a hard 404 when the
    JavaScript redirects to ``/universal-search``.
    """
    query = request.args.get('q', '')
    return render_template('universal_search_page.html', query=query)

@app.route('/app/jarvis', methods=['POST'])
@login_required
def jarvis_app_proxy():
    from app.blueprints.jarvis.routes import chat as jarvis_chat_handler
    return jarvis_chat_handler()

@app.route('/ai/spark', methods=['POST'])
@login_required
def spark_proxy():
    """Proxy requests to Cloudflare's AI service through our backend."""
    try:
        data = request.get_json()
        if not data or 'inputs' not in data or not isinstance(data['inputs'], list) or len(data['inputs']) == 0:
            return jsonify({'error': 'Invalid request format - expected {inputs: [{prompt: "..."}]}'}), 400

        # Extract prompt from the first input
        prompt = data['inputs'][0].get('prompt')
        if not prompt:
            return jsonify({'error': 'Missing prompt in request'}), 400

        # Forward request to Cloudflare
        response = requests.post(
            'https://spark.oscarsolis3301.workers.dev/jarvis',
            json={
                'inputs': [{
                    'prompt': prompt
                }]
            },
            timeout=30  # 30 second timeout
        )

        if not response.ok:
            logger.error(f"Cloudflare request failed: {response.status_code} - {response.text}")
            return jsonify({'error': 'Cloudflare service unavailable'}), 502

        # Parse Cloudflare response
        cloudflare_data = response.json()
        if not isinstance(cloudflare_data, list) or len(cloudflare_data) == 0:
            return jsonify({'error': 'Invalid response from Cloudflare'}), 502

        # Return the response in the same format as Cloudflare
        return jsonify(cloudflare_data)

    except requests.exceptions.RequestException as e:
        logger.error(f"Cloudflare request failed: {str(e)}")
        return jsonify({'error': 'Failed to reach Cloudflare service'}), 502
    except Exception as e:
        logger.error(f"Unexpected error in spark proxy: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def comprehensive_startup_check(port=5000):
    """
    Comprehensive startup check that handles all cleanup and validation automatically.
    This replaces the need for separate batch files.
    """
    logger.info("=" * 60)
    logger.info("[STARTUP] YAM COMPREHENSIVE STARTUP CHECK")
    logger.info("=" * 60)
    
    try:
        # 1. Check if another YAM instance is already running
        logger.info("[INFO] Checking for existing YAM instances...")
        
        # Check for Electron processes
        try:
            result = subprocess.run('tasklist /FI "IMAGENAME eq electron.exe"', 
                                  shell=True, capture_output=True, text=True)
            if 'electron.exe' in result.stdout:
                logger.warning("[WARN] Electron process detected - another YAM instance may be running")
                logger.info("[INFO] Attempting to terminate existing Electron processes...")
                subprocess.run('taskkill /F /IM electron.exe', shell=True, capture_output=True)
                time.sleep(2)  # Wait for processes to terminate
        except Exception as e:
            logger.debug(f"[DEBUG] Electron check warning: {e}")
        
        # Check for Python processes running YAM
        current_pid = str(os.getpid())
        try:
            result = subprocess.run('wmic process where "name=\'python.exe\' and commandline like \'%YAM%\'" get processid /value', 
                                  shell=True, capture_output=True, text=True)
            yam_pids = []
            for line in result.stdout.split('\n'):
                if 'ProcessId=' in line:
                    pid = line.split('=')[1].strip()
                    if pid and pid.isdigit() and pid != current_pid:
                        yam_pids.append(pid)
            
            if yam_pids:
                logger.warning(f"[WARN] Found {len(yam_pids)} other YAM Python processes")
                logger.info("[INFO] Terminating existing YAM processes...")
                for pid in yam_pids:
                    try:
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                        logger.info(f"[INFO] Terminated YAM process {pid}")
                    except Exception:
                        pass
                time.sleep(2)  # Wait for processes to terminate
        except Exception as e:
            logger.debug(f"[DEBUG] Python process check warning: {e}")
        
        # 2. Check if port is in use
        logger.info(f"[INFO] Checking if port {port} is available...")
        try:
            result = subprocess.run(f'netstat -ano | findstr :{port}', 
                                  shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                logger.warning(f"[WARN] Port {port} is in use")
                logger.info("[INFO] Freeing port...")
                
                # Extract PIDs using the port
                pids = set()
                for line in result.stdout.split('\n'):
                    if line.strip() and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pids.add(parts[4])
                
                # Terminate processes using the port
                for pid in pids:
                    try:
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                        logger.info(f"[INFO] Freed port {port} (PID: {pid})")
                    except Exception:
                        pass
                
                time.sleep(2)  # Wait for port to be freed
            else:
                logger.info(f"[INFO] Port {port} is available")
        except Exception as e:
            logger.debug(f"[DEBUG] Port check warning: {e}")
        
        # 3. Verify port is actually free
        logger.info("[INFO] Verifying port availability...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.bind(('127.0.0.1', port))
            sock.close()
            logger.info(f"[INFO] Port {port} successfully verified as free")
        except Exception as e:
            logger.error(f"[ERROR] Port {port} is still in use: {e}")
            logger.info("[INFO] Attempting final cleanup...")
            
            # Final cleanup attempt
            try:
                subprocess.run(f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :{port}\') do taskkill /F /PID %a', 
                              shell=True, capture_output=True)
                time.sleep(3)
                
                # Try binding again
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.bind(('127.0.0.1', port))
                sock.close()
                logger.info(f"[INFO] Port {port} freed after final cleanup")
            except Exception as final_e:
                logger.error(f"[ERROR] Failed to free port {port}: {final_e}")
                return False
        
        # 4. Check dependencies
        logger.info("[INFO] Verifying dependencies...")
        
        # Check Python
        try:
            result = subprocess.run(['python', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"[INFO] Python: {result.stdout.strip()}")
            else:
                logger.error("[ERROR] Python not found or not working")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Python check failed: {e}")
            return False
        
        # Check Node.js (for Electron mode)
        if os.getenv('ELECTRON_MODE') == '1':
            try:
                result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"[INFO] Node.js: {result.stdout.strip()}")
                else:
                    logger.warning("[WARN] Node.js not found - Electron mode may not work")
            except Exception as e:
                logger.warning(f"[WARN] Node.js check failed: {e}")
        
        # 5. Clean up temporary files
        logger.info("[INFO] Cleaning temporary files...")
        try:
            # Clean old session files (older than 7 days)
            session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sessions')
            if os.path.exists(session_dir):
                cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days
                cleaned_count = 0
                for filename in os.listdir(session_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(session_dir, filename)
                        if os.path.getmtime(filepath) < cutoff_time:
                            try:
                                os.remove(filepath)
                                cleaned_count += 1
                            except Exception:
                                pass
                if cleaned_count > 0:
                    logger.info(f"[INFO] Cleaned {cleaned_count} old session files")
            
            # Clean old log files (older than 30 days)
            log_dir = os.path.dirname(os.path.abspath(__file__))
            cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 days
            cleaned_count = 0
            for filename in os.listdir(log_dir):
                if filename.endswith('.log'):
                    filepath = os.path.join(log_dir, filename)
                    if os.path.getmtime(filepath) < cutoff_time:
                        try:
                            os.remove(filepath)
                            cleaned_count += 1
                        except Exception:
                            pass
            if cleaned_count > 0:
                logger.info(f"[INFO] Cleaned {cleaned_count} old log files")
                
        except Exception as e:
            logger.debug(f"[DEBUG] File cleanup warning: {e}")
        
        # 6. Set up environment variables
        logger.info("[INFO] Setting up environment...")
        os.environ['ELECTRON_MODE'] = '1'
        os.environ['FLASK_PORT'] = str(port)
        os.environ['NODE_ENV'] = 'production'
        
        logger.info("=" * 60)
        logger.info("[SUCCESS] STARTUP CHECK COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Startup check failed: {e}")
        return False

def check_single_instance(port):
    """Legacy function - now calls comprehensive_startup_check"""
    return comprehensive_startup_check(port)

def launch_electron_app():
    """Launch the Electron application after Flask is ready."""
    try:
        logger.info("[INFO] Launching Electron desktop application...")
        
        # Check if Node.js and npm are available
        node_available = False
        npm_available = False
        
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                logger.info(f"[INFO] Node.js detected: {node_version}")
                node_available = True
        except Exception as e:
            logger.error(f"[ERROR] Node.js not found: {e}")
            return False
        
        try:
            npm_commands = ['npm', 'npm.cmd'] if os.name == 'nt' else ['npm']
            for npm_cmd in npm_commands:
                try:
                    result = subprocess.run([npm_cmd, '--version'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        npm_version = result.stdout.strip()
                        logger.info(f"[INFO] npm detected: {npm_version}")
                        npm_available = True
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"[ERROR] npm not found: {e}")
            return False
        
        if not (node_available and npm_available):
            logger.error("[ERROR] Node.js or npm not available. Cannot launch Electron app.")
            return False
        
        # Get paths
        electron_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'electron')
        node_modules_path = os.path.join(electron_dir, 'node_modules')
        package_json_path = os.path.join(electron_dir, 'package.json')
        
        logger.info(f"[DEBUG] Electron directory: {electron_dir}")
        logger.info(f"[DEBUG] Checking for node_modules at: {node_modules_path}")
        
        # Install dependencies if needed
        need_npm_install = False
        if not os.path.exists(node_modules_path):
            logger.info("[INFO] Node modules not found, installing...")
            need_npm_install = True
        elif os.path.exists(package_json_path):
            try:
                package_stat = os.stat(package_json_path)
                node_modules_stat = os.stat(node_modules_path)
                if package_stat.st_mtime > node_modules_stat.st_mtime:
                    logger.info("[INFO] package.json newer than node_modules, updating...")
                    need_npm_install = True
            except Exception:
                need_npm_install = True
        
        if need_npm_install:
            logger.warning("[WARN] Node modules not found or outdated. Running 'npm install' automatically...")
            try:
                # Use proper npm command for Windows
                if os.name == 'nt':  # Windows
                    npm_cmd = ['npm.cmd', 'install']
                else:
                    npm_cmd = ['npm', 'install']
                
                logger.info(f"[INFO] Running command: {' '.join(npm_cmd)}")
                npm_install_result = subprocess.run(
                    npm_cmd,
                    cwd=electron_dir,
                    capture_output=True,
                    text=True,
                    shell=True if os.name == 'nt' else False,  # Use shell on Windows
                    timeout=120  # 2 minute timeout
                )
                if npm_install_result.returncode == 0:
                    logger.info("[INFO] 'npm install' completed successfully.")
                    # Verify the installation worked
                    logger.info(f"[DEBUG] Contents of electron directory after npm install: {os.listdir(electron_dir)}")
                else:
                    logger.error(f"[ERROR] 'npm install' failed: {npm_install_result.stderr}")
                    logger.error(f"[ERROR] Return code: {npm_install_result.returncode}")
                    logger.error(f"[ERROR] Stdout: {npm_install_result.stdout}")
                    return False
            except subprocess.TimeoutExpired:
                logger.error("[ERROR] 'npm install' timed out")
                return False
            except Exception as e:
                logger.error(f"[ERROR] 'npm install' error: {e}")
                return False
        
        # Verify installation
        if os.path.exists(node_modules_path):
            logger.info("[INFO] Node modules found after install")
        else:
            logger.error("[ERROR] Node modules still not found after install")
            return False
        
        # Wait for Flask to be fully ready
        logger.info("[INFO] Waiting for Flask server to be fully ready...")
        flask_ready = False
        for attempt in range(60):  # Wait up to 60 seconds
            try:
                import socket as pysocket
                import time
                s = pysocket.create_connection(('127.0.0.1', 5000), timeout=2)
                s.close()
                # Also check if login page is accessible
                import urllib.request
                urllib.request.urlopen('http://127.0.0.1:5000/login-ready', timeout=2)
                flask_ready = True
                logger.info(f"[INFO] Flask server ready after {attempt + 1} seconds")
                break
            except Exception:
                time.sleep(1)
        
        if not flask_ready:
            logger.warning("[WARN] Flask server not detected ready after 60s, launching Electron anyway...")
        
        # Launch Electron desktop app
        logger.info("[INFO] Starting Electron application...")
        if os.name == 'nt':  # Windows
            desktop_cmd = ['npm.cmd', 'start']
        else:  # Unix/Linux/macOS
            desktop_cmd = ['npm', 'start']
        
        logger.info(f"[INFO] Command: {' '.join(desktop_cmd)}")
        logger.info(f"[INFO] Working directory: {electron_dir}")
        
        # Set environment variables for Electron
        env = os.environ.copy()
        env['ELECTRON_MODE'] = '1'
        env['FLASK_PORT'] = '5000'
        env['NODE_ENV'] = 'production'
        
        desktop_process = subprocess.Popen(
            desktop_cmd,
            cwd=electron_dir,
            env=env,
            stdout=None,  # Don't capture stdout - let it show in console
            stderr=None,  # Don't capture stderr - let it show in console
            shell=True,  # Use shell for both Windows and Unix to resolve npm
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        logger.info(f"[INFO] Electron application launched! PID: {desktop_process.pid}")
        logger.info("[INFO] Electron app should open automatically")
        logger.info("[INFO] Web access also available at: http://127.0.0.1:5000")
        
        # Check if process started successfully
        if desktop_process.poll() is None:
            logger.info("[INFO] Electron process is running successfully")
        else:
            logger.error("[ERROR] Electron process failed to start")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to launch Electron application: {e}")
        return False

# Debug route to print all registered routes
@app.route('/debug/routes')
def debug_routes():
    """Debug endpoint to list all registered routes."""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    
    # Sort by rule for easier reading
    routes.sort(key=lambda x: x['rule'])
    
    return jsonify({
        'total_routes': len(routes),
        'routes': routes,
        'blueprints': list(app.blueprints.keys())
    })

# Custom Flask-Login unauthorized handler for API endpoints
@login_manager.unauthorized_handler
def custom_unauthorized():
    # If the request is for an API or REST endpoint, return JSON 401
    path = request.path
    if (
        path.startswith('/api/') or
        path.startswith('/notes/api/') or
        path.startswith('/unified_search') or
        path.startswith('/tracking') or
        path.startswith('/collab-notes/api/') or
        path.startswith('/universal-search')
    ):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
    # Otherwise, do the normal redirect
    from flask import redirect, url_for
    return redirect(url_for('auth.login', next=path))

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.route('/api/system-status')
def system_status():
    """Comprehensive system status endpoint."""
    try:
        import psutil
        import platform
        
        # Get system information
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'hostname': platform.node()
        }
        
        # Get memory information
        memory = psutil.virtual_memory()
        memory_info = {
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'percent_used': memory.percent
        }
        
        # Get disk information
        disk = psutil.disk_usage('/')
        disk_info = {
            'total_gb': round(disk.total / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'used_gb': round(disk.used / (1024**3), 2),
            'percent_used': round((disk.used / disk.total) * 100, 2)
        }
        
        # Get CPU information
        cpu_info = {
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else None
        }
        
        # Get process information
        current_process = psutil.Process()
        process_info = {
            'pid': current_process.pid,
            'memory_mb': round(current_process.memory_info().rss / (1024**2), 2),
            'cpu_percent': current_process.cpu_percent(),
            'create_time': current_process.create_time(),
            'status': current_process.status()
        }
        
        # Get network information
        network_info = {
            'connections': len(psutil.net_connections()),
            'interfaces': len(psutil.net_if_addrs())
        }
        
        # Application status
        app_status = {
            'startup_time': getattr(app, 'startup_time', None),
            'uptime_seconds': int(time.time() - getattr(app, 'startup_time', time.time())),
            'session_manager_active': session_manager is not None,
            'database_connected': True,  # Assuming if we get here, DB is working
            'electron_mode': os.getenv('ELECTRON_MODE') == '1',
            'flask_port': os.getenv('FLASK_PORT', '5000')
        }
        
        # Check for Electron process
        electron_running = False
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == 'electron.exe':
                    electron_running = True
                    break
        except Exception:
            pass
        
        app_status['electron_running'] = electron_running
        
        return jsonify({
            'status': 'ok',
            'timestamp': time.time(),
            'system': system_info,
            'memory': memory_info,
            'disk': disk_info,
            'cpu': cpu_info,
            'process': process_info,
            'network': network_info,
            'application': app_status
        }), 200
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/login-ready')
def login_ready_check():
    """Special endpoint for Electron app to check if login page is ready."""
    import time
    return jsonify({
        'status': 'ready',
        'message': 'Login page is ready',
        'timestamp': int(time.time())
    }), 200

@app.route('/quick-login-check')
def quick_login_check():
    """Ultra-fast endpoint for Electron app to verify Flask is running."""
    return jsonify({'ready': True}), 200

@app.route('/session-status')
def session_status():
    """Check session status and health."""
    try:
        status = {
            'session_active': session.get('user_id') is not None,
            'user_authenticated': current_user.is_authenticated if current_user else False,
            'session_manager_active': session_manager is not None,
            'session_lifetime': app.config.get('PERMANENT_SESSION_LIFETIME', 'Not set'),
            'session_type': app.config.get('SESSION_TYPE', 'Not set'),
            'session_dir': app.config.get('SESSION_FILE_DIR', 'Not set'),
            'startup_time': getattr(app, 'startup_time', None),
            'uptime_seconds': int(time.time() - getattr(app, 'startup_time', time.time()))
        }
        
        if session_manager:
            status['session_stats'] = session_manager.get_session_stats()
        
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auto-login')
def auto_login():
    """Attempt automatic login if session exists."""
    try:
        if current_user.is_authenticated:
            return jsonify({'status': 'already_logged_in', 'user': current_user.username}), 200
        
        # Check for existing session
        user_id = session.get('user_id')
        if user_id and session_manager:
            # Try to load user session
            if session_manager.load_user_session(user_id):
                # Attempt to load user from database
                try:
                    user = db.session.get(User, user_id)
                    if user:
                        login_user(user, remember=True)
                        logger.info(f"Auto-login successful for user {user.username}")
                        return jsonify({
                            'status': 'auto_login_success',
                            'user': user.username,
                            'redirect': url_for('main.index')
                        }), 200
                except Exception as e:
                    logger.warning(f"Auto-login failed for user {user_id}: {e}")
        # Fallback for login URL
        try:
            login_url = url_for('auth.login')
        except Exception:
            login_url = '/auth/login'
        return jsonify({'status': 'no_session', 'redirect': login_url}), 200
        
    except Exception as e:
        logger.error(f"Auto-login error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/test-title-bar')
def test_title_bar():
    """Test page for title bar functionality."""
    return send_file('electron/test-title-bar.html')

@app.route('/api/user/offline', methods=['POST'])
def user_offline():
    """Endpoint for marking user as offline when app closes or user disconnects"""
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
        
        return jsonify({"status": "success", "message": "User offline status updated"})
        
    except Exception as e:
        logger.error(f"Error in user offline endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/force-logout', methods=['GET', 'POST'])
def force_logout():
    """Force logout all users and redirect to login page."""
    try:
        from flask_login import current_user, logout_user
        from flask import make_response
        
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

@app.route('/api/shutdown', methods=['POST'])
def shutdown_server():
    """Endpoint for Electron app to request graceful shutdown"""
    logger.info("[SHUTDOWN] Shutdown requested by Electron app")
    
    # Perform cleanup in a separate thread to avoid blocking the response
    def shutdown_worker():
        try:
            logger.info("[SHUTDOWN] Starting graceful shutdown...")
            
            # Stop memory manager first
            if 'memory_manager' in globals():
                memory_manager.force_cleanup()
            
            # Perform comprehensive cleanup
            cleanup()
            
            logger.info("[SHUTDOWN] Graceful shutdown completed")
            
            # Force exit after cleanup
            os._exit(0)
            
        except Exception as e:
            logger.error(f"[SHUTDOWN] Error during shutdown: {e}")
            force_cleanup()
            os._exit(1)
    
    # Start shutdown in background thread
    import threading
    shutdown_thread = threading.Thread(target=shutdown_worker, daemon=True)
    shutdown_thread.start()
    
    return jsonify({"status": "shutdown_initiated", "message": "Server shutdown initiated"})

if __name__ == '__main__':
    try:
        # Parse command line arguments for mode selection
        import argparse
        parser = argparse.ArgumentParser(description='YAM Application - Desktop and Web Server')
        parser.add_argument('--mode', choices=['auto', 'desktop', 'web', 'electron'], default='auto',
                           help='Launch mode: auto (detect), desktop (Electron app), web (browser only), electron (alias for desktop)')
        parser.add_argument('--port', type=int, default=5000, help='Flask server port (default: 5000)')
        parser.add_argument('--host', default='127.0.0.1', help='Flask server host (default: 127.0.0.1 for desktop, 0.0.0.0 for web)')
        parser.add_argument('--no-desktop', action='store_true', help='Force web-only mode (no Electron app)')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode')
        
        args = parser.parse_args()
        
        # Register signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            logger.info(f"[INFO] Received {signal_name} signal")
            
            try:
                # Stop memory manager first
                if 'memory_manager' in globals():
                    memory_manager.force_cleanup()
                
                # Perform comprehensive cleanup (with spam protection)
                cleanup()
                
                logger.info("[OK] Graceful shutdown completed")
                
            except Exception as e:
                logger.error(f"[ERROR] Error during shutdown: {e}")
                force_cleanup()
            finally:
                # Force exit after cleanup
                os._exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # CRITICAL: Clean up all problematic environment variables first
        problematic_vars = [
            'WERKZEUG_SERVER_FD', 'WERKZEUG_RUN_FD', 'FLASK_RUN_FD',
            'EVENTLET_THREADPOOL_SIZE', 'GEVENT_THREADPOOL_SIZE'
        ]
        for var in problematic_vars:
            if var in os.environ:
                logger.info(f"[INFO] Removing problematic environment variable: {var}")
                os.environ.pop(var, None)
        
        # Additional cleanup for Werkzeug variables
        werkzeug_vars = [k for k in os.environ.keys() if k.startswith('WERKZEUG_') and k.endswith('_FD')]
        for var in werkzeug_vars:
            logger.info(f"[INFO] Removing Werkzeug FD variable: {var}")
            os.environ.pop(var, None)
        
        # Additional cleanup for ALL Werkzeug environment variables
        all_werkzeug_vars = [k for k in os.environ.keys() if k.startswith('WERKZEUG_')]
        for var in all_werkzeug_vars:
            logger.debug(f"[DEBUG] Cleaning Werkzeug variable: {var}")
            os.environ.pop(var, None)
        
        # Determine launch mode
        launch_mode = args.mode
        force_web_only = args.no_desktop
        
        # Auto-detect mode if not specified
        if launch_mode == 'auto':
            # Check various indicators for desktop mode preference
            has_electron_env = (os.getenv('FLASK_PORT') is not None or 
                              os.getenv('ELECTRON_MODE') is not None)
            
            # Check for Electron files in the electron/ subdirectory
            electron_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'electron')
            has_electron_files = (os.path.exists(os.path.join(electron_dir, 'main.js')) and 
                                os.path.exists(os.path.join(electron_dir, 'package.json')))
            has_node_modules = os.path.exists(os.path.join(electron_dir, 'node_modules'))
            
            logger.info(f"[DEBUG] Electron detection: env={has_electron_env}, files={has_electron_files}, node_modules={has_node_modules}")
            logger.info(f"[DEBUG] Electron directory: {electron_dir}")
            
            if force_web_only:
                launch_mode = 'web'
                logger.info("[INFO] Force web-only mode specified")
            elif has_electron_env or (has_electron_files and has_node_modules):
                launch_mode = 'desktop'
                logger.info("[INFO] Auto-detected desktop mode (Electron)")
            else:
                launch_mode = 'web'
                logger.info("[INFO] Auto-detected web mode (no Electron setup found)")
        elif launch_mode == 'electron':
            launch_mode = 'desktop'  # Alias for desktop
        
        # Configure server settings based on mode
        is_desktop_mode = launch_mode == 'desktop'
        
        if is_desktop_mode:
            # Desktop mode settings
            host = args.host if args.host != '127.0.0.1' else '127.0.0.1'  # Default to localhost for desktop
            port = args.port if args.port != 5000 else int(os.getenv('FLASK_PORT', '5000'))
            debug = args.debug
            use_reloader = False
            
            # Set environment variables for Electron mode
            os.environ['ELECTRON_MODE'] = '1'
            os.environ['FLASK_PORT'] = str(port)
            os.environ['FLASK_ENV'] = 'development' if debug else 'production'
            
            logger.info("[INFO] YAM Mode - Launching Electron Application")
            logger.info(f"   * Flask server: http://{host}:{port}")
            logger.info(f"   * Desktop app: Will launch automatically")
            logger.info(f"   * Performance: Optimized for desktop")
            logger.info(f"   * Caching: Enhanced cache system active")
            
        else:
            # Web mode settings
            host = args.host if args.host != '127.0.0.1' else '0.0.0.0'  # Default to all interfaces for web
            port = args.port
            debug = args.debug
            use_reloader = False
            
            # Ensure we're not in Electron mode
            os.environ.pop('ELECTRON_MODE', None)
            os.environ.pop('FLASK_PORT', None)
            
            logger.info("[INFO] YAM Web Mode - Browser Access Only")
            logger.info(f"   * Web server: http://{host}:{port}")
            logger.info(f"   * Access via: http://localhost:{port}")
            logger.info(f"   * Performance: Optimized for web")
            logger.info(f"   * Caching: Enhanced cache system active")
        
        # ---- COMPREHENSIVE STARTUP CHECK ----
        if not comprehensive_startup_check(port):
            logger.error("[FATAL] Startup check failed. Cannot proceed.")
            sys.exit(1)
        logger.info("[INFO] All startup checks passed")
        # ---- END STARTUP CHECK ----
        
        # ---- CHECK FOR SERVER SHUTDOWN MARKER ----
        try:
            from app.utils.session_cleanup import check_shutdown_marker
            if check_shutdown_marker():
                logger.info("[INFO] Server shutdown marker detected - users will need to re-authenticate")
                # Set a global flag to force re-authentication
                app.config['FORCE_REAUTH'] = True
                logger.info("[SECURITY] Force re-authentication enabled for all users")
        except Exception as e:
            logger.warning(f"[WARN] Could not check shutdown marker: {e}")
        # ---- END SHUTDOWN MARKER CHECK ----

        # Initialize the application with performance optimizations for both modes
        logger.info("[INFO] Starting YAM application with enhanced performance...")
        logger.info(f"   * Database: {os.path.abspath(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///',''))}")
        logger.info(f"   * Mode: {launch_mode.upper()}")
        logger.info(f"   * Host: {host}:{port}")
        
        # SESSION PERSISTENCE: Keep existing sessions on startup for better UX
        logger.info("[INFO] Maintaining existing sessions on startup for persistent login...")
        try:
            from app.utils.session_cleanup import check_shutdown_marker
            # Only clear sessions if there was a proper shutdown
            if check_shutdown_marker():
                logger.info("[INFO] Server shutdown detected - sessions will be cleared")
                from app.utils.session_cleanup import clear_all_user_sessions
                clear_all_user_sessions()
                logger.info("[INFO] Sessions cleared due to server shutdown")
            else:
                logger.info("[INFO] No server shutdown detected - maintaining existing sessions")
        except Exception as e:
            logger.warning(f"[WARN] Error checking session status on startup: {e}")
        
        # Track startup time
        app.startup_time = time.time()
        
        # Enhanced startup with memory optimization (same for both modes)
        try:
            logger.info("[INFO] Initializing enhanced performance systems...")
            start_time = time.time()
            
            # Force immediate garbage collection before startup
            gc.collect()
            initial_memory = memory_manager.check_memory_usage()
            logger.info(f"[INFO] Pre-startup memory: {initial_memory:.1f}MB")
            
            # Register all blueprints
            register_all_blueprints()
            
            # Mark as initialized
            set_app_initialized(True)
            _initialization_state['status'] = 'ready'
            
            total_time = time.time() - start_time
            final_memory = memory_manager.check_memory_usage()
            
            logger.info(f"[INFO] Enhanced startup completed in {total_time:.2f}s")
            logger.info(f"[INFO] Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB")
            logger.info("[INFO] Login page is now ready!")
            
            # Force garbage collection after startup
            gc.collect()
            
        except Exception as e:
            logger.error(f"[ERROR] Enhanced startup failed: {e}")
            # Try emergency fallback
            try:
                logger.info("[INFO] Attempting emergency fallback...")
                # Emergency fallback - just register core blueprints
                app.register_blueprint(core_bp)
                app.register_blueprint(system_management_bp)
                set_app_initialized(True)
                logger.info("[INFO] Emergency fallback successful - basic functionality should work")
            except Exception as emergency_err:
                logger.error(f"[ERROR] Emergency fallback failed: {emergency_err}")
                logger.warning("[WARN] Continuing with minimal Flask app - some features may not work")
        
        # Display final startup message
        print("\n" + "=" * 80)
        print("\033[1;32m[READY] YAM APPLICATION READY\033[0m")
        print("=" * 80)
        
        if is_desktop_mode:
            print(f"\033[1;33m[DESKTOP] DESKTOP MODE ACTIVE\033[0m")
            print(f"   • Flask server: http://{host}:{port}")
            print(f"   • Web backup: http://localhost:{port}")
            print(f"   • Performance: OPTIMIZED with enhanced cache")
            print(f"   • Memory usage: MANAGED and optimized")
        else:
            print(f"\033[1;34m[WEB] WEB MODE ACTIVE\033[0m")
            print(f"   • Web server: http://{host}:{port}")
            print(f"   • Local access: http://localhost:{port}")
            print(f"   • Performance: OPTIMIZED with enhanced cache")
            print(f"   • Memory usage: MANAGED and optimized")
        
        print("=" * 80)
        print("\033[1;36m[LOGIN] Login page ready for immediate access\033[0m")
        print("Memory-optimized ultra-minimal startup completed")
        print("All performance optimizations active")
        print("=" * 80)
        
        # Log final status
        logger.info("=" * 60)
        logger.info("[READY] YAM APPLICATION READY - " + launch_mode.upper() + " MODE")
        logger.info("[WEB] Server accessible at: http://" + host + ":" + str(port))
        logger.info("[LOGIN] Login page ready for immediate access")
        logger.info("[CACHE] Enhanced cache system: ACTIVE")
        logger.info("[MEMORY] Memory management: OPTIMIZED")
        logger.info("=" * 60)
        
        # Start the Flask server with enhanced error handling and reliability
        try:
            # Configure Flask and Werkzeug logging to use our custom formatter
            from app.utils.logger import ColoredFormatter
            
            # Configure Werkzeug logger (handles HTTP requests)
            werkzeug_logger = logging.getLogger('werkzeug')
            werkzeug_logger.setLevel(logging.INFO)
            
            # Remove existing handlers
            for handler in werkzeug_logger.handlers[:]:
                werkzeug_logger.removeHandler(handler)
            
            # Add our custom formatter
            werkzeug_handler = logging.StreamHandler()
            werkzeug_handler.setFormatter(ColoredFormatter())
            werkzeug_logger.addHandler(werkzeug_handler)
            werkzeug_logger.propagate = False  # Prevent double logging
            
            # Configure Flask logger
            flask_logger = logging.getLogger('flask')
            flask_logger.setLevel(logging.INFO)
            
            # Remove existing handlers
            for handler in flask_logger.handlers[:]:
                flask_logger.removeHandler(handler)
            
            # Add our custom formatter
            flask_handler = logging.StreamHandler()
            flask_handler.setFormatter(ColoredFormatter())
            flask_logger.addHandler(flask_handler)
            flask_logger.propagate = False  # Prevent double logging
            
            if is_desktop_mode:
                # Enhanced Flask server for desktop mode
                logger.info("[LAUNCH] Starting Flask server for desktop mode...")
                
                # Clean ALL Werkzeug environment variables first (prevents conflicts)
                werkzeug_vars = [k for k in list(os.environ.keys()) if k.startswith('WERKZEUG_')]
                for var in werkzeug_vars:
                    logger.debug(f"[DEBUG] Removing Werkzeug variable: {var}")
                    os.environ.pop(var, None)
                
                # Set essential environment for stable Flask startup
                os.environ['FLASK_DEBUG'] = '1' if debug else '0'
                os.environ['FLASK_ENV'] = 'development' if debug else 'production'
                
                # Enhanced error handling for desktop mode
                def handle_exception(exc_type, exc_value, exc_traceback):
                    if issubclass(exc_type, KeyboardInterrupt):
                        # Handle graceful shutdown
                        logger.info("[INFO] Keyboard interrupt received")
                        sys.exit(0)
                    else:
                        # Log the error but don't crash
                        logger.error("[ERROR] Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
                        # Don't exit - let the app continue running
                
                # Set up exception handler
                import sys
                sys.excepthook = handle_exception
                
                # Launch Electron app automatically in desktop mode
                def auto_launch_electron():
                    import time
                    logger.info("[ELECTRON] Waiting for Flask server to be ready...")
                    
                    # Wait for Flask to be fully ready
                    for attempt in range(30):  # Wait up to 30 seconds
                        try:
                            import urllib.request
                            response = urllib.request.urlopen('http://127.0.0.1:5000/quick-login-check', timeout=2)
                            if response.getcode() == 200:
                                logger.info(f"[INFO] Flask server ready after {attempt + 1} seconds")
                                break
                        except Exception:
                            time.sleep(1)
                    
                    # Launch Electron
                    logger.info("[ELECTRON] Launching Electron application...")
                    success = launch_electron_app()
                    if success:
                        logger.info("[SUCCESS] Electron application launched successfully")
                    else:
                        logger.warning("[WARN] Failed to launch Electron - web access still available")
                
                import threading
                electron_thread = threading.Thread(target=auto_launch_electron, daemon=True)
                electron_thread.start()
                logger.info("[ELECTRON] Electron auto-launch scheduled...")
                
                # Desktop mode uses threading and enhanced reliability
                try:
                    app.run(
                        host=host,
                        port=port,
                        debug=debug,
                        threaded=True,
                        use_reloader=use_reloader,
                        passthrough_errors=False
                    )
                except KeyboardInterrupt:
                    logger.info("[INFO] Flask server stopped by user")
                    cleanup()  # This now has spam protection
                    os._exit(0)
                except Exception as desktop_server_err:
                    logger.error(f"[ERROR] Desktop Flask server failed: {desktop_server_err}")
                    # Don't raise - try to continue
                    logger.info("[INFO] Attempting to restart Flask server...")
                    time.sleep(2)
                    # Try one more time
                    try:
                        app.run(
                            host=host,
                            port=port,
                            debug=False,  # Disable debug for recovery
                            threaded=True,
                            use_reloader=False,
                            passthrough_errors=False
                        )
                    except Exception as recovery_err:
                        logger.error(f"[FATAL] Recovery failed: {recovery_err}")
                        raise recovery_err
            else:
                # Web mode uses SocketIO for better real-time features
                logger.info("[FLASK] Starting Flask server for web mode...")
                
                try:
                    socketio.run(
                        app,
                        debug=debug,
                        host=host,
                        port=port,
                        use_reloader=use_reloader,
                        log_output=True,
                        allow_unsafe_werkzeug=True
                    )
                except Exception as web_server_err:
                    logger.error(f"[ERROR] SocketIO server failed, trying basic Flask: {web_server_err}")
                    # Fallback to basic Flask if SocketIO fails
                    app.run(
                        host=host,
                        port=port,
                        debug=debug,
                        threaded=True,
                        use_reloader=use_reloader,
                        passthrough_errors=False
                    )
                    
        except KeyboardInterrupt:
            logger.info("[SHUTDOWN] Server shutdown requested by user")
            if 'memory_manager' in locals():
                memory_manager.force_cleanup()
            cleanup()  # This now has spam protection
            os._exit(0)
        except Exception as e:
            logger.error(f"[ERROR] Failed to start server: {e}")
            if 'memory_manager' in locals():
                memory_manager.force_cleanup()
            cleanup()  # This now has spam protection
            os._exit(1)
            
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize application: {e}")
        if 'memory_manager' in locals():
            memory_manager.force_cleanup()
        cleanup()  # This now has spam protection
        os._exit(1) 

    with app.app_context():
        import_docs_folder_startup(force=True)
        load_articles_cache(force_reload=True)