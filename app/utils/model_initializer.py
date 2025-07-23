import os
import logging
from app.config import Config

logger = logging.getLogger('spark')

def initialize_models():
    """Initialize all required models and return their status"""
    try:
        # Validate configuration
        Config.validate()
        
        # Initialize models
        from app.utils.models import get_model, get_embedder, get_processor, get_caption_model
        
        model = get_model()
        embedder = get_embedder()
        processor = get_processor()
        caption_model = get_caption_model()
        
        if all(x is None for x in [model, embedder, processor, caption_model]):
            logger.error("Failed to initialize any models")
            return False
            
        if model is None:
            logger.warning("Language model failed to initialize")
            
        if embedder is None:
            logger.warning("Embedding model failed to initialize")
            
        if processor is None or caption_model is None:
            logger.warning("Image processing models failed to initialize")
            
        return True
    except Exception as e:
        logger.error(f"Error during model initialization: {e}")
        return False 