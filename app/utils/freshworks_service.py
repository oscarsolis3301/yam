import requests
import os
from datetime import datetime, timezone, timedelta, date
from collections import defaultdict
from dotenv import load_dotenv
from app.extensions import db
from app.models.base import TicketClosure, FreshworksUserMapping, User, TicketSyncMetadata
from app.utils.logger import setup_logging

load_dotenv()
logger = setup_logging()

class FreshworksService:
    def __init__(self):
        self.api_key = os.getenv('FRESH_API')
        self.endpoint = os.getenv('FRESH_ENDPOINT')
        self.group_id = 18000294963
        self.status_resolved = 4
        self.per_page = 100
        
        if not self.api_key or not self.endpoint:
            raise ValueError("FRESH_API and FRESH_ENDPOINT environment variables must be set")
        
        # Ensure endpoint ends with slash
        if not self.endpoint.endswith('/'):
            self.endpoint += '/'
    
    def load_id_name_mapping(self, filepath=None):
        """Load ID to name mapping from IDs.txt file with improved parsing"""
        if filepath is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(script_dir, 'Freshworks', 'IDs.txt')
        
        id_name_map = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Handle "Name - ID" format
                    if ' - ' in line:
                        parts = line.split(' - ', 1)
                        if len(parts) == 2:
                            name = parts[0].strip()
                            id_str = parts[1].strip()
                            try:
                                id_int = int(id_str)
                                id_name_map[id_int] = name
                                logger.debug(f"✅ Mapped: {name} -> {id_int}")
                            except ValueError:
                                logger.warning(f"⚠️ Invalid ID format on line {line_num}: {id_str}")
                    else:
                        logger.warning(f"⚠️ Invalid format on line {line_num}: {line}")
                        
        except FileNotFoundError:
            logger.warning(f"⚠️ ID file '{filepath}' not found. Proceeding without name mapping.")
        except Exception as e:
            logger.error(f"❌ Error reading ID file: {e}")
        
        logger.info(f"📋 Loaded {len(id_name_map)} user mappings from {filepath}")
        return id_name_map
    
    def get_tickets_for_date(self, target_date=None):
        """Get tickets updated on a specific date (defaults to today)"""
        if target_date is None:
            target_date = date.today()
        
        tickets = []
        page = 1
        
        # Set the date range for the target date
        if isinstance(target_date, date):
            target_datetime = datetime.combine(target_date, datetime.min.time())
        else:
            target_datetime = target_date
            
        target_start_utc = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        updated_since = target_start_utc.isoformat()

        while True:
            url = f"{self.endpoint}tickets"
            params = {
                "page": page,
                "per_page": self.per_page,
                "updated_since": updated_since
            }
            
            try:
                response = requests.get(url, params=params, auth=(self.api_key, 'X'))
                logger.info(f"Fetching page {page}... Status: {response.status_code}")
                response.raise_for_status()

                page_tickets = response.json().get('tickets', [])
                if not isinstance(page_tickets, list):
                    logger.warning("⚠️ Unexpected 'tickets' format, stopping pagination.")
                    break

                tickets.extend(page_tickets)
                if len(page_tickets) < self.per_page:
                    break
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error fetching tickets: {e}")
                break

        return tickets
    
    def get_daily_closures(self, target_date=None):
        """Get ticket closures for a specific date and return counts by responder with detailed unmapped user info"""
        if target_date is None:
            target_date = date.today()
        
        tickets = self.get_tickets_for_date(target_date)
        
        if isinstance(target_date, date):
            target_date_obj = target_date
        else:
            target_date_obj = target_date.date()
        
        counts = defaultdict(int)
        unmapped_users = defaultdict(list)  # Track unmapped users with ticket details
        
        for ticket in tickets:
            if not isinstance(ticket, dict):
                continue
            if ticket.get('status') != self.status_resolved:
                continue
            if ticket.get('group_id') != self.group_id:
                continue

            updated_at_str = ticket.get('updated_at')
            if not updated_at_str:
                continue

            try:
                updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ").date()
            except Exception:
                continue

            if updated_at != target_date_obj:
                continue

            responder_id = ticket.get('responder_id')
            if responder_id:
                counts[responder_id] += 1
                # Track ticket details for unmapped users
                unmapped_users[responder_id].append({
                    'ticket_id': ticket.get('id'),
                    'responder_id': responder_id,
                    'updated_at': updated_at_str
                })
        
        logger.info(f"📊 Found {len(counts)} responders with resolved tickets for {target_date_obj}")
        
        # Log detailed unmapped user information
        id_name_map = self.load_id_name_mapping()
        for responder_id in counts.keys():
            if responder_id not in id_name_map:
                tickets_info = unmapped_users[responder_id]
                logger.warning(f"⚠️ Unmapped Freshworks User ID: {responder_id}")
                logger.warning(f"   📋 Tickets found: {len(tickets_info)}")
                logger.warning(f"   🎫 Sample ticket IDs: {[t['ticket_id'] for t in tickets_info[:3]]}")
                logger.warning(f"   🔍 Add to IDs.txt: 'Unknown User {responder_id} - {responder_id}'")
        
        return counts
    
    def sync_user_mappings(self):
        """Sync Freshworks user IDs with local users using improved mapping logic"""
        id_name_map = self.load_id_name_mapping()
        
        mappings_created = 0
        mappings_updated = 0
        
        for freshworks_id, freshworks_name in id_name_map.items():
            # First, check if mapping already exists
            existing_mapping = FreshworksUserMapping.query.filter_by(
                freshworks_user_id=freshworks_id
            ).first()
            
            if existing_mapping:
                # Update existing mapping if name changed
                if existing_mapping.freshworks_username != freshworks_name:
                    existing_mapping.freshworks_username = freshworks_name
                    existing_mapping.updated_at = datetime.utcnow()
                    mappings_updated += 1
                    logger.info(f"🔄 Updated mapping: {freshworks_name} (ID: {freshworks_id})")
                continue
            
            # Try to find a local user that matches
            local_user = self._find_matching_user(freshworks_name)
            
            if local_user:
                # Create new mapping with user link
                mapping = FreshworksUserMapping(
                    user_id=local_user.id,
                    freshworks_user_id=freshworks_id,
                    freshworks_username=freshworks_name
                )
                db.session.add(mapping)
                mappings_created += 1
                logger.info(f"✅ Created mapping: {freshworks_name} -> {local_user.username} (ID: {freshworks_id})")
            else:
                # Create mapping without user link (will be linked later)
                mapping = FreshworksUserMapping(
                    user_id=None,
                    freshworks_user_id=freshworks_id,
                    freshworks_username=freshworks_name
                )
                db.session.add(mapping)
                mappings_created += 1
                logger.warning(f"⚠️ No local user found for Freshworks user: {freshworks_name} (ID: {freshworks_id})")
                logger.warning(f"   🔍 Consider adding a local user with username/email matching: {freshworks_name}")
        
        try:
            db.session.commit()
            logger.info(f"✅ User mappings synced successfully: {mappings_created} created, {mappings_updated} updated")
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Error syncing user mappings: {e}")
    
    def _find_matching_user(self, freshworks_name):
        """Find a local user that matches the Freshworks name using improved logic"""
        # Normalize the name for comparison
        freshworks_name_lower = freshworks_name.lower().strip()
        freshworks_name_original = freshworks_name.strip()
        
        # Try exact username match first (case-insensitive)
        local_user = User.query.filter(User.username.ilike(freshworks_name_original)).first()
        if local_user:
            return local_user
        
        # Try exact username match with lowercase
        local_user = User.query.filter_by(username=freshworks_name_lower).first()
        if local_user:
            return local_user
        
        # Try email match (case-insensitive)
        local_user = User.query.filter(User.email.ilike(freshworks_name_original)).first()
        if local_user:
            return local_user
        
        # Try email match with lowercase
        local_user = User.query.filter_by(email=freshworks_name_lower).first()
        if local_user:
            return local_user
        
        # Try partial matches with name parts
        name_parts = freshworks_name_lower.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
            
            # Look for users with similar patterns
            possible_users = User.query.filter(
                (User.username.ilike(f"{first_name}%")) |
                (User.username.ilike(f"%{first_name}%")) |
                (User.email.ilike(f"{first_name}%")) |
                (User.username.ilike(f"%{last_name}%")) |
                (User.email.ilike(f"%{last_name}%"))
            ).all()
            
            # Find the best match
            for user in possible_users:
                user_lower = user.username.lower()
                email_lower = user.email.lower() if user.email else ""
                
                # Check if both first and last name are present
                if (first_name in user_lower or first_name in email_lower) and \
                   (last_name in user_lower or last_name in email_lower):
                    return user
                
                # Check for exact first name match
                if user_lower.startswith(first_name) or email_lower.startswith(first_name):
                    return user
        
        # Try single word matches (for cases like "AJ", "JZ")
        if len(name_parts) == 1:
            single_name = name_parts[0]
            # Try exact match for single names
            local_user = User.query.filter(User.username.ilike(single_name)).first()
            if local_user:
                return local_user
        
        return None
    
    def sync_daily_closures_with_tickets(self, target_date=None, force_sync=False):
        """Sync daily ticket closures with ticket number tracking"""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        # Check rate limiting unless force sync
        if not force_sync:
            can_sync, time_until_next = self._check_sync_availability(target_date)
            if not can_sync:
                minutes_left = int(time_until_next / 60)
                logger.info(f"⏰ Sync rate limited. Next sync available in {minutes_left} minutes.")
                return False
        
        logger.info(f"🔄 Starting enhanced sync for {target_date} with ticket tracking...")
        
        # Get closure counts and ticket details from Freshworks
        closure_data = self.get_daily_closures_with_tickets(target_date)
        
        total_tickets_processed = sum(data['count'] for data in closure_data.values())
        
        # Update database records - ensuring one entry per user per day
        for freshworks_id, data in closure_data.items():
            count = data['count']
            ticket_numbers = data['ticket_numbers']
            
            # Find the user mapping
            mapping = FreshworksUserMapping.query.filter_by(
                freshworks_user_id=freshworks_id
            ).first()
            
            if mapping and mapping.user_id:
                # Always update existing record or create new one (upsert logic)
                existing_closure = TicketClosure.query.filter_by(
                    user_id=mapping.user_id,
                    date=target_date
                ).first()
                
                # Convert ticket numbers to JSON string
                import json
                ticket_numbers_json = json.dumps(ticket_numbers) if ticket_numbers else None
                
                if existing_closure:
                    # Update existing record (only one entry per user per day)
                    existing_closure.tickets_closed = count
                    existing_closure.freshworks_user_id = freshworks_id
                    existing_closure.ticket_numbers = ticket_numbers_json
                    existing_closure.updated_at = datetime.utcnow()
                    logger.info(f"🔄 Updated: {mapping.freshworks_username} - {count} tickets with numbers")
                else:
                    # Create new record
                    new_closure = TicketClosure(
                        user_id=mapping.user_id,
                        freshworks_user_id=freshworks_id,
                        date=target_date,
                        tickets_closed=count,
                        ticket_numbers=ticket_numbers_json
                    )
                    db.session.add(new_closure)
                    logger.info(f"➕ Created new entry for {mapping.freshworks_username}: {count} tickets on {target_date}")
            else:
                # Enhanced unmapped user logging
                id_name_map = self.load_id_name_mapping()
                name = id_name_map.get(freshworks_id, f"Unknown User {freshworks_id}")
                logger.warning(f"⚠️ No user mapping found for Freshworks user ID: {freshworks_id}")
                logger.warning(f"   📝 Name from IDs.txt: {name}")
                logger.warning(f"   🎫 Tickets closed: {count}")
                logger.warning(f"   🔍 Add to IDs.txt: '{name} - {freshworks_id}' or create local user")
        
        # Update sync metadata with persistent tracking
        try:
            db.session.commit()
            
            # Update sync metadata
            metadata = TicketSyncMetadata.query.filter_by(sync_date=target_date).first()
            if metadata:
                metadata.sync_count += 1
                metadata.tickets_processed = total_tickets_processed
                metadata.last_sync_time = datetime.utcnow()
            else:
                metadata = TicketSyncMetadata(
                    sync_date=target_date,
                    sync_count=1,
                    tickets_processed=total_tickets_processed
                )
                db.session.add(metadata)
            
            db.session.commit()
            logger.info(f"✅ Enhanced daily closures synced successfully for {target_date} - {total_tickets_processed} tickets processed with numbers")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Error syncing ticket closures with numbers: {e}")
            return False

    def get_daily_closures_with_tickets(self, target_date=None):
        """Get daily closure counts with ticket numbers for each user"""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        logger.info(f"🎫 Fetching daily closures with ticket numbers for {target_date}")
        
        # Get all tickets for the date
        tickets = self.get_tickets_for_date(target_date)
        
        # Group by responder and collect ticket numbers
        closure_data = {}
        
        for ticket in tickets:
            if not isinstance(ticket, dict):
                continue
                
            if ticket.get('status') != 4:  # Not resolved
                continue
                
            if ticket.get('group_id') != self.group_id:
                continue
            
            responder_id = ticket.get('responder_id')
            if not responder_id:
                continue
            
            ticket_id = ticket.get('id')
            
            if responder_id not in closure_data:
                closure_data[responder_id] = {
                    'count': 0,
                    'ticket_numbers': []
                }
            
            closure_data[responder_id]['count'] += 1
            if ticket_id:
                closure_data[responder_id]['ticket_numbers'].append(ticket_id)
        
        logger.info(f"📊 Found {len(closure_data)} users with closures, {sum(data['count'] for data in closure_data.values())} total tickets")
        return closure_data
    
    def sync_daily_closures(self, target_date=None, force_sync=False):
        """Sync daily closure data for a specific date with improved rate limiting and persistent tracking"""
        if target_date is None:
            target_date = date.today()
        
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # Enhanced rate limiting check with persistent tracking
        if not force_sync:
            can_sync, time_until_next = self._check_sync_availability(target_date)
            if not can_sync:
                minutes_left = int(time_until_next / 60)
                logger.info(f"⏰ Sync rate limited. Next sync available in {minutes_left} minutes.")
                return False
        
        logger.info(f"🔄 Starting sync for {target_date}...")
        
        # Get closure counts from Freshworks
        closure_counts = self.get_daily_closures(target_date)
        
        total_tickets_processed = sum(closure_counts.values())
        
        # Update database records - ensuring one entry per user per day
        for freshworks_id, count in closure_counts.items():
            # Find the user mapping
            mapping = FreshworksUserMapping.query.filter_by(
                freshworks_user_id=freshworks_id
            ).first()
            
            if mapping and mapping.user_id:
                # Always update existing record or create new one (upsert logic)
                existing_closure = TicketClosure.query.filter_by(
                    user_id=mapping.user_id,
                    date=target_date
                ).first()
                
                if existing_closure:
                    # Update existing record (only one entry per user per day)
                    existing_closure.tickets_closed = count
                    existing_closure.freshworks_user_id = freshworks_id
                    existing_closure.updated_at = datetime.utcnow()
                    logger.info(f"🔄 Updated: {mapping.freshworks_username} - {count} tickets")
                else:
                    # Create new record
                    new_closure = TicketClosure(
                        user_id=mapping.user_id,
                        freshworks_user_id=freshworks_id,
                        date=target_date,
                        tickets_closed=count
                    )
                    db.session.add(new_closure)
                    logger.info(f"➕ Created new entry for {mapping.freshworks_username}: {count} tickets on {target_date}")
            else:
                # Enhanced unmapped user logging
                id_name_map = self.load_id_name_mapping()
                name = id_name_map.get(freshworks_id, f"Unknown User {freshworks_id}")
                logger.warning(f"⚠️ No user mapping found for Freshworks user ID: {freshworks_id}")
                logger.warning(f"   📝 Name from IDs.txt: {name}")
                logger.warning(f"   🎫 Tickets closed: {count}")
                logger.warning(f"   🔍 Add to IDs.txt: '{name} - {freshworks_id}' or create local user")
        
        # Update sync metadata with persistent tracking
        try:
            db.session.commit()
            
            # Update sync metadata
            metadata = TicketSyncMetadata.query.filter_by(sync_date=target_date).first()
            if metadata:
                metadata.sync_count += 1
                metadata.tickets_processed = total_tickets_processed
                metadata.last_sync_time = datetime.utcnow()
            else:
                metadata = TicketSyncMetadata(
                    sync_date=target_date,
                    sync_count=1,
                    tickets_processed=total_tickets_processed
                )
                db.session.add(metadata)
            
            db.session.commit()
            logger.info(f"✅ Daily closures synced successfully for {target_date} - {total_tickets_processed} tickets processed")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Error syncing ticket closures: {e}")
            return False
    
    def _check_sync_availability(self, target_date):
        """Check if sync is available with enhanced persistent tracking"""
        metadata = TicketSyncMetadata.query.filter_by(sync_date=target_date).first()
        
        if not metadata:
            return True, 0  # No previous sync, can sync now
        
        # Check if at least 1 hour has passed since last sync
        now = datetime.utcnow()
        time_since_last = (now - metadata.last_sync_time).total_seconds()
        time_until_next = max(0, 3600 - time_since_last)
        
        can_sync = time_until_next <= 0
        
        if not can_sync:
            logger.info(f"⏰ Rate limiting active. Last sync: {metadata.last_sync_time}")
            logger.info(f"   ⏱️ Time since last sync: {int(time_since_last / 60)} minutes")
            logger.info(f"   ⏳ Time until next sync: {int(time_until_next / 60)} minutes")
        
        return can_sync, time_until_next
    
    def get_closure_data_for_period(self, start_date, end_date):
        """Get closure data for a date range"""
        closures = TicketClosure.query.filter(
            TicketClosure.date >= start_date,
            TicketClosure.date <= end_date
        ).all()
        
        return [closure.to_dict() for closure in closures]
    
    def get_top_performers(self, target_date=None, limit=10):
        """Get top performers for a specific date"""
        if target_date is None:
            target_date = date.today()
        
        closures = TicketClosure.query.filter_by(date=target_date)\
            .order_by(TicketClosure.tickets_closed.desc())\
            .limit(limit)\
            .all()
        
        return [closure.to_dict() for closure in closures]
    
    def get_unmapped_users_info(self):
        """Get information about unmapped users for debugging"""
        id_name_map = self.load_id_name_mapping()
        unmapped_info = []
        
        for freshworks_id, name in id_name_map.items():
            mapping = FreshworksUserMapping.query.filter_by(
                freshworks_user_id=freshworks_id
            ).first()
            
            if not mapping or not mapping.user_id:
                unmapped_info.append({
                    'freshworks_id': freshworks_id,
                    'freshworks_name': name,
                    'status': 'unmapped',
                    'suggestion': f"Add to IDs.txt: '{name} - {freshworks_id}' or create local user"
                })
        
        return unmapped_info

    def get_ticket_details(self, ticket_id):
        """Get detailed information for a specific ticket by ID"""
        try:
            url = f"{self.endpoint}tickets/{ticket_id}"
            headers = {
                'Authorization': f'Basic {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if 'ticket' in data:
                return data['ticket']
            else:
                logger.warning(f"Unexpected response format for ticket {ticket_id}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ticket {ticket_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ticket {ticket_id}: {e}")
            return None

    def get_user_tickets_for_date(self, freshworks_user_id, target_date):
        """Get tickets for a specific user on a specific date from Freshworks API"""
        if target_date is None:
            target_date = date.today()
        
        tickets = []
        page = 1
        
        # Set the date range for the target date
        if isinstance(target_date, date):
            target_datetime = datetime.combine(target_date, datetime.min.time())
        else:
            target_datetime = target_date
            
        target_start_utc = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        updated_since = target_start_utc.isoformat()

        while True:
            url = f"{self.endpoint}tickets"
            params = {
                "page": page,
                "per_page": self.per_page,
                "updated_since": updated_since,
                "responder_id": freshworks_user_id
            }
            
            try:
                response = requests.get(url, params=params, auth=(self.api_key, 'X'))
                logger.info(f"Fetching tickets for user {freshworks_user_id} on {target_date}, page {page}... Status: {response.status_code}")
                response.raise_for_status()

                page_tickets = response.json().get('tickets', [])
                if not isinstance(page_tickets, list):
                    logger.warning("⚠️ Unexpected 'tickets' format, stopping pagination.")
                    break

                # Filter tickets that were actually updated on the target date
                filtered_tickets = []
                for ticket in page_tickets:
                    updated_at_str = ticket.get('updated_at')
                    if updated_at_str:
                        try:
                            updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ")
                            updated_at_date = updated_at.date()
                            if updated_at_date == target_date:
                                filtered_tickets.append(ticket)
                        except ValueError:
                            logger.warning(f"Could not parse updated_at for ticket {ticket.get('id')}: {updated_at_str}")
                
                tickets.extend(filtered_tickets)
                
                if len(page_tickets) < self.per_page:
                    break
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error fetching tickets for user {freshworks_user_id}: {e}")
                break

        logger.info(f"Found {len(tickets)} tickets for user {freshworks_user_id} on {target_date}")
        return tickets

# Create a singleton instance
freshworks_service = FreshworksService()