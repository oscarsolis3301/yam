from flask import render_template, url_for
from flask_login import login_required

from . import bp
from app.models import User
from app.extensions import db


@bp.route('/', methods=['GET'])
@login_required
def team_page():
    """Render the Team page, listing all users with profile information."""
    users = User.query.all()
    users_data = []
    for user in users:
        # Use user's uploaded picture if available; fallback to default
        if user.profile_picture and user.profile_picture.lower() not in ['none', '', 'default.png']:
            img_url = url_for('static', filename=f'uploads/profile_pictures/{user.profile_picture}')
        else:
            img_url = url_for('static', filename='uploads/profile_pictures/boy.png')

        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'profile_picture': img_url,
            'role': getattr(user, 'role', 'Team Member'),
            'department': getattr(user, 'department', 'General'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if getattr(user, 'last_login', None) else 'Never',
            'is_online': getattr(user, 'is_online', False),
            'join_date': user.created_at.strftime('%Y-%m-%d') if getattr(user, 'created_at', None) else 'Unknown',
            'tickets_created': len(user.tickets) if hasattr(user, 'tickets') else 0,
            'tickets_resolved': len([t for t in user.tickets if t.status == 'resolved']) if hasattr(user, 'tickets') else 0,
            'recent_activity': [
                {
                    'action': activity.action,
                    'details': activity.details,
                    'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S') if getattr(activity, 'timestamp', None) else 'Unknown'
                } for activity in user.activities[-5:] if hasattr(user, 'activities')
            ]
        })

    return render_template('team.html', users=users_data) 