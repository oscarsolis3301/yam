import os
import csv
import threading
from datetime import datetime
from collections import Counter
from pathlib import Path
from app.utils.logger import setup_logging

logger = setup_logging()

# Global caches
_devices_cache = []
_devices_cache_mtime = None
_devices_cache_path = None
_devices_cache_lock = threading.Lock()

_articles_cache = []
_articles_cache_mtime = None
_articles_cache_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Device CSV helper – self-contained implementation
# ---------------------------------------------------------------------------

def _resolve_devices_dir():
    """Return the absolute Devices directory path"""
    # Current file: <project>/app/utils/cache.py → parent = *utils*, parent of that is *app*
    app_dir = Path(__file__).resolve().parent.parent
    devices_dir = app_dir / "Devices"

    # Fallback to legacy location at repository root if moved
    if not devices_dir.exists():
        repo_root = app_dir.parent  # one level above *app*
        devices_dir = repo_root / "Devices"

    return devices_dir

def get_devices_csv_path(filename=None):
    """Return absolute path to a devices CSV file"""
    devices_dir = _resolve_devices_dir()
    
    # Ensure directory exists
    devices_dir.mkdir(parents=True, exist_ok=True)
    
    if filename:
        return str(devices_dir / filename)
    
    # Today's file
    today_fmt = datetime.now().strftime("%m%d%Y")
    todays_file = devices_dir / f"{today_fmt}Devices.csv"
    if todays_file.exists():
        return str(todays_file)
    
    # Newest CSV in the directory
    csv_files = sorted(devices_dir.glob("*Devices.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if csv_files:
        return str(csv_files[0])
    
    # Fall back to today's path (may not exist)
    return str(todays_file)

def load_devices_cache(force_reload=False):
    """Load devices from CSV with caching"""
    global _devices_cache, _devices_cache_mtime, _devices_cache_path
    
    path = get_devices_csv_path()
    
    try:
        mtime = os.path.getmtime(path) if os.path.exists(path) else None
    except Exception:
        mtime = None
    
    with _devices_cache_lock:
        # Return cached data if available and not forced reload
        if (not force_reload and _devices_cache and 
            _devices_cache_path == path and _devices_cache_mtime == mtime):
            return _devices_cache
        
        try:
            with open(path, newline='', encoding='utf-8') as f:
                _devices_cache = list(csv.DictReader(f))
            _devices_cache_mtime = mtime
            _devices_cache_path = path
            logger.info(f"Loaded {len(_devices_cache)} devices from cache")
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            _devices_cache = []
    
    return _devices_cache

def load_articles_cache(force_reload=False):
    """Load KB articles with caching and proper Flask app context checking"""
    global _articles_cache, _articles_cache_mtime
    
    with _articles_cache_lock:
        if force_reload or not _articles_cache:
            try:
                # Ensure we have a proper Flask app context
                from flask import has_app_context, current_app
                if not has_app_context():
                    logger.debug("No app context available for articles cache loading")
                    return _articles_cache  # Return existing cache or empty list
                
                # Test database connectivity before proceeding
                from extensions import db
                from sqlalchemy import text
                try:
                    db.session.execute(text('SELECT 1'))
                except Exception as db_test_err:
                    logger.debug(f"Database not ready for articles cache loading: {db_test_err}")
                    return _articles_cache  # Return existing cache or empty list
                
                # Import KBArticle with SearchHistory conflict handling
                try:
                    from app.models.base import KBArticle
                except Exception as import_err:
                    logger.warning(f"Failed to import KBArticle from base: {import_err}")
                    # Fallback to direct import
                    from app.models import KBArticle
                
                # Use raw SQL to avoid SearchHistory conflicts
                try:
                    result = db.session.execute(text("""
                        SELECT id, title, description, category, tags, status, is_public, 
                               created_at, file_path, author_id
                        FROM kb_article 
                        WHERE status = 'approved' AND is_public = 1
                        ORDER BY created_at DESC
                    """))
                    
                    articles_data = result.fetchall()
                    articles = []
                    
                    for row in articles_data:
                        # Handle created_at properly - convert string to datetime if needed
                        created_at = row[7]
                        if isinstance(created_at, str):
                            try:
                                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                # If parsing fails, use current time as fallback
                                created_at = datetime.utcnow()
                        
                        article = type('KBArticle', (), {
                            'id': row[0],
                            'title': row[1],
                            'description': row[2],
                            'category': row[3],
                            'tags': row[4],
                            'status': row[5],
                            'is_public': row[6],
                            'created_at': created_at,
                            'file_path': row[8],
                            'author': type('User', (), {'username': 'System'})()
                        })()
                        articles.append(article)
                        
                except Exception as sql_err:
                    logger.warning(f"Raw SQL failed, trying ORM: {sql_err}")
                    # Fallback to ORM
                    articles = (
                        KBArticle.query
                        .filter(
                            KBArticle.status == 'approved',
                            KBArticle.is_public == True
                        )
                        .order_by(KBArticle.created_at.desc())
                        .all()
                    )
                
                # Count statuses for logging
                status_counts = Counter(a.status for a in articles)
                statuses_str = ', '.join(f"{count} - {status}" for status, count in status_counts.items())
                logger.info(f"Loaded {len(articles)} articles. Statuses: {statuses_str}")
                
                # Debug: Log the first few created_at values to help diagnose issues
                if articles:
                    for i, article in enumerate(articles[:3]):
                        logger.debug(f"Article {i+1} created_at type: {type(article.created_at)}, value: {article.created_at}")
                
                # Build cache with error handling for each article
                _articles_cache = []
                for a in articles:
                    try:
                        # Handle created_at conversion safely
                        created_at_str = None
                        if hasattr(a.created_at, 'isoformat'):
                            created_at_str = a.created_at.isoformat()
                        elif isinstance(a.created_at, str):
                            created_at_str = a.created_at
                        else:
                            created_at_str = str(a.created_at)
                        
                        article_dict = {
                            'id': a.id,
                            'title': a.title,
                            'description': a.description,
                            'category': a.category,
                            'tags': a.tags.split(',') if a.tags else [],
                            'author': a.author.username if hasattr(a.author, 'username') else "System",
                            'created_at': created_at_str,
                            'file_path': a.file_path if a.file_path and a.file_path.lower().endswith('.pdf') else a.file_path,
                            'status': a.status,
                            'is_public': a.is_public
                        }
                        _articles_cache.append(article_dict)
                    except Exception as article_err:
                        logger.warning(f"Failed to process article {getattr(a, 'id', 'unknown')}: {article_err}")
                        # Continue processing other articles
                        continue
                
                _articles_cache_mtime = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Failed to load articles cache: {e}")
                # Don't clear existing cache on error, just return what we have
                return _articles_cache
    
    return _articles_cache

def clear_articles_cache():
    """Clear the articles cache"""
    global _articles_cache
    with _articles_cache_lock:
        _articles_cache.clear()
        logger.info("Articles cache cleared")

def clear_devices_cache():
    """Clear the devices cache"""
    global _devices_cache
    with _devices_cache_lock:
        _devices_cache.clear()
        logger.info("Devices cache cleared") 