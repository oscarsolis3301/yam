"""
Index Management Utility

This module provides functionality to automatically index new content
and keep the search index up to date in real-time.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from queue import Queue, Empty
import os

from app.utils.search_engine import search_engine
from app.utils.optimized_search_engine import extract_plain_text_from_quill
from app.models import KBArticle, Outage, User, Document, Note
from app.extensions import db

logger = logging.getLogger(__name__)

class IndexManager:
    """Manages automatic indexing of content changes."""
    
    def __init__(self):
        self.index_queue = Queue()
        self.is_running = False
        self.index_thread = None
        self.last_index_time = {}
        
        # Track what needs to be indexed
        self.pending_indexes = {
            'kb_articles': set(),
            'outages': set(),
            'users': set(),
            'documents': set(),
            'notes': set()
        }
    
    def start(self):
        """Start the index manager background thread."""
        if self.is_running:
            return
        
        self.is_running = True
        self.index_thread = threading.Thread(target=self._index_worker, daemon=True)
        self.index_thread.start()
        logger.info("Index manager started")
    
    def stop(self):
        """Stop the index manager."""
        self.is_running = False
        if self.index_thread:
            self.index_thread.join(timeout=5)
        logger.info("Index manager stopped")
    
    def _index_worker(self):
        """Background worker that processes index queue."""
        while self.is_running:
            try:
                # Process queue items
                while not self.index_queue.empty():
                    item = self.index_queue.get_nowait()
                    self._process_index_item(item)
                    self.index_queue.task_done()
                
                # Sleep briefly before next iteration
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in index worker: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _process_index_item(self, item: Dict[str, Any]):
        """Process a single index item."""
        try:
            action = item.get('action')
            content_type = item.get('content_type')
            item_id = item.get('item_id')
            
            if action == 'index':
                search_engine.index_single_item(content_type, item_id)
            elif action == 'delete':
                self._delete_from_index(content_type, item_id)
            elif action == 'rebuild':
                search_engine.rebuild_index()
            
            logger.info(f"Processed index item: {action} {content_type}:{item_id}")
            
        except Exception as e:
            logger.error(f"Error processing index item: {e}")
    
    def _delete_from_index(self, content_type: str, item_id: int):
        """Delete an item from the search index."""
        try:
            with search_engine.index.writer() as writer:
                writer.delete_by_term('id', f'{content_type}_{item_id}')
            logger.info(f"Deleted {content_type}:{item_id} from index")
        except Exception as e:
            logger.error(f"Error deleting from index: {e}")
    
    def queue_index_item(self, content_type: str, item_id: int, action: str = 'index'):
        """Queue an item for indexing."""
        item = {
            'action': action,
            'content_type': content_type,
            'item_id': item_id,
            'timestamp': datetime.utcnow()
        }
        self.index_queue.put(item)
    
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
            logger.error(f"Error processing pending indexes: {e}")
    
    def _index_kb_articles(self, article_ids: List[int]):
        """Index specific KB articles."""
        try:
            with search_engine.index.writer() as writer:
                articles = KBArticle.query.filter(KBArticle.id.in_(article_ids)).all()
                
                for article in articles:
                    # Delete existing index entry
                    writer.delete_by_term('id', f'kb_{article.id}')
                    
                    # Get document text if file exists
                    content = article.content or ""
                    if article.file_path and os.path.exists(article.file_path):
                        file_ext = os.path.splitext(article.file_path)[1].lower()
                        if file_ext in search_engine.processors:
                            content += "\n" + search_engine.processors[file_ext](article.file_path)
                    
                    searchable_text = f"{article.title} {content} {article.description or ''} {' '.join(article.tags.split(',') if article.tags else [])}"
                    
                    # Add new index entry
                    writer.add_document(
                        id=f"kb_{article.id}",
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
                        searchable_text=searchable_text
                    )
                
                logger.info(f"Indexed {len(articles)} KB articles")
        except Exception as e:
            logger.error(f"Error indexing KB articles: {e}")
    
    def _index_outages(self, outage_ids: List[int]):
        """Index specific outages."""
        try:
            with search_engine.index.writer() as writer:
                outages = Outage.query.filter(Outage.id.in_(outage_ids)).all()
                
                for outage in outages:
                    # Delete existing index entry
                    writer.delete_by_term('id', f'outage_{outage.id}')
                    
                    searchable_text = f"{outage.title} {outage.description} {outage.affected_systems or ''} {outage.ticket_id or ''}"
                    
                    # Add new index entry
                    writer.add_document(
                        id=f"outage_{outage.id}",
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
                        searchable_text=searchable_text
                    )
                
                logger.info(f"Indexed {len(outages)} outages")
        except Exception as e:
            logger.error(f"Error indexing outages: {e}")
    
    def _index_users(self, user_ids: List[int]):
        """Index specific users."""
        try:
            with search_engine.index.writer() as writer:
                users = User.query.filter(User.id.in_(user_ids)).all()
                
                for user in users:
                    # Delete existing index entry
                    writer.delete_by_term('id', f'user_{user.id}')
                    
                    searchable_text = f"{user.username} {user.email} {user.role}"
                    
                    # Add new index entry
                    writer.add_document(
                        id=f"user_{user.id}",
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
                        searchable_text=searchable_text
                    )
                
                logger.info(f"Indexed {len(users)} users")
        except Exception as e:
            logger.error(f"Error indexing users: {e}")
    
    def _index_documents(self, document_ids: List[int]):
        """Index specific documents."""
        try:
            with search_engine.index.writer() as writer:
                documents = Document.query.filter(Document.id.in_(document_ids)).all()
                
                for document in documents:
                    # Delete existing index entry
                    writer.delete_by_term('id', f'doc_{document.id}')
                    
                    content = document.content or ""
                    if document.file_path and os.path.exists(document.file_path):
                        file_ext = os.path.splitext(document.file_path)[1].lower()
                        if file_ext in search_engine.processors:
                            content += "\n" + search_engine.processors[file_ext](document.file_path)
                    
                    searchable_text = f"{document.title} {content} {document.description or ''}"
                    
                    # Add new index entry
                    writer.add_document(
                        id=f"doc_{document.id}",
                        content_type="document",
                        title=document.title,
                        content=content,
                        description=document.description or "",
                        author=document.user.username if document.user else "Unknown",
                        tags=document.tags or "",
                        category="Documents",
                        status="active",
                        url=f"/documents/{document.id}",
                        section="Documents",
                        created_at=document.created_at,
                        updated_at=document.updated_at,
                        priority=1.0,
                        views=0,
                        searchable_text=searchable_text
                    )
                
                logger.info(f"Indexed {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
    
    def _index_notes(self, note_ids: List[int]):
        """Index specific notes."""
        try:
            with search_engine.index.writer() as writer:
                notes = Note.query.filter(Note.id.in_(note_ids)).all()
                
                for note in notes:
                    # Delete existing index entry
                    writer.delete_by_term('id', f'note_{note.id}')
                    
                    # Extract plain text from Quill content for better search
                    plain_text = extract_plain_text_from_quill(note.content)
                    searchable_text = f"{note.title} {plain_text} {note.tags or ''}"
                    
                    # Create a clean description from plain text (not raw JSON)
                    description = plain_text[:200] + "..." if len(plain_text) > 200 else plain_text
                    
                    # Add new index entry
                    writer.add_document(
                        id=f"note_{note.id}",
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
                        searchable_text=searchable_text
                    )
                
                logger.info(f"Indexed {len(notes)} notes")
        except Exception as e:
            logger.error(f"Error indexing notes: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index manager statistics."""
        return {
            'is_running': self.is_running,
            'queue_size': self.index_queue.qsize(),
            'pending_indexes': {
                content_type: len(ids) for content_type, ids in self.pending_indexes.items()
            },
            'last_index_time': self.last_index_time
        }

# Global index manager instance
index_manager = IndexManager() 