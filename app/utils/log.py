import logging
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models import User, ChatQA

logger = logging.getLogger('spark')

def log_upload(ip_address, filename, username):
    """
    Log file upload for audit purposes
    
    Args:
        ip_address (str): IP address of the uploader
        filename (str): Name of the uploaded file
        username (str): Username of the uploader
    """
    try:
        # For now, we'll just log to the application log
        # In the future, this could be extended to store in a database table
        logger.info(f"File upload logged - IP: {ip_address}, File: {filename}, User: {username}")
        
        # TODO: Create an UploadLog model and store the data in the database
        # upload_log = UploadLog(
        #     ip_address=ip_address,
        #     filename=filename,
        #     username=username,
        #     timestamp=datetime.utcnow()
        # )
        # db.session.add(upload_log)
        # db.session.commit()
        
    except Exception as e:
        logger.error(f"Failed to log upload: {str(e)}")

def get_user_history(user_id=None, limit=10):
    """
    Get recent QA history for a user
    
    Args:
        user_id: User ID to get history for (if None, gets current user)
        limit (int): Maximum number of records to return
        
    Returns:
        list: List of tuples (question, answer, feedback, timestamp)
    """
    try:
        if user_id is None:
            # Get current user from Flask-Login
            from flask_login import current_user
            if current_user.is_authenticated:
                user_id = current_user.username
            else:
                return []
        
        # Query the ChatQA table
        history = ChatQA.query.filter_by(user=user_id)\
            .order_by(ChatQA.timestamp.desc())\
            .limit(limit)\
            .all()
        
        # Return in the expected format: (question, answer, feedback, timestamp)
        # Note: ChatQA model doesn't have a feedback field, so we'll use None
        return [
            (qa.question, qa.answer, None, qa.timestamp)
            for qa in history
        ]
        
    except Exception as e:
        logger.error(f"Error getting user history: {str(e)}")
        return [] 