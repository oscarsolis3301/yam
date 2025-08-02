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
    """API endpoint to get tickets from the SQLite database with filtering and search support."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Freshworks', 'tickets.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get filter parameters from request
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')
        search = request.args.get('search', '')
        created_filter = request.args.get('created', 'any')
        overdue_filter = request.args.get('overdue', 'false')
        sort_by = request.args.get('sort_by', 'updated_at')
        sort_direction = request.args.get('sort_direction', 'desc')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Build base query
        query = """
        SELECT id, subject, status, priority, requester_id, created_at, updated_at, category, full_text
        FROM tickets 
        WHERE 1=1
        """
        
        params = []
        
        # Apply status filter
        if status_filter != 'all':
            if status_filter == 'unresolved':
                query += " AND status IN ('2', '3')"  # Open and Pending
            else:
                status_map = {'open': '2', 'pending': '3', 'resolved': '4', 'closed': '5'}
                if status_filter in status_map:
                    query += " AND status = ?"
                    params.append(status_map[status_filter])
        
        # Apply priority filter
        if priority_filter != 'all':
            priority_map = {'low': '1', 'medium': '2', 'high': '3', 'urgent': '4'}
            if priority_filter in priority_map:
                query += " AND priority = ?"
                params.append(priority_map[priority_filter])
        
        # Apply search filter
        if search:
            query += " AND (subject LIKE ? OR category LIKE ? OR full_text LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        
        # Apply created filter
        if created_filter != 'any':
            current_time = datetime.now()
            if created_filter == 'today':
                query += " AND DATE(created_at) = DATE('now')"
            elif created_filter == 'yesterday':
                query += " AND DATE(created_at) = DATE('now', '-1 day')"
            elif created_filter == 'this_week':
                query += " AND DATE(created_at) >= DATE('now', '-7 days')"
            elif created_filter == 'this_month':
                query += " AND DATE(created_at) >= DATE('now', 'start of month')"
        
        # Apply overdue filter
        if overdue_filter == 'true':
            query += " AND (priority IN ('3', '4') AND updated_at < datetime('now', '-1 day'))"
        
        # Apply sorting
        sort_field_map = {
            'status': 'status',
            'subject': 'subject',
            'priority': 'priority',
            'updated_at': 'updated_at',
            'requester': 'requester_id'
        }
        
        if sort_by in sort_field_map:
            query += f" ORDER BY {sort_field_map[sort_by]} {sort_direction.upper()}"
        else:
            query += " ORDER BY updated_at DESC"
        
        # Apply pagination
        offset = (page - 1) * per_page
        query += f" LIMIT {per_page} OFFSET {offset}"
        
        # Execute query
        cursor.execute(query, params)
        
        tickets = []
        for row in cursor.fetchall():
            ticket_id, subject, status, priority, requester_id, created_at, updated_at, category, full_text = row
            
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
        
        # Get total count for pagination
        count_query = query.replace("SELECT id, subject, status, priority, requester_id, created_at, updated_at, category, full_text", "SELECT COUNT(*)")
        count_query = count_query.split("ORDER BY")[0] if "ORDER BY" in count_query else count_query
        count_query = count_query.split("LIMIT")[0] if "LIMIT" in count_query else count_query
        
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'tickets': tickets,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
@login_required
def update_ticket(ticket_id):
    """API endpoint to update ticket status or priority."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Freshworks', 'tickets.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if ticket exists
        cursor.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Update fields
        update_fields = []
        params = []
        
        if 'status' in data:
            status_map = {'Open': '2', 'Pending': '3', 'Resolved': '4', 'Closed': '5'}
            if data['status'] in status_map:
                update_fields.append("status = ?")
                params.append(status_map[data['status']])
        
        if 'priority' in data:
            priority_map = {'Low': '1', 'Medium': '2', 'High': '3', 'Urgent': '4'}
            if data['priority'] in priority_map:
                update_fields.append("priority = ?")
                params.append(priority_map[data['priority']])
        
        if update_fields:
            update_fields.append("updated_at = datetime('now')")
            params.append(ticket_id)
            
            query = f"UPDATE tickets SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            
            conn.close()
            return jsonify({'message': 'Ticket updated successfully'})
        else:
            conn.close()
            return jsonify({'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 