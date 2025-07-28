#!/usr/bin/env python3
"""
Script to fix authentication loop issues by clearing sessions and resetting user status
"""

import os
import sys
import shutil
from pathlib import Path

def clear_sessions():
    """Clear all session files."""
    session_dirs = [
        'sessions',
        'app/sessions',
        'instance/sessions'
    ]
    
    for session_dir in session_dirs:
        if os.path.exists(session_dir):
            print(f"Clearing session directory: {session_dir}")
            try:
                shutil.rmtree(session_dir)
                os.makedirs(session_dir, exist_ok=True)
                print(f"✓ Cleared {session_dir}")
            except Exception as e:
                print(f"✗ Error clearing {session_dir}: {e}")

def clear_cache():
    """Clear cache directories."""
    cache_dirs = [
        'cache',
        'app/cache',
        '__pycache__',
        'app/__pycache__'
    ]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            print(f"Clearing cache directory: {cache_dir}")
            try:
                shutil.rmtree(cache_dir)
                print(f"✓ Cleared {cache_dir}")
            except Exception as e:
                print(f"✗ Error clearing {cache_dir}: {e}")

def reset_user_status():
    """Reset user online status in database."""
    try:
        # Import Flask app and database
        sys.path.insert(0, 'app')
        from app import create_app, db
        from app.models.user import User
        
        app = create_app()
        
        with app.app_context():
            # Reset all users to online status
            users = User.query.all()
            for user in users:
                user.is_online = True
                print(f"✓ Reset user {user.username} to online status")
            
            db.session.commit()
            print("✓ All users reset to online status")
            
    except Exception as e:
        print(f"✗ Error resetting user status: {e}")

def main():
    print("🔧 Fixing authentication loop issues...")
    print("=" * 50)
    
    # Clear sessions
    print("\n1. Clearing session files...")
    clear_sessions()
    
    # Clear cache
    print("\n2. Clearing cache files...")
    clear_cache()
    
    # Reset user status
    print("\n3. Resetting user online status...")
    reset_user_status()
    
    print("\n" + "=" * 50)
    print("✅ Authentication loop fix completed!")
    print("\nNext steps:")
    print("1. Restart the server")
    print("2. Try accessing the application again")
    print("3. If issues persist, check the server logs")

if __name__ == "__main__":
    main() 