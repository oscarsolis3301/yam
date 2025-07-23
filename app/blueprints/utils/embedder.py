import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import os
from pathlib import Path

logger = logging.getLogger('spark')

class TextEmbedder:
    def __init__(self):
        try:
            # Try to load from cache first
            cache_dir = Path.home() / '.cache' / 'sentence-transformers'
            model_path = cache_dir / 'all-MiniLM-L6-v2'
            
            if model_path.exists():
                logger.info("Loading model from cache...")
                self.model = SentenceTransformer(str(model_path))
            else:
                logger.info("Downloading model from HuggingFace...")
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            logger.info("Text embedder initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize text embedder: {str(e)}")
            self.model = None
            # Create a simple fallback embedder
            self._init_fallback()

    def _init_fallback(self):
        """Initialize a simple fallback embedder that uses basic text features"""
        logger.info("Initializing fallback embedder...")
        self.fallback_dim = 128  # Simple fixed dimension for fallback

    def _fallback_embed(self, text):
        """Simple fallback embedding using basic text features"""
        # Convert text to lowercase and split into words
        words = text.lower().split()
        # Create a simple bag-of-words like embedding
        embedding = np.zeros(self.fallback_dim)
        for i, word in enumerate(words):
            if i < self.fallback_dim:
                # Use word length and position as simple features
                embedding[i] = len(word) / 10.0  # Normalize by max word length
        return embedding

    def embed_text(self, text):
        """
        Convert text to embedding vector
        """
        try:
            if self.model:
                # Use the main model
                embedding = self.model.encode(text)
                return embedding.tobytes()
            else:
                # Use fallback
                embedding = self._fallback_embed(text)
                return embedding.tobytes()
        except Exception as e:
            logger.error(f"Error embedding text: {str(e)}")
            return None

    def compute_similarity(self, text1, text2):
        """
        Compute similarity between two texts
        """
        try:
            if self.model:
                # Use the main model
                emb1 = self.model.encode(text1)
                emb2 = self.model.encode(text2)
            else:
                # Use fallback
                emb1 = self._fallback_embed(text1)
                emb2 = self._fallback_embed(text2)
            
            # Compute cosine similarity
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            return 0.0

# Create a singleton instance
embedder = TextEmbedder() 