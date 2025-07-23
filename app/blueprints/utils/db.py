import logging
import time
from sqlalchemy.exc import OperationalError

logger = logging.getLogger('spark')

def safe_commit(session, max_retries=5, delay=1):
    """Safely commit database changes with retry logic for locked database"""
    for attempt in range(max_retries):
        try:
            session.commit()
            return True
        except OperationalError as e:
            if 'database is locked' in str(e):
                logger.warning(f"Database locked. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                session.rollback()
                time.sleep(delay)
            else:
                session.rollback()
                logger.error(f"DB commit failed: {e}")
                raise
    logger.error("Could not commit to database after retries.")
    return False 