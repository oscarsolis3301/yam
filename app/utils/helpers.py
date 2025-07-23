import os
import json
import base64
import random
import string
import logging
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from PIL import Image
import fitz  # PyMuPDF
import pytesseract
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer
from transformers import BlipProcessor, BlipForConditionalGeneration
from gpt4all import GPT4All
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logger = logging.getLogger('spark')

# Initialize models (only once)
model = None
embedder = None
processor = None
caption_model = None
asr_model = None

def init_models():
    """Initialize ML models - call this once at startup"""
    global model, embedder, processor, caption_model, asr_model
    
    # Initialize GPT4All model
    try:
        from app.config import Config
        model = GPT4All(Config.MODEL_ID)
        logger.info("Loaded GPT4All model")
    except Exception as e:
        logger.error(f"Error initializing GPT4All model: {e}")
        model = None
    
    # Initialize embedder
    try:
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded embedder model")
    except Exception as e:
        logger.error(f"Error initializing embedder: {e}")
        embedder = None
    
    # Initialize image captioning
    try:
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        logger.info("Loaded image captioning model")
    except Exception as e:
        logger.error(f"Error initializing image captioning: {e}")
        processor = None
        caption_model = None
    
    # Initialize ASR model
    try:
        import whisper
        asr_model = whisper.load_model("base")
        logger.info("Loaded Whisper ASR model")
    except ImportError:
        logger.warning("whisper module not found; real-time transcription disabled.")
        asr_model = None
    except Exception as e:
        logger.warning(f"Failed to load Whisper model ({e}); real-time transcription disabled.")
        asr_model = None
    
    return model, embedder, processor, caption_model, asr_model

def extract_text(path):
    """Extract text from PDF, image, or txt files"""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.pdf':
            doc = fitz.open(path)
            text = "\n".join(page.get_text("text") for page in doc).strip()
            if not text:
                text = ""
                for i in range(len(doc)):
                    pix = doc.load_page(i).get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    try:
                        text += pytesseract.image_to_string(img) + "\n"
                    except pytesseract.pytesseract.TesseractNotFoundError:
                        logger.warning("Tesseract not found; skipping OCR for PDF.")
                        break
            return text

        elif ext in ['.png', '.jpg', '.jpeg']:
            img = Image.open(path)
            try:
                ocr_text = pytesseract.image_to_string(img).strip()
            except pytesseract.pytesseract.TesseractNotFoundError:
                ocr_text = ''
                logger.warning("Tesseract not found; skipping image OCR.")
            
            if processor and caption_model:
                inputs = processor(images=img.convert("RGB"), return_tensors="pt")
                out = caption_model.generate(**inputs)
                caption = processor.decode(out[0], skip_special_tokens=True)
                if ocr_text:
                    return f"Image description: {caption}\nDetected text: {ocr_text}"
                return f"Image description: {caption}"
            return ocr_text

        elif ext == '.txt':
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        else:
            return ''

    except Exception as e:
        logger.error(f"extract_text error: {e}")
        return ''

def extract_pdf_details(pdf_path):
    """Extract PDF content as images for display"""
    try:
        doc = fitz.open(pdf_path)
        content = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
            img_data = pix.tobytes("png")
            img_b64 = base64.b64encode(img_data).decode()
            content.append(f'<div class="pdf-page"><img src="data:image/png;base64,{img_b64}" style="width:100%;margin:0;padding:0;"></div>')
            del page
            del pix
        
        metadata = doc.metadata
        doc.close()
        
        return ''.join(content), metadata
    except Exception as e:
        logger.error(f"Failed to extract PDF details from {pdf_path}: {e}")
        return "", {}

def summarize_text(text_block, max_tokens=200):
    """Summarize text using the local model"""
    if not model:
        return "[Model not available]"
    
    text_block = text_block.strip()
    if not text_block:
        return "[No text to summarize]"

    prompt = (
        "Please simplify the following information for someone who has never heard or seen this. "
        "I want you to sound as human as possible. " + text_block
    )
    
    try:
        with model.chat_session():
            return model.generate(prompt, max_tokens=max_tokens)
    except Exception as e:
        logger.error(f"Error in summarize_text: {e}")
        return "[Error generating summary]"

def answer_query(query):
    """Answer a query using the model and context"""
    if not model:
        return "Model not available. Please try again later."
    
    try:
        # Import here to avoid circular imports
        from app.models import KBArticle
        
        kb_articles = KBArticle.query.all()
        kb_texts = [a.content for a in kb_articles]
        
        docs_dir = './docs'
        doc_texts = []
        if os.path.exists(docs_dir):
            import glob
            for pdf_file in glob.glob(os.path.join(docs_dir, '*.pdf')):
                text, _ = extract_pdf_details(pdf_file)
                doc_texts.append(text)
        
        all_context = kb_texts + doc_texts
        context = '\n\n'.join(all_context)
        
        # Limit context size
        max_context_length = 2000
        if len(context) > max_context_length:
            context = context[:max_context_length] + "..."
        
        prompt = f"""Based on the following context, please answer the question. If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {query}

Answer:"""
        
        with model.chat_session():
            response = model.generate(prompt, max_tokens=500)
        return response
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "I apologize, but I encountered an error while processing your request."

def retrieve_similar_questions(query, top_k=3):
    """Retrieve similar past questions"""
    if not embedder:
        return []
    
    from log import get_all_past_questions
    past = get_all_past_questions()[:100]
    questions = [q for q, _ in past]
    if not questions:
        return []
    
    emb = embedder.encode(questions)
    qv = embedder.encode([query])[0]
    
    sims = cosine_similarity([qv], emb)[0]
    scored_sims = [(questions[i], past[i][1], sims[i]) for i in range(len(questions))]
    scored_sims.sort(key=lambda x: x[2], reverse=True)
    return [f"Q: {q}\nA: {a}" for q, a, _ in scored_sims[:top_k]]

def safe_commit(session, max_retries=5, delay=1):
    """Safely commit database changes with retry logic"""
    import time
    from sqlalchemy.exc import OperationalError
    
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

def allowed_file(filename):
    """Check if file extension is allowed"""
    from app.config import Config
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def generate_short_code():
    """Generate a unique short code"""
    while True:
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        # Check uniqueness in DB
        from app.models import SharedLink
        if not SharedLink.query.filter_by(short_code=code).first():
            return code

def get_db_connection():
    """Get SQLite database connection"""
    from app.config import Config
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_cache_table():
    """Create api_cache table if it doesn't exist"""
    from app.config import Config
    conn = sqlite3.connect(Config.QUESTIONS_DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_cache (
      query      TEXT PRIMARY KEY,
      raw_json   TEXT,
      summary    TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def cache_storage(device_name, data):
    """Cache device storage data"""
    from app.config import Config
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    path = os.path.join(Config.CACHE_DIR, f"storage_{device_name}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            "cached_at": datetime.utcnow().isoformat(),
            "data": data
        }, f)

def load_cached_storage(device_name):
    """Load cached device storage data"""
    from app.config import Config
    path = os.path.join(Config.CACHE_DIR, f"storage_{device_name}.json")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def verify_file_exists(file_path):
    """Verify if a file exists in the docs directory"""
    if not file_path:
        return False
    
    # Get the correct path to the docs directory
    # The server runs from YAM/ but the docs are in app/static/docs
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    docs_root = os.path.join(current_dir, 'app', 'static', 'docs')
    
    # First try direct path
    direct_path = os.path.join(docs_root, file_path)
    if os.path.exists(direct_path):
        return True
    
    # If not found, recursively search
    if os.path.exists(docs_root):
        for root, dirs, files in os.walk(docs_root):
            if os.path.basename(file_path) in files:
                return True
    
    return False

def extract_text_from_document(file_path):
    """Extract text from PDF, Word, or plain-text documents.

    This helper consolidates basic document-parsing logic so that other
    parts of the app (e.g. unified search, KB API) can obtain a plain
    text representation of a file regardless of its original format.
    The implementation is intentionally kept lightweight and free of
    heavy external dependencies so it can run in constrained
    environments.
    """
    if not file_path:
        return ""

    try:
        # Normalise and work with absolute paths for safety
        abs_path = os.path.abspath(file_path)
        lower = abs_path.lower()

        if lower.endswith('.pdf'):
            import PyPDF2
            text = ""
            with open(abs_path, 'rb') as fh:
                pdf_reader = PyPDF2.PdfReader(fh)
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text() or ""
                    except Exception:
                        page_text = ""
                    text += page_text + "\n"
            return text

        elif lower.endswith(('.doc', '.docx')):
            import docx
            try:
                doc_obj = docx.Document(abs_path)
                return "\n".join(paragraph.text for paragraph in doc_obj.paragraphs)
            except Exception:
                return ""

        elif lower.endswith('.txt'):
            try:
                with open(abs_path, 'r', encoding='utf-8') as fh:
                    return fh.read()
            except Exception:
                return ""

        else:
            # Unsupported extension – return empty string to avoid raising.
            return ""

    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def get_document_text(article):
    """Return plain-text content for a KB *article* dict.

    If the article already contains inline `content`, it is used directly
    (this covers HTML-based articles created inside the app). If the
    article references a `file_path`, the helper will attempt to locate
    the file inside the `static/docs` directory tree and extract text
    via `extract_text_from_document`. If neither is available, an empty
    string is returned.
    """
    # Guard against non-dicts or missing keys
    if not isinstance(article, dict):
        return ""

    # If the article has an in-DB content field, prefer it.
    if article.get('content'):
        return article['content']

    file_path_attr = article.get('file_path')
    if not file_path_attr:
        return ""

    # Construct full path to the correct docs directory
    # The server runs from YAM/ but the docs are in app/static/docs
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    docs_root = os.path.join(current_dir, 'app', 'static', 'docs')
    candidate = os.path.join(docs_root, file_path_attr)

    if os.path.exists(candidate):
        return extract_text_from_document(candidate)

    # Fallback: search recursively in docs_root (handles legacy uploads)
    if os.path.exists(docs_root):
        for root, _dirs, files in os.walk(docs_root):
            if os.path.basename(file_path_attr) in files:
                return extract_text_from_document(os.path.join(root, os.path.basename(file_path_attr)))

    # If we reach this point, the file is missing – return empty string.
    return "" 