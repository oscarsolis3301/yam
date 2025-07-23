import os
import csv
import threading
from datetime import datetime
from flask import current_app
import logging

from . import bp  # Import the shared blueprint instance
from app.utils.device import get_devices_csv_path  # Unified path helper
from extensions import db

# In-memory device cache
_devices_cache = []
_devices_cache_mtime = None
_devices_cache_path = None
_devices_cache_lock = threading.Lock()

logger = logging.getLogger(__name__)

def load_devices_cache(force_reload=False):
    global _devices_cache, _devices_cache_mtime, _devices_cache_path
    path = get_devices_csv_path()
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None
    with _devices_cache_lock:
        if (not force_reload and _devices_cache and _devices_cache_path == path and _devices_cache_mtime == mtime):
            return _devices_cache
        try:
            with open(path, newline='', encoding='utf-8') as f:
                _devices_cache = list(csv.DictReader(f))
            _devices_cache_mtime = mtime
            _devices_cache_path = path
        except Exception as e:
            print(f"[DeviceCache] Failed to load devices: {e}")
            _devices_cache = []
    return _devices_cache

@bp.route('/cache/reload', methods=['POST'])
def reload_cache():
    """Force reload the devices cache"""
    load_devices_cache(force_reload=True)
    return {'status': 'success', 'message': 'Cache reloaded'}

@bp.route('/cache/status', methods=['GET'])
def cache_status():
    """Get the current status of the devices cache"""
    return {
        'cache_size': len(_devices_cache),
        'last_modified': _devices_cache_mtime,
        'cache_path': _devices_cache_path
    } 