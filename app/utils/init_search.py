"""
Search System Initialization

This module initializes the universal search system including
the optimized search engine and index manager.
"""

import logging
from app.utils.optimized_search_engine import optimized_search_engine
from app.utils.optimized_index_manager import optimized_index_manager

logger = logging.getLogger(__name__)

def init_search_system():
    """Initialize the universal search system with optimized database storage."""
    try:
        logger.info("Initializing optimized universal search system...")
        
        # Initialize optimized search engine
        logger.info("Initializing optimized search engine...")
        optimized_search_engine.initialize_index()
        
        # Start optimized index manager
        logger.info("Starting optimized index manager...")
        optimized_index_manager.start()
        
        logger.info("Optimized universal search system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize optimized search system: {e}")
        return False

def get_search_stats():
    """Get search system statistics."""
    try:
        index_stats = optimized_index_manager.get_stats()
        search_stats = optimized_search_engine.get_stats()
        
        return {
            'index_manager': index_stats,
            'search_engine': search_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting optimized search stats: {e}")
        return {} 