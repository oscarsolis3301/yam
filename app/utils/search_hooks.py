"""
Search Indexing Hooks

This module provides hooks for automatically indexing content when it's
created, updated, or deleted. This ensures the search index stays up to date.
"""

import logging
from typing import Optional
from app.utils.optimized_index_manager import optimized_index_manager

logger = logging.getLogger(__name__)

def index_kb_article(article_id: int, action: str = 'index'):
    """Index a KB article when created or updated."""
    try:
        optimized_index_manager.queue_index_item('kb_article', article_id, action)
        logger.debug(f"Queued KB article {article_id} for {action}")
    except Exception as e:
        logger.error(f"Error queuing KB article {article_id} for indexing: {e}")

def index_outage(outage_id: int, action: str = 'index'):
    """Index an outage when created or updated."""
    try:
        optimized_index_manager.queue_index_item('outage', outage_id, action)
        logger.debug(f"Queued outage {outage_id} for {action}")
    except Exception as e:
        logger.error(f"Error queuing outage {outage_id} for indexing: {e}")

def index_user(user_id: int, action: str = 'index'):
    """Index a user when created or updated."""
    try:
        optimized_index_manager.queue_index_item('user', user_id, action)
        logger.debug(f"Queued user {user_id} for {action}")
    except Exception as e:
        logger.error(f"Error queuing user {user_id} for indexing: {e}")

def index_document(document_id: int, action: str = 'index'):
    """Index a document when created or updated."""
    try:
        optimized_index_manager.queue_index_item('document', document_id, action)
        logger.debug(f"Queued document {document_id} for {action}")
    except Exception as e:
        logger.error(f"Error queuing document {document_id} for indexing: {e}")

def index_note(note_id: int, action: str = 'index'):
    """Index a note when created or updated."""
    try:
        optimized_index_manager.queue_index_item('note', note_id, action)
        logger.debug(f"Queued note {note_id} for {action}")
    except Exception as e:
        logger.error(f"Error queuing note {note_id} for indexing: {e}")

def delete_from_index(content_type: str, item_id: int):
    """Delete an item from the search index."""
    try:
        optimized_index_manager.queue_index_item(content_type, item_id, 'delete')
        logger.debug(f"Queued {content_type} {item_id} for deletion from index")
    except Exception as e:
        logger.error(f"Error queuing {content_type} {item_id} for deletion: {e}")

def rebuild_search_index():
    """Queue a full search index rebuild."""
    try:
        optimized_index_manager.queue_rebuild()
        logger.info("Queued full search index rebuild")
    except Exception as e:
        logger.error(f"Error queuing search index rebuild: {e}")

# Convenience functions for common operations
def on_kb_article_created(article_id: int):
    """Called when a KB article is created."""
    index_kb_article(article_id, 'index')

def on_kb_article_updated(article_id: int):
    """Called when a KB article is updated."""
    index_kb_article(article_id, 'index')

def on_kb_article_deleted(article_id: int):
    """Called when a KB article is deleted."""
    delete_from_index('kb_article', article_id)

def on_outage_created(outage_id: int):
    """Called when an outage is created."""
    index_outage(outage_id, 'index')

def on_outage_updated(outage_id: int):
    """Called when an outage is updated."""
    index_outage(outage_id, 'index')

def on_outage_deleted(outage_id: int):
    """Called when an outage is deleted."""
    delete_from_index('outage', outage_id)

def on_user_created(user_id: int):
    """Called when a user is created."""
    index_user(user_id, 'index')

def on_user_updated(user_id: int):
    """Called when a user is updated."""
    index_user(user_id, 'index')

def on_user_deleted(user_id: int):
    """Called when a user is deleted."""
    delete_from_index('user', user_id)

def on_document_created(document_id: int):
    """Called when a document is created."""
    index_document(document_id, 'index')

def on_document_updated(document_id: int):
    """Called when a document is updated."""
    index_document(document_id, 'index')

def on_document_deleted(document_id: int):
    """Called when a document is deleted."""
    delete_from_index('document', document_id)

def on_note_created(note_id: int):
    """Called when a note is created."""
    index_note(note_id, 'index')

def on_note_updated(note_id: int):
    """Called when a note is updated."""
    index_note(note_id, 'index')

def on_note_deleted(note_id: int):
    """Called when a note is deleted."""
    delete_from_index('note', note_id) 