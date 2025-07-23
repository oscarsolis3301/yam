import logging
import sqlite3
from app import db
from app.config import Config
from app.utils.helpers import (
    verify_file_exists as helpers_verify_file_exists,
    extract_text_from_document as helpers_extract_text_from_document,
    get_document_text as helpers_get_document_text,
    allowed_file as _allowed_file_helper
)
from . import bp

logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row  # Allow access to columns by name
    return conn

def allowed_file(filename):
    return _allowed_file_helper(filename)

def verify_file_exists(file_path: str) -> bool:
    """Delegate to *app.utils.helpers.verify_file_exists* to retain legacy API."""
    return helpers_verify_file_exists(file_path)

def extract_text_from_document(file_path: str) -> str:
    """Delegate to *app.utils.helpers.extract_text_from_document*."""
    return helpers_extract_text_from_document(file_path)

def get_document_text(article):
    """Delegate to *app.utils.helpers.get_document_text*."""
    return helpers_get_document_text(article) 