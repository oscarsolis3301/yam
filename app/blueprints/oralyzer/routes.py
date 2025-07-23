from flask import render_template
from flask_login import login_required

from . import bp


@bp.route('/', methods=['GET'])
@login_required
def oralyzer_home():
    """Render the main Oralyzer page (previously /oralyzer)."""
    return render_template('oralyzer.html', active_page='oralyzer')


@bp.route('/clean', methods=['GET'])
@login_required
def oralyzer_clean():
    """Render the Oralyzer clean page (previously /oralyzer/clean)."""
    return render_template('oralyzer_clean.html')


@bp.route('/dashboard', methods=['GET'])
@login_required
def oralyzer_dashboard():
    """Render the Oralyzer dashboard page with static ticket stats (previously /oralyzer/dashboard)."""
    # Get ticket statistics (placeholder values)
    total_tickets = 15  # Replace with actual database query
    active_tickets = 8  # Replace with actual database query
    resolved_tickets = 7  # Replace with actual database query

    # Get recent tickets (placeholder data)
    tickets = [
        {
            'id': 1,
            'title': 'Calibration Required',
            'description': 'Device needs routine calibration check',
            'status': 'active',
            'created_at': '2024-03-28 10:30:00'
        },
        {
            'id': 2,
            'title': 'Software Update Available',
            'description': 'New firmware version 2.1.0 ready for installation',
            'status': 'pending',
            'created_at': '2024-03-27 14:15:00'
        }
    ]

    return render_template(
        'oralyzer_dashboard.html',
        active_page='oralyzer',
        total_tickets=total_tickets,
        active_tickets=active_tickets,
        resolved_tickets=resolved_tickets,
        tickets=tickets
    ) 