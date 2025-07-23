import os
import logging
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Always load .env from the app/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Freshdesk API Configuration
FRESH_ENDPOINT = os.getenv('FRESH_ENDPOINT', 'https://disabled.freshservice.com/api/v2/')
FRESH_API = os.getenv('FRESH_API', 'disabled-api-key')

# Ticket Status Mappings
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

class Config:
    # Flask settings
    SECRET_KEY = 'REPLACE_WITH_A_STRONG_RANDOM_SECRET_KEY_2025'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # 2 hours for better stability
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Status mappings
    STATUSES = {
        'online': 'Online',
        'away': 'Away',
        'busy': 'Busy',
        'offline': 'Offline'
    }
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    MODELS_DIR = DATA_DIR / "models"
    UPLOADS_DIR = BASE_DIR / 'uploads'
    DB_DIR = BASE_DIR / 'app' / 'db'  # Centralized database directory
    CACHE_DIR = BASE_DIR / 'cache'
    SESSION_TRACKER_FILE = str(BASE_DIR / 'session_tracker.json')
    
    # Ensure directories exist
    for dir_path in [DATA_DIR, MODELS_DIR, UPLOADS_DIR, DB_DIR, CACHE_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Model settings
    # ------------------------------------------------------------------
    # GPT4All model – use an official file name recognised by the hub. The
    # "Q4_K_M" quantised variant keeps memory usage reasonable (~4-5 GB)
    # while offering good quality for an offline fallback.
    # ------------------------------------------------------------------
    # Default local GGUF file shipped with this repository.  Administrators can
    # replace it with any other GPT4All-compatible file without changing code –
    # validation logic below auto-discovers alternative names if the default is
    # missing.
    MODEL_NAME = "orca-mini-3b.gguf"
    MODEL_TYPE = "gguf"  # Explicit model type for GPT4All (avoids .bin suffix)

    # Local cache path – file will be stored under *data/models/* if the
    # application downloads it automatically the first time.
    MODEL_PATH = str((Path(__file__).parent.parent / 'data' / 'models' / MODEL_NAME).resolve())
    # Direct download fallback – used when GPT4All hub fails. Default points to
    # the official HF mirror of the same file name.
    MODEL_DOWNLOAD_URL = os.getenv(
        'MODEL_DOWNLOAD_URL',
        'https://huggingface.co/TheBloke/orca-mini-3b-gguf/resolve/main/orca-mini-3b.Q4_K_M.gguf',
    )
    EMBEDDER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Default embedder model
    # Legacy attribute used by some helper modules – map to EMBEDDER_MODEL to
    # maintain backward-compatibility without needing widespread refactors.
    SENTENCE_TRANSFORMER_MODEL = EMBEDDER_MODEL
    EMBEDDER_PATH = str(MODELS_DIR / 'local_embedder')  # Local embedder path
    # When set to 'true' (case-insensitive) the application skips any network
    # download attempts for large models and relies solely on *existing* local
    # files.  This can also be controlled via an environment variable so that
    # administrators can toggle the behaviour without editing source code.
    OFFLINE_MODE = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'
    USE_LOCAL_EMBEDDER = True  # Use local embedder if available
    MAX_CONTEXT_LENGTH = 1000
    MAX_TOKENS = 200
    TEMPERATURE = 0.7

    # Database paths
    DB_PATH = str(DB_DIR / 'admin_dashboard.db')
    QUESTIONS_DB = str(DB_DIR / 'servicedesk_ai.db')
    CHAT_QA_DB = str(DB_DIR / 'chat_qa.db')
    CACHE_DB = str(DB_DIR / 'cache.db')
    FRESHWORKS_DB = str(DB_DIR / 'freshworks.db')  # Dedicated Freshworks database
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FILE = str(BASE_DIR / 'spark.log')
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_DIR}/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection pool settings to prevent connection exhaustion
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 50,  # Increased pool size for better concurrency
        'pool_timeout': 60,  # Increased timeout to handle connection delays
        'pool_recycle': 3600,  # Recycle connections every hour
        'pool_pre_ping': True,  # Verify connections before use
        'max_overflow': 50,  # Increased overflow limit
        'echo': False,  # Set to True for SQL debugging
        'connect_args': {
            'timeout': 30,  # SQLite connection timeout
            'check_same_thread': False,  # Allow multi-threaded access
            'isolation_level': None  # Autocommit mode for better performance
        }
    }
    
    # Upload settings
    UPLOAD_FOLDER = str(UPLOADS_DIR)
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Application settings
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = os.getenv('FLASK_TESTING', 'False').lower() == 'true'
    
    # Sources configuration
    SOURCES = {
        'kb': {
            'name': 'Knowledge Base',
            'description': 'Internal knowledge base articles',
            'icon': 'book',
            'color': '#4CAF50'
        },
        'tickets': {
            'name': 'Tickets',
            'description': 'Support tickets and their resolutions',
            'icon': 'ticket',
            'color': '#2196F3'
        },
        'devices': {
            'name': 'Devices',
            'description': 'Network devices and their configurations',
            'icon': 'server',
            'color': '#FF9800'
        }
    }
    
    # Priority levels for tickets and tasks
    PRIORITIES = {
        'low': {
            'name': 'Low',
            'color': '#4CAF50',
            'icon': 'arrow-down'
        },
        'medium': {
            'name': 'Medium',
            'color': '#FFC107',
            'icon': 'minus'
        },
        'high': {
            'name': 'High',
            'color': '#FF9800',
            'icon': 'arrow-up'
        },
        'urgent': {
            'name': 'Urgent',
            'color': '#F44336',
            'icon': 'exclamation'
        }
    }
    
    # Cloud AI settings
    USE_CLOUD_AI = os.getenv('USE_CLOUD_AI', 'true').lower() == 'true'
    CLOUD_AI_ENDPOINT = os.getenv('CLOUD_AI_ENDPOINT', 'https://spark.oscarsolis3301.workers.dev/')
    
    # Safe int conversion for timeout
    try:
        timeout_str = os.getenv('CLOUD_AI_TIMEOUT', '5')
        CLOUD_AI_TIMEOUT = int(timeout_str) if timeout_str and timeout_str.strip() else 5
    except (ValueError, TypeError):
        CLOUD_AI_TIMEOUT = 5  # Default fallback
    
    # Developer contact settings
    DEVELOPER_EMAIL = os.getenv('DEVELOPER_EMAIL', 'oscar.solis@pdshealth.com')
    DEVELOPER_NAME = os.getenv('DEVELOPER_NAME', 'Oscar Solis')
    DEVELOPER_TEAMS_ID = os.getenv('DEVELOPER_TEAMS_ID', '')  # Optional Teams user ID for direct chat
    
    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        try:
            # Check if model directory exists
            if not cls.MODELS_DIR.exists():
                cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            
            # ------------------------------------------------------------------
            # Locate a usable *.gguf/*.bin file if the configured one is absent
            # ------------------------------------------------------------------
            if not Path(cls.MODEL_PATH).exists():
                alt_model = None
                for pattern in ("*.gguf", "*.bin"):
                    found = list(cls.MODELS_DIR.glob(pattern))
                    if found:
                        alt_model = found[0]
                        break

                if alt_model:
                    cls.MODEL_PATH = str(alt_model.resolve())
                    cls.MODEL_NAME = alt_model.name
                    logging.info(f"Using discovered local model at {cls.MODEL_PATH}")
                else:
                    logging.warning(f"Local model not found at {cls.MODEL_PATH}")
            
            # Check if local embedder exists – only log INFO to avoid alarming
            if not Path(cls.EMBEDDER_PATH).exists():
                logging.info(f"No local sentence-transformer found at {cls.EMBEDDER_PATH}; will use hub model")
            
            return True
        except Exception as e:
            logging.error(f"Configuration validation failed: {e}")
            return False

# Ensure directories exist and validate configuration
os.makedirs(Config.DB_DIR, exist_ok=True)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.CACHE_DIR, exist_ok=True)

# Try to validate and download models, but don't fail if it doesn't work
try:
    Config.validate()
except Exception as e:
    logging.getLogger('spark').error(f"Error during model validation: {e}")

# Status and priority mappings
STATUSES = {
    2: "Open",
    3: "Pending",
    4: "Resolved",
    5: "Closed",
    6: "N/A",
    7: "N/A",
    8: "User Unavailable",
    9: "Awaiting Information",
    10: "On Hold"
}

SOURCES = {
    1: "Email",
    2: "Portal",
    3: "Phone",
    4: "Chat",
    5: "Feedback widget",
    6: "Yammer",
    7: "AWS Cloud",
    8: "Pagerduty",
    9: "Walkup",
    10: "Slack",
    1002: "ADAPT"
}

PRIORITIES = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Urgent"
} 