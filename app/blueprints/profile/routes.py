from flask import jsonify, request, render_template, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from . import bp
from app.extensions import db
from app.models import User
import logging

logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
def profile():
    """Render the profile page"""
    return render_template('profile/index.html')

@bp.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile"""
    try:
        return jsonify(current_user.to_dict())
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        user = User.query.get(current_user.id)
        
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
            
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/profile/password', methods=['PUT'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        user = User.query.get(current_user.id)
        
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400
            
        user.set_password(data['new_password'])
        db.session.commit()
        return jsonify({'message': 'Password updated successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing password: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/profile/picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Upload profile picture"""
    try:
        if 'picture' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['picture']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{current_user.id}_{file.filename}")
            upload_dir = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
            profile_pictures_dir = os.path.join(upload_dir, 'profile_pictures')
            os.makedirs(profile_pictures_dir, exist_ok=True)
            filepath = os.path.join(profile_pictures_dir, filename)
            file.save(filepath)
            
            user = User.query.get(current_user.id)
            user.profile_picture = filename
            db.session.commit()
            
            return jsonify({'message': 'Profile picture uploaded successfully'})
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading profile picture: {str(e)}")
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    """Check if file type is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 