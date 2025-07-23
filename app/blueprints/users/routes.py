from flask import jsonify, request, render_template
from flask_login import login_required, current_user
from . import bp
from extensions import db
from app.models import User, UserCache
import logging
import subprocess
import json
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the shared, persistent cache database
CACHE_DB_PATH = Path(__file__).resolve().parents[2] / 'app' / 'db' / 'clock_id_cache.db'
CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Ensure the cache table exists
with sqlite3.connect(CACHE_DB_PATH) as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clock_id TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            email TEXT,
            job_title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

def get_cache_entry(clock_id):
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cur = conn.execute("SELECT clock_id, first_name, last_name, username, email, job_title FROM user_cache WHERE clock_id = ?", (clock_id.lstrip('0'),))
        row = cur.fetchone()
        if row:
            return dict(zip(['clock_id', 'first_name', 'last_name', 'username', 'email', 'job_title'], row))
        return None

def insert_cache_entry(clock_id, first_name, last_name, username, email, job_title):
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO user_cache (clock_id, first_name, last_name, username, email, job_title)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (clock_id.lstrip('0'), first_name, last_name, username, email, job_title))
        conn.commit()

@bp.route('/')
@login_required
def users():
    """Render the users page"""
    # Render the new single-page user interface
    return render_template('users1.html')

@bp.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Get a specific user"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update a user"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        for key, value in data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user"""
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/users/search', methods=['GET'])
@login_required
def search_users():
    """Search users"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify([])
            
        users = User.query.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%'))
        ).all()
        
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/users/online', methods=['GET'])
@login_required
def get_online_users():
    """Get list of online users with presence information"""
    try:
        from app.services.user_presence import UserPresenceService
        
        # Create a temporary presence service instance
        presence_service = UserPresenceService()
        
        # Get online users with details
        users_list = presence_service.get_online_users(include_details=True)
        presence_stats = presence_service.get_presence_stats()
        
        response_data = {
            "users": users_list,
            "stats": {
                "total_online": presence_stats.get('online_users', 0),
                "total_users": presence_stats.get('total_users', 0),
                "last_cleanup": presence_stats.get('last_cleanup', datetime.utcnow().isoformat())
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.debug(f"API: Sent online users list: {len(users_list)} users")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting online users via API: {e}")
        return jsonify({'error': 'Error loading online users'}), 500

@bp.route('/api/users/session-health', methods=['GET'])
@login_required
def get_session_health():
    """Check session health and return status"""
    try:
        from app.services.user_presence import UserPresenceService
        
        # Create a temporary presence service instance
        presence_service = UserPresenceService()
        
        # Get current user's status
        user_status = presence_service.get_user_status(current_user.id) if current_user.is_authenticated else None
        
        # Get presence stats
        presence_stats = presence_service.get_presence_stats()
        
        response_data = {
            "user_id": current_user.id if current_user.is_authenticated else None,
            "username": current_user.username if current_user.is_authenticated else None,
            "session_active": True,
            "last_activity": datetime.utcnow().isoformat(),
            "presence_stats": presence_stats,
            "user_status": user_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.debug(f"API: Session health check for user {current_user.id if current_user.is_authenticated else 'anonymous'}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error checking session health: {e}")
        return jsonify({'error': 'Error checking session health'}), 500

@bp.route('/api/users/<int:user_id>/heartbeat', methods=['POST'])
@login_required
def update_user_heartbeat(user_id):
    """Update user's heartbeat to mark them as online"""
    try:
        # Check if user is updating their own heartbeat or is admin
        if current_user.id != user_id and not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Unauthorized'}), 403
        
        from app.services.user_presence import UserPresenceService
        
        # Create a temporary presence service instance
        presence_service = UserPresenceService()
        
        # Update the user's heartbeat
        success = presence_service.update_heartbeat(user_id)
        
        if success:
            # Get updated user status
            user_status = presence_service.get_user_status(user_id)
            
            response_data = {
                "success": True,
                "message": f"User {user_id} heartbeat updated",
                "user_status": user_status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.debug(f"API: Updated heartbeat for user {user_id}")
            return jsonify(response_data)
        else:
            return jsonify({'error': 'Failed to update heartbeat'}), 500
        
    except Exception as e:
        logger.error(f"Error updating user heartbeat: {e}")
        return jsonify({'error': 'Error updating heartbeat'}), 500

@bp.route('', methods=['POST'])
@login_required
def powershell_user_lookup():
    """AD/Okta user lookup via PowerShell.

    Always returns a **structured** JSON payload so the front-end can
    differentiate between *transport-level* errors (HTTP 4xx/5xx) and
    *lookup* failures (\"success": false).
    """

    data = request.get_json(silent=True) or {}
    query = str(data.get('user', '')).strip()

    if not query:
        return jsonify({'success': False, 'error': 'No user provided.'}), 200

    # Very naive input sanitation – keep valid digits / letters only.
    if any(ch in query for ch in [';', '&', '|', '<', '>']):
        return jsonify({'success': False, 'error': 'Invalid characters in input.'}), 200

    # --- Locate the PowerShell script (works regardless of CWD) ---
    from pathlib import Path
    script_path = Path(__file__).resolve().parents[3] / 'scripts' / 'user_lookup.ps1'

    if not script_path.exists():
        logger.error('PowerShell lookup script missing: %s', script_path)
        return jsonify({'success': False, 'error': 'Lookup script not found on server.'}), 200

    try:
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(script_path), query
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        stdout = (result.stdout or '').strip()
        stderr = (result.stderr or '').strip()

        if result.returncode != 0:
            logger.warning('PowerShell lookup non-zero exit (code=%s) – stderr: %s', result.returncode, stderr)

        if not stdout:
            # Treat as *not found* but not a server error.
            return jsonify({'success': False, 'error': 'User not found.'}), 200

        try:
            data_json = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.error('JSON parsing failed for PowerShell output: %s | stderr: %s', stdout[:500], stderr)
            return jsonify({'success': False, 'error': 'Malformed response from lookup script.'}), 200

        if not isinstance(data_json, dict) or len(data_json) == 0:
            return jsonify({'success': False, 'error': 'User not found.'}), 200

        # --------------------------------------------------
        # Cache **stable** attributes for faster future hits
        # --------------------------------------------------
        try:
            clock_id = str(data_json.get('ClockID', query)).lstrip('0')
            if clock_id:
                cached = get_cache_entry(clock_id)
                if not cached:
                    full_name = data_json.get('FullName') or ''
                    first_name, last_name = '', ''
                    if full_name:
                        parts = full_name.strip().split()
                        first_name = parts[0]
                        last_name = parts[-1] if len(parts) > 1 else ''

                    insert_cache_entry(
                        clock_id,
                        first_name,
                        last_name,
                        data_json.get('Username'),
                        data_json.get('Email'),
                        data_json.get('Title'),
                    )
        except Exception as cache_err:
            logger.warning('UserCache insert failed: %s', cache_err)

        # Successful lookup
        payload = {'success': True, 'user': data_json}
        payload.update(data_json)  # keep backward-compat plain fields
        return jsonify(payload), 200

    except subprocess.TimeoutExpired:
        logger.error('PowerShell lookup timed out for query %s', query)
        return jsonify({'success': False, 'error': 'Lookup timed out.'}), 200
    except Exception as exc:
        logger.exception('Unhandled server error during PowerShell lookup')
        return jsonify({'success': False, 'error': 'Internal server error.'}), 200

# -------------------------------------------------------------
#            Lightweight UserCache API Endpoints
# -------------------------------------------------------------

@bp.route('/cache/<clock_id>', methods=['GET'])
@login_required
def get_user_cache(clock_id):
    """Fast, persistent cache endpoint using dedicated SQLite DB."""
    try:
        entry = get_cache_entry(clock_id)
        if entry:
            payload = {'success': True}
            payload.update(entry)
            return jsonify(payload), 200
        # If not in cache, try to populate it from AD
        try:
            script_path = Path(__file__).resolve().parents[3] / 'scripts' / 'user_lookup.ps1'
            if script_path.exists():
                import subprocess
                import json
                cmd = [
                    'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                    '-File', str(script_path), clock_id
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        data_json = json.loads(result.stdout.strip())
                        if isinstance(data_json, dict) and len(data_json) > 0:
                            full_name = data_json.get('FullName') or ''
                            first_name, last_name = '', ''
                            if full_name:
                                parts = full_name.strip().split()
                                first_name = parts[0]
                                last_name = parts[-1] if len(parts) > 1 else ''
                            insert_cache_entry(
                                clock_id.lstrip('0'),
                                first_name,
                                last_name,
                                data_json.get('Username'),
                                data_json.get('Email'),
                                data_json.get('Title'),
                            )
                            entry = get_cache_entry(clock_id)
                            payload = {'success': True}
                            payload.update(entry)
                            return jsonify(payload), 200
                    except Exception as e:
                        logger.warning(f'Failed to parse/cache user data for {clock_id}: {e}')
        except Exception as e:
            logger.warning(f'Failed to populate cache for {clock_id}: {e}')
        return jsonify({'success': False, 'error': 'User not found in cache.'}), 200
    except Exception as e:
        logger.error('UserCache lookup error: %s', e)
        return jsonify({'success': False, 'error': 'Cache lookup failure.'}), 200

# Optional endpoint to add new cache entries manually (admin-only)
@bp.route('/cache', methods=['POST'])
@login_required
def add_user_cache():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    required = {'clock_id', 'first_name', 'last_name', 'username', 'email'}
    if not required.issubset(data.keys()):
        return jsonify({'error': f'Missing required fields: {required - data.keys()}'}), 400

    try:
        existing = get_cache_entry(str(data['clock_id']).lstrip('0'))
        if existing:
            return jsonify({'message': 'Entry already exists.'}), 200

        insert_cache_entry(
            str(data['clock_id']).lstrip('0'),
            data.get('first_name'),
            data.get('last_name'),
            data.get('username'),
            data.get('email'),
            data.get('job_title'),
        )
        return jsonify({'success': True}), 201
    except Exception as e:
        logger.error(f"UserCache insert error: {e}")
        return jsonify({'error': 'Failed to insert cache entry.'}), 500

@bp.route('/cache/stats', methods=['GET'])
@login_required
def get_cache_stats():
    """Get cache statistics for monitoring."""
    try:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            total_entries = conn.execute("SELECT COUNT(*) FROM user_cache").fetchone()[0]
            recent_entries = conn.execute("""
                SELECT COUNT(*) FROM user_cache WHERE created_at >= datetime('now', '-7 days')
            """).fetchone()[0]
        
        return jsonify({
            'success': True,
            'total_entries': total_entries,
            'recent_entries': recent_entries,
            'cache_size_mb': total_entries * 0.001  # Rough estimate
        }), 200
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return jsonify({'error': 'Failed to get cache stats.'}), 500

@bp.route('/cache/populate', methods=['POST'])
@login_required
def populate_cache():
    """Populate cache with frequently searched clock IDs (admin-only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    clock_ids = data.get('clock_ids', [])
    
    if not clock_ids:
        return jsonify({'error': 'No clock IDs provided'}), 400

    results = {'success': [], 'failed': [], 'existing': []}
    
    for clock_id in clock_ids:
        try:
            # Check if already cached
            normalized_id = str(clock_id).lstrip('0')
            existing = get_cache_entry(normalized_id)
            if existing:
                results['existing'].append(clock_id)
                continue

            # Perform AD lookup
            from pathlib import Path
            script_path = Path(__file__).resolve().parents[3] / 'scripts' / 'user_lookup.ps1'
            
            if not script_path.exists():
                results['failed'].append({'clock_id': clock_id, 'error': 'Lookup script not found'})
                continue

            import subprocess
            import json
            
            cmd = [
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', str(script_path), str(clock_id)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data_json = json.loads(result.stdout.strip())
                    if isinstance(data_json, dict) and len(data_json) > 0:
                        # Extract and cache user data
                        full_name = data_json.get('FullName') or ''
                        first_name, last_name = '', ''
                        if full_name:
                            parts = full_name.strip().split()
                            first_name = parts[0]
                            last_name = parts[-1] if len(parts) > 1 else ''

                        insert_cache_entry(
                            normalized_id,
                            first_name,
                            last_name,
                            data_json.get('Username'),
                            data_json.get('Email'),
                            data_json.get('Title'),
                        )
                        results['success'].append(clock_id)
                    else:
                        results['failed'].append({'clock_id': clock_id, 'error': 'User not found'})
                except (json.JSONDecodeError, Exception) as e:
                    results['failed'].append({'clock_id': clock_id, 'error': f'Parse error: {str(e)}'})
            else:
                results['failed'].append({'clock_id': clock_id, 'error': 'Lookup failed'})
                
        except Exception as e:
            results['failed'].append({'clock_id': clock_id, 'error': str(e)})

    # Commit all successful additions
    try:
        # No explicit commit needed for SQLite, changes are auto-committed
        pass
    except Exception as e:
        logger.error(f'Failed to commit cache entries: {str(e)}')
        return jsonify({'error': f'Failed to commit cache entries: {str(e)}'}), 500

    return jsonify({
        'success': True,
        'results': results,
        'summary': {
            'total_processed': len(clock_ids),
            'successful': len(results['success']),
            'failed': len(results['failed']),
            'already_existed': len(results['existing'])
        }
    }), 200 