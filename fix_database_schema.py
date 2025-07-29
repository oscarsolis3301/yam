#!/usr/bin/env python3
"""
Script to fix the missing requires_password_change column in the user table.
This script will add the missing column that's causing login failures.
"""

import os
import sys
import sqlite3
from pathlib import Path

def fix_database_schema():
    """Add the missing requires_password_change column to the user table."""
    
    # Find the database file - check multiple possible locations
    db_paths = [
        'app/db/app.db',  # Main database location
        'app.db',
        'instance/app.db',
        'app/app.db',
        'db/app.db'
    ]
    
    db_file = None
    for path in db_paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:  # Check file exists and has content
            db_file = path
            break
    
    if not db_file:
        print("Error: Could not find a valid app.db file")
        print("Searched in:", db_paths)
        return False
    
    print(f"Found database at: {db_file}")
    print(f"Database size: {os.path.getsize(db_file)} bytes")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"Tables in database: {tables}")
        
        if 'user' not in tables:
            print("User table does not exist. Database needs to be initialized.")
            print("Please run the application initialization first.")
            print("Or use the reset_db.py script to create a fresh database.")
            conn.close()
            return False
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Current columns in user table: {columns}")
        
        if 'requires_password_change' in columns:
            print("Column 'requires_password_change' already exists in user table")
            conn.close()
            return True
        
        # Add the missing column
        print("Adding missing column 'requires_password_change' to user table...")
        try:
            cursor.execute("""
                ALTER TABLE user 
                ADD COLUMN requires_password_change BOOLEAN DEFAULT TRUE
            """)
            print("ALTER TABLE command executed successfully")
        except sqlite3.OperationalError as e:
            print(f"SQLite error during ALTER TABLE: {e}")
            # Try alternative syntax
            try:
                cursor.execute("""
                    ALTER TABLE user 
                    ADD COLUMN requires_password_change INTEGER DEFAULT 1
                """)
                print("ALTER TABLE command executed with INTEGER type")
            except sqlite3.OperationalError as e2:
                print(f"Alternative ALTER TABLE also failed: {e2}")
                return False
        
        # Commit the changes
        conn.commit()
        print("Changes committed to database")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Columns after adding: {columns}")
        
        if 'requires_password_change' in columns:
            print("Successfully added 'requires_password_change' column to user table")
            
            # Update existing users to not require password change (for existing users)
            try:
                cursor.execute("""
                    UPDATE user 
                    SET requires_password_change = 0 
                    WHERE requires_password_change IS NULL
                """)
                conn.commit()
                print("Updated existing users to not require password change")
            except Exception as e:
                print(f"Warning: Could not update existing users: {e}")
            
        else:
            print("Error: Column was not added successfully")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error fixing database schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Fixing database schema...")
    success = fix_database_schema()
    
    if success:
        print("Database schema fixed successfully!")
        print("You should now be able to login to your application.")
    else:
        print("Failed to fix database schema.")
        print("\nTo fix this issue, you can:")
        print("1. Run: python app/reset_db.py (to create a fresh database)")
        print("2. Or restart your application (which should initialize the database)")
        sys.exit(1) 