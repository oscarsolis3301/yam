import requests
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv

# Add the app directory to the Python path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import after adding to path
from app import create_app
from app.models.base import TicketClosure, FreshworksUserMapping, User, TicketSyncMetadata
from app.extensions import db
from app.utils.freshworks_service import freshworks_service
from app.utils.ticket_closure_service import ticket_closure_service

load_dotenv()

API_KEY = os.getenv('FRESH_API')
ENDPOINT = os.getenv('FRESH_ENDPOINT')  # Ensure trailing slash
GROUP_ID = 18000294963
STATUS_RESOLVED = 4
PER_PAGE = 100

def load_id_name_map(filepath):
    """Load ID to name mapping from IDs.txt file with improved parsing"""
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
                            print(f"✅ Mapped: {name} -> {id_int}")
                        except ValueError:
                            print(f"⚠️ Invalid ID format on line {line_num}: {id_str}")
                else:
                    print(f"⚠️ Invalid format on line {line_num}: {line}")
                    
    except FileNotFoundError:
        print(f"⚠️ ID file '{filepath}' not found. Proceeding without name mapping.")
    except Exception as e:
        print(f"❌ Error reading ID file: {e}")
    
    print(f"📋 Loaded {len(id_name_map)} user mappings from {filepath}")
    return id_name_map

def get_todays_tickets():
    """Get tickets updated today using the FreshworksService"""
    return freshworks_service.get_tickets_for_date()

def sync_user_mappings_to_db(id_name_map):
    """Sync user mappings from IDs.txt to the database using the service"""
    print("🔄 Syncing user mappings to database...")
    freshworks_service.sync_user_mappings()

def link_users_to_mappings():
    """Link existing users to Freshworks mappings based on username similarity"""
    print("🔗 Linking users to Freshworks mappings...")
    
    mappings = FreshworksUserMapping.query.filter_by(user_id=None).all()
    linked_count = 0
    
    for mapping in mappings:
        # Use the improved matching logic from the service
        local_user = freshworks_service._find_matching_user(mapping.freshworks_username)
        
        if local_user:
            mapping.user_id = local_user.id
            linked_count += 1
            print(f"✅ Linked {mapping.freshworks_username} to user {local_user.username}")
    
    try:
        db.session.commit()
        print(f"✅ Successfully linked {linked_count} users to mappings")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error linking users: {e}")

def sync_ticket_closures_to_db(tickets, id_name_map):
    """Sync ticket closure data to the database using the enhanced service with historical tracking"""
    print("🔄 Syncing ticket closures to database with historical tracking...")
    
    # Use the enhanced service to sync hourly closures
    today = datetime.now().date()
    current_hour = datetime.now().hour
    
    success = ticket_closure_service.sync_hourly_closures(today, current_hour)
    
    if success:
        print("✅ Ticket closures synced successfully with historical tracking")
        return True
    else:
        print("❌ Failed to sync ticket closures")
        return False

def summarize_closed_by_responder(tickets, id_name_map):
    """Generate summary file with ticket closure data including ticket numbers"""
    today = datetime.now(timezone.utc).date()
    counts = defaultdict(int)
    ticket_details = defaultdict(list)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(script_dir, f"resolved_tickets_summary_{timestamp}.txt")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Ticket Summary for {today} (Resolved, Group {GROUP_ID}):\n\n")

        for ticket in tickets:
            if not isinstance(ticket, dict):
                continue
            if ticket.get('status') != STATUS_RESOLVED:
                continue
            if ticket.get('group_id') != GROUP_ID:
                continue

            updated_at_str = ticket.get('updated_at')
            if not updated_at_str:
                continue

            try:
                updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ").date()
            except Exception:
                continue

            if updated_at != today:
                continue

            responder_id = ticket.get('responder_id')
            if responder_id:
                counts[responder_id] += 1
                ticket_id = ticket.get('id')
                ticket_details[responder_id].append(ticket_id)
                line = f"Ticket ID: {ticket_id}, Responder ID: {responder_id}, Updated At: {updated_at_str}\n"
                f.write(line)

        f.write("\nSummary (Most to Least Tickets Resolved):\n")
        if not counts:
            msg = "No resolved tickets found today for the specified group."
            print(msg)
            f.write(msg + "\n")
        else:
            # Sort counts descending by number of tickets
            sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            for responder_id, count in sorted_counts:
                name = id_name_map.get(responder_id, f"Responder ID# {responder_id}")
                ticket_numbers = ticket_details[responder_id]
                line = f"{name} has resolved {count} ticket(s) today!"
                print(line)
                f.write(line + "\n")
                
                # Add ticket numbers to the summary
                if ticket_numbers:
                    ticket_list = ", ".join([f"INC-{tid}" for tid in ticket_numbers])
                    detail_line = f"  Ticket Numbers: {ticket_list}\n"
                    f.write(detail_line)
                    print(f"  Ticket Numbers: {ticket_list}")

    print(f"\n✅ Summary saved to: {filename}")
    return counts

def main():
    try:
        # Create Flask app context
        app = create_app()
        with app.app_context():
            print("🚀 Starting enhanced leaderboard sync with ticket tracking...")
            print("=" * 60)
            
            # Load user mappings
            script_dir = os.path.dirname(os.path.abspath(__file__))
            id_file_path = os.path.join(script_dir, 'IDs.txt')
            id_name_map = load_id_name_map(id_file_path)
            
            # Sync user mappings to database
            sync_user_mappings_to_db(id_name_map)
            
            # Link users to mappings
            link_users_to_mappings()
            
            # Get ticket data
            tickets = get_todays_tickets()
            print(f"\n🎟️ Retrieved {len(tickets)} ticket(s) updated today.")
            
            # Generate summary file (original functionality)
            summarize_closed_by_responder(tickets, id_name_map)
            
            # Sync to database for YAM dashboard with ticket numbers
            success = sync_ticket_closures_to_db(tickets, id_name_map)
            
            if success:
                print("\n🎉 Enhanced leaderboard sync completed successfully!")
                print("📊 Data is now available in the YAM Dashboard Daily Ticket Closures graph")
                print("🎫 Ticket numbers are now stored and can be viewed in user detail modals")
                
                # Show current sync status
                print("\n📈 Current Sync Status:")
                print("=" * 50)
                
                # Count mappings
                total_mappings = FreshworksUserMapping.query.count()
                linked_mappings = FreshworksUserMapping.query.filter(FreshworksUserMapping.user_id.isnot(None)).count()
                print(f"User Mappings: {linked_mappings} linked, {total_mappings} total")
                
                # Count today's closures
                today = datetime.now(timezone.utc).date()
                today_closures = TicketClosure.query.filter_by(date=today).count()
                total_closures = TicketClosure.query.count()
                print(f"Ticket Closures: {today_closures} for today, {total_closures} total")
                
                # Show sync metadata
                metadata = TicketSyncMetadata.query.filter_by(sync_date=today).first()
                if metadata:
                    print(f"Today's Sync: {metadata.sync_count} syncs, {metadata.tickets_processed} tickets processed")
                    print(f"Last Sync: {metadata.last_sync_time}")
                else:
                    print("Today's Sync: No syncs yet")
                
            else:
                print("\n❌ Database sync failed, but summary file was created")
                
    except requests.HTTPError as e:
        print(f"❌ HTTP error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
