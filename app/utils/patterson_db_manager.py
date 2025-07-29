import json
import os
import glob
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import PattersonTicket, PattersonCalendarEvent, UserMapping, User
from app.utils.patterson_file_manager import get_patterson_file_manager
from app.config import Config
from sqlalchemy import create_engine, text
from pathlib import Path
import re

class PattersonDBManager:
    """Database manager for Patterson tickets using dedicated Freshworks database."""
    
    def __init__(self, app=None):
        self.app = app
        self.db_path = Config.FRESHWORKS_DB
        self.engine = None
        self._init_database()
    
    def _init_database(self):
        """Initialize the dedicated Freshworks database."""
        try:
            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # Create SQLite engine for the dedicated database
            self.engine = create_engine(f'sqlite:///{self.db_path}')
            
            # Create tables if they don't exist
            self._create_tables()
            
            if self.app:
                self.app.logger.info(f"Freshworks database initialized at {self.db_path}")
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error initializing Freshworks database: {str(e)}")
            raise
    
    def _create_tables(self):
        """Create tables in the dedicated Freshworks database."""
        try:
            with self.engine.connect() as conn:
                # Create PattersonTicket table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS patterson_tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        freshworks_id TEXT UNIQUE,
                        ticket_number TEXT NOT NULL,
                        title TEXT,
                        office_name TEXT,
                        technician TEXT,
                        technician_id TEXT,
                        description TEXT,
                        priority TEXT,
                        urgency TEXT,
                        status TEXT,
                        scheduled_date DATE,
                        scheduled_time TEXT,
                        estimated_duration TEXT,
                        stage TEXT,
                        category TEXT,
                        source TEXT,
                        notes TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        created_by INTEGER,
                        updated_by INTEGER
                    )
                """))
                
                # Create PattersonCalendarEvent table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS patterson_calendar_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        office TEXT,
                        technician_id INTEGER,
                        technician_name TEXT,
                        event_date DATE NOT NULL,
                        event_time TEXT,
                        duration TEXT,
                        priority TEXT,
                        urgency TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        created_by INTEGER,
                        updated_by INTEGER
                    )
                """))
                
                conn.commit()
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error creating tables: {str(e)}")
            raise
    
    def sync_file_data_to_db(self):
        """Sync data from file system to database, preserving existing database records."""
        try:
            # Get tickets from file manager
            file_manager = get_patterson_file_manager()
            if not file_manager:
                if self.app:
                    self.app.logger.error("Patterson file manager not initialized")
                return False
            
            file_tickets = file_manager.get_tickets()
            if not file_tickets:
                if self.app:
                    self.app.logger.warning("No tickets found in file system")
                return True
            
            # Convert to database format
            db_tickets = self._convert_file_tickets_to_db_format(file_tickets)
            
            # Sync each ticket
            synced_count = 0
            for ticket_data in db_tickets:
                if self._sync_ticket_to_db(ticket_data):
                    synced_count += 1
            
            if self.app:
                self.app.logger.info(f"Synced {synced_count} tickets to Freshworks database")
            
            return True
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error syncing file data to database: {str(e)}")
            return False
    
    def import_all_dated_files(self):
        """Import all dated .txt files from the Freshworks directory into the database."""
        try:
            # Get the Freshworks directory
            freshworks_dir = os.path.join(self.app.root_path, "Freshworks")
            if not os.path.exists(freshworks_dir):
                if self.app:
                    self.app.logger.error(f"Freshworks directory not found: {freshworks_dir}")
                return 0
            
            # Find all .txt files with date patterns (YYYY-MM-DD.txt)
            import re as _re
            date_files = []
            date_pattern = _re.compile(r'(\d{4}-\d{2}-\d{2})')  # Captures the YYYY-MM-DD part

            for filename in os.listdir(freshworks_dir):
                if not filename.lower().endswith('.txt'):
                    continue

                m = date_pattern.search(filename)
                if not m:
                    continue  # Skip files without any date component

                # Validate date string extracted
                try:
                    datetime.strptime(m.group(1), '%Y-%m-%d')
                    date_files.append(filename)
                except ValueError:
                    continue  # Date component wasn't valid (should rarely happen)
            
            if self.app:
                self.app.logger.info(f"Found {len(date_files)} dated files to import: {date_files}")
            
            total_imported = 0
            
            for filename in sorted(date_files):  # Process in chronological order
                file_path = os.path.join(freshworks_dir, filename)
                imported_count = self.import_file_to_db(file_path)
                total_imported += imported_count
                
                if self.app:
                    self.app.logger.info(f"Imported {imported_count} tickets from {filename}")
            
            if self.app:
                self.app.logger.info(f"Total tickets imported from all dated files: {total_imported}")
            
            return total_imported
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error importing dated files: {str(e)}")
            return 0
    
    def import_file_to_db(self, file_path):
        """Import a specific .txt file into the database."""
        try:
            # Parse the specific file directly
            from app.utils.patterson_file_manager import PattersonFileManager
            
            file_manager = PattersonFileManager(self.app)
            file_tickets = file_manager.parse_txt_file(file_path)
            
            if not file_tickets:
                if self.app:
                    self.app.logger.info(f"No tickets found in {os.path.basename(file_path)}")
                return 0
            
            # Convert to database format
            db_tickets = self._convert_file_tickets_to_db_format(file_tickets, file_path)
            
            # Import each ticket
            imported_count = 0
            for ticket_data in db_tickets:
                if self._sync_ticket_to_db(ticket_data):
                    imported_count += 1
            
            if self.app:
                self.app.logger.info(f"Imported {imported_count} tickets from {os.path.basename(file_path)}")
            
            return imported_count
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error importing file {file_path}: {str(e)}")
            return 0
    
    def clear_all_tickets(self):
        """Remove ALL tickets from the database (use with caution)."""
        try:
            with self.engine.connect() as conn:
                # Clear all calendar events first (due to foreign key constraints)
                result = conn.execute(text("DELETE FROM patterson_calendar_events"))
                events_cleared = result.rowcount
                
                # Clear all tickets
                result = conn.execute(text("DELETE FROM patterson_tickets"))
                tickets_cleared = result.rowcount
                
                conn.commit()
                
                if self.app:
                    self.app.logger.info(f"Cleared ALL {tickets_cleared} tickets and {events_cleared} calendar events from Freshworks database")
                
                return tickets_cleared, events_cleared
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error clearing all tickets: {str(e)}")
            return 0, 0
    
    def clear_test_tickets(self):
        """Remove test tickets from the database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM patterson_tickets 
                    WHERE ticket_number LIKE '%test%' 
                    OR description LIKE '%test%' 
                    OR ticket_number LIKE '%TEST%' 
                    OR ticket_number LIKE '%LOCAL%'
                """))
                count = result.rowcount
                conn.commit()
                
                if self.app:
                    self.app.logger.info(f"Removed {count} test tickets from Freshworks database")
                
                return count
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error clearing test tickets: {str(e)}")
            return 0
    
    def _convert_file_tickets_to_db_format(self, file_tickets, file_path=None):
        """Convert file tickets to database format."""
        db_tickets = []
        
        # Extract year from file path if provided
        file_year = None
        if file_path:
            import re
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(file_path))
            if match:
                file_year = int(match.group(1))
        
        for ticket in file_tickets:
            # Extract ticket number from ID
            ticket_id = ticket.get('id', 'UNKNOWN')
            ticket_number = f"INC-{ticket_id}"
            
            # -------------------------------------------------------------
            # Resolve technician display name
            # -------------------------------------------------------------
            technician_id = ticket.get('responder_id')
            technician_name = None
            
            # 1) Try to parse from notes (Assigned by / Tech fields)
            notes = ticket.get('notes', [])
            if isinstance(notes, str):
                try:
                    import json as _json
                    notes = _json.loads(notes)
                except Exception:
                    notes = [notes]
            if not isinstance(notes, list):
                notes = [str(notes)]
            import re as _re
            for n in notes:
                if not isinstance(n, str):
                    continue
                m = _re.search(r"Tech\s*:\s*([^|\n]+)", n, _re.IGNORECASE)
                if not m:
                    m = _re.search(r"Assigned by\s*:\s*([^|\n]+)", n, _re.IGNORECASE)
                if m:
                    full = m.group(1).strip()
                    parts = full.split()
                    if parts:
                        technician_name = parts[0] if len(parts)==1 else f"{parts[0]} {parts[-1][0]}."
                    break
            
            # 2) Fallback to user-mapping table
            if technician_name is None:
                technician_name = self._get_technician_name(technician_id)
            
            # Parse notes
            notes = ticket.get('notes', [])
            notes_json = json.dumps(notes) if notes else None
            
            # Get the full title from Ticket-Title field (no processing)
            subject = ticket.get('subject') or ticket.get('title', '')
            # Use the full title without any processing - don't cut off before pipe
            clean_title = subject if subject else "Untitled Ticket"
            
            # Extract date from subject
            scheduled_date = self._extract_date_from_subject(subject, default_year=file_year)
            
            # Set office to Unknown Office by default (no extraction)
            office_name = 'Unknown Office'
            
            # Determine stage based on whether date was found
            if scheduled_date:
                stage = 'scheduled'
            else:
                stage = 'in_progress'
            
            # Get priority from status
            status = ticket.get('status', 2)
            priority = self._get_priority_from_status(status)
            
            # Get source
            source = 'Freshworks'
            
            db_ticket = {
                'freshworks_id': str(ticket_id),  # Add the missing freshworks_id
                'ticket_number': ticket_number,
                'title': clean_title,
                'office_name': office_name,  # Always Unknown Office
                'technician': technician_name,
                'technician_id': technician_id,
                'description': ticket.get('description', ''),
                'priority': priority,
                'urgency': priority,  # Use same as priority for now
                'status': self._map_status(status),
                'scheduled_date': scheduled_date.isoformat() if scheduled_date else None,
                'scheduled_time': '09:00',  # Default time
                'estimated_duration': '2 hours',  # Default duration
                'stage': stage,
                'category': 'IT',  # Default category
                'source': source,
                'notes': notes_json,
                'created_at': ticket.get('created_at'),
                'updated_at': ticket.get('created_at')  # Use created_at as updated_at initially
            }
            
            db_tickets.append(db_ticket)
        
        return db_tickets
    
    def _sync_ticket_to_db(self, ticket_data):
        """Sync a single ticket to database, updating if exists."""
        try:
            with self.engine.connect() as conn:
                # Check if ticket already exists
                existing_ticket = None  # Initialize to None
                if ticket_data.get('freshworks_id'):
                    result = conn.execute(
                        text("SELECT id FROM patterson_tickets WHERE freshworks_id = :freshworks_id"),
                        {"freshworks_id": ticket_data['freshworks_id']}
                    )
                    existing_ticket = result.fetchone()
                
                if existing_ticket:
                    # Update existing ticket
                    conn.execute(text("""
                        UPDATE patterson_tickets SET
                            ticket_number = :ticket_number,
                            title = :title,
                            office_name = :office_name,
                            technician = :technician,
                            technician_id = :technician_id,
                            description = :description,
                            priority = :priority,
                            urgency = :urgency,
                            status = :status,
                            scheduled_date = :scheduled_date,
                            scheduled_time = :scheduled_time,
                            estimated_duration = :estimated_duration,
                            stage = :stage,
                            category = :category,
                            source = :source,
                            notes = :notes,
                            updated_at = :updated_at
                        WHERE freshworks_id = :freshworks_id
                    """), {
                        **ticket_data,
                        "updated_at": datetime.utcnow()
                    })
                    
                    conn.commit()
                    
                    # Create calendar event if ticket has a scheduled date
                    if ticket_data.get('scheduled_date'):
                        self.create_calendar_event_from_ticket(ticket_data)
                    
                    return True
                else:
                    # Create new ticket
                    conn.execute(text("""
                        INSERT INTO patterson_tickets (
                            freshworks_id, ticket_number, title, office_name, technician, 
                            technician_id, description, priority, urgency, status, 
                            scheduled_date, scheduled_time, estimated_duration, stage, 
                            category, source, notes, created_at, updated_at
                        ) VALUES (
                            :freshworks_id, :ticket_number, :title, :office_name, :technician,
                            :technician_id, :description, :priority, :urgency, :status,
                            :scheduled_date, :scheduled_time, :estimated_duration, :stage,
                            :category, :source, :notes, :created_at, :updated_at
                        )
                    """), {
                        **ticket_data,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    })
                    
                    conn.commit()
                    
                    # Create calendar event if ticket has a scheduled date
                    if ticket_data.get('scheduled_date'):
                        self.create_calendar_event_from_ticket(ticket_data)
                    
                    return True
                    
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error syncing ticket to database: {str(e)}")
            return False
    
    def get_all_tickets(self):
        """Get all tickets from database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM patterson_tickets 
                    ORDER BY created_at DESC
                """))
                
                tickets = []
                for row in result.fetchall():
                    ticket_dict = dict(row._mapping)
                    # Convert date objects to strings for JSON serialization
                    if ticket_dict.get('scheduled_date'):
                        ticket_dict['scheduled_date'] = str(ticket_dict['scheduled_date'])
                    if ticket_dict.get('created_at'):
                        ticket_dict['created_at'] = str(ticket_dict['created_at'])
                    if ticket_dict.get('updated_at'):
                        ticket_dict['updated_at'] = str(ticket_dict['updated_at'])
                    tickets.append(ticket_dict)
                
                return tickets
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting tickets from database: {str(e)}")
            return []
    
    def get_ticket_by_id(self, ticket_id):
        """Get a specific ticket by ID."""
        try:
            ticket = PattersonTicket.query.get(ticket_id)
            return ticket.to_dict() if ticket else None
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
            return None
    
    def get_ticket_by_number(self, ticket_number):
        """Get a ticket by ticket number."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM patterson_tickets WHERE ticket_number = :ticket_number"),
                    {"ticket_number": ticket_number}
                )
                row = result.fetchone()
                if row:
                    ticket_dict = dict(row._mapping)
                    # Convert date objects to strings for JSON serialization
                    if ticket_dict.get('scheduled_date'):
                        ticket_dict['scheduled_date'] = str(ticket_dict['scheduled_date'])
                    if ticket_dict.get('created_at'):
                        ticket_dict['created_at'] = str(ticket_dict['created_at'])
                    if ticket_dict.get('updated_at'):
                        ticket_dict['updated_at'] = str(ticket_dict['updated_at'])
                    return ticket_dict
                return None
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting ticket by number {ticket_number}: {str(e)}")
            return None
    
    def insert_ticket(self, ticket_data):
        """Insert a new ticket into the database."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO patterson_tickets (
                        freshworks_id, ticket_number, title, office_name, technician, 
                        technician_id, description, priority, urgency, status, 
                        scheduled_date, scheduled_time, estimated_duration, stage, 
                        category, source, notes, created_at, updated_at
                    ) VALUES (
                        :freshworks_id, :ticket_number, :title, :office_name, :technician,
                        :technician_id, :description, :priority, :urgency, :status,
                        :scheduled_date, :scheduled_time, :estimated_duration, :stage,
                        :category, :source, :notes, :created_at, :updated_at
                    )
                """), {
                    **ticket_data,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                
                conn.commit()
                return True
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error inserting ticket: {str(e)}")
            return False
    
    def create_ticket(self, ticket_data, user_id):
        """Create a new ticket in database."""
        try:
            # Generate ticket number if not provided
            if not ticket_data.get('ticket_number'):
                ticket_data['ticket_number'] = f"LOCAL-{int(datetime.utcnow().timestamp())}"
            
            # Set source to local
            ticket_data['source'] = 'local'
            ticket_data['created_by'] = user_id
            ticket_data['updated_by'] = user_id
            
            # Parse scheduled date
            if ticket_data.get('scheduled_date'):
                if isinstance(ticket_data['scheduled_date'], str):
                    ticket_data['scheduled_date'] = datetime.strptime(ticket_data['scheduled_date'], '%Y-%m-%d').date()
            
            new_ticket = PattersonTicket(**ticket_data)
            db.session.add(new_ticket)
            db.session.commit()
            
            return new_ticket.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error creating ticket: {str(e)}")
            raise
    
    def update_ticket(self, ticket_id, ticket_data, user_id):
        """Update an existing ticket."""
        try:
            ticket = PattersonTicket.query.get(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")
            
            # Update fields
            for key, value in ticket_data.items():
                if hasattr(ticket, key) and key not in ['id', 'created_at', 'created_by']:
                    if key == 'scheduled_date' and isinstance(value, str):
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    setattr(ticket, key, value)
            
            ticket.updated_by = user_id
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            
            return ticket.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
            raise
    
    def update_ticket_stage(self, ticket_id, stage, user_id):
        """Update ticket stage."""
        try:
            ticket = PattersonTicket.query.get(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")
            
            ticket.stage = stage
            ticket.updated_by = user_id
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            
            return ticket.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error updating ticket stage {ticket_id}: {str(e)}")
            raise
    
    def update_ticket_urgency(self, ticket_id, urgency, user_id):
        """Update ticket urgency."""
        try:
            ticket = PattersonTicket.query.get(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")
            
            ticket.urgency = urgency
            ticket.updated_by = user_id
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            
            return ticket.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error updating ticket urgency {ticket_id}: {str(e)}")
            raise
    
    def admin_update_ticket(self, ticket_id, ticket_data, user_id):
        """Admin update ticket with full field access (admin only)."""
        try:
            ticket = PattersonTicket.query.get(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")
            
            # Admin can update any field except id, created_at, created_by
            for key, value in ticket_data.items():
                if hasattr(ticket, key) and key not in ['id', 'created_at', 'created_by']:
                    if key == 'scheduled_date' and isinstance(value, str):
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    setattr(ticket, key, value)
            
            ticket.updated_by = user_id
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            
            return ticket.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error in admin update ticket {ticket_id}: {str(e)}")
            raise
    
    def delete_ticket(self, ticket_id):
        """Delete a ticket."""
        try:
            ticket = PattersonTicket.query.get(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")
            
            db.session.delete(ticket)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error deleting ticket {ticket_id}: {str(e)}")
            raise
    
    def get_calendar_events(self):
        """Get all calendar events from database."""
        try:
            events = PattersonCalendarEvent.query.order_by(PattersonCalendarEvent.event_date.desc()).all()
            return [event.to_dict() for event in events]
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting calendar events: {str(e)}")
            return []
    
    def create_calendar_event(self, event_data, user_id):
        """Create a new calendar event."""
        try:
            # Parse event date
            if event_data.get('event_date'):
                if isinstance(event_data['event_date'], str):
                    event_data['event_date'] = datetime.strptime(event_data['event_date'], '%Y-%m-%d').date()
            
            event_data['created_by'] = user_id
            
            new_event = PattersonCalendarEvent(**event_data)
            db.session.add(new_event)
            db.session.commit()
            
            return new_event.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error creating calendar event: {str(e)}")
            raise
    
    def update_calendar_event(self, event_id, event_data, user_id):
        """Update a calendar event."""
        try:
            event = PattersonCalendarEvent.query.get(event_id)
            if not event:
                raise ValueError("Calendar event not found")
            
            # Update fields
            for key, value in event_data.items():
                if hasattr(event, key) and key not in ['id', 'created_at', 'created_by']:
                    if key == 'event_date' and isinstance(value, str):
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    setattr(event, key, value)
            
            event.updated_at = datetime.utcnow()
            db.session.commit()
            
            return event.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error updating calendar event {event_id}: {str(e)}")
            raise
    
    def delete_calendar_event(self, event_id):
        """Delete a calendar event."""
        try:
            event = PattersonCalendarEvent.query.get(event_id)
            if not event:
                raise ValueError("Calendar event not found")
            
            db.session.delete(event)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error deleting calendar event {event_id}: {str(e)}")
            raise
    
    def get_ticket_stats(self):
        """Get ticket statistics."""
        try:
            total = PattersonTicket.query.count()
            in_progress = PattersonTicket.query.filter_by(stage='in_progress').count()
            scheduled = PattersonTicket.query.filter_by(stage='scheduled').count()
            completed = PattersonTicket.query.filter_by(stage='completed').count()
            
            return {
                'total': total,
                'in_progress': in_progress,
                'scheduled': scheduled,
                'completed': completed
            }
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting ticket stats: {str(e)}")
            return {'total': 0, 'in_progress': 0, 'scheduled': 0, 'completed': 0}
    
    def create_calendar_event_from_ticket(self, ticket_data):
        """Create a calendar event from ticket data if it has a scheduled date."""
        try:
            if not ticket_data.get('scheduled_date'):
                return None
            
            # Check if calendar event already exists for this ticket
            existing_event = PattersonCalendarEvent.query.filter_by(
                ticket_id=ticket_data.get('id')
            ).first()
            
            if existing_event:
                return existing_event.to_dict()
            
            # Ensure event_date is a proper Python date object
            from datetime import datetime as _dt
            event_date = ticket_data.get('scheduled_date')
            if isinstance(event_date, str):
                try:
                    event_date = _dt.strptime(event_date, '%Y-%m-%d').date()
                except Exception:
                    event_date = None

            # Create new calendar event
            event_data = {
                'title': ticket_data.get('title', f"{ticket_data.get('ticket_number', 'TICKET')} - {ticket_data.get('office_name', 'Unknown Office')}"),
                'event_date': event_date,
                'event_time': ticket_data.get('scheduled_time', '09:00'),
                'description': ticket_data.get('description', ''),
                'priority': ticket_data.get('priority', 'Medium'),
                'ticket_id': ticket_data.get('id'),
                'created_by': 1  # Default admin user
            }
            
            new_event = PattersonCalendarEvent(**event_data)
            db.session.add(new_event)
            db.session.commit()
            
            if self.app:
                self.app.logger.info(f"Created calendar event for ticket {ticket_data.get('ticket_number')}")
            
            return new_event.to_dict()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error creating calendar event from ticket: {str(e)}")
            return None
    
    # Helper methods
    def _get_technician_name(self, technician_id):
        """Return human-readable technician name.

        Priority order:
        1. Active record in *UserMapping* table (admin-maintained mapping).
        2. Generic fallback "Technician <id>" when the mapping is unknown
           or *technician_id* is missing/None.
        """
        if not technician_id:
            return 'Unassigned'

        try:
            mapping = UserMapping.query.filter_by(
                freshworks_id=str(technician_id),
                is_active=True
            ).first()
            if mapping and mapping.name:
                return mapping.name
        except Exception:
            # SQLAlchemy might not be fully configured outside app context –
            # we swallow the error and fall back to the default string.
            pass

        return f"Technician {technician_id}"
    
    def _get_priority_from_status(self, status):
        """Convert status to priority."""
        priority_map = {
            1: 'Low',
            2: 'Medium', 
            3: 'High',
            4: 'Urgent'
        }
        return priority_map.get(status, 'Medium')
    
    def _extract_date_from_subject(self, subject, default_year=None):
        """Extract date from ticket subject, using default_year if year is missing."""
        if not subject:
            return None
        import re
        from datetime import datetime
        
        # Pattern 1: Extract from "6/19 - 12-4pm | ..." format
        pipe_date_pattern = r'^(\d{1,2})/(\d{1,2})\s*-\s*\d{1,2}-\d{1,2}[ap]m\s*\|'
        match = re.search(pipe_date_pattern, subject.strip(), re.IGNORECASE)
        if match:
            month, day = match.groups()
            year = default_year if default_year else datetime.now().year
            try:
                return datetime.strptime(f"{year}-{int(month):02d}-{int(day):02d}", '%Y-%m-%d').date()
            except:
                pass
        
        # Pattern 2: Extract from "6/25 8am-12pm | ..." format
        pipe_date_pattern2 = r'^(\d{1,2})/(\d{1,2})\s*\d{1,2}[ap]m-\d{1,2}[ap]m\s*\|'
        match = re.search(pipe_date_pattern2, subject.strip(), re.IGNORECASE)
        if match:
            month, day = match.groups()
            year = default_year if default_year else datetime.now().year
            try:
                return datetime.strptime(f"{year}-{int(month):02d}-{int(day):02d}", '%Y-%m-%d').date()
            except:
                pass
        
        # Pattern 3: Extract from "6/19/2025 | ..." format
        full_date_pattern = r'^(\d{1,2})/(\d{1,2})/(\d{4})'
        match = re.search(full_date_pattern, subject.strip())
        if match:
            month, day, year = match.groups()
            try:
                return datetime.strptime(f"{year}-{int(month):02d}-{int(day):02d}", '%Y-%m-%d').date()
            except:
                pass
        
        # Pattern 4: Extract from "6/19 - ..." or "6/19 ..." format (no year)
        short_date_pattern = r'^(\d{1,2})/(\d{1,2})'
        match = re.search(short_date_pattern, subject.strip())
        if match:
            month, day = match.groups()
            year = default_year if default_year else datetime.now().year
            try:
                return datetime.strptime(f"{year}-{int(month):02d}-{int(day):02d}", '%Y-%m-%d').date()
            except:
                pass
        
        # Pattern 5: Standard date patterns (existing logic)
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}/\d{2}/\d{4})',  # MM/DD/YYYY
            r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
        ]
        for pattern in date_patterns:
            match = re.search(pattern, subject)
            if match:
                date_str = match.group(1)
                try:
                    if '-' in date_str and len(date_str.split('-')[0]) == 4:
                        return datetime.strptime(date_str, '%Y-%m-%d').date()
                    elif '/' in date_str:
                        return datetime.strptime(date_str, '%m/%d/%Y').date()
                    else:
                        return datetime.strptime(date_str, '%m-%d-%Y').date()
                except:
                    continue
        return None
    
    def _map_priority(self, priority_id):
        """Map Freshworks priority ID to string."""
        priority_map = {
            1: 'Low',
            2: 'Medium',
            3: 'High',
            4: 'Urgent'
        }
        return priority_map.get(priority_id, 'Medium')
    
    def _map_status(self, status_id):
        """Map Freshworks status ID to string."""
        status_map = {
            2: 'Open',
            3: 'Pending',
            4: 'Resolved',
            5: 'Closed'
        }
        return status_map.get(status_id, 'Open')

    def import_from_freshworks_files(self):
        """Import tickets from Freshworks text files."""
        try:
            if not self.app:
                return 0
            
            freshworks_dir = Path(self.app.root_path) / 'Freshworks'
            if not freshworks_dir.exists():
                self.app.logger.warning("Freshworks directory not found")
                return 0
            
            total_imported = 0
            
            # Get all .txt files in the Freshworks directory
            txt_files = list(freshworks_dir.glob('*.txt'))
            
            for file_path in txt_files:
                try:
                    # Skip files that don't match the date pattern
                    if not re.search(r'\d{4}-\d{2}-\d{2}', file_path.name):
                        continue
                    
                    self.app.logger.info(f"Processing file: {file_path.name}")
                    
                    # Parse tickets from file
                    file_manager = get_patterson_file_manager()
                    file_tickets = file_manager.parse_txt_file(file_path)
                    
                    if not file_tickets:
                        self.app.logger.warning(f"No tickets found in {file_path.name}")
                        continue
                    
                    # Convert to database format
                    db_tickets = self._convert_file_tickets_to_db_format(file_tickets, file_path)
                    
                    # Import each ticket
                    for db_ticket in db_tickets:
                        try:
                            # Check if ticket already exists
                            existing = self.get_ticket_by_number(db_ticket['ticket_number'])
                            if existing:
                                self.app.logger.debug(f"Ticket {db_ticket['ticket_number']} already exists, skipping")
                                continue
                            
                            # Insert new ticket
                            self.insert_ticket(db_ticket)
                            total_imported += 1
                            
                        except Exception as e:
                            self.app.logger.error(f"Error importing ticket {db_ticket.get('ticket_number', 'unknown')}: {str(e)}")
                            continue
                    
                except Exception as e:
                    self.app.logger.error(f"Error processing file {file_path.name}: {str(e)}")
                    continue
            
            self.app.logger.info(f"Import completed. Total tickets imported: {total_imported}")
            return total_imported
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error importing from Freshworks files: {str(e)}")
            return 0

    def import_all_historical_files(self):
        """Backward-compatibility alias for import_all_dated_files().

        Some legacy routes (e.g. /api/initialize-database) still invoke
        *import_all_historical_files()* even though the canonical method was
        renamed to *import_all_dated_files* during the refactor.  To avoid
        AttributeError exceptions at runtime we provide this thin wrapper that
        simply delegates to the current implementation.
        """
        return self.import_all_dated_files()

# Global instance
_patterson_db_manager = None

def init_patterson_db_manager(app):
    """Initialize the Patterson database manager."""
    global _patterson_db_manager
    _patterson_db_manager = PattersonDBManager(app)
    return _patterson_db_manager

def get_patterson_db_manager():
    """Get the global Patterson database manager instance."""
    return _patterson_db_manager 