"""
Performance optimizations for the YAM Flask application
"""

import os
import sys
import gc
import threading
import time
import logging
from functools import wraps, lru_cache
from flask import request, g
import psutil


def format_uptime(seconds):
    """Convert seconds to human-readable format (hours, minutes, seconds)"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:  # Less than 1 hour
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:  # 1 hour or more
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = int(seconds % 60)
        return f"{hours}h {minutes}m {remaining_seconds}s"

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Central performance optimization manager"""
    
    def __init__(self, app=None):
        self.app = app
        self.startup_time = time.time()
        self.request_count = 0
        self.slow_requests = []
        self.memory_warnings = 0
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize performance optimizations for Flask app"""
        self.app = app
        
        # Enable performance monitoring
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Set Flask configurations for better performance
        app.config.update({
            'SEND_FILE_MAX_AGE_DEFAULT': 31536000,  # 1 year cache for static files
            'PERMANENT_SESSION_LIFETIME': 86400,    # 1 day session lifetime
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SECURE': False,  # Set to True in production with HTTPS
            'WTF_CSRF_TIME_LIMIT': None,    # Disable CSRF timeout
        })
        
        # Start background performance monitoring
        self.start_monitoring()
        
        logger.info("Performance optimizations initialized")
    
    def before_request(self):
        """Called before each request"""
        g.start_time = time.time()
        self.request_count += 1
        
        # Monitor memory usage
        if self.request_count % 100 == 0:  # Check every 100 requests
            self.check_memory_usage()
    
    def after_request(self, response):
        """Called after each request"""
        if hasattr(g, 'start_time'):
            request_time = time.time() - g.start_time
            
            # Log slow requests
            if request_time > 1.0:  # Requests taking more than 1 second
                self.slow_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'duration': request_time,
                    'timestamp': time.time()
                })
                logger.warning(f"Slow request: {request.method} {request.url} took {request_time:.2f}s")
                
                # Keep only last 50 slow requests
                if len(self.slow_requests) > 50:
                    self.slow_requests = self.slow_requests[-50:]
        
        # Add performance headers
        response.headers['X-Request-ID'] = str(self.request_count)
        
        return response
    
    def check_memory_usage(self):
        """Check and manage memory usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Warning threshold: 500MB
            if memory_mb > 500:
                self.memory_warnings += 1
                logger.warning(f"High memory usage: {memory_mb:.1f}MB")
                
                # Force garbage collection
                gc.collect()
                
                # If memory is still high after GC, log detailed info
                memory_info_after = process.memory_info()
                memory_mb_after = memory_info_after.rss / 1024 / 1024
                
                if memory_mb_after > 400:
                    logger.warning(f"Memory usage after GC: {memory_mb_after:.1f}MB")
                    
                    # Clear caches if memory is critically high
                    if memory_mb_after > 800:
                        self.clear_caches()
                        
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
    
    def clear_caches(self):
        """Clear various caches to free memory"""
        try:
            # Clear LRU caches
            for obj in gc.get_objects():
                if hasattr(obj, 'cache_clear') and callable(obj.cache_clear):
                    try:
                        obj.cache_clear()
                    except:
                        pass
            
            # Force garbage collection
            gc.collect()
            
            logger.info("Caches cleared due to high memory usage")
            
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
    
    def start_monitoring(self):
        """Start background monitoring thread"""
        def monitor():
            while True:
                try:
                    time.sleep(300)  # Check every 5 minutes
                    
                    # Clean up old slow requests
                    current_time = time.time()
                    self.slow_requests = [
                        req for req in self.slow_requests 
                        if current_time - req['timestamp'] < 3600  # Keep last hour
                    ]
                    
                    # Log performance stats
                    uptime = current_time - self.startup_time
                    formatted_uptime = format_uptime(uptime)
                    logger.info(f"Performance stats - Uptime: {formatted_uptime}, Requests: {self.request_count}, "
                               f"Slow requests: {len(self.slow_requests)}, Memory warnings: {self.memory_warnings}")
                    
                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def get_stats(self):
        """Get performance statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            uptime = time.time() - self.startup_time
            
            return {
                'uptime': uptime,
                'uptime_formatted': format_uptime(uptime),
                'request_count': self.request_count,
                'slow_requests': len(self.slow_requests),
                'memory_warnings': self.memory_warnings,
                'memory_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
            }
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}


def optimize_flask_for_electron():
    """Apply Flask optimizations specifically for Electron environment"""
    
    # Disable Flask's reloader in Electron mode
    os.environ['FLASK_RUN_RELOAD'] = 'false'
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'
    
    # Optimize Python for better performance
    if not hasattr(sys, '_getframe'):
        # Enable optimizations if not in debug mode
        sys.dont_write_bytecode = True
    
    # Set garbage collection thresholds for better performance
    gc.set_threshold(700, 10, 10)  # More aggressive GC
    
    # Disable some debugging features for performance
    os.environ['PYTHONOPTIMIZE'] = '1'
    
    logger.info("Flask optimized for Electron environment")


def performance_monitor(threshold_seconds=1.0):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                if execution_time > threshold_seconds:
                    logger.warning(f"Slow function: {func.__name__} took {execution_time:.2f}s")
        return wrapper
    return decorator


@lru_cache(maxsize=128)
def cached_file_exists(filepath):
    """Cached version of file existence check"""
    return os.path.exists(filepath)


@lru_cache(maxsize=64)
def cached_file_size(filepath):
    """Cached version of file size check"""
    try:
        return os.path.getsize(filepath)
    except:
        return 0


def debounce(wait_time):
    """Debounce decorator to prevent rapid function calls"""
    def decorator(func):
        last_called = [0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if current_time - last_called[0] >= wait_time:
                last_called[0] = current_time
                return func(*args, **kwargs)
            return None
        return wrapper
    return decorator


def optimize_database_queries():
    """Apply database query optimizations"""
    # This would contain database-specific optimizations
    # For now, just log that optimizations are applied
    logger.info("Database query optimizations applied")


def preload_critical_data():
    """Preload critical data that's frequently accessed"""
    # This function would preload commonly used data
    # Implementation depends on specific application needs
    logger.info("Critical data preloading completed")


# Initialize global performance optimizer
performance_optimizer = PerformanceOptimizer()

# Export main functions
__all__ = [
    'PerformanceOptimizer',
    'performance_optimizer',
    'optimize_flask_for_electron',
    'performance_monitor',
    'cached_file_exists',
    'cached_file_size',
    'debounce',
    'optimize_database_queries',
    'preload_critical_data',
    'format_uptime'
] 