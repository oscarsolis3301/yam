import logging
from flask import request, jsonify
from . import bp
from app.extensions import socketio
from app.extensions import db

@bp.route('/ad_event', methods=['POST'])
def ad_event():
    """Endpoint to receive Active Directory events.

    The endpoint expects a JSON body representing the AD event payload.  Once
    received it logs the event and broadcasts it to any connected Socket.IO
    clients so that the front-end can react in real-time.
    """
    data = request.get_json(silent=True) or {}

    # Basic logging for observability
    logging.getLogger(__name__).info("Received AD event: %s", data)

    # Broadcast the event to all connected clients
    try:
        socketio.emit('ad_event', data, namespace='/')
    except Exception as e:
        logging.getLogger(__name__).warning("Failed to broadcast ad_event: %s", e)

    return jsonify(status='received'), 200 