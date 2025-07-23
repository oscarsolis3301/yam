"""
Optimized Index Management Utility

This module provides functionality to automatically index new content
and keep the search index up to date in real-time using the database-based
search engine.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from queue import Queue
import os

from app.utils.optimized_search_engine import optimized_search_engine, extract_plain_text_from_quill
from app.models import KBArticle, Outage, User, Document, Note, SearchIndex
from extensions import db

logger = logging.getLogger(__name__)

class OptimizedIndexManager:
    """Manages automatic indexing of content changes using database storage."""
    
    def __init__(self):
        self.index_queue = Queue()
        self.is_running = False
        self.index_thread = None
        self.last_index_time = {}
        self.app = None  # Store Flask app instance for context
        
        # Track what needs to be indexed
        self.pending_indexes = {
            'kb_articles': set(),
            'outages': set(),
            'users': set(),
            'documents': set(),
            'notes': set()
        }
    
    def set_app(self, app):
        """Set the Flask app instance for application context."""
        self.app = app
    
    def start(self):
        """Start the index manager background thread."""
        if self.is_running:
            return
        
        self.is_running = True
        self.index_thread = threading.Thread(target=self._index_worker, daemon=True)
        self.index_thread.start()
        logger.info("Optimized index manager started")
    
    def stop(self):
        """Stop the index manager."""
        self.is_running = False
        if self.index_thread:
            self.index_thread.join(timeout=5)
        logger.info("Optimized index manager stopped")
    
    def _index_worker(self):
        """Background worker that processes index queue."""
        while self.is_running:
            try:
                # Only process if app is available
                if not self.app:
                    time.sleep(5)  # Wait longer when app is not available
                    continue
                
                # Process queue items
                while not self.index_queue.empty():
                    item = self.index_queue.get_nowait()
                    self._process_index_item_with_context(item)
                    self.index_queue.task_done()
                
                # Process pending indexes periodically
                self._process_pending_indexes_with_context()
                
                # Sleep briefly before next iteration
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in optimized index worker: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _process_index_item_with_context(self, item: Dict[str, Any]):
        """Process a single index item with proper Flask application context."""
        if not self.app:
            # Don't log error repeatedly - just skip silently until app is available
            return
            
        try:
            with self.app.app_context():
                self._process_index_item(item)
        except Exception as e:
            logger.error(f"Error processing optimized index item with context: {e}")
    
    def _process_pending_indexes_with_context(self):
        """Process pending indexes with proper Flask application context."""
        if not self.app:
            # Don't log error repeatedly - just skip silently until app is available
            return
            
        try:
            with self.app.app_context():
                self.process_pending_indexes()
        except Exception as e:
            logger.error(f"Error processing pending indexes with context: {e}")
    
    def _process_index_item(self, item: Dict[str, Any]):
        """Process a single index item."""
        try:
            action = item.get('action')
            content_type = item.get('content_type')
            item_id = item.get('item_id')
            
            if action == 'index':
                optimized_search_engine.index_single_item(content_type, item_id)
            elif action == 'delete':
                self._delete_from_index(content_type, item_id)
            elif action == 'rebuild':
                optimized_search_engine.rebuild_index()
            
            logger.info(f"Processed optimized index item: {action} {content_type}:{item_id}")
            
        except Exception as e:
            logger.error(f"Error processing optimized index item: {e}")
    
    def _delete_from_index(self, content_type: str, item_id: int):
        """Delete an item from the search index."""
        try:
            optimized_search_engine.delete_item(content_type, item_id)
            logger.info(f"Deleted {content_type}:{item_id} from optimized index")
        except Exception as e:
            logger.error(f"Error deleting from optimized index: {e}")
    
    def queue_index_item(self, content_type: str, item_id: int, action: str = 'index'):
        """Queue an item for indexing."""
        item = {
            'action': action,
            'content_type': content_type,
            'item_id': item_id,
            'timestamp': datetime.utcnow()
        }
        self.index_queue.put(item)
    
    def index_item_sync(self, content_type: str, item_id: int, action: str = 'index'):
        """Index an item synchronously (immediate, no queue)."""
        if not self.app:
            # Skip silently if app is not available yet
            return
            
        try:
            with self.app.app_context():
                if action == 'index':
                    optimized_search_engine.index_single_item(content_type, item_id)
                elif action == 'delete':
                    optimized_search_engine.delete_item(content_type, item_id)
                logger.info(f"Synchronously indexed {content_type}:{item_id} with action {action}")
        except Exception as e:
            logger.error(f"Error synchronously indexing {content_type}:{item_id}: {e}")
    
    def queue_rebuild(self):
        """Queue a full index rebuild."""
        item = {
            'action': 'rebuild',
            'timestamp': datetime.utcnow()
        }
        self.index_queue.put(item)
    
    def mark_for_indexing(self, content_type: str, item_id: int):
        """Mark an item for indexing (for batch processing)."""
        if content_type in self.pending_indexes:
            self.pending_indexes[content_type].add(item_id)
    
    def process_pending_indexes(self):
        """Process all pending indexes."""
        try:
            # Process KB articles
            if self.pending_indexes['kb_articles']:
                self._index_kb_articles(list(self.pending_indexes['kb_articles']))
                self.pending_indexes['kb_articles'].clear()
            
            # Process outages
            if self.pending_indexes['outages']:
                self._index_outages(list(self.pending_indexes['outages']))
                self.pending_indexes['outages'].clear()
            
            # Process users
            if self.pending_indexes['users']:
                self._index_users(list(self.pending_indexes['users']))
                self.pending_indexes['users'].clear()
            
            # Process documents
            if self.pending_indexes['documents']:
                self._index_documents(list(self.pending_indexes['documents']))
                self.pending_indexes['documents'].clear()
            
            # Process notes
            if self.pending_indexes['notes']:
                self._index_notes(list(self.pending_indexes['notes']))
                self.pending_indexes['notes'].clear()
                
        except Exception as e:
            logger.error(f"Error processing pending optimized indexes: {e}")
    
    def _index_kb_articles(self, article_ids: List[int]):
        """Index specific KB articles."""
        try:
            articles = KBArticle.query.filter(KBArticle.id.in_(article_ids)).all()
            
            for article in articles:
                # Delete existing index entry
                db.session.query(SearchIndex).filter(
                    SearchIndex.content_type == 'kb_article',
                    SearchIndex.content_id == f'kb_{article.id}'
                ).delete()
                
                # Get document text if file exists
                content = article.content or ""
                if article.file_path and os.path.exists(article.file_path):
                    file_ext = os.path.splitext(article.file_path)[1].lower()
                    if file_ext in optimized_search_engine.processors:
                        content += "\n" + optimized_search_engine.processors[file_ext](article.file_path)
                
                searchable_text = f"{article.title} {content} {article.description or ''} {' '.join(article.tags.split(',') if article.tags else [])}"
                
                # Add new index entry
                search_index = SearchIndex(
                    content_id=f"kb_{article.id}",
                    content_type="kb_article",
                    title=article.title,
                    content=content,
                    description=article.description or "",
                    author=article.author,
                    tags=article.tags or "",
                    category=article.category or "",
                    status=article.status,
                    url=f"/kb/{article.id}",
                    section="Knowledge Base",
                    created_at=article.created_at,
                    updated_at=article.updated_at,
                    priority=3.0,
                    views=article.views or 0,
                    searchable_text=searchable_text,
                    last_indexed=datetime.utcnow()
                )
                db.session.add(search_index)
            
            db.session.commit()
            logger.info(f"Indexed {len(articles)} KB articles in optimized manager")
        except Exception as e:
            logger.error(f"Error indexing KB articles in optimized manager: {e}")
            db.session.rollback()
    
    def _index_outages(self, outage_ids: List[int]):
        """Index specific outages."""
        try:
            outages = Outage.query.filter(Outage.id.in_(outage_ids)).all()
            
            for outage in outages:
                # Delete existing index entry
                db.session.query(SearchIndex).filter(
                    SearchIndex.content_type == 'outage',
                    SearchIndex.content_id == f'outage_{outage.id}'
                ).delete()
                
                searchable_text = f"{outage.title} {outage.description} {outage.affected_systems or ''} {outage.ticket_id or ''}"
                
                # Add new index entry
                search_index = SearchIndex(
                    content_id=f"outage_{outage.id}",
                    content_type="outage",
                    title=outage.title,
                    content=outage.description,
                    description=outage.description,
                    author="System",
                    tags=f"outage,{outage.severity},{outage.status}",
                    category="System Status",
                    status=outage.status,
                    url=f"/outages/{outage.id}",
                    section="Outages",
                    created_at=outage.created_at,
                    updated_at=outage.updated_at,
                    priority=2.0,
                    views=0,
                    searchable_text=searchable_text,
                    last_indexed=datetime.utcnow()
                )
                db.session.add(search_index)
            
            db.session.commit()
            logger.info(f"Indexed {len(outages)} outages in optimized manager")
        except Exception as e:
            logger.error(f"Error indexing outages in optimized manager: {e}")
            db.session.rollback()
    
    def _index_users(self, user_ids: List[int]):
        """Index specific users."""
        try:
            users = User.query.filter(User.id.in_(user_ids)).all()
            
            for user in users:
                # Delete existing index entry
                db.session.query(SearchIndex).filter(
                    SearchIndex.content_type == 'user',
                    SearchIndex.content_id == f'user_{user.id}'
                ).delete()
                
                searchable_text = f"{user.username} {user.email} {user.role}"
                
                # Add new index entry
                search_index = SearchIndex(
                    content_id=f"user_{user.id}",
                    content_type="user",
                    title=user.username,
                    content=f"Email: {user.email}\nRole: {user.role}",
                    description=f"User profile for {user.username}",
                    author=user.username,
                    tags=f"user,{user.role}",
                    category="Users",
                    status="active" if user.is_active else "inactive",
                    url=f"/users/{user.id}",
                    section="Users",
                    created_at=user.created_at,
                    updated_at=user.last_seen or user.created_at,
                    priority=1.5,
                    views=0,
                    searchable_text=searchable_text,
                    last_indexed=datetime.utcnow()
                )
                db.session.add(search_index)
            
            db.session.commit()
            logger.info(f"Indexed {len(users)} users in optimized manager")
        except Exception as e:
            logger.error(f"Error indexing users in optimized manager: {e}")
            db.session.rollback()
    
    def _index_documents(self, document_ids: List[int]):
        """Index specific documents."""
        try:
            documents = Document.query.filter(Document.id.in_(document_ids)).all()
            
            for doc in documents:
                # Delete existing index entry
                db.session.query(SearchIndex).filter(
                    SearchIndex.content_type == 'document',
                    SearchIndex.content_id == f'doc_{doc.id}'
                ).delete()
                
                content = doc.content or ""
                if doc.file_path and os.path.exists(doc.file_path):
                    file_ext = os.path.splitext(doc.file_path)[1].lower()
                    if file_ext in optimized_search_engine.processors:
                        content += "\n" + optimized_search_engine.processors[file_ext](doc.file_path)
                
                searchable_text = f"{doc.title} {content} {doc.description or ''}"
                
                # Add new index entry
                search_index = SearchIndex(
                    content_id=f"doc_{doc.id}",
                    content_type="document",
                    title=doc.title,
                    content=content,
                    description=doc.description or "",
                    author=doc.user.username if doc.user else "Unknown",
                    tags=doc.tags or "",
                    category="Documents",
                    status="active",
                    url=f"/documents/{doc.id}",
                    section="Documents",
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                    priority=1.0,
                    views=0,
                    searchable_text=searchable_text,
                    last_indexed=datetime.utcnow()
                )
                db.session.add(search_index)
            
            db.session.commit()
            logger.info(f"Indexed {len(documents)} documents in optimized manager")
        except Exception as e:
            logger.error(f"Error indexing documents in optimized manager: {e}")
            db.session.rollback()
    
    def _index_notes(self, note_ids: List[int]):
        """Index specific notes."""
        try:
            notes = Note.query.filter(Note.id.in_(note_ids)).all()
            
            for note in notes:
                # Delete existing index entry
                db.session.query(SearchIndex).filter(
                    SearchIndex.content_type == 'note',
                    SearchIndex.content_id == f'note_{note.id}'
                ).delete()
                
                # Extract plain text from Quill content for better search
                plain_text = extract_plain_text_from_quill(note.content)
                searchable_text = f"{note.title} {plain_text} {note.tags or ''}"
                
                # Create a clean description from plain text (not raw JSON)
                description = plain_text[:200] + "..." if len(plain_text) > 200 else plain_text
                
                # Add new index entry
                search_index = SearchIndex(
                    content_id=f"note_{note.id}",
                    content_type="note",
                    title=note.title,
                    content=note.content,  # Keep original content for full processing
                    description=description,  # Use clean plain text for preview
                    author=note.user.username if note.user else "Unknown",
                    tags=note.tags or "",
                    category="Notes",
                    status="active",
                    url=f"/notes/{note.id}",
                    section="Notes",
                    created_at=note.created_at,
                    updated_at=note.updated_at,
                    priority=1.0,
                    views=0,
                    searchable_text=searchable_text,
                    last_indexed=datetime.utcnow()
                )
                db.session.add(search_index)
            
            db.session.commit()
            logger.info(f"Indexed {len(notes)} notes in optimized manager")
        except Exception as e:
            logger.error(f"Error indexing notes in optimized manager: {e}")
            db.session.rollback()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index manager statistics."""
        try:
            return {
                'is_running': self.is_running,
                'queue_size': self.index_queue.qsize(),
                'pending_indexes': {
                    content_type: len(ids) for content_type, ids in self.pending_indexes.items()
                },
                'last_index_time': self.last_index_time
            }
        except Exception as e:
            logger.error(f"Error getting optimized index manager stats: {e}")
            return {}

# Global instance - don't auto-start it here
optimized_index_manager = OptimizedIndexManager()

def get_index_manager():
    """Compatibility method to return the global optimized index manager instance."""
    return optimized_index_manager

# NOTE: Don't auto-start here - we need to set the app instance first 