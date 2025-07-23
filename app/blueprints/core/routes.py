import os
import time
import logging
import pandas as pd
from pathlib import Path
from flask import render_template_string, redirect, url_for, jsonify, request, current_app
from flask_login import current_user
from . import bp
from app.shared_state import _app_initialized, _initialization_state, memory_manager

logger = logging.getLogger(__name__)

def _load_offices_dataframe():
    """Return a pandas DataFrame with office metadata.

    Tries to locate a CSV inside the *Offices/* directory.  If no CSV file is
    found or loading fails, returns an **empty** DataFrame with the expected
    columns so downstream code does not raise ``NameError``/``KeyError``.
    """
    expected_cols = [
        'Internal Name', 'Location', 'Phone', 'Address', 'Operations Manager',
        'Mnemonic', 'IP', 'Number'
    ]

    offices_dir = Path('Offices')
    if offices_dir.exists():
        for csv_path in offices_dir.glob('*.csv'):
            try:
                df_tmp = pd.read_csv(csv_path)
                # Ensure all expected columns exist; fill missing with "".
                for col in expected_cols:
                    if col not in df_tmp.columns:
                        df_tmp[col] = ''
                return df_tmp
            except Exception as exc:
                logger.warning(f"Failed to load offices CSV {csv_path}: {exc}")
    # Fallback – empty DataFrame with expected columns
    return pd.DataFrame(columns=expected_cols)

df = _load_offices_dataframe()

@bp.route('/status')
def status():
    """Status page for system health monitoring"""
    try:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>YAM - System Status</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
                .status { background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .loading { color: #007bff; }
                .ready { color: #28a745; }
                .error { color: #dc3545; }
            </style>
        </head>
        <body>
            <h1>YAM System Status</h1>
            <div class="status">
                <h2>System Status</h2>
                <p>Status: {{ status }}</p>
                <p>Initialized: {{ initialized }}</p>
                <p>Auth Blueprint: {{ auth_ready }}</p>
            </div>
            <div>
                <p><a href="/health">Health Check</a> | <a href="/">Go to Home</a></p>
            </div>
        </body>
        </html>
        """, 
        status=_initialization_state.get('status', 'unknown'), 
        initialized=_app_initialized,
        auth_ready='auth' in current_app.blueprints)
    except Exception as e:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>YAM - Error</title>
            <style>body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }</style>
        </head>
        <body>
            <h1>YAM Application Error</h1>
            <p>An error occurred during startup: {{ error }}</p>
            <p><a href="/health">Health Check</a></p>
        </body>
        </html>
        """, error=str(e))

@bp.route('/api/ui/responsiveness')
def ui_responsiveness_status():
    """Get UI responsiveness status for debugging"""
    try:
        from app.utils.responsive_ui import get_ui_responsiveness_status
        
        status = get_ui_responsiveness_status()
        
        # Add additional memory information
        try:
            import psutil
            memory = psutil.virtual_memory()
            status['system_memory'] = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'percent_used': round(memory.percent, 2)
            }
        except Exception:
            pass
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'responsive_ui_active': False
        }), 500

@bp.route('/api/ui/force-cleanup', methods=['POST'])
def force_ui_cleanup():
    """Force UI cleanup for admin users"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        # Force memory cleanup
        memory_manager.force_cleanup()
        
        # Force responsive UI cleanup
        try:
            from app.utils.responsive_ui import responsive_ui
            if responsive_ui._check_memory_pressure():
                responsive_ui._handle_memory_pressure()
        except Exception as ui_err:
            logger.warning(f"Responsive UI cleanup failed: {ui_err}")
        
        logger.info(f"Force UI cleanup triggered by admin user {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'UI cleanup completed',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Force UI cleanup failed: {e}")
        return jsonify({
            'error': str(e),
            'message': 'UI cleanup failed'
        }), 500 