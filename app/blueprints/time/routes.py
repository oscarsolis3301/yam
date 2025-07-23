from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models.time import TimeEntry
from extensions import db

bp = Blueprint('time', __name__, url_prefix='/time')

@bp.route('/status')
@login_required
def time_status():
    # Check if user has an active time entry
    active_entry = TimeEntry.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).first()
    
    return jsonify({
        'clocked_in': active_entry is not None,
        'current_entry': active_entry.to_dict() if active_entry else None
    })

@bp.route('/entries')
@login_required
def time_entries():
    # Get today's entries
    today = datetime.utcnow().date()
    entries = TimeEntry.query.filter(
        TimeEntry.user_id == current_user.id,
        db.func.date(TimeEntry.clock_in) == today
    ).order_by(TimeEntry.clock_in.desc()).all()
    
    return jsonify([entry.to_dict() for entry in entries])

@bp.route('/clock-in', methods=['POST'])
@login_required
def clock_in():
    # Check if user is already clocked in
    active_entry = TimeEntry.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).first()
    
    if active_entry:
        return jsonify({'error': 'Already clocked in'}), 400
    
    # Create new time entry
    entry = TimeEntry(
        user_id=current_user.id,
        clock_in=datetime.utcnow(),
        status='active'
    )
    
    try:
        db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'Successfully clocked in'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/clock-out', methods=['POST'])
@login_required
def clock_out():
    # Find active time entry
    active_entry = TimeEntry.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not active_entry:
        return jsonify({'error': 'No active time entry found'}), 400
    
    # Update time entry
    active_entry.clock_out = datetime.utcnow()
    active_entry.status = 'completed'
    
    try:
        db.session.commit()
        return jsonify({'message': 'Successfully clocked out'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 