import os
import time
import logging
from flask import jsonify, request, render_template_string, current_app
from flask_login import login_required, current_user
from sqlalchemy import text
from . import bp
from extensions import db
from app.shared_state import memory_manager, _initialization_state, _app_initialized, _blueprints_registered

logger = logging.getLogger(__name__)

@bp.route('/login-ready')
def login_ready_check():
    """Check if login functionality is truly ready and accessible."""
    try:
        # Always return ready as soon as _app_initialized is True
        if _app_initialized:
            return jsonify({
                'ready': True,
                'status': 'login_ready',
                'message': 'Login page is ready',
                'timestamp': time.time()
            })
        # Fallback to legacy checks if not initialized
        from flask import current_app
        auth_ready = 'auth' in current_app.blueprints
        db_ready = False
        try:
            with current_app.app_context():
                from app.models import User
                User.query.first()
                db_ready = True
        except Exception:
            pass
        login_route_ready = False
        try:
            for rule in current_app.url_map.iter_rules():
                if rule.endpoint == 'auth.login':
                    login_route_ready = True
                    break
        except Exception:
            pass
        login_ready = auth_ready and db_ready and login_route_ready
        if login_ready:
            return jsonify({
                'ready': True,
                'status': 'login_ready',
                'message': 'Login page is ready',
                'timestamp': time.time()
            })
        else:
            return jsonify({
                'ready': False,
                'status': 'initializing',
                'auth_blueprint': auth_ready,
                'database': db_ready,
                'login_route': login_route_ready,
                'message': 'Login not yet ready',
                'timestamp': time.time()
            }), 503  # Service Unavailable
    except Exception as e:
        return jsonify({
            'ready': False,
            'status': 'error',
            'error': str(e),
            'message': 'Error checking login readiness',
            'timestamp': time.time()
        }), 500

@bp.route('/quick-status')
def quick_status():
    """Ultra-fast status check for Electron health monitoring."""
    # Always return ready as soon as _app_initialized is True
    if _app_initialized:
        return jsonify({
            'status': 'ok',
            'ready': True,
            'timestamp': time.time(),
            'login_available': 'auth' in current_app.blueprints
        })
    return jsonify({
        'status': 'initializing',
        'ready': False,
        'timestamp': time.time(),
        'login_available': 'auth' in current_app.blueprints
    })

@bp.route('/performance-status')
def performance_status():
    """Performance metrics for Electron adaptive behavior."""
    try:
        import psutil
        
        # Calculate safe performance metrics
        try:
            memory = psutil.virtual_memory()
            cpu_count = psutil.cpu_count() or 4
            
            # Safe calculations to prevent NaN/undefined
            memory_gb = (memory.total / (1024**3)) if memory and memory.total > 0 else 8.0
            available_gb = (memory.available / (1024**3)) if memory and memory.available > 0 else 4.0
            memory_percent = memory.percent if memory and hasattr(memory, 'percent') else 50.0
            
            # Calculate performance score safely
            memory_score = min(2.0, max(0.1, available_gb / 4.0))
            cpu_score = min(2.0, max(0.1, cpu_count / 4.0))
            performance_score = (memory_score + cpu_score) / 2
            
            # Ensure all values are valid numbers
            performance_score = performance_score if isinstance(performance_score, (int, float)) and performance_score > 0 else 1.0
            timeout_multiplier = max(0.5, min(2.0, 1.0 / performance_score)) if performance_score > 0 else 1.0
            
            return jsonify({
                'status': 'ok',
                'timestamp': time.time(),
                'system': {
                    'cpu_count': cpu_count,
                    'memory_total_gb': round(memory_gb, 1),
                    'memory_available_gb': round(available_gb, 1),
                    'memory_percent': round(memory_percent, 1)
                },
                'performance': {
                    'score': round(performance_score, 2),
                    'timeout_multiplier': round(timeout_multiplier, 2),
                    'memory_score': round(memory_score, 2),
                    'cpu_score': round(cpu_score, 2)
                },
                'adaptive_timeouts': {
                    'flask_startup': int(75000 * timeout_multiplier),
                    'window_load': int(30000 * timeout_multiplier),
                    'responsiveness_check': int(10000 * timeout_multiplier),
                    'health_check': int(15000 * timeout_multiplier)
                },
                'app_status': {
                    'initialized': _app_initialized,
                    'blueprints_registered': _blueprints_registered,
                    'initialization_state': _initialization_state.get('status', 'unknown')
                }
            })
            
        except Exception as metrics_err:
            logger.warning(f"Failed to get detailed metrics: {metrics_err}")
            # Return safe defaults
            return jsonify({
                'status': 'ok',
                'timestamp': time.time(),
                'system': {
                    'cpu_count': 4,
                    'memory_total_gb': 8.0,
                    'memory_available_gb': 4.0,
                    'memory_percent': 50.0
                },
                'performance': {
                    'score': 1.0,
                    'timeout_multiplier': 1.0,
                    'memory_score': 1.0,
                    'cpu_score': 1.0
                },
                'adaptive_timeouts': {
                    'flask_startup': 75000,
                    'window_load': 30000,
                    'responsiveness_check': 10000,
                    'health_check': 15000
                },
                'app_status': {
                    'initialized': _app_initialized,
                    'blueprints_registered': _blueprints_registered,
                    'initialization_state': _initialization_state.get('status', 'unknown')
                }
            })
            
    except Exception as e:
        logger.error(f"Performance status endpoint failed: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': time.time(),
            'error': str(e),
            'performance': {
                'score': 1.0,
                'timeout_multiplier': 1.0
            }
        }), 500

@bp.route('/health')
def health_check():
    """Simple health check endpoint for debugging"""
    try:
        # Check database connectivity
        with current_app.app_context():
            db.session.execute(text('SELECT 1'))
        
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    # Check initialization status
    init_status = _initialization_state.get('status', 'unknown')
    
    return jsonify({
        'status': 'ok' if db_status == 'connected' else 'partial',
        'message': 'YAM application health check',
        'electron_mode': os.getenv('ELECTRON_MODE') == '1',
        'database': db_status,
        'initialization': init_status,
        'app_initialized': _app_initialized,
        'blueprints_registered': _blueprints_registered,
        'uptime_seconds': time.time() - _initialization_state.get('start_time', time.time())
    })

@bp.route('/startup-health')
def startup_health_check():
    """Enhanced health check for Electron startup verification"""
    try:
        current_memory = memory_manager.check_memory_usage()
        
        # Check if essential components are ready
        auth_ready = 'auth' in current_app.blueprints
        db_ready = False
        login_route_ready = False
        
        # Test database connectivity
        try:
            with current_app.app_context():
                db.session.execute(text('SELECT 1'))
                db_ready = True
        except Exception:
            pass
            
        # Check if login route exists and is accessible
        try:
            for rule in current_app.url_map.iter_rules():
                if rule.endpoint == 'auth.login':
                    login_route_ready = True
                    break
        except Exception:
            pass
        
        # Overall readiness assessment
        login_functional = auth_ready and db_ready and login_route_ready
        
        # Server performance assessment
        performance_score = 1.0
        if current_memory > 0:
            if current_memory < 300:
                performance_score = 2.0  # Excellent
            elif current_memory < 500:
                performance_score = 1.5  # Good
            elif current_memory < 750:
                performance_score = 1.0  # Fair
            else:
                performance_score = 0.5  # Poor
        
        status = 'ready' if login_functional else 'initializing'
        http_code = 200 if login_functional else 503
        
        response_data = {
            'status': status,
            'login_functional': login_functional,
            'memory_mb': current_memory,
            'performance_score': performance_score,
            'components': {
                'auth_blueprint': auth_ready,
                'database': db_ready,
                'login_route': login_route_ready,
                'app_initialized': _app_initialized,
                'blueprints_registered': _blueprints_registered
            },
            'initialization': {
                'status': _initialization_state.get('status', 'unknown'),
                'elapsed_seconds': time.time() - _initialization_state.get('start_time', time.time())
            },
            'recommendations': []
        }
        
        # Add performance recommendations
        if current_memory > 600:
            response_data['recommendations'].append('High memory usage detected - consider restarting if performance degrades')
        if not login_functional:
            response_data['recommendations'].append('Login not yet ready - please wait for initialization to complete')
        if performance_score < 1.0:
            response_data['recommendations'].append('System under load - startup may take longer than usual')
            
        return jsonify(response_data), http_code
        
    except Exception as e:
        # Fallback response even if health check fails
        return jsonify({
            'status': 'error',
            'error': str(e),
            'login_functional': False,
            'message': 'Health check failed - server may be starting up',
            'recommendations': ['Retry in a few seconds', 'Check server logs for errors']
        }), 500

@bp.route('/status')
def detailed_status():
    """Detailed status endpoint for debugging startup issues"""
    try:
        return jsonify({
            'application': {
                'name': 'YAM',
                'mode': 'electron' if os.getenv('ELECTRON_MODE') == '1' else 'standalone',
                'initialized': _app_initialized,
                'blueprints_registered': _blueprints_registered
            },
            'initialization': _initialization_state,
            'system': _initialization_state.get('performance_metrics', {}).get('system_info', {}),
            'blueprints': list(current_app.blueprints.keys()),
            'environment': {
                'ELECTRON_MODE': os.getenv('ELECTRON_MODE'),
                'FLASK_PORT': os.getenv('FLASK_PORT'),
                'python_version': sys.version.split()[0]
            }
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@bp.route('/quick-login-check')
def quick_login_check():
    """Quick check to see if login functionality is available"""
    try:
        # Check if auth blueprint is registered
        auth_available = 'auth' in current_app.blueprints
        
        # Check if database has User table
        user_table_exists = False
        try:
            from app.models import User
            User.query.first()
            user_table_exists = True
        except Exception:
            pass
        
        login_ready = auth_available and user_table_exists
        
        return jsonify({
            'login_ready': login_ready,
            'auth_blueprint': auth_available,
            'user_table': user_table_exists,
            'message': 'Login is ready' if login_ready else 'Login not yet available'
        })
        
    except Exception as e:
        return jsonify({
            'login_ready': False,
            'error': str(e),
            'message': 'Error checking login status'
        }), 500

@bp.route('/api/initialization/status')
def initialization_status():
    """Get current initialization status and performance metrics"""
    try:
        # Add real-time metrics
        current_metrics = None
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            # Get system info
            system_memory = psutil.virtual_memory()
            system_cpu = psutil.cpu_percent(interval=0.1)
            
            current_metrics = {
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
        except Exception:
            pass
        
        status = _initialization_state.copy()
        if current_metrics:
            status['current_metrics'] = current_metrics
        
        # Calculate overall progress
        total_components = len(status['components'])
        completed_components = sum(1 for comp in status['components'].values() 
                                 if comp['status'] in ['complete', 'success'])
        
        status['progress'] = {
            'total': total_components,
            'completed': completed_components,
            'percentage': (completed_components / total_components * 100) if total_components > 0 else 0
        }
        
        # Add timing information
        elapsed_time = time.time() - status['start_time']
        status['elapsed_time'] = elapsed_time
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'message': 'Failed to get initialization status'
        }), 500

@bp.route('/scan')
def scan_page():
    return render_template('scan.html')

@bp.route('/emergency')
def emergency():
    return "YAM Emergency Mode - System Starting" 