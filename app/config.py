#!/usr/bin/env python3
"""
Configuration management for YAM Client
Handles app settings, environment variables, and configuration loading/saving
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Freshworks API Configuration
FRESH_ENDPOINT = os.getenv('FRESH_ENDPOINT', 'https://disabled.freshservice.com/api/v2/')
FRESH_API = os.getenv('FRESH_API', 'disabled-api-key')


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


# Configuration class for Flask application
class Config:
    """Configuration class for Flask application."""
    from pathlib import Path
    BASE_DIR = Path(__file__).parent.resolve()
    DATA_DIR = 'data'
    MODELS_DIR = 'data/models'
    UPLOADS_DIR = 'uploads'
    UPLOAD_FOLDER = 'static/uploads'  # Base upload folder for file serving
    DB_DIR = 'db'
    DB_PATH = str(BASE_DIR / 'db' / 'app.db')
    
    # Flask settings
    SECRET_KEY = 'server-key-2025'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 7200  # 2 hours
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