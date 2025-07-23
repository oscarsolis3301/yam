#!/usr/bin/env python3
"""
Enhanced Caching System for YAM

This module provides a comprehensive caching system that dramatically improves
YAM's performance through intelligent caching of database queries, file operations,
computed results, and frequently accessed data.

Features:
- Multi-tier caching (memory + file)
- Cache warming during background initialization
- Intelligent TTL (Time To Live) management
- Automatic cache invalidation
- Performance metrics and monitoring
- Compression for large cached data
- Thread-safe operations
- Memory management and cleanup
"""

import os
import json
import pickle
import gzip
import time
import threading
import hashlib
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from collections import defaultdict, OrderedDict
from contextlib import contextmanager

# Enhanced logging - delayed import to avoid circular dependencies
import logging
logger = logging.getLogger(__name__)

def setup_cache_logging():
    """Setup logging for cache system with fallback"""
    global logger
    try:
        from app.utils.logger import setup_logging
        logger = setup_logging()
    except ImportError:
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
    return logger

class CacheMetrics:
    """Track cache performance metrics"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.invalidations = 0
        self.memory_usage = 0
        self.disk_usage = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def record_hit(self):
        with self.lock:
            self.hits += 1
    
    def record_miss(self):
        with self.lock:
            self.misses += 1
    
    def record_set(self):
        with self.lock:
            self.sets += 1
    
    def record_invalidation(self):
        with self.lock:
            self.invalidations += 1
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            uptime = time.time() - self.start_time
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'sets': self.sets,
                'invalidations': self.invalidations,
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests,
                'memory_usage_mb': round(self.memory_usage / (1024 * 1024), 2),
                'disk_usage_mb': round(self.disk_usage / (1024 * 1024), 2),
                'uptime_seconds': round(uptime, 2)
            }

class CacheEntry:
    """Represents a cached item with metadata"""
    
    def __init__(self, data: Any, ttl: Optional[float] = None, tags: Optional[List[str]] = None):
        self.data = data
        self.created_at = time.time()
        self.last_accessed = self.created_at
        self.access_count = 0
        self.ttl = ttl
        self.tags = tags or []
        self.size = self._calculate_size(data)
    
    def _calculate_size(self, data: Any) -> int:
        """Estimate the size of the cached data"""
        try:
            return len(pickle.dumps(data))
        except Exception:
            return len(str(data).encode('utf-8'))
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired"""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl
    
    def access(self) -> Any:
        """Record access and return data"""
        self.last_accessed = time.time()
        self.access_count += 1
        return self.data

class EnhancedCache:
    """
    Comprehensive caching system with multiple tiers and intelligent management
    """
    
    def __init__(self, 
                 memory_limit_mb: int = 100,
                 disk_limit_mb: int = 500,
                 default_ttl: float = 3600,  # 1 hour
                 cache_dir: Optional[str] = None):
        
        self.memory_limit = memory_limit_mb * 1024 * 1024  # Convert to bytes
        self.disk_limit = disk_limit_mb * 1024 * 1024
        self.default_ttl = default_ttl
        
        # Memory cache (LRU-style with TTL)
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.memory_lock = threading.RLock()
        
        # File cache directory
        self.cache_dir = Path(cache_dir) if cache_dir else Path('app/cache/enhanced')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Metrics tracking
        self.metrics = CacheMetrics()
        
        # Cache warming strategies
        self.warm_functions: Dict[str, Callable] = {}
        
        # Tag-based invalidation
        self.tag_registry: Dict[str, List[str]] = defaultdict(list)
        
        # Background cleanup
        self._cleanup_thread = None
        self._running = True
        
        logger.info(f"Enhanced cache initialized - Memory: {memory_limit_mb}MB, Disk: {disk_limit_mb}MB")
    
    def start_background_cleanup(self):
        """Start background thread for cache maintenance"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._background_cleanup, 
                daemon=True, 
                name="CacheCleanup"
            )
            self._cleanup_thread.start()
            logger.info("Cache background cleanup started")
    
    def _background_cleanup(self):
        """Background thread for cache maintenance"""
        while self._running:
            try:
                # Clean up expired entries every 5 minutes
                time.sleep(300)  # 5 minutes
                self.cleanup_expired()
                self.cleanup_lru()
                self._update_disk_usage()
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _generate_key_hash(self, key: str) -> str:
        """Generate a filesystem-safe hash for the key"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a cached key"""
        key_hash = self._generate_key_hash(key)
        return self.cache_dir / f"{key_hash}.cache"
    
    def _get_meta_path(self, key: str) -> Path:
        """Get the metadata file path for a cached key"""
        key_hash = self._generate_key_hash(key)
        return self.cache_dir / f"{key_hash}.meta"
    
    def set(self, 
            key: str, 
            data: Any, 
            ttl: Optional[float] = None, 
            tags: Optional[List[str]] = None,
            force_disk: bool = False) -> bool:
        """
        Store data in cache with optional TTL and tags
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (None for no expiration)
            tags: Tags for invalidation
            force_disk: Force storage to disk instead of memory
        """
        try:
            ttl = ttl or self.default_ttl
            tags = tags or []
            
            entry = CacheEntry(data, ttl, tags)
            
            # Store in memory cache unless forced to disk or data is too large
            if not force_disk and entry.size < self.memory_limit / 10:  # Max 10% of memory per item
                with self.memory_lock:
                    self.memory_cache[key] = entry
                    self._enforce_memory_limit()
            
            # Also store large items or force_disk items to disk
            if force_disk or entry.size >= self.memory_limit / 10:
                self._store_to_disk(key, entry)
            
            # Update tag registry
            for tag in tags:
                if key not in self.tag_registry[tag]:
                    self.tag_registry[tag].append(key)
            
            self.metrics.record_set()
            logger.debug(f"Cached '{key}' with TTL {ttl}s, size {entry.size} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache '{key}': {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve data from cache
        
        Args:
            key: Cache key
            default: Default value if key not found
        """
        try:
            # Check memory cache first
            with self.memory_lock:
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    if not entry.is_expired():
                        # Move to end (LRU)
                        self.memory_cache.move_to_end(key)
                        self.metrics.record_hit()
                        return entry.access()
                    else:
                        # Remove expired entry
                        del self.memory_cache[key]
            
            # Check disk cache
            entry = self._load_from_disk(key)
            if entry and not entry.is_expired():
                # Promote frequently accessed items to memory
                if entry.access_count > 3:
                    with self.memory_lock:
                        if len(self.memory_cache) < 100:  # Don't overfill memory
                            self.memory_cache[key] = entry
                
                self.metrics.record_hit()
                return entry.access()
            
            self.metrics.record_miss()
            return default
            
        except Exception as e:
            logger.error(f"Failed to get '{key}': {e}")
            self.metrics.record_miss()
            return default
    
    def _store_to_disk(self, key: str, entry: CacheEntry):
        """Store cache entry to disk with compression"""
        try:
            file_path = self._get_file_path(key)
            meta_path = self._get_meta_path(key)
            
            # Store compressed data
            with gzip.open(file_path, 'wb') as f:
                pickle.dump(entry.data, f)
            
            # Store metadata
            meta = {
                'created_at': entry.created_at,
                'ttl': entry.ttl,
                'tags': entry.tags,
                'size': entry.size,
                'access_count': entry.access_count
            }
            with open(meta_path, 'w') as f:
                json.dump(meta, f)
                
        except Exception as e:
            logger.error(f"Failed to store '{key}' to disk: {e}")
    
    def _load_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Load cache entry from disk"""
        try:
            file_path = self._get_file_path(key)
            meta_path = self._get_meta_path(key)
            
            if not file_path.exists() or not meta_path.exists():
                return None
            
            # Load metadata
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            # Load compressed data
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # Reconstruct entry
            entry = CacheEntry(data, meta['ttl'], meta['tags'])
            entry.created_at = meta['created_at']
            entry.access_count = meta['access_count']
            entry.size = meta['size']
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to load '{key}' from disk: {e}")
            return None
    
    def _enforce_memory_limit(self):
        """Remove oldest items if memory limit exceeded"""
        current_size = sum(entry.size for entry in self.memory_cache.values())
        self.metrics.memory_usage = current_size
        
        while current_size > self.memory_limit and self.memory_cache:
            # Remove least recently used item
            old_key, old_entry = self.memory_cache.popitem(last=False)
            current_size -= old_entry.size
            logger.debug(f"Evicted '{old_key}' from memory cache")
    
    def _update_disk_usage(self):
        """Update disk usage metrics"""
        try:
            total_size = sum(
                f.stat().st_size 
                for f in self.cache_dir.glob('*.cache') 
                if f.exists()
            )
            self.metrics.disk_usage = total_size
        except Exception as e:
            logger.error(f"Failed to calculate disk usage: {e}")
    
    def clear_all(self):
        """Clear all cache data"""
        try:
            # Clear memory cache
            with self.memory_lock:
                self.memory_cache.clear()
            
            # Clear disk cache
            for cache_file in self.cache_dir.glob('*'):
                if cache_file.is_file():
                    cache_file.unlink()
            
            # Clear tag registry
            self.tag_registry.clear()
            
            # Reset metrics
            self.metrics = CacheMetrics()
            
            logger.info("All cache data cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def clear_expired(self):
        """Remove all expired entries from memory and disk cache"""
        try:
            expired_count = 0
            
            # Clear expired memory entries
            with self.memory_lock:
                expired_keys = [
                    key for key, entry in self.memory_cache.items() 
                    if entry.is_expired()
                ]
                for key in expired_keys:
                    del self.memory_cache[key]
                    expired_count += 1
            
            # Clear expired disk entries
            for cache_file in self.cache_dir.glob('*.cache'):
                try:
                    meta_file = cache_file.with_suffix('.meta')
                    if meta_file.exists():
                        with open(meta_file, 'r') as f:
                            meta = json.load(f)
                        
                        # Check if expired
                        if meta.get('ttl') and (time.time() - meta['created_at']) > meta['ttl']:
                            cache_file.unlink()
                            meta_file.unlink()
                            expired_count += 1
                except Exception as e:
                    logger.warning(f"Failed to check expiry for {cache_file}: {e}")
            
            if expired_count > 0:
                logger.info(f"Cleared {expired_count} expired cache entries")
                
        except Exception as e:
            logger.error(f"Failed to clear expired entries: {e}")
    
    def cleanup_lru(self, max_items: Optional[int] = None):
        """Remove least recently used items to reduce memory usage"""
        try:
            with self.memory_lock:
                if max_items is None:
                    # Remove items until under memory limit
                    current_size = sum(entry.size for entry in self.memory_cache.values())
                    removed_count = 0
                    
                    while current_size > self.memory_limit and self.memory_cache:
                        old_key, old_entry = self.memory_cache.popitem(last=False)
                        current_size -= old_entry.size
                        removed_count += 1
                    
                    if removed_count > 0:
                        logger.debug(f"LRU cleanup removed {removed_count} items (memory limit)")
                else:
                    # Remove items until under max_items limit
                    removed_count = 0
                    while len(self.memory_cache) > max_items and self.memory_cache:
                        old_key, old_entry = self.memory_cache.popitem(last=False)
                        removed_count += 1
                    
                    if removed_count > 0:
                        logger.debug(f"LRU cleanup removed {removed_count} items (max items: {max_items})")
                
        except Exception as e:
            logger.error(f"LRU cleanup failed: {e}")
    
    def cleanup_expired(self):
        """Alias for clear_expired for backward compatibility"""
        self.clear_expired()
    
    def ensure_initialized(self):
        """Ensure the cache system is properly initialized"""
        try:
            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Start background cleanup if not running
            if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
                self.start_background_cleanup()
            
            # Initialize metrics if needed
            if not hasattr(self, 'metrics') or self.metrics is None:
                self.metrics = CacheMetrics()
            
            # Initialize tag registry if needed
            if not hasattr(self, 'tag_registry'):
                self.tag_registry = defaultdict(list)
            
            logger.debug("Enhanced cache initialization verified")
            
        except Exception as e:
            logger.error(f"Cache initialization verification failed: {e}")
    
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag"""
        try:
            invalidated_count = 0
            
            # Find keys with this tag
            keys_to_remove = self.tag_registry.get(tag, [])
            
            # Remove from memory cache
            with self.memory_lock:
                for key in keys_to_remove:
                    if key in self.memory_cache:
                        del self.memory_cache[key]
                        invalidated_count += 1
            
            # Remove from disk cache
            for key in keys_to_remove:
                try:
                    file_path = self._get_file_path(key)
                    meta_path = self._get_meta_path(key)
                    if file_path.exists():
                        file_path.unlink()
                        invalidated_count += 1
                    if meta_path.exists():
                        meta_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove disk cache for key {key}: {e}")
            
            # Clear tag registry for this tag
            if tag in self.tag_registry:
                del self.tag_registry[tag]
            
            if invalidated_count > 0:
                logger.info(f"Invalidated {invalidated_count} cache entries with tag '{tag}'")
                self.metrics.invalidations += invalidated_count
            
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate by tag '{tag}': {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = self.metrics.get_stats()
        
        with self.memory_lock:
            stats['memory_items'] = len(self.memory_cache)
        
        # Count disk items
        try:
            disk_items = len(list(self.cache_dir.glob('*.cache')))
            stats['disk_items'] = disk_items
        except Exception:
            stats['disk_items'] = 0
        
        stats['tag_count'] = len(self.tag_registry)
        
        # Add memory usage breakdown
        stats['memory_usage'] = {
            'total_mb': round(self.metrics.memory_usage / (1024 * 1024), 2),
            'limit_mb': round(self.memory_limit / (1024 * 1024), 2),
            'usage_percent': round((self.metrics.memory_usage / self.memory_limit) * 100, 2) if self.memory_limit > 0 else 0
        }
        
        return stats

# Global enhanced cache instance
enhanced_cache = EnhancedCache()

# Convenience decorator for caching function results
def cache_result(key_func: Optional[Callable] = None, 
                ttl: Optional[float] = None, 
                tags: Optional[List[str]] = None):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            result = enhanced_cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            enhanced_cache.set(cache_key, result, ttl=ttl, tags=tags)
            return result
        
        return wrapper
    return decorator

# Initialize logging and background cleanup with error handling
try:
    setup_cache_logging()
    enhanced_cache.start_background_cleanup()
    logger.info("Enhanced caching system loaded and ready")
except Exception as e:
    logger.error(f"Enhanced cache initialization failed: {e}")
    # Continue anyway - basic cache should still work
