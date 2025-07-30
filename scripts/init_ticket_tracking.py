#!/usr/bin/env python3
"""
Initialize Ticket Tracking System

This script sets up the database tables and syncs initial data from the leaderboard.py
to populate the Daily Ticket Closures graph in the YAM Dashboard.
"""

import os
import sys
from datetime import date, timedelta

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

def main():
    """Main initialization function"""
    print("🚀 Initializing Ticket Tracking System")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    with app.app_context():
        # Import models and services only after app context is set up
        from app.extensions import db
        from app.models.base import TicketClosure, FreshworksUserMapping, User, TicketSyncMetadata
        from app.utils.freshworks_service import freshworks_service

        def sync_user_mappings():
            print("🔄 Syncing user mappings...")
            try:
                freshworks_service.sync_user_mappings()
                print("✅ User mappings synced successfully")
                return True
            except Exception as e:
                print(f"❌ Error syncing user mappings: {e}")
                return False

        def sync_initial_data():
            print("📊 Syncing initial ticket closure data...")
            today = date.today()
            yesterday = today - timedelta(days=1)
            dates_to_sync = [today, yesterday]
            for sync_date in dates_to_sync:
                print(f"🔄 Syncing data for {sync_date}...")
                try:
                    success = freshworks_service.sync_daily_closures_with_tickets(sync_date, force_sync=True)
                    if success:
                        print(f"✅ Successfully synced data for {sync_date}")
                    else:
                        print(f"⚠️ Sync failed for {sync_date}")
                except Exception as e:
                    print(f"❌ Error syncing data for {sync_date}: {e}")

        def display_sync_status():
            print("\n📈 Current Sync Status:")
            print("=" * 50)
            mapping_count = FreshworksUserMapping.query.count()
            linked_count = FreshworksUserMapping.query.filter(FreshworksUserMapping.user_id.isnot(None)).count()
            print(f"User Mappings: {mapping_count} total, {linked_count} linked to local users")
            today = date.today()
            today_closures = TicketClosure.query.filter_by(date=today).count()
            total_closures = TicketClosure.query.count()
            print(f"Ticket Closures: {today_closures} for today, {total_closures} total")
            today_metadata = TicketSyncMetadata.query.filter_by(sync_date=today).first()
            if today_metadata:
                print(f"Today's Sync: {today_metadata.sync_count} syncs, {today_metadata.tickets_processed} tickets processed")
                print(f"Last Sync: {today_metadata.last_sync_time}")
            else:
                print("Today's Sync: No sync data available")

        # Sync user mappings
        if not sync_user_mappings():
            print("❌ User mapping sync failed. Exiting.")
            return
        # Sync initial data
        sync_initial_data()
        # Display status
        display_sync_status()
        print("\n🎉 Ticket tracking system initialized successfully!")
        print("\nNext steps:")
        print("1. Run the enhanced leaderboard.py script to sync current data:")
        print("   python app/Freshworks/leaderboard.py")
        print("2. The YAM Dashboard Daily Ticket Closures graph should now show real data")
        print("3. Set up automated sync (optional) via cron job")

if __name__ == "__main__":
    main()