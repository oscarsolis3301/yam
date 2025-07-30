#!/usr/bin/env python3
"""
Daily sync script for ticket closures
This script should be run daily via cron to keep ticket closure data up to date
"""

import sys
import os
from datetime import date, datetime, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def sync_daily_closures():
    """Sync daily ticket closures from Freshworks with hourly rate limiting"""
    try:
        # Import Flask app and services
        from app import create_app
        from app.utils.freshworks_service import freshworks_service
        from app.models.base import TicketSyncMetadata
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            print(f"🔄 [{datetime.now()}] Starting hourly ticket closure sync...")
            
            # Sync user mappings first (in case there are new users)
            print("👥 Syncing user mappings...")
            freshworks_service.sync_user_mappings()
            
            # Sync today's closures (respects hourly rate limiting)
            today = date.today()
            print(f"🎫 Attempting to sync ticket closures for {today}...")
            
            can_sync_today = TicketSyncMetadata.can_sync_now(today)
            if can_sync_today:
                sync_result = freshworks_service.sync_daily_closures_with_tickets(today)
                if sync_result:
                    print(f"✅ Successfully synced closures for {today}")
                else:
                    print(f"⚠️ Sync failed for {today}")
            else:
                print(f"⏰ Sync rate limited for {today} - skipping")
            
            # Also attempt to sync yesterday's data (in case of late updates)
            yesterday = today - timedelta(days=1)
            print(f"🎫 Attempting to sync ticket closures for {yesterday} (backfill)...")
            
            can_sync_yesterday = TicketSyncMetadata.can_sync_now(yesterday)
            if can_sync_yesterday:
                sync_result = freshworks_service.sync_daily_closures_with_tickets(yesterday)
                if sync_result:
                    print(f"✅ Successfully synced closures for {yesterday}")
                else:
                    print(f"⚠️ Sync failed for {yesterday}")
            else:
                print(f"⏰ Sync rate limited for {yesterday} - skipping")
            
            print(f"🏁 [{datetime.now()}] Daily sync process completed!")
            
    except Exception as e:
        print(f"❌ [{datetime.now()}] Error during daily sync: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    sync_daily_closures()