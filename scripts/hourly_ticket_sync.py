#!/usr/bin/env python3
"""
Hourly Ticket Closure Sync
Automated script to sync ticket closures every hour with historical tracking
"""

import os
import sys
import time
from datetime import datetime, date

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.utils.ticket_closure_service import ticket_closure_service
from app.utils.logger import setup_logging

logger = setup_logging()

def run_hourly_sync():
    """Run hourly sync for ticket closures"""
    try:
        app = create_app()
        
        with app.app_context():
            current_time = datetime.now()
            current_date = current_time.date()
            current_hour = current_time.hour
            
            logger.info(f"🔄 Starting hourly sync for {current_date} at hour {current_hour}")
            
            # Perform hourly sync
            success = ticket_closure_service.sync_hourly_closures(current_date, current_hour)
            
            if success:
                logger.info(f"✅ Hourly sync completed successfully for {current_date} hour {current_hour}")
                return True
            else:
                logger.error(f"❌ Hourly sync failed for {current_date} hour {current_hour}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error during hourly sync: {e}")
        return False

def run_continuous_sync():
    """Run continuous hourly sync (for development/testing)"""
    print("🔄 Starting continuous hourly sync (press Ctrl+C to stop)")
    print("=" * 50)
    
    while True:
        try:
            success = run_hourly_sync()
            
            if success:
                print(f"✅ Sync completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"❌ Sync failed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Wait for 1 hour (3600 seconds)
            print("⏰ Waiting 1 hour until next sync...")
            time.sleep(3600)
            
        except KeyboardInterrupt:
            print("\n🛑 Continuous sync stopped by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            print("⏰ Retrying in 5 minutes...")
            time.sleep(300)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Hourly Ticket Closure Sync')
    parser.add_argument('--continuous', action='store_true', 
                       help='Run continuous hourly sync (for development)')
    parser.add_argument('--once', action='store_true', 
                       help='Run sync once and exit')
    
    args = parser.parse_args()
    
    if args.continuous:
        run_continuous_sync()
    elif args.once:
        success = run_hourly_sync()
        if success:
            print("✅ Single sync completed successfully")
            sys.exit(0)
        else:
            print("❌ Single sync failed")
            sys.exit(1)
    else:
        # Default: run once
        success = run_hourly_sync()
        if success:
            print("✅ Sync completed successfully")
        else:
            print("❌ Sync failed") 