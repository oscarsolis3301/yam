from datetime import datetime, timedelta
from app.models import Activity, User
from app.extensions import db

def get_user_history(user_id, days=7):
    """Get user activity history for the specified number of days"""
    start_date = datetime.utcnow() - timedelta(days=days)
    activities = Activity.query.filter(
        Activity.user_id == user_id,
        Activity.timestamp >= start_date
    ).order_by(Activity.timestamp.desc()).all()
    
    return [{
        'id': activity.id,
        'action': activity.action,
        'details': activity.details,
        'timestamp': activity.timestamp.isoformat()
    } for activity in activities]

def log_activity(user_id, action, details=None):
    """Log a user activity"""
    activity = Activity(
        user_id=user_id,
        action=action,
        details=details
    )
    db.session.add(activity)
    db.session.commit()
    return activity

def log_upload(user_ip, filename, user_name=None):
    """Wrapper for root log.py log_upload for compatibility."""
    try:
        from log import log_upload as root_log_upload
        return root_log_upload(user_ip, filename, user_name)
    except ImportError:
        # Fallback: do nothing or log
        pass 