from flask import jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import UserSettings
from . import bp
import logging
from app.utils.remote_session import encrypt_password, decrypt_password

logger = logging.getLogger(__name__)


def _get_or_create_settings():
    """Helper to fetch the current user's UserSettings row.

    If the row does not yet exist (first time the user touches their settings)
    we create it so that subsequent updates work transparently.
    """
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()
    return settings


# ---------------------------------------------------------------------------
# Notification Settings
# ---------------------------------------------------------------------------

@bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    """Get or update the current user's notification settings.

    • **GET** – returns the current notification settings.
    • **POST** – accepts a JSON payload to update the settings.
    """
    try:
        settings = _get_or_create_settings()

        if request.method == 'POST':
            data = request.get_json() or {}
            # Update notification-related fields only if present in the payload
            if 'email_notifications' in data:
                settings.email_notifications = data['email_notifications']
            if 'browser_notifications' in data:
                settings.browser_notifications = data['browser_notifications']
            if 'notification_frequency' in data:
                settings.notification_frequency = data['notification_frequency']

            db.session.commit()
            msg = 'Notification settings updated successfully'
        else:
            # GET request – no changes, just serialise existing settings.
            msg = 'Notification settings retrieved successfully'

        response = {
            'message': msg,
            'settings': {
                'email_notifications': settings.email_notifications,
                'browser_notifications': settings.browser_notifications,
                'notification_frequency': settings.notification_frequency,
            }
        }
        return jsonify(response)
    except Exception as exc:
        logger.exception('Failed to process notification settings')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Privacy Settings
# ---------------------------------------------------------------------------

@bp.route('/privacy', methods=['GET', 'POST'])
@login_required
def privacy():
    """Get or update the current user's privacy settings.

    • **GET** – returns the current privacy settings.
    • **POST** – accepts a JSON payload to update the settings.
    """
    try:
        settings = _get_or_create_settings()

        if request.method == 'POST':
            data = request.get_json() or {}
            if 'search_history' in data:
                settings.save_search_history = data['search_history']
            if 'activity_tracking' in data:
                settings.track_activity = data['activity_tracking']
            if 'data_collection' in data:
                settings.allow_data_collection = data['data_collection']

            db.session.commit()
            msg = 'Privacy settings updated successfully'
        else:
            msg = 'Privacy settings retrieved successfully'

        response = {
            'message': msg,
            'settings': {
                'save_search_history': settings.save_search_history,
                'track_activity': settings.track_activity,
                'allow_data_collection': settings.allow_data_collection,
            }
        }
        return jsonify(response)
    except Exception as exc:
        logger.exception('Failed to process privacy settings')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Appearance Settings
# ---------------------------------------------------------------------------

@bp.route('/appearance', methods=['GET', 'POST'])
@login_required
def appearance():
    """Get or update the current user's appearance settings.

    • **GET** – returns the current appearance settings.
    • **POST** – accepts a JSON payload to update the settings.
    """
    try:
        settings = _get_or_create_settings()

        if request.method == 'POST':
            data = request.get_json() or {}
            if 'theme' in data:
                settings.theme = data['theme']
            if 'accent_color' in data:
                settings.accent_color = data['accent_color']
            if 'font_size' in data:
                settings.font_size = data['font_size']

            db.session.commit()
            msg = 'Appearance settings updated successfully'
        else:
            msg = 'Appearance settings retrieved successfully'

        response = {
            'message': msg,
            'settings': {
                'theme': settings.theme,
                'accent_color': settings.accent_color,
                'font_size': settings.font_size,
            },
        }
        return jsonify(response)
    except Exception as exc:
        logger.exception('Failed to process appearance settings')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@bp.route('/dameware_credentials', methods=['GET', 'POST'])
@login_required
def dameware_credentials():
    """Get or update the current user's Dameware credentials (username, domain, password)."""
    try:
        settings = _get_or_create_settings()
        if request.method == 'POST':
            data = request.get_json() or {}
            if 'dameware_username' in data:
                settings.dameware_username = data['dameware_username']
            if 'dameware_domain' in data:
                settings.dameware_domain = data['dameware_domain']
            if 'dameware_password' in data and data['dameware_password']:
                settings.dameware_password_encrypted = encrypt_password(data['dameware_password'])
            if 'dameware_auth_type' in data:
                settings.dameware_auth_type = data['dameware_auth_type']
            db.session.commit()
            msg = 'Dameware credentials updated successfully.'
        else:
            msg = 'Dameware credentials retrieved successfully.'
        # Handle decryption errors gracefully
        try:
            decrypted_password = decrypt_password(settings.dameware_password_encrypted) if settings.dameware_password_encrypted else None
        except Exception as exc:
            decrypted_password = None
            msg = 'Warning: Dameware password could not be decrypted. Please re-enter your credentials.'
        response = {
            'message': msg,
            'credentials': {
                'dameware_username': settings.dameware_username,
                'dameware_domain': settings.dameware_domain,
                'dameware_password': decrypted_password,
                'dameware_auth_type': getattr(settings, 'dameware_auth_type', None)
            }
        }
        return jsonify(response)
    except Exception as exc:
        logger.exception('Failed to process Dameware credentials')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500 