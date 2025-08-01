import os
import sys
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
from app import create_app
from app.models.timer_state import TimerState
from app.extensions import db

class LeaderboardTimerService:
    """Service to manage persistent leaderboard sync timer that survives server restarts"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LeaderboardTimerService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.app = create_app()
        self.is_running = False
        self.timer_thread = None
        self.leaderboard_process = None
        self._initialized = True
        
    def start_timer_service(self, interval_minutes=60):
        """Start the persistent timer service"""
        with self.app.app_context():
            print("🚀 Starting Leaderboard Timer Service...")
            
            # Get or create timer state
            timer = TimerState.get_or_create_leaderboard_timer(interval_minutes)
            
            if self.is_running:
                print("⚠️ Timer service is already running")
                return
            
            self.is_running = True
            self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
            self.timer_thread.start()
            
            # Show initial countdown
            time_until_next = TimerState.get_time_until_next_run()
            hours = time_until_next // 3600
            minutes = (time_until_next % 3600) // 60
            seconds = time_until_next % 60
            
            print(f"✅ Timer service started with {interval_minutes} minute interval")
            print(f"🕐 Next sync scheduled at: {timer.next_run}")
            print(f"⏳ Initial countdown: {hours:02d}:{minutes:02d}:{seconds:02d}")
            print("=" * 60)
    
    def stop_timer_service(self):
        """Stop the timer service"""
        print("🛑 Stopping Leaderboard Timer Service...")
        self.is_running = False
        
        if self.leaderboard_process:
            try:
                self.leaderboard_process.terminate()
                self.leaderboard_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.leaderboard_process.kill()
            except Exception as e:
                print(f"⚠️ Error stopping leaderboard process: {e}")
        
        if self.timer_thread:
            self.timer_thread.join(timeout=5)
        
        print("✅ Timer service stopped")
    
    def _timer_loop(self):
        """Main timer loop that checks if it's time to run the leaderboard sync"""
        print("🕐 Leaderboard Timer Service: Starting countdown loop...")
        
        while self.is_running:
            try:
                with self.app.app_context():
                    # Check if it's time to run
                    if TimerState.is_time_to_run():
                        print("🔄 Timer triggered - running leaderboard sync...")
                        self._run_leaderboard_sync()
                    else:
                        # Get time until next run
                        time_until_next = TimerState.get_time_until_next_run()
                        if time_until_next > 0:
                            # Calculate hours, minutes, seconds
                            hours = time_until_next // 3600
                            minutes = (time_until_next % 3600) // 60
                            seconds = time_until_next % 60
                            
                            # Log countdown every 5 minutes or when getting close
                            if time_until_next % 300 == 0 or time_until_next <= 600:  # Every 5 minutes or last 10 minutes
                                if time_until_next <= 300:  # Last 5 minutes
                                    print(f"⚠️  URGENT: Next leaderboard sync in {hours:02d}:{minutes:02d}:{seconds:02d}")
                                elif time_until_next <= 600:  # Last 10 minutes
                                    print(f"🕐 WARNING: Next leaderboard sync in {hours:02d}:{minutes:02d}:{seconds:02d}")
                                else:
                                    print(f"🕐 Next leaderboard sync in {hours:02d}:{minutes:02d}:{seconds:02d}")
                        
                        # Sleep for 1 minute before checking again
                        time.sleep(60)
                        
            except Exception as e:
                print(f"❌ Error in timer loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _run_leaderboard_sync(self):
        """Run the leaderboard.py script"""
        try:
            # Get the path to leaderboard.py
            script_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'Freshworks')
            script_path = os.path.join(script_dir, 'leaderboard.py')
            
            if not os.path.exists(script_path):
                print(f"❌ Leaderboard script not found at: {script_path}")
                return
            
            print(f"🔄 Running leaderboard sync: {script_path}")
            
            # Run the leaderboard script
            self.leaderboard_process = subprocess.Popen(
                [sys.executable, script_path],
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = self.leaderboard_process.communicate(timeout=300)  # 5 minute timeout
                
                if self.leaderboard_process.returncode == 0:
                    print("✅ Leaderboard sync completed successfully")
                    # Update timer state
                    TimerState.update_leaderboard_timer()
                else:
                    print(f"❌ Leaderboard sync failed with return code: {self.leaderboard_process.returncode}")
                    if stderr:
                        print(f"Error output: {stderr}")
                
            except subprocess.TimeoutExpired:
                print("⏰ Leaderboard sync timed out after 5 minutes")
                self.leaderboard_process.kill()
                
        except Exception as e:
            print(f"❌ Error running leaderboard sync: {e}")
    
    def get_timer_status(self):
        """Get current timer status"""
        with self.app.app_context():
            timer = TimerState.query.filter_by(timer_name='leaderboard_sync').first()
            if timer:
                time_until_next = TimerState.get_time_until_next_run()
                hours = time_until_next // 3600
                minutes = (time_until_next % 3600) // 60
                seconds = time_until_next % 60
                
                return {
                    'is_active': timer.is_active,
                    'is_running': self.is_running,
                    'interval_minutes': timer.interval_minutes,
                    'last_run': timer.last_run.isoformat() if timer.last_run else None,
                    'next_run': timer.next_run.isoformat(),
                    'time_until_next': {
                        'total_seconds': time_until_next,
                        'hours': hours,
                        'minutes': minutes,
                        'seconds': seconds,
                        'formatted': f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    }
                }
            return None
    
    def reset_timer(self, interval_minutes=60):
        """Reset the timer with new interval"""
        with self.app.app_context():
            timer = TimerState.query.filter_by(timer_name='leaderboard_sync').first()
            if timer:
                timer.interval_minutes = interval_minutes
                timer.is_active = True
                
                # Calculate new next run time
                now = datetime.now(timezone.utc)
                next_run = now.replace(second=0, microsecond=0)
                next_run = next_run.replace(minute=next_run.minute + interval_minutes)
                if next_run.minute >= 60:
                    next_run = next_run.replace(hour=next_run.hour + 1, minute=next_run.minute - 60)
                
                timer.next_run = next_run
                timer.updated_at = now
                db.session.commit()
                
                print(f"🔄 Timer reset: next run at {next_run} (interval: {interval_minutes} minutes)")
                return True
            return False

# Create singleton instance
def get_leaderboard_timer_service():
    """Get the singleton instance of the leaderboard timer service"""
    if LeaderboardTimerService._instance is None:
        LeaderboardTimerService._instance = LeaderboardTimerService()
    return LeaderboardTimerService._instance 