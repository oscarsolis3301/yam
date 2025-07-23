from flask import Blueprint, jsonify, current_app
from flask_login import login_required
from datetime import datetime, timedelta
from flask_socketio import emit
import os
import requests
import psutil

from extensions import db, socketio
from app.models import User, Outage, Activity

bp = Blueprint('system', __name__, url_prefix='/api')

# ---------------------------------------------------------------------------
# Weather Endpoint
# ---------------------------------------------------------------------------

@bp.route('/weather')
@login_required
def get_weather():
    """Return current weather information for the configured CITY using the
    OpenWeatherMap API.  Falls back to the same hard-coded values that existed
    previously if environment variables are not provided, so behaviour remains
    identical to the old implementation.
    """
    try:
        # You can override these via environment variables if desired
        api_key = os.getenv('WEATHER_API_KEY', 'YOUR_WEATHER_API_KEY')
        city = os.getenv('WEATHER_CITY', 'Your City')

        response = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={
                'q': city,
                'appid': api_key,
                'units': 'imperial'
            }
        )
        data = response.json()

        return jsonify({
            'temperature': round(data['main']['temp']),
            'humidity': data['main']['humidity'],
            'wind_speed': round(data['wind']['speed']),
            'condition': data['weather'][0]['main'],
            'location': data['name']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
# Birthdays Endpoint
# ---------------------------------------------------------------------------

@bp.route('/birthdays')
@login_required
def get_birthdays():
    """Return a list of users whose birthday is today."""
    try:
        today = datetime.now()
        birthdays = User.query.filter(
            db.extract('month', User.birthday) == today.month,
            db.extract('day', User.birthday) == today.day
        ).all()

        return jsonify([
            {
                'name': user.name,
                'department': user.department
            }
            for user in birthdays
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
# Admin Dashboard Endpoint
# ---------------------------------------------------------------------------

@bp.route('/admin/dashboard')
@login_required
def admin_dashboard_data():
    """Return dashboard metrics used by the admin panel."""
    try:
        now = datetime.utcnow()

        total_users = User.query.count()
        active_sessions = User.query.filter(
            User.last_seen >= now - timedelta(minutes=5)
        ).count()

        try:
            active_outages = Outage.query.filter_by(status='active').count()
        except Exception as e:
            current_app.logger.warning(f'Could not get outage count: {e}')
            active_outages = 0

        users = User.query.all()
        users_list = [
            {
                'id': user.id,
                'name': user.username,
                'email': user.email,
                'role': user.role,
                'profile_picture': user.profile_picture or 'default.png',
                'is_online': user.is_online and (now - user.last_seen).total_seconds() < 300 if user.last_seen else False,
                'last_seen': user.last_seen.isoformat() if user.last_seen else None,
            }
            for user in users
        ]

        return jsonify({
            'total_users': total_users,
            'active_sessions': active_sessions,
            'active_outages': active_outages,
            'online_users': users_list,
        })

    except Exception as e:
        current_app.logger.error(f'Error getting dashboard data: {e}')
        return (
            jsonify(
                {
                    'error': 'Error loading dashboard data',
                    'total_users': 0,
                    'active_sessions': 0,
                    'active_outages': 0,
                    'online_users': [],
                }
            ),
            500,
        )

# ---------------------------------------------------------------------------
# Socket.IO Handlers
# ---------------------------------------------------------------------------

@socketio.on('get_system_status')
def handle_system_status():
    """Emit current system resource usage to the requesting client."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        network = psutil.net_io_counters()
        network_status = 'Connected' if network.bytes_sent > 0 or network.bytes_recv > 0 else 'Disconnected'

        emit(
            'system_status',
            {
                'cpu': cpu_percent,
                'memory': memory_percent,
                'disk': disk_percent,
                'network': network_status,
            },
        )
    except Exception as e:
        emit('system_status', {'error': str(e)})


@socketio.on('get_recent_activity')
def handle_recent_activity():
    """Emit the 10 most recent Activity rows to the client."""
    try:
        activities = Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()
        emit(
            'recent_activity',
            [
                {
                    'type': activity.type,
                    'description': activity.description,
                    'timestamp': activity.timestamp.isoformat(),
                }
                for activity in activities
            ],
        )
    except Exception as e:
        emit('recent_activity', [{'error': str(e)}]) 