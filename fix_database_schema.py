#!/usr/bin/env python3
"""
Fix database schema for FreshworksUserMapping table
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.base import FreshworksUserMapping

def fix_schema():
    """Fix the database schema by dropping and recreating the table"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Fixing database schema...")
        
        try:
            # Drop the existing table
            print("🗑️ Dropping existing freshworks_user_mapping table...")
            with db.engine.connect() as conn:
                conn.execute(db.text("DROP TABLE IF EXISTS freshworks_user_mapping"))
                conn.commit()
            
            # Create the table with the correct schema
            print("🏗️ Creating freshworks_user_mapping table with correct schema...")
            db.create_all()
            
            print("✅ Database schema fixed successfully!")
            
        except Exception as e:
            print(f"❌ Error fixing schema: {e}")

if __name__ == "__main__":
    fix_schema() 