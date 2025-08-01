import requests
import os
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import time
import json

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
    """Get tickets updated today using the FreshworksService with proper filtering"""
    today = datetime.now().date()
    print(f"🎯 Fetching tickets for date: {today}")
    
    # Get all tickets updated today
    all_tickets = freshworks_service.get_tickets_for_date(today)
    print(f"📊 Retrieved {len(all_tickets)} total tickets updated today")
    
    # Filter for resolved tickets from our specific group
    filtered_tickets = []
    for ticket in all_tickets:
        if not isinstance(ticket, dict):
            continue
            
        # Check if ticket is resolved
        if ticket.get('status') != STATUS_RESOLVED:
            continue
            
        # Check if ticket is from our group
        if ticket.get('group_id') != GROUP_ID:
            continue
            
        # Check if ticket was actually updated on today's date
        updated_at_str = ticket.get('updated_at')
        if not updated_at_str:
            continue
            
        try:
            updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ").date()
            if updated_at == today:
                filtered_tickets.append(ticket)
        except ValueError:
            print(f"⚠️ Could not parse updated_at for ticket {ticket.get('id')}: {updated_at_str}")
    
    print(f"✅ Filtered to {len(filtered_tickets)} resolved tickets from group {GROUP_ID} for {today}")
    return filtered_tickets

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
    
    if not tickets:
        print("⚠️ No tickets to sync - skipping database sync")
        return True
    
    # Use the enhanced service to sync the actual tickets found
    today = datetime.now().date()
    
    # Process each ticket and create closure records
    closure_count = 0
    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
            
        responder_id = ticket.get('responder_id')
        if not responder_id:
            continue
            
        ticket_id = ticket.get('id')
        if not ticket_id:
            continue
            
        # Create or update ticket closure record
        try:
            # First, try to find a mapped user for this Freshworks ID
            mapping = FreshworksUserMapping.query.filter_by(
                freshworks_user_id=responder_id
            ).first()
            
            user_id = None
            if mapping and mapping.user_id:
                user_id = mapping.user_id
                print(f"✅ Found mapped user for Freshworks ID {responder_id}: {mapping.freshworks_username}")
            else:
                print(f"⚠️ No mapped user found for Freshworks ID {responder_id}")
                # Skip tickets from unmapped users for now
                continue
            
            # Check if closure already exists for this user and date
            existing_closure = TicketClosure.query.filter_by(
                user_id=user_id,
                date=today
            ).first()
            
            if existing_closure:
                # Update existing closure with additional ticket
                ticket_numbers = []
                if existing_closure.ticket_numbers:
                    try:
                        ticket_numbers = json.loads(existing_closure.ticket_numbers)
                    except:
                        ticket_numbers = []
                
                if str(ticket_id) not in ticket_numbers:
                    ticket_numbers.append(str(ticket_id))
                    existing_closure.tickets_closed = len(ticket_numbers)
                    existing_closure.ticket_numbers = json.dumps(ticket_numbers)
                    existing_closure.updated_at = datetime.utcnow()
                    closure_count += 1
            else:
                # Create new closure record
                closure = TicketClosure(
                    user_id=user_id,  # Use the mapped user ID
                    freshworks_user_id=responder_id,
                    date=today,
                    tickets_closed=1,
                    ticket_numbers=json.dumps([str(ticket_id)]),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(closure)
                closure_count += 1
                
        except Exception as e:
            print(f"⚠️ Error processing ticket {ticket_id}: {e}")
            continue
    
    # Note: User linking is now handled during ticket processing above
    print(f"✅ User linking completed during ticket processing")
    
    # Commit all changes
    try:
        db.session.commit()
        print(f"✅ Successfully synced {closure_count} ticket closures to database")
        
        # Update sync metadata
        metadata = TicketSyncMetadata.query.filter_by(sync_date=today).first()
        if metadata:
            metadata.sync_count += 1
            metadata.tickets_processed += len(tickets)
            metadata.last_sync_time = datetime.utcnow()
        else:
            metadata = TicketSyncMetadata(
                sync_date=today,
                sync_count=1,
                tickets_processed=len(tickets),
                last_sync_time=datetime.utcnow()
            )
            db.session.add(metadata)
        
        db.session.commit()
        print(f"✅ Updated sync metadata: {metadata.sync_count} syncs, {metadata.tickets_processed} tickets")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error committing ticket closures: {e}")
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
            print(f"📅 Target Date: {datetime.now().date()}")
            print(f"🎯 Group ID: {GROUP_ID}")
            print(f"✅ Status Resolved: {STATUS_RESOLVED}")
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
            print("\n🎟️ Fetching tickets from Freshworks API...")
            tickets = get_todays_tickets()
            print(f"📊 Retrieved {len(tickets)} ticket(s) updated today.")
            
            if tickets:
                print("📋 Sample tickets:")
                for i, ticket in enumerate(tickets[:3]):  # Show first 3 tickets
                    print(f"  {i+1}. Ticket ID: {ticket.get('id')}, Status: {ticket.get('status')}, Group: {ticket.get('group_id')}, Responder: {ticket.get('responder_id')}")
                if len(tickets) > 3:
                    print(f"  ... and {len(tickets) - 3} more tickets")
            else:
                print("⚠️ No tickets found - this might indicate:")
                print("   - No tickets were updated today")
                print("   - No tickets match the group ID or status criteria")
                print("   - API connection issues")
                print("   - Date/time zone issues")
            
            # Generate summary file (original functionality)
            print("\n📝 Generating summary file...")
            summarize_closed_by_responder(tickets, id_name_map)
            
            # Sync to database for YAM dashboard with ticket numbers
            print("\n💾 Syncing to database...")
            success = sync_ticket_closures_to_db(tickets, id_name_map)
            
            if success:
                print("\n🎉 Enhanced leaderboard sync completed successfully!")
                print("📊 Data is now available in the YAM Dashboard Daily Ticket Closures graph")
                print("🎫 Ticket numbers are now stored and can be viewed in user detail modals")
                
                # Invalidate frontend cache to ensure fresh data is displayed
                try:
                    import requests
                    # Clear the ticket closure cache to force fresh data fetch
                    cache_clear_response = requests.post('http://localhost:5000/api/tickets/invalidate-cache', 
                                                       timeout=5)
                    if cache_clear_response.status_code == 200:
                        print("✅ Frontend cache invalidated - fresh data will be displayed")
                    else:
                        print("⚠️ Cache invalidation failed, but data sync was successful")
                except Exception as e:
                    print(f"⚠️ Cache invalidation error (non-critical): {e}")
                
                # Emit WebSocket event to notify frontend of sync completion
                try:
                    socket_emit_response = requests.post('http://localhost:5000/api/tickets/emit-sync-complete', 
                                                       json={'sync_type': 'leaderboard', 'timestamp': datetime.now().isoformat()},
                                                       timeout=5)
                    if socket_emit_response.status_code == 200:
                        print("✅ WebSocket event emitted - frontend notified of sync completion")
                    else:
                        print("⚠️ WebSocket emit failed, but data sync was successful")
                except Exception as e:
                    print(f"⚠️ WebSocket emit error (non-critical): {e}")
                
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
        import traceback
        traceback.print_exc()

def loop(interval_minutes=60):
    """Continuously run the leaderboard sync every `interval_minutes`. Displays a live countdown in the terminal."""
    print(f"🔄 Starting continuous sync loop with {interval_minutes}-minute intervals")
    print("=" * 60)
    
    while True:
        try:
            start_time = datetime.now()
            print(f"\n🚀 Starting sync at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            main()
            
            # Calculate how long the sync took and determine remaining time until next run
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = max(0, interval_minutes * 60 - elapsed)
            next_run = datetime.now() + timedelta(seconds=sleep_time)
            
            print(f"\n⏰ Next sync scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️ Sync took {elapsed:.1f} seconds, waiting {int(sleep_time)} seconds until next sync")
            print("=" * 60)
            
            # Enhanced live countdown with progress bar
            if sleep_time > 0:
                print("⏳ Live countdown to next sync:")
                for remaining in range(int(sleep_time), 0, -1):
                    hrs, rem = divmod(remaining, 3600)
                    mins, secs = divmod(rem, 60)
                    
                    # Calculate progress percentage
                    progress = ((interval_minutes * 60 - remaining) / (interval_minutes * 60)) * 100
                    progress_bar_length = 30
                    filled_length = int(progress_bar_length * progress / 100)
                    bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
                    
                    # Clear line and show enhanced countdown
                    print(f"\r⏳ [{bar}] {hrs:02d}:{mins:02d}:{secs:02d} remaining | {progress:.1f}% complete", end='', flush=True)
                    
                    # Add a small indicator every 10 seconds
                    if remaining % 10 == 0:
                        print(f" | ⏰ {next_run.strftime('%H:%M:%S')}", end='', flush=True)
                    
                    time.sleep(1)
                
                print()  # ensure newline after countdown completes
                print("🔄 Starting next sync cycle...")
            else:
                print("⚡ No wait time - starting next sync immediately")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user - exiting leaderboard sync loop.")
            break
        except Exception as e:
            print(f"\n❌ Error in sync loop: {e}")
            print("🔄 Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Freshworks Leaderboard Sync - Continuous")
    parser.add_argument('--interval', type=int, default=60, help='Interval between syncs in minutes (default: 60)')
    args = parser.parse_args()
    try:
        loop(args.interval)
    except KeyboardInterrupt:
        print("\n👋 Exiting leaderboard sync loop.")
