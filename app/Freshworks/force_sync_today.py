#!/usr/bin/env python3
"""
Force Sync Today's Ticket Data

This script forces a sync of today's ticket closure data, bypassing rate limiting,
so we can immediately see the real data in the YAM Dashboard.
"""

import os
import sys
from datetime import datetime, date

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.utils.freshworks_service import freshworks_service
from app.models.base import TicketClosure, User, FreshworksUserMapping, TicketSyncMetadata
from app.extensions import db

def force_sync_today():
    """Force sync today's ticket closure data"""
    print("🚀 Force syncing today's ticket closure data...")
    print("=" * 50)
    
    today = date.today()
    
    # Force sync today's data
    success = freshworks_service.sync_daily_closures_with_tickets(today, force_sync=True)
    
    if success:
        print("✅ Force sync completed successfully!")
        
        # Get the updated data
        closures = TicketClosure.query.filter_by(date=today).join(User).all()
        
        print(f"\n📊 Today's Ticket Closures ({today}):")
        print("-" * 40)
        
        total_tickets = 0
        for closure in closures:
            print(f"   {closure.user.username}: {closure.tickets_closed} tickets")
            total_tickets += closure.tickets_closed
        
        print(f"\n📈 Total tickets closed today: {total_tickets}")
        print(f"👥 Users with closures: {len(closures)}")
        
        return True
    else:
        print("❌ Force sync failed!")
        return False

def verify_database_data():
    """Verify the data in the database"""
    print("\n🔍 Verifying database data...")
    print("=" * 40)
    
    today = date.today()
    
    # Check ticket closures
    closures = TicketClosure.query.filter_by(date=today).join(User).all()
    print(f"📊 Ticket closures for {today}: {len(closures)} records")
    
    # Check user mappings
    mappings = FreshworksUserMapping.query.all()
    linked_mappings = [m for m in mappings if m.user_id]
    print(f"👥 User mappings: {len(linked_mappings)} linked, {len(mappings)} total")
    
    # Check sync metadata
    metadata = TicketSyncMetadata.query.filter_by(sync_date=today).first()
    if metadata:
        print(f"🔄 Sync metadata: {metadata.sync_count} syncs, {metadata.tickets_processed} tickets processed")
        print(f"   Last sync: {metadata.last_sync_time}")
    else:
        print("⚠️ No sync metadata found for today")
    
    return len(closures) > 0

def main():
    """Main function"""
    try:
        # Create Flask app context
        app = create_app()
        with app.app_context():
            print("🚀 Starting force sync process...")
            
            # Force sync today's data
            success = force_sync_today()
            
            if success:
                # Verify the data
                has_data = verify_database_data()
                
                if has_data:
                    print("\n🎉 Success! The Daily Ticket Closures graph should now show real data.")
                    print("📊 Refresh the YAM Dashboard to see the updated chart.")
                else:
                    print("\n⚠️ Sync completed but no data found in database.")
            else:
                print("\n❌ Force sync failed. Check the logs for errors.")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main() 