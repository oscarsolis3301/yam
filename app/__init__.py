#!/usr/bin/env python3
"""
Flask extensions and database configuration
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
import os
from pathlib import Path

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
migrate = Migrate()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Database configuration
def get_database_path():
    """Get the database file path."""
    current_dir = Path(__file__).parent.resolve()
    db_dir = current_dir / 'db'
    db_dir.mkdir(exist_ok=True)
    return str(db_dir / 'app.db')

# Database URI configuration
def get_database_uri():
    """Get the database URI for SQLAlchemy."""
    db_path = get_database_path()
    return f'sqlite:///{db_path}'

# Default configuration
class Config:
    """Default configuration class."""
    SECRET_KEY = 'server-key-2025'
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 7200  # 2 hours
    SESSION_FILE_THRESHOLD = 1000
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'yam_session'
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    
    # Additional configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'
    DATA_DIR = 'data'
    MODELS_DIR = 'data/models'
    UPLOADS_DIR = 'uploads'
    DB_DIR = 'db'

def init_extensions(app):
    """Initialize all extensions with the Flask app."""
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    migrate.init_app(app, db)

#!/usr/bin/env python3
"""
Configuration management for YAM Client
Handles app settings, environment variables, and configuration loading/saving
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration and settings."""
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir or Path.cwd() / "yam_workspace"
        self.settings_file = self.workspace_dir / "data" / "app-settings.json"
        self._settings = None
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings."""
        return {
            "defaultServerUrl": "http://127.0.0.1:5000",
            "autoConnect": True,
            "connectionTimeout": 10000,
            "maxReconnectAttempts": 5,
            "discoveredServers": [],
            "lastUsedServer": "http://127.0.0.1:5000",
            "portableMode": True,
            "theme": "default",
            "language": "en",
            "logLevel": "info",
            "enableDebugMode": False,
            "autoUpdateCheck": True,
            "startupDelay": 1000,
            "windowState": {
                "width": 1600,
                "height": 1000,
                "maximized": True
            }
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create default if not exists."""
        if self._settings is not None:
            return self._settings
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                default_settings = self.get_default_settings()
                for key, value in default_settings.items():
                    if key not in self._settings:
                        self._settings[key] = value
                return self._settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Failed to load settings: {e}")
                self._settings = self.get_default_settings()
                return self._settings
        else:
            self._settings = self.get_default_settings()
            self.save_settings()
            return self._settings
    
    def save_settings(self) -> bool:
        """Save current settings to file."""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings or self.get_default_settings(), f, indent=2)
            return True
        except IOError as e:
            print(f"❌ Failed to save settings: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        settings = self.load_settings()
        return settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a specific setting value."""
        if self._settings is None:
            self.load_settings()
        self._settings[key] = value
        return self.save_settings()
    
    def get_environment_config(self) -> Dict[str, str]:
        """Get environment-specific configuration."""
        return {
            'YAM_WORKSPACE': str(self.workspace_dir),
            'NODE_ENV': 'development',
            'ELECTRON_IS_DEV': 'true',
            'YAM_LOG_LEVEL': self.get_setting('logLevel', 'info'),
            'YAM_DEBUG_MODE': str(self.get_setting('enableDebugMode', False)).lower(),
            'YAM_SERVER_URL': self.get_setting('defaultServerUrl', 'http://127.0.0.1:5000')
        }
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server connection configuration."""
        return {
            'url': self.get_setting('defaultServerUrl', 'http://127.0.0.1:5000'),
            'timeout': self.get_setting('connectionTimeout', 10000),
            'maxAttempts': self.get_setting('maxReconnectAttempts', 5),
            'autoConnect': self.get_setting('autoConnect', True)
        }
    
    def get_window_config(self) -> Dict[str, Any]:
        """Get window configuration."""
        return self.get_setting('windowState', {
            'width': 1600,
            'height': 1000,
            'maximized': True
        })


# Import Config class from extensions to avoid circular imports
try:
    from app.extensions import Config
except ImportError:
    # Fallback configuration if extensions is not available
    class Config:
        """Fallback configuration class."""
        SECRET_KEY = 'server-key-2025'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SESSION_TYPE = 'filesystem'
        PERMANENT_SESSION_LIFETIME = 7200
        JSON_AS_ASCII = False
        TEMPLATES_AUTO_RELOAD = True
        SEND_FILE_MAX_AGE_DEFAULT = 0


def get_config(workspace_dir: Optional[Path] = None) -> ConfigManager:
    """Get a configuration manager instance."""
    return ConfigManager(workspace_dir)


def load_app_config() -> Dict[str, Any]:
    """Load application configuration."""
    config = ConfigManager()
    return config.load_settings()


def get_server_url() -> str:
    """Get the default server URL from configuration."""
    config = ConfigManager()
    return config.get_setting('defaultServerUrl', 'http://127.0.0.1:5000')


def get_workspace_path() -> Path:
    """Get the workspace path from configuration."""
    config = ConfigManager()
    return config.workspace_dir

from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
import logging
from pathlib import Path

# Import Config from extensions
try:
    from app.extensions import Config
except ImportError:
    # Fallback if extensions is not available
    class Config:
        SECRET_KEY = 'server-key-2025'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SESSION_TYPE = 'filesystem'
        PERMANENT_SESSION_LIFETIME = 7200
        JSON_AS_ASCII = False
        TEMPLATES_AUTO_RELOAD = True
        SEND_FILE_MAX_AGE_DEFAULT = 0

# Import extensions
try:
    from app.extensions import db, login_manager, socketio, migrate, init_extensions
except ImportError:
    # Create fallback extensions if not available
    from flask_sqlalchemy import SQLAlchemy
    from flask_login import LoginManager
    from flask_socketio import SocketIO
    from flask_migrate import Migrate
    
    db = SQLAlchemy()
    login_manager = LoginManager()
    socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
    migrate = Migrate()
    
    def init_extensions(app):
        db.init_app(app)
        login_manager.init_app(app)
        socketio.init_app(app)
        migrate.init_app(app, db)

# Import blueprints
try:
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
    from .blueprints.api import bp as api_bp
    from .blueprints.workstations import bp as workstations_bp
    from .blueprints.team import bp as team_bp
    from .blueprints.tickets import bp as tickets_bp
    from .blueprints.tickets_api import tickets_api_bp
    from .blueprints.settings_api import bp as settings_api_bp
    from .blueprints.freshworks_linking import bp as freshworks_linking_bp
except ImportError as e:
    print(f"Warning: Some blueprints could not be imported: {e}")

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    init_extensions(app)
    
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
        level=getattr(app.config, 'LOG_LEVEL', 'INFO'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=getattr(app.config, 'LOG_FILE', 'app.log')
    )
    
    # Ensure required directories exist
    data_dir = getattr(app.config, 'DATA_DIR', 'data')
    models_dir = getattr(app.config, 'MODELS_DIR', 'data/models')
    uploads_dir = getattr(app.config, 'UPLOADS_DIR', 'uploads')
    db_dir = getattr(app.config, 'DB_DIR', 'db')
    
    for dir_path in [data_dir, models_dir, uploads_dir, db_dir]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    with app.app_context():
        # Ensure model registration to prevent conflicts
        try:
            from app.models import cleanup_model_registry, ensure_model_registration, resolve_searchhistory_conflicts
            cleanup_model_registry()
            ensure_model_registration()
            resolve_searchhistory_conflicts()
        except Exception as e:
            app.logger.warning(f"Model registration failed: {e}")
        
        # Initialize database
        db.create_all()
        
        # Initialize persistent leaderboard timer service
        try:
            from app.services.leaderboard_timer_service import get_leaderboard_timer_service
            # Start the timer service with 60-minute interval
            leaderboard_timer_service = get_leaderboard_timer_service()
            leaderboard_timer_service.start_timer_service(60)
            app.logger.info("✅ Persistent leaderboard timer service started")
        except Exception as e:
            app.logger.warning(f"Failed to start leaderboard timer service: {e}")
        
        # Try to register blueprints if they exist
        try:
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
            app.register_blueprint(universal_search_bp)
            app.register_blueprint(dameware_bp)
            app.register_blueprint(clock_id_cache_bp)
            app.register_blueprint(chat_bp, url_prefix='/api/chat')
            app.register_blueprint(api_bp, url_prefix='/api')
            app.register_blueprint(workstations_bp)
            app.register_blueprint(team_bp)
            app.register_blueprint(tickets_bp)
            app.register_blueprint(tickets_api_bp)
            app.register_blueprint(settings_api_bp, url_prefix='/api/settings')
            app.register_blueprint(freshworks_linking_bp)
            
            # Import and register private messages blueprint
            from app.blueprints.api.private_messages import private_messages_bp
            app.register_blueprint(private_messages_bp, url_prefix='/api/private-messages')
        except Exception as e:
            app.logger.warning(f"Blueprint registration failed: {e}")
    
    return app 