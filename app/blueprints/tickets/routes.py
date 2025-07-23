from flask import request, jsonify
from flask_login import login_required
import requests

from . import bp
from app.config import FRESH_ENDPOINT, FRESH_API


@bp.route('/create_ticket', methods=['POST'])
@login_required
def create_ticket():
    """Create a Freshdesk ticket using the incoming JSON payload.

    Expects JSON with at least:
      - subject: Ticket subject line
      - description: Ticket body / description
      - requestor: Email address of the requestor (optional)

    The endpoint mirrors the original implementation from *app/spark.py* so
    existing frontend code can continue posting to `/create_ticket` without
    modification.
    """
    incoming = request.get_json(force=True, silent=True) or {}

    subject = incoming.get('subject', '')
    description = incoming.get('description', '')
    email = incoming.get('requestor')  # Optional – keeps same key as before

    # Prepare Freshdesk payload. These hard-coded fields match the original
    # behaviour (status=2 "Open", priority=1 "Low", etc.).
    data = {
        'subject': subject,
        'description': description,
        'email': email,
        'phone': '+1 (714) 845-8500',
        'status': 2,
        'priority': 1,
        'source': 2,
        'tags': ['spark'],
        'group_id': 18000294963,
        'category': 'IT',
        'responder_id': 18014125885,
    }

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(
            f"{FRESH_ENDPOINT}tickets/",
            auth=(FRESH_API, 'CREATE'),
            json=data,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        # Bubble up error details to client – helpful for debugging.
        return jsonify({'error': 'Failed to create ticket', 'details': str(exc)}), 500

    # Optionally forward Freshdesk's response if needed. For now, keep it
    # simple and mimic the previous success message.
    return jsonify({'message': 'Ticket created successfully'}), 201 