#!/usr/bin/env python3
"""
Database Migration Script
Adds ticket_numbers column to ticket_closure table
"""

import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🔄 Starting Database Migration")
    print("=" * 40)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from app import create_app
        from app.utils.database import add_missing_columns
        
        # Create Flask app context
        app = create_app()
        with app.app_context():
            print("📊 Running database migration...")
            add_missing_columns()
            print("✅ Database migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during database migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 