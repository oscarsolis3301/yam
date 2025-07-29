#!/usr/bin/env python3
"""
Enhanced Leaderboard Sync Script
Runs the improved leaderboard.py with ticket number tracking
"""

import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🚀 Starting Enhanced Leaderboard Sync with Ticket Tracking")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Import and run the enhanced leaderboard script
        from app.Freshworks.leaderboard import main as run_leaderboard
        
        # Run the enhanced leaderboard sync
        run_leaderboard()
        
        print()
        print("✅ Enhanced leaderboard sync completed successfully!")
        print("🎫 Ticket numbers are now stored in the database")
        print("📊 Data is available in the YAM Dashboard")
        
    except Exception as e:
        print(f"❌ Error running enhanced leaderboard sync: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 