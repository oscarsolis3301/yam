from flask import request, jsonify, render_template
from flask_login import login_required
import requests
import sqlite3
import os
from datetime import datetime

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

@bp.route('/tickets')
@login_required
def tickets_page():
    """Full-screen ticketing page that displays tickets from the SQLite database."""
    return render_template('tickets_fullscreen.html')

@bp.route('/api/tickets')
@login_required
def get_tickets():
    """API endpoint to get tickets from the SQLite database."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Freshworks', 'tickets.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tickets with basic information
        cursor.execute("""
            SELECT id, subject, status, priority, requester_id, created_at, updated_at, category
            FROM tickets 
            ORDER BY updated_at DESC
        """)
        
        tickets = []
        for row in cursor.fetchall():
            ticket_id, subject, status, priority, requester_id, created_at, updated_at, category = row
            
            # Convert status and priority to readable format
            status_map = {
                '2': 'Open',
                '3': 'Pending',
                '4': 'Resolved',
                '5': 'Closed'
            }
            
            priority_map = {
                '1': 'Low',
                '2': 'Medium', 
                '3': 'High',
                '4': 'Urgent'
            }
            
            tickets.append({
                'id': ticket_id,
                'subject': subject,
                'status': status_map.get(status, status),
                'priority': priority_map.get(priority, priority),
                'requester_id': requester_id,
                'created_at': created_at,
                'updated_at': updated_at,
                'category': category
            })
        
        conn.close()
        return jsonify({'tickets': tickets})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 