"""
Clock ID Cache API Routes

These routes provide fast Clock ID lookups using the persistent cache
instead of running PowerShell scripts on every search.
"""

from flask import jsonify, request, Blueprint
from flask_login import login_required, current_user
from app.models.clock_id_cache import (
    get_clock_id_user, search_clock_ids, update_search_stats, 
    get_popular_searches, get_cache_stats, ensure_cache_tables
)
import logging

logger = logging.getLogger(__name__)

# Create a new blueprint for Clock ID cache routes
bp = Blueprint('clock_id_cache', __name__, url_prefix='/api/clock-id')

@bp.route('/lookup/<clock_id>', methods=['GET'])
@login_required
def lookup_clock_id(clock_id):
    """Fast Clock ID lookup from cache."""
    try:
        # Normalize clock ID (remove leading zeros)
        normalized_id = str(clock_id).lstrip('0')
        
        # Get user data from cache
        user_data = get_clock_id_user(normalized_id)
        
        if user_data:
            # Update search statistics
            update_search_stats(normalized_id)
            
            # Convert to user profile format for modal display
            profile_data = {
                'username': user_data['username'],
                'full_name': user_data['full_name'],
                'email': user_data['email'],
                'role': user_data['job_title'] or 'User',
                'title': user_data['job_title'],
                'clock_id': user_data['clock_id'],
                'profile_picture': None,
                'phone': '',  # Not stored in cache
                'password_last_reset': user_data['password_last_reset'],
                'account_status': user_data['account_status'],
                'locked_out': user_data['locked_out'],
                'password_expired': user_data['password_expired'],
                'email_license': None,  # Not stored in cache
                'department': user_data['department'],
                'epic_status': None,  # Not stored in cache
                'epic_block': None,  # Not stored in cache
                'immutable_id': user_data['immutable_id'],
                'not_locked_out': not user_data['locked_out'],
                'password_not_expired': not user_data['password_expired'],
                'group_membership': [],  # Not stored in cache
                'password_expiration_date': '',  # Not stored in cache
                'mfa_status': '',  # Not stored in cache
                'device_logon_history': []  # Not stored in cache
            }
            
            return jsonify({
                'success': True,
                'user': profile_data,
                'source': 'cache'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'No user found for Clock ID {clock_id}',
                'source': 'cache'
            }), 404
            
    except Exception as e:
        logger.error(f"Error in Clock ID lookup for {clock_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'source': 'cache'
        }), 500

@bp.route('/fallback/<clock_id>', methods=['POST'])
@login_required
def fallback_clock_id_lookup(clock_id):
    """Fallback to PowerShell lookup when cache miss occurs."""
    try:
        # Normalize clock ID (remove leading zeros)
        normalized_id = str(clock_id).lstrip('0')
        
        # Direct PowerShell lookup instead of trying to reuse the route function
        from pathlib import Path
        import subprocess
        import json
        
        script_path = Path(__file__).resolve().parents[3] / 'scripts' / 'user_lookup.ps1'
        
        if not script_path.exists():
            logger.error('PowerShell lookup script missing: %s', script_path)
            return jsonify({
                'success': False, 
                'error': 'Lookup script not found on server.',
                'source': 'fallback'
            }), 200

        # Very naive input sanitation – keep valid digits / letters only.
        if any(ch in normalized_id for ch in [';', '&', '|', '<', '>']):
            return jsonify({
                'success': False, 
                'error': 'Invalid characters in input.',
                'source': 'fallback'
            }), 200

        try:
            cmd = [
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', str(script_path), normalized_id
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
                return jsonify({
                    'success': False, 
                    'error': 'User not found.',
                    'source': 'fallback'
                }), 200

            try:
                data_json = json.loads(stdout)
            except json.JSONDecodeError as exc:
                logger.error('JSON parsing failed for PowerShell output: %s | stderr: %s', stdout[:500], stderr)
                return jsonify({
                    'success': False, 
                    'error': 'Malformed response from lookup script.',
                    'source': 'fallback'
                }), 200

            if not isinstance(data_json, dict) or len(data_json) == 0:
                return jsonify({
                    'success': False, 
                    'error': 'User not found.',
                    'source': 'fallback'
                }), 200

            # --------------------------------------------------
            # Cache **stable** attributes for faster future hits
            # --------------------------------------------------
            try:
                clock_id = str(data_json.get('ClockID', normalized_id)).lstrip('0')
                if clock_id:
                    from app.models.clock_id_cache import get_cache_db_connection
                    import sqlite3
                    
                    conn = get_cache_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        
                        # Parse full name into first and last name
                        full_name = data_json.get('FullName', '')
                        first_name, last_name = '', ''
                        if full_name:
                            parts = full_name.strip().split()
                            first_name = parts[0]
                            last_name = parts[-1] if len(parts) > 1 else ''
                        
                        # Insert into cache
                        cursor.execute('''
                            INSERT OR REPLACE INTO clock_id_cache (
                                clock_id, first_name, last_name, full_name, username, email,
                                job_title, department, display_name, user_principal_name,
                                immutable_id, account_status, locked_out, password_expired,
                                password_last_reset, bad_logon_count, last_logon, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            clock_id,
                            first_name,
                            last_name,
                            full_name,
                            data_json.get('Username', ''),
                            data_json.get('Email', ''),
                            data_json.get('Title', ''),
                            data_json.get('Department', ''),
                            data_json.get('DisplayName', ''),
                            data_json.get('UserPrincipalName', ''),
                            data_json.get('ImmutableID', ''),
                            data_json.get('AccountStatus', ''),
                            data_json.get('LockedOut', False),
                            data_json.get('PasswordExpired', False),
                            data_json.get('PasswordLastReset', ''),
                            data_json.get('BadLogonCount', 0),
                            data_json.get('LastLogon', ''),
                            'CURRENT_TIMESTAMP'
                        ))
                        
                        conn.commit()
                        conn.close()
                        logger.info(f"Cached Clock ID {clock_id} from fallback lookup")
                        
            except Exception as cache_error:
                logger.warning(f"Failed to cache Clock ID {normalized_id}: {cache_error}")

            # Convert to user profile format for modal display
            profile_data = {
                'username': data_json.get('Username', normalized_id),
                'full_name': data_json.get('FullName', ''),
                'email': data_json.get('Email', ''),
                'role': data_json.get('Title', 'User'),
                'title': data_json.get('Title', ''),
                'clock_id': data_json.get('ClockID', normalized_id),
                'profile_picture': None,
                'phone': data_json.get('Phone', ''),
                'password_last_reset': data_json.get('PasswordLastReset', ''),
                'account_status': data_json.get('AccountStatus', ''),
                'locked_out': data_json.get('LockedOut', False),
                'password_expired': data_json.get('PasswordExpired', False),
                'email_license': data_json.get('EmailLicense', None),
                'department': data_json.get('Department', ''),
                'epic_status': data_json.get('EpicStatus', ''),
                'epic_block': data_json.get('EpicBlock', ''),
                'immutable_id': data_json.get('ImmutableID', ''),
                'not_locked_out': data_json.get('NotLockedOut', True),
                'password_not_expired': data_json.get('PasswordNotExpired', True),
                'group_membership': [],
                'password_expiration_date': data_json.get('PasswordExpirationDate', ''),
                'mfa_status': data_json.get('MFAStatus', ''),
                'device_logon_history': []
            }

            # Successful lookup
            return jsonify({
                'success': True, 
                'user': profile_data,
                'source': 'fallback'
            }), 200

        except subprocess.TimeoutExpired:
            logger.error('PowerShell lookup timed out for query %s', normalized_id)
            return jsonify({
                'success': False, 
                'error': 'Lookup timed out.',
                'source': 'fallback'
            }), 200
        except Exception as exc:
            logger.exception('Unhandled server error during PowerShell lookup')
            return jsonify({
                'success': False, 
                'error': 'Internal server error.',
                'source': 'fallback'
            }), 200
        
    except Exception as e:
        logger.error(f"Error in fallback Clock ID lookup for {clock_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Fallback lookup failed',
            'source': 'fallback'
        }), 500

@bp.route('/suggestions', methods=['GET'])
@login_required
def get_clock_id_suggestions():
    """Get Clock ID suggestions for universal search."""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': True,
                'suggestions': [],
                'query': query
            }), 200
        
        # Check if query is a numeric Clock ID (1-5 digits)
        if query.isdigit() and 1 <= len(query) <= 5:
            # Direct Clock ID lookup
            user_data = get_clock_id_user(query)
            if user_data:
                suggestions = [{
                    'type': 'clock_id',
                    'clock_id': user_data['clock_id'],
                    'full_name': user_data['full_name'],
                    'username': user_data['username'],
                    'email': user_data['email'],
                    'job_title': user_data['job_title'],
                    'display_text': f"{user_data['full_name']} ({user_data['clock_id']})",
                    'subtitle': f"Clock ID: {user_data['clock_id']}"
                }]
            else:
                suggestions = [{
                    'type': 'clock_id_not_found',
                    'clock_id': query,
                    'display_text': f"Find user {query.zfill(5)}",
                    'subtitle': 'Lookup user by Clock ID'
                }]
        else:
            # Search by name, username, or email
            search_results = search_clock_ids(query, limit=5)
            suggestions = []
            
            for result in search_results:
                suggestions.append({
                    'type': 'clock_id',
                    'clock_id': result['clock_id'],
                    'full_name': result['full_name'],
                    'username': result['username'],
                    'email': result['email'],
                    'job_title': result['job_title'],
                    'display_text': f"{result['full_name']} ({result['clock_id']})",
                    'subtitle': f"{result['job_title']} • {result['department']}" if result['job_title'] and result['department'] else f"Clock ID: {result['clock_id']}"
                })
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'query': query
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting Clock ID suggestions for '{query}': {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get suggestions',
            'suggestions': []
        }), 500

@bp.route('/popular', methods=['GET'])
@login_required
def get_popular_clock_ids():
    """Get most frequently searched Clock IDs."""
    try:
        limit = request.args.get('limit', 10, type=int)
        popular = get_popular_searches(limit)
        
        return jsonify({
            'success': True,
            'popular_searches': popular
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting popular Clock IDs: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get popular searches',
            'popular_searches': []
        }), 500

@bp.route('/stats', methods=['GET'])
@login_required
def get_clock_id_stats():
    """Get cache statistics."""
    try:
        stats = get_cache_stats()
        
        if stats:
            return jsonify({
                'success': True,
                'stats': stats
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to get cache statistics'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting Clock ID cache stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get statistics'
        }), 500

@bp.route('/init', methods=['POST'])
@login_required
def initialize_cache():
    """Initialize cache tables (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        success = ensure_cache_tables()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Cache tables initialized successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to initialize cache tables'
            }), 500
            
    except Exception as e:
        logger.error(f"Error initializing cache: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to initialize cache'
        }), 500 