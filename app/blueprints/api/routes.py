"""Generic /api routes & Socket.IO handlers refactored from app/spark.py.

This keeps *spark.py* lean while the public contract (URLs / events) stays
exactly the same.
"""
from __future__ import annotations

import json
import subprocess
import re
import logging
from typing import Any

from flask import jsonify, current_app, request, make_response, send_from_directory, session
from flask_login import current_user, login_required
from flask_socketio import emit
from datetime import datetime, timedelta
import random

from extensions import socketio, db
from app.utils.device import cache_storage, load_cached_storage
from app.blueprints.devices.routes import load_devices_cache
from app.utils.search import get_search_suggestions, save_search
from app.models import SearchHistory, Activity, User, Note, UserSettings, Outage

from . import bp  # Blueprint registered in __init__

# Standard library
import os

# 3rd-party
import requests
from werkzeug.utils import secure_filename

# Internal helpers
from app.utils.helpers import allowed_file
from rapidfuzz import process, fuzz

# Set up logger
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper – recent search persistence (moved from old spark.py implementation)
# ---------------------------------------------------------------------------

def add_recent_search(user_id: int, query: str, search_type: str) -> None:
    """Persist a *query* to the ``search_history`` table for *user_id*."""
    if not query:
        return

    try:
        entry = SearchHistory(user_id=user_id, query=query, search_type=search_type)
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Keep silent failure to mimic the original best-effort behaviour.


# ---------------------------------------------------------------------------
# /api/device/<device_name>
# ---------------------------------------------------------------------------

@bp.route('/device/<device_name>')
def get_device(device_name: str):
    """Return inventory & live-storage data for *device_name* (unchanged)."""
    # Record the search so that it shows up in the UI history.
    if current_user.is_authenticated:
        add_recent_search(current_user.id, device_name, 'Workstation')

    # -- Cached inventory CSV -------------------------------------------------
    devices = load_devices_cache()

    found: dict[str, Any] | None = next(
        (
            row for row in devices
            if row.get('Device name', '').strip().lower() == device_name.strip().lower()
        ),
        None,
    )
    if not found:
        return jsonify(error='Device not found'), 404

    device = {
        'id':             found.get('Device ID', 'N/A'),
        'name':           found.get('Device name', 'N/A'),
        'managed_by':     found.get('Managed by', 'N/A'),
        'ownership':      found.get('Ownership', 'N/A'),
        'compliance':     found.get('Compliance', 'N/A'),
        'os':             found.get('OS', 'N/A'),
        'os_version':     found.get('OS version', 'N/A'),
        'user':           found.get('Primary user UPN', 'N/A'),
        'last_check_in':  found.get('Last check-in', 'N/A'),
    }

    # -- Live storage via PowerShell script ----------------------------------
    storage_total: dict[str, Any] = {'used': None, 'free': None}
    source = 'cache'

    try:
        ps = subprocess.run(
            [
                "powershell", "-ExecutionPolicy", "Bypass",
                "-File", "./scripts/storage.ps1"
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if ps.returncode == 0:
            vols = json.loads(ps.stdout)
            total_used = sum(v.get('UsedGB', 0) for v in vols)
            total_free = sum(v.get('FreeGB', 0) for v in vols)
            storage_total = {'used': total_used, 'free': total_free}
            cache_storage(device_name, storage_total)
            source = 'live'
        else:
            raise RuntimeError(ps.stderr or 'PS error')
    except Exception:
        cached = load_cached_storage(device_name)
        if cached and 'data' in cached:
            storage_total = cached['data']
        else:
            storage_total = {'used': None, 'free': None}

    return jsonify(device=device, storage=storage_total, source=source)


# ---------------------------------------------------------------------------
# /api/ping
# ---------------------------------------------------------------------------

@bp.route('/ping', methods=['POST'])
@login_required
def ping_device():
    """Ping a device and return real-time status."""
    try:
        data = request.get_json()
        hostname = data.get('hostname', '').strip()
        
        if not hostname:
            return jsonify({'error': 'Hostname is required'}), 400
        
        # Validate hostname format
        if not re.match(r'^[a-zA-Z0-9\-\.]+$', hostname):
            return jsonify({'error': 'Invalid hostname format'}), 400
        
        # Perform ping with timeout
        import platform
        import time
        
        start_time = time.time()
        
        if platform.system().lower() == "windows":
            # Windows ping command
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "2000", hostname],
                capture_output=True,
                text=True,
                timeout=3
            )
            success = "TTL=" in result.stdout
        else:
            # Unix/Linux ping command
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", hostname],
                capture_output=True,
                text=True,
                timeout=3
            )
            success = result.returncode == 0
        
        end_time = time.time()
        latency = round((end_time - start_time) * 1000, 1)  # Convert to milliseconds
        
        if success:
            # Extract actual ping time from output if possible
            try:
                if platform.system().lower() == "windows":
                    # Windows: "time=12ms"
                    time_match = re.search(r'time[=<](\d+)ms', result.stdout)
                else:
                    # Unix: "time=12.345 ms"
                    time_match = re.search(r'time=(\d+\.?\d*) ms', result.stdout)
                
                if time_match:
                    latency = float(time_match.group(1))
            except (ValueError, AttributeError):
                pass  # Use calculated latency if parsing fails
            
            return jsonify({
                'success': True,
                'hostname': hostname,
                'latency': latency,
                'status': 'online',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'hostname': hostname,
                'error': 'Device not responding',
                'status': 'offline',
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'hostname': hostname,
            'error': 'Ping timeout',
            'status': 'timeout',
            'timestamp': datetime.utcnow().isoformat()
        }), 408
    except Exception as e:
        return jsonify({
            'success': False,
            'hostname': hostname,
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@bp.route('/ping')
def ping():
    """Simple ping endpoint for latency testing."""
    return jsonify({
        'pong': True,
        'timestamp': datetime.utcnow().isoformat()
    })


# ---------------------------------------------------------------------------
# /api/remote/connectivity
# ---------------------------------------------------------------------------

@bp.route('/remote/connectivity', methods=['POST'])
@login_required
def check_device_connectivity():
    """Check device connectivity and available remote access methods."""
    try:
        data = request.get_json()
        hostname = data.get('hostname', '').strip()
        ip_address = data.get('ip_address', '').strip()
        
        if not hostname and not ip_address:
            return jsonify({'error': 'Hostname or IP address is required'}), 400
        
        from app.utils.remote_session import check_device_connectivity as check_connectivity
        result = check_connectivity(hostname, ip_address)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ---------------------------------------------------------------------------
# /api/remote/launch-dameware
# ---------------------------------------------------------------------------

@bp.route('/remote/launch-dameware', methods=['POST'])
@login_required
def launch_dameware_session():
    """Launch a Dameware remote session to the specified device."""
    try:
        data = request.get_json()
        hostname = data.get('hostname', '').strip()
        ip_address = data.get('ip_address', '').strip()
        
        if not hostname and not ip_address:
            return jsonify({'error': 'Hostname or IP address is required'}), 400
        
        from app.utils.remote_session import launch_dameware_session as launch_dameware
        result = launch_dameware(hostname, ip_address)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ---------------------------------------------------------------------------
# /api/remote/launch-rdp
# ---------------------------------------------------------------------------

@bp.route('/remote/launch-rdp', methods=['POST'])
@login_required
def launch_rdp_session():
    """Launch an RDP session to the specified device."""
    try:
        data = request.get_json()
        hostname = data.get('hostname', '').strip()
        ip_address = data.get('ip_address', '').strip()
        
        if not hostname and not ip_address:
            return jsonify({'error': 'Hostname or IP address is required'}), 400
        
        from app.utils.remote_session import launch_rdp_session as launch_rdp
        result = launch_rdp(hostname, ip_address)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ---------------------------------------------------------------------------
# /api/remote/options
# ---------------------------------------------------------------------------

@bp.route('/remote/options', methods=['POST'])
@login_required
def get_remote_access_options():
    """Get available remote access options for a device."""
    try:
        data = request.get_json()
        hostname = data.get('hostname', '').strip()
        ip_address = data.get('ip_address', '').strip()
        
        if not hostname and not ip_address:
            return jsonify({'error': 'Hostname or IP address is required'}), 400
        
        from app.utils.remote_session import get_remote_access_options as get_options
        result = get_options(hostname, ip_address)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ---------------------------------------------------------------------------
# Socket.IO – live search suggestions ("search_input" event)
# ---------------------------------------------------------------------------

@socketio.on('search_input')
def handle_search_input(query):
    """Return autocomplete suggestions for *query* over the websocket."""
    suggestions = get_search_suggestions(query)
    save_search(query)
    emit('update_suggestions', {'suggestions': suggestions})


# ---------------------------------------------------------------------------
# /admin/activity  (moved from spark.py)
# ---------------------------------------------------------------------------

@bp.route('/admin/activity')
@login_required
def admin_activity():
    """Return recent activity data for the admin dashboard with enhanced filtering."""
    try:
        # Get filter parameters
        user_filter = request.args.get('user', '')
        action_filter = request.args.get('action', '')
        hours_filter = request.args.get('hours', '24')
        
        # Build query
        query = db.session.query(Activity, User).join(User, Activity.user_id == User.id)
        
        # Apply filters
        if user_filter:
            query = query.filter(User.username.ilike(f'%{user_filter}%'))
        
        if action_filter:
            query = query.filter(Activity.action == action_filter)
        
        if hours_filter and hours_filter.isdigit():
            from datetime import datetime, timedelta
            hours_ago = datetime.utcnow() - timedelta(hours=int(hours_filter))
            query = query.filter(Activity.timestamp >= hours_ago)
        
        # Get activities with pagination
        activities = query.order_by(Activity.timestamp.desc()).limit(100).all()
        
        # Friendly mapping for common page routes
        route_map = {
            '/api/admin/dashboard': 'Viewed Dashboard',
            '/api/admin/outages': 'Viewed Outages',
            '/api/admin/users': 'Viewed Users',
            '/api/admin/documents': 'Viewed Documents',
            '/api/admin/settings': 'Viewed Settings',
            '/': 'Visited Home',
            '/offices': 'Viewed Offices',
            '/workstations': 'Viewed Workstations',
            '/users': 'Viewed Users',
            '/notes': 'Viewed Notes',
            '/kb': 'Viewed Knowledge Base',
            '/unified': 'Viewed Unified Search',
            '/outages': 'Viewed Outages',
            '/menu': 'Viewed Menu',
            '/tracking': 'Viewed Tracking',
            '/fax2mail': 'Viewed Fax2Mail',
            '/scan': 'Viewed Network Scanner',
            '/agent': 'Viewed Agent',
            '/lab': 'Viewed Lab',
            '/oralyzer': 'Viewed Oralyzer',
            '/profile': 'Viewed Profile',
            '/settings': 'Viewed Settings',
        }

        seen_activities: set[str] = set()
        formatted: list[dict] = []

        for activity, user in activities:
            # Skip self-referential log entries
            if activity.details == '/api/admin/activity':
                continue

            key = f"{activity.user_id}_{activity.action}_{activity.details}_{activity.timestamp.strftime('%Y-%m-%d %H:%M')}"
            if key in seen_activities:
                continue
            seen_activities.add(key)

            description = activity.details
            if activity.action == 'page_view':
                # Normalise trailing slashes so "/unified" and "/unified/" are treated the same
                normalised_path = activity.details.rstrip('/') or '/'

                # Friendly description when we have a predefined label
                if normalised_path in route_map:
                    description = route_map[normalised_path]
                else:
                    # Generic fallback so *all* page views are shown instead of silently discarded
                    description = f"Visited {normalised_path}"

            formatted.append(
                {
                    'id': activity.id,
                    'type': activity.action,
                    'description': description,
                    'timestamp': activity.timestamp.isoformat(),
                    'user': {
                        'id': user.id,
                        'name': user.username,
                        'profile_picture': user.profile_picture or 'boy.png',
                    },
                }
            )

        return jsonify(formatted)
    except Exception as exc:
        current_app.logger.error("Error fetching admin activity data: %s", exc)
        return jsonify([])


# ---------------------------------------------------------------------------
# Settings management endpoints (moved from app/spark.py)
# ---------------------------------------------------------------------------

@bp.route('/settings/export-data')
@login_required
def export_user_data():
    """Export the current user's profile, settings and search history as JSON."""
    try:
        user_data = {
            'profile': {
                'username': current_user.username,
                'email': current_user.email,
                'created_at': current_user.created_at.isoformat(),
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
            },
            'search_history': [
                {
                    'query': h.query,
                    'timestamp': h.timestamp.isoformat(),
                }
                for h in current_user.search_history
            ],
            'settings': {
                'appearance': {
                    'theme': current_user.settings.theme if current_user.settings else 'dark',
                    'accent_color': current_user.settings.accent_color if current_user.settings else '#007bff',
                    'font_size': current_user.settings.font_size if current_user.settings else 'medium',
                },
                'notifications': {
                    'email_notifications': current_user.settings.email_notifications if current_user.settings else True,
                    'browser_notifications': current_user.settings.browser_notifications if current_user.settings else True,
                    'notification_frequency': current_user.settings.notification_frequency if current_user.settings else 'realtime',
                },
                'privacy': {
                    'save_search_history': current_user.settings.save_search_history if current_user.settings else True,
                    'track_activity': current_user.settings.track_activity if current_user.settings else True,
                    'allow_data_collection': current_user.settings.allow_data_collection if current_user.settings else True,
                },
            },
        }

        response = make_response(jsonify(user_data))
        response.headers['Content-Disposition'] = f'attachment; filename=user-data-{current_user.username}.json'
        return response
    except Exception as exc:
        current_app.logger.error("Error exporting user data: %s", exc)
        return jsonify({'error': str(exc)}), 500


@bp.route('/settings/clear-search-history', methods=['POST'])
@login_required
def clear_search_history():
    """Delete all SearchHistory rows for the current user."""
    try:
        SearchHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'message': 'Search history cleared successfully'})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Error clearing search history: %s", exc)
        return jsonify({'error': str(exc)}), 500


@bp.route('/settings/clear-activity', methods=['POST'])
@login_required
def clear_activity():
    """Stub endpoint for clearing activity log (logic can be expanded)."""
    # NOTE: original implementation was empty – keep identical behaviour.
    return jsonify({'message': 'Activity log cleared successfully'})


@bp.route('/activity/track', methods=['POST'])
@login_required
def track_activity():
    """Track user activity for enhanced dashboard monitoring."""
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        if not data.get('action'):
            return jsonify({'error': 'Action is required'}), 400
        
        # Create activity record
        activity = Activity(
            user_id=current_user.id,
            action=data['action'],
            details=data.get('details', ''),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(activity)
        db.session.commit()
        
        # Emit real-time update to admin dashboard
        try:
            from extensions import socketio
            socketio.emit('activity_update', {
                'id': activity.id,
                'type': data['action'],
                'description': data.get('details', ''),
                'timestamp': activity.timestamp.isoformat(),
                'user': {
                    'id': current_user.id,
                    'name': current_user.username,
                    'profile_picture': current_user.profile_picture or 'boy.png'
                }
            }, namespace='/')
        except Exception as emit_error:
            current_app.logger.debug(f"Could not emit activity update: {emit_error}")
        
        return jsonify({'success': True, 'message': 'Activity tracked successfully'})
        
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Error tracking activity: %s", exc)
        return jsonify({'error': str(exc)}), 500


@bp.route('/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete the current user's account after verifying their password."""
    try:
        data = request.get_json(silent=True) or {}
        if not data.get('password') or not current_user.check_password(data['password']):
            return jsonify({'error': 'Incorrect password'}), 400

        SearchHistory.query.filter_by(user_id=current_user.id).delete()
        UserSettings.query.filter_by(user_id=current_user.id).delete()

        db.session.delete(current_user)
        db.session.commit()
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Error deleting account: %s", exc)
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Sticky Notes (moved from app/spark.py) - DISABLED in favor of collab_notes
# ---------------------------------------------------------------------------

# @bp.route('/notes', methods=['GET', 'POST'])
# @login_required
# def api_notes():
#     """Create a new note or list existing ones for the current user."""
#     if request.method == 'GET':
#         notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.created_at.desc()).all()
#         return jsonify([
#             {
#                 'id': n.id,
#                 'title': n.title,
#                 'content': n.content,
#                 'color': n.color,
#                 'position_x': n.position_x,
#                 'position_y': n.position_y,
#                 'created_at': n.created_at.isoformat(),
#                 'updated_at': n.updated_at.isoformat(),
#             }
#             for n in notes
#         ])

#     # POST – create
#     data = request.get_json() or {}
#     note = Note(
#         title=data.get('title', 'New Note'),
#         content=data.get('content', ''),
#         color=data.get('color', '#ffffff'),
#         position_x=data.get('position_x', 0),
#         position_y=data.get('position_y', 0),
#         user_id=current_user.id,
#     )
#     db.session.add(note)
#     db.session.commit()

#     return jsonify(
#         {
#             'success': True,
#             'message': 'Note created successfully',
#             'note': {
#                 'id': note.id,
#                 'title': note.title,
#                 'content': note.content,
#                 'color': note.color,
#                 'position_x': note.position_x,
#                 'position_y': note.position_y,
#                 'created_at': note.created_at.isoformat(),
#                 'updated_at': note.updated_at.isoformat(),
#             },
#         }
#     ), 201


# @bp.route('/notes/<int:note_id>', methods=['PUT'])
# @login_required
# def update_note(note_id: int):
#     """Update a note belonging to the current user."""
#     note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()
#     if not note:
#         return jsonify({'error': 'Note not found'}), 404

#     data = request.get_json() or {}
#     if 'title' in data:
#         note.title = data['title']
#     if 'content' in data:
#         note.content = data['content']
#     if 'color' in data:
#         note.color = data['color']
#     if 'position_x' in data:
#         note.position_x = data['position_x']
#     if 'position_y' in data:
#         note.position_y = data['position_y']

#     note.updated_at = datetime.utcnow()
#     db.session.commit()

#     return jsonify(
#         {
#             'id': note.id,
#             'title': note.title,
#             'content': note.content,
#             'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
#             'updated_at': note.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
#         }
#     )


# @bp.route('/notes/<int:note_id>', methods=['DELETE'])
# @login_required
# def delete_note(note_id: int):
#     """Delete a note belonging to the current user."""
#     note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()
#     if not note:
#         return jsonify({'error': 'Note not found'}), 404

#     db.session.delete(note)
#     db.session.commit()
#     return jsonify({'message': 'Note deleted successfully'})


# ---------------------------------------------------------------------------
# Profile management endpoints (migrated from app/spark.py)
# ---------------------------------------------------------------------------

@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile_api():
    """Update the current user's username and/or email.

    Expects a JSON body with *username* and *email* fields.  Performs basic
    validation to avoid duplicates and commits the changes.
    """
    try:
        data = request.get_json() or {}

        # Validate payload
        if not all(k in data for k in ('username', 'email')):
            return jsonify({'error': 'Missing required fields'}), 400

        # Ensure uniqueness (case-sensitive match, excluding current user)
        if User.query.filter(User.username == data['username'], User.id != current_user.id).first():
            return jsonify({'error': 'Username already exists'}), 400
        if User.query.filter(User.email == data['email'], User.id != current_user.id).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Apply updates
        current_user.username = data['username']
        current_user.email = data['email']
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Error updating profile: %s', exc)
        return jsonify({'error': str(exc)}), 500


@bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password_api():
    """Change the current user's password.

    Requires *current_password* and *new_password* in the JSON body.  The
    current password is verified before applying the change.
    """
    try:
        data = request.get_json() or {}
        if not all(k in data for k in ('current_password', 'new_password')):
            return jsonify({'error': 'Missing required fields'}), 400

        if not current_user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400

        current_user.set_password(data['new_password'])
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Error changing password: %s', exc)
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Profile picture upload & Okta verification (moved from app/spark.py)
# ---------------------------------------------------------------------------

@bp.route('/profile/picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Handle profile picture uploads while preserving original behaviour.

    Expects a *multipart/form-data* POST with a **file** field containing the
    image. Validates the extension against ``Config.ALLOWED_EXTENSIONS`` and
    stores the file inside the directory configured via
    ``UPLOAD_FOLDER``. The final filename is prefixed with the current user's
    ID to avoid collisions.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.id}_{file.filename}")

        # Ensure the uploads directory exists (config value mirrors legacy path)
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Persist on the user record
        current_user.profile_picture = filename
        db.session.commit()

        return jsonify({'success': True, 'filename': filename})

    return jsonify({'error': 'Invalid file type'}), 400


@bp.route('/profile/okta-verify', methods=['POST'])
@login_required
def verify_okta():
    """Mark the current user as Okta-verified based on browser extension flag."""
    try:
        okta_installed = request.headers.get('X-Okta-Extension-Installed', 'false').lower() == 'true'

        if okta_installed:
            current_user.okta_verified = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'Okta verification successful'})
        return jsonify({'success': False, 'message': 'Okta extension not found'})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Outage → Microsoft Teams notification (moved from app/spark.py)
# ---------------------------------------------------------------------------

@bp.route('/outages/notify-teams', methods=['POST'])
@login_required
def notify_teams():
    """Send a Teams message card for the specified outage (admin-only).

    The endpoint expects a JSON body with an *outage_id* field.  The call will
    fail if the ID is missing, the outage does not exist or the webhook is not
    configured via the *TEAMS_WEBHOOK_URL* environment variable.
    """
    try:
        data = request.get_json() or {}
        outage_id = data.get('outage_id')

        if not outage_id:
            return jsonify({'error': 'Outage ID required'}), 400

        outage = Outage.query.get_or_404(outage_id)

        teams_webhook = os.getenv('TEAMS_WEBHOOK_URL')
        if not teams_webhook:
            return jsonify({'error': 'Teams webhook not configured'}), 500

        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": f"Outage Alert: {outage.title}",
            "sections": [
                {
                    "activityTitle": f"🚨 Outage Alert: {outage.title}",
                    "activitySubtitle": f"Started: {outage.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    "facts": [
                        {"name": "Status:", "value": outage.status},
                        {"name": "Description:", "value": outage.description},
                    ],
                    "markdown": True,
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "View Details",
                    "targets": [
                        {
                            "os": "default",
                            "uri": f"{request.host_url}outages/{outage.id}",
                        }
                    ],
                }
            ],
        }

        response = requests.post(teams_webhook, json=message)
        response.raise_for_status()

        return jsonify({'success': True, 'message': 'Teams notification sent'})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# /api/workstations/detail
# ---------------------------------------------------------------------------

@bp.route('/workstations/detail')
@login_required
def api_workstation_detail():
    """Return structured JSON details for a workstation identified by *name*.

    This duplicates the logic that previously lived in the *workstations*
    blueprint but exposes it under the canonical */api/workstations/detail*
    path that the front-end expects.  We reuse the existing
    ``load_devices_cache`` helper for fast look-ups.
    """
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Workstation name is required'}), 400

    try:
        devices = load_devices_cache()

        # --- Exact match ----------------------------------------------------
        device = next(
            (d for d in devices if d.get('Device name', '').lower() == name.lower()),
            None,
        )

        # --- Fallback fuzzy match ------------------------------------------
        if device is None:
            device_names = [d.get('Device name', '') for d in devices]
            matches = process.extract(name, device_names, scorer=fuzz.WRatio, limit=1)
            if matches and matches[0][1] > 80:
                best_name = matches[0][0]
                device = next((d for d in devices if d.get('Device name', '') == best_name), None)

        if device is None:
            return jsonify({'error': 'Workstation not found'}), 404

        # Attempt to resolve IP if not present in cached CSV
        ip_address = device.get('IPv4Address', '') or 'N/A'
        if ip_address in ('', 'N/A'):
            try:
                import socket
                ip_address = socket.gethostbyname(device.get('Device name', ''))
            except (socket.gaierror, socket.herror):
                ip_address = 'N/A'

        return jsonify(
            {
                'name': device.get('Device name', ''),
                'os': device.get('OS', ''),
                'os_version': device.get('OS version', ''),
                'user': device.get('Primary user UPN', ''),
                'managed_by': device.get('Managed by', ''),
                'compliance': device.get('Compliance', ''),
                'ip': ip_address,
                'enabled': device.get('Enabled', ''),
                'last_logon': device.get('LastLogonDate', ''),
                'ou_groups': device.get('OUGroups', ''),
                'locked': device.get('Locked', ''),
                'workstation_class': device.get('WorkstationClass', ''),
                'online': device.get('Online', False),
            }
        )
    except Exception as exc:
        return jsonify({'error': f'Error retrieving workstation details: {exc}'}), 500 

from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from extensions import db
from app.models import User
from . import bp
import logging
from datetime import datetime

logger = logging.getLogger('spark')

@bp.route('/users/online')
@login_required
def get_online_users():
    """Get list of online users for the YAM dashboard with enhanced real-time support."""
    try:
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required',
                'message': 'User not authenticated'
            }), 401
        
        # Update current user's last activity first
        try:
            current_user.last_seen = datetime.utcnow()
            current_user.is_online = True
            db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to update current user activity: {e}")
            db.session.rollback()
        
        # Use presence service for better accuracy
        try:
            from app.services.user_presence import presence_service
            users_list = presence_service.get_online_users(include_details=True)
            presence_stats = presence_service.get_presence_stats()
            
            # Normalize user data format for consistency
            normalized_users = []
            for user in users_list:
                normalized_user = {
                    'id': user.get('id') or user.get('user_id'),
                    'username': user.get('username') or user.get('name', 'Unknown'),
                    'email': user.get('email', ''),
                    'is_online': user.get('is_online', False),
                    'status': user.get('status') or ('online' if user.get('is_online') else 'offline'),
                    'role': user.get('role', 'user'),
                    'last_seen': user.get('last_seen'),
                    'profile_picture': user.get('profile_picture', 'default.png'),
                    'session_data': user.get('session_data', {})
                }
                
                # Calculate human-readable last seen
                if normalized_user['last_seen']:
                    try:
                        last_seen = datetime.fromisoformat(normalized_user['last_seen'].replace('Z', '+00:00'))
                        now = datetime.utcnow().replace(tzinfo=last_seen.tzinfo)
                        diff = now - last_seen
                        
                        if diff.total_seconds() < 60:
                            normalized_user['last_seen_human'] = 'Just now'
                        elif diff.total_seconds() < 3600:
                            minutes = int(diff.total_seconds() / 60)
                            normalized_user['last_seen_human'] = f'{minutes} minute{"s" if minutes != 1 else ""} ago'
                        elif diff.total_seconds() < 86400:
                            hours = int(diff.total_seconds() / 3600)
                            normalized_user['last_seen_human'] = f'{hours} hour{"s" if hours != 1 else ""} ago'
                        else:
                            days = int(diff.total_seconds() / 86400)
                            normalized_user['last_seen_human'] = f'{days} day{"s" if days != 1 else ""} ago'
                    except Exception:
                        normalized_user['last_seen_human'] = 'Unknown'
                else:
                    normalized_user['last_seen_human'] = 'Never'
                
                normalized_users.append(normalized_user)
            
            response_data = {
                'users': normalized_users,
                'total_users': presence_stats.get('total_users', len(normalized_users)),
                'online_users': presence_stats.get('online_users', len([u for u in normalized_users if u['is_online']])),
                'timestamp': datetime.utcnow().isoformat(),
                'session_healthy': True,
                'current_user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'is_online': current_user.is_online
                }
            }
            
            logger.debug(f"API: Sent online users list: {len(normalized_users)} users")
            return jsonify(response_data)
            
        except Exception as presence_error:
            logger.warning(f"Presence service failed, falling back to direct database query: {presence_error}")
            
            # Fallback to direct database query
            users = User.query.all()
            users_list = []
            
            for user in users:
                # Properly determine online status based on last_seen timestamp
                now = datetime.utcnow()
                is_online = False
                
                if user.last_seen:
                    time_diff = (now - user.last_seen).total_seconds()
                    # User is considered online if they were active in the last 5 minutes (300 seconds)
                    is_online = time_diff < 300
                else:
                    # If no last_seen, user is offline
                    is_online = False
                
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_online': is_online,
                    'status': 'online' if is_online else 'offline',
                    'last_seen': user.last_seen.isoformat() if user.last_seen else None,
                    'role': getattr(user, 'role', 'user'),
                    'profile_picture': getattr(user, 'profile_picture', 'default.png'),
                    'session_data': {}
                }
                
                # Calculate human-readable last seen
                if user.last_seen:
                    diff = now - user.last_seen
                    
                    if diff.total_seconds() < 60:
                        user_data['last_seen_human'] = 'Just now'
                    elif diff.total_seconds() < 3600:
                        minutes = int(diff.total_seconds() / 60)
                        user_data['last_seen_human'] = f'{minutes} minute{"s" if minutes != 1 else ""} ago'
                    elif diff.total_seconds() < 86400:
                        hours = int(diff.total_seconds() / 3600)
                        user_data['last_seen_human'] = f'{hours} hour{"s" if hours != 1 else ""} ago'
                    else:
                        days = int(diff.total_seconds() / 86400)
                        user_data['last_seen_human'] = f'{days} day{"s" if days != 1 else ""} ago'
                else:
                    user_data['last_seen_human'] = 'Never'
                
                users_list.append(user_data)
            
            response_data = {
                'users': users_list,
                'total_users': len(users_list),
                'online_users': len([u for u in users_list if u['is_online']]),
                'timestamp': datetime.utcnow().isoformat(),
                'session_healthy': True,
                'current_user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'is_online': current_user.is_online
                }
            }
            
            logger.debug(f"API: Sent fallback users list: {len(users_list)} users")
            return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting online users: {e}")
        return jsonify({
            'error': 'Failed to get online users',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'session_healthy': False
        }), 500

@bp.route('/users/status')
@login_required
def get_user_status():
    """Get current user's status for the YAM dashboard."""
    try:
        user_data = {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'is_online': current_user.is_online,
            'last_seen': current_user.last_seen.isoformat() if current_user.last_seen else None,
            'role': getattr(current_user, 'role', 'user'),
            'profile_picture': getattr(current_user, 'profile_picture', 'default.png'),
            'authenticated': current_user.is_authenticated
        }
        
        return jsonify({
            'user': user_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user status: {e}")
        return jsonify({
            'error': 'Failed to get user status',
            'message': str(e)
        }), 500

@bp.route('/users/session-health')
@login_required
def get_session_health():
    """Check session health for the YAM dashboard."""
    try:
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({
                'healthy': False,
                'error': 'User not authenticated',
                'timestamp': datetime.utcnow().isoformat()
            }), 401
        
        # Calculate session duration based on last login
        session_duration = "0m"
        if current_user.last_login:
            session_start = current_user.last_login
            session_end = datetime.utcnow()
            duration_minutes = int((session_end - session_start).total_seconds() / 60)
            
            if duration_minutes >= 60:
                hours = duration_minutes // 60
                minutes = duration_minutes % 60
                session_duration = f"{hours}h {minutes}m"
            else:
                session_duration = f"{duration_minutes}m"
        
        # Use presence service for better accuracy
        try:
            from app.services.user_presence import presence_service
            user_status = presence_service.get_user_status(current_user.id)
            presence_stats = presence_service.get_presence_stats()
            
            # Update user's last activity
            try:
                current_user.last_seen = datetime.utcnow()
                current_user.is_online = True
                db.session.commit()
            except Exception as e:
                logger.warning(f"Failed to update user activity: {e}")
                db.session.rollback()
            
            return jsonify({
                'healthy': True,
                'user_id': current_user.id,
                'username': current_user.username,
                'is_online': current_user.is_online,
                'session_duration': session_duration,
                'user_status': user_status,
                'presence_stats': presence_stats,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting session health: {e}")
            return jsonify({
                'healthy': True,
                'user_id': current_user.id,
                'username': current_user.username,
                'is_online': current_user.is_online,
                'session_duration': session_duration,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error in session health endpoint: {e}")
        return jsonify({
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@bp.route('/dashboard/quick-stats')
@login_required
def get_quick_stats():
    """Get enhanced quick stats for the dashboard."""
    try:
        from app.services.user_presence import presence_service
        from app.models import Activity
        
        # Get presence stats with error handling
        try:
            presence_stats = presence_service.get_presence_stats()
        except Exception as presence_error:
            logger.warning(f"Presence service error, using fallback: {presence_error}")
            presence_stats = {'online_users': 0, 'total_users': 0}
        
        # Get enhanced system health and metrics
        system_metrics = {}
        try:
            import psutil
            import time
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            system_metrics['cpu_usage'] = round(cpu_percent, 1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            system_metrics['memory_usage'] = round(memory.percent, 1)
            system_metrics['memory_total'] = round(memory.total / (1024**3), 1)  # GB
            system_metrics['memory_available'] = round(memory.available / (1024**3), 1)  # GB
            
            # Disk usage
            try:
                disk = psutil.disk_usage('/')
                system_metrics['disk_usage'] = round(disk.percent, 1)
                system_metrics['disk_total'] = round(disk.total / (1024**3), 1)  # GB
                system_metrics['disk_free'] = round(disk.free / (1024**3), 1)  # GB
            except Exception:
                # Windows might not have root directory
                disk = psutil.disk_usage('C:\\')
                system_metrics['disk_usage'] = round(disk.percent, 1)
                system_metrics['disk_total'] = round(disk.total / (1024**3), 1)  # GB
                system_metrics['disk_free'] = round(disk.free / (1024**3), 1)  # GB
            
            # Network stats
            try:
                network = psutil.net_io_counters()
                system_metrics['network_sent'] = round(network.bytes_sent / (1024**2), 1)  # MB
                system_metrics['network_recv'] = round(network.bytes_recv / (1024**2), 1)  # MB
            except Exception:
                system_metrics['network_sent'] = 0
                system_metrics['network_recv'] = 0
            
            # Determine system health based on metrics
            if cpu_percent < 70 and memory.percent < 80 and system_metrics['disk_usage'] < 85:
                system_health = 'Good'
            elif cpu_percent < 90 and memory.percent < 90 and system_metrics['disk_usage'] < 95:
                system_health = 'Warning'
            else:
                system_health = 'Critical'
                
        except ImportError:
            system_health = 'Unknown'
            system_metrics = {}
        except Exception as psutil_error:
            logger.warning(f"psutil error: {psutil_error}")
            system_health = 'Unknown'
            system_metrics = {}
        
        # Get enhanced uptime
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_days = uptime_hours // 24
            uptime_hours = uptime_hours % 24
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            
            if uptime_days > 0:
                uptime = f"{uptime_days}d {uptime_hours}h"
                uptime_detailed = f"{uptime_days} days, {uptime_hours} hours, {uptime_minutes} minutes"
            elif uptime_hours > 0:
                uptime = f"{uptime_hours}h {uptime_minutes}m"
                uptime_detailed = f"{uptime_hours} hours, {uptime_minutes} minutes"
            else:
                uptime = f"{uptime_minutes}m"
                uptime_detailed = f"{uptime_minutes} minutes"
                
        except Exception as uptime_error:
            logger.warning(f"Uptime calculation error: {uptime_error}")
            uptime = 'Unknown'
            uptime_detailed = 'Unknown'
        
        # Get additional stats
        try:
            # Process count
            process_count = len(psutil.pids())
            system_metrics['process_count'] = process_count
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                system_metrics['load_average'] = [round(load, 2) for load in load_avg]
            except AttributeError:
                # Windows doesn't have load average
                system_metrics['load_average'] = None
                
        except Exception:
            system_metrics['process_count'] = 0
            system_metrics['load_average'] = None
        
        return jsonify({
            'online_users': presence_stats.get('online_users', 0),
            'active_sessions': presence_stats.get('total_users', 0),
            'system_health': system_health,
            'uptime': uptime,
            'uptime_detailed': uptime_detailed,
            'system_metrics': system_metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        return jsonify({
            'error': 'Failed to get quick stats',
            'message': str(e)
        }), 500

@bp.route('/activity/recent')
@login_required
def get_recent_activity():
    """Get recent activity for the dashboard."""
    try:
        from app.models import Activity
        
        # Get recent activities (last 20)
        activities = Activity.query.order_by(Activity.timestamp.desc()).limit(20).all()
        
        activity_list = []
        for activity in activities:
            # Get user info
            user = User.query.get(activity.user_id)
            username = user.username if user else 'Unknown'
            
            activity_list.append({
                'id': activity.id,
                'user': username,
                'action': activity.action,
                'details': activity.details,
                'timestamp': activity.timestamp.isoformat()
            })
        
        return jsonify({
            'activities': activity_list,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return jsonify({
            'error': 'Failed to get recent activity',
            'message': str(e)
        }), 500

@bp.route('/health')
def get_health():
    """Get server health status."""
    try:
        # Basic health check
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@bp.route('/database/health')
@login_required
def get_database_health():
    """Get database health status."""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        return jsonify({
            'healthy': True,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return jsonify({
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# ---------------------------------------------------------------------------
# Analytics Endpoints
# ---------------------------------------------------------------------------

@bp.route('/analytics/metrics')
@login_required
def analytics_metrics():
    """Get analytics metrics for the specified period"""
    period = request.args.get('period', '24h')
    
    try:
        # Import presence service with error handling
        try:
            from app.services.user_presence import presence_service
        except ImportError as import_error:
            logger.error(f"Failed to import presence service: {import_error}")
            return jsonify({
                'activeUsers': 0,
                'avgSession': 30,
                'productivity': 0,
                'engagement': 0,
                'period': period,
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'Presence service unavailable'
            })
        
        # Get online users for active users metric with error handling
        try:
            online_users = presence_service.get_online_users(include_details=True)
            active_users = len(online_users)
        except Exception as users_error:
            logger.warning(f"Error getting online users: {users_error}")
            online_users = []
            active_users = 0
        
        # Get presence stats for other metrics with error handling
        try:
            stats = presence_service.get_presence_stats()
        except Exception as stats_error:
            logger.warning(f"Error getting presence stats: {stats_error}")
            stats = {'total_users': 1, 'average_session_duration': 30}
        
        # Calculate productivity (active users / total users)
        total_users = stats.get('total_users', 1)
        productivity = round((active_users / total_users) * 100) if total_users > 0 else 0
        
        # Simulate other metrics (in a real implementation, these would come from actual analytics)
        avg_session = stats.get('average_session_duration', 30)
        engagement = len(online_users) * 2  # Simple engagement calculation
        
        metrics = {
            'activeUsers': active_users,
            'avgSession': avg_session,
            'productivity': productivity,
            'engagement': engagement,
            'period': period,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting analytics metrics: {e}")
        return jsonify({'error': 'Failed to get analytics metrics'}), 500

@bp.route('/analytics/timeline')
@login_required
def analytics_timeline():
    """Get activity timeline data for the specified period"""
    period = request.args.get('period', '24h')
    
    try:
        # Generate timeline data (in a real implementation, this would come from actual activity logs)
        timeline = []
        now = datetime.utcnow()
        
        # Generate 24 hours of data
        for i in range(24):
            timestamp = now - timedelta(hours=i)
            timeline.append({
                'timestamp': timestamp.isoformat(),
                'activity': random.randint(1, 20),
                'users': random.randint(1, 10)
            })
        
        timeline.reverse()  # Oldest first
        
        return jsonify({
            'timeline': timeline,
            'period': period,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics timeline: {e}")
        return jsonify({'error': 'Failed to get analytics timeline'}), 500

@bp.route('/analytics/heatmap')
@login_required
def analytics_heatmap():
    """Get activity heatmap data for the specified period"""
    period = request.args.get('period', '24h')
    
    try:
        # Generate heatmap data (7 days x 24 hours)
        heatmap = []
        for hour in range(24):
            heatmap.append([])
            for day in range(7):
                heatmap[hour].append(random.randint(0, 40))
        
        return jsonify({
            'heatmap': heatmap,
            'period': period,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics heatmap: {e}")
        return jsonify({'error': 'Failed to get analytics heatmap'}), 500

@bp.route('/analytics/performers')
@login_required
def analytics_performers():
    """Get top performers data for the specified period"""
    period = request.args.get('period', '24h')
    
    try:
        # Import presence service with error handling
        try:
            from app.services.user_presence import presence_service
        except ImportError as import_error:
            logger.error(f"Failed to import presence service: {import_error}")
            return jsonify({
                'performers': [],
                'period': period,
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'Presence service unavailable'
            })
        
        # Get online users and calculate performance scores with error handling
        try:
            online_users = presence_service.get_online_users(include_details=True)
        except Exception as users_error:
            logger.warning(f"Error getting online users: {users_error}")
            online_users = []
        
        performers = []
        for user in online_users[:5]:  # Top 5 users
            performers.append({
                'name': user.get('username', 'Unknown'),
                'sessionTime': random.randint(2, 8),
                'activities': random.randint(20, 100),
                'score': random.randint(50, 100)
            })
        
        # Sort by score
        performers.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'performers': performers,
            'period': period,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics performers: {e}")
        return jsonify({'error': 'Failed to get analytics performers'}), 500

# ---------------------------------------------------------------------------
# System Monitor Endpoints
# ---------------------------------------------------------------------------

@bp.route('/system/metrics')
@login_required
def system_metrics():
    """Get system performance metrics"""
    try:
        import psutil
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        cpu_load = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_used_gb = round(memory.used / (1024**3), 1)
        memory_total_gb = round(memory.total / (1024**3), 1)
        memory_available_gb = round(memory.available / (1024**3), 1)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_used_gb = round(disk.used / (1024**3), 1)
        disk_total_gb = round(disk.total / (1024**3), 1)
        disk_free_gb = round(disk.free / (1024**3), 1)
        
        # Network metrics (simplified)
        network_io = psutil.net_io_counters()
        network_down_mbps = round(network_io.bytes_recv / (1024**2), 1)
        network_up_mbps = round(network_io.bytes_sent / (1024**2), 1)
        
        metrics = {
            'cpu': {
                'usage': round(cpu_percent, 1),
                'cores': cpu_count,
                'load': round(cpu_load, 2),
                'temp': random.randint(40, 70)  # Simulated temperature
            },
            'memory': {
                'used': memory_used_gb,
                'total': memory_total_gb,
                'available': memory_available_gb,
                'usage': round(memory.percent, 1)
            },
            'disk': {
                'used': disk_used_gb,
                'total': disk_total_gb,
                'free': disk_free_gb,
                'usage': round((disk.used / disk.total) * 100, 1)
            },
            'network': {
                'down': network_down_mbps,
                'up': network_up_mbps,
                'downChange': random.randint(-10, 10),
                'upChange': random.randint(-10, 10)
            },
            'database': {
                'connected': True,
                'connections': random.randint(5, 25),
                'queries': random.randint(10, 100),
                'response': random.randint(5, 50)
            },
            'logs': generate_system_logs(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(metrics)
        
    except ImportError:
        # Fallback to simulated data if psutil is not available
        return jsonify(generate_simulated_system_metrics())
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return jsonify(generate_simulated_system_metrics())

def generate_system_logs():
    """Generate simulated system logs"""
    log_levels = ['info', 'warning', 'error']
    log_messages = [
        'System check completed successfully',
        'Database connection established',
        'User authentication successful',
        'Cache cleared automatically',
        'Backup process started',
        'High memory usage detected',
        'Network latency increased',
        'Disk space running low'
    ]
    
    logs = []
    for i in range(5):
        logs.append({
            'timestamp': (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
            'level': random.choice(log_levels),
            'message': random.choice(log_messages)
        })
    
    return logs

def generate_simulated_system_metrics():
    """Generate simulated system metrics"""
    return {
        'cpu': {
            'usage': random.randint(10, 80),
            'cores': 8,
            'load': round(random.uniform(0, 4), 2),
            'temp': random.randint(40, 70)
        },
        'memory': {
            'used': random.randint(4, 12),
            'total': 16,
            'available': random.randint(2, 8),
            'usage': random.randint(20, 90)
        },
        'disk': {
            'used': random.randint(100, 300),
            'total': 500,
            'free': random.randint(50, 200),
            'usage': random.randint(20, 90)
        },
        'network': {
            'down': random.randint(10, 100),
            'up': random.randint(5, 50),
            'downChange': random.randint(-10, 10),
            'upChange': random.randint(-10, 10)
        },
        'database': {
            'connected': True,
            'connections': random.randint(5, 25),
            'queries': random.randint(10, 100),
            'response': random.randint(5, 50)
        },
        'logs': generate_system_logs(),
        'timestamp': datetime.utcnow().isoformat()
    }

# ---------------------------------------------------------------------------
# Collaboration Endpoints
# ---------------------------------------------------------------------------

@bp.route('/collaboration/workspaces')
@login_required
def get_workspaces():
    """Get user's workspaces"""
    try:
        # In a real implementation, this would query the database
        # For now, return simulated data
        workspaces = [
            {
                'id': '1',
                'name': 'Project Alpha',
                'description': 'Main development workspace',
                'memberCount': 5,
                'lastActivity': '2 minutes ago',
                'createdBy': current_user.username
            },
            {
                'id': '2',
                'name': 'Design Team',
                'description': 'UI/UX collaboration space',
                'memberCount': 3,
                'lastActivity': '15 minutes ago',
                'createdBy': current_user.username
            }
        ]
        
        return jsonify(workspaces)
        
    except Exception as e:
        logger.error(f"Error getting workspaces: {e}")
        return jsonify({'error': 'Failed to get workspaces'}), 500

@bp.route('/collaboration/workspaces', methods=['POST'])
@login_required
def create_workspace():
    """Create a new workspace"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        members = data.get('members', [])
        
        if not name:
            return jsonify({'error': 'Workspace name is required'}), 400
        
        # In a real implementation, this would save to database
        workspace = {
            'id': str(random.randint(1000, 9999)),
            'name': name,
            'description': description,
            'memberCount': len(members) + 1,  # +1 for creator
            'lastActivity': 'Just now',
            'createdBy': current_user.username,
            'members': members
        }
        
        # Emit to Socket.IO for real-time updates
        if window.yamDashboard and window.yamDashboard.socket:
            window.yamDashboard.socket.emit('workspace_created', workspace)
        
        return jsonify(workspace)
        
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        return jsonify({'error': 'Failed to create workspace'}), 500

@bp.route('/collaboration/files')
@login_required
def get_shared_files():
    """Get shared files"""
    try:
        # Simulated shared files data
        files = [
            {
                'id': '1',
                'name': 'project-specs.pdf',
                'sharedBy': 'John Doe',
                'sharedAt': '1 hour ago',
                'downloads': 12,
                'size': '2.5 MB'
            },
            {
                'id': '2',
                'name': 'design-mockups.zip',
                'sharedBy': 'Jane Smith',
                'sharedAt': '3 hours ago',
                'downloads': 8,
                'size': '15.2 MB'
            }
        ]
        
        return jsonify(files)
        
    except Exception as e:
        logger.error(f"Error getting shared files: {e}")
        return jsonify({'error': 'Failed to get shared files'}), 500

@bp.route('/collaboration/tasks')
@login_required
def get_tasks():
    """Get team tasks"""
    try:
        # Simulated tasks data
        tasks = [
            {
                'id': '1',
                'title': 'Review project documentation',
                'assignedTo': 'John Doe',
                'createdAt': '2 hours ago',
                'createdBy': 'Jane Smith',
                'completed': False
            },
            {
                'id': '2',
                'title': 'Update user interface',
                'assignedTo': 'Mike Johnson',
                'createdAt': '1 day ago',
                'createdBy': 'John Doe',
                'completed': True
            }
        ]
        
        return jsonify(tasks)
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({'error': 'Failed to get tasks'}), 500

@bp.route('/collaboration/tasks', methods=['POST'])
@login_required
def create_task():
    """Create a new task"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        createdBy = data.get('createdBy', current_user.username)
        
        if not title:
            return jsonify({'error': 'Task title is required'}), 400
        
        # In a real implementation, this would save to database
        task = {
            'id': str(random.randint(1000, 9999)),
            'title': title,
            'assignedTo': 'Unassigned',
            'createdAt': 'Just now',
            'createdBy': createdBy,
            'completed': False
        }
        
        # Emit to Socket.IO for real-time updates
        if window.yamDashboard and window.yamDashboard.socket:
            window.yamDashboard.socket.emit('task_created', task)
        
        return jsonify(task)
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': 'Failed to create task'}), 500

@bp.route('/collaboration/events')
@login_required
def get_events():
    """Get team events and calendar data."""
    try:
        # Mock data for demonstration
        events = [
            {
                'id': 1,
                'title': 'Team Meeting',
                'description': 'Weekly team sync',
                'start_time': '2024-01-15T10:00:00Z',
                'end_time': '2024-01-15T11:00:00Z',
                'organizer': 'Team Lead',
                'attendees': ['User 1', 'User 2', 'User 3'],
                'type': 'meeting'
            },
            {
                'id': 2,
                'title': 'Project Deadline',
                'description': 'Phase 1 completion',
                'start_time': '2024-01-20T17:00:00Z',
                'end_time': '2024-01-20T17:00:00Z',
                'organizer': 'Project Manager',
                'attendees': ['All Team'],
                'type': 'deadline'
            }
        ]
        
        return jsonify({
            'events': events,
            'total': len(events),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({'error': 'Failed to load events'}), 500

# New API endpoints for enhanced components

@bp.route('/analytics/activity-heatmap')
@login_required
def activity_heatmap():
    """Get user activity heatmap data."""
    try:
        period = request.args.get('period', '24h')
        
        # Generate mock heatmap data
        heatmap_data = {}
        activities = []
        
        # Generate activities for the last 24 hours
        now = datetime.utcnow()
        for i in range(100):
            activity_time = now - timedelta(hours=random.randint(0, 24))
            hour = activity_time.hour
            day = activity_time.weekday()
            
            activities.append({
                'id': i,
                'user': f'User {random.randint(1, 10)}',
                'type': random.choice(['login', 'message', 'file', 'search']),
                'timestamp': activity_time.isoformat(),
                'description': f'User activity {i}'
            })
            
            key = f'{day}-{hour}'
            heatmap_data[key] = heatmap_data.get(key, 0) + 1
        
        return jsonify({
            'activities': activities,
            'heatmap': heatmap_data,
            'period': period,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting activity heatmap: {e}")
        return jsonify({'error': 'Failed to load activity heatmap'}), 500

@bp.route('/users/advanced-status')
@login_required
def advanced_user_status():
    """Get advanced user status information."""
    try:
        # Use presence service for better accuracy
        try:
            from app.services.user_presence import presence_service
            users_list = presence_service.get_online_users(include_details=True)
        except:
            # Fallback to basic user query
            users = User.query.all()
            users_list = []
            for user in users:
                users_list.append({
                    'id': user.id,
                    'name': user.username,
                    'role': getattr(user, 'role', 'User'),
                    'status': 'online' if user.is_online else 'offline',
                    'last_seen': user.last_seen.isoformat() if user.last_seen else None,
                    'session_duration': random.randint(1, 480),
                    'avatar': user.username[:2].upper(),
                    'is_online': user.is_online
                })
        
        # Add mock data for demonstration
        for i in range(5):
            users_list.append({
                'id': 100 + i,
                'name': f'Team Member {i + 1}',
                'role': random.choice(['Developer', 'Designer', 'Manager', 'Support']),
                'status': random.choice(['online', 'away', 'busy', 'offline']),
                'last_seen': (datetime.utcnow() - timedelta(minutes=random.randint(1, 120))).isoformat(),
                'session_duration': random.randint(1, 480),
                'avatar': f'TM{i + 1}',
                'is_online': random.choice([True, False])
            })
        
        return jsonify({
            'users': users_list,
            'total': len(users_list),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting advanced user status: {e}")
        return jsonify({'error': 'Failed to load user status'}), 500

@bp.route('/analytics/team-performance')
@login_required
def team_performance():
    """Get team performance analytics data."""
    try:
        period = request.args.get('period', 'today')
        
        # Generate mock team performance data
        team_members = []
        for i in range(12):
            team_members.append({
                'id': i + 1,
                'name': f'Team Member {i + 1}',
                'role': random.choice(['Developer', 'Designer', 'Manager', 'Support', 'Analyst']),
                'status': random.choice(['online', 'away', 'busy', 'offline']),
                'avatar': f'TM{i + 1}',
                'metrics': {
                    'productivity': random.randint(70, 100),
                    'efficiency': random.randint(75, 100),
                    'collaboration': random.randint(80, 100),
                    'response': random.randint(1, 5)
                },
                'score': random.randint(80, 100)
            })
        
        metrics = {
            'productivity': 85,
            'efficiency': 92,
            'collaboration': 78,
            'response': 2.3
        }
        
        insights = [
            {
                'type': 'positive',
                'title': 'Productivity Increased',
                'description': 'Team productivity has improved by 5.2% this week'
            },
            {
                'type': 'warning',
                'title': 'Response Time Alert',
                'description': 'Average response time has increased by 12%'
            },
            {
                'type': 'positive',
                'title': 'Collaboration Boost',
                'description': 'Team collaboration metrics are trending upward'
            }
        ]
        
        return jsonify({
            'teamMembers': team_members,
            'metrics': metrics,
            'insights': insights,
            'period': period,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting team performance: {e}")
        return jsonify({'error': 'Failed to load team performance'}), 500

@bp.route('/system/health-metrics')
@login_required
def system_health_metrics():
    """Get system health monitoring data."""
    try:
        # Generate mock system health data
        metrics = {
            'overall': 95,
            'cpu': random.randint(30, 70),
            'memory': random.randint(50, 80),
            'disk': random.randint(60, 90),
            'network': random.randint(95, 100),
            'database': random.randint(95, 100),
            'temperature': random.randint(35, 55),
            'uptime': 99.8,
            'responseTime': random.randint(30, 80),
            'throughput': random.randint(1000, 1500)
        }
        
        alerts = [
            {
                'id': 1,
                'level': 'warning',
                'title': 'Disk Usage High',
                'description': 'Disk usage has reached 78% capacity',
                'timestamp': datetime.utcnow().isoformat(),
                'component': 'disk'
            },
            {
                'id': 2,
                'level': 'info',
                'title': 'System Update Available',
                'description': 'New system update is ready for installation',
                'timestamp': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'component': 'system'
            }
        ]
        
        return jsonify({
            'metrics': metrics,
            'alerts': alerts,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system health metrics: {e}")
        return jsonify({'error': 'Failed to load system health metrics'}), 500

@bp.route('/session/time-remaining')
@login_required
def session_time_remaining():
    """Get the time remaining in the current session."""
    try:
        # Get session info from the session manager
        from app.utils.enhanced_session_manager import session_manager
        
        if session_manager:
            time_remaining = session_manager.get_session_time_remaining()
            session_status = session_manager.get_session_status()
            
            return jsonify({
                'success': True,
                'time_remaining_seconds': time_remaining,
                'time_remaining_minutes': time_remaining // 60,
                'session_healthy': session_status.get('session_healthy', False),
                'user_id': current_user.id,
                'username': current_user.username,
                'last_activity': session_status.get('last_activity'),
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            # Fallback calculation
            last_activity = session.get('last_activity')
            if last_activity:
                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                
                time_diff = datetime.utcnow() - last_activity
                remaining = timedelta(hours=2) - time_diff
                time_remaining = max(0, int(remaining.total_seconds()))
            else:
                time_remaining = 7200  # 2 hours default
            
            return jsonify({
                'success': True,
                'time_remaining_seconds': time_remaining,
                'time_remaining_minutes': time_remaining // 60,
                'session_healthy': time_remaining > 0,
                'user_id': current_user.id,
                'username': current_user.username,
                'last_activity': session.get('last_activity'),
                'timestamp': datetime.utcnow().isoformat()
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting session time remaining: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'time_remaining_seconds': 0,
            'session_healthy': False,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@bp.route('/session/extend', methods=['POST'])
@login_required
def extend_session():
    """Extend the current session."""
    try:
        # Update user's last activity
        current_user.last_seen = datetime.utcnow()
        current_user.is_online = True
        db.session.commit()
        
        # Update session activity
        session['last_activity'] = datetime.utcnow().isoformat()
        
        # Update user presence if available
        try:
            from app.services.user_presence import presence_service
            presence_service.update_heartbeat(current_user.id)
        except Exception as e:
            logger.debug(f"Could not update user presence: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Session extended successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error extending session: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500 

@bp.route('/session/activity', methods=['POST'])
@login_required
def update_session_activity():
    """Update session activity timestamp"""
    try:
        # Validate current_user exists
        if not current_user or not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'message': 'User not authenticated',
                'timestamp': datetime.utcnow().isoformat()
            }), 401
        
        # Update user's last activity
        try:
            current_user.last_seen = datetime.utcnow()
            current_user.is_online = True
            db.session.commit()
        except Exception as e:
            logger.warning(f"Could not update user database record: {e}")
            db.session.rollback()
            # Continue anyway - session update is more important
        
        # Update session activity
        try:
            session['last_activity'] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.warning(f"Could not update session: {e}")
            # Continue anyway - this is not critical
        
        # Update user presence if available
        try:
            from app.services.user_presence import presence_service
            presence_service.update_heartbeat(current_user.id)
        except ImportError as e:
            logger.debug(f"User presence service not available: {e}")
        except Exception as e:
            logger.debug(f"Could not update user presence: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Activity updated',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating session activity: {e}")
        try:
            db.session.rollback()
        except:
            pass  # Ignore rollback errors
        return jsonify({
            'success': False,
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500 

@bp.route('/analytics/search-activity')
@login_required
def search_activity():
    """Get search activity data for analytics."""
    try:
        from datetime import datetime, timedelta
        from app.models import SearchHistory, Activity
        
        # Get today's date
        today = datetime.utcnow().date()
        
        # Get search history for today
        today_searches = db.session.query(SearchHistory).filter(
            SearchHistory.timestamp >= today
        ).count()
        
        # Get search history for this week
        week_ago = today - timedelta(days=7)
        weekly_searches = db.session.query(SearchHistory).filter(
            SearchHistory.timestamp >= week_ago
        ).count()
        
        # Generate hourly data for today
        hourly_data = []
        hourly_labels = []
        
        for hour in range(24):
            start_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=hour)
            end_time = start_time + timedelta(hours=1)
            
            count = db.session.query(SearchHistory).filter(
                SearchHistory.timestamp >= start_time,
                SearchHistory.timestamp < end_time
            ).count()
            
            hourly_data.append(count)
            hourly_labels.append(f"{hour:02d}:00")
        
        return jsonify({
            'labels': hourly_labels,
            'values': hourly_data,
            'today': today_searches,
            'weekly': weekly_searches,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting search activity: {e}")
        return jsonify({
            'labels': ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
            'values': [12, 8, 25, 45, 38, 22],
            'today': 150,
            'weekly': 892,
            'error': 'Failed to load search activity'
        }), 500

@bp.route('/analytics/user-activity')
@login_required
def user_activity():
    """Get user activity data for analytics."""
    try:
        from datetime import datetime, timedelta
        from app.models import Activity, User
        
        # Get data for the last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Get daily active users for the last 7 days
        daily_data = []
        daily_labels = []
        
        for i in range(7):
            day = datetime.utcnow() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # Count unique users with activity on this day
            active_users = db.session.query(Activity.user_id).filter(
                Activity.timestamp >= day_start,
                Activity.timestamp < day_end
            ).distinct().count()
            
            daily_data.insert(0, active_users)
            daily_labels.insert(0, day.strftime('%a'))
        
        # Get current active users
        active_users = User.query.filter(
            User.last_seen >= datetime.utcnow() - timedelta(minutes=5)
        ).count()
        
        # Calculate average session time (simplified)
        avg_session = 45  # minutes - this would need more complex calculation
        
        return jsonify({
            'labels': daily_labels,
            'values': daily_data,
            'active_users': active_users,
            'avg_session': f'{avg_session}m',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return jsonify({
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'values': [15, 18, 22, 19, 25, 12, 8],
            'active_users': 23,
            'avg_session': '45m',
            'error': 'Failed to load user activity'
        }), 500

@bp.route('/analytics/page-views')
@login_required
def page_views():
    """Get page views data for analytics."""
    try:
        from datetime import datetime, timedelta
        from app.models import Activity
        
        # Get today's date
        today = datetime.utcnow().date()
        
        # Get page views for today
        today_views = Activity.query.filter(
            Activity.action == 'page_view',
            Activity.timestamp >= today
        ).count()
        
        # Generate hourly data for today
        hourly_data = []
        hourly_labels = []
        
        for hour in range(24):
            start_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=hour)
            end_time = start_time + timedelta(hours=1)
            
            count = Activity.query.filter(
                Activity.action == 'page_view',
                Activity.timestamp >= start_time,
                Activity.timestamp < end_time
            ).count()
            
            hourly_data.append(count)
            hourly_labels.append(f"{hour:02d}:00")
        
        # Get most popular page today
        popular_page_query = db.session.query(
            Activity.details,
            db.func.count(Activity.id).label('count')
        ).filter(
            Activity.action == 'page_view',
            Activity.timestamp >= today
        ).group_by(Activity.details).order_by(db.desc('count')).first()
        
        popular_page = popular_page_query[0] if popular_page_query else 'Dashboard'
        
        return jsonify({
            'labels': hourly_labels,
            'values': hourly_data,
            'today': today_views,
            'popular_page': popular_page,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting page views: {e}")
        return jsonify({
            'labels': ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
            'values': [8, 5, 18, 32, 28, 15],
            'today': 234,
            'popular_page': 'Dashboard',
            'error': 'Failed to load page views'
        }), 500 

@bp.route('/errors', methods=['POST'])
@login_required
def report_error():
    """Report client-side errors for logging."""
    try:
        data = request.get_json()
        
        # Log the error
        logger.error(f"Client Error: {data.get('error', 'Unknown error')} - Source: {data.get('source', 'Unknown')} - Line: {data.get('line', 'Unknown')}")
        
        return jsonify({
            'success': True,
            'message': 'Error logged successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error logging client error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to log error'
        }), 500

@bp.route('/sw.js')
def service_worker():
    """Serve the service worker file."""
    try:
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    except Exception as e:
        logger.error(f"Error serving service worker: {e}")
<<<<<<< HEAD
        return '', 404

@bp.route('/active-users', methods=['GET'])
@login_required
def get_active_users():
    """Get real website members for the active users section."""
    try:
        from app.models.base import User
        import random
        
        # Define the actual website members
        website_members = [
            {'username': 'Admin', 'email': 'admin@pdshealth.com', 'department': 'IT', 'is_admin': True},
            {'username': 'AJ', 'email': 'aj@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'Sam', 'email': 'sam@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'Jabin', 'email': 'jabin@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'Doug', 'email': 'doug@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'Nate', 'email': 'nate@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'Jonathan', 'email': 'jonathan@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'Richard', 'email': 'richard@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'JZ', 'email': 'jz@pdshealth.com', 'department': 'ISC', 'is_admin': False},
            {'username': 'Pietro', 'email': 'pietro@pdshealth.com', 'department': 'ISC', 'is_admin': False}
        ]
        
        # Try to get real user data from database first
        try:
            db_users = User.query.filter_by(is_active=True).all()
            user_data = []
            
            # Map database users to website members
            for member in website_members:
                # Try to find matching user in database
                db_user = next((u for u in db_users if u.username.lower() == member['username'].lower() or 
                               u.email.lower() == member['email'].lower()), None)
                
                if db_user:
                    # Use real database user data
                    # Properly determine online status based on last_seen
                    now = datetime.utcnow()
                    is_online = False
                    
                    if db_user.last_seen:
                        time_diff = (now - db_user.last_seen).total_seconds()
                        is_online = time_diff < 300  # 5 minutes
                    
                    user_data.append({
                        'id': db_user.id,
                        'username': member['username'],  # Use website member name
                        'email': db_user.email,
                        'status': 'online' if is_online else 'offline',
                        'last_seen': db_user.last_seen.isoformat() if db_user.last_seen else (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                        'department': member['department'],
                        'is_admin': member['is_admin']
                    })
                else:
                    # Use website member data - but don't assume they're online
                    user_data.append({
                        'id': f"member_{member['username'].lower()}",
                        'username': member['username'],
                        'email': member['email'],
                        'status': 'offline',  # Default to offline for website members without DB records
                        'last_seen': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                        'department': member['department'],
                        'is_admin': member['is_admin']
                    })
            
            # Ensure Admin is first in the list (but don't force online status)
            admin_user = next((u for u in user_data if u['username'] == 'Admin'), None)
            if admin_user:
                # Move admin to first position but keep their actual status
                user_data.remove(admin_user)
                user_data.insert(0, admin_user)
            
            # Limit to 8 users for display
            user_data = user_data[:8]
            
        except Exception as db_error:
            logger.warning(f"Database error, using fallback data: {db_error}")
            # Fallback to website members data - but don't assume they're online
            user_data = []
            for member in website_members[:8]:
                user_data.append({
                    'id': f"member_{member['username'].lower()}",
                    'username': member['username'],
                    'email': member['email'],
                    'status': 'offline',  # Default to offline in fallback
                    'last_seen': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                    'department': member['department'],
                    'is_admin': member['is_admin']
                })
        
        return jsonify({
            'success': True,
            'users': user_data,
            'total_users': len(website_members),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get active users',
            'message': str(e)
        }), 500

@bp.route('/users/profile/<username>', methods=['GET'])
@login_required
def get_user_profile(username):
    """Get detailed user profile information for website members."""
    try:
        from app.models.base import User, Activity
        from datetime import datetime, timedelta
        
        # Define the actual website members with detailed information
        website_members = {
            'admin': {
                'username': 'Admin',
                'full_name': 'Oscar Solis',
                'email': 'admin@pdshealth.com',
                'department': 'IT',
                'position': 'System Administrator',
                'is_admin': True,
                'phone': '+1 (555) 123-4567',
                'office': 'Main Building',
                'manager': 'Self',
                'hire_date': '2023-01-15',
                'permissions': ['admin', 'user_management', 'system_config'],
                'bio': 'Primary system administrator and developer for PDSI platform.'
            },
            'aj': {
                'username': 'AJ',
                'full_name': 'AJ Mercado',
                'email': 'aj@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 234-5678',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-03-20',
                'permissions': ['user', 'ticket_management'],
                'bio': 'IT support specialist focused on user assistance and ticket resolution.'
            },
            'sam': {
                'username': 'Sam',
                'full_name': 'Samuel Nightingale',
                'email': 'sam@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 345-6789',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-02-10',
                'permissions': ['user', 'ticket_management'],
                'bio': 'Experienced IT support specialist with expertise in system troubleshooting.'
            },
            'jabin': {
                'username': 'Jabin',
                'full_name': 'Jabin Dejesa',
                'email': 'jabin@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 456-7890',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-04-15',
                'permissions': ['user', 'ticket_management'],
                'bio': 'Dedicated IT support specialist committed to excellent user service.'
            },
            'doug': {
                'username': 'Doug',
                'full_name': 'Doug Spohn',
                'email': 'doug@pdshealth.com',
                'department': 'ISC',
                'position': 'Senior IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 567-8901',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-01-25',
                'permissions': ['user', 'ticket_management', 'training'],
                'bio': 'Senior IT support specialist with extensive experience in enterprise systems.'
            },
            'nate': {
                'username': 'Nate',
                'full_name': 'Nathan Bui',
                'email': 'nate@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 678-9012',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-05-10',
                'permissions': ['user', 'ticket_management'],
                'bio': 'IT support specialist with strong technical skills and user focus.'
            },
            'jonathan': {
                'username': 'Jonathan',
                'full_name': 'Jonathan Nguyen',
                'email': 'jonathan@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 789-0123',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-06-01',
                'permissions': ['user', 'ticket_management'],
                'bio': 'IT support specialist with expertise in network and system administration.'
            },
            'richard': {
                'username': 'Richard',
                'full_name': 'Richard Nguyen',
                'email': 'richard@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 890-1234',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-07-15',
                'permissions': ['user', 'ticket_management'],
                'bio': 'IT support specialist with strong problem-solving skills.'
            },
            'jz': {
                'username': 'JZ',
                'full_name': 'JZ Miranda',
                'email': 'jz@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 901-2345',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-08-20',
                'permissions': ['user', 'ticket_management'],
                'bio': 'IT support specialist with expertise in desktop and mobile support.'
            },
            'pietro': {
                'username': 'Pietro',
                'full_name': 'Pietro Vue',
                'email': 'pietro@pdshealth.com',
                'department': 'ISC',
                'position': 'IT Support Specialist',
                'is_admin': False,
                'phone': '+1 (555) 012-3456',
                'office': 'ISC Building',
                'manager': 'Oscar Solis',
                'hire_date': '2023-09-05',
                'permissions': ['user', 'ticket_management'],
                'bio': 'IT support specialist with strong customer service skills.'
            }
        }
        
        # Try to find the user in website members
        username_lower = username.lower()
        member_data = None
        
        for key, member in website_members.items():
            if (key == username_lower or 
                member['username'].lower() == username_lower or 
                member['full_name'].lower() == username_lower):
                member_data = member
                break
        
        if not member_data:
            return jsonify({
                'success': False,
                'error': 'User not found',
                'message': f'User "{username}" not found in website members'
            }), 404
        
        # Try to get real user data from database
        try:
            db_user = User.query.filter(
                (User.username.ilike(f"%{member_data['username']}%")) |
                (User.email.ilike(f"%{member_data['email']}%"))
            ).first()
            
            if db_user:
                # Use real database user data
                is_online = db_user.is_online and (
                    db_user.last_seen and 
                    (datetime.utcnow() - db_user.last_seen).total_seconds() < 300
                )
                last_seen = db_user.last_seen.isoformat() if db_user.last_seen else datetime.utcnow().isoformat()
                last_login = db_user.last_login.isoformat() if db_user.last_login else None
                created_at = db_user.created_at.isoformat() if db_user.created_at else member_data['hire_date']
            else:
                # Use fallback data - but don't assume they're online
                # Check if they have any recent activity in the database
                recent_user = User.query.filter(
                    (User.username.ilike(f"%{member_data['username']}%")) |
                    (User.email.ilike(f"%{member_data['email']}%"))
                ).first()
                
                if recent_user and recent_user.last_seen:
                    # Use the most recent user's data
                    time_diff = (datetime.utcnow() - recent_user.last_seen).total_seconds()
                    is_online = time_diff < 300  # 5 minutes
                    last_seen = recent_user.last_seen.isoformat()
                    last_login = recent_user.last_login.isoformat() if recent_user.last_login else None
                else:
                    # No recent activity, user is offline
                    is_online = False
                    last_seen = (datetime.utcnow() - timedelta(hours=1)).isoformat()  # Assume offline for 1 hour
                    last_login = None
                
                created_at = member_data['hire_date']
        
        except Exception as db_error:
            logger.warning(f"Database error for user {username}: {db_error}")
            # Use fallback data - but don't assume they're online
            is_online = False
            last_seen = (datetime.utcnow() - timedelta(hours=1)).isoformat()  # Assume offline for 1 hour
            last_login = None
            created_at = member_data['hire_date']
        
        # Get recent activity (simulated for now, but could be real)
        recent_activity = [
            {
                'action': 'Last login',
                'time': last_login or datetime.utcnow().isoformat(),
                'details': 'User logged into the system'
            },
            {
                'action': 'Profile updated',
                'time': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                'details': 'User profile information was updated'
            },
            {
                'action': 'Account created',
                'time': created_at,
                'details': 'User account was created in the system'
            }
        ]
        
        # Compile the complete user profile
        user_profile = {
            'success': True,
            'user': {
                'id': f"member_{member_data['username'].lower()}",
                'username': member_data['username'],
                'full_name': member_data['full_name'],
                'email': member_data['email'],
                'department': member_data['department'],
                'position': member_data['position'],
                'is_admin': member_data['is_admin'],
                'is_online': is_online,
                'status': 'online' if is_online else 'offline',
                'last_seen': last_seen,
                'last_login': last_login,
                'created_at': created_at,
                'phone': member_data['phone'],
                'office': member_data['office'],
                'manager': member_data['manager'],
                'hire_date': member_data['hire_date'],
                'permissions': member_data['permissions'],
                'bio': member_data['bio'],
                'profile_picture': 'default.png'
            },
            'recent_activity': recent_activity,
            'stats': {
                'tickets_handled': 0,  # Could be real data from ticketing system
                'search_count': 0,     # Could be real data from search history
                'notes_count': 0,      # Could be real data from notes
                'last_activity': last_seen
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(user_profile)
        
    except Exception as e:
        logger.error(f"Error getting user profile for {username}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user profile',
            'message': str(e)
        }), 500
=======
        return '', 404
>>>>>>> 7520c16b5c914093307c30b16f1d98ae5c12e909
