import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer
from flask import current_app
from app.config import Config
from app.models import KBArticle, Document, ChatQA, APICache
from app.log import get_user_history
from app.utils.models import get_model, get_embedder, get_processor, get_caption_model
import os
import logging
from datetime import datetime
from extensions import db

logger = logging.getLogger('spark')

# Initialize models with fallback
try:
    model = get_model()
    embedder = get_embedder()
    processor = get_processor()
    caption_model = get_caption_model()
except Exception as e:
    logger.warning(f"Failed to initialize AI models: {e}")
    model = None
    embedder = None
    processor = None
    caption_model = None

_cached_responses = {}

def get_cached_response(cache_key):
    try:
        cache_entry = APICache.query.filter_by(query=cache_key).first()
        return cache_entry.raw_json if cache_entry else None
    except Exception as e:
        logger.error(f"Error getting cached response: {str(e)}")
        return None

def set_cached_response(cache_key, value):
    try:
        cache_entry = APICache.query.filter_by(query=cache_key).first()
        if cache_entry:
            cache_entry.raw_json = value
            cache_entry.created_at = datetime.utcnow()
        else:
            cache_entry = APICache(query=cache_key, raw_json=value)
            db.session.add(cache_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error setting cached response: {str(e)}")
        db.session.rollback()

def generate_cache_key(text, context=""):
    # Create a unique key based on input and context
    combined = f"{text.lower().strip()}|{context.lower().strip()}"
    return hashlib.md5(combined.encode()).hexdigest()

def ensure_chat_qa_table():
    try:
        db.create_all()
    except Exception as e:
        logger.error(f"Error ensuring chat QA table: {str(e)}")

def store_qa(user, question, answer, image_path=None, image_caption=None):
    try:
        # Compute embedding if embedder is available
        embedding = None
        if embedder:
            try:
                embedding = embedder.encode([question])[0].astype('float32').tobytes()
            except Exception as e:
                logger.warning(f"Failed to compute embedding: {e}")
        
        qa_entry = ChatQA(
            user=user,
            question=question,
            answer=answer,
            image_path=image_path,
            image_caption=image_caption,
            embedding=embedding
        )
        db.session.add(qa_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error storing QA: {str(e)}")
        db.session.rollback()

def find_semantic_qa(question, threshold=0.82):
    if not embedder:
        return None
        
    try:
        qa_entries = ChatQA.query.filter(ChatQA.embedding.isnot(None)).all()
        if not qa_entries:
            return None
            
        q_emb = embedder.encode([question])[0]
        best_score = 0
        best_answer = None
        
        for entry in qa_entries:
            db_emb = np.frombuffer(entry.embedding, dtype='float32')
            score = float(np.dot(q_emb, db_emb) / (np.linalg.norm(q_emb) * np.linalg.norm(db_emb)))
            if score > best_score and score >= threshold:
                best_score = score
                best_answer = entry.answer
                
        return best_answer
    except Exception as e:
        logger.error(f"Error finding semantic QA: {str(e)}")
        return None

def ensure_cache_table():
    try:
        db.create_all()
    except Exception as e:
        logger.error(f"Error ensuring cache table: {str(e)}")

def answer_query(question, context="", user="anonymous", image_path=None, image_caption=None):
    try:
        # Check cache first
        cache_key = generate_cache_key(question, context)
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response
            
        # Check for similar questions
        similar_answer = find_semantic_qa(question)
        if similar_answer:
            # Cache the response
            set_cached_response(cache_key, similar_answer)
            return similar_answer
            
        # If no model is available, return a default response
        if not model:
            return "I apologize, but I'm currently unable to process your request. The AI model is not available. Please try again later or contact support if the issue persists."
            
        # Generate new response using the model
        with model.chat_session():
            response = model.generate(question)
            
        # Store the Q&A pair
        store_qa(user, question, response)
        
        # Cache the response
        set_cached_response(cache_key, response)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in answer_query: {str(e)}")
        return "I apologize, but I encountered an error processing your request. Please try again."

def initialize_ai_models():
    """Initialize AI models with fallback"""
    try:
        # Initialize language model
        if os.path.exists(Config.MODEL_PATH):
            try:
                from gpt4all import GPT4All
                model = GPT4All(Config.MODEL_PATH)
                logger.info("Language model initialized successfully")
                return model
            except Exception as e:
                logger.error(f"Error initializing language model: {str(e)}")
                return None
        else:
            logger.warning("Language model file not found. Some features may be limited.")
            return None
    except Exception as e:
        logger.error(f"Error initializing AI models: {str(e)}")
        return None

def get_similar_articles(query, limit=5):
    """Get similar articles based on query"""
    try:
        if not embedder:
            logger.warning("Embedder not available. Returning empty results.")
            return []
            
        # Get all articles
        articles = KBArticle.query.filter_by(is_public=True).all()
        if not articles:
            return []
            
        # Encode query and articles
        query_embedding = embedder.encode(query)
        article_embeddings = embedder.encode([article.title + " " + article.content for article in articles])
        
        # Calculate similarities
        similarities = []
        for i, article in enumerate(articles):
            similarity = query_embedding.dot(article_embeddings[i]) / (
                query_embedding.norm() * article_embeddings[i].norm()
            )
            similarities.append((article, similarity))
            
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [article for article, _ in similarities[:limit]]
    except Exception as e:
        logger.error(f"Error getting similar articles: {str(e)}")
        return []

def generate_summary(text, max_length=200):
    """Generate a summary of the given text"""
    try:
        if not model:
            return text[:max_length] + "..."
            
        prompt = f"Please summarize the following text in {max_length} characters or less:\n\n{text}"
        with model.chat_session():
            summary = model.generate(prompt)
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return text[:max_length] + "..."

def process_document(file_path):
    """Process a document and extract relevant information"""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Generate summary
        summary = generate_summary(content)
        
        # Extract key information
        model = initialize_ai_models()
        if model:
            prompt = f"Extract key information from this text:\n\n{content}"
            key_info = model.generate(prompt, max_tokens=200)
        else:
            key_info = summary
            
        return {
            'content': content,
            'summary': summary,
            'key_info': key_info
        }
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return None 