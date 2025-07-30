#!/usr/bin/env python3
"""
Initialize Ticket Closure Tracking Database
Creates new tables for historical ticket closure tracking with hourly updates
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.base import (
    TicketClosure, 
    TicketClosureHistory, 
    TicketClosureDaily,
    FreshworksUserMapping, 
    TicketSyncMetadata,
    User
)
from app.extensions import db
from app.utils.ticket_closure_service import ticket_closure_service
from app.utils.freshworks_service import freshworks_service

def init_ticket_closure_tracking():
    """Initialize the ticket closure tracking system"""
    print("🚀 Initializing Ticket Closure Tracking System")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            print("📊 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Sync user mappings
            print("\n👥 Syncing user mappings...")
            freshworks_service.sync_user_mappings()
            print("✅ User mappings synced")
            
            # Link users to mappings
            print("\n🔗 Linking users to mappings...")
            link_users_to_mappings()
            print("✅ Users linked to mappings")
            
            # Initialize today's data
            print("\n📅 Initializing today's data...")
            today = date.today()
            success = ticket_closure_service.sync_hourly_closures(today, datetime.now().hour)
            if success:
                print("✅ Today's data initialized")
            else:
                print("⚠️ Today's data initialization failed")
            
            # Initialize yesterday's data (if available)
            print("\n📅 Initializing yesterday's data...")
            yesterday = today - timedelta(days=1)
            success = ticket_closure_service.sync_hourly_closures(yesterday, 23)  # Last hour of yesterday
            if success:
                print("✅ Yesterday's data initialized")
            else:
                print("⚠️ Yesterday's data initialization failed")
            
            # Show database statistics
            print("\n📈 Database Statistics:")
            print("-" * 30)
            show_database_stats()
            
            print("\n🎉 Ticket Closure Tracking System initialized successfully!")
            print("\n📋 Next Steps:")
            print("1. The system will now track hourly updates automatically")
            print("2. Historical data is available for time period filtering")
            print("3. Ticket numbers are stored for detailed viewing")
            print("4. Database file location: app/db/ticket_closure_tracking.db")
            
        except Exception as e:
            print(f"❌ Error initializing ticket closure tracking: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

def link_users_to_mappings():
    """Link existing users to Freshworks mappings"""
    mappings = FreshworksUserMapping.query.filter_by(user_id=None).all()
    linked_count = 0
    
    for mapping in mappings:
        # Use the improved matching logic from the service
        local_user = freshworks_service._find_matching_user(mapping.freshworks_username)
        
        if local_user:
            mapping.user_id = local_user.id
            linked_count += 1
            print(f"✅ Linked {mapping.freshworks_username} to user {local_user.username}")
    
    try:
        db.session.commit()
        print(f"✅ Successfully linked {linked_count} users to mappings")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error linking users: {e}")

def show_database_stats():
    """Show current database statistics"""
    try:
        # Count records
        total_history = TicketClosureHistory.query.count()
        total_daily = TicketClosureDaily.query.count()
        total_legacy = TicketClosure.query.count()
        total_mappings = FreshworksUserMapping.query.count()
        linked_mappings = FreshworksUserMapping.query.filter(
            FreshworksUserMapping.user_id.isnot(None)
        ).count()
        
        # Today's data
        today = date.today()
        today_history = TicketClosureHistory.query.filter_by(date=today).count()
        today_daily = TicketClosureDaily.query.filter_by(date=today).count()
        
        print(f"📊 Historical Records: {total_history}")
        print(f"📊 Daily Records: {total_daily}")
        print(f"📊 Legacy Records: {total_legacy}")
        print(f"👥 User Mappings: {linked_mappings}/{total_mappings}")
        print(f"📅 Today's History Records: {today_history}")
        print(f"📅 Today's Daily Records: {today_daily}")
        
    except Exception as e:
        print(f"❌ Error getting database stats: {e}")

def migrate_existing_data():
    """Migrate existing data to new tables"""
    print("\n🔄 Migrating existing data to new tables...")
    
    try:
        # Get existing closure records
        existing_closures = TicketClosure.query.all()
        migrated_count = 0
        
        for closure in existing_closures:
            # Create daily record
            daily_record = TicketClosureDaily.query.filter_by(
                user_id=closure.user_id,
                date=closure.date
            ).first()
            
            if not daily_record:
                daily_record = TicketClosureDaily(
                    user_id=closure.user_id,
                    freshworks_user_id=closure.freshworks_user_id,
                    date=closure.date,
                    tickets_closed=closure.tickets_closed,
                    ticket_numbers=closure.ticket_numbers,
                    last_sync_hour=23,  # Assume last hour of the day
                    sync_count=1
                )
                db.session.add(daily_record)
                migrated_count += 1
        
        db.session.commit()
        print(f"✅ Migrated {migrated_count} existing records to daily table")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error migrating data: {e}")

if __name__ == "__main__":
    print("Ticket Closure Tracking System Initialization")
    print("=" * 50)
    
    # Check if user wants to migrate existing data
    migrate = input("Do you want to migrate existing data to new tables? (y/n): ").lower().strip()
    
    if migrate == 'y':
        print("🔄 Migration mode enabled")
        init_ticket_closure_tracking()
        migrate_existing_data()
    else:
        print("🆕 Fresh installation mode")
        init_ticket_closure_tracking()
    
    print("\n✅ Initialization complete!") 