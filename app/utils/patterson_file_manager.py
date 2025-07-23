import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import threading
import re

# Load environment variables
load_dotenv()

class PattersonFileManager:
    """Manages Patterson ticket data with 3-hour refresh intervals and file-based storage."""
    
    def __init__(self, app=None):
        self.app = app
        self.TARGET_GROUP_ID = 18000305996
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.FRESHWORKS_DIR = os.path.join(self.BASE_DIR, "Freshworks")
        self.TIMER_FILE = os.path.join(self.FRESHWORKS_DIR, "last_update.txt")
        self.REFRESH_INTERVAL = 3 * 60 * 60  # 3 hours in seconds
        
        # Ensure directories exist
        os.makedirs(self.FRESHWORKS_DIR, exist_ok=True)
        
        # DISABLED: Background refresh thread - now handled by frontend timer system
        # self.start_background_refresh()
        
        if self.app:
            self.app.logger.info("Patterson file manager initialized (background refresh disabled - using frontend timer)")
    
    def get_today_filename(self):
        """Get today's date in YYYY-MM-DD.txt format."""
        return datetime.utcnow().strftime('%Y-%m-%d') + '.txt'
    
    def get_today_iso(self):
        """Get today's date in ISO format for API calls."""
        return datetime.utcnow().strftime('%Y-%m-%dT00:00:00Z')
    
    def get_today_date_only(self):
        """Get today's date in YYYY-MM-DD format."""
        return datetime.utcnow().strftime('%Y-%m-%d')
    
    def update_timer_file(self):
        """Update the timer file with current timestamp."""
        try:
            with open(self.TIMER_FILE, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error updating timer file: {e}")
    
    # Note: All Freshworks API calls now use app/freshworks.py functions
    # Removed: fetch_all_today_tickets, fetch_notes, filter_tickets, save_tickets_to_file
    
    def refresh_data(self):
        """Manually refresh data from Freshworks API (only called when user clicks refresh or timer allows)."""
        if self.app:
            self.app.logger.info("Manual refresh requested, checking timer...")
        
        # Check if we should actually refresh based on timer
        should_refresh = self._should_refresh_based_on_timer()
        
        if not should_refresh:
            if self.app:
                self.app.logger.info("Manual refresh: Timer indicates refresh not needed, reading from existing file")
            existing_file = self.get_existing_today_file()
            if existing_file:
                return self.get_tickets_from_file()
            else:
                if self.app:
                    self.app.logger.info("Manual refresh: No existing file found, proceeding with API call")
        
        if self.app:
            self.app.logger.info("Manual refresh: Timer allows refresh, using freshworks.py logic...")
        
        try:
            # Use freshworks.py logic to fetch and save today's tickets
            from app import freshworks
            all_tix  = freshworks.fetch_all_today_tickets()
            filt_tix = freshworks.filter_tickets(all_tix)
            freshworks.save_tickets(filt_tix)
            self.update_timer_file()
            if self.app:
                self.app.logger.info(f"Manual refresh completed. Saved {len(filt_tix)} tickets to file.")
            return self.get_tickets_from_file()
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Manual refresh failed (freshworks.py): {e}")
            existing_file = self.get_existing_today_file()
            if existing_file:
                if self.app:
                    self.app.logger.info(f"Manual refresh failed, reading from existing file: {os.path.basename(existing_file)}")
                return self.get_tickets_from_file()
            if self.app:
                self.app.logger.warning("Manual refresh failed and no file exists, returning empty ticket list")
            return []

    def _should_refresh_based_on_timer(self):
        """Check if we should refresh based on the timer file and 3-hour interval."""
        try:
            if not os.path.exists(self.TIMER_FILE):
                if self.app:
                    self.app.logger.info("Timer file does not exist, refresh allowed")
                return True
            
            # Read last update time from timer file
            with open(self.TIMER_FILE, 'r') as f:
                last_update_str = f.read().strip()
            
            if not last_update_str:
                if self.app:
                    self.app.logger.info("Timer file is empty, refresh allowed")
                return True
            
            # Parse last update time
            last_update = datetime.fromisoformat(last_update_str)
            current_time = datetime.now()
            time_since_last_update = (current_time - last_update).total_seconds()
            
            if self.app:
                self.app.logger.info(f"Time since last update: {time_since_last_update} seconds (limit: {self.REFRESH_INTERVAL})")
            
            # Only refresh if 3 hours (10800 seconds) have passed
            if time_since_last_update >= self.REFRESH_INTERVAL:
                if self.app:
                    self.app.logger.info("Timer allows refresh (3+ hours since last update)")
                return True
            else:
                remaining_time = self.REFRESH_INTERVAL - time_since_last_update
                if self.app:
                    self.app.logger.info(f"Timer blocks refresh (refresh in {remaining_time:.0f} seconds)")
                return False
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error checking timer: {e}")
            # If timer check fails, allow refresh to be safe
            return True
    
    def get_tickets_from_file(self):
        """Get tickets from today's file with description and notes."""
        # Check for existing files first
        existing_file = self.get_existing_today_file()
        if existing_file:
            filename = existing_file
        else:
            # Fallback to standard naming
            today = self.get_today_date_only()
            filename = os.path.join(self.FRESHWORKS_DIR, f"{today}.txt")
        
        return self._parse_specific_file(filename)
    
    def _parse_specific_file(self, file_path):
        """Parse a specific file path and extract ticket data."""
        if not os.path.exists(file_path):
            return []
        
        try:
            tickets = []
            current_ticket = {}
            in_description = False
            in_notes = False
            current_notes = []
            
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("Ticket #"):
                    if current_ticket:
                        if current_notes:
                            current_ticket["notes"] = current_notes
                        tickets.append(current_ticket)
                    current_ticket = {"id": line.split("#")[1]}
                    in_description = False
                    in_notes = False
                    current_notes = []
                    
                elif line.startswith("Ticket-Title"):
                    if ':' in line:
                        title = line.split(':', 1)[1].strip()
                        current_ticket["title"] = title
                        current_ticket["subject"] = title
                    else:
                        title = line.replace('Ticket-Title', '').strip()
                        if title:
                            current_ticket["title"] = title
                            current_ticket["subject"] = title
                elif line.startswith("Title"):
                    if 'title' not in current_ticket:
                        if ':' in line:
                            title = line.split(':', 1)[1].strip()
                            current_ticket["title"] = title
                            current_ticket["subject"] = title
                        else:
                            title = line.replace('Title', '').strip()
                            if title:
                                current_ticket["title"] = title
                                current_ticket["subject"] = title
                elif line.startswith("Subject"):
                    if 'title' not in current_ticket:
                        if ':' in line:
                            subject = line.split(':', 1)[1].strip()
                            current_ticket["subject"] = subject
                        else:
                            subject = line.replace('Subject', '').strip()
                            if subject:
                                current_ticket["subject"] = subject
                elif line.startswith("Group ID      :"):
                    current_ticket["group_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("Assigned To   :"):
                    responder_id = line.split(":", 1)[1].strip()
                    current_ticket["responder_id"] = responder_id if responder_id != "Unassigned" else None
                elif line.startswith("Created At    :"):
                    current_ticket["created_at"] = line.split(":", 1)[1].strip()
                elif line.startswith("Status        :"):
                    current_ticket["status"] = line.split(":", 1)[1].strip()
                elif line.startswith("Ticket-Description") and not in_description:
                    in_description = True
                    in_notes = False
                    current_ticket["description"] = ""
                    continue
                elif in_description:
                    # Stop if we hit Notes or a blank line
                    if line.startswith('Notes:') or not line:
                        in_description = False
                        in_notes = line.startswith('Notes:')
                        if in_notes:
                            current_notes = []
                        continue
                    # Add to description
                    if current_ticket.get('description'):
                        current_ticket['description'] += '\n' + line
                    else:
                        current_ticket['description'] = line
                elif in_notes and line.startswith("  ["):
                    note_content = line[line.find("]") + 1:].strip()
                    current_notes.append(note_content)
                elif in_notes and line and not line.startswith("  ["):
                    if current_notes:
                        current_notes[-1] += "\n" + line
            # Add the last ticket if exists
            if current_ticket:
                if current_notes:
                    current_ticket["notes"] = current_notes
                tickets.append(current_ticket)
            if self.app:
                self.app.logger.info(f"Read {len(tickets)} tickets from {os.path.basename(file_path)}")
            return tickets
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error reading tickets from file {file_path}: {e}")
            return []
    
    def migrate_old_file_to_new_format(self):
        """Migrate old format files to new simple date format if needed."""
        today = self.get_today_date_only()
        simple_file = os.path.join(self.FRESHWORKS_DIR, f"{today}.txt")
        
        # If simple format already exists, no migration needed
        if os.path.exists(simple_file):
            return
        
        # Look for old format files
        old_files = []
        for filename in os.listdir(self.FRESHWORKS_DIR):
            if today in filename and filename.endswith('.txt') and filename != f"{today}.txt":
                old_files.append(filename)
        
        if old_files:
            # Use the group-specific file if it exists
            group_file = f"tickets_status_10_group_{self.TARGET_GROUP_ID}_{today}.txt"
            if group_file in old_files:
                source_file = os.path.join(self.FRESHWORKS_DIR, group_file)
            else:
                source_file = os.path.join(self.FRESHWORKS_DIR, old_files[0])
            
            # Copy content to new format (don't delete old file)
            try:
                import shutil
                shutil.copy2(source_file, simple_file)
                if self.app:
                    self.app.logger.info(f"Migrated {os.path.basename(source_file)} to {os.path.basename(simple_file)}")
            except Exception as e:
                if self.app:
                    self.app.logger.error(f"Error migrating file: {e}")
    
    def get_tickets(self):
        """Get tickets from existing files only - no automatic API calls."""
        # First, try to migrate old format files to new format
        self.migrate_old_file_to_new_format()
        
        # Check for existing files with today's date
        existing_file = self.get_existing_today_file()
        
        # If today's file exists, read from it immediately
        if existing_file:
            if self.app:
                self.app.logger.info(f"Reading tickets from existing file: {os.path.basename(existing_file)}")
            return self.get_tickets_from_file()
        
        # If no file exists for today, return empty list - API calls are now handled by frontend timer
        if self.app:
            self.app.logger.info("No file for today found - API calls are handled by frontend timer system")
        return []
    
    def get_existing_today_file(self):
        """Check for existing files with today's date and return the best match."""
        today = self.get_today_date_only()
        
        # Look for the simple date format file first
        simple_file = os.path.join(self.FRESHWORKS_DIR, f"{today}.txt")
        if os.path.exists(simple_file):
            return simple_file
        
        # If simple format doesn't exist, look for files with today's date
        existing_files = []
        for filename in os.listdir(self.FRESHWORKS_DIR):
            if today in filename and filename.endswith('.txt'):
                existing_files.append(filename)
        
        if existing_files:
            # Prefer the group-specific file if it exists
            group_file = f"tickets_status_10_group_{self.TARGET_GROUP_ID}_{today}.txt"
            if group_file in existing_files:
                return os.path.join(self.FRESHWORKS_DIR, group_file)
            
            # Otherwise return the first file with today's date
            return os.path.join(self.FRESHWORKS_DIR, existing_files[0])
        
        return None
    
    def parse_txt_file(self, file_path):
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
                for line in lines:
                    line = line.strip()
                    if line.startswith("Ticket #"):
                        ticket = {"id": line.split("#")[1]}
                        in_description = False
                        in_notes = False
                        current_notes = []
                    elif line.startswith("Ticket-Title"):
                        if ':' in line:
                            title = line.split(':', 1)[1].strip()
                            ticket["title"] = title
                            ticket["subject"] = title
                        else:
                            title = line.replace('Ticket-Title', '').strip()
                            if title:
                                ticket["title"] = title
                                ticket["subject"] = title
                    elif line.startswith("Title"):
                        if 'title' not in ticket:
                            if ':' in line:
                                title = line.split(':', 1)[1].strip()
                                ticket["title"] = title
                                ticket["subject"] = title
                            else:
                                title = line.replace('Title', '').strip()
                                if title:
                                    ticket["title"] = title
                                    ticket["subject"] = title
                    elif line.startswith("Subject"):
                        if 'title' not in ticket:
                            if ':' in line:
                                subject = line.split(':', 1)[1].strip()
                                ticket["subject"] = subject
                            else:
                                subject = line.replace('Subject', '').strip()
                                if subject:
                                    ticket["subject"] = subject
                    elif line.startswith("Group ID"):
                        ticket["group_id"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Assigned To"):
                        responder_id = line.split(":", 1)[1].strip()
                        ticket["responder_id"] = responder_id if responder_id != "Unassigned" else None
                    elif line.startswith("Created At"):
                        ticket["created_at"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Status"):
                        ticket["status"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Ticket-Description"):
                        in_description = True
                        in_notes = False
                        ticket["description"] = ""
                        continue
                    elif in_description:
                        if line.startswith('Notes:') or not line:
                            in_description = False
                            in_notes = line.startswith('Notes:')
                            if in_notes:
                                current_notes = []
                            continue
                        if ticket.get('description'):
                            ticket['description'] += '\n' + line
                        else:
                            ticket['description'] = line
                    elif line.startswith('Notes:'):
                        in_notes = True
                        in_description = False
                        current_notes = []
                    elif in_notes and line.startswith("  ["):
                        note_content = line[line.find("]") + 1:].strip()
                        current_notes.append(note_content)
                    elif in_notes and line and not line.startswith("  ["):
                        if current_notes:
                            current_notes[-1] += "\n" + line
                if current_notes:
                    ticket["notes"] = current_notes
                if ticket:
                    tickets.append(ticket)
            return tickets
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error parsing file {file_path}: {str(e)}")
            return []

    def parse_csv_file(self, file_path):
        """Parse uploaded CSV file and extract ticket data."""
        try:
            import csv
            tickets = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticket = {
                        'id': int(row.get('id', 0)),
                        'subject': row.get('subject', ''),
                        'description': row.get('description', ''),
                        'responder_id': row.get('responder_id'),
                        'created_at': row.get('created_at', ''),
                        'status': int(row.get('status', 10)),
                        'group_id': int(row.get('group_id', self.TARGET_GROUP_ID)),
                        'notes': []
                    }
                    
                    # Parse notes if present
                    if row.get('notes'):
                        ticket['notes'] = [note.strip() for note in row['notes'].split('|') if note.strip()]
                    
                    tickets.append(ticket)
            
            return tickets
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error parsing CSV file: {e}")
            return []

    def parse_json_file(self, file_path):
        """Parse uploaded JSON file and extract ticket data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON formats
            if isinstance(data, list):
                tickets = data
            elif isinstance(data, dict) and 'tickets' in data:
                tickets = data['tickets']
            else:
                tickets = [data]
            
            # Ensure all tickets have required fields
            for ticket in tickets:
                if 'id' not in ticket:
                    ticket['id'] = int(time.time())
                if 'status' not in ticket:
                    ticket['status'] = 10
                if 'group_id' not in ticket:
                    ticket['group_id'] = self.TARGET_GROUP_ID
            
            return tickets
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error parsing JSON file: {e}")
            return []

    def save_calendar_event(self, event):
        """Save a calendar event to a special file."""
        try:
            calendar_file = os.path.join(self.FRESHWORKS_DIR, "calendar_events.json")
            
            # Load existing events
            events = []
            if os.path.exists(calendar_file):
                with open(calendar_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            
            # Add new event
            events.append(event)
            
            # Save back to file
            with open(calendar_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            
            if self.app:
                self.app.logger.info(f"Saved calendar event: {event.get('title', 'Untitled')}")
            
            return True
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error saving calendar event: {e}")
            return False

    def get_calendar_events(self):
        """Get all calendar events."""
        try:
            calendar_file = os.path.join(self.FRESHWORKS_DIR, "calendar_events.json")
            
            if os.path.exists(calendar_file):
                with open(calendar_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return []
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error loading calendar events: {e}")
            return []

    def force_refresh_data(self):
        """Force refresh data from Freshworks API (bypasses timer - for admin manual pull)."""
        if self.app:
            self.app.logger.info("Force refresh requested (admin manual pull), using freshworks.py logic...")
        try:
            from app import freshworks
            all_tix  = freshworks.fetch_all_today_tickets()
            filt_tix = freshworks.filter_tickets(all_tix)
            freshworks.save_tickets(filt_tix)
            self.update_timer_file()
            if self.app:
                self.app.logger.info(f"Force refresh completed. Saved {len(filt_tix)} tickets to file.")
            return self.get_tickets_from_file()
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Force refresh failed (freshworks.py): {e}")
            existing_file = self.get_existing_today_file()
            if existing_file:
                if self.app:
                    self.app.logger.info(f"Force refresh failed, reading from existing file: {os.path.basename(existing_file)}")
                return self.get_tickets_from_file()
            if self.app:
                self.app.logger.warning("Force refresh failed and no file exists, returning empty ticket list")
            return []

# Global instance
patterson_file_manager = None

def init_patterson_file_manager(app):
    """Initialize the Patterson file manager with Flask app."""
    global patterson_file_manager
    patterson_file_manager = PattersonFileManager(app)
    return patterson_file_manager

def get_patterson_file_manager():
    """Get the global Patterson file manager instance."""
    return patterson_file_manager 