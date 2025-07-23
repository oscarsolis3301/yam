"""
Shared state module for YAM application.

This module contains global variables and state that need to be shared
across multiple blueprints and modules.
"""

import time
import threading
import weakref
from contextlib import contextmanager



# Global initialization tracking
_app_initialized = False
_background_init_started = False
_blueprints_registered = False

_initialization_state = {
    'status': 'starting',  # starting, basic_complete, full_complete, error
    'start_time': time.time(),
    'components': {},
    'performance_metrics': {
        'memory_usage': [],
        'initialization_times': {},
        'system_info': {},
        'errors': []
    },
    'last_heartbeat': time.time()
}

# Memory Management System with Enhanced Caching Integration
class MemoryManager:
    """Enhanced memory manager with cache integration and better cleanup"""
    
    def __init__(self):
        self.cleanup_callbacks = []
        self.memory_threshold_mb = 300  # More aggressive threshold for Electron
        self.force_gc_threshold_mb = 450  # Lower force GC threshold
        self.cache_cleanup_threshold_mb = 350  # Lower cache cleanup threshold
        self.last_cleanup = time.time()
        self.cleanup_interval = 15  # More frequent cleanup
        
    def register_cleanup(self, callback):
        """Register a cleanup callback"""
        self.cleanup_callbacks.append(weakref.ref(callback))
        
    def check_memory_usage(self):
        """Check current memory usage and trigger cleanup if needed"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            # More aggressive memory management for Electron
            if memory_mb > self.force_gc_threshold_mb:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"High memory usage detected: {memory_mb:.1f}MB - forcing cleanup")
                self.force_cleanup()
                
            elif memory_mb > self.cache_cleanup_threshold_mb:
                # Use enhanced cache cleanup
                self.smart_cache_cleanup()
                
            elif memory_mb > self.memory_threshold_mb:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Elevated memory usage: {memory_mb:.1f}MB")
                # Periodic cleanup
                if time.time() - self.last_cleanup > self.cleanup_interval:
                    self.gentle_cleanup()
                
            return memory_mb
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not check memory usage: {e}")
            return 0
            
    def smart_cache_cleanup(self):
        """Use enhanced cache system for intelligent cleanup"""
        try:
            from app.utils.enhanced_cache import enhanced_cache
            
            # Get cache stats first
            stats = enhanced_cache.get_stats()
            memory_usage = stats.get('memory_usage', {})
            
            if memory_usage.get('total_mb', 0) > 50:  # If cache using >50MB
                # Clean LRU items first
                enhanced_cache.cleanup_lru(max_items=50)
                import logging
                logger = logging.getLogger(__name__)
                logger.debug("Performed smart cache LRU cleanup")
                
            # Gentle garbage collection
            import gc
            gc.collect()
            self.last_cleanup = time.time()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Smart cache cleanup failed: {e}")
            self.gentle_cleanup()
            
    def gentle_cleanup(self):
        """Gentle cleanup without affecting performance"""
        try:
            # Run registered cleanup callbacks
            for callback_ref in self.cleanup_callbacks[:]:
                callback = callback_ref()
                if callback is not None:
                    try:
                        callback()
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Cleanup callback failed: {e}")
                else:
                    self.cleanup_callbacks.remove(callback_ref)
            
            # Gentle garbage collection
            import gc
            gc.collect()
            self.last_cleanup = time.time()
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("Gentle memory cleanup completed")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Gentle cleanup failed: {e}")
            
    def force_cleanup(self):
        """Force aggressive cleanup when memory is critical"""
        try:
            # Enhanced cache cleanup
            try:
                from app.utils.enhanced_cache import enhanced_cache
                enhanced_cache.clear_expired()
                enhanced_cache.cleanup_lru(max_items=25)  # More aggressive
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Enhanced cache force cleanup completed")
            except Exception as cache_err:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Enhanced cache cleanup failed: {cache_err}")
            
            # Run all cleanup callbacks
            for callback_ref in self.cleanup_callbacks[:]:
                callback = callback_ref()
                if callback is not None:
                    try:
                        callback()
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Force cleanup callback failed: {e}")
                else:
                    self.cleanup_callbacks.remove(callback_ref)
            
            # Force multiple GC passes
            import gc
            for _ in range(2):  # Reduced from 3 to 2
                gc.collect()
            
            self.last_cleanup = time.time()
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Force memory cleanup completed")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Force cleanup failed: {e}")

# Global memory manager instance
memory_manager = MemoryManager()

@contextmanager
def memory_managed_operation(operation_name):
    """Context manager for memory-managed operations"""
    initial_memory = memory_manager.check_memory_usage()
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Starting {operation_name} - Memory: {initial_memory:.1f}MB")
    
    try:
        yield
    finally:
        final_memory = memory_manager.check_memory_usage()
        logger.debug(f"Completed {operation_name} - Memory: {final_memory:.1f}MB")
        
        # Force cleanup if memory increased significantly
        if final_memory > initial_memory + 50:  # 50MB threshold
            logger.info(f"Memory increased by {final_memory - initial_memory:.1f}MB during {operation_name}, forcing cleanup")
            memory_manager.force_cleanup()

def update_initialization_status(component, status, duration=None, error=None):
    """Update initialization status for a specific component - Windows-safe logging"""
    global _initialization_state
    
    _initialization_state['components'][component] = {
        'status': status,
        'timestamp': time.time(),
        'duration': duration,
        'error': error
    }
    
    if duration:
        _initialization_state['performance_metrics']['initialization_times'][component] = duration
    
    if error:
        _initialization_state['performance_metrics']['errors'].append({
            'component': component,
            'error': str(error),
            'timestamp': time.time()
        })
    
    _initialization_state['last_heartbeat'] = time.time()
    
    # Windows-safe logging (avoid Unicode arrows)
    status_msg = f"Component '{component}': {status}"
    if duration:
        status_msg += f" ({duration:.2f}s)"
    if error:
        status_msg += f" - Error: {error}"
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(status_msg)

def get_initialization_status():
    """Get current initialization status"""
    return _initialization_state.copy()

def set_app_initialized(value=True):
    """Set the app initialized flag"""
    global _app_initialized
    _app_initialized = value

def set_blueprints_registered(value=True):
    """Set the blueprints registered flag"""
    global _blueprints_registered
    _blueprints_registered = value

def set_background_init_started(value=True):
    """Set the background init started flag"""
    global _background_init_started
    _background_init_started = value

# Export the variables that blueprints need
__all__ = [
    'memory_manager',
    '_initialization_state',
    '_app_initialized',
    '_blueprints_registered',
    '_background_init_started',
    'update_initialization_status',
    'get_initialization_status',
    'set_app_initialized',
    'set_blueprints_registered',
    'set_background_init_started',
    'memory_managed_operation'
] 