# reset_db.py
# ---------------------------------------------------------------------------
# Standard library imports
# ---------------------------------------------------------------------------
import os
import sys
import time
import psutil
import signal
import sqlite3
from datetime import datetime
import logging
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure that the project root directory (one level up from this file) is on
# PYTHONPATH so that absolute imports like `extensions` and `models` resolve
# to the *root-level* modules instead of accidentally picking up siblings in
# the current directory.  This prevents circular-import problems such as:
#   ImportError: cannot import name 'login_manager' from partially initialized module 'extensions'
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Third-party / application imports (now that PYTHONPATH is patched)
# ---------------------------------------------------------------------------
from flask import Flask
from app.extensions import db  # use the root-level singleton instance
from app.models import (
    User,
    SearchHistory,
    SystemSettings,
    UserSettings,
    Note,
    Activity,
    Document,
    KBArticle,
    KBAttachment,
    SharedLink,
    KBFeedback,
    FreshworksUserMapping,
    TicketClosure,
)

logger = logging.getLogger(__name__)

def load_freshworks_team_members():
    """Load team members from Freshworks IDs.txt file"""
    team_members = []
    ids_file_path = os.path.join(PROJECT_ROOT, 'app', 'Freshworks', 'IDs.txt')
    
    try:
        if os.path.exists(ids_file_path):
            with open(ids_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ' - ' in line:
                        name, freshworks_id = line.split(' - ', 1)
                        # Clean up the name and create email
                        clean_name = name.strip()
                        # Create email from name (first name + @pdshealth.com)
                        first_name = clean_name.split()[0].lower()
                        email = f"{first_name}@pdshealth.com"
                        
                        team_members.append({
                            'username': clean_name,
                            'email': email,
                            'freshworks_id': freshworks_id.strip()
                        })
            print(f"✓ Loaded {len(team_members)} team members from Freshworks IDs.txt")
        else:
            print(f"⚠️ Freshworks IDs.txt not found at {ids_file_path}")
    except Exception as e:
        print(f"Error loading Freshworks team members: {e}")
    
    return team_members

def create_users_from_ticket_closures():
    """Create user accounts for team members found in Daily Ticket Closures database"""
    try:
        # Get all unique Freshworks users from the mapping table
        mappings = FreshworksUserMapping.query.all()
        created_users = []
        
        for mapping in mappings:
            if mapping.freshworks_username:
                # Check if user already exists
                existing_user = User.query.filter_by(username=mapping.freshworks_username).first()
                if not existing_user:
                    # Create email from username
                    first_name = mapping.freshworks_username.split()[0].lower()
                    email = f"{first_name}@pdshealth.com"
                    
                    # Create new user
                    user = User(
                        username=mapping.freshworks_username,
                        email=email,
                        role='user',
                        is_active=True,
                        profile_picture='default.png',
                        okta_verified=False,
                        teams_notifications=True
                    )
                    user.set_password('password')  # Set default password
                    db.session.add(user)
                    created_users.append(mapping.freshworks_username)
                    print(f"➕ Created user from ticket closures: {mapping.freshworks_username}")
        
        if created_users:
            db.session.commit()
            print(f"✓ Created {len(created_users)} users from ticket closures database")
            print(f"Created users: {', '.join(created_users)}")
        else:
            print("✓ No new users to create from ticket closures database")
            
    except Exception as e:
        print(f"Error creating users from ticket closures: {e}")
        db.session.rollback()

def kill_processes_using_file(file_path):
    """Kill all processes that have the specified file open."""
    killed_processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                # Check if process has the file open
                if proc.info['open_files']:
                    for file_info in proc.info['open_files']:
                        if file_path.lower() in file_info.path.lower():
                            print(f"Found process {proc.info['name']} (PID: {proc.info['pid']}) using {file_path}")
                            proc.terminate()
                            killed_processes.append(proc.info['pid'])
                            print(f"Terminated process {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Wait for processes to terminate
        if killed_processes:
            print("Waiting for processes to terminate...")
            time.sleep(2)
            
            # Force kill if still running
            for pid in killed_processes[:]:  # Copy list to avoid modification during iteration
                try:
                    proc = psutil.Process(pid)
                    if proc.is_running():
                        print(f"Force killing process {pid}")
                        proc.kill()
                except psutil.NoSuchProcess:
                    pass
                    
    except Exception as e:
        print(f"Warning: Could not check for processes using file: {e}")
    
    return killed_processes

def close_all_db_connections():
    """Close all database connections and dispose of the engine."""
    try:
        # Close all sessions
        if hasattr(db, 'session'):
            db.session.close()
        
        # Dispose of the engine to close all connections
        if hasattr(db, 'engine') and db.engine:
            db.engine.dispose()
            print("Database engine disposed successfully")
            
        # Also try to close any SQLAlchemy connections
        if hasattr(db, 'get_engine'):
            engine = db.get_engine()
            if engine:
                engine.dispose()
                print("Database engine disposed via get_engine")
                
    except Exception as e:
        print(f"Warning: Could not close database connections: {e}")

def wait_for_file_unlock(file_path, max_wait=30):
    """Wait for a file to become unlocked, with timeout."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # Try to open the file in exclusive mode
            with open(file_path, 'r+b') as f:
                # If we can open it, it's not locked
                break
        except (PermissionError, OSError):
            print(f"File {file_path} is still locked, waiting...")
            time.sleep(1)
    else:
        raise TimeoutError(f"File {file_path} remained locked after {max_wait} seconds")

def safe_remove_file(file_path, max_retries=5):
    """Safely remove a file, handling locks and retrying if necessary."""
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                # First, try to close any processes using the file
                kill_processes_using_file(file_path)
                
                # Wait a moment for processes to fully close
                time.sleep(1)
                
                # Try to remove the file
                os.remove(file_path)
                print(f"Successfully removed: {file_path}")
                return True
                
        except PermissionError as e:
            print(f"Attempt {attempt + 1}: Permission denied removing {file_path}: {e}")
            if attempt < max_retries - 1:
                print("Retrying after closing connections...")
                close_all_db_connections()
                kill_processes_using_file(file_path)
                time.sleep(2)
            else:
                print(f"Failed to remove {file_path} after {max_retries} attempts")
                return False
                
        except OSError as e:
            print(f"Attempt {attempt + 1}: OS error removing {file_path}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"Failed to remove {file_path} after {max_retries} attempts")
                return False
    
    return False

# NOTE: The Note, NoteCollaborator, NoteVersion, UserCache, and Team Chat tables are NEVER deleted, dropped, or reset by this script. 
# Notes are permanent and excluded from all reset operations.
# UserCache contains persistent user data for personalized suggestions and is preserved across resets.
# Team Chat tables contain persistent chat messages and sessions that survive database resets.
def reset_database():
    """Reset and initialize the database with all required tables, EXCLUDING notes tables."""
    try:
        # Create db directory under the project root to match the main
        # application configuration (see ``app/config.py``)
        db_dir = os.path.join(PROJECT_ROOT, 'db')
        os.makedirs(db_dir, exist_ok=True)
        
        # Set up a minimal Flask app for DB creation
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(db_dir, 'app.db')}"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        # Close any existing database connections
        print("Closing existing database connections...")
        close_all_db_connections()
        
        # Handle existing database file
        db_path = os.path.join(db_dir, 'app.db')
        if os.path.exists(db_path):
            # --- SAFEGUARD: Do NOT delete notes tables or chat tables ---
            # Instead of deleting the whole DB, drop all tables except notes and chat tables
            from sqlalchemy import create_engine, inspect, text
            engine = create_engine(f"sqlite:///{db_path}")
            inspector = inspect(engine)
            with engine.connect() as conn:
                for table in inspector.get_table_names():
                    if table.lower() not in [
                        'note', 'note_collaborator', 'note_version', 'user_cache',
                        'team_chat_messages', 'team_chat_sessions', 'team_chat_typing', 'team_chat_settings'
                    ]:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                conn.commit()
            engine.dispose()
            print("All tables except notes, user cache, and team chat tables dropped.")
        else:
            print("No existing database found, creating new one.")
        
        with app.app_context():
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully")
            
            # Create admin user
            admin = User(
                username='admin',
                email='admin@pdshealth.com',
                role='admin',
                is_active=True,
                profile_picture='boy.png',
                okta_verified=False,
                teams_notifications=True
            )
            admin.set_password('admin123')  # Set a default password
            db.session.add(admin)
            
            # Create default system settings
            settings = SystemSettings()
            db.session.add(settings)
            
            # Load team members from Freshworks IDs.txt
            freshworks_team = load_freshworks_team_members()
            
            # Create default users from Freshworks team
            created_users = []
            for user_data in freshworks_team:
                try:
                    user = User(
                        username=user_data['username'],
                        email=user_data['email'],
                        role='user',
                        is_active=True,
                        profile_picture='default.png',
                        okta_verified=False,
                        teams_notifications=True,
                        requires_password_change=True
                    )
                    user.set_password('password')  # Set default password
                    db.session.add(user)
                    created_users.append(user_data['username'])
                    print(f"Added Freshworks team member: {user_data['username']}")
                except Exception as e:
                    print(f"Error creating user {user_data['username']}: {e}")
            
            # Create additional default users (fallback list)
            additional_default_users = [
                {'username': 'Alex', 'email': 'alex@pdshealth.com'},
                {'username': 'Sam', 'email': 'sam@pdshealth.com'},
                {'username': 'AJ', 'email': 'aj@pdshealth.com'},
                {'username': 'Jarvis', 'email': 'jarvis@pdshealth.com'},
                {'username': 'Jabin', 'email': 'jabin@pdshealth.com'},
                {'username': 'Doug', 'email': 'doug@pdshealth.com'},
                {'username': 'Nate', 'email': 'nate@pdshealth.com'},
                {'username': 'Jonathan', 'email': 'jonathan@pdshealth.com'},
                {'username': 'Richard', 'email': 'richard@pdshealth.com'},
                {'username': 'JZ', 'email': 'jz@pdshealth.com'},
            ]
            
            # Create additional default users (only if not already created from Freshworks)
            existing_usernames = {user_data['username'] for user_data in freshworks_team}
            for user_data in additional_default_users:
                if user_data['username'] not in existing_usernames:
                    try:
                        user = User(
                            username=user_data['username'],
                            email=user_data['email'],
                            role='user',
                            is_active=True,
                            profile_picture='default.png',
                            okta_verified=False,
                            teams_notifications=True
                        )
                        user.set_password('password')  # Set default password
                        db.session.add(user)
                        created_users.append(user_data['username'])
                        print(f"Added additional user: {user_data['username']}")
                    except Exception as e:
                        print(f"Error creating user {user_data['username']}: {e}")
            
            # Commit all changes
            try:
                db.session.commit()
                print(f"✓ Admin user and {len(created_users)} team members created successfully")
                print(f"Created users: {', '.join(created_users)}")
            except Exception as e:
                print(f"Error committing users to database: {e}")
                db.session.rollback()
                raise
            
            # Close the session
            db.session.close()
            
            return True
            
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        print(f"Error resetting database: {e}")
        return False

def reset_chat_qa_db():
    """Reset the chat Q&A database."""
    try:
        # Store chat_qa.db alongside the main application database for consistency
        chat_qa_dir = os.path.join(PROJECT_ROOT, 'db')
        os.makedirs(chat_qa_dir, exist_ok=True)
        chat_qa_path = os.path.join(chat_qa_dir, 'chat_qa.db')
        
        if os.path.exists(chat_qa_path):
            print(f"Attempting to remove existing chat Q&A database: {chat_qa_path}")
            if not safe_remove_file(chat_qa_path):
                print("Could not remove chat_qa.db. Trying alternative approach...")
                # Try to rename the file instead
                backup_path = f"{chat_qa_path}.backup.{int(time.time())}"
                try:
                    os.rename(chat_qa_path, backup_path)
                    print(f"Renamed existing chat_qa.db to: {backup_path}")
                except OSError as e:
                    print(f"Could not rename chat_qa.db: {e}")
                    return False
        
        # Recreate the table with the latest schema
        print("Creating new chat_qa.db...")
        conn = sqlite3.connect(chat_qa_path)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chat_qa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                question TEXT,
                answer TEXT,
                image_path TEXT,
                image_caption TEXT,
                embedding BLOB
            )
        ''')
        conn.commit()
        conn.close()
        print("chat_qa.db reset and table recreated successfully.")
        return True
        
    except Exception as e:
        print(f"Error resetting chat_qa.db: {e}")
        return False

def reset_all_databases():
    """Reset all databases in the system."""
    print("=" * 60)
    print("DATABASE RESET UTILITY")
    print("=" * 60)
    
    # First, close all database connections
    print("\n1. Closing all database connections...")
    close_all_db_connections()
    
    # Reset chat_qa database
    print("\n2. Resetting chat_qa database...")
    if reset_chat_qa_db():
        print("✓ Chat Q&A database reset successful")
    else:
        print("✗ Chat Q&A database reset failed")
    
    # Reset main database
    print("\n3. Resetting main database...")
    if reset_database():
        print("✓ Main database reset successful")
    else:
        print("✗ Main database reset failed")
    
    print("\n" + "=" * 60)
    print("DATABASE RESET COMPLETED")
    print("=" * 60)

if __name__ == '__main__':
    reset_all_databases()
