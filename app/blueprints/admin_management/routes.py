import logging
from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from . import bp

logger = logging.getLogger(__name__)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    if request.method == 'GET':
        return jsonify({
            'teams_webhook': current_app.config.get('TEAMS_WEBHOOK_URL', ''),
            'default_role': current_app.config.get('DEFAULT_USER_ROLE', 'user'),
            'require_okta': current_app.config.get('REQUIRE_OKTA', False)
        })
        
    elif request.method == 'POST':
        data = request.get_json()
        
        # Update settings
        if 'teams_webhook' in data:
            current_app.config['TEAMS_WEBHOOK_URL'] = data['teams_webhook']
        if 'default_role' in data:
            current_app.config['DEFAULT_USER_ROLE'] = data['default_role']
        if 'require_okta' in data:
            current_app.config['REQUIRE_OKTA'] = data['require_okta']
            
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        }) 