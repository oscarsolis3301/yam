from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
import logging
from pathlib import Path

from .config import Config
from extensions import db, login_manager, socketio, migrate, init_extensions

# Import blueprints
from .blueprints.auth import bp as auth_bp, init_auth_blueprint
from .blueprints.main import bp as main_bp
from .blueprints.admin import bp as admin_bp
from .blueprints.ai import bp as ai_bp
from .blueprints.kb import bp as kb_bp
from .blueprints.kb_api import bp as kb_api_bp
from .blueprints.outages import bp as outages_bp
from .blueprints.profile import bp as profile_bp
from .blueprints.settings import bp as settings_bp
from .blueprints.time import bp as time_bp
from .blueprints.users import bp as users_bp
from .blueprints.utils import bp as utils_bp
from .blueprints.tracking import bp as tracking_bp, init_tracking_blueprint
from .blueprints.collab_notes import bp as collab_notes_bp
from .blueprints.universal_search import bp as universal_search_bp
from .blueprints.dameware import bp as dameware_bp
from .blueprints.users.clock_id_routes import bp as clock_id_cache_bp
from .blueprints.api.chat_routes import chat_bp
from .blueprints.workstations import bp as workstations_bp
from .blueprints.team import bp as team_bp
from .blueprints.tickets import bp as tickets_bp
from .blueprints.settings_api import bp as settings_api_bp

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Add template context processor to ensure current_user is always available
    @app.context_processor
    def inject_current_user():
        from flask_login import current_user
        return dict(current_user=current_user)
    
    # Initialize model conflicts resolution at startup
    with app.app_context():
        try:
            from app.models import initialize_models_safely
            initialize_models_safely()
        except Exception as e:
            app.logger.warning(f"Model initialization failed: {e}")
    
    # Setup logging
    logging.basicConfig(
        level=app.config['LOG_LEVEL'],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=app.config['LOG_FILE']
    )
    
    # Ensure required directories exist
    for dir_path in [app.config['DATA_DIR'], app.config['MODELS_DIR'], 
                    app.config['UPLOADS_DIR'], app.config['DB_DIR']]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    with app.app_context():
        # Ensure model registration to prevent conflicts
        from app.models import cleanup_model_registry, ensure_model_registration, resolve_searchhistory_conflicts
        cleanup_model_registry()
        ensure_model_registration()
        resolve_searchhistory_conflicts()
        
        # Initialize database
        db.create_all()
        
        # Initialize session middleware
        from app.utils.session_middleware import init_session_middleware
        init_session_middleware(app)
        
        # Initialize presence service and socket handlers
        _initialize_presence_system(app)
        
        # Register blueprints - auth first
        init_auth_blueprint(app)
        app.register_blueprint(main_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(ai_bp)
        app.register_blueprint(kb_bp)
        app.register_blueprint(kb_api_bp)
        app.register_blueprint(outages_bp)
        app.register_blueprint(profile_bp)
        app.register_blueprint(settings_bp)
        app.register_blueprint(time_bp)
        app.register_blueprint(users_bp)
        app.register_blueprint(utils_bp)
        init_tracking_blueprint(app)
        app.register_blueprint(collab_notes_bp)
        app.register_blueprint(universal_search_bp)  # Universal Search API
        app.register_blueprint(dameware_bp)  # Dameware Remote Connection
        app.register_blueprint(clock_id_cache_bp)  # Clock ID Cache API
        app.register_blueprint(chat_bp, url_prefix='/api/chat')  # Team Chat API
        app.register_blueprint(workstations_bp)  # Workstations
        app.register_blueprint(team_bp)  # Team
        app.register_blueprint(tickets_bp)  # Tickets
        app.register_blueprint(settings_api_bp, url_prefix='/api/settings')  # Settings API
        
        # Import and register private messages blueprint
        from app.blueprints.api.private_messages import private_messages_bp
        app.register_blueprint(private_messages_bp, url_prefix='/api/private-messages')  # Private Messages API
    
    return app

def _initialize_presence_system(app):
    """Initialize the comprehensive user presence system."""
    try:
        # Initialize presence service with app context
        from app.utils.user_activity import initialize_presence_service
        initialize_presence_service(app)
        
        # Set app context for socket handlers
        from app.socket_handlers.connection import set_flask_app, schedule_periodic_cleanup
        set_flask_app(app)
        
        # Import socket handlers to register them (this triggers the @socketio.on decorators)
        import app.socket_handlers.connection  # noqa: F401
        import app.socket_handlers.admin_presence  # noqa: F401
        import app.socket_handlers.team_chat  # noqa: F401
        
        # Start periodic cleanup task
        schedule_periodic_cleanup()
        
        print("User presence system initialized successfully")
        
    except Exception as e:
        print(f"Error initializing presence system: {e}")
        # Don't fail app startup, but log the error 