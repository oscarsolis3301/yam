#!/usr/bin/env python3
"""
Auto-Start Leaderboard Timer
Runs automatically with optimal settings - no user interaction required
"""

import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import after adding to path
from app import create_app
from app.models.base import TicketSyncMetadata
from app.extensions import db

load_dotenv()

def get_sync_status():
    """Get current sync status from database"""
    try:
        app = create_app()
        with app.app_context():
            today = datetime.now().date()
            metadata = TicketSyncMetadata.query.filter_by(sync_date=today).first()
            
            if metadata:
                return {
                    'last_sync': metadata.last_sync_time,
                    'sync_count': metadata.sync_count,
                    'tickets_processed': metadata.tickets_processed,
                    'next_sync_available': metadata.last_sync_time + timedelta(hours=1)
                }
            else:
                return None
    except Exception as e:
        print(f"❌ Error getting sync status: {e}")
        return None

def format_time_ago(timestamp):
    """Format time ago from timestamp"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def show_auto_timer():
    """Show auto timer with optimal settings"""
    print("🕐 YAM Leaderboard Auto-Timer")
    print("=" * 50)
    print(f"⏰ Auto-Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔄 Sync Interval: 60 minutes (optimal)")
    print(f"🎯 Mode: Automatic (no user interaction)")
    print("=" * 50)
    
    while True:
        try:
            # Get current sync status
            sync_status = get_sync_status()
            
            # Clear screen (works on most terminals)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("🕐 YAM Leaderboard Auto-Timer")
            print("=" * 50)
            print(f"⏰ Auto-Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔄 Sync Interval: 60 minutes (optimal)")
            print(f"🎯 Mode: Automatic (no user interaction)")
            print("=" * 50)
            
            if sync_status:
                last_sync = sync_status['last_sync']
                next_sync = sync_status['next_sync_available']
                time_since_last = datetime.utcnow() - last_sync
                time_until_next = next_sync - datetime.utcnow()
                
                print(f"📊 Last Sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⏱️ Time Since Last: {format_time_ago(last_sync)}")
                print(f"🔄 Sync Count Today: {sync_status['sync_count']}")
                print(f"🎫 Tickets Processed: {sync_status['tickets_processed']}")
                print("=" * 50)
                
                if time_until_next.total_seconds() > 0:
                    # Show countdown to next sync
                    remaining_seconds = int(time_until_next.total_seconds())
                    hrs, rem = divmod(remaining_seconds, 3600)
                    mins, secs = divmod(rem, 60)
                    
                    # Calculate progress
                    progress = ((60 * 60 - remaining_seconds) / (60 * 60)) * 100
                    progress_bar_length = 40
                    filled_length = int(progress_bar_length * progress / 100)
                    bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
                    
                    print(f"⏰ Next Sync: {next_sync.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"⏳ Time Remaining: {hrs:02d}:{mins:02d}:{secs:02d}")
                    print(f"📈 Progress: [{bar}] {progress:.1f}%")
                    
                    # Status indicator
                    if remaining_seconds < 300:  # Less than 5 minutes
                        print("🟢 Status: Ready for sync")
                    elif remaining_seconds < 1800:  # Less than 30 minutes
                        print("🟡 Status: Approaching sync time")
                    else:
                        print("🔴 Status: Waiting for sync")
                else:
                    print("🟢 Status: Ready for sync now!")
                    print("⏰ Next sync can be triggered immediately")
            else:
                print("❌ No sync data found for today")
                print("🔄 Run the leaderboard script to start syncing")
            
            print("=" * 50)
            print("💡 Press Ctrl+C to exit")
            print("💡 Timer runs automatically - no action needed")
            
            # Wait 10 seconds before updating
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n\n👋 Exiting auto timer...")
            break
        except Exception as e:
            print(f"\n❌ Error in timer: {e}")
            time.sleep(10)

if __name__ == "__main__":
    show_auto_timer() 