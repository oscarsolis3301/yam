import os
import logging
from PyPDF2 import PdfReader
import docx
import pytesseract
from PIL import Image
import io
import re

logger = logging.getLogger('spark')

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        text = ""
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                # Collapse multiple consecutive blank lines while preserving single paragraph breaks
                page_text = re.sub(r"\n{3,}", "\n\n", page_text)
                text += page_text + "\n"

        # Final cleanup across all pages – ensure no overly large gaps remain
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        # Remove excessive blank lines caused by images/tables
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        return None

def extract_text_from_image(file_path):
    """Extract text from an image using OCR"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        return None

def extract_text(file_path):
    """Extract text from various file types"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return extract_text_from_docx(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return extract_text_from_image(file_path)
        elif file_ext == '.txt':
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as read_err:
                logger.error(f"Error reading TXT file {file_path}: {read_err}")
                return None
        else:
            logger.error(f"Unsupported file type: {file_ext}")
            return None
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return None

def get_file_metadata(file_path):
    """Get metadata from a file"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        file_stats = os.stat(file_path)
        return {
            'size': file_stats.st_size,
            'created': file_stats.st_ctime,
            'modified': file_stats.st_mtime,
            'extension': os.path.splitext(file_path)[1].lower()
        }
    except Exception as e:
        logger.error(f"Error getting file metadata: {str(e)}")
        return None 