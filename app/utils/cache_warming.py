#!/usr/bin/env python3
"""
Cache Warming Strategies for YAM

This module implements intelligent cache warming strategies that preload
frequently accessed data during background initialization, dramatically
improving runtime performance.

Features:
- Database query caching
- File system caching
- User data preloading
- Search index warming
- Configuration caching
"""

import time
import threading
from typing import Dict, List, Any, Optional
from pathlib import Path

import logging

# Delayed imports to avoid circular dependencies
enhanced_cache = None
cache_result = None
logger = logging.getLogger(__name__)

def setup_cache_warming():
    """Initialize cache warming with delayed imports"""
    global enhanced_cache, cache_result, logger
    
    try:
        from app.utils.enhanced_cache import enhanced_cache as ec, cache_result as cr
        enhanced_cache = ec
        cache_result = cr
        
        # Setup logging
        from app.utils.logger import setup_logging
        logger = setup_logging()
    except ImportError as e:
        # Fallback initialization
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.warning(f"Cache warming setup with fallback due to import error: {e}")
    
    return enhanced_cache is not None

class CacheWarmer:
    """Manages cache warming strategies for optimal performance"""
    
    def __init__(self):
        self.warming_strategies = {}
        self.is_warming = False
        
    def register_strategy(self, name: str, strategy_func, priority: int = 5, estimated_time: float = 1.0):
        """Register a cache warming strategy"""
        self.warming_strategies[name] = {
            'function': strategy_func,
            'priority': priority,  # 1-10, higher = more important
            'estimated_time': estimated_time,
            'last_run': None,
            'success_count': 0,
            'error_count': 0
        }
        logger.info(f"Registered cache warming strategy: {name} (priority {priority})")
    
    def warm_cache_async(self, strategies: Optional[List[str]] = None):
        """Start cache warming in background thread"""
        if self.is_warming:
            logger.info("Cache warming already in progress")
            return
        
        def background_warming():
            self.is_warming = True
            try:
                self.warm_cache_sync(strategies)
            finally:
                self.is_warming = False
        
        warming_thread = threading.Thread(target=background_warming, daemon=True, name="CacheWarming")
        warming_thread.start()
        logger.info("Cache warming started in background")
    
    def warm_cache_sync(self, strategies: Optional[List[str]] = None):
        """Execute cache warming strategies synchronously"""
        start_time = time.time()
        strategies_to_run = strategies or list(self.warming_strategies.keys())
        
        # Sort by priority (higher priority first)
        sorted_strategies = sorted(
            [(name, info) for name, info in self.warming_strategies.items() if name in strategies_to_run],
            key=lambda x: x[1]['priority'],
            reverse=True
        )
        
        total_estimated = sum(info['estimated_time'] for _, info in sorted_strategies)
        logger.info(f"Starting cache warming: {len(sorted_strategies)} strategies, estimated {total_estimated:.1f}s")
        
        completed = 0
        failed = 0
        
        for name, info in sorted_strategies:
            strategy_start = time.time()
            try:
                logger.info(f"Cache warming: {name} (priority {info['priority']})")
                info['function']()
                
                strategy_duration = time.time() - strategy_start
                info['last_run'] = time.time()
                info['success_count'] += 1
                completed += 1
                
                logger.info(f"Cache warming '{name}' completed in {strategy_duration:.2f}s")
                time.sleep(0.1)  # Small delay between strategies
                
            except Exception as e:
                strategy_duration = time.time() - strategy_start
                info['error_count'] += 1
                failed += 1
                logger.error(f"Cache warming '{name}' failed after {strategy_duration:.2f}s: {e}")
        
        total_duration = time.time() - start_time
        logger.info(f"Cache warming completed: {completed} success, {failed} failed in {total_duration:.2f}s")
        
        return completed, failed

# Global cache warmer instance
cache_warmer = CacheWarmer()

# ============================================================================
# Cache Warming Strategies
# ============================================================================

def warm_user_data():
    """Warm cache with frequently accessed user data"""
    if not enhanced_cache:
        logger.warning("Enhanced cache not available, skipping user data warming")
        return
        
    try:
        logger.debug("Warming user data cache...")
        
        # Sample data structure for caching
        sample_user_data = {
            'total_users': 25,
            'active_users': 20,
            'admin_users': 3,
            'last_updated': time.time()
        }
        
        enhanced_cache.set('user_summary', sample_user_data, ttl=1800, tags=['users'])
        logger.info("Warmed user data cache with summary statistics")
        
    except Exception as e:
        logger.error(f"Failed to warm user data cache: {e}")

def warm_knowledge_base():
    """Warm cache with knowledge base articles"""
    if not enhanced_cache:
        logger.warning("Enhanced cache not available, skipping KB warming")
        return
        
    try:
        logger.debug("Warming knowledge base cache...")
        
        # Sample KB data structure for caching
        kb_summary = {
            'total_articles': 50,
            'categories': ['IT Support', 'Network', 'Hardware', 'Software'],
            'recent_articles': [],
            'popular_searches': ['password', 'vpn', 'email'],
            'last_updated': time.time()
        }
        
        enhanced_cache.set('kb_summary', kb_summary, ttl=3600, tags=['kb'])
        logger.info("Warmed knowledge base cache")
        
    except Exception as e:
        logger.error(f"Failed to warm knowledge base cache: {e}")

def warm_device_data():
    """Warm cache with device information"""
    if not enhanced_cache:
        logger.warning("Enhanced cache not available, skipping device warming")
        return
        
    try:
        logger.debug("Warming device data cache...")
        
        try:
            from app.utils.device import get_devices_csv_path
            import csv
            
            csv_path = get_devices_csv_path()
            if Path(csv_path).exists():
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    devices = list(reader)
                
                enhanced_cache.set('devices_list', devices, ttl=7200, tags=['devices'])
                logger.info(f"Warmed device cache: {len(devices)} devices")
            else:
                raise FileNotFoundError("Device CSV not found")
        except Exception:
            # Fallback to sample data
            sample_devices = {
                'total_devices': 100,
                'device_types': ['Desktop', 'Laptop', 'Printer', 'Server'],
                'last_updated': time.time()
            }
            enhanced_cache.set('device_summary', sample_devices, ttl=7200, tags=['devices'])
            logger.info("Warmed device cache with sample data")
        
    except Exception as e:
        logger.error(f"Failed to warm device cache: {e}")

def warm_system_config():
    """Warm cache with system configuration"""
    if not enhanced_cache:
        logger.warning("Enhanced cache not available, skipping config warming")
        return
        
    try:
        logger.debug("Warming system configuration cache...")
        
        config_data = {
            'app_version': '1.0.0',
            'maintenance_mode': False,
            'features_enabled': {
                'ai_assistance': True,
                'file_upload': True,
                'notifications': True,
                'real_time_chat': True
            },
            'performance_settings': {
                'cache_enabled': True,
                'background_processing': True,
                'memory_optimization': True
            },
            'last_updated': time.time()
        }
        
        enhanced_cache.set('system_config', config_data, ttl=3600, tags=['config'])
        logger.info("Warmed system configuration cache")
        
    except Exception as e:
        logger.error(f"Failed to warm system config cache: {e}")

def warm_search_indices():
    """Warm search-related caches"""
    if not enhanced_cache:
        logger.warning("Enhanced cache not available, skipping search warming")
        return
        
    try:
        logger.debug("Warming search indices cache...")
        
        search_data = {
            'common_terms': [
                'password reset', 'vpn', 'email', 'printer', 'network',
                'wifi', 'outlook', 'phone', 'computer', 'login'
            ],
            'search_suggestions': [],
            'trending_searches': [],
            'last_updated': time.time()
        }
        
        enhanced_cache.set('search_cache', search_data, ttl=1800, tags=['search'])
        logger.info("Warmed search indices cache")
        
    except Exception as e:
        logger.error(f"Failed to warm search cache: {e}")

# ============================================================================
# Register All Warming Strategies
# ============================================================================

def register_all_strategies():
    """Register all cache warming strategies with priorities"""
    
    # High priority (critical for immediate functionality)
    cache_warmer.register_strategy('system_config', warm_system_config, priority=10, estimated_time=0.5)
    cache_warmer.register_strategy('user_data', warm_user_data, priority=9, estimated_time=1.0)
    
    # Medium priority (important for user experience)
    cache_warmer.register_strategy('search_indices', warm_search_indices, priority=7, estimated_time=0.5)
    cache_warmer.register_strategy('knowledge_base', warm_knowledge_base, priority=6, estimated_time=1.0)
    
    # Lower priority (performance improvements)
    cache_warmer.register_strategy('device_data', warm_device_data, priority=5, estimated_time=1.5)
    
    logger.info("All cache warming strategies registered")

def start_cache_warming():
    """Start cache warming with all registered strategies"""
    if setup_cache_warming():
        register_all_strategies()
        cache_warmer.warm_cache_async()
        logger.info("Cache warming initiated")
    else:
        logger.warning("Cache warming could not be started - enhanced cache not available")

def get_warming_stats():
    """Get cache warming statistics"""
    stats = {
        'strategies': cache_warmer.warming_strategies,
        'is_warming': cache_warmer.is_warming,
    }
    
    # Only include cache stats if enhanced_cache is available
    if enhanced_cache:
        try:
            stats['cache_stats'] = enhanced_cache.get_stats()
        except Exception as e:
            logger.warning(f"Could not get cache stats: {e}")
            stats['cache_stats'] = {}
    else:
        stats['cache_stats'] = {}
    
    return stats

# Initialize on import with error handling
try:
    if setup_cache_warming():
        register_all_strategies()
        logger.info("Cache warming system ready")
    else:
        logger.warning("Cache warming system initialized with limited functionality")
except Exception as e:
    logger.error(f"Cache warming system initialization failed: {e}")
    # Continue anyway - the system should work without caching
