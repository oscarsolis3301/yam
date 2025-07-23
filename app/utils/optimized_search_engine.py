"""
Optimized Universal Search Engine for PDSI Application

This module provides a fast search system that uses a persistent database
instead of rebuilding the index on every startup. This dramatically reduces
startup time while maintaining all search functionality.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
from io import StringIO
import pandas as pd
from sqlalchemy import or_, and_, func, text
from sqlalchemy.orm import joinedload

# Document processing imports
import PyPDF2
import docx
from PIL import Image
import pytesseract

# Database imports
from extensions import db
from app.models import User, KBArticle, Outage, SearchHistory, Document, Note, Activity, SearchIndex
from app.blueprints.offices.routes import df as offices_df
from app.utils.device import load_devices_cache

logger = logging.getLogger(__name__)

def extract_plain_text_from_quill(content: str) -> str:
    """
    Extract plain text from Quill editor Delta format.
    
    Args:
        content: String containing Quill Delta JSON format
        
    Returns:
        Plain text string with images and other embeds filtered out
    """
    try:
        if not content:
            return ""
            
        # Try to parse as JSON
        data = json.loads(content)
        
        # Check if it's Quill Delta format
        if isinstance(data, dict) and 'ops' in data and isinstance(data['ops'], list):
            text_parts = []
            
            for op in data['ops']:
                if isinstance(op, dict) and 'insert' in op:
                    insert_data = op['insert']
                    
                    # Only process text inserts, skip images and other embeds
                    if isinstance(insert_data, str):
                        # Clean up the text - remove excessive newlines but preserve structure
                        text = insert_data.replace('\n\n\n', '\n\n')  # Reduce triple+ newlines to double
                        text_parts.append(text)
                    # Skip non-string inserts (images, videos, etc.)
            
            return ' '.join(text_parts).strip()
        else:
            # If not Quill format, return as-is (fallback for plain text)
            return content
            
    except (json.JSONDecodeError, KeyError, TypeError):
        # If parsing fails, treat as plain text
        return content

class OptimizedSearchEngine:
    """Optimized search engine that uses database for persistent storage."""
    
    def __init__(self):
        # Initialize document processors
        self._init_processors()
        
        # Track indexing status - don't load immediately to avoid app context issues
        self.last_full_index = None
        self._index_time_loaded = False
    
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
        """Extract text from PDF files and include page markers for accurate previews."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_parts: List[str] = []
                for idx, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text() or ""
                    # Prefix each page with an easily searchable marker so we can
                    # later determine the originating page for a snippet.
                    text_parts.append(f"[Page {idx + 1}] {page_text}\n")
                return "".join(text_parts)
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
    
    def _extract_snippet(self, full_text: str, query: str, window: int = 120) -> Tuple[str, Optional[int]]:
        """Return a contextual text snippet containing *query* and, if present,
        the PDF page number extracted from the ``[Page X]`` markers added at
        indexing time.
        
        Parameters
        ----------
        full_text: str
            The entire body text previously extracted from the document.
        query: str
            The user search query (case-insensitive).
        window: int, default 120
            Number of characters to include **before** and **after** the match.
        
        Returns
        -------
        snippet: str
            A shortened snippet with surrounding context. Newlines are replaced
            with spaces for safe inline rendering.
        page: Optional[int]
            The 1-based page number when detected, otherwise ``None``.
        """
        try:
            if not full_text:
                return "", None

            lower_full = full_text.lower()
            lower_query = query.lower()
            idx = lower_full.find(lower_query)
            if idx == -1:
                return "", None

            start = max(0, idx - window)
            end = min(len(full_text), idx + len(query) + window)
            raw_snippet = full_text[start:end].replace("\n", " ")
            # Attempt to find last "[Page X]" before the match
            page_match = None
            page_marker_re = re.compile(r"\[Page (\d+)\]", re.IGNORECASE)
            for m in page_marker_re.finditer(full_text[:idx]):
                page_match = int(m.group(1))
            return raw_snippet.strip(), page_match
        except Exception as exc:
            logger.error("Failed to build snippet: %s", exc)
            return "", None
    
    def _load_last_index_time(self):
        """Load the last full index time from database."""
        if self._index_time_loaded:
            return
            
        try:
            # Get the most recent last_indexed time
            result = db.session.query(func.max(SearchIndex.last_indexed)).scalar()
            self.last_full_index = result
            self._index_time_loaded = True
            logger.info(f"Last full index time: {self.last_full_index}")
        except Exception as e:
            logger.error(f"Error loading last index time: {e}")
            self.last_full_index = None
            self._index_time_loaded = True
    
    def needs_full_rebuild(self) -> bool:
        """Check if a full index rebuild is needed."""
        # Load the last index time if not already loaded
        self._load_last_index_time()
        
        if self.last_full_index is None:
            return True
        
        # Check if any content has been updated since last index
        try:
            # Check KB articles
            kb_updated = db.session.query(KBArticle).filter(
                KBArticle.updated_at > self.last_full_index
            ).first() is not None
            
            # Check outages
            outages_updated = db.session.query(Outage).filter(
                Outage.updated_at > self.last_full_index
            ).first() is not None
            
            # Check users
            users_updated = db.session.query(User).filter(
                User.last_seen > self.last_full_index
            ).first() is not None
            
            # Check documents
            docs_updated = db.session.query(Document).filter(
                Document.updated_at > self.last_full_index
            ).first() is not None
            
            # Check notes
            notes_updated = db.session.query(Note).filter(
                Note.updated_at > self.last_full_index
            ).first() is not None
            
            return kb_updated or outages_updated or users_updated or docs_updated or notes_updated
            
        except Exception as e:
            logger.error(f"Error checking if rebuild needed: {e}")
            return True
    
    def initialize_index(self):
        """Initialize the search index - only rebuild if necessary."""
        try:
            logger.info("Initializing optimized search index...")
            
            if self.needs_full_rebuild():
                logger.info("Full index rebuild needed, rebuilding...")
                self.rebuild_index()
            else:
                logger.info("Index is up to date, no rebuild needed")
            
            # Update last index time
            self.last_full_index = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error initializing search index: {e}")
            raise
    
    def rebuild_index(self):
        """Rebuild the entire search index."""
        try:
            logger.info("Starting full search index rebuild...")
            
            # Clear existing index
            db.session.query(SearchIndex).delete()
            db.session.commit()
            
            # Index all content types
            self._index_kb_articles()
            self._index_outages()
            self._index_users()
            self._index_offices()
            self._index_workstations()
            self._index_documents()
            self._index_notes()
            
            # Update last index time
            self.last_full_index = datetime.utcnow()
            
            logger.info("Search index rebuilt successfully")
        except Exception as e:
            logger.error(f"Error rebuilding search index: {e}")
            db.session.rollback()
            raise
    
    def _index_kb_articles(self):
        """Index all knowledge base articles."""
        try:
            articles = KBArticle.query.all()
            
            for article in articles:
                # Get document text if file exists
                content = article.content or ""
                url = f"/kb/{article.id}"
                if article.file_path and os.path.exists(article.file_path):
                    file_ext = Path(article.file_path).suffix.lower()
                    if file_ext == ".pdf":
                        # Serve PDF directly from static/docs or wherever it's stored
                        filename = os.path.basename(article.file_path)
                        url = f"/static/docs/{filename}"
                    elif file_ext in self.processors:
                        content += "\n" + self.processors[file_ext](article.file_path)
                
                searchable_text = f"{article.title} {content} {article.description or ''} {' '.join(article.tags.split(',') if article.tags else [])}"
                
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
                    url=url,
                    section="Knowledge Base",
                    created_at=article.created_at,
                    updated_at=article.updated_at,
                    priority=3.0,  # High priority for KB articles
                    views=article.views or 0,
                    searchable_text=searchable_text,
                    last_indexed=datetime.utcnow()
                )
                db.session.add(search_index)
            
            db.session.commit()
            logger.info(f"Indexed {len(articles)} KB articles")
        except Exception as e:
            logger.error(f"Error indexing KB articles: {e}")
            db.session.rollback()
            raise
    
    def _index_outages(self):
        """Index all outage posts."""
        try:
            outages = Outage.query.all()
            
            for outage in outages:
                searchable_text = f"{outage.title} {outage.description} {outage.affected_systems or ''} {outage.ticket_id or ''}"
                
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
            logger.info(f"Indexed {len(outages)} outages")
        except Exception as e:
            logger.error(f"Error indexing outages: {e}")
            db.session.rollback()
            raise
    
    def _index_users(self):
        """Index all user profiles."""
        try:
            users = User.query.filter_by(is_active=True).all()
            
            for user in users:
                searchable_text = f"{user.username} {user.email} {user.role}"
                
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
            logger.info(f"Indexed {len(users)} users")
        except Exception as e:
            logger.error(f"Error indexing users: {e}")
            db.session.rollback()
            raise
    
    def _index_offices(self):
        """Index all office information."""
        try:
            if offices_df is not None and len(offices_df) > 0:
                for _, office in offices_df.iterrows():
                    searchable_text = f"{office.get('Internal Name', '')} {office.get('Location', '')} {office.get('Mnemonic', '')} {office.get('Number', '')} {office.get('Operations Manager', '')}"
                    # Use /unified?q=<office name or number> for lookup
                    office_query = office.get('Internal Name', '') or office.get('Number', '')
                    url = f"/unified?q={office_query}"
                    search_index = SearchIndex(
                        content_id=f"office_{office.get('Number', '')}",
                        content_type="office",
                        title=office.get('Internal Name', ''),
                        content=f"Location: {office.get('Location', '')}\nPhone: {office.get('Phone', '')}\nManager: {office.get('Operations Manager', '')}",
                        description=f"Office location: {office.get('Location', '')}",
                        author="System",
                        tags=f"office,{office.get('Mnemonic', '')}",
                        category="Offices",
                        status="active",
                        url=url,
                        section="Offices",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        priority=2.0,
                        views=0,
                        searchable_text=searchable_text,
                        last_indexed=datetime.utcnow()
                    )
                    db.session.add(search_index)
                
                db.session.commit()
                logger.info(f"Indexed {len(offices_df)} offices")
        except Exception as e:
            logger.error(f"Error indexing offices: {e}")
            db.session.rollback()
            raise
    
    def _index_workstations(self):
        """Index all workstation information."""
        try:
            devices = load_devices_cache()
            if devices is not None and len(devices) > 0:
                # Convert list to DataFrame if needed
                if not hasattr(devices, 'iterrows'):
                    devices = pd.DataFrame(devices)
                
                for _, device in devices.iterrows():
                    searchable_text = f"{device.get('Computer Name', '')} {device.get('User Name', '')} {device.get('Office', '')} {device.get('IP Address', '')}"
                    # Use /unified?q=<computer name> for lookup
                    ws_query = device.get('Computer Name', '')
                    url = f"/unified?q={ws_query}"
                    search_index = SearchIndex(
                        content_id=f"workstation_{device.get('Computer Name', '')}",
                        content_type="workstation",
                        title=device.get('Computer Name', ''),
                        content=f"User: {device.get('User Name', '')}\nOffice: {device.get('Office', '')}\nIP: {device.get('IP Address', '')}",
                        description=f"Workstation for {device.get('User Name', '')}",
                        author="System",
                        tags=f"workstation,{device.get('Office', '')}",
                        category="Workstations",
                        status="active",
                        url=url,
                        section="Workstations",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        priority=1.5,
                        views=0,
                        searchable_text=searchable_text,
                        last_indexed=datetime.utcnow()
                    )
                    db.session.add(search_index)
                
                db.session.commit()
                logger.info(f"Indexed {len(devices)} workstations")
        except Exception as e:
            logger.error(f"Error indexing workstations: {e}")
            db.session.rollback()
            raise
    
    def _index_documents(self):
        """Index all uploaded documents."""
        try:
            documents = Document.query.all()
            
            for doc in documents:
                content = doc.content or ""
                if doc.file_path and os.path.exists(doc.file_path):
                    file_ext = Path(doc.file_path).suffix.lower()
                    if file_ext in self.processors:
                        content += "\n" + self.processors[file_ext](doc.file_path)
                
                searchable_text = f"{doc.title} {content} {doc.description or ''}"
                
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
            logger.info(f"Indexed {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            db.session.rollback()
            raise
    
    def _index_notes(self):
        """Index all public user notes."""
        try:
            # Only index public notes
            notes = Note.query.filter_by(is_public=True).all()
            
            for note in notes:
                # Extract plain text from Quill content for better search
                plain_text = extract_plain_text_from_quill(note.content)
                searchable_text = f"{note.title} {plain_text} {note.tags or ''}"
                
                # Create a clean description from plain text (not raw JSON)
                description = plain_text[:200] + "..." if len(plain_text) > 200 else plain_text
                
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
            logger.info(f"Indexed {len(notes)} public notes")
        except Exception as e:
            logger.error(f"Error indexing notes: {e}")
            db.session.rollback()
            raise
    
    def search(self, query: str, limit: int = 20, content_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search across all indexed content using database queries with intelligent pattern recognition."""
        try:
            if not query.strip():
                return []
            
            # Check for special patterns and enhance search accordingly
            enhanced_query = self._enhance_query_for_patterns(query)
            search_terms = enhanced_query.lower().split()
            
            # Create SQL LIKE conditions for each search term
            search_conditions = []
            for term in search_terms:
                term_condition = or_(
                    SearchIndex.title.ilike(f'%{term}%'),
                    SearchIndex.content.ilike(f'%{term}%'),
                    SearchIndex.description.ilike(f'%{term}%'),
                    SearchIndex.searchable_text.ilike(f'%{term}%'),
                    SearchIndex.tags.ilike(f'%{term}%'),
                    SearchIndex.author.ilike(f'%{term}%')
                )
                search_conditions.append(term_condition)
            
            # Combine all conditions with AND (all terms must match)
            final_condition = and_(*search_conditions)
            
            # Add content type filter if specified
            if content_types:
                final_condition = and_(final_condition, SearchIndex.content_type.in_(content_types))
            
            # Retrieve a larger candidate set first so we can compute a precise
            # relevance score in Python and then return the **top *limit***
            # matches.  We fetch ``limit * 5`` rows (falling back to 100 max)
            # which keeps the query performant even on large tables while
            # giving the ranking algorithm enough data to produce accurate
            # results.

            candidate_limit = min(limit * 5, 100)

            candidates = (
                db.session.query(SearchIndex)
                .filter(final_condition)
                .order_by(
                    SearchIndex.priority.desc(),
                    SearchIndex.views.desc()
                )
                .limit(candidate_limit)
                .all()
            )
            
            # Format results
            formatted_results = []
            for result in candidates:
                # Calculate relevance score based on term frequency
                score = self._calculate_relevance_score(result, search_terms)
                
                # Decide which text to use for preview/description
                description_text = result.description or ""
                highlighted_description = self._highlight_text(description_text, query)

                # If the default description is empty or does not contain the
                # query, fall back to generating a snippet from the *content*
                # field (this is especially useful for PDFs where the match may
                # live deep inside the document body).
                if (not description_text or query.lower() not in description_text.lower()) and result.content:
                    snippet, page_no = self._extract_snippet(result.content, query)
                    if snippet:
                        description_text = (f"Page {page_no}: {snippet}" if page_no else snippet)
                        highlighted_description = self._highlight_text(description_text, query)

                # Highlight title AFTER we potentially changed it (rare)
                highlighted_title = self._highlight_text(result.title, query)
                
                formatted_results.append({
                    'id': result.content_id,
                    'content_type': result.content_type,
                    'title': result.title,
                    'highlighted_title': highlighted_title,
                    'description': description_text,
                    'highlighted_description': highlighted_description,
                    'author': result.author,
                    'tags': result.tags,
                    'category': result.category,
                    'status': result.status,
                    'url': result.url,
                    'section': result.section,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'updated_at': result.updated_at.isoformat() if result.updated_at else None,
                    'priority': result.priority,
                    'views': result.views,
                    'score': score
                })
            
            # Sort by computed *score* (highest first) and then by created date
            formatted_results.sort(key=lambda r: r.get('score', 0), reverse=True)

            # Return only the requested amount
            return formatted_results[:limit]
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _calculate_relevance_score(self, result: SearchIndex, search_terms: List[str]) -> float:
        """Calculate relevance score for a search result."""
        score = 0.0
        
        # Base score from priority
        score += result.priority
        
        # Term frequency scoring
        text_to_search = f"{result.title} {result.content} {result.description or ''} {result.searchable_text}"
        text_lower = text_to_search.lower()
        
        for term in search_terms:
            # Count occurrences
            term_count = text_lower.count(term)
            score += term_count * 0.1
            
            # Bonus for exact matches in title
            if term in result.title.lower():
                score += 2.0
            
            # Bonus for matches in tags
            if result.tags and term in result.tags.lower():
                score += 1.0
        
        return score
    
    def _highlight_text(self, text: str, query: str) -> str:
        """Highlight search terms in text."""
        if not text or not query:
            return text
        
        # Split query into terms
        terms = query.lower().split()
        highlighted_text = text
        
        # Highlight each term
        for term in terms:
            # Use case-insensitive replacement
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted_text = pattern.sub(
                f'<mark>{term}</mark>',
                highlighted_text
            )
        
        return highlighted_text
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query with intelligent pattern recognition."""
        try:
            if not query.strip():
                return []
            
            suggestions = []
            
            # Check for special patterns and add intelligent suggestions
            pattern_suggestions = self._get_pattern_suggestions(query)
            suggestions.extend(pattern_suggestions)
            
            # Search for similar titles and content
            db_suggestions = db.session.query(SearchIndex.title).filter(
                or_(
                    SearchIndex.title.ilike(f'%{query}%'),
                    SearchIndex.searchable_text.ilike(f'%{query}%')
                )
            ).distinct().limit(limit - len(suggestions)).all()
            
            suggestions.extend([s[0] for s in db_suggestions])
            
            return suggestions[:limit]
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
    
    def _enhance_query_for_patterns(self, query: str) -> str:
        """Enhance search query based on detected patterns."""
        enhanced_terms = []
        
        # Check for clock ID pattern (5-digit numbers)
        if re.match(r'^\d{5}$', query):
            enhanced_terms.extend([
                query,  # Original query
                f"Clock ID {query}",
                f"Employee {query}",
                f"User {query}"
            ])
        
        # Check for IP address pattern
        elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', query):
            enhanced_terms.extend([
                query,  # Original query
                f"IP {query}",
                f"Network {query}",
                f"Device {query}"
            ])
        
        # Check for MAC address pattern
        elif re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', query):
            enhanced_terms.extend([
                query,  # Original query
                f"MAC {query}",
                f"Device {query}",
                f"Hardware {query}"
            ])
        
        # Check for ticket number pattern
        elif re.match(r'^[A-Z]{2,4}-\d{4,6}$', query.upper()):
            enhanced_terms.extend([
                query,  # Original query
                f"Ticket {query}",
                f"Case {query}",
                f"Support {query}"
            ])
        
        # Check for email pattern
        elif '@' in query:
            enhanced_terms.extend([
                query,  # Original query
                f"Email {query}",
                f"Contact {query}",
                f"User {query.split('@')[0]}"
            ])
        
        # Check for phone number pattern
        elif re.match(r'^[\d\s\-\(\)\+]+$', query) and len(query.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')) >= 10:
            enhanced_terms.extend([
                query,  # Original query
                f"Phone {query}",
                f"Contact {query}",
                f"Call {query}"
            ])
        
        # Default case - return original query
        if not enhanced_terms:
            enhanced_terms = [query]
        
        return ' '.join(enhanced_terms)
    
    def _get_pattern_suggestions(self, query: str) -> List[str]:
        """Get intelligent suggestions based on query patterns."""
        suggestions = []
        
        # Clock ID suggestions (when typing numbers)
        if re.match(r'^\d{1,4}$', query):
            suggestions.append(f"Search for Clock ID {query}")
            suggestions.append(f"Find employee {query}")
        
        # IP address suggestions
        elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}$', query):
            suggestions.append(f"Search for IP {query}")
            suggestions.append(f"Find network {query}")
        
        # MAC address suggestions
        elif re.match(r'^([0-9A-Fa-f]{2}[:-]){1,5}([0-9A-Fa-f]{2})?$', query):
            suggestions.append(f"Search for MAC {query}")
            suggestions.append(f"Find device {query}")
        
        # Ticket number suggestions
        elif re.match(r'^[A-Z]{2,4}-\d{1,5}$', query.upper()):
            suggestions.append(f"Search for ticket {query}")
            suggestions.append(f"Find case {query}")
        
        # Email suggestions
        elif '@' in query and '.' in query.split('@')[1]:
            suggestions.append(f"Search for email {query}")
            suggestions.append(f"Find contact {query}")
        
        # Phone number suggestions
        elif re.match(r'^[\d\s\-\(\)\+]+$', query) and len(query.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')) >= 7:
            suggestions.append(f"Search for phone {query}")
            suggestions.append(f"Find contact {query}")
        
        # General suggestions for short queries
        elif len(query) < 3:
            suggestions.extend([
                "Search users",
                "Search offices", 
                "Search workstations",
                "Search knowledge base",
                "Search notes",
                "Check outages"
            ])
        
        return suggestions
    
    def index_single_item(self, content_type: str, item_id: int):
        """Index a single item by content type and ID."""
        try:
            # Delete existing entry
            db.session.query(SearchIndex).filter(
                SearchIndex.content_type == content_type,
                SearchIndex.content_id == f"{content_type}_{item_id}"
            ).delete()
            
            # Index based on content type
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
            
            db.session.commit()
        except Exception as e:
            logger.error(f"Error indexing single item {content_type}:{item_id}: {e}")
            db.session.rollback()
    
    def _index_single_kb_article(self, article: KBArticle):
        """Index a single KB article."""
        content = article.content or ""
        url = f"/kb/{article.id}"
        if article.file_path and os.path.exists(article.file_path):
            file_ext = Path(article.file_path).suffix.lower()
            if file_ext == ".pdf":
                # Serve PDF directly from static/docs or wherever it's stored
                filename = os.path.basename(article.file_path)
                url = f"/static/docs/{filename}"
            elif file_ext in self.processors:
                content += "\n" + self.processors[file_ext](article.file_path)
        
        searchable_text = f"{article.title} {content} {article.description or ''} {' '.join(article.tags.split(',') if article.tags else [])}"
        
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
            url=url,
            section="Knowledge Base",
            created_at=article.created_at,
            updated_at=article.updated_at,
            priority=3.0,
            views=article.views or 0,
            searchable_text=searchable_text,
            last_indexed=datetime.utcnow()
        )
        db.session.add(search_index)
    
    def _index_single_outage(self, outage: Outage):
        """Index a single outage."""
        searchable_text = f"{outage.title} {outage.description} {outage.affected_systems or ''} {outage.ticket_id or ''}"
        
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
    
    def _index_single_user(self, user: User):
        """Index a single user."""
        searchable_text = f"{user.username} {user.email} {user.role}"
        
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
    
    def _index_single_document(self, document: Document):
        """Index a single document."""
        content = document.content or ""
        if document.file_path and os.path.exists(document.file_path):
            file_ext = Path(document.file_path).suffix.lower()
            if file_ext in self.processors:
                content += "\n" + self.processors[file_ext](document.file_path)
        
        searchable_text = f"{document.title} {content} {document.description or ''}"
        
        search_index = SearchIndex(
            content_id=f"doc_{document.id}",
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
            searchable_text=searchable_text,
            last_indexed=datetime.utcnow()
        )
        db.session.add(search_index)
    
    def _index_single_note(self, note: Note):
        """Index a single note."""
        # Only index if the note is public
        if not note.is_public:
            logger.info(f"Skipping private note {note.id} from search index")
            return
        
        # Extract plain text from Quill content for better search
        plain_text = extract_plain_text_from_quill(note.content)
        searchable_text = f"{note.title} {plain_text} {note.tags or ''}"
        
        # Create a clean description from plain text (not raw JSON)
        description = plain_text[:200] + "..." if len(plain_text) > 200 else plain_text
        
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
    
    def delete_item(self, content_type: str, item_id: int):
        """Delete an item from the search index."""
        try:
            db.session.query(SearchIndex).filter(
                SearchIndex.content_type == content_type,
                SearchIndex.content_id == f"{content_type}_{item_id}"
            ).delete()
            db.session.commit()
            logger.info(f"Deleted {content_type}:{item_id} from search index")
        except Exception as e:
            logger.error(f"Error deleting from search index: {e}")
            db.session.rollback()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics."""
        try:
            total_documents = db.session.query(SearchIndex).count()
            
            # Count by content type
            content_type_counts = {}
            for content_type in ['kb_article', 'outage', 'user', 'office', 'workstation', 'document', 'note']:
                count = db.session.query(SearchIndex).filter(
                    SearchIndex.content_type == content_type
                ).count()
                content_type_counts[content_type] = count
            
            return {
                'total_documents': total_documents,
                'content_type_counts': content_type_counts,
                'last_full_index': self.last_full_index.isoformat() if self.last_full_index else None
            }
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {}
    
    def sync_notes_index(self) -> Dict[str, Any]:
        """Sync the notes search index with the database to ensure consistency."""
        try:
            logger.info("Starting notes index sync...")
            
            # Get all public notes from database
            public_notes = Note.query.filter_by(is_public=True).all()
            public_note_ids = {note.id for note in public_notes}
            
            # Get all indexed notes
            indexed_notes = db.session.query(SearchIndex).filter(
                SearchIndex.content_type == 'note'
            ).all()
            indexed_note_ids = {int(note.content_id.replace('note_', '')) for note in indexed_notes}
            
            # Find notes that should be indexed but aren't
            notes_to_add = public_note_ids - indexed_note_ids
            
            # Find notes that are indexed but shouldn't be (private or deleted)
            notes_to_remove = indexed_note_ids - public_note_ids
            
            logger.info(f"Found {len(notes_to_add)} notes to add to index")
            logger.info(f"Found {len(notes_to_remove)} notes to remove from index")
            
            # Add missing notes
            for note_id in notes_to_add:
                note = Note.query.get(note_id)
                if note and note.is_public:
                    self._index_single_note(note)
                    logger.info(f"Added note {note_id} to search index")
            
            # Remove notes that shouldn't be indexed
            for note_id in notes_to_remove:
                self.delete_item('note', note_id)
                logger.info(f"Removed note {note_id} from search index")
            
            db.session.commit()
            
            sync_stats = {
                'notes_added': len(notes_to_add),
                'notes_removed': len(notes_to_remove),
                'total_public_notes': len(public_notes),
                'total_indexed_notes': len(indexed_notes) + len(notes_to_add) - len(notes_to_remove)
            }
            
            logger.info(f"Notes index sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            logger.error(f"Error syncing notes index: {e}")
            db.session.rollback()
            return {'error': str(e)}

# Global instance
optimized_search_engine = OptimizedSearchEngine() 