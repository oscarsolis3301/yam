"""
Session configuration for YAM application
"""

from datetime import timedelta

# Session configuration
SESSION_CONFIG = {
    'PERMANENT_SESSION_LIFETIME': timedelta(days=30),
    'SESSION_TYPE': 'filesystem',
    'SESSION_FILE_THRESHOLD': 1000,
    'SESSION_REFRESH_EACH_REQUEST': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SECURE': False,  # Set to True in production with HTTPS
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_COOKIE_NAME': 'yam_session'
}

def apply_session_config(app):
    """Apply session configuration to Flask app"""
    for key, value in SESSION_CONFIG.items():
        app.config[key] = value
    
    # Ensure session directory exists
    import os
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions')
    os.makedirs(session_dir, exist_ok=True)
    app.config['SESSION_FILE_DIR'] = session_dir
