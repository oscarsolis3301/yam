from flask import jsonify, request, render_template, current_app
from flask_login import login_required, current_user
from . import bp
from app.extensions import db
from app.models import User, UserSettings
import logging

logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
def settings():
    """Render the settings page"""
    # Use the legacy template path so existing front-end links keep working.
    return render_template('settings.html')

@bp.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get user settings"""
    try:
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
            db.session.commit()
        return jsonify(settings.to_dict())
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/settings', methods=['PUT'])
@login_required
def update_settings():
    """Update user settings"""
    try:
        data = request.get_json()
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
        
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        db.session.commit()
        return jsonify(settings.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/settings/notifications', methods=['PUT'])
@login_required
def update_notification_settings():
    """Update notification settings"""
    try:
        data = request.get_json()
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
        
        if 'email_notifications' in data:
            settings.email_notifications = data['email_notifications']
        if 'push_notifications' in data:
            settings.push_notifications = data['push_notifications']
        if 'notification_frequency' in data:
            settings.notification_frequency = data['notification_frequency']
        
        db.session.commit()
        return jsonify(settings.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating notification settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/settings/privacy', methods=['PUT'])
@login_required
def update_privacy_settings():
    """Update privacy settings"""
    try:
        data = request.get_json()
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
        
        if 'profile_visibility' in data:
            settings.profile_visibility = data['profile_visibility']
        if 'activity_visibility' in data:
            settings.activity_visibility = data['activity_visibility']
        if 'search_visibility' in data:
            settings.search_visibility = data['search_visibility']
        
        db.session.commit()
        return jsonify(settings.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating privacy settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/settings/appearance', methods=['PUT'])
@login_required
def update_appearance_settings():
    """Update appearance settings"""
    try:
        data = request.get_json()
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
        
        if 'theme' in data:
            settings.theme = data['theme']
        if 'font_size' in data:
            settings.font_size = data['font_size']
        if 'color_scheme' in data:
            settings.color_scheme = data['color_scheme']
        
        db.session.commit()
        return jsonify(settings.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating appearance settings: {str(e)}")
        return jsonify({'error': str(e)}), 500 