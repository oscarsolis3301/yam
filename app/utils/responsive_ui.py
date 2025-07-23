#!/usr/bin/env python3
"""
Responsive UI Management for YAM

This module provides utilities to maintain UI responsiveness during heavy operations,
manage resource-intensive tasks, and provide smooth interaction with the Electron interface.

Features:
- Background task management
- UI operation throttling  
- Memory pressure monitoring
- Responsive operation splitting
- Electron interface optimization
"""

import time
import threading
import queue
import gc
from typing import Callable, Any, Optional, Dict, List
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class ResponsiveUIManager:
    """Manages UI responsiveness during heavy operations"""
    
    def __init__(self):
        self.operation_queue = queue.Queue(maxsize=100)
        self.worker_thread = None
        self.is_running = False
        self.current_operation = None
        self.memory_threshold_mb = 800  # Start throttling at 800MB
        self.max_operation_time_ms = 50  # Max time per operation chunk
        self.operation_stats = {
            'completed': 0,
            'failed': 0,
            'throttled': 0,
            'memory_cleanups': 0
        }
        
    def start(self):
        """Start the responsive UI worker thread"""
        if self.is_running:
            return
            
        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop, 
            daemon=True, 
            name="ResponsiveUIWorker"
        )
        self.worker_thread.start()
        logger.info("Responsive UI manager started")
    
    def stop(self):
        """Stop the responsive UI manager"""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        logger.info("Responsive UI manager stopped")
    
    def _worker_loop(self):
        """Main worker loop for processing operations"""
        while self.is_running:
            try:
                # Get next operation with timeout
                try:
                    operation = self.operation_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Check memory pressure before executing
                if self._check_memory_pressure():
                    self._handle_memory_pressure()
                    self.operation_stats['memory_cleanups'] += 1
                
                # Execute operation with time limiting
                self._execute_responsive_operation(operation)
                
                # Mark operation as complete
                self.operation_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in responsive UI worker: {e}")
                self.operation_stats['failed'] += 1
    
    def _execute_responsive_operation(self, operation):
        """Execute an operation with responsiveness controls"""
        start_time = time.time()
        self.current_operation = operation.get('name', 'unknown')
        
        try:
            func = operation['function']
            args = operation.get('args', ())
            kwargs = operation.get('kwargs', {})
            callback = operation.get('callback')
            
            # Execute with time monitoring
            result = func(*args, **kwargs)
            
            # Check if operation took too long
            execution_time_ms = (time.time() - start_time) * 1000
            if execution_time_ms > self.max_operation_time_ms:
                self.operation_stats['throttled'] += 1
                logger.debug(f"Operation '{self.current_operation}' took {execution_time_ms:.1f}ms (throttled)")
            
            # Execute callback if provided
            if callback:
                callback(result)
                
            self.operation_stats['completed'] += 1
            
        except Exception as e:
            logger.error(f"Operation '{self.current_operation}' failed: {e}")
            self.operation_stats['failed'] += 1
        finally:
            self.current_operation = None
    
    def _check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            process = psutil.Process()
            
            # Check both system and process memory
            system_pressure = memory.percent > 85
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            process_pressure = process_memory_mb > self.memory_threshold_mb
            
            return system_pressure or process_pressure
            
        except Exception as e:
            logger.warning(f"Failed to check memory pressure: {e}")
            return False
    
    def _handle_memory_pressure(self):
        """Handle memory pressure by cleaning up resources"""
        try:
            logger.info("Memory pressure detected, performing cleanup")
            
            # Try to clean enhanced cache
            try:
                from app.utils.enhanced_cache import enhanced_cache
                enhanced_cache.cleanup_lru(max_items=50)
                enhanced_cache.clear_expired()
                logger.debug("Enhanced cache cleanup completed")
            except Exception as cache_err:
                logger.warning(f"Cache cleanup failed: {cache_err}")
            
            # Force garbage collection
            gc.collect()
            
            # Small delay to allow cleanup to take effect
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Memory pressure handling failed: {e}")
    
    def schedule_operation(self, 
                          function: Callable, 
                          *args,
                          name: str = None,
                          callback: Callable = None,
                          priority: bool = False,
                          **kwargs) -> bool:
        """Schedule an operation for responsive execution"""
        try:
            operation = {
                'function': function,
                'args': args,
                'kwargs': kwargs,
                'name': name or function.__name__,
                'callback': callback,
                'priority': priority
            }
            
            if priority:
                # For priority operations, try to put at front
                # This is a simple implementation - could be improved with priority queue
                logger.debug(f"Scheduling priority operation: {operation['name']}")
            
            self.operation_queue.put(operation, block=False)
            return True
            
        except queue.Full:
            logger.warning(f"Operation queue full, dropping operation: {name}")
            return False
        except Exception as e:
            logger.error(f"Failed to schedule operation: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get responsive UI manager statistics"""
        return {
            'queue_size': self.operation_queue.qsize(),
            'is_running': self.is_running,
            'current_operation': self.current_operation,
            'stats': self.operation_stats.copy(),
            'memory_threshold_mb': self.memory_threshold_mb,
            'max_operation_time_ms': self.max_operation_time_ms
        }

# Global responsive UI manager
responsive_ui = ResponsiveUIManager()

@contextmanager
def responsive_operation(name: str = None, yield_interval: float = 0.01):
    """Context manager for making operations responsive by yielding control"""
    start_time = time.time()
    last_yield = start_time
    
    class ResponsiveContext:
        def __init__(self):
            self.should_yield = False
            self.total_yields = 0
        
        def yield_if_needed(self):
            nonlocal last_yield
            current_time = time.time()
            
            # Yield every yield_interval seconds
            if current_time - last_yield > yield_interval:
                time.sleep(0.001)  # Very small sleep to yield control
                last_yield = current_time
                self.total_yields += 1
                self.should_yield = False
                
                # Check memory pressure periodically
                if self.total_yields % 100 == 0:
                    if responsive_ui._check_memory_pressure():
                        responsive_ui._handle_memory_pressure()
    
    context = ResponsiveContext()
    try:
        yield context
    finally:
        total_time = time.time() - start_time
        if name and total_time > 0.1:  # Log operations that take > 100ms
            logger.debug(f"Responsive operation '{name}' completed in {total_time:.2f}s "
                        f"with {context.total_yields} yields")

def responsive_split_operation(items: List[Any], 
                             operation_func: Callable,
                             batch_size: int = 10,
                             name: str = None) -> List[Any]:
    """Split a large operation into responsive batches"""
    results = []
    total_items = len(items)
    
    with responsive_operation(name=name or "split_operation") as ctx:
        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]
            batch_results = []
            
            for item in batch:
                try:
                    result = operation_func(item)
                    batch_results.append(result)
                except Exception as e:
                    logger.warning(f"Item processing failed: {e}")
                    batch_results.append(None)
                
                # Yield control between items
                ctx.yield_if_needed()
            
            results.extend(batch_results)
            
            # Log progress for large operations
            if total_items > 100:
                progress = min(i + batch_size, total_items)
                if progress % (total_items // 10) == 0:  # Log every 10%
                    logger.debug(f"Responsive operation progress: {progress}/{total_items}")
    
    return results

def throttled_function(max_calls_per_second: float = 10.0):
    """Decorator to throttle function calls to maintain responsiveness"""
    min_interval = 1.0 / max_calls_per_second
    last_call_time = 0
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal last_call_time
            
            current_time = time.time()
            time_since_last = current_time - last_call_time
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
            
            last_call_time = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def ensure_responsive_ui():
    """Ensure responsive UI manager is running"""
    if not responsive_ui.is_running:
        responsive_ui.start()

def get_ui_responsiveness_status() -> Dict[str, Any]:
    """Get current UI responsiveness status"""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        status = {
            'responsive_ui_active': responsive_ui.is_running,
            'memory_usage_mb': round(memory_mb, 1),
            'memory_pressure': memory_mb > responsive_ui.memory_threshold_mb,
            'ui_stats': responsive_ui.get_stats()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get UI responsiveness status: {e}")
        return {
            'responsive_ui_active': responsive_ui.is_running,
            'error': str(e)
        }

# Auto-start responsive UI manager
try:
    ensure_responsive_ui()
    logger.info("Responsive UI management system initialized")
except Exception as e:
    logger.error(f"Failed to initialize responsive UI management: {e}") 