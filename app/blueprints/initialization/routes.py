import os
import sys
import time
import logging
import threading
import gc
import weakref
from contextlib import contextmanager
from flask import current_app
from extensions import db
from app.shared_state import memory_manager, _initialization_state, _app_initialized, _blueprints_registered

logger = logging.getLogger(__name__)

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
                logger.warning(f"High memory usage detected: {memory_mb:.1f}MB - forcing cleanup")
                self.force_cleanup()
                
            elif memory_mb > self.cache_cleanup_threshold_mb:
                # Use enhanced cache cleanup
                self.smart_cache_cleanup()
                
            elif memory_mb > self.memory_threshold_mb:
                logger.debug(f"Elevated memory usage: {memory_mb:.1f}MB")
                # Periodic cleanup
                if time.time() - self.last_cleanup > self.cleanup_interval:
                    self.gentle_cleanup()
                
            return memory_mb
        except Exception as e:
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
                logger.debug("Performed smart cache LRU cleanup")
                
            # Gentle garbage collection
            gc.collect()
            self.last_cleanup = time.time()
            
        except Exception as e:
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
                        logger.warning(f"Cleanup callback failed: {e}")
                else:
                    self.cleanup_callbacks.remove(callback_ref)
            
            # Gentle garbage collection
            gc.collect()
            self.last_cleanup = time.time()
            logger.debug("Gentle memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Gentle cleanup failed: {e}")
            
    def force_cleanup(self):
        """Force aggressive cleanup when memory is critical"""
        try:
            # Enhanced cache cleanup
            try:
                from app.utils.enhanced_cache import enhanced_cache
                enhanced_cache.clear_expired()
                enhanced_cache.cleanup_lru(max_items=25)  # More aggressive
                logger.info("Enhanced cache force cleanup completed")
            except Exception as cache_err:
                logger.warning(f"Enhanced cache cleanup failed: {cache_err}")
            
            # Run all cleanup callbacks
            for callback_ref in self.cleanup_callbacks[:]:
                callback = callback_ref()
                if callback is not None:
                    try:
                        callback()
                    except Exception as e:
                        logger.warning(f"Force cleanup callback failed: {e}")
                else:
                    self.cleanup_callbacks.remove(callback_ref)
            
            # Force multiple GC passes
            for _ in range(2):  # Reduced from 3 to 2
                gc.collect()
            
            self.last_cleanup = time.time()
            logger.info("Force memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Force cleanup failed: {e}")

@contextmanager
def memory_managed_operation(operation_name):
    """Context manager for memory-managed operations"""
    initial_memory = memory_manager.check_memory_usage()
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
    
    logger.info(status_msg)

def get_initialization_status():
    """Get current initialization status"""
    return _initialization_state.copy()

def log_system_performance():
    """Log current system performance metrics"""
    try:
        import psutil
        import os
        
        # Get process info
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        # Get system info
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=0.1)
        
        metrics = {
            'timestamp': time.time(),
            'process': {
                'memory_mb': memory_info.rss / (1024 * 1024),
                'cpu_percent': cpu_percent,
                'threads': process.num_threads(),
                'open_files': len(process.open_files())
            },
            'system': {
                'memory_percent': system_memory.percent,
                'memory_available_mb': system_memory.available / (1024 * 1024),
                'cpu_percent': system_cpu,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        }
        
        _initialization_state['performance_metrics']['memory_usage'].append(metrics)
        
        # Keep only last 50 measurements
        if len(_initialization_state['performance_metrics']['memory_usage']) > 50:
            _initialization_state['performance_metrics']['memory_usage'] = \
                _initialization_state['performance_metrics']['memory_usage'][-50:]
        
        # Log warning if memory usage is high
        if metrics['process']['memory_mb'] > 500:
            logger.warning(f"High memory usage: {metrics['process']['memory_mb']:.1f}MB")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to collect performance metrics: {e}")
        return None

def start_performance_monitoring():
    """Start lightweight performance monitoring for Electron mode"""
    def lightweight_monitor_performance():
        # Very long intervals to minimize CPU usage
        startup_interval = 600   # 10 minutes during startup
        normal_interval = 300    # 5 minutes during normal operation
        
        iteration_count = 0
        
        while True:
            try:
                # Use very long adaptive intervals to prevent CPU overhead
                if _initialization_state['status'] in ['starting', 'login_ready']:
                    sleep_time = startup_interval
                else:
                    sleep_time = normal_interval
                
                time.sleep(sleep_time)
                iteration_count += 1
                
                # Minimal monitoring during startup
                if _initialization_state['status'] in ['starting', 'login_ready']:
                    _initialization_state['last_heartbeat'] = time.time()
                    
                    # Log progress very infrequently (every 10 minutes)
                    elapsed = time.time() - _initialization_state['start_time']
                    if elapsed % 600 < 1:  # Log every 10 minutes
                        completed_components = sum(1 for comp in _initialization_state['components'].values() 
                                                if comp['status'] in ['complete', 'success'])
                        total_components = len(_initialization_state['components'])
                        
                        if total_components > 0:
                            logger.debug(f"Startup progress: {completed_components}/{total_components} components, "
                                       f"elapsed: {elapsed:.1f}s")
                else:
                    # Very light monitoring after initialization
                    if iteration_count % 5 == 0:  # Only every fifth iteration
                        log_system_performance()
                    _initialization_state['last_heartbeat'] = time.time()
                
                # Memory management every 10 iterations to reduce frequency
                if iteration_count % 10 == 0:
                    memory_manager.gentle_cleanup()
                    
                    # Check responsive UI health less frequently
                    try:
                        from app.utils.responsive_ui import responsive_ui
                        if responsive_ui.is_running:
                            ui_stats = responsive_ui.get_stats()
                            if ui_stats['queue_size'] > 75:  # Higher threshold
                                logger.warning(f"Responsive UI queue size high: {ui_stats['queue_size']}")
                    except Exception as ui_err:
                        logger.debug(f"Responsive UI check failed: {ui_err}")
                    
                    logger.debug(f"Lightweight monitor: Performed cleanup (iteration {iteration_count})")
                
            except Exception as e:
                logger.error(f"Error in lightweight performance monitoring: {e}")
                time.sleep(600)  # Wait much longer on error
    
    monitor_thread = threading.Thread(target=lightweight_monitor_performance, daemon=True, name="LightweightMonitor")
    monitor_thread.start()
    logger.info("Lightweight performance monitoring started for Electron mode")

def init_basic_app():
    """Initialize only critical app components needed for login and basic functionality - DEPRECATED"""
    # This function is now deprecated in favor of init_fast_startup()
    # Kept for backward compatibility but does minimal work
    global _initialization_state
    
    if _app_initialized:
        logger.info("App already initialized via fast startup, skipping basic init")
        return
    
    logger.info("Running deprecated basic init - consider using fast startup instead")
    
    try:
        # Just ensure app context and database tables exist
        with current_app.app_context():
            db.create_all()
            logger.info("Basic database tables created")
        
        # Start performance monitoring
        try:
            start_performance_monitoring()
        except Exception as pm_err:
            logger.warning(f"Performance monitoring failed: {pm_err}")
        
        _initialization_state['status'] = 'basic_complete'
        logger.info("Basic app initialization completed (deprecated path)")
        
    except Exception as e:
        _initialization_state['status'] = 'error'
        logger.error(f"Basic app initialization failed: {e}")
        # Don't raise - let the app continue with minimal functionality

def init_ultra_minimal_startup():
    """Enhanced ultra-minimal startup with better memory management and caching"""
    global _app_initialized, _initialization_state
    
    if _app_initialized:
        logger.info("App already initialized, skipping ultra-minimal startup")
        return
    
    update_initialization_status('ultra_minimal_startup', 'starting')
    ultra_start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("RESPONSIVE ULTRA-MINIMAL STARTUP: CACHE-OPTIMIZED")
    logger.info("Using enhanced cache system for optimal performance")
    logger.info("=" * 60)
    
    # Check initial memory
    initial_memory = memory_manager.check_memory_usage()
    logger.info(f"Initial memory usage: {initial_memory:.1f}MB")
    
    try:
        # STEP 1: Initialize enhanced cache system first with optimized settings
        logger.info("[INIT] Step 1: Initializing enhanced cache system...")
        update_initialization_status('enhanced_cache', 'starting')
        
        try:
            from app.utils.enhanced_cache import enhanced_cache
            # Set more aggressive memory limits for Electron
            enhanced_cache.memory_limit = 50 * 1024 * 1024  # 50MB limit
            enhanced_cache.ensure_initialized()
            
            # Pre-warm cache with essential data
            enhanced_cache.set('app_startup_time', ultra_start_time, ttl=3600)
            logger.info("Enhanced cache system initialized with optimized settings")
        except Exception as cache_err:
            logger.warning(f"Enhanced cache initialization failed: {cache_err}")
        
        update_initialization_status('enhanced_cache', 'complete', time.time() - ultra_start_time)
        
        # STEP 2: MINIMAL database with caching and immediate memory management
        logger.info("[INIT] Step 2: Creating minimal database tables...")
        update_initialization_status('minimal_database', 'starting')
        
        try:
            with current_app.app_context():
                # Only create essential tables for login
                from app.models import User, UserSettings
                
                # Check cache first to avoid redundant operations
                cache_key = "essential_tables_created"
                cached_result = enhanced_cache.get(cache_key) if 'enhanced_cache' in locals() else None
                
                if not cached_result:
                    User.__table__.create(db.engine, checkfirst=True)
                    UserSettings.__table__.create(db.engine, checkfirst=True)
                    if 'enhanced_cache' in locals():
                        enhanced_cache.set(cache_key, True, ttl=3600)  # Cache for 1 hour
                
                logger.info("Essential database tables ready (cached)")
                
                # Immediate memory cleanup after database operations
                memory_manager.gentle_cleanup()
                
        except Exception as db_err:
            logger.error(f"Essential database creation failed: {db_err}")
        
        update_initialization_status('minimal_database', 'complete', time.time() - ultra_start_time)
        
        # STEP 3: Register ALL BLUEPRINTS IMMEDIATELY (before any requests)
        logger.info("[INIT] Step 3: Registering all blueprints...")
        update_initialization_status('all_blueprints', 'starting')
        
        try:
            # Register essential blueprints first
            register_absolutely_minimal_blueprints()
            logger.info("Essential blueprints registered (auth + main)")
            
            # Register ALL additional blueprints IMMEDIATELY to prevent timing issues
            register_all_blueprints_safely_before_requests()
            logger.info("All blueprints registered successfully before any requests")
            
        except Exception as bp_err:
            logger.error(f"Blueprint registration failed: {bp_err}")
            try:
                register_emergency_auth_only()
                logger.info("Emergency auth-only registration successful")
            except Exception as fallback_err:
                logger.error(f"Emergency fallback failed: {fallback_err}")
                raise bp_err
        
        update_initialization_status('all_blueprints', 'complete', time.time() - ultra_start_time)
        
        # STEP 4: Initialize responsive UI system
        logger.info("[INIT] Step 4: Initializing responsive UI system...")
        update_initialization_status('responsive_ui', 'starting')
        
        try:
            from app.utils.responsive_ui import responsive_ui
            responsive_ui.memory_threshold_mb = 350  # Lower threshold for Electron
            responsive_ui.start()
            logger.info("Responsive UI system initialized")
        except Exception as ui_err:
            logger.warning(f"Responsive UI initialization failed: {ui_err}")
        
        update_initialization_status('responsive_ui', 'complete', time.time() - ultra_start_time)
        
        # STEP 5: Mark as login-ready IMMEDIATELY
        logger.info("[INIT] Step 5: Marking app as login-ready...")
        _app_initialized = True
        
        # Complete ultra-minimal startup tracking
        ultra_total_duration = time.time() - ultra_start_time
        final_memory = memory_manager.check_memory_usage()
        
        update_initialization_status('ultra_minimal_startup', 'complete', ultra_total_duration)
        _initialization_state['status'] = 'login_ready'
        
        logger.info("=" * 60)
        logger.info(f"LOGIN-READY in {ultra_total_duration:.2f}s")
        logger.info(f"Memory usage: {initial_memory:.1f}MB to {final_memory:.1f}MB")
        logger.info("YAM login page is now accessible!")
        logger.info("Enhanced cache system active for optimal performance")
        logger.info("=" * 60)
        
        # STEP 6: Schedule background components with shorter delay
        logger.info("Scheduling background initialization (30 seconds)...")
        threading.Timer(30.0, start_responsive_background_components).start()
        
    except Exception as e:
        error_duration = time.time() - ultra_start_time
        update_initialization_status('ultra_minimal_startup', 'error', error_duration, e)
        _initialization_state['status'] = 'error'
        logger.error(f"Ultra-minimal startup failed after {error_duration:.2f}s: {e}")
        
        # Emergency fallback
        try:
            logger.info("Attempting emergency absolute minimum initialization...")
            emergency_absolute_minimum_init()
            logger.info("Emergency absolute minimum successful - basic login should work")
        except Exception as emergency_err:
            logger.error(f"Emergency absolute minimum failed: {emergency_err}")
        # CRITICAL: Force app as initialized to allow login even if errors occurred
        _app_initialized = True
        logger.error("[FORCE-READY] Forcing _app_initialized = True to allow login despite errors.")

def register_absolutely_minimal_blueprints():
    """Register ONLY auth and main blueprints - nothing else"""
    global _blueprints_registered
    
    try:
        # Register ONLY auth blueprint for login
        if 'auth' not in current_app.blueprints:
            from app.blueprints.auth import init_auth_blueprint
            init_auth_blueprint(current_app)
            logger.info("Auth blueprint registered")
        
        # Register ONLY main blueprint for index route
        if 'main' not in current_app.blueprints:
            from app.blueprints.main import bp as main_bp
            current_app.register_blueprint(main_bp)
            logger.info("Main blueprint registered")
        
        logger.info("Essential blueprints registration completed (2 blueprints only)")
        
    except Exception as e:
        logger.error(f"Essential blueprint registration failed: {e}")
        raise

def register_all_blueprints_safely_before_requests():
    """Register ALL blueprints BEFORE any requests to prevent timing issues"""
    global _blueprints_registered
    
    if _blueprints_registered:
        logger.info("All blueprints already registered")
        return
    
    try:
        # Register all additional blueprints with minimal memory overhead
        blueprints_to_register = [
            ('api', 'app.blueprints.api', '/api'),
            ('devices', 'app.blueprints.devices', '/devices'),
            ('unified', 'app.blueprints.unified', '/unified'),
            ('workstations', 'app.blueprints.workstations', '/workstations'),
            ('admin_outages', 'app.blueprints.admin_outages', '/admin/outages'),
            ('lab', 'app.blueprints.lab', '/lab'),
            ('team', 'app.blueprints.team', '/team'),
            ('events', 'app.blueprints.events', '/events'),
            ('oralyzer', 'app.blueprints.oralyzer', '/oralyzer'),
            ('kb_api', 'app.blueprints.kb_api', '/api/kb'),
            ('unified_search', 'app.blueprints.unified_search', '/api/search'),
            ('universal_search', 'app.blueprints.universal_search', '/universal-search'),
            ('kb_files', 'app.blueprints.kb_files', '/kb/files'),
            ('kb_shared', 'app.blueprints.kb_shared', '/kb/shared'),
            ('jarvis', 'app.blueprints.jarvis', '/jarvis'),
            ('outages', 'app.blueprints.outages', '/outages'),
            ('patterson', 'app.blueprints.patterson', '/patterson'),
            ('kb', 'app.blueprints.kb', '/kb'),
            ('system', 'app.blueprints.system', '/system'),
            ('collab_notes', 'app.blueprints.collab_notes', '/collab-notes'),
            ('users', 'app.blueprints.users', '/users'),
            ('admin_api', 'app.blueprints.admin_api', '/api/admin'),
            ('settings_api', 'app.blueprints.settings_api', '/api/settings'),
            ('db', 'app.blueprints.db', '/db'),
            ('ai', 'app.blueprints.ai', '/ai'),
            ('modal_api', 'app.blueprints.modal_api', '/api/modals'),
        ]
        
        registered_count = 0
        
        for name, module_path, url_prefix in blueprints_to_register:
            try:
                if name not in current_app.blueprints:
                    # Dynamic import to save memory
                    module = __import__(module_path, fromlist=['bp'])
                    blueprint = getattr(module, 'bp')
                    current_app.register_blueprint(blueprint, url_prefix=url_prefix)
                    registered_count += 1
                    
                    # Gentle memory check every 5 blueprints
                    if registered_count % 5 == 0:
                        memory_manager.check_memory_usage()
                        
            except Exception as e:
                logger.warning(f"Failed to register blueprint {name}: {e}")
                continue
        
        # Register special blueprints that need initialization
        try:
            if 'admin' not in current_app.blueprints:
                from app.blueprints.admin import init_admin_blueprint
                init_admin_blueprint(current_app)
                registered_count += 1
                logger.debug("Admin blueprint registered")
        except Exception as e:
            logger.warning(f"Failed to register admin blueprint: {e}")
            
        try:
            if 'offices' not in current_app.blueprints:
                from app.blueprints.offices import init_offices_blueprint
                init_offices_blueprint(current_app)
                registered_count += 1
                logger.debug("Offices blueprint registered")
        except Exception as e:
            logger.warning(f"Failed to register offices blueprint: {e}")
        
        _blueprints_registered = True
        logger.info(f"All blueprints registered successfully: {registered_count} total")
        
        # Immediate memory cleanup after blueprint registration
        memory_manager.gentle_cleanup()
        
    except Exception as e:
        logger.error(f"Blueprint registration failed: {e}")
        raise

def register_emergency_auth_only():
    """Emergency registration - auth blueprint only"""
    try:
        if 'auth' not in current_app.blueprints:
            from app.blueprints.auth import init_auth_blueprint
            init_auth_blueprint(current_app)
            logger.info("Emergency auth blueprint registered")
        
        # Create minimal index route directly
        @current_app.route('/')
        def emergency_index():
            if current_user.is_authenticated:
                return "<h1>YAM</h1><p>System loading...</p><p><a href='/logout'>Logout</a></p>"
            else:
                return redirect(url_for('auth.login'))
        
        logger.info("Emergency auth-only registration completed")
        
    except Exception as e:
        logger.error(f"Emergency auth-only registration failed: {e}")
        raise

def start_responsive_background_components():
    """Responsive background initialization that doesn't block the UI"""
    logger.info("Starting responsive background component initialization")
    
    def responsive_background_init():
        """Background initialization with responsive UI integration"""
        try:
            # Wait for system to stabilize
            logger.info("Background init: Waiting 10 seconds for system stability...")
            time.sleep(10)
            
            # Import responsive UI system
            try:
                from app.utils.responsive_ui import responsive_ui, responsive_operation
            except ImportError:
                logger.warning("Responsive UI not available, using standard initialization")
                responsive_ui = None
                responsive_operation = None
            
            # Check memory and proceed with caution
            current_memory = memory_manager.check_memory_usage()
            if current_memory > 400:  # If already using > 400MB, be more careful
                logger.warning(f"High memory usage detected ({current_memory:.1f}MB), using gentle initialization")
                time.sleep(10)  # Additional wait
            
            logger.info("Background init: Beginning responsive component initialization...")
            
            with current_app.app_context():
                # Use enhanced cache for all background operations
                from app.utils.enhanced_cache import enhanced_cache
                
                # Step 1: Initialize search system with responsiveness
                try:
                    if responsive_operation:
                        with responsive_operation(name="search_system_init") as ctx:
                            init_cached_search_system()
                            ctx.yield_if_needed()
                    else:
                        init_cached_search_system()
                    logger.info("Search system initialized (responsive)")
                except Exception as e:
                    logger.warning(f"Search system initialization failed: {e}")
                
                # Step 2: Initialize remaining database tables
                try:
                    if responsive_operation:
                        with responsive_operation(name="remaining_tables_init") as ctx:
                            init_cached_remaining_tables()
                            ctx.yield_if_needed()
                    else:
                        init_cached_remaining_tables()
                    logger.info("Remaining database tables created (responsive)")
                except Exception as e:
                    logger.warning(f"Database tables creation failed: {e}")
                
                # Step 3: Initialize cache warming
                try:
                    if responsive_operation:
                        with responsive_operation(name="cache_warming_init") as ctx:
                            init_cached_cache_warming()
                            ctx.yield_if_needed()
                    else:
                        init_cached_cache_warming()
                    logger.info("Cache warming initialized (responsive)")
                except Exception as e:
                    logger.warning(f"Cache warming initialization failed: {e}")
                
                # Step 4: Initialize knowledge base cache
                try:
                    init_knowledge_base_cache()
                    logger.info("Knowledge base cache initialized (responsive)")
                except Exception as e:
                    logger.warning(f"Knowledge base cache initialization failed: {e}")
                
                # Step 5: Initialize background tasks
                try:
                    if responsive_operation:
                        with responsive_operation(name="background_tasks_init") as ctx:
                            init_background_tasks()
                            ctx.yield_if_needed()
                    else:
                        init_background_tasks()
                    logger.info("Background tasks initialized (responsive)")
                except Exception as e:
                    logger.warning(f"Background tasks initialization failed: {e}")
                
                # Mark as fully complete
                _initialization_state['status'] = 'full_complete'
                logger.info("Responsive background initialization completed successfully")
                
                # Final memory check and gentle cleanup
                final_memory = memory_manager.check_memory_usage()
                logger.info(f"Final background memory usage: {final_memory:.1f}MB")
                memory_manager.gentle_cleanup()
                
        except Exception as e:
            logger.error(f"Responsive background initialization failed: {e}")
            _initialization_state['status'] = 'partial_complete'
            # Gentle cleanup on error
            memory_manager.gentle_cleanup()
    
    # Start in a separate thread with normal priority
    bg_thread = threading.Thread(target=responsive_background_init, daemon=True, name="ResponsiveBackgroundInit")
    bg_thread.start()
    logger.info("Responsive background initialization thread started")

def init_cached_search_system():
    """Initialize search system with enhanced caching"""
    try:
        from app.utils.enhanced_cache import enhanced_cache
        from app.utils.responsive_ui import responsive_operation
        
        # Check cache first
        cache_key = "search_system_initialized"
        if enhanced_cache.get(cache_key):
            logger.info("Search system already initialized (cached)")
            return
        
        # Use responsive operation for search system initialization
        with responsive_operation(name="search_system_init") as ctx:
            from app.utils.search import init_search_table
            init_search_table()
            
            # Yield control during initialization
            ctx.yield_if_needed()
        
        # Cache the initialization status
        enhanced_cache.set(cache_key, True, ttl=3600)
        logger.info("Search system initialized with caching")
        
    except Exception as e:
        logger.warning(f"Cached search system initialization failed: {e}")

def init_cached_remaining_tables():
    """Initialize remaining database tables with caching"""
    try:
        from app.utils.enhanced_cache import enhanced_cache
        from app.utils.responsive_ui import responsive_operation
        
        # Check cache first
        cache_key = "remaining_tables_created"
        if enhanced_cache.get(cache_key):
            logger.info("Remaining tables already created (cached)")
            return
        
        # Use responsive operation for table creation
        with responsive_operation(name="remaining_tables_init") as ctx:
            # Create remaining tables that weren't created in minimal startup
            db.create_all()
            
            # Yield control during creation
            ctx.yield_if_needed()
        
        # Cache the creation status
        enhanced_cache.set(cache_key, True, ttl=3600)
        logger.info("Remaining database tables created with caching")
        
    except Exception as e:
        logger.warning(f"Cached remaining tables creation failed: {e}")

def init_cached_cache_warming():
    """Initialize cache warming with enhanced caching integration"""
    try:
        from app.utils.responsive_ui import responsive_operation
        
        # Use responsive operation for cache warming
        with responsive_operation(name="cache_warming_init") as ctx:
            from app.utils.cache_warming import start_cache_warming
            start_cache_warming()
            
            # Yield control during warming
            ctx.yield_if_needed()
            
        logger.info("Cached cache warming system initialized")
    except Exception as e:
        logger.warning(f"Cached cache warming initialization failed: {e}")

def init_knowledge_base_cache():
    """Initialize knowledge base cache during background startup"""
    try:
        from app.utils.responsive_ui import responsive_operation
        
        # Use responsive operation for KB cache loading
        with responsive_operation(name="kb_cache_init") as ctx:
            # Import and load docs (only if startup import hasn't been done)
            try:
                from app.utils.kb_import import import_docs_folder_startup, check_for_new_documents
                # Only import if there are new documents or startup hasn't been completed
                if check_for_new_documents():
                    import_docs_folder_startup()
                    logger.info("New documents imported during background initialization")
                else:
                    logger.info("No new documents detected, skipping import")
            except Exception as exc:  
                logger.error("Failed to import docs folder: %s", exc)
            
            # Yield control between operations
            ctx.yield_if_needed()
            
            # Load articles cache
            try:
                from app.utils.cache import load_articles_cache
                load_articles_cache(force_reload=True)
                logger.info("Articles cache loaded during background initialization")
            except Exception as cache_err:
                logger.error("Failed to load articles cache: %s", cache_err)
            
            # Yield control again
            ctx.yield_if_needed()
            
        logger.info("Knowledge base cache initialization completed")
    except Exception as e:
        logger.warning(f"Knowledge base cache initialization failed: {e}")

def init_background_tasks():
    """Initialize background tasks with enhanced caching"""
    try:
        from app.utils.responsive_ui import responsive_operation
        
        # Use responsive operation for background tasks
        with responsive_operation(name="background_tasks_init") as ctx:
            init_background_tasks()
            
            # Yield control during initialization
            ctx.yield_if_needed()
            
        logger.info("Cached background tasks initialized")
    except Exception as e:
        logger.warning(f"Cached background tasks initialization failed: {e}")

def emergency_absolute_minimum_init():
    """Absolute minimum initialization for emergency fallback."""
    try:
        # Just ensure database exists and create emergency routes
        with current_app.app_context():
            db.create_all()
            
        # Create absolute minimum route
        @current_app.route('/emergency')
        def emergency():
            return "YAM Emergency Mode - System Starting"
            
        logger.info("Emergency absolute minimum initialization completed")
        
    except Exception as e:
        logger.error(f"Emergency absolute minimum failed: {e}")
        raise

def cleanup():
    """Cleanup function to be called on shutdown"""
    try:
        # Stop the optimized index manager
        from app.utils.optimized_index_manager import optimized_index_manager
        if hasattr(optimized_index_manager, 'stop'):
            optimized_index_manager.stop()
        
        # Stop background threads gracefully
        try:
            import threading
            for thread in threading.enumerate():
                if thread != threading.current_thread() and hasattr(thread, 'daemon') and thread.daemon:
                    # Only try to join threads that are actually started
                    if thread.is_alive():
                        try:
                            thread.join(timeout=1.0)  # Give threads 1 second to finish
                        except Exception as thread_err:
                            logger.warning(f"Could not join thread {thread.name}: {thread_err}")
        except Exception as thread_cleanup_err:
            logger.warning(f"Error during thread cleanup: {thread_cleanup_err}")
        
        with current_app.app_context():
            try:
                db.session.remove()
                logger.info("Database session cleaned up")
            except Exception as db_err:
                logger.warning(f"Error cleaning up database session: {db_err}")
            
            logger.info("Cleaning up resources...")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def init_background_tasks():
    """Initialize background tasks with proper resource management to prevent memory leaks"""
    try:
        import threading
        import gc
        
        # Clean up any existing background threads first
        existing_threads = [t for t in threading.enumerate() if 'status_emitter' in t.name.lower() or 'backgroundstatus' in t.name.lower()]
        
        if len(existing_threads) > 1:
            logger.warning(f"Multiple background status threads detected ({len(existing_threads)}), this could cause memory leaks")
        
        if not existing_threads:
            # Start background status emitter with memory management
            def memory_safe_status_emitter():
                """Memory-safe wrapper for status emitter"""
                try:
                    # Import here to avoid circular imports
                    from app.utils.status_emitter import background_status_emitter
                    background_status_emitter()
                except Exception as e:
                    logger.error(f"Background status emitter failed: {e}")
                finally:
                    # Force garbage collection when thread ends
                    gc.collect()
            
            status_thread = threading.Thread(target=memory_safe_status_emitter, daemon=True, name="BackgroundStatusEmitter")
            status_thread.start()
            logger.info("Memory-safe background status emitter started")
        else:
            logger.info(f"Background status emitter already running ({len(existing_threads)} threads)")
        
        # Force garbage collection to clean up any leaked objects
        gc.collect()
        
    except Exception as e:
        logger.error(f"Failed to start background tasks: {e}")
        # Don't fail the entire application if background tasks fail
        pass 