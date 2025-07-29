"""
Universal Search Engine for PDSI Application

This module provides a comprehensive search system that indexes and searches across:
- Knowledge Base articles
- Outage posts
- User profiles
- Office information
- Workstation data
- Uploaded documents (PDF, DOCX, TXT)
- Ticket descriptions and comments
- Any other dynamic content
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
from io import StringIO
import pandas as pd

# Search engine imports
from whoosh.index import create_in, open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser, MultifieldParser, FuzzyTermPlugin
from whoosh.analysis import StandardAnalyzer, StemmingAnalyzer
from whoosh.writing import AsyncWriter
from whoosh.scoring import BM25F
from whoosh.query import *
from whoosh.highlight import HtmlFormatter, ContextFragmenter
from whoosh.sorting import FieldFacet

# Document processing imports
import PyPDF2
import docx
from PIL import Image
import pytesseract

# Database imports
from app.extensions import db
from app.models import User, KBArticle, Outage, SearchHistory, Document, Note, Activity
from app.blueprints.offices.routes import df as offices_df
from app.utils.device import load_devices_cache
from app.utils.optimized_search_engine import extract_plain_text_from_quill

logger = logging.getLogger(__name__)

# Global variable for offices dataframe
offices_df = None

def load_offices_dataframe():
    """Load offices dataframe for indexing."""
    global offices_df
    try:
        offices_dir = Path('Offices')
        if offices_dir.exists():
            for csv_path in offices_dir.glob('*.csv'):
                try:
                    offices_df = pd.read_csv(csv_path)
                    logger.info(f"Loaded offices data from {csv_path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load offices CSV {csv_path}: {e}")
        offices_df = pd.DataFrame()  # Empty dataframe if no file found
    except Exception as e:
        logger.error(f"Error loading offices dataframe: {e}")
        offices_df = pd.DataFrame()

# Load offices data on module import
load_offices_dataframe()

class UniversalSearchEngine:
    """Universal search engine that indexes and searches across all content types."""
    
    def __init__(self, index_dir: str = "search_index"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)
        
        # Define the schema for our search index
        self.schema = Schema(
            id=ID(stored=True),
            content_type=ID(stored=True),
            title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            description=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            author=TEXT(stored=True),
            tags=TEXT(stored=True),
            category=TEXT(stored=True),
            status=TEXT(stored=True),
            url=TEXT(stored=True),
            section=TEXT(stored=True),
            created_at=DATETIME(stored=True),
            updated_at=DATETIME(stored=True),
            priority=NUMERIC(stored=True, numtype=float),
            views=NUMERIC(stored=True, numtype=int),
            searchable_text=TEXT(stored=True, analyzer=StemmingAnalyzer())
        )
        
        # Initialize the index
        self._init_index()
        
        # Initialize document processors
        self._init_processors()
    
    def _init_index(self):
        """Initialize the search index."""
        try:
            if self.index_dir.exists() and any(self.index_dir.iterdir()):
                self.index = open_dir(str(self.index_dir))
                logger.info("Opened existing search index")
            else:
                self.index = create_in(str(self.index_dir), self.schema)
                logger.info("Created new search index")
        except Exception as e:
            logger.error(f"Error initializing search index: {e}")
            # Create a fresh index if there's an error
            import shutil
            if self.index_dir.exists():
                shutil.rmtree(self.index_dir)
            self.index_dir.mkdir(exist_ok=True)
            self.index = create_in(str(self.index_dir), self.schema)
            logger.info("Created fresh search index after error")
    
    def _init_processors(self):
        """Initialize document processors for different file types."""
        self.processors = {
            '.pdf': self._extract_pdf_text,
            '.docx': self._extract_docx_text,
            '.doc': self._extract_docx_text,
            '.txt': self._extract_txt_text,
            '.md': self._extract_txt_text,
            '.html': self._extract_txt_text,
            '.htm': self._extract_txt_text
        }
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF files."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error extracting PDF text from {file_path}: {e}")
            return ""
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX files."""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting DOCX text from {file_path}: {e}")
            return ""
    
    def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_image_text(self, file_path: str) -> str:
        """Extract text from images using OCR."""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Error extracting image text from {file_path}: {e}")
            return ""
    
    def rebuild_index(self):
        """Rebuild the entire search index."""
        try:
            # Clear existing index
            with self.index.writer() as writer:
                writer.delete_by_query(Every())
            
            # Index all content types
            self._index_kb_articles()
            self._index_outages()
            self._index_users()
            self._index_offices()
            self._index_workstations()
            self._index_documents()
            self._index_notes()
            
            logger.info("Search index rebuilt successfully")
        except Exception as e:
            logger.error(f"Error rebuilding search index: {e}")
            raise
    
    def _index_kb_articles(self):
        """Index all knowledge base articles."""
        try:
            with self.index.writer() as writer:
                articles = KBArticle.query.all()
                
                for article in articles:
                    # Get document text if file exists
                    content = article.content or ""
                    if article.file_path and os.path.exists(article.file_path):
                        file_ext = Path(article.file_path).suffix.lower()
                        if file_ext in self.processors:
                            content += "\n" + self.processors[file_ext](article.file_path)
                    
                    searchable_text = f"{article.title} {content} {article.description or ''} {' '.join(article.tags.split(',') if article.tags else [])}"
                    
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
                        priority=3.0,  # High priority for KB articles
                        views=article.views or 0,
                        searchable_text=searchable_text
                    )
                
                logger.info(f"Indexed {len(articles)} KB articles")
        except Exception as e:
            logger.error(f"Error indexing KB articles: {e}")
    
    def _index_outages(self):
        """Index all outage posts."""
        try:
            with self.index.writer() as writer:
                outages = Outage.query.all()
                
                for outage in outages:
                    searchable_text = f"{outage.title} {outage.description} {outage.affected_systems or ''} {outage.ticket_id or ''}"
                    
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
    
    def _index_users(self):
        """Index all user profiles."""
        try:
            with self.index.writer() as writer:
                users = User.query.filter_by(is_active=True).all()
                
                for user in users:
                    searchable_text = f"{user.username} {user.email} {user.role}"
                    
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
    
    def _index_offices(self):
        """Index all office information."""
        try:
            with self.index.writer() as writer:
                if offices_df is not None and len(offices_df) > 0:
                    for _, office in offices_df.iterrows():
                        searchable_text = f"{office.get('Internal Name', '')} {office.get('Location', '')} {office.get('Mnemonic', '')} {office.get('Number', '')} {office.get('Operations Manager', '')}"
                        
                        writer.add_document(
                            id=f"office_{office.get('Number', '')}",
                            content_type="office",
                            title=office.get('Internal Name', ''),
                            content=f"Location: {office.get('Location', '')}\nPhone: {office.get('Phone', '')}\nManager: {office.get('Operations Manager', '')}",
                            description=f"Office location: {office.get('Location', '')}",
                            author="System",
                            tags=f"office,{office.get('Mnemonic', '')}",
                            category="Offices",
                            status="active",
                            url=f"/offices/{office.get('Number', '')}",
                            section="Offices",
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            priority=2.0,
                            views=0,
                            searchable_text=searchable_text
                        )
                    
                    logger.info(f"Indexed {len(offices_df)} offices")
        except Exception as e:
            logger.error(f"Error indexing offices: {e}")
    
    def _index_workstations(self):
        """Index all workstation information."""
        try:
            with self.index.writer() as writer:
                devices = load_devices_cache()
                if devices is not None and len(devices) > 0:
                    # Convert list to DataFrame if needed
                    if not hasattr(devices, 'iterrows'):
                        import pandas as pd
                        devices = pd.DataFrame(devices)
                    
                    for _, device in devices.iterrows():
                        searchable_text = f"{device.get('Computer Name', '')} {device.get('User Name', '')} {device.get('Office', '')} {device.get('IP Address', '')}"
                        
                        writer.add_document(
                            id=f"workstation_{device.get('Computer Name', '')}",
                            content_type="workstation",
                            title=device.get('Computer Name', ''),
                            content=f"User: {device.get('User Name', '')}\nOffice: {device.get('Office', '')}\nIP: {device.get('IP Address', '')}",
                            description=f"Workstation for {device.get('User Name', '')}",
                            author="System",
                            tags=f"workstation,{device.get('Office', '')}",
                            category="Workstations",
                            status="active",
                            url=f"/workstations/{device.get('Computer Name', '')}",
                            section="Workstations",
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            priority=1.5,
                            views=0,
                            searchable_text=searchable_text
                        )
                    
                    logger.info(f"Indexed {len(devices)} workstations")
        except Exception as e:
            logger.error(f"Error indexing workstations: {e}")
    
    def _index_documents(self):
        """Index all uploaded documents."""
        try:
            with self.index.writer() as writer:
                documents = Document.query.all()
                
                for doc in documents:
                    content = doc.content or ""
                    if doc.file_path and os.path.exists(doc.file_path):
                        file_ext = Path(doc.file_path).suffix.lower()
                        if file_ext in self.processors:
                            content += "\n" + self.processors[file_ext](doc.file_path)
                    
                    searchable_text = f"{doc.title} {content} {doc.description or ''}"
                    
                    writer.add_document(
                        id=f"doc_{doc.id}",
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
                        searchable_text=searchable_text
                    )
                
                logger.info(f"Indexed {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
    
    def _index_notes(self):
        """Index all public user notes."""
        try:
            with self.index.writer() as writer:
                # Only index public notes
                notes = Note.query.filter_by(is_public=True).all()
                
                for note in notes:
                    # Extract plain text from Quill content for better search
                    plain_text = extract_plain_text_from_quill(note.content)
                    searchable_text = f"{note.title} {plain_text} {note.tags or ''}"
                    
                    # Create a clean description from plain text (not raw JSON)
                    description = plain_text[:200] + "..." if len(plain_text) > 200 else plain_text
                    
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
                
                logger.info(f"Indexed {len(notes)} public notes")
        except Exception as e:
            logger.error(f"Error indexing notes: {e}")
    
    def search(self, query: str, limit: int = 20, content_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search across all indexed content."""
        try:
            if not query.strip():
                return []
            
            # Create query parser with fuzzy matching
            parser = MultifieldParser(
                ['title', 'content', 'description', 'searchable_text', 'tags', 'author'],
                self.schema
            )
            parser.add_plugin(FuzzyTermPlugin())
            
            # Parse the query
            q = parser.parse(query)
            
            # Add content type filter if specified
            if content_types:
                content_type_query = Or([Term('content_type', ct) for ct in content_types])
                q = And([q, content_type_query])
            
            # Perform the search
            with self.index.searcher() as searcher:
                results = searcher.search(q, limit=limit)
                
                # Format results
                formatted_results = []
                for result in results:
                    # Highlight search terms
                    highlighted_title = self._highlight_text(result['title'], query)
                    highlighted_description = self._highlight_text(result['description'], query)
                    
                    formatted_results.append({
                        'id': result['id'],
                        'content_type': result['content_type'],
                        'title': result['title'],
                        'highlighted_title': highlighted_title,
                        'description': result['description'],
                        'highlighted_description': highlighted_description,
                        'author': result['author'],
                        'tags': result['tags'],
                        'category': result['category'],
                        'status': result['status'],
                        'url': result['url'],
                        'section': result['section'],
                        'created_at': result['created_at'].isoformat() if result['created_at'] else None,
                        'updated_at': result['updated_at'].isoformat() if result['updated_at'] else None,
                        'priority': result['priority'],
                        'views': result['views'],
                        'score': result.score
                    })
                
                return formatted_results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _highlight_text(self, text: str, query: str) -> str:
        """Highlight search terms in text."""
        if not text or not query:
            return text
        
        try:
            # Simple highlighting - can be enhanced with more sophisticated algorithms
            query_terms = query.lower().split()
            highlighted_text = text
            
            for term in query_terms:
                if len(term) > 2:  # Only highlight terms longer than 2 characters
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    highlighted_text = pattern.sub(f'<mark>{term}</mark>', highlighted_text)
            
            return highlighted_text
        except Exception as e:
            logger.error(f"Error highlighting text: {e}")
            return text
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        try:
            if len(query.strip()) < 2:
                return []
            
            # Get recent search history
            recent_searches = db.session.query(SearchHistory).filter(
                SearchHistory.query.ilike(f'%{query}%')
            ).order_by(SearchHistory.timestamp.desc()).limit(limit).all()
            
            suggestions = []
            for search in recent_searches:
                if search.query not in suggestions:
                    suggestions.append(search.query)
            
            # Add common patterns if we don't have enough suggestions
            if len(suggestions) < limit:
                common_patterns = [
                    f"{query} outage",
                    f"{query} user",
                    f"{query} office",
                    f"{query} workstation",
                    f"{query} document"
                ]
                for pattern in common_patterns:
                    if pattern not in suggestions and len(suggestions) < limit:
                        suggestions.append(pattern)
            
            return suggestions[:limit]
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
    
    def index_single_item(self, content_type: str, item_id: int):
        """Index a single item by content type and ID."""
        try:
            if content_type == 'kb_article':
                article = KBArticle.query.get(item_id)
                if article:
                    self._index_single_kb_article(article)
            elif content_type == 'outage':
                outage = Outage.query.get(item_id)
                if outage:
                    self._index_single_outage(outage)
            elif content_type == 'user':
                user = User.query.get(item_id)
                if user:
                    self._index_single_user(user)
            elif content_type == 'document':
                document = Document.query.get(item_id)
                if document:
                    self._index_single_document(document)
            elif content_type == 'note':
                note = Note.query.get(item_id)
                if note:
                    self._index_single_note(note)
        except Exception as e:
            logger.error(f"Error indexing single item {content_type}:{item_id}: {e}")
    
    def _index_single_kb_article(self, article: KBArticle):
        """Index a single KB article."""
        with self.index.writer() as writer:
            # Delete existing entry
            writer.delete_by_term('id', f'kb_{article.id}')
            
            # Add new entry
            content = article.content or ""
            if article.file_path and os.path.exists(article.file_path):
                file_ext = Path(article.file_path).suffix.lower()
                if file_ext in self.processors:
                    content += "\n" + self.processors[file_ext](article.file_path)
            
            searchable_text = f"{article.title} {content} {article.description or ''} {' '.join(article.tags.split(',') if article.tags else [])}"
            
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
    
    def _index_single_outage(self, outage: Outage):
        """Index a single outage."""
        with self.index.writer() as writer:
            writer.delete_by_term('id', f'outage_{outage.id}')
            
            searchable_text = f"{outage.title} {outage.description} {outage.affected_systems or ''} {outage.ticket_id or ''}"
            
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
    
    def _index_single_user(self, user: User):
        """Index a single user."""
        with self.index.writer() as writer:
            writer.delete_by_term('id', f'user_{user.id}')
            
            searchable_text = f"{user.username} {user.email} {user.role}"
            
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
    
    def _index_single_document(self, document: Document):
        """Index a single document."""
        with self.index.writer() as writer:
            writer.delete_by_term('id', f'doc_{document.id}')
            
            content = document.content or ""
            if document.file_path and os.path.exists(document.file_path):
                file_ext = Path(document.file_path).suffix.lower()
                if file_ext in self.processors:
                    content += "\n" + self.processors[file_ext](document.file_path)
            
            searchable_text = f"{document.title} {content} {document.description or ''}"
            
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
    
    def _index_single_note(self, note: Note):
        """Index a single note."""
        with self.index.writer() as writer:
            writer.delete_by_term('id', f'note_{note.id}')
            
            # Only index if the note is public
            if not note.is_public:
                logger.info(f"Skipping private note {note.id} from search index")
                return
            
            # Extract plain text from Quill content for better search
            plain_text = extract_plain_text_from_quill(note.content)
            searchable_text = f"{note.title} {plain_text} {note.tags or ''}"
            
            # Create a clean description from plain text (not raw JSON)
            description = plain_text[:200] + "..." if len(plain_text) > 200 else plain_text
            
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

# Global search engine instance
search_engine = UniversalSearchEngine() 