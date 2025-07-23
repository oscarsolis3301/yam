#!/usr/bin/env python3
"""
Freshworks Database Manager
Handles all dated txt files and provides proper date parsing and status management.
"""

import os
import sqlite3
import json
import re
from datetime import datetime, date
from pathlib import Path
from sqlalchemy import create_engine, text
import logging

class FreshworksDBManager:
    def __init__(self, app=None):
        self.app = app
        self.db_path = os.path.join(app.root_path, 'db', 'freshworks.db') if app else 'app/db/freshworks.db'
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        self._init_database()
        
    def _init_database(self):
        """Initialize the database with proper tables."""
        try:
            with self.engine.connect() as conn:
                # Create FreshworksTicket table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS freshworks_tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        freshworks_id TEXT UNIQUE,
                        ticket_number TEXT NOT NULL,
                        title TEXT,
                        original_title TEXT,
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
                        file_source TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        created_by INTEGER,
                        updated_by INTEGER
                    )
                """))
                
                # Create index for better performance
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_freshworks_tickets_number 
                    ON freshworks_tickets(ticket_number)
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_freshworks_tickets_date 
                    ON freshworks_tickets(scheduled_date)
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_freshworks_tickets_stage 
                    ON freshworks_tickets(stage)
                """))
                
                conn.commit()
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error creating tables: {str(e)}")
            raise
    
    def import_all_dated_files(self):
        """Import all dated txt files into the database."""
        try:
            freshworks_dir = Path(self.app.root_path) / 'Freshworks' if self.app else Path('app/Freshworks')
            if not freshworks_dir.exists():
                if self.app:
                    self.app.logger.error(f"Freshworks directory not found: {freshworks_dir}")
                return 0
            
            # Find all .txt files with date patterns (YYYY-MM-DD.txt)
            date_files = []
            for filename in os.listdir(freshworks_dir):
                if filename.endswith('.txt') and len(filename) == 14:  # YYYY-MM-DD.txt = 14 chars
                    try:
                        # Validate it's a date format
                        date_str = filename.replace('.txt', '')
                        datetime.strptime(date_str, '%Y-%m-%d')
                        date_files.append(filename)
                    except ValueError:
                        continue  # Not a date file
            
            if self.app:
                self.app.logger.info(f"Found {len(date_files)} historical date files: {date_files}")
            
            total_imported = 0
            
            for filename in sorted(date_files):  # Process in chronological order
                file_path = freshworks_dir / filename
                imported_count = self.import_file_to_db(file_path)
                total_imported += imported_count
                
                if self.app:
                    self.app.logger.info(f"Imported {imported_count} tickets from {filename}")
            
            return total_imported
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error importing historical files: {str(e)}")
            return 0
    
    def import_file_to_db(self, file_path):
        """Import a specific .txt file into the database."""
        try:
            # Parse the file
            file_tickets = self._parse_txt_file(file_path)
            
            if not file_tickets:
                if self.app:
                    self.app.logger.info(f"No tickets found in {file_path.name}")
                return 0
            
            # Convert to database format
            db_tickets = self._convert_file_tickets_to_db_format(file_tickets, file_path)
            
            # Import each ticket
            imported_count = 0
            for ticket_data in db_tickets:
                if self._sync_ticket_to_db(ticket_data):
                    imported_count += 1
            
            if self.app:
                self.app.logger.info(f"Imported {imported_count} tickets from {file_path.name}")
            
            return imported_count
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error importing file {file_path}: {str(e)}")
            return 0
    
    def _parse_txt_file(self, file_path):
        """Parse uploaded TXT file and extract ticket data."""
        try:
            tickets = []
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by ticket separators (60 dashes)
            ticket_sections = content.split('-' * 60)
            
            for section in ticket_sections:
                if not section.strip():
                    continue
                
                lines = section.strip().split('\n')
                ticket = {}
                in_description = False
                in_notes = False
                current_notes = []
                description_parsed = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('Ticket #'):
                        ticket['id'] = int(line.split('#')[1])
                    elif line.startswith('Ticket-Title'):
                        # Handle Ticket-Title format: "Ticket-Title       : actual title"
                        if ':' in line:
                            title = line.split(':', 1)[1].strip()
                            ticket['title'] = title
                            ticket['subject'] = title  # Also store as subject for compatibility
                        else:
                            title = line.replace('Ticket-Title', '').strip()
                            if title:
                                ticket['title'] = title
                                ticket['subject'] = title
                    elif line.startswith('Title'):
                        # Fallback for old format - only use if Ticket-Title is not already set
                        if 'title' not in ticket:
                            if ':' in line:
                                title = line.split(':', 1)[1].strip()
                                ticket['title'] = title
                                ticket['subject'] = title
                            else:
                                title = line.replace('Title', '').strip()
                                if title:
                                    ticket['title'] = title
                                    ticket['subject'] = title
                    elif line.startswith('Group ID'):
                        if ':' in line:
                            ticket['group_id'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Assigned To'):
                        if ':' in line:
                            ticket['responder_id'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Created At'):
                        if ':' in line:
                            ticket['created_at'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Status'):
                        if ':' in line:
                            try:
                                ticket['status'] = int(line.split(':', 1)[1].strip())
                            except ValueError:
                                ticket['status'] = 10  # Default status
                    elif line.startswith('Ticket-Description'):
                        # Start collecting description
                        in_description = True
                        ticket['description'] = ''
                        continue
                    elif line.startswith('Notes:'):
                        # Start collecting notes
                        in_description = False
                        in_notes = True
                        current_notes = []
                        continue
                    elif line.startswith('  ['):
                        # This is a note
                        current_notes.append(line.strip())
                    elif in_description and not description_parsed:
                        # This is description content
                        if 'description' not in ticket:
                            ticket['description'] = line
                        else:
                            ticket['description'] += '\n' + line
                    elif in_notes and line.startswith('  '):
                        # Continue collecting notes
                        current_notes.append(line.strip())
                    elif in_notes and not line.startswith('  '):
                        # End of notes section
                        in_notes = False
                        ticket['notes'] = current_notes
                
                if 'id' in ticket:
                    if 'notes' not in ticket:
                        ticket['notes'] = current_notes
                    tickets.append(ticket)
            
            return tickets
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error parsing file {file_path}: {str(e)}")
            return []
    
    def _convert_file_tickets_to_db_format(self, file_tickets, file_path=None):
        """Convert file tickets to database format."""
        db_tickets = []
        
        # Extract year from file path if provided
        file_year = None
        if file_path:
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(file_path))
            if match:
                file_year = int(match.group(1))
        
        for ticket in file_tickets:
            # Extract ticket number from ID
            ticket_id = ticket.get('id', 'UNKNOWN')
            ticket_number = f"INC-{ticket_id}"
            
            # Get technician name
            technician_id = ticket.get('responder_id')
            technician_name = self._get_technician_name(technician_id)
            
            # Parse notes
            notes = ticket.get('notes', [])
            notes_json = json.dumps(notes) if notes else None
            
            # Extract clean title from subject (use full subject for better extraction)
            subject = ticket.get('subject') or ticket.get('title', '')
            clean_title = self._extract_clean_title_from_subject(subject)
            
            # Extract date from subject with proper year handling
            scheduled_date = self._extract_date_from_subject(subject, default_year=file_year)
            
            # Determine stage based on whether date was found
            if scheduled_date:
                stage = 'scheduled'
            else:
                stage = 'in_progress'
            
            # Get description
            description = ticket.get('description', '')
            
            # Get priority from status
            status = ticket.get('status', 2)
            priority = self._get_priority_from_status(status)
            
            # Get source
            source = 'Freshworks'
            
            # Parse created_at date
            created_at = datetime.utcnow()
            if ticket.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(ticket.get('created_at').replace('Z', '+00:00'))
                except:
                    created_at = datetime.utcnow()
            
            db_ticket = {
                'freshworks_id': str(ticket.get('id')),
                'ticket_number': ticket_number,
                'title': clean_title,
                'original_title': subject,  # Keep original for reference
                'office_name': self._extract_office_from_notes(notes) or self._extract_office_from_subject(subject) or 'Unknown Office',
                'technician': technician_name,
                'technician_id': technician_id,
                'description': description,
                'priority': priority,
                'urgency': priority,  # Use same as priority for now
                'status': self._map_status(status),
                'scheduled_date': scheduled_date,
                'scheduled_time': '09:00',  # Default time
                'estimated_duration': '2 hours',  # Default duration
                'stage': stage,
                'category': 'IT',
                'source': source,
                'notes': notes_json,
                'file_source': file_path.name if file_path else None,
                'created_at': created_at,
                'updated_at': created_at
            }
            
            db_tickets.append(db_ticket)
        
        return db_tickets
    
    def _sync_ticket_to_db(self, ticket_data):
        """Sync a ticket to the database."""
        try:
            with self.engine.connect() as conn:
                # Check if ticket already exists
                existing_ticket = None
                if ticket_data.get('freshworks_id'):
                    result = conn.execute(
                        text("SELECT id FROM freshworks_tickets WHERE freshworks_id = :freshworks_id"),
                        {"freshworks_id": ticket_data['freshworks_id']}
                    )
                    existing_ticket = result.fetchone()
                
                if existing_ticket:
                    # Update existing ticket
                    conn.execute(text("""
                        UPDATE freshworks_tickets SET
                            ticket_number = :ticket_number,
                            title = :title,
                            original_title = :original_title,
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
                            file_source = :file_source,
                            updated_at = :updated_at
                        WHERE freshworks_id = :freshworks_id
                    """), {
                        **ticket_data,
                        "updated_at": datetime.utcnow()
                    })
                    
                    conn.commit()
                    return True
                else:
                    # Insert new ticket
                    conn.execute(text("""
                        INSERT INTO freshworks_tickets (
                            freshworks_id, ticket_number, title, original_title, office_name, 
                            technician, technician_id, description, priority, urgency, status, 
                            scheduled_date, scheduled_time, estimated_duration, stage, 
                            category, source, notes, file_source, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """), (
                        ticket_data['freshworks_id'],
                        ticket_data['ticket_number'],
                        ticket_data['title'],
                        ticket_data['original_title'],
                        ticket_data['office_name'],
                        ticket_data['technician'],
                        ticket_data['technician_id'],
                        ticket_data['description'],
                        ticket_data['priority'],
                        ticket_data['urgency'],
                        ticket_data['status'],
                        ticket_data['scheduled_date'],
                        ticket_data['scheduled_time'],
                        ticket_data['estimated_duration'],
                        ticket_data['stage'],
                        ticket_data['category'],
                        ticket_data['source'],
                        ticket_data['notes'],
                        ticket_data['file_source'],
                        ticket_data['created_at'],
                        ticket_data['updated_at']
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error syncing ticket {ticket_data.get('ticket_number', 'unknown')}: {str(e)}")
            return False
    
    def get_all_tickets(self):
        """Get all tickets from the database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM freshworks_tickets 
                    ORDER BY created_at DESC
                """))
                
                tickets = []
                for row in result.fetchall():
                    ticket = dict(row._mapping)
                    
                    # Parse notes JSON
                    if ticket.get('notes'):
                        try:
                            ticket['notes'] = json.loads(ticket['notes'])
                        except:
                            ticket['notes'] = []
                    else:
                        ticket['notes'] = []
                    
                    tickets.append(ticket)
                
                return tickets
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting tickets: {str(e)}")
            return []
    
    def get_tickets_by_stage(self, stage=None):
        """Get tickets filtered by stage."""
        try:
            with self.engine.connect() as conn:
                if stage:
                    result = conn.execute(text("""
                        SELECT * FROM freshworks_tickets 
                        WHERE stage = :stage
                        ORDER BY created_at DESC
                    """), {"stage": stage})
                else:
                    result = conn.execute(text("""
                        SELECT * FROM freshworks_tickets 
                        ORDER BY created_at DESC
                    """))
                
                tickets = []
                for row in result.fetchall():
                    ticket = dict(row._mapping)
                    
                    # Parse notes JSON
                    if ticket.get('notes'):
                        try:
                            ticket['notes'] = json.loads(ticket['notes'])
                        except:
                            ticket['notes'] = []
                    else:
                        ticket['notes'] = []
                    
                    tickets.append(ticket)
                
                return tickets
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting tickets by stage: {str(e)}")
            return []
    
    def get_ticket_stats(self):
        """Get ticket statistics."""
        try:
            with self.engine.connect() as conn:
                # Total tickets
                result = conn.execute(text("SELECT COUNT(*) FROM freshworks_tickets"))
                total = result.fetchone()[0]
                
                # Tickets by stage
                result = conn.execute(text("""
                    SELECT stage, COUNT(*) FROM freshworks_tickets 
                    GROUP BY stage
                """))
                stages = dict(result.fetchall())
                
                # Tickets with scheduled dates
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM freshworks_tickets 
                    WHERE scheduled_date IS NOT NULL
                """))
                scheduled = result.fetchone()[0]
                
                return {
                    'total': total,
                    'scheduled': scheduled,
                    'in_progress': total - scheduled,
                    'stages': stages
                }
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting ticket stats: {str(e)}")
            return {'total': 0, 'scheduled': 0, 'in_progress': 0, 'stages': {}}
    
    def _extract_clean_title_from_subject(self, subject):
        """Extract a clean title from ticket subject, removing date/time prefixes."""
        if not subject:
            return "Untitled Ticket"
        
        # Pattern 1: "6/19 - 12-4pm | Primescan Down" -> "Primescan Down"
        pipe_pattern = r'^.*?\|\s*(.+)$'
        match = re.search(pipe_pattern, subject.strip())
        if match:
            return match.group(1).strip()
        
        # Pattern 2: Remove date/time prefixes
        prefix_patterns = [
            r'^\d{1,2}/\d{1,2}\s*-\s*\d{1,2}:\d{2}[ap]m\s*',  # "6/19 - 12:4pm "
            r'^\d{1,2}/\d{1,2}\s*-\s*\d{1,2}-\d{1,2}[ap]m\s*',  # "6/19 - 12-4pm "
            r'^\d{1,2}/\d{1,2}\s*\d{1,2}[ap]m-\d{1,2}[ap]m\s*',  # "6/25 8am-12pm "
            r'^\d{1,2}/\d{1,2}\s*-\s*',  # "6/19 - "
            r'^\d{1,2}/\d{1,2}\s*',      # "6/19 "
        ]
        
        cleaned_subject = subject.strip()
        for pattern in prefix_patterns:
            cleaned_subject = re.sub(pattern, '', cleaned_subject, flags=re.IGNORECASE)
        
        return cleaned_subject.strip() if cleaned_subject.strip() else "Untitled Ticket"
    
    def _extract_date_from_subject(self, subject, default_year=None):
        """Extract date from ticket subject with proper year handling."""
        if not subject:
            return None
        
        # Pattern 1: Extract from "6/19/2025 | ..." format
        full_date_pattern = r'^(\d{1,2})/(\d{1,2})/(\d{4})'
        match = re.search(full_date_pattern, subject.strip())
        if match:
            month, day, year = match.groups()
            try:
                return datetime.strptime(f"{year}-{int(month):02d}-{int(day):02d}", '%Y-%m-%d').date()
            except:
                pass
        
        # Pattern 2: Extract from "6/19 - ..." or "6/19 ..." format (no year)
        short_date_pattern = r'^(\d{1,2})/(\d{1,2})'
        match = re.search(short_date_pattern, subject.strip())
        if match:
            month, day = match.groups()
            year = default_year if default_year else datetime.now().year
            try:
                return datetime.strptime(f"{year}-{int(month):02d}-{int(day):02d}", '%Y-%m-%d').date()
            except:
                pass
        
        return None
    
    def _extract_office_from_subject(self, subject):
        """Extract office information from ticket subject."""
        if not subject:
            return None
        
        # Look for office patterns in subject
        patterns = [
            r'office\s+(\d+)',  # "office 633"
            r'(\d+)\s*-\s*([A-Z]+)',  # "6 - IRV"
            r'(\d+)\s*-\s*([A-Za-z\s]+)',  # "1015-Aurora 9"
            r'(\d+)\s*-\s*([A-Za-z\s]+)\s*(\d+)',  # "908-Riverview 2"
            r'(\d+)\s*-\s*([A-Za-z\s]+)\s*(\d+)',  # "188-Mountains Edge"
            r'Office\s+(\d+)',  # "Office 633"
            r'(\d+)\s*-\s*([A-Za-z\s]+)\s*Office',  # "188-Mountains Edge Office"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                if len(match.groups()) == 1:
                    return f"Office {match.group(1)}"
                elif len(match.groups()) == 2:
                    return f"{match.group(1)} - {match.group(2).strip()}"
                elif len(match.groups()) == 3:
                    return f"{match.group(1)} - {match.group(2).strip()} {match.group(3)}"
        
        return None
    
    def _extract_office_from_notes(self, notes):
        """Extract office information from ticket notes."""
        if not notes:
            return None
        
        # Convert notes to string for searching
        notes_text = ' '.join(notes) if isinstance(notes, list) else str(notes)
        
        # Look for office patterns in notes
        patterns = [
            r'office\s+(\d+)',  # "office 633"
            r'(\d+)\s*-\s*([A-Z]+)',  # "6 - IRV"
            r'(\d+)\s*-\s*([A-Za-z\s]+)',  # "1015-Aurora 9"
            r'(\d+)\s*-\s*([A-Za-z\s]+)\s*(\d+)',  # "908-Riverview 2"
            r'(\d+)\s*-\s*([A-Za-z\s]+)\s*(\d+)',  # "188-Mountains Edge"
            r'Office\s+(\d+)',  # "Office 633"
            r'(\d+)\s*-\s*([A-Za-z\s]+)\s*Office',  # "188-Mountains Edge Office"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, notes_text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 1:
                    return f"Office {match.group(1)}"
                elif len(match.groups()) == 2:
                    return f"{match.group(1)} - {match.group(2).strip()}"
                elif len(match.groups()) == 3:
                    return f"{match.group(1)} - {match.group(2).strip()} {match.group(3)}"
        
        return None
    
    def _get_technician_name(self, technician_id):
        """Get technician name from ID."""
        if not technician_id:
            return "Unassigned"
        
        # For now, return a formatted technician ID
        # In the future, this could query a technician mapping table
        return f"Technician {technician_id}"
    
    def _get_priority_from_status(self, status):
        """Map Freshworks status to priority."""
        # Default to Medium priority
        return 'Medium'
    
    def _map_status(self, status_id):
        """Map Freshworks status ID to string."""
        status_map = {
            2: 'Open',
            3: 'Pending',
            4: 'Resolved',
            5: 'Closed',
            10: 'Open'  # Default for status 10
        }
        return status_map.get(status_id, 'Open')
    
    def clear_all_tickets(self):
        """Clear all tickets from the database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("DELETE FROM freshworks_tickets"))
                conn.commit()
                return result.rowcount
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error clearing tickets: {str(e)}")
            return 0

# Global instance
_freshworks_db_manager = None

def init_freshworks_db_manager(app):
    """Initialize the Freshworks database manager."""
    global _freshworks_db_manager
    _freshworks_db_manager = FreshworksDBManager(app)
    return _freshworks_db_manager

def get_freshworks_db_manager():
    """Get the global Freshworks database manager instance."""
    return _freshworks_db_manager 