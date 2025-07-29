from __future__ import annotations

"""Utility helpers for bulk-importing PDF documents into the Knowledge-Base.

This module centralises the *import_docs_folder* implementation so it can be
re-used by background jobs, blueprints and the application bootstrap phase
without introducing circular-import issues.
"""

from pathlib import Path
import logging
import os
import time
import re
import hashlib
import json
from typing import Dict, Set, Tuple, Optional
from datetime import datetime

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import KBArticle, User
from app.blueprints.utils.db import safe_commit
from app.utils.helpers import extract_pdf_details  # already re-exported in spark utils
from app.utils.cache import _articles_cache_lock, _articles_cache  # shared cache
from app.utils.ai_helpers import store_qa, ensure_chat_qa_table  # Auto-FAQ generation

logger = logging.getLogger("spark")

__all__ = ["import_docs_folder", "import_docs_folder_startup", "check_for_new_documents"]


# In-memory lock file name (relative to *current_app.root_path*) used to prevent
# concurrent import runs. Equivalent behaviour to the previous implementation
# in *app.spark*.
_LOCK_FILENAME = "import_docs.lock"

# File to track import state and file hashes
_IMPORT_STATE_FILE = "kb_import_state.json"

# Global flag to track if startup import has completed
_startup_import_completed = False


def _get_import_state_file(app_root_path: str) -> str:
    """Get the path to the import state file."""
    return os.path.join(app_root_path, _IMPORT_STATE_FILE)


def _load_import_state(app_root_path: str) -> Dict:
    """Load the import state from file."""
    state_file = _get_import_state_file(app_root_path)
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load import state: {e}")
    return {"file_hashes": {}, "last_import": 0, "startup_completed": False}


def _save_import_state(app_root_path: str, state: Dict) -> None:
    """Save the import state to file."""
    state_file = _get_import_state_file(app_root_path)
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save import state: {e}")


def _calculate_file_hash(file_path: str) -> str:
    """Calculate a hash for a file to detect changes."""
    try:
        stat = os.stat(file_path)
        # Use modification time and file size as a simple hash
        return f"{stat.st_mtime}_{stat.st_size}"
    except Exception:
        return ""


def _get_all_document_files(docs_directories: list) -> Set[Tuple[str, str]]:
    """Get all document files from all docs directories with their hashes."""
    files = set()
    supported_ext = {".pdf", ".docx", ".txt"}
    
    for dir_type, docs_dir in docs_directories:
        if not os.path.exists(docs_dir):
            continue
            
        for root, _, file_list in os.walk(docs_dir):
            for file in file_list:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_ext:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, docs_dir).replace("\\", "/")
                    prefixed_rel_path = f"{dir_type}/{rel_path}"
                    file_hash = _calculate_file_hash(abs_path)
                    files.add((prefixed_rel_path, file_hash))
    
    return files


def check_for_new_documents() -> bool:
    """Check if there are any new or modified documents that need importing.
    
    Returns:
        bool: True if new documents are detected, False otherwise
    """
    app = current_app
    app_root_path = app.root_path
    
    # Load current state
    state = _load_import_state(app_root_path)
    current_hashes = state.get("file_hashes", {})
    
    # Find all docs directories
    docs_directories = find_docs_directories(app_root_path)
    if not docs_directories:
        return False
    
    # Get current files and their hashes
    current_files = _get_all_document_files(docs_directories)
    current_file_dict = dict(current_files)
    
    # Check for new or modified files
    for file_path, file_hash in current_files:
        if file_path not in current_hashes or current_hashes[file_path] != file_hash:
            logger.info(f"[IMPORT] New or modified document detected: {file_path}")
            return True
    
    # Check for deleted files (optional - we might want to keep them in DB)
    for file_path in current_hashes:
        if file_path not in current_file_dict:
            logger.info(f"[IMPORT] Document deleted: {file_path}")
            # For now, we'll return True to trigger a re-import
            # This could be optimized to only remove the specific file from DB
            return True
    
    return False


def import_docs_folder_startup(force: bool = False) -> None:
    """Import documents during server startup only.
    
    This function should be called once during server startup to ensure
    all documents are imported before the server starts serving requests.
    
    Parameters:
        force: If True, force import even if startup import was already completed
    """
    global _startup_import_completed
    
    app = current_app
    
    # Check if startup import was already completed
    if _startup_import_completed and not force:
        logger.info("[IMPORT] Startup import already completed, skipping")
        return
    
    logger.info("[IMPORT] Starting startup document import...")
    
    # Perform the actual import
    import_docs_folder(force=force, is_startup=True)
    
    # Mark startup as completed
    _startup_import_completed = True
    
    # Update state file
    state = _load_import_state(app.root_path)
    state["startup_completed"] = True
    state["last_import"] = time.time()
    _save_import_state(app.root_path, state)
    
    logger.info("[IMPORT] Startup document import completed")


def import_docs_folder(force: bool = False, is_startup: bool = False) -> None:
    """Import documents from the docs folder into the knowledge base.

    This function scans the docs folder for new or modified documents and
    imports them into the knowledge base. It uses a lock file to prevent
    concurrent imports and tracks import state to avoid re-importing unchanged
    files.

    Parameters:
        force: If True, force import even if files haven't changed
        is_startup: If True, this is being called during server startup
    """
    app = current_app
    
    # Check if we're already importing
    lock_file = os.path.join(app.root_path, _LOCK_FILENAME)
    if os.path.exists(lock_file):
        if is_startup:
            logger.info("[IMPORT] Import already in progress, skipping startup import")
            return
        else:
            logger.warning("[IMPORT] Import already in progress, skipping")
            return
    
    # Create lock file
    try:
        with open(lock_file, 'w') as f:
            f.write(str(time.time()))
    except Exception as e:
        logger.error(f"[IMPORT] Failed to create lock file: {e}")
        return
    
    try:
        # Load import state
        state = _load_import_state(app.root_path)
        
        # Check for sentence-transformers availability
        try:
            from sentence_transformers import SentenceTransformer
            sentence_transformers_available = True
            logger.info("[IMPORT] sentence-transformers available for embeddings")
        except ImportError:
            sentence_transformers_available = False
            logger.warning("[IMPORT] sentence-transformers not available, using fallback embedder")
        
        # Get docs directory
        docs_dir = os.path.join(app.root_path, "docs")
        if not os.path.exists(docs_dir):
            logger.info(f"[IMPORT] Docs directory {docs_dir} does not exist, creating it")
            os.makedirs(docs_dir, exist_ok=True)
            state["file_hashes"] = {}
            _save_import_state(app.root_path, state)
            return
        
        # Get admin user for import
        admin_user = User.query.filter_by(is_admin=True).first()
        if not admin_user:
            logger.error("[IMPORT] No admin user found, cannot import documents")
            return
        admin_user_id = admin_user.id
        
        # Scan for documents
        logger.info("[IMPORT] Scanning for documents...")
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        for root, dirs, files in os.walk(docs_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, docs_dir)
                
                # Calculate file hash
                try:
                    file_hash = _calculate_file_hash(file_path)
                except Exception as e:
                    logger.error(f"[IMPORT] Failed to calculate hash for {file}: {e}")
                    error_count += 1
                    continue
                
                # Check if file has changed
                if not force and rel_path in state["file_hashes"] and state["file_hashes"][rel_path] == file_hash:
                    skipped_count += 1
                    continue
                
                # Check if file is already imported
                existing_article = KBArticle.query.filter_by(file_path=rel_path).first()
                if existing_article and not force:
                    # Update hash even if we don't re-import
                    state["file_hashes"][rel_path] = file_hash
                    skipped_count += 1
                    continue
                
                # Import the file
                try:
                    # Determine file type
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in ['.pdf', '.docx', '.txt', '.md']:
                        logger.info(f"[IMPORT] Skipping unsupported file type: {file}")
                        skipped_count += 1
                        continue
                    
                    # Extract text based on file type
                    if ext == '.pdf':
                        try:
                            text, _meta = extract_pdf_details(file_path)
                        except Exception as e:
                            logger.error(f"[IMPORT] Failed to extract PDF text from {file}: {e}")
                            error_count += 1
                            continue
                    elif ext == '.docx':
                        try:
                            import docx
                            doc = docx.Document(file_path)
                            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                        except Exception as e:
                            logger.error(f"[IMPORT] Failed to extract DOCX text from {file}: {e}")
                            error_count += 1
                            continue
                    else:  # .txt or .md
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                text = f.read()
                        except Exception as e:
                            logger.error(f"[IMPORT] Failed to read text file {file}: {e}")
                            error_count += 1
                            continue
                    
                    if not text.strip():
                        logger.warning(f"[IMPORT] No text extracted from {file}")
                        error_count += 1
                        continue
                    
                    # Determine category based on directory structure
                    dir_type = os.path.basename(root)
                    if root == docs_dir:
                        category = f"DOCS/{dir_type.upper()}"
                    else:
                        subfolder = os.path.relpath(root, docs_dir)
                        category = f"DOCS/{dir_type.upper()}/{subfolder}"
                    
                    # Create or update article
                    title = os.path.splitext(file)[0]
                    
                    if existing_article:
                        # Update existing article
                        existing_article.content = text
                        existing_article.updated_at = datetime.utcnow()
                        existing_article.import_status = "completed"
                        logger.info(f"[IMPORT] Updated existing article: {title}")
                    else:
                        # Create new article
                        article = KBArticle(
                            title=title,
                            content=text,
                            description=f"{ext.upper()[1:]} document in {category}",
                            category=category,
                            tags="imported",
                            status="approved",
                            is_public=True,
                            file_path=rel_path,
                            import_status="completed",
                            author_id=admin_user_id,
                        )
                        db.session.add(article)
                        logger.info(f"[IMPORT] Created new article: {title}")
                    
                    # Update file hash
                    state["file_hashes"][rel_path] = file_hash
                    imported_count += 1
                    
                    # Commit periodically
                    if imported_count % 10 == 0:
                        if not safe_commit(db.session):
                            logger.error("[IMPORT] Database commit failed")
                            db.session.rollback()
                            error_count += imported_count
                            imported_count = 0
                
                except Exception as e:
                    logger.error(f"[IMPORT] Error importing {file}: {e}")
                    error_count += 1
                    continue
        
        # Final commit
        if imported_count > 0:
            if not safe_commit(db.session):
                logger.error("[IMPORT] Final database commit failed")
                db.session.rollback()
                error_count += imported_count
                imported_count = 0
        
        # Update import state
        state["last_import"] = time.time()
        _save_import_state(app.root_path, state)
        
        # Log results
        logger.info(f"[IMPORT] Import complete. {imported_count} new/updated, {skipped_count} skipped, {error_count} errors")
        
        # Clear cache to reflect new articles
        try:
            with _articles_cache_lock:
                _articles_cache.clear()
        except Exception:
            pass
        
        # Emit socket event if not startup
        if not is_startup:
            try:
                from flask_socketio import emit
                emit('kb_update', {'type': 'refresh', 'message': f'Imported {imported_count} documents'})
            except Exception:
                pass
    
    finally:
        # Remove lock file
        try:
            os.remove(lock_file)
        except Exception:
            pass


def find_docs_directories(app_root_path):
    """Find all potential docs directories in the application"""
    docs_dirs = []
    
    # Primary docs directory: app/static/docs
    primary_docs = os.path.join(app_root_path, "app", "static", "docs")
    if os.path.exists(primary_docs):
        docs_dirs.append(("primary", primary_docs))
        logger.info(f"[IMPORT] Found primary docs directory: {primary_docs}")
    
    # Search for docs directories in YAM subdirectories
    yam_dirs = []
    for root, dirs, files in os.walk(app_root_path):
        # Look for directories named 'docs' or 'YAM'
        for dir_name in dirs:
            if dir_name.lower() == 'docs':
                docs_path = os.path.join(root, dir_name)
                if docs_path not in [d[1] for d in docs_dirs]:
                    docs_dirs.append(("subdir", docs_path))
                    logger.info(f"[IMPORT] Found docs subdirectory: {docs_path}")
            elif dir_name.upper() == 'YAM':
                yam_path = os.path.join(root, dir_name)
                yam_dirs.append(yam_path)
        
        # Limit search depth to avoid infinite recursion
        if root.count(os.sep) - app_root_path.count(os.sep) > 3:
            dirs.clear()  # Don't go deeper
    
    # Search within YAM directories for docs
    for yam_dir in yam_dirs:
        for root, dirs, files in os.walk(yam_dir):
            for dir_name in dirs:
                if dir_name.lower() == 'docs':
                    docs_path = os.path.join(root, dir_name)
                    if docs_path not in [d[1] for d in docs_dirs]:
                        docs_dirs.append(("yam", docs_path))
                        logger.info(f"[IMPORT] Found YAM docs directory: {docs_path}")
            
            # Limit search depth within YAM directories
            if root.count(os.sep) - yam_dir.count(os.sep) > 2:
                dirs.clear()
    
    return docs_dirs 