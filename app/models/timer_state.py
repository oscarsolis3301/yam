from app.models.base import db
from datetime import datetime, timezone

class TimerState(db.Model):
    """Model to store persistent timer state that survives server restarts"""
    __tablename__ = 'timer_state'
    
    id = db.Column(db.Integer, primary_key=True)
    timer_name = db.Column(db.String(100), unique=True, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    interval_minutes = db.Column(db.Integer, nullable=False, default=60)
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TimerState {self.timer_name}: next_run={self.next_run}>'
    
    @classmethod
    def get_or_create_leaderboard_timer(cls, interval_minutes=60):
        """Get or create the leaderboard sync timer"""
        timer = cls.query.filter_by(timer_name='leaderboard_sync').first()
        
        if not timer:
            # Create new timer
            now = datetime.now(timezone.utc)
            next_run = now.replace(second=0, microsecond=0)
            # Add interval minutes
            next_run = next_run.replace(minute=next_run.minute + interval_minutes)
            if next_run.minute >= 60:
                next_run = next_run.replace(hour=next_run.hour + 1, minute=next_run.minute - 60)
            
            timer = cls(
                timer_name='leaderboard_sync',
                start_time=now,
                interval_minutes=interval_minutes,
                next_run=next_run,
                is_active=True
            )
            db.session.add(timer)
            db.session.commit()
            print(f"🕐 Created new leaderboard timer: next run at {next_run}")
        else:
            print(f"🕐 Found existing leaderboard timer: next run at {timer.next_run}")
        
        return timer
    
    @classmethod
    def update_leaderboard_timer(cls):
        """Update the leaderboard timer after a successful run"""
        timer = cls.query.filter_by(timer_name='leaderboard_sync').first()
        if timer:
            now = datetime.now(timezone.utc)
            timer.last_run = now
            
            # Calculate next run time
            next_run = now.replace(second=0, microsecond=0)
            next_run = next_run.replace(minute=next_run.minute + timer.interval_minutes)
            if next_run.minute >= 60:
                next_run = next_run.replace(hour=next_run.hour + 1, minute=next_run.minute - 60)
            
            timer.next_run = next_run
            timer.updated_at = now
            db.session.commit()
            print(f"🕐 Updated leaderboard timer: next run at {next_run}")
            return timer
        return None
    
    @classmethod
    def get_time_until_next_run(cls):
        """Get time remaining until next run in seconds"""
        timer = cls.query.filter_by(timer_name='leaderboard_sync').first()
        if timer and timer.is_active:
            now = datetime.now(timezone.utc)
            time_diff = timer.next_run - now
            return max(0, int(time_diff.total_seconds()))
        return 0
    
    @classmethod
    def is_time_to_run(cls):
        """Check if it's time to run the leaderboard sync"""
        timer = cls.query.filter_by(timer_name='leaderboard_sync').first()
        if timer and timer.is_active:
            now = datetime.now(timezone.utc)
            return now >= timer.next_run
        return False 