from flask import Blueprint, current_app
from flask_login import login_required
import os
import sqlite3
from datetime import datetime
from app.extensions import db

bp = Blueprint('db', __name__)

# Database paths
DB_PATH = 'kb_fresh4.db'
QUESTIONS_DB = 'servicedesk_ai.db'
SESSION_TRACKER_FILE = 'user_sessions.json'
CHAT_QA_DB = 'chat_qa.db'
CACHE_DB = 'cache.db'

@bp.route('/init')
def init_database():
    with current_app.app_context():
        # Create database directory if it doesn't exist
        db_dir = os.path.join(os.path.dirname(current_app.root_path), 'db')
        os.makedirs(db_dir, exist_ok=True)
        
        # Set database URI to a persistent file
        current_app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(db_dir, 'app.db')}"
        
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            try:
                # Create admin user if it doesn't exist
                admin = User(
                    username='admin',
                    email='admin@pdshealth.com',
                    role='admin',
                    is_active=True,
                    profile_picture='boy.png',
                    okta_verified=False,
                    teams_notifications=True,
                    created_at=datetime.utcnow()
                )
                admin.set_password('admin123')  # Set default password
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating admin user: {e}")
        else:
            try:
                # Update admin user if it exists
                admin.email = 'admin@pdshealth.com'
                admin.set_password('admin123')  # Reset password to default
                admin.is_active = True
                admin.role = 'admin'
                db.session.commit()
                print("Admin user updated successfully!")
            except Exception as e:
                db.session.rollback()
                print(f"Error updating admin user: {e}")

    # Initialize cache table
    cache_conn = sqlite3.connect(QUESTIONS_DB)
    cache_cur = cache_conn.cursor()

    cache_cur.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            query      TEXT PRIMARY KEY,
            raw_json   TEXT,
            summary    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cache_conn.commit()
    cache_conn.close()
    
    return {'status': 'success', 'message': 'Database initialized successfully'} 