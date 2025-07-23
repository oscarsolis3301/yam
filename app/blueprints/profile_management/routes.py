import logging
from flask import jsonify, request, render_template, flash, redirect, url_for, make_response, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from app import db
from app.models import SearchHistory, UserSettings
from . import bp

logger = logging.getLogger(__name__)

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password')
    confirm_password = PasswordField('Confirm Password', validators=[EqualTo('new_password')])
    submit = SubmitField('Update Profile')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        if form.current_password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect', 'danger')
                return render_template('profile.html', form=form)
            
            if form.new_password.data:
                current_user.set_password(form.new_password.data)
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile_management.profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template('profile.html', form=form)

@bp.route('/api/settings/export-data')
@login_required
def export_user_data():
    try:
        # Get user data
        user_data = {
            'profile': {
                'username': current_user.username,
                'email': current_user.email,
                'created_at': current_user.created_at.isoformat(),
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None
            },
            'search_history': [{
                'query': history.query,
                'timestamp': history.timestamp.isoformat()
            } for history in current_user.search_history],
            'settings': {
                'appearance': {
                    'theme': current_user.settings.theme if current_user.settings else 'dark',
                    'accent_color': current_user.settings.accent_color if current_user.settings else '#007bff',
                    'font_size': current_user.settings.font_size if current_user.settings else 'medium'
                },
                'notifications': {
                    'email_notifications': current_user.settings.email_notifications if current_user.settings else True,
                    'browser_notifications': current_user.settings.browser_notifications if current_user.settings else True,
                    'notification_frequency': current_user.settings.notification_frequency if current_user.settings else 'realtime'
                },
                'privacy': {
                    'save_search_history': current_user.settings.save_search_history if current_user.settings else True,
                    'track_activity': current_user.settings.track_activity if current_user.settings else True,
                    'allow_data_collection': current_user.settings.allow_data_collection if current_user.settings else True
                }
            }
        }
        
        # Create JSON response
        response = make_response(jsonify(user_data))
        response.headers['Content-Disposition'] = f'attachment; filename=user-data-{current_user.username}.json'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/settings/clear-activity', methods=['POST'])
@login_required
def clear_activity():
    try:
        # Add activity log clearing logic here
        return jsonify({'message': 'Activity log cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    try:
        data = request.get_json()
        
        # Verify password
        if not current_user.check_password(data['password']):
            return jsonify({'error': 'Incorrect password'}), 400
        
        # Delete user data
        SearchHistory.query.filter_by(user_id=current_user.id).delete()
        UserSettings.query.filter_by(user_id=current_user.id).delete()
        
        # Delete user
        db.session.delete(current_user)
        db.session.commit()
        
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 