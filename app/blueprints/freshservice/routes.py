from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
import sqlite3
from datetime import datetime
import os

bp = Blueprint('freshservice', __name__, url_prefix='/freshservice')

def get_freshservice_db():
    """Get connection to Freshservice database"""
    # Use the correct relative path from the project root
    db_path = 'app/Freshworks/tickets.db'
    
    if os.path.exists(db_path):
        current_app.logger.info(f"Found Freshservice database at: {db_path}")
        return sqlite3.connect(db_path)
    
    # Try alternative paths if the relative path doesn't work
    alternative_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'Freshworks', 'tickets.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Freshworks', 'tickets.db'),
        'Freshworks/tickets.db',
        'tickets.db'
    ]
    
    for alt_path in alternative_paths:
        if os.path.exists(alt_path):
            current_app.logger.info(f"Found Freshservice database at: {alt_path}")
            return sqlite3.connect(alt_path)
    
    # If no database found, raise an error
    raise FileNotFoundError(f"Freshservice database not found. Tried paths: {db_path}, {alternative_paths}")

def load_user_mapping():
    """Load user ID to name mapping from IDs.txt"""
    mapping = {}
    try:
        # Try multiple possible paths for the IDs.txt file
        possible_paths = [
            'app/Freshworks/IDs.txt',
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'Freshworks', 'IDs.txt'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Freshworks', 'IDs.txt'),
            'Freshworks/IDs.txt',
            'IDs.txt'
        ]
        
        ids_file = None
        for path in possible_paths:
            if os.path.exists(path):
                ids_file = path
                break
        
        if ids_file:
            current_app.logger.info(f"Loading user mapping from: {ids_file}")
            with open(ids_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ' - ' in line:
                        name, user_id = line.split(' - ', 1)
                        try:
                            mapping[int(user_id)] = name.strip()
                        except ValueError:
                            continue
        else:
            current_app.logger.warning("IDs.txt file not found, using default user mapping")
            # Provide some default mappings if file not found
            mapping = {
                18012927832: "Default User",
                18013653802: "Default User 2"
            }
    except Exception as e:
        current_app.logger.error(f"Error loading user mapping: {e}")
        # Provide fallback mapping
        mapping = {
            18012927832: "Default User",
            18013653802: "Default User 2"
        }
    
    return mapping

@bp.route('/tickets')
@login_required
def tickets():
    """Freshservice tickets page"""
    try:
        # Test database connection to ensure it works
        conn = get_freshservice_db()
        conn.close()
        return render_template('freshservice/tickets.html', active_page='freshservice_tickets')
    except Exception as e:
        current_app.logger.error(f"Error accessing FreshService tickets page: {e}")
        # Return a simple error page instead of failing completely
        return f"""
        <html>
        <head><title>FreshService Tickets - Error</title></head>
        <body>
            <h1>FreshService Tickets</h1>
            <p>Error loading FreshService tickets: {str(e)}</p>
            <p>Please check the database connection and try again.</p>
            <a href="/">Return to Home</a>
        </body>
        </html>
        """, 500

@bp.route('/api/tickets')
@login_required
def get_tickets():
    """API endpoint to get tickets from Freshservice database"""
    try:
        conn = get_freshservice_db()
        cursor = conn.cursor()
        user_mapping = load_user_mapping()
        
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')
        agent_filter = request.args.get('agent', 'all')
        category_filter = request.args.get('category', 'all')
        sub_category_filter = request.args.get('sub_category', 'all')
        item_category_filter = request.args.get('item_category', 'all')
        requester_filter = request.args.get('requester', '')
        created_filter = request.args.get('created', 'any')
        department_filter = request.args.get('department', 'select')
        group_filter = request.args.get('group', 'select')
        overdue_filter = request.args.get('overdue', 'false')
        search = request.args.get('search', '')
        sort_by = request.args.get('sort_by', 'updated_date')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 30))
        
        # Build query with actual database fields
        query = """
        SELECT 
            t.id,
            t.subject,
            t.description,
            t.status,
            t.priority,
            t.requester_id,
            t.created_at,
            t.updated_at,
            t.category,
            t.sub_category,
            t.item_category,
            t.full_text
        FROM tickets t
        WHERE 1=1
        """
        
        params = []
        
        # Apply filters
        if status_filter != 'all':
            query += " AND t.status = ?"
            params.append(status_filter)
            
        if priority_filter != 'all':
            query += " AND t.priority = ?"
            params.append(priority_filter)
            
        if category_filter != 'all':
            query += " AND t.category = ?"
            params.append(category_filter)
            
        if sub_category_filter != 'all':
            query += " AND t.sub_category = ?"
            params.append(sub_category_filter)
            
        if item_category_filter != 'all':
            query += " AND t.item_category = ?"
            params.append(item_category_filter)
            
        if requester_filter:
            # Search by requester name in the user mapping
            requester_ids = []
            for req_id, req_name in user_mapping.items():
                if requester_filter.lower() in req_name.lower():
                    requester_ids.append(req_id)
            
            if requester_ids:
                placeholders = ','.join(['?' for _ in requester_ids])
                query += f" AND t.requester_id IN ({placeholders})"
                params.extend(requester_ids)
            else:
                # If no matching names found, return no results
                query += " AND 1=0"
        
        # Apply created date filter
        if created_filter != 'any':
            from datetime import datetime, timedelta
            now = datetime.now()
            
            if created_filter == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif created_filter == 'yesterday':
                start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif created_filter == 'this_week':
                start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7)
            elif created_filter == 'this_month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    end_date = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    end_date = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                # Default to any
                start_date = None
                end_date = None
            
            if start_date and end_date:
                query += " AND t.created_at BETWEEN ? AND ?"
                params.extend([start_date.isoformat(), end_date.isoformat()])
        
        if search:
            # Enhanced search to include ticket number search
            search_term = f"%{search}%"
            query += """ AND (
                t.subject LIKE ? OR 
                t.description LIKE ? OR 
                CAST(t.id AS TEXT) LIKE ? OR 
                t.category LIKE ? OR 
                t.sub_category LIKE ? OR 
                t.item_category LIKE ? OR
                t.full_text LIKE ?
            )"""
            params.extend([search_term, search_term, search_term, search_term, search_term, search_term, search_term])
        
        # Add ordering based on sort parameter
        if sort_by == 'created_date':
            query += " ORDER BY t.created_at DESC"
        elif sort_by == 'priority':
            query += " ORDER BY t.priority ASC, t.updated_at DESC"
        elif sort_by == 'status':
            query += " ORDER BY t.status ASC, t.updated_at DESC"
        elif sort_by == 'requester':
            query += " ORDER BY t.requester_id ASC, t.updated_at DESC"
        else:  # default to updated_date
            query += " ORDER BY t.updated_at DESC"
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Add pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        tickets = cursor.fetchall()

        # Convert to list of dictionaries with actual fields
        ticket_list = []
        for ticket in tickets:
            requester_id = ticket[5]
            requester_name = user_mapping.get(requester_id, f'User {requester_id}' if requester_id else 'Unknown')
            
            ticket_dict = {
                'id': ticket[0],
                'subject': ticket[1] or 'No Subject',
                'description': ticket[2] or '',
                'status': get_status_text(ticket[3]),
                'priority': get_priority_text(ticket[4]),
                'created_at': ticket[6],
                'updated_at': ticket[7],
                'requester_id': requester_id,
                'category': ticket[8] or 'General',
                'sub_category': ticket[9] or 'Other',
                'item_category': ticket[10] or 'General',
                'full_text': ticket[11] or '',
                'source': 'Freshservice',
                'requester_name': requester_name,
                'requester_email': '',
                'agent_name': 'Unassigned',
                'agent_email': '',
                'ticket_number': f"INC-{ticket[0]}"
            }
            ticket_list.append(ticket_dict)
        
        # Get statistics
        stats = get_ticket_stats(cursor)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'tickets': ticket_list,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching tickets: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch tickets',
            'message': str(e)
        }), 500

@bp.route('/api/ticket/<int:ticket_id>')
@login_required
def get_ticket_details(ticket_id):
    """Get detailed information for a specific ticket"""
    try:
        conn = get_freshservice_db()
        cursor = conn.cursor()
        user_mapping = load_user_mapping()
        
        # Get ticket details
        cursor.execute("""
            SELECT 
                id, subject, description, status, priority, requester_id,
                created_at, updated_at, category, sub_category, item_category, full_text
            FROM tickets 
            WHERE id = ?
        """, (ticket_id,))
        
        ticket_data = cursor.fetchone()
        if not ticket_data:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Ticket not found'
            }), 404
        
        # Get conversations for this ticket
        cursor.execute("""
            SELECT id, body, incoming, private, created_at
            FROM conversations 
            WHERE ticket_id = ?
            ORDER BY created_at ASC
        """, (ticket_id,))
        
        conversations_data = cursor.fetchall()
        
        # Convert ticket data
        requester_id = ticket_data[5]
        requester_name = user_mapping.get(requester_id, f'User {requester_id}' if requester_id else 'Unknown')
        
        ticket = {
            'id': ticket_data[0],
            'subject': ticket_data[1] or 'No Subject',
            'description': ticket_data[2] or '',
            'status': get_status_text(ticket_data[3]),
            'priority': get_priority_text(ticket_data[4]),
            'requester_id': requester_id,
            'requester_name': requester_name,
            'created_at': ticket_data[6],
            'updated_at': ticket_data[7],
            'category': ticket_data[8] or 'General',
            'sub_category': ticket_data[9] or 'Other',
            'item_category': ticket_data[10] or 'General',
            'full_text': ticket_data[11] or '',
            'agent_name': 'Unassigned',
            'time_elapsed': calculate_time_elapsed(ticket_data[6], ticket_data[7])
        }
        
        # Convert conversations data
        conversations = []
        for conv in conversations_data:
            conversation = {
                'id': conv[0],
                'body': conv[1] or '',
                'incoming': bool(conv[2]),
                'private': bool(conv[3]),
                'created_at': conv[4],
                'user_name': 'System' if conv[2] else requester_name
            }
            conversations.append(conversation)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'ticket': ticket,
            'conversations': conversations
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching ticket details: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch ticket details',
            'message': str(e)
        }), 500

def calculate_time_elapsed(created_at, updated_at):
    """Calculate time elapsed between creation and update"""
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elapsed = updated - created
        
        days = elapsed.days
        hours = elapsed.seconds // 3600
        minutes = (elapsed.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "N/A"

def get_status_text(status_code):
    """Convert status code to text"""
    status_mapping = {
        '1': 'Open',
        '2': 'Pending',
        '3': 'Resolved',
        '4': 'Closed',
        '5': 'Awaiting User',
        '6': 'Awaiting Third Party'
    }
    return status_mapping.get(str(status_code), f'Status {status_code}')

def get_priority_text(priority_code):
    """Convert priority code to text"""
    priority_mapping = {
        '1': 'Low',
        '2': 'Medium',
        '3': 'High',
        '4': 'Urgent'
    }
    return priority_mapping.get(str(priority_code), f'Priority {priority_code}')

def get_source_text(source_code):
    """Convert source code to text"""
    source_mapping = {
        '1': 'Email',
        '2': 'Portal',
        '3': 'Phone',
        '4': 'Chat',
        '5': 'Mobihelp',
        '6': 'Feedback Widget',
        '7': 'Outbound Email'
    }
    return source_mapping.get(str(source_code), f'Source {source_code}')

def get_ticket_stats(cursor):
    """Get ticket statistics"""
    try:
        # Total tickets
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total = cursor.fetchone()[0]
        
        # Open tickets
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = '1'")
        open_count = cursor.fetchone()[0]
        
        # Pending tickets
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = '2'")
        pending_count = cursor.fetchone()[0]
        
        # Resolved tickets
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = '3'")
        resolved_count = cursor.fetchone()[0]
        
        return {
            'total': total,
            'open': open_count,
            'pending': pending_count,
            'resolved': resolved_count
        }
    except Exception as e:
        current_app.logger.error(f"Error getting stats: {e}")
        return {
            'total': 0,
            'open': 0,
            'pending': 0,
            'resolved': 0
        }

@bp.route('/api/check-database-changes')
@login_required
def check_database_changes():
    """Check if the database has been modified since last check"""
    try:
        db_path = 'app/Freshworks/tickets.db'
        
        # Try alternative paths if the relative path doesn't work
        alternative_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'Freshworks', 'tickets.db'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Freshworks', 'tickets.db'),
            'Freshworks/tickets.db',
            'tickets.db'
        ]
        
        actual_db_path = None
        for path in [db_path] + alternative_paths:
            if os.path.exists(path):
                actual_db_path = path
                break
        
        if not actual_db_path:
            return jsonify({'hasChanges': False, 'error': 'Database not found'})
        
        # Get the last modification time of the database file
        db_mtime = os.path.getmtime(actual_db_path)
        
        # Get the last check time from the request
        last_check = request.args.get('since', 0)
        last_check = float(last_check) if last_check else 0
        
        # Check if database has been modified since last check
        has_changes = db_mtime > (last_check / 1000)  # Convert from milliseconds to seconds
        
        return jsonify({
            'hasChanges': has_changes,
            'lastModified': db_mtime,
            'currentTime': datetime.now().timestamp()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking database changes: {str(e)}")
        return jsonify({
            'hasChanges': False,
            'error': 'Failed to check database changes'
        }), 500

@bp.route('/api/categories')
@login_required
def get_categories():
    """Get all categories from the database"""
    try:
        conn = get_freshservice_db()
        cursor = conn.cursor()
        
        # Get unique categories
        cursor.execute("SELECT DISTINCT category FROM tickets WHERE category IS NOT NULL AND category != '' ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        
        # Get unique sub-categories
        cursor.execute("SELECT DISTINCT sub_category FROM tickets WHERE sub_category IS NOT NULL AND sub_category != '' ORDER BY sub_category")
        sub_categories = [row[0] for row in cursor.fetchall()]
        
        # Get unique item categories
        cursor.execute("SELECT DISTINCT item_category FROM tickets WHERE item_category IS NOT NULL AND item_category != '' ORDER BY item_category")
        item_categories = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'categories': categories,
            'sub_categories': sub_categories,
            'item_categories': item_categories
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch categories',
            'message': str(e)
        }), 500

@bp.route('/api/requesters')
@login_required
def get_requesters():
    """Get popular requesters with ticket counts"""
    try:
        conn = get_freshservice_db()
        cursor = conn.cursor()
        user_mapping = load_user_mapping()
        
        # Get requesters with ticket counts, ordered by count descending
        cursor.execute("""
            SELECT requester_id, COUNT(*) as ticket_count
            FROM tickets 
            WHERE requester_id IS NOT NULL
            GROUP BY requester_id 
            ORDER BY ticket_count DESC 
            LIMIT 10
        """)
        
        requesters = []
        for row in cursor.fetchall():
            requester_id = row[0]
            ticket_count = row[1]
            requester_name = user_mapping.get(requester_id, f'User {requester_id}' if requester_id else 'Unknown')
            
            requesters.append({
                'id': requester_id,
                'name': requester_name,
                'count': ticket_count
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'requesters': requesters
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching requesters: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch requesters',
            'message': str(e)
        }), 500