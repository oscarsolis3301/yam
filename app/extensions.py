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
    UPLOAD_FOLDER = 'static/uploads'  # Base upload folder for file serving
    DB_DIR = 'db'
    BASE_DIR = Path(__file__).parent.resolve()
    
    # Model configuration
    MODEL_NAME = 'orca-mini-3b.gguf'
    EMBEDDER_PATH = str(BASE_DIR / 'data' / 'models' / 'local_embedder')
    IMAGE_MODEL = 'Salesforce/blip-image-captioning-base'
    
    @classmethod
    def validate(cls):
        """Validate configuration settings."""
        try:
            # Check if required directories exist or can be created
            Path(cls.MODELS_DIR).mkdir(parents=True, exist_ok=True)
            Path(cls.UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
            Path(cls.DB_DIR).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    # Freshworks API configuration
    FRESH_ENDPOINT = 'https://your-domain.freshdesk.com'
    FRESH_API = 'your-api-key'
    
    # Ticket configuration
    TICKET_STATUSES = {
        2: "Open",
        3: "Pending", 
        4: "Resolved",
        5: "Closed"
    }
    
    TICKET_SOURCES = {
        1: "Email",
        2: "Portal",
        3: "Phone",
        4: "Chat",
        5: "Feedback Widget",
        6: "Outbound Email"
    }
    
    TICKET_PRIORITIES = {
        1: "Low",
        2: "Medium",
        3: "High",
        4: "Urgent"
    }

def init_extensions(app):
    """Initialize all extensions with the Flask app."""
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    migrate.init_app(app, db) 