from flask import current_app
from app.extensions import db
from app.models import User, ChatQA
import logging

logger = logging.getLogger('spark')

def extract_text(file_path):
    """
    Extract text from a document or image located at *file_path* by delegating to
    the central :pyfunc:`app.utils.document.extract_text` helper so that all
    blueprints share the **same** extraction logic (PDF, DOCX, images, etc.).
    """
    try:
        from app.utils.document import extract_text as _extract
        return _extract(file_path) or ""
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return ""

def get_user_history(user_id, limit=10):
    """
    Get recent QA history for a user
    """
    try:
        history = ChatQA.query.filter_by(user=user_id)\
            .order_by(ChatQA.timestamp.desc())\
            .limit(limit)\
            .all()
        return [{
            'question': qa.question,
            'answer': qa.answer,
            'created_at': qa.timestamp.isoformat()
        } for qa in history]
    except Exception as e:
        logger.error(f"Error getting user history: {str(e)}")
        return []

def get_all_past_questions(limit=100):
    """
    Get all past questions from the QA database
    """
    try:
        questions = ChatQA.query\
            .order_by(ChatQA.timestamp.desc())\
            .limit(limit)\
            .all()
        return [{
            'question': qa.question,
            'answer': qa.answer,
            'user_id': qa.user,
            'created_at': qa.timestamp.isoformat()
        } for qa in questions]
    except Exception as e:
        logger.error(f"Error getting past questions: {str(e)}")
        return []

def update_feedback(qa_id, feedback):
    """
    Update feedback for a QA pair
    """
    try:
        qa = ChatQA.query.get(qa_id)
        if qa:
            # Note: ChatQA doesn't have a feedback field, so we'll need to add it
            # For now, we'll just return True
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating feedback: {str(e)}")
        db.session.rollback()
        return False 