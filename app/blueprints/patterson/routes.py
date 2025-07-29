from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import csv
import os
import requests
from . import bp
from app.models import User, SearchHistory, SystemSettings, UserSettings, Note, Activity, Document, KBArticle, KBAttachment, SharedLink, UserPresence, TimeEntry, UserMapping, PattersonTicket, PattersonCalendarEvent  # Import new models
from app.extensions import Config
from app.utils.patterson_file_manager import get_patterson_file_manager
from app.utils.patterson_db_manager import get_patterson_db_manager
# Import the new Freshworks database manager
try:
    from app.utils.freshworks_db_manager import get_freshworks_db_manager, init_freshworks_db_manager
except ImportError:
    # Fallback if the module doesn't exist yet
    get_freshworks_db_manager = None
    init_freshworks_db_manager = None
import socket
import time
from flask_sqlalchemy import SQLAlchemy
from app.extensions import db
import subprocess
import sys
import re
from sqlalchemy import func, distinct, and_
import sqlite3

# Sample tickets for fallback
SAMPLE_TICKETS = [
    {
        'id': 1,
        'ticket_number': 'INC-2024-001',
        'office_name': '6 - IRV',
        'technician': 'John Smith',
        'technician_id': 1,
        'description': 'Network connectivity issues - Router needs replacement',
        'priority': 'High',
        'status': 'Scheduled',
        'scheduled_date': '2024-01-15',
        'scheduled_time': '09:00',
        'estimated_duration': '2 hours',
        'stage': 'scheduled',
        'created_at': '2024-01-10T10:30:00',
        'updated_at': '2024-01-10T14:45:00'
    }
]

def convert_db_tickets_to_dashboard_format(db_tickets):
    """Convert database ticket format to dashboard format."""
    dashboard_tickets = []
    
    for ticket in db_tickets:
        # Use the title field from the database if available
        subject = ticket.get('title')
        
        # If no title field, fall back to the old logic
        if not subject:
            # -------------------------------------------------------------
            # Robust subject extraction – DB model currently has no
            # dedicated *subject* column, therefore we try several fall-
            # backs so the UI can always display a meaningful title.
            # -------------------------------------------------------------
            subject = ticket.get('subject')  # May exist in future migrations

            if not subject:
                # 1) Try to parse from notes (look for "Subject: ...")
                raw_notes = ticket.get('notes', [])

                # Ensure *raw_notes* is a list (could be JSON-encoded str)
                if isinstance(raw_notes, str):
                    try:
                        raw_notes = json.loads(raw_notes)
                    except Exception:
                        raw_notes = [raw_notes]

                import re  # Local import to avoid pollution
                for note in raw_notes:
                    if isinstance(note, str):
                        m = re.search(r'Subject\s*:\s*(.+?)(?:\s{2,}|Description|$)', note, re.IGNORECASE)
                        if m:
                            subject = m.group(1).strip()
                            break

            if not subject:
                # 2) Fallback – first sentence of *description*
                description_preview = ticket.get('description', '').split('\n')[0]
                subject = description_preview[:80].strip() or 'No Subject'

        # Handle scheduled_date properly to avoid timezone issues
        scheduled_date = ticket.get('scheduled_date')
        if scheduled_date:
            # If it's already a string, use it as is
            if isinstance(scheduled_date, str):
                # Ensure it's in YYYY-MM-DD format
                if 'T' in scheduled_date:
                    scheduled_date = scheduled_date.split('T')[0]
            else:
                # If it's a date object, convert to string
                scheduled_date = scheduled_date.isoformat() if hasattr(scheduled_date, 'isoformat') else str(scheduled_date)

        dashboard_ticket = {
            'id': ticket['id'],
            'freshworks_id': ticket.get('freshworks_id'),
            'ticket_number': ticket['ticket_number'],
            'title': subject,  # Use the clean title
            'office_name': ticket['office_name'],
            # Prefer extracted "Assigned by" name, fallback to technician column
            'technician': _extract_assigned_by_display(ticket) or ticket.get('technician', 'Unassigned'),
            'technician_id': ticket.get('technician_id'),
            'description': ticket['description'],
            'subject': subject,
            'priority': ticket.get('priority', 'Medium'),
            'urgency': ticket.get('urgency', 'Medium'),
            'status': ticket.get('status', 'Scheduled'),
            'scheduled_date': scheduled_date,
            'scheduled_time': ticket.get('scheduled_time', '09:00'),
            'estimated_duration': ticket.get('estimated_duration', '2 hours'),
            'stage': ticket.get('stage', 'scheduled'),
            'category': ticket.get('category'),
            'source': ticket.get('source', 'database'),
            'notes': ticket.get('notes', []),
            'created_at': ticket['created_at'],
            'updated_at': ticket['updated_at']
        }
        dashboard_tickets.append(dashboard_ticket)
    
    return dashboard_tickets

def convert_file_tickets_to_dashboard_format(file_tickets):
    """Convert file ticket format to dashboard format."""
    dashboard_tickets = []
    
    for ticket in file_tickets:
        # Use the full title from Ticket-Title field (no processing)
        subject = ticket.get('subject') or ticket.get('title', '')
        # Use the full title without any processing - don't cut off before pipe
        clean_title = subject if subject else "Untitled Ticket"
        
        # Extract date from subject
        scheduled_date = extract_date_from_subject(subject)
        
        # Set office to Unknown Office by default (no extraction)
        office_name = 'Unknown Office'
        
        # Determine stage based on whether date was found
        if scheduled_date:
            stage = 'scheduled'
        else:
            stage = 'in_progress'
        
        # Get priority from status
        status = ticket.get('status', 2)
        priority = get_priority_from_status(status)
        
        # Get source
        source = 'Freshworks'
        
        # Determine technician display name
        technician_display = _extract_assigned_by_display(ticket) or get_technician_name(ticket.get('responder_id'))

        dashboard_ticket = {
            'id': ticket.get('id'),
            'freshworks_id': str(ticket.get('id')),
            'ticket_number': f"INC-{ticket.get('id', 'UNKNOWN')}",
            'title': clean_title,  # Use the full title
            'office_name': office_name,  # Always Unknown Office
            'technician': technician_display,
            'technician_id': ticket.get('responder_id'),
            'description': ticket.get('description', ''),
            'subject': clean_title,  # Use the full title
            'priority': priority,
            'urgency': priority,
            'status': map_status(status),
            'scheduled_date': scheduled_date,
            'scheduled_time': '09:00',
            'estimated_duration': '2 hours',
            'stage': stage,
            'category': 'IT',
            'source': source,
            'notes': ticket.get('notes', []),
            'created_at': ticket.get('created_at'),
            'updated_at': ticket.get('created_at')
        }
        dashboard_tickets.append(dashboard_ticket)
    
    return dashboard_tickets

def extract_clean_title_from_subject(subject):
    """Extract a clean title from ticket subject, removing date/time prefixes."""
    if not subject:
        return "Untitled Ticket"
    
    import re
    
    # Pattern 1: "6/19 - 12-4pm | Primescan Down" -> "Primescan Down"
    # Pattern 2: "6/25 8am-12pm | Hand held Gendex x-ray button..." -> "Hand held Gendex x-ray button..."
    pipe_pattern = r'^.*?\|\s*(.+)$'
    match = re.search(pipe_pattern, subject.strip())
    if match:
        return match.group(1).strip()
    
    # Pattern 3: "6/19 - 12-4pm Primescan Down" -> "Primescan Down"
    # Look for date/time patterns followed by actual title
    date_time_patterns = [
        r'^\d{1,2}/\d{1,2}\s*-\s*\d{1,2}:\d{2}[ap]m\s*(.+)$',  # "6/19 - 12:4pm Title"
        r'^\d{1,2}/\d{1,2}\s*-\s*\d{1,2}-\d{1,2}[ap]m\s*(.+)$',  # "6/19 - 12-4pm Title"
        r'^\d{1,2}/\d{1,2}\s*\d{1,2}[ap]m-\d{1,2}[ap]m\s*(.+)$',  # "6/25 8am-12pm Title"
        r'^\d{1,2}/\d{1,2}\s*\d{1,2}:\d{2}[ap]m-\d{1,2}:\d{2}[ap]m\s*(.+)$',  # "6/25 8:00am-12:00pm Title"
    ]
    
    for pattern in date_time_patterns:
        match = re.search(pattern, subject.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Pattern 4: Remove common prefixes that are just dates/times
    prefix_patterns = [
        r'^\d{1,2}/\d{1,2}\s*-\s*',  # "6/19 - "
        r'^\d{1,2}/\d{1,2}\s*',      # "6/19 "
        r'^\d{1,2}-\d{1,2}\s*-\s*',  # "6-19 - "
        r'^\d{1,2}-\d{1,2}\s*',      # "6-19 "
    ]
    
    cleaned_subject = subject.strip()
    for pattern in prefix_patterns:
        cleaned_subject = re.sub(pattern, '', cleaned_subject, flags=re.IGNORECASE)
    
    # If we still have content, return it
    if cleaned_subject.strip():
        return cleaned_subject.strip()
    
    # Check if the original subject is just a date pattern
    date_only_patterns = [
        r'^\d{1,2}/\d{1,2}\s*-\s*$',  # "6/19 - "
        r'^\d{1,2}/\d{1,2}\s*$',      # "6/19 "
        r'^\d{1,2}-\d{1,2}\s*-\s*$',  # "6-19 - "
        r'^\d{1,2}-\d{1,2}\s*$',      # "6-19 "
    ]
    
    for pattern in date_only_patterns:
        if re.match(pattern, subject.strip(), re.IGNORECASE):
            return "Untitled Ticket"
    
    # If all else fails, return the original subject
    return subject.strip()

def extract_office_from_subject(subject):
    """Extract office information from ticket subject."""
    if not subject:
        return "Unknown Office"
    
    # Common patterns for office extraction
    import re
    
    # Pattern 1: "office 633" or "Office 633"
    office_pattern = re.search(r'office\s*(\d+)', subject, re.IGNORECASE)
    if office_pattern:
        return f"Office {office_pattern.group(1)}"
    
    # Pattern 2: Look for specific office names
    office_names = ['IRV', 'IRVINE', 'ANAHEIM', 'ANA', 'FULLERTON', 'FULL']
    for name in office_names:
        if name.lower() in subject.lower():
            return f"Office - {name}"
    
    # Pattern 3: If subject contains a date pattern, extract the description part
    date_pattern = re.search(r'(\d+)/(\d+)/(\d+)\s*\|\s*(.+)', subject)
    if date_pattern:
        description = date_pattern.group(4).strip()
        # Try to find office in the description
        office_match = re.search(r'office\s*(\d+)', description, re.IGNORECASE)
        if office_match:
            return f"Office {office_match.group(1)}"
        # If no office found, use the description as the title
        return description
    
    # Pattern 4: Look for numbers that might be office numbers (3 digits)
    numbers = re.findall(r'\b(\d{3})\b', subject)
    if numbers:
        return f"Office {numbers[0]}"
    
    # If no clear pattern found, use the subject as the office name (truncated if too long)
    if len(subject) > 50:
        return subject[:47] + "..."
    return subject

def extract_date_from_subject(subject):
    """Extract date information from ticket subject."""
    if not subject:
        return None  # Return None instead of default date
    
    import re
    from datetime import datetime
    
    # Pattern 1: "6/19 - 12-4pm | Primescan Down" format
    pipe_date_pattern = r'^(\d{1,2})/(\d{1,2})\s*-\s*\d{1,2}-\d{1,2}[ap]m\s*\|'
    match = re.search(pipe_date_pattern, subject.strip(), re.IGNORECASE)
    if match:
        month, day = match.groups()
        current_year = datetime.now().year
        return f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Pattern 2: "6/25 8am-12pm | Hand held Gendex x-ray button" format
    pipe_date_pattern2 = r'^(\d{1,2})/(\d{1,2})\s*\d{1,2}[ap]m-\d{1,2}[ap]m\s*\|'
    match = re.search(pipe_date_pattern2, subject.strip(), re.IGNORECASE)
    if match:
        month, day = match.groups()
        current_year = datetime.now().year
        return f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Pattern 3: "6/19/2025 | Scanner camera is broke" or "06/19/2025 | Scanner camera is broke"
    date_pattern = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', subject)
    if date_pattern:
        month, day, year = date_pattern.groups()
        # Handle 2-digit years
        if len(year) == 2:
            year = '20' + year
        # Ensure month and day are zero-padded
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Pattern 4: "6/25 - 12-4pm | Milling Unit Error" (old pattern, keep for compatibility)
    date_pattern2 = re.search(r'(\d{1,2})/(\d{1,2})\s*-\s*(\d+)-(\d+)pm', subject)
    if date_pattern2:
        month, day = date_pattern2.groups()[:2]
        current_year = datetime.now().year
        return f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return None  # Return None if no date found

def extract_office_from_notes(notes):
    """Extract office information from ticket notes."""
    if not notes:
        return None
    
    import re
    
    # Convert notes to list if it's a string
    if isinstance(notes, str):
        try:
            notes_data = json.loads(notes)
        except:
            notes_data = [notes]
    else:
        notes_data = notes
    
    # Look for office information in notes with improved patterns
    for note in notes_data:
        if isinstance(note, str):
            # Allow flexible / multiple whitespace characters so slight
            # formatting differences do not break the regex.
            external_dept_pattern = r'External\s+Name\s+([A-Za-z\s]+?)\s+Department\s+Name\s+(\d+)-([A-Za-z\s]+?)\s+Office\s+Number\s+(\d+)'
            match = re.search(external_dept_pattern, note, re.IGNORECASE)
            if match:
                external_name = match.group(1).strip()
                dept_num = match.group(2)
                dept_name = match.group(3).strip()
                office_num = match.group(4)
                
                # Return the most descriptive format: "Office Number - External Name"
                return f"{office_num} - {external_name}"
            
            # Pattern 2: Extract from "External Name X Department Name Y" format
            external_dept_simple = r'External\s+Name\s+([A-Za-z\s]+?)\s+Department\s+Name\s+(\d+)-([A-Za-z\s]+)'
            match = re.search(external_dept_simple, note, re.IGNORECASE)
            if match:
                external_name = match.group(1).strip()
                dept_num = match.group(2)
                dept_name = match.group(3).strip()
                
                # Return "Department Number - External Name"
                return f"{dept_num} - {external_name}"
            
            # Pattern 3: Just "Office Number X"
            office_num_pattern = r'Office\s+Number\s+(\d+)'
            match = re.search(office_num_pattern, note, re.IGNORECASE)
            if match:
                office_num = match.group(1)
                return f"Office {office_num}"
            
            # Pattern 4: "Department Name X-Y"
            dept_pattern = r'Department Name (\d+)-([A-Za-z\s]+)'
            match = re.search(dept_pattern, note, re.IGNORECASE)
            if match:
                dept_num = match.group(1)
                dept_name = match.group(2).strip()
                return f"{dept_num} - {dept_name}"
            
            # Pattern 5: "External Name X" only
            external_pattern = r'External Name ([A-Za-z\s]+)'
            match = re.search(external_pattern, note, re.IGNORECASE)
            if match:
                external_name = match.group(1).strip()
                return external_name
    
    return None

def load_offices_from_csv():
    """Load offices from CSV file."""
    try:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                               'Offices', 'offices_info.csv')
        
        if not os.path.exists(csv_path):
            current_app.logger.warning(f"Offices CSV file not found: {csv_path}")
            return []
        
        offices = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                office = {
                    'number': row.get('#', ''),
                    'mnemonic': row.get('Mnemonic', ''),
                    'name': row.get('Name', ''),
                    'display': f"{row.get('#', '')} - {row.get('Mnemonic', '')}"
                }
                offices.append(office)
        
        return offices
    except Exception as e:
        current_app.logger.error(f"Error loading offices from CSV: {e}")
        return []

@bp.route('/')
@login_required
def patterson_dashboard():
    """Render the main Patterson dispatch dashboard."""
    try:
        # Trigger the import of all dated files every time the dashboard is loaded
        db_manager = get_patterson_db_manager()
        if db_manager:
            current_app.logger.info("Triggering import of all dated Freshworks files...")
            db_manager.import_all_dated_files()
        else:
            current_app.logger.error("Patterson DB manager not available, cannot import files.")
    except Exception as e:
        current_app.logger.error(f"Failed to auto-import dated files: {str(e)}")

    return render_template('patterson/patterson1.html')

@bp.route('/api/tickets')
@login_required
def get_tickets():
    """
    Get all tickets, ensuring data is fresh by checking file system first.
    This automatically imports new ticket files if available.
    """
    source = 'database'
    try:
        patterson_db_manager = get_patterson_db_manager()
        patterson_file_manager = get_patterson_file_manager()

        # Automatically import latest files to ensure DB is up-to-date
        try:
            patterson_file_manager.import_and_archive_latest_files()
            current_app.logger.info("Checked for new ticket files and imported them.")
        except Exception as e:
            current_app.logger.error(f"Could not auto-import ticket files: {e}")

        # Now, fetch all tickets from the database
        db_tickets = patterson_db_manager.get_all_tickets()
        
        if not db_tickets:
            # Fallback to sample data if database is empty after import attempt
            tickets = SAMPLE_TICKETS
            source = 'sample'
        else:
            tickets = convert_db_tickets_to_dashboard_format(db_tickets)

        return jsonify({'success': True, 'tickets': tickets, 'source': source})

    except Exception as e:
        current_app.logger.error(f"Error in get_tickets: {e}")
        return jsonify({
            'success': False, 
            'error': f'An error occurred: {str(e)}', 
            'tickets': SAMPLE_TICKETS, 
            'source': 'fallback'
        }), 500

@bp.route('/api/tickets', methods=['POST'])
@login_required
def create_ticket():
    """Create a new ticket in the database."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['office_name', 'technician_id', 'description', 'scheduled_date', 'scheduled_time']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Get technician name
        technician = User.query.get(data['technician_id'])
        if not technician:
            return jsonify({
                'success': False,
                'error': 'Technician not found'
            }), 404
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Prepare ticket data
        ticket_data = {
            'office_name': data['office_name'],
            'technician': technician.username,
            'technician_id': data['technician_id'],
            'description': data['description'],
            'scheduled_date': data['scheduled_date'],
            'scheduled_time': data['scheduled_time'],
            'priority': data.get('priority', 'Medium'),
            'urgency': data.get('urgency', 'Medium'),
            'estimated_duration': data.get('estimated_duration', '2 hours'),
            'stage': 'scheduled',
            'category': 'IT'
        }
        
        # Create ticket in database
        new_ticket = db_manager.create_ticket(ticket_data, current_user.id)
        
        # Convert to dashboard format
        dashboard_ticket = convert_db_tickets_to_dashboard_format([new_ticket])[0]
        
        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'ticket': dashboard_ticket
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating ticket: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
@login_required
def update_ticket(ticket_id):
    """Update an existing ticket in the database."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        data = request.get_json()
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Update ticket in database
        updated_ticket = db_manager.update_ticket(ticket_id, data, current_user.id)
        
        # Convert to dashboard format
        dashboard_ticket = convert_db_tickets_to_dashboard_format([updated_ticket])[0]
        
        return jsonify({
            'success': True,
            'message': 'Ticket updated successfully',
            'ticket': dashboard_ticket
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/tickets/<int:ticket_id>/stage', methods=['PUT'])
@login_required
def update_ticket_stage(ticket_id):
    """Update ticket stage in the database."""
    try:
        data = request.get_json()
        new_stage = data.get('stage')
        
        if not new_stage:
            return jsonify({
                'success': False,
                'error': 'Stage is required'
            }), 400
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Update ticket stage in database
        updated_ticket = db_manager.update_ticket_stage(ticket_id, new_stage, current_user.id)
        
        # Convert to dashboard format
        dashboard_ticket = convert_db_tickets_to_dashboard_format([updated_ticket])[0]
        
        return jsonify({
            'success': True,
            'message': f'Ticket stage updated to {new_stage}',
            'ticket': dashboard_ticket
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Error updating ticket stage {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/tickets/<int:ticket_id>/urgency', methods=['PUT'])
@login_required
def update_ticket_urgency(ticket_id):
    """Update ticket urgency in the database."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        data = request.get_json()
        new_urgency = data.get('urgency')
        
        if not new_urgency:
            return jsonify({
                'success': False,
                'error': 'Urgency is required'
            }), 400
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Update ticket urgency in database
        updated_ticket = db_manager.update_ticket_urgency(ticket_id, new_urgency, current_user.id)
        
        # Convert to dashboard format
        dashboard_ticket = convert_db_tickets_to_dashboard_format([updated_ticket])[0]
        
        return jsonify({
            'success': True,
            'message': f'Ticket urgency updated to {new_urgency}',
            'ticket': dashboard_ticket
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Error updating ticket urgency {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/calendar')
@login_required
def get_calendar_data():
    """Get calendar data for the current month from database and file system."""
    try:
        # Get current month
        now = datetime.now()
        current_month = now.strftime('%B %Y')
        
        all_events = []
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if db_manager:
            # Get tickets from database
            db_tickets = db_manager.get_all_tickets()
            if db_tickets:
                # Convert database tickets to calendar events
                for ticket in db_tickets:
                    if ticket.get('scheduled_date'):
                        # Use the clean title if available, otherwise fall back to ticket number and office
                        title = ticket.get('title', f"{ticket['ticket_number']} - {ticket['office_name']}")
                        all_events.append({
                            'id': ticket['id'],
                            'title': title,
                            'date': ticket['scheduled_date'],
                            'time': ticket.get('scheduled_time', '09:00'),
                            'priority': ticket.get('priority', 'Medium'),
                            'stage': ticket.get('stage', 'scheduled'),
                            'type': 'ticket',
                            'technician': ticket.get('technician', 'Unassigned')
                        })
            
            # Get calendar events from database
            db_events = db_manager.get_calendar_events()
            for event in db_events:
                all_events.append({
                    'id': event['id'],
                    'title': event['title'],
                    'date': event['event_date'],
                    'time': event.get('event_time', '09:00'),
                    'priority': event.get('priority', 'Medium'),
                    'stage': 'scheduled',
                    'type': 'calendar_event',
                    'technician': event.get('technician', 'Unassigned')
                })
        
        # If no database events, fallback to file system
        if not all_events:
            file_manager = get_patterson_file_manager()
            if file_manager:
                file_tickets = file_manager.get_tickets()
                if file_tickets:
                    dashboard_tickets = convert_file_tickets_to_dashboard_format(file_tickets)
                    
                    # Add ticket events
                    for ticket in dashboard_tickets:
                        # Try to extract a date from the subject/title first
                        subject_date = extract_date_from_subject(ticket.get('subject', ''))
                        
                        # Use subject date if found, otherwise use scheduled_date
                        event_date = subject_date if subject_date else ticket.get('scheduled_date')
                        
                        # Only add to calendar if we have a valid date
                        if event_date:
                            # Use the clean title if available, otherwise fall back to ticket number and office
                            title = ticket.get('title', f"{ticket['ticket_number']} - {ticket['office_name']}")
                            all_events.append({
                                'id': ticket['id'],
                                'title': title,
                                'date': event_date,
                                'time': ticket.get('scheduled_time', '09:00'),
                                'priority': ticket['priority'],
                                'stage': ticket['stage'],
                                'type': 'ticket',
                                'technician': ticket.get('technician', 'Unassigned')
                            })
                    
                    # Get calendar events from file
                    calendar_events = file_manager.get_calendar_events()
                    for event in calendar_events:
                        if event.get('scheduled_date'):
                            all_events.append({
                                'id': event['id'],
                                'title': event.get('title', event.get('ticket_number', 'Event')),
                                'date': event['scheduled_date'],
                                'time': event.get('scheduled_time', '09:00'),
                                'priority': event.get('priority', 'Medium'),
                                'stage': event.get('stage', 'scheduled'),
                                'type': 'calendar_event',
                                'technician': event.get('technician', 'Unassigned')
                            })
        
        # Group events by date
        from collections import defaultdict
        events_by_date = defaultdict(list)
        for event in all_events:
            event_date = event.get('date')
            if event_date:
                # Handle cases where date might have a time component
                if isinstance(event_date, datetime):
                    event_date_str = event_date.strftime('%Y-%m-%d')
                else:
                    event_date_str = str(event_date).split('T')[0]
                events_by_date[event_date_str].append(event)
        
        # Create summary events for the calendar
        summary_events = []
        for date, daily_events in events_by_date.items():
            count = len(daily_events)
            summary_events.append({
                'date': date,
                'count': count,
                'tickets': daily_events
            })

        return jsonify({
            'success': True,
            'events': summary_events,
            'current_month': current_month
        })
    except Exception as e:
        current_app.logger.error(f"Error getting calendar data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/technicians')
@login_required
def get_technicians():
    """Get all technicians from the database, including both mapped users and unmapped Freshworks IDs."""
    try:
        technician_data = []
        
        # Step 1: Get users with technician role or specific criteria
        technicians = User.query.filter(
            (User.role == 'technician') | 
            (User.role == 'admin') |
            (User.username.contains('tech'))
        ).all()
        
        for tech in technicians:
            technician_data.append({
                'id': tech.id,
                'name': tech.username,
                'email': tech.email,
                'role': tech.role,
                'source': 'user_database'
            })
        
        # Step 2: Get mapped Freshworks users
        mapped_users = UserMapping.query.filter_by(is_active=True).all()
        for mapping in mapped_users:
            technician_data.append({
                'id': mapping.freshworks_id,  # Use freshworks_id as the ID
                'name': mapping.name,
                'email': mapping.email or '',
                'role': mapping.role or 'technician',
                'source': 'user_mapping'
            })
        
        # Step 3: Get unmapped Freshworks IDs from tickets
        # Get all distinct technician IDs that are already mapped
        mapped_ids = {
            str(mapping.freshworks_id)
            for mapping in UserMapping.query.filter_by(is_active=True).all()
        }
        
        # Get all tickets to find unmapped IDs
        all_tickets = PattersonTicket.query.all()
        unmapped_ids = set()
        
        for ticket in all_tickets:
            # Check 'responder_id' - often the most reliable source
            if getattr(ticket, 'responder_id', None) is not None:
                unmapped_ids.add(str(ticket.responder_id))
            
            # Check 'technician_id'
            if getattr(ticket, 'technician_id', None) is not None:
                unmapped_ids.add(str(ticket.technician_id))
            
            # Fallback to extracting from the 'technician' text field
            if getattr(ticket, 'technician', None):
                import re
                matches = re.findall(r'\d+', ticket.technician)
                for match in matches:
                    unmapped_ids.add(match)
        
        # Add unmapped IDs that aren't already mapped
        for user_id in unmapped_ids:
            if user_id and user_id not in mapped_ids:
                # Try to find a name from tickets
                name = 'Unknown Technician'
                for ticket in all_tickets:
                    if (getattr(ticket, 'responder_id', None) == user_id or 
                        getattr(ticket, 'technician_id', None) == user_id or
                        (ticket.technician and user_id in ticket.technician)):
                        if ticket.technician and not ticket.technician.isdigit():
                            name = ticket.technician
                            break
                
                technician_data.append({
                    'id': user_id,
                    'name': f"{name} (ID: {user_id})",
                    'email': '',
                    'role': 'technician',
                    'source': 'unmapped_freshworks'
                })
        
        return jsonify({
            'success': True,
            'technicians': technician_data
        })
    except Exception as e:
        current_app.logger.error(f"Error getting technicians: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/offices')
@login_required
def get_offices():
    """Get all offices from CSV file."""
    try:
        offices = load_offices_from_csv()
        office_names = [office['display'] for office in offices]
        
        return jsonify({
            'success': True,
            'offices': office_names
        })
    except Exception as e:
        current_app.logger.error(f"Error getting offices: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/refresh')
@login_required
def refresh_data():
    """Refresh data from Freshworks using the working freshworks.py logic."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        # Run freshworks.py **in a dedicated subprocess** so Eventlet's monkey-patching
        # (especially greendns) cannot interfere with DNS resolution.
        try:
            script_path = os.path.join(current_app.root_path, 'freshworks.py')

            # Execute the script with the same Python interpreter; capture output for logging.
            completed = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                check=False
            )

            # Log stdout / stderr for auditing & troubleshooting.
            if completed.stdout:
                current_app.logger.info("freshworks.py stdout:\n%s", completed.stdout.strip())
            if completed.stderr:
                current_app.logger.warning("freshworks.py stderr:\n%s", completed.stderr.strip())

            # Extract how many tickets were added today (look for the ✅ Added … line)
            added_count = 0
            m = re.search(r"Added\s+(\d+)\s+new ticket", completed.stdout or "")
            if m:
                added_count = int(m.group(1))
            
            current_app.logger.info(
                "freshworks.py finished with return code %s – %s new tickets", completed.returncode, added_count
            )

            # Sync refreshed data to database
            db_manager = get_patterson_db_manager()
            if db_manager:
                # Sync the new file data to database
                sync_success = db_manager.sync_file_data_to_db()
                
                # Update persistent timer so countdown restarts (3-hour window)
                try:
                    timer_file = os.path.join(current_app.root_path, 'Freshworks', 'persistent_timer.txt')
                    os.makedirs(os.path.dirname(timer_file), exist_ok=True)
                    with open(timer_file, 'w') as tf:
                        tf.write(datetime.now().isoformat())
                except Exception as timer_err:
                    current_app.logger.warning("Failed to update persistent timer: %s", timer_err)
                
                # Get updated ticket count
                all_db_tickets = db_manager.get_all_tickets()
                total_tickets = len(all_db_tickets)
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully pulled {added_count} tickets from Freshworks and synced to database',
                    'tickets_pulled': added_count,
                    'total_tickets_in_db': total_tickets,
                    'sync_success': sync_success,
                    'timer_updated': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f'Successfully pulled {added_count} tickets from Freshworks (database sync not available)',
                    'tickets_pulled': added_count,
                    'database_sync': False,
                    'timer_updated': datetime.now().isoformat()
                })
                
        except Exception as e:
            current_app.logger.error("freshworks.py script not found at %s", script_path)
            return jsonify({
                'success': False,
                'error': 'Freshworks script not available'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error refreshing data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/status')
@login_required
def get_freshworks_status():
    """Get Freshworks connection status."""
    try:
        # Test Freshworks connectivity
        if not Config.FRESH_ENDPOINT or Config.FRESH_ENDPOINT == 'https://your-domain.freshdesk.com/api/v2/':
            return jsonify({
                'success': False,
                'connected': False,
                'message': 'Freshworks not configured'
            })
        
        # Test API connectivity directly
        try:
            query = 'tag:patterson-dispatch AND status:2'
            response = requests.get(
                        f"{Config.FRESH_ENDPOINT}tickets/filter?query=\"{query}\"",
        auth=(Config.FRESH_API, 'TICKETS'),
                timeout=10
            )
            
            if response.status_code == 200:
                tickets = response.json().get('tickets', [])
                return jsonify({
                    'success': True,
                    'connected': True,
                    'message': f'Connected to Freshworks - {len(tickets)} tickets found',
                    'ticket_count': len(tickets)
                })
            else:
                return jsonify({
                    'success': False,
                    'connected': False,
                    'message': f'Freshworks API error: {response.status_code}'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'connected': False,
                'message': f'API connection failed: {str(e)}'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error checking Freshworks status: {str(e)}")
        return jsonify({
            'success': False,
            'connected': False,
            'message': str(e)
        }), 500

@bp.route('/api/unmapped-users')
@login_required
def get_unmapped_users():
    """
    Get a robust list of user IDs from tickets that don't have active mappings yet.
    This version checks multiple fields to ensure all potential users are found.
    Now queries db/freshworks.db directly.
    """
    import sqlite3
    from app.models.base import UserMapping
    from flask import current_app
    try:
        # Step 1: Get all distinct technician IDs that are already actively mapped
        mapped_ids = {
            str(mapping.freshworks_id)
            for mapping in UserMapping.query.filter_by(is_active=True).all()
        }

        # Step 2: Query db/freshworks.db for all tickets
        conn = sqlite3.connect('db/freshworks.db')
        cursor = conn.cursor()
        cursor.execute("SELECT technician_id, technician FROM patterson_tickets")
        rows = cursor.fetchall()
        conn.close()

        potential_unmapped = {}
        for technician_id, technician in rows:
            ids_in_ticket = set()
            if technician_id:
                ids_in_ticket.add(str(technician_id))
            if technician:
                import re
                matches = re.findall(r'\d+', technician)
                for match in matches:
                    ids_in_ticket.add(match)
            for user_id_str in ids_in_ticket:
                if user_id_str and user_id_str not in mapped_ids:
                    if user_id_str not in potential_unmapped:
                        potential_unmapped[user_id_str] = {
                            'id': user_id_str,
                            'name': technician if technician and not technician.isdigit() else f'Unknown ({user_id_str})',
                            'ticket_count': 0,
                            'last_seen': None
                        }
                    potential_unmapped[user_id_str]['ticket_count'] += 1
        # Step 3: Format the output
        unmapped_users_data = [
            {
                'id': data['id'],
                'name': data['name'],
                'ticket_count': data['ticket_count'],
                'last_seen': data['last_seen'] or 'N/A'
            }
            for data in potential_unmapped.values()
        ]
        # Sort by ticket count (most active first)
        unmapped_users_data.sort(key=lambda x: x['ticket_count'], reverse=True)
        return jsonify({'success': True, 'users': unmapped_users_data})
    except Exception as e:
        current_app.logger.error(f"Error getting unmapped users: {str(e)}")
        return jsonify({'success': False, 'error': str(e), 'users': []}), 500

@bp.route('/api/user-mappings')
@login_required
def get_user_mappings():
    """Get all user mappings."""
    try:
        mappings = UserMapping.query.filter_by(is_active=True).all()
        mapping_data = []
        
        for mapping in mappings:
            # Update statistics before returning
            mapping.update_ticket_stats()
            mapping_data.append(mapping.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mappings': mapping_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user mappings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/user-mappings', methods=['POST'])
@login_required
def add_user_mapping():
    """Add a new user mapping."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('freshworks_id') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: freshworks_id and name'
            }), 400
        
        # Check if mapping already exists
        existing = UserMapping.query.filter_by(freshworks_id=data['freshworks_id']).first()
        if existing:
            # Update existing mapping
            existing.name = data['name']
            existing.email = data.get('email', '')
            existing.role = data.get('role', 'technician')
            existing.region = data.get('region', '')
            existing.user_id = data.get('user_id')
            existing.updated_at = datetime.utcnow()
            
            # Auto-verify if email matches linked user
            if data.get('auto_verify', False) and existing.user_id:
                linked_user = User.query.get(existing.user_id)
                if linked_user and linked_user.email == existing.email:
                    existing.is_verified = True
            
            # Update ticket statistics
            existing.update_ticket_stats()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'User mapping updated successfully',
                'mapping': existing.to_dict()
            })
        else:
            # Create new mapping
            new_mapping = UserMapping(
                freshworks_id=data['freshworks_id'],
                name=data['name'],
                email=data.get('email', ''),
                role=data.get('role', 'technician'),
                region=data.get('region', ''),
                user_id=data.get('user_id'),
                notes=data.get('notes', '')
            )
            
            # Auto-verify if email matches linked user
            if data.get('auto_verify', False) and new_mapping.user_id:
                linked_user = User.query.get(new_mapping.user_id)
                if linked_user and linked_user.email == new_mapping.email:
                    new_mapping.is_verified = True
            
            db.session.add(new_mapping)
            db.session.commit()
            
            # Update ticket statistics
            new_mapping.update_ticket_stats()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'User mapping created successfully',
                'mapping': new_mapping.to_dict()
            })
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding user mapping: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/user-mappings/<int:mapping_id>', methods=['DELETE'])
@login_required
def delete_user_mapping(mapping_id):
    """Delete a user mapping."""
    if current_user.role == 'user':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        # Get the mapping
        mapping = UserMapping.query.filter_by(freshworks_id=mapping_id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
        # Delete the mapping
        db.session.delete(mapping)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mapping deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/mapping-statistics')
@login_required
def get_mapping_statistics():
    """Get statistics for user mappings."""
    try:
        import sqlite3
        
        # Count mapped users
        mapped_users = UserMapping.query.filter_by(is_active=True).count()
        
        # Count total tickets
        total_tickets = PattersonTicket.query.count()
        
        # Get all distinct technician IDs that are already actively mapped
        mapped_ids = {
            str(mapping.freshworks_id)
            for mapping in UserMapping.query.filter_by(is_active=True).all()
        }
        
        # Query db/freshworks.db for all tickets to get accurate counts
        conn = sqlite3.connect('db/freshworks.db')
        cursor = conn.cursor()
        cursor.execute("SELECT technician_id, technician FROM patterson_tickets")
        rows = cursor.fetchall()
        conn.close()
        
        # Count assigned tickets (tickets with technician_id)
        assigned_tickets = 0
        potential_unmapped = {}
        
        for technician_id, technician in rows:
            ids_in_ticket = set()
            if technician_id:
                ids_in_ticket.add(str(technician_id))
                assigned_tickets += 1  # Count as assigned if technician_id exists
            if technician:
                import re
                matches = re.findall(r'\d+', technician)
                for match in matches:
                    ids_in_ticket.add(match)
            
            # Track unmapped users
            for user_id_str in ids_in_ticket:
                if user_id_str and user_id_str not in mapped_ids:
                    if user_id_str not in potential_unmapped:
                        potential_unmapped[user_id_str] = {
                            'id': user_id_str,
                            'name': technician if technician and not technician.isdigit() else f'Unknown ({user_id_str})',
                            'ticket_count': 0,
                            'last_seen': None
                        }
                    potential_unmapped[user_id_str]['ticket_count'] += 1
        
        # Count unmapped users
        unmapped_users = len(potential_unmapped)
        
        # Calculate total unique users (mapped + unmapped)
        total_users = mapped_users + unmapped_users
        
        # Calculate percentage of users mapped
        coverage_percentage = 0
        if total_users > 0:
            coverage_percentage = round((mapped_users / total_users) * 100, 1)
        
        stats = {
            'mapped_users': mapped_users,
            'unmapped_users': unmapped_users,
            'total_tickets': total_tickets,
            'assigned_tickets': assigned_tickets,
            'coverage': coverage_percentage
        }
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/user-mappings/<int:mapping_id>', methods=['GET'])
@login_required
def get_user_mapping(mapping_id):
    """Get a specific user mapping for editing."""
    try:
        mapping = UserMapping.query.filter_by(freshworks_id=mapping_id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
        mapping_data = {
            'freshworks_id': mapping.freshworks_id,
            'name': mapping.name,
            'email': mapping.email,
            'role': mapping.role,
            'region': mapping.region
        }
        
        return jsonify({'success': True, 'mapping': mapping_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/user-mappings/<int:mapping_id>', methods=['PUT'])
@login_required
def update_user_mapping(mapping_id):
    """Update a user mapping."""
    if current_user.role == 'user':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Get the mapping
        mapping = UserMapping.query.filter_by(freshworks_id=mapping_id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
        # Update the mapping
        mapping.name = data.get('name', mapping.name)
        mapping.email = data.get('email', mapping.email)
        mapping.role = data.get('role', mapping.role)
        mapping.region = data.get('region', mapping.region)
        mapping.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mapping updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/user-tickets/<int:user_id>')
@login_required
def get_user_tickets(user_id):
    """Get tickets for a specific user."""
    try:
        # Get tickets where this user is the technician
        tickets = PattersonTicket.query.filter_by(freshworks_id=user_id).all()
        
        ticket_data = []
        for ticket in tickets:
            ticket_data.append({
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'title': ticket.title,
                'status': ticket.status,
                'scheduled_date': ticket.scheduled_date.isoformat() if ticket.scheduled_date else None,
                'priority': ticket.priority
            })
        
        return jsonify({'success': True, 'tickets': ticket_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/available-users')
@login_required
def get_available_users():
    """Get all available users for linking."""
    try:
        users = User.query.filter_by(is_active=True).all()
        user_data = []
        
        for user in users:
            # Check if user is already linked to a mapping
            existing_mapping = UserMapping.query.filter_by(user_id=user.id).first()
            if not existing_mapping:
                user_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                })
        
        return jsonify({'success': True, 'users': user_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/search-users')
@login_required
def search_users():
    """Search users by username or email."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'success': True, 'users': []})
        
        # Search by username or email
        users = User.query.filter(
            db.or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            ),
            User.is_active == True
        ).limit(10).all()
        
        user_data = []
        for user in users:
            # Check if user is already linked
            existing_mapping = UserMapping.query.filter_by(user_id=user.id).first()
            if not existing_mapping:
                user_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                })
        
        return jsonify({'success': True, 'users': user_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/user-stats/<int:freshworks_id>')
@login_required
def get_user_stats(freshworks_id):
    """Get detailed statistics for a specific user."""
    try:
        mapping = UserMapping.query.filter_by(freshworks_id=freshworks_id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
        # Update stats first
        mapping.update_ticket_stats()
        db.session.commit()
        
        # Get recent activity (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        tickets = PattersonTicket.query.filter_by(freshworks_id=freshworks_id).all()
        recent_tickets = [t for t in tickets if t.created_at >= thirty_days_ago]
        
        # Group by date
        activity_by_date = {}
        for ticket in recent_tickets:
            date_str = ticket.created_at.strftime('%Y-%m-%d')
            if date_str not in activity_by_date:
                activity_by_date[date_str] = {'count': 0, 'completed': 0}
            activity_by_date[date_str]['count'] += 1
            if ticket.stage == 'completed':
                activity_by_date[date_str]['completed'] += 1
        
        recent_activity = []
        for date_str, data in sorted(activity_by_date.items(), reverse=True)[:10]:
            status = 'completed' if data['completed'] == data['count'] else 'mixed'
            status_color = 'success' if status == 'completed' else 'warning'
            recent_activity.append({
                'date': date_str,
                'ticket_count': data['count'],
                'status': status,
                'status_color': status_color
            })
        
        stats = {
            'name': mapping.name,
            'total_tickets_handled': mapping.total_tickets_handled,
            'tickets_this_month': mapping.tickets_this_month,
            'tickets_this_week': mapping.tickets_this_week,
            'average_resolution_time': mapping.average_resolution_time,
            'success_rate': mapping.success_rate,
            'last_ticket_date': mapping.last_ticket_date.isoformat() if mapping.last_ticket_date else None,
            'linked_username': mapping.linked_user.username if mapping.linked_user else None,
            'recent_activity': recent_activity
        }
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/update-all-stats', methods=['POST'])
@login_required
def update_all_stats():
    """Update statistics for all user mappings."""
    if current_user.role == 'user':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        mappings = UserMapping.query.filter_by(is_active=True).all()
        
        for mapping in mappings:
            mapping.update_ticket_stats()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Updated stats for {len(mappings)} mappings'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/next-refresh')
@login_required
def get_next_refresh_time():
    """Get the next refresh time for non-user roles with persistent timer."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        # Persistent timer file path
        timer_file = os.path.join(current_app.root_path, 'Freshworks', 'persistent_timer.txt')
        refresh_interval = 3 * 60 * 60  # 3 hours in seconds
        
        # Ensure Freshworks directory exists
        os.makedirs(os.path.dirname(timer_file), exist_ok=True)
        
        # Try to read existing timer state
        if os.path.exists(timer_file):
            try:
                with open(timer_file, 'r') as f:
                    timer_data = f.read().strip()
                    if timer_data:
                        last_update = datetime.fromisoformat(timer_data)
                        next_refresh = last_update + timedelta(seconds=refresh_interval)
                        time_until_refresh = (next_refresh - datetime.now()).total_seconds()
                        
                        # If timer has expired, update it to now
                        if time_until_refresh <= 0:
                            current_time = datetime.now()
                            with open(timer_file, 'w') as f:
                                f.write(current_time.isoformat())
                            
                            return jsonify({
                                'success': True,
                                'last_update': current_time.isoformat(),
                                'next_refresh': (current_time + timedelta(seconds=refresh_interval)).isoformat(),
                                'time_until_refresh': refresh_interval,
                                'refresh_interval': refresh_interval,
                                'source': 'persistent_timer_reset'
                            })
                        
                        return jsonify({
                            'success': True,
                            'last_update': last_update.isoformat(),
                            'next_refresh': next_refresh.isoformat(),
                            'time_until_refresh': max(0, time_until_refresh),
                            'refresh_interval': refresh_interval,
                            'source': 'persistent_timer'
                        })
            except Exception as e:
                current_app.logger.error(f"Error reading persistent timer: {e}")
        
        # If no timer file exists or error reading, create new timer
        current_time = datetime.now()
        with open(timer_file, 'w') as f:
            f.write(current_time.isoformat())
        
        return jsonify({
            'success': True,
            'last_update': current_time.isoformat(),
            'next_refresh': (current_time + timedelta(seconds=refresh_interval)).isoformat(),
            'time_until_refresh': refresh_interval,
            'refresh_interval': refresh_interval,
            'source': 'new_persistent_timer'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting next refresh time: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/upload-file', methods=['POST'])
@login_required
def upload_file():
    """Upload a file to be processed and displayed."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file extension
        allowed_extensions = {'txt', 'csv', 'json'}
        if not file.filename.lower().endswith(tuple(f'.{ext}' for ext in allowed_extensions)):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only .txt, .csv, and .json files are allowed.'
            }), 400
        
        # Get file manager
        file_manager = get_patterson_file_manager()
        if not file_manager:
            return jsonify({
                'success': False,
                'error': 'Patterson file manager not initialized'
            }), 500
        
        # Save uploaded file with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"uploaded_{timestamp}_{file.filename}"
        upload_path = os.path.join(file_manager.FRESHWORKS_DIR, filename)
        
        file.save(upload_path)
        
        # Process the file based on its type
        tickets = []
        if filename.endswith('.txt'):
            tickets = file_manager.parse_txt_file(upload_path)
        elif filename.endswith('.csv'):
            tickets = file_manager.parse_csv_file(upload_path)
        elif filename.endswith('.json'):
            tickets = file_manager.parse_json_file(upload_path)
        
        if tickets:
            # Convert to dashboard format
            dashboard_tickets = convert_file_tickets_to_dashboard_format(tickets)
            
            return jsonify({
                'success': True,
                'message': f'File uploaded and processed successfully. Found {len(dashboard_tickets)} tickets.',
                'tickets': dashboard_tickets,
                'filename': filename
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No valid ticket data found in the uploaded file.'
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error uploading file: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/calendar/events', methods=['POST'])
@login_required
def create_calendar_event():
    """Create a new calendar event in the database."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['date', 'title', 'description']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate date format
        try:
            event_date = datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        # Get technician name if technician_id is provided
        technician_name = 'Unassigned'
        if data.get('technician_id'):
            technician = User.query.get(data['technician_id'])
            if technician:
                technician_name = technician.username
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Prepare event data
        event_data = {
            'title': data['title'],
            'description': data['description'],
            'office': data.get('office', 'General'),
            'technician_id': data.get('technician_id'),
            'technician_name': technician_name,
            'event_date': data['date'],
            'event_time': data.get('time', '09:00'),
            'duration': data.get('duration', '1 hour'),
            'priority': data.get('priority', 'Medium'),
            'urgency': data.get('urgency', 'Medium')
        }
        
        # Create calendar event in database
        new_event = db_manager.create_calendar_event(event_data, current_user.id)
        
        # Convert to dashboard format
        dashboard_event = {
            'id': new_event['id'],
            'title': new_event['title'],
            'date': new_event['event_date'],
            'time': new_event['event_time'],
            'priority': new_event['priority'],
            'stage': 'scheduled',
            'type': 'calendar_event'
        }
        
        return jsonify({
            'success': True,
            'message': 'Calendar event created successfully',
            'event': dashboard_event
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating calendar event: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/tickets/<int:ticket_id>/edit', methods=['GET'])
@login_required
def get_ticket_for_edit(ticket_id):
    """Get ticket data for editing (enhanced for non-user roles)."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        # Get tickets from file manager
        file_manager = get_patterson_file_manager()
        if not file_manager:
            return jsonify({
                'success': False,
                'error': 'Patterson file manager not initialized'
            }), 500
        
        file_tickets = file_manager.get_tickets()
        dashboard_tickets = convert_file_tickets_to_dashboard_format(file_tickets)
        
        # Find the specific ticket
        ticket = next((t for t in dashboard_tickets if t['id'] == ticket_id), None)
        
        if not ticket:
            return jsonify({
                'success': False,
                'error': 'Ticket not found'
            }), 404
        
        # Add additional fields for enhanced editing
        enhanced_ticket = {
            **ticket,
            'can_edit_all': True,
            'available_priorities': ['Low', 'Medium', 'High', 'Urgent'],
            'available_urgencies': ['Low', 'Medium', 'High', 'Urgent'],
            'available_stages': ['in_progress', 'scheduled', 'completed'],
            'available_durations': ['30 minutes', '1 hour', '1.5 hours', '2 hours', '3 hours', '4 hours', 'Full day']
        }
        
        return jsonify({
            'success': True,
            'ticket': enhanced_ticket
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting ticket for edit: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/initialize-database', methods=['POST'])
@login_required
def initialize_database():
    """Initialize database with all historical ticket data and clear all existing tickets."""
    try:
        if current_user.role != 'admin':
            return jsonify({
                'success': False,
                'error': 'Access denied - admin role required'
            }), 403
        
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Clear ALL tickets first (not just test tickets)
        tickets_cleared, events_cleared = db_manager.clear_all_tickets()
        
        # Import all historical files
        imported_count = db_manager.import_all_historical_files()
        
        # Sync current data
        sync_success = db_manager.sync_file_data_to_db()
        
        # Get total tickets in database
        total_tickets = len(db_manager.get_all_tickets())
        
        # Get tickets with titles
        tickets_with_titles = PattersonTicket.query.filter(
            PattersonTicket.title.isnot(None),
            PattersonTicket.title != ''
        ).count()
        
        return jsonify({
            'success': True,
            'message': f'Database initialized successfully',
            'tickets_cleared': tickets_cleared,
            'events_cleared': events_cleared,
            'tickets_imported': imported_count,
            'sync_success': sync_success,
            'total_tickets_in_db': total_tickets,
            'tickets_with_titles': tickets_with_titles
        })
        
    except Exception as e:
        current_app.logger.error(f"Error initializing database: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/freshworks-tickets')
@login_required
def get_freshworks_tickets():
    """Get tickets from the Freshworks database manager."""
    try:
        # Initialize the Freshworks database manager if not already done
        if not get_freshworks_db_manager():
            if init_freshworks_db_manager:
                init_freshworks_db_manager(current_app)
            else:
                return jsonify({'error': 'Freshworks database manager not available'}), 500
        
        freshworks_manager = get_freshworks_db_manager()
        if not freshworks_manager:
            return jsonify({'error': 'Failed to initialize Freshworks database manager'}), 500
        
        # Get all tickets from the database
        db_tickets = freshworks_manager.get_all_tickets()
        
        # Convert to dashboard format
        dashboard_tickets = []
        for ticket in db_tickets:
            # Convert database ticket to dashboard format
            dashboard_ticket = {
                'id': ticket['id'],
                'freshworks_id': ticket.get('freshworks_id'),
                'ticket_number': ticket['ticket_number'],
                'title': ticket.get('title', 'Untitled Ticket'),
                'original_title': ticket.get('original_title', ''),
                'office_name': ticket.get('office_name', 'Unknown Office'),
                'technician': ticket.get('technician', 'Unassigned'),
                'technician_id': ticket.get('technician_id'),
                'description': ticket.get('description', ''),
                'priority': ticket.get('priority', 'Medium'),
                'urgency': ticket.get('urgency', 'Medium'),
                'status': ticket.get('status', 'Open'),
                'scheduled_date': ticket.get('scheduled_date'),
                'scheduled_time': ticket.get('scheduled_time', '09:00'),
                'estimated_duration': ticket.get('estimated_duration', '2 hours'),
                'stage': ticket.get('stage', 'in_progress'),
                'category': ticket.get('category', 'IT'),
                'source': ticket.get('source', 'Freshworks'),
                'notes': ticket.get('notes', []),
                'file_source': ticket.get('file_source', ''),
                'created_at': ticket.get('created_at'),
                'updated_at': ticket.get('updated_at')
            }
            dashboard_tickets.append(dashboard_ticket)
        
        # Get ticket statistics
        stats = freshworks_manager.get_ticket_stats()
        
        return jsonify({
            'success': True,
            'tickets': dashboard_tickets,
            'stats': stats,
            'source': 'freshworks_database',
            'total_tickets': len(dashboard_tickets),
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting Freshworks tickets: {str(e)}")
        return jsonify({'error': f'Failed to get tickets: {str(e)}'}), 500

@bp.route('/api/import-dated-files', methods=['POST'])
@login_required
def import_dated_files():
    """Import all dated .txt files from the Freshworks directory into the database."""
    try:
        # Get the Patterson database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({'error': 'Failed to initialize Patterson database manager'}), 500
        
        # Import all dated files
        total_imported = db_manager.import_all_dated_files()
        
        # Get updated ticket count
        all_tickets = db_manager.get_all_tickets()
        total_tickets = len(all_tickets)
        
        # Get ticket statistics
        stats = {
            'total_tickets': total_tickets,
            'in_progress': len([t for t in all_tickets if t.get('stage') == 'in_progress']),
            'scheduled': len([t for t in all_tickets if t.get('stage') == 'scheduled']),
            'completed': len([t for t in all_tickets if t.get('stage') == 'completed'])
        }
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {total_imported} tickets from all dated files',
            'total_imported': total_imported,
            'stats': stats,
            'total_tickets_in_db': total_tickets,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error importing dated files: {str(e)}")
        return jsonify({'error': f'Failed to import files: {str(e)}'}), 500

@bp.route('/api/freshworks-import', methods=['POST'])
@login_required
def import_freshworks_files():
    """Import all dated Freshworks files into the database."""
    try:
        # Initialize the Freshworks database manager if not already done
        if not get_freshworks_db_manager():
            if init_freshworks_db_manager:
                init_freshworks_db_manager(current_app)
            else:
                return jsonify({'error': 'Freshworks database manager not available'}), 500
        
        freshworks_manager = get_freshworks_db_manager()
        if not freshworks_manager:
            return jsonify({'error': 'Failed to initialize Freshworks database manager'}), 500
        
        # Import all dated files
        total_imported = freshworks_manager.import_all_dated_files()
        
        # Get updated ticket count
        stats = freshworks_manager.get_ticket_stats()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {total_imported} tickets from all dated files',
            'total_imported': total_imported,
            'stats': stats,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error importing Freshworks files: {str(e)}")
        return jsonify({'error': f'Failed to import files: {str(e)}'}), 500

@bp.route('/api/freshworks-clear', methods=['POST'])
@login_required
def clear_freshworks_database():
    """Clear all tickets from the Freshworks database."""
    try:
        # Initialize the Freshworks database manager if not already done
        if not get_freshworks_db_manager():
            if init_freshworks_db_manager:
                init_freshworks_db_manager(current_app)
            else:
                return jsonify({'error': 'Freshworks database manager not available'}), 500
        
        freshworks_manager = get_freshworks_db_manager()
        if not freshworks_manager:
            return jsonify({'error': 'Failed to initialize Freshworks database manager'}), 500
        
        # Clear all tickets
        cleared_count = freshworks_manager.clear_all_tickets()
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {cleared_count} tickets from the database',
            'cleared_count': cleared_count,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error clearing Freshworks database: {str(e)}")
        return jsonify({'error': f'Failed to clear database: {str(e)}'}), 500

def get_technician_name(technician_id):
    """Get technician name from UserMapping database."""
    if not technician_id:
        return 'Unassigned'
    
    # Try to get technician name from UserMapping database
    user_mapping = UserMapping.query.filter_by(
        freshworks_id=str(technician_id),
        is_active=True
    ).first()
    
    if user_mapping:
        return user_mapping.name
    else:
        # If no mapping exists, show as unmapped
        return f"Technician {technician_id} (Unmapped)"

def get_priority_from_status(status):
    """Get priority from status code."""
    priority_map = {
        1: 'Low',
        2: 'Medium', 
        3: 'High',
        4: 'Urgent'
    }
    return priority_map.get(status, 'Medium')

def map_status(status):
    """Map status code to status string."""
    status_map = {
        1: 'Open',
        2: 'In Progress',
        3: 'Pending',
        4: 'Resolved',
        5: 'Closed'
    }
    return status_map.get(status, 'Open')

@bp.route('/api/calendar/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_calendar_event(event_id):
    """Delete a calendar event (admin only)."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Delete the calendar event
        success = db_manager.delete_calendar_event(event_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Calendar event deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Calendar event not found or could not be deleted'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error deleting calendar event: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/calendar/events/<int:event_id>', methods=['PUT'])
@login_required
def update_calendar_event(event_id):
    """Update a calendar event (admin only)."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'date', 'description']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Update the calendar event
        updated_event = db_manager.update_calendar_event(event_id, data)
        
        if updated_event:
            return jsonify({
                'success': True,
                'message': 'Calendar event updated successfully',
                'event': updated_event
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Calendar event not found or could not be updated'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error updating calendar event: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/tickets/<int:ticket_id>', methods=['DELETE'])
@login_required
def delete_ticket(ticket_id):
    """Delete a ticket (admin only)."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Delete the ticket
        success = db_manager.delete_ticket(ticket_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Ticket deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ticket not found or could not be deleted'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error deleting ticket: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/manual-api-pull', methods=['POST'])
@login_required
def manual_api_pull():
    """Manually pull data from Freshworks API using the working freshworks.py logic (admin only)."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        # Run freshworks.py **in a dedicated subprocess** so Eventlet's monkey-patching
        # (especially greendns) cannot interfere with DNS resolution.
        try:
            script_path = os.path.join(current_app.root_path, 'freshworks.py')

            # Execute the script with the same Python interpreter; capture output for logging.
            completed = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                check=False
            )

            # Log stdout / stderr for auditing & troubleshooting.
            if completed.stdout:
                current_app.logger.info("freshworks.py stdout:\n%s", completed.stdout.strip())
            if completed.stderr:
                current_app.logger.warning("freshworks.py stderr:\n%s", completed.stderr.strip())

            # Extract how many tickets were added today (look for the ✅ Added … line)
            added_count = 0
            m = re.search(r"Added\s+(\d+)\s+new ticket", completed.stdout or "")
            if m:
                added_count = int(m.group(1))
            
            current_app.logger.info(
                "freshworks.py finished with return code %s – %s new tickets", completed.returncode, added_count
            )

            # Sync refreshed data to database
            db_manager = get_patterson_db_manager()
            if db_manager:
                # Sync the new file data to database
                sync_success = db_manager.sync_file_data_to_db()
                
                # Update persistent timer so countdown restarts (3-hour window)
                try:
                    timer_file = os.path.join(current_app.root_path, 'Freshworks', 'persistent_timer.txt')
                    os.makedirs(os.path.dirname(timer_file), exist_ok=True)
                    with open(timer_file, 'w') as tf:
                        tf.write(datetime.now().isoformat())
                except Exception as timer_err:
                    current_app.logger.warning("Failed to update persistent timer: %s", timer_err)
                
                # Get updated ticket count
                all_db_tickets = db_manager.get_all_tickets()
                total_tickets = len(all_db_tickets)
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully pulled {added_count} tickets from Freshworks and synced to database',
                    'tickets_pulled': added_count,
                    'total_tickets_in_db': total_tickets,
                    'sync_success': sync_success,
                    'timer_updated': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f'Successfully pulled {added_count} tickets from Freshworks (database sync not available)',
                    'tickets_pulled': added_count,
                    'database_sync': False,
                    'timer_updated': datetime.now().isoformat()
                })
                
        except Exception as e:
            current_app.logger.error("freshworks.py script not found at %s", script_path)
            return jsonify({
                'success': False,
                'error': 'Freshworks script not available'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error in manual API pull: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to pull data from Freshworks API: {str(e)}'
        }), 500

@bp.route('/api/tickets/<int:ticket_id>/admin-update', methods=['PUT'])
@login_required
def admin_update_ticket(ticket_id):
    """Admin update ticket with full field access (admin only)."""
    try:
        if current_user.role == 'user':
            return jsonify({
                'success': False,
                'error': 'Access denied for user role'
            }), 403
        
        data = request.get_json()
        
        # Get database manager
        db_manager = get_patterson_db_manager()
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database manager not initialized'
            }), 500
        
        # Update the ticket with admin privileges
        updated_ticket = db_manager.admin_update_ticket(ticket_id, data, current_user.id)
        
        if updated_ticket:
            return jsonify({
                'success': True,
                'message': 'Ticket updated successfully with admin privileges',
                'ticket': updated_ticket
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ticket not found or could not be updated'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error in admin ticket update: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 

# -----------------------------------------------------------------------------
# Helper – extract "Assigned by" display name from ticket notes
# -----------------------------------------------------------------------------


def _extract_assigned_by_display(ticket):
    """Return display name (``First L.``) from *Assigned by:* footer in notes.

    Searches ticket["notes"] (list or JSON-encoded str) for a pattern like::

        Assigned by: Anthony Risker | anthony.risker@pacden.com

    If such a line is found the function returns ``"Anthony R."``. Otherwise
    ``None`` is returned so that the caller can fall back to other sources.
    """

    import re
    import json

    notes = ticket.get("notes", [])

    # Normalise *notes* to a list of strings
    if isinstance(notes, str):
        try:
            notes = json.loads(notes)
        except Exception:
            notes = [notes]

    if not isinstance(notes, list):
        notes = [str(notes)]

    for note in notes:
        if not isinstance(note, str):
            continue
        # First attempt: explicit "Tech:" field (oft. shows actual technician)
        m = re.search(r"Tech\s*:\s*([^|\n]+)", note, re.IGNORECASE)
        if not m:
            # Second attempt: "Assigned by:" footer
            m = re.search(r"Assigned by\s*:\s*([^|\n]+)\s*(?:\||$)", note, re.IGNORECASE)
        if not m:
            # Third attempt: ADAPT phrasing
            m = re.search(r"created\s+through\s+ADAPT\s+by\s+([^|\n]+)", note, re.IGNORECASE)
        if m:
            full_name = m.group(1).strip()
            # Remove any trailing role / commas  e.g. "Anthony Risker. Jr"
            full_name = re.split(r"[|,]", full_name)[0].strip()

            parts = full_name.split()
            if not parts:
                return None
            if len(parts) == 1:
                return parts[0]  # Single-word name
            first, last = parts[0], parts[-1].rstrip('.')
            return f"{first} {last[0]}."

    return None

@bp.route('/api/run-initializer', methods=['POST'])
@login_required
def run_initializer():
    """Run the Freshworks database initializer script and return its output."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    try:
        script_path = os.path.join(current_app.root_path, 'Freshworks', 'initializer.py')
        if not os.path.exists(script_path):
            return jsonify({'success': False, 'error': f'Script not found: {script_path}'}), 404
        # Run the script as a subprocess
        completed = subprocess.run(
            ['python', script_path],
            capture_output=True,
            text=True,
            check=False
        )
        output = completed.stdout + (('\n' + completed.stderr) if completed.stderr else '')
        return jsonify({'success': completed.returncode == 0, 'output': output, 'returncode': completed.returncode})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500