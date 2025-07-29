from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from rapidfuzz import process, fuzz
from app.blueprints.devices.routes import load_devices_cache
from app.extensions import db

from . import bp  # Blueprint instance

@bp.route('', methods=['GET', 'POST'])
@login_required
def workstations():
    """Render workstation page on GET or lookup workstation details on POST."""
    if request.method == 'POST':
        computer = (request.json or {}).get('computer', '').strip()
        if not computer:
            return jsonify({'error': 'No workstation provided.'}), 400
        try:
            devices = load_devices_cache()
            # Exact match
            device = next((d for d in devices if d.get('Device name', '').lower() == computer.lower()), None)
            if not device:
                device_names = [d.get('Device name', '') for d in devices]
                matches = process.extract(computer, device_names, scorer=fuzz.WRatio, limit=1)
                if matches and matches[0][1] > 60:
                    device = next((d for d in devices if d.get('Device name', '') == matches[0][0]), None)
            if not device:
                return jsonify({'error': 'Workstation not found.'}), 404
            response = {
                'Name': device.get('Device name', ''),
                'OS': device.get('OS', ''),
                'Version': device.get('OS version', ''),
                'User': device.get('Primary user UPN', ''),
                'ManagedBy': device.get('Managed by', ''),
                'Compliance': device.get('Compliance', '')
            }
            return jsonify(response), 200
        except Exception as e:
            return jsonify({'error': f'Error searching workstations: {str(e)}'}), 500

    # GET request – render page (retain original template path)
    return render_template('workstations.html', active_page='workstations')

@bp.route('/api/workstations/detail')
@login_required
def workstation_detail():
    """Get detailed information for a specific workstation by name."""
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Workstation name is required'}), 400
    
    try:
        devices = load_devices_cache()
        
        # Try exact match first
        device = next((d for d in devices if d.get('Device name', '').lower() == name.lower()), None)
        
        if not device:
            # Try fuzzy matching if exact match fails
            device_names = [d.get('Device name', '') for d in devices]
            matches = process.extract(name, device_names, scorer=fuzz.WRatio, limit=1)
            
            if matches and matches[0][1] > 80:  # High confidence threshold
                best_match_name = matches[0][0]
                device = next((d for d in devices if d.get('Device name', '') == best_match_name), None)
        
        if not device:
            return jsonify({'error': 'Workstation not found'}), 404
        
        # Try to resolve IP address if not already available
        ip_address = device.get('IPv4Address', '')
        if not ip_address:
            try:
                import socket
                ip_address = socket.gethostbyname(device.get('Device name', ''))
            except (socket.gaierror, socket.herror):
                ip_address = 'N/A'
        
        return jsonify({
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
            'online': device.get('Online', False)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error searching workstations: {str(e)}'}), 500 