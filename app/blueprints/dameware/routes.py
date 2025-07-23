from flask import render_template, request, jsonify
from flask_login import login_required, current_user
import subprocess
import os
from . import bp
from app.models import UserSettings
from app.utils.remote_session import decrypt_password

@bp.route('/dameware')
@login_required
def dameware_page():
    """Render the Dameware remote connection page"""
    return render_template('dameware.html', active_page='dameware')

@bp.route('/api/dameware/connect', methods=['POST'])
@login_required
def connect_dameware():
    """Launch Dameware connection to specified host using stored credentials if available"""
    try:
        data = request.get_json()
        target_host = data.get('host', '').strip()
        if not target_host:
            return jsonify({'success': False, 'error': 'Host name or IP address is required'}), 400
        
        # Try multiple Dameware paths
        dameware_paths = [
            r"C:\Program Files\SolarWinds\Dameware Mini Remote Control x64\DWRCC.exe",
            r"C:\Program Files\SolarWinds\Dameware Mini Remote Control\DWRCC.exe",
            r"C:\Program Files (x86)\SolarWinds\Dameware Mini Remote Control\DWRCC.exe",
            r"C:\Program Files\SolarWinds\Dameware Remote Support\DWRCC.exe",
            r"C:\Program Files (x86)\SolarWinds\Dameware Remote Support\DWRCC.exe"
        ]
        
        dameware_path = None
        for path in dameware_paths:
            if os.path.exists(path):
                dameware_path = path
                break
        
        if not dameware_path:
            return jsonify({'success': False, 'error': 'Dameware not found. Please ensure it is installed at one of the standard locations.'}), 404
        
        # Fetch user Dameware credentials
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        username = settings.dameware_username if settings else None
        domain = settings.dameware_domain if settings else None
        password = decrypt_password(settings.dameware_password_encrypted) if settings and settings.dameware_password_encrypted else None
        auth_type = getattr(settings, 'dameware_auth_type', None) or '1'  # Default to 1 if not set
        
        # Validate credentials if provided
        if username and not domain:
            return jsonify({'success': False, 'error': 'Domain is required when username is provided'}), 400
        if domain and not username:
            return jsonify({'success': False, 'error': 'Username is required when domain is provided'}), 400
        
        # Build Dameware command with correct parameters
        cmd = [dameware_path, "-c:", f"-m:{target_host}"]
        if username:
            cmd.append(f"-u:{username}")
        if password:
            cmd.append(f"-p:{password}")
        if domain:
            cmd.append(f"-d:{domain}")
        if auth_type:
            cmd.append(f"-a:{auth_type}")
        
        # Launch Dameware process
        process = subprocess.Popen(cmd, shell=True)
        
        return jsonify({
            'success': True, 
            'message': f'Dameware connection initiated to {target_host}',
            'pid': process.pid,
            'command': ' '.join(cmd)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to launch Dameware: {str(e)}'}), 500

@bp.route('/api/dameware/debug', methods=['GET'])
@login_required
def debug_dameware():
    """Debug endpoint to check Dameware installation and configuration"""
    try:
        debug_info = {
            'dameware_paths': [],
            'found_path': None,
            'credentials_configured': False,
            'test_commands': []
        }
        
        # Check Dameware paths
        dameware_paths = [
            r"C:\Program Files\SolarWinds\Dameware Mini Remote Control x64\DWRCC.exe",
            r"C:\Program Files\SolarWinds\Dameware Mini Remote Control\DWRCC.exe",
            r"C:\Program Files (x86)\SolarWinds\Dameware Mini Remote Control\DWRCC.exe",
            r"C:\Program Files\SolarWinds\Dameware Remote Support\DWRCC.exe",
            r"C:\Program Files (x86)\SolarWinds\Dameware Remote Support\DWRCC.exe"
        ]
        
        for path in dameware_paths:
            exists = os.path.exists(path)
            debug_info['dameware_paths'].append({
                'path': path,
                'exists': exists
            })
            if exists and not debug_info['found_path']:
                debug_info['found_path'] = path
        
        # Check credentials
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        if settings:
            debug_info['credentials_configured'] = bool(
                settings.dameware_username and 
                settings.dameware_domain and 
                settings.dameware_password_encrypted
            )
        
        # Generate test commands
        if debug_info['found_path']:
            test_host = "TEST-HOST"
            debug_info['test_commands'] = [
                f'"{debug_info["found_path"]}" -h:{test_host} -c:full-control',
                f'"{debug_info["found_path"]}" -h:{test_host} -c:full-control -m:1',
                f'"{debug_info["found_path"]}" -h:{test_host} -c:full-control -m:1 -v:1'
            ]
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': f'Debug failed: {str(e)}'}), 500 