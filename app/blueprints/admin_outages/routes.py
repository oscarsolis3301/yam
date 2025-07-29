import logging
from datetime import datetime, timezone

from flask import jsonify, request
from flask_login import login_required, current_user

from . import bp
from app.extensions import db, socketio
from app.models import Outage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _is_admin():
    """Convenience helper to check admin permissions."""
    return getattr(current_user, 'is_admin', False)


# ---------------------------------------------------------------------------
# Collection-level routes
# ---------------------------------------------------------------------------

@bp.route('', methods=['GET'])  # /api/admin/outages
@login_required
def list_outages():
    """Return outages (active by default, all if ?all=1).
    Mirrors original behaviour from app/spark.py.
    """
    all_param = request.args.get('all')
    try:
        if all_param:
            outages = Outage.query.order_by(Outage.created_at.desc()).all()
        else:
            outages = (
                Outage.query.filter_by(status='active')
                .order_by(Outage.created_at.desc())
                .all()
            )
        return jsonify([o.to_dict() for o in outages])
    except Exception as e:
        logger.error(f"Error fetching outages: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('', methods=['POST'])  # /api/admin/outages
@login_required
def create_outage():
    """Create a new outage (admin-only)."""
    if not _is_admin():
        return jsonify({'error': 'Only administrators can create outages'}), 403

    data = request.get_json() or {}

    # Validate required fields
    if not data.get('title') or not data.get('description'):
        return jsonify({'error': 'Title and description are required'}), 400

    # Parse start_time (optional)
    if data.get('start_time'):
        try:
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
        except ValueError as e:
            return jsonify({'error': f'Invalid start_time format: {e}'}), 400
    else:
        start_time = datetime.now(timezone.utc)

    outage = Outage(
        title=data['title'],
        description=data['description'],
        start_time=start_time,
        affected_systems=data.get('affected_systems', ''),
        status='active',
        created_by=current_user.id,
    )

    try:
        db.session.add(outage)
        db.session.commit()

        response = outage.to_dict()
        # Augment with duration if caller supplied end_time
        if data.get('end_time'):
            try:
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
                response['duration'] = (end_time - start_time).total_seconds() / 3600
            except ValueError:
                pass

        # Notify connected clients
        socketio.emit('new_outage', response, namespace='/')
        return jsonify(response), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating outage: {e}")
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Item-level routes
# ---------------------------------------------------------------------------


def _get_outage_or_404(outage_id):
    """Helper to fetch outage or return JSON 404."""
    outage = Outage.query.get_or_404(outage_id)
    return outage


@bp.route('/<int:outage_id>', methods=['GET'])
@login_required
def get_outage(outage_id):
    """Retrieve a single outage (admin-only)."""
    if not _is_admin():
        return jsonify({'error': 'Only administrators can view outage details'}), 403
    outage = _get_outage_or_404(outage_id)
    return jsonify(outage.to_dict())


@bp.route('/<int:outage_id>', methods=['PUT'])
@login_required
def update_outage(outage_id):
    """Update outage fields (admin-only)."""
    if not _is_admin():
        return jsonify({'error': 'Only administrators can modify outages'}), 403

    outage = _get_outage_or_404(outage_id)
    data = request.get_json() or {}

    if not data.get('title') or not data.get('description'):
        return jsonify({'error': 'Title and description are required'}), 400

    try:
        outage.title = data['title']
        outage.description = data['description']
        outage.ticket_id = data.get('ticket_id')
        outage.affected_systems = data.get('affected_systems', '')
        # Optionally update severity, status, etc.
        if 'severity' in data:
            outage.severity = data['severity']

        db.session.commit()

        # Broadcast modification
        socketio.emit('outage_modified', outage.to_dict(), namespace='/')
        return jsonify(outage.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating outage {outage_id}: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:outage_id>/resolve', methods=['POST'])
@login_required
def resolve_outage(outage_id):
    """Mark outage as resolved (admin-only)."""
    if not _is_admin():
        return jsonify({'error': 'Only administrators can resolve outages'}), 403

    outage = _get_outage_or_404(outage_id)

    try:
        outage.status = 'resolved'
        outage.end_time = datetime.now(timezone.utc)
        db.session.commit()

        response = {
            'id': outage.id,
            'status': 'resolved',
            'end_time': outage.end_time.isoformat(),
            'message': 'Outage resolved successfully',
        }
        socketio.emit('outage_update', response, namespace='/')
        return jsonify(response)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resolving outage {outage_id}: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:outage_id>', methods=['DELETE'])
@login_required
def delete_outage(outage_id):
    """Delete an outage (admin-only)."""
    if not _is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    outage = _get_outage_or_404(outage_id)

    try:
        outage_data = outage.to_dict()
        db.session.delete(outage)
        db.session.commit()
        socketio.emit('outage_deleted', outage_data, namespace='/')
        return '', 204
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting outage {outage_id}: {e}")
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Socket.IO passthrough handlers (broadcast helpers)
# ---------------------------------------------------------------------------


@socketio.on('outage_update')
def handle_outage_update(data):
    """Re-broadcast outage update events to all clients."""
    socketio.emit('outage_update', data)


@socketio.on('new_outage')
def handle_new_outage(data):
    """Re-broadcast new outage events to all clients."""
    socketio.emit('new_outage', data) 