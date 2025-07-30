# Ticket Closure Tracking System

This system integrates real Freshworks ticket closure data into the YAM Dashboard, replacing dummy data with actual daily performance metrics.

## Features

- **Hourly Updates**: Fetches actual ticket closure data from Freshworks API every hour (not real-time)
- **Rate Limiting**: Prevents excessive API calls with 1-hour minimum between syncs
- **User Mapping**: Maps Freshworks user IDs to local users using `app/Freshworks/IDs.txt`
- **Persistent Storage**: Stores daily closure data in SQLite database with single entry per user per day
- **Dashboard Integration**: Displays real user names and ticket counts in YAM Daily Ticket Closures graph
- **Time Periods**: View data for Today, Yesterday, This Week, and This Month
- **Smart Sync Button**: Shows sync availability and rate limiting status

## Setup Instructions

### 1. Environment Variables

Ensure your `.env` file contains:
```
FRESH_API=your_freshworks_api_key
FRESH_ENDPOINT=https://your-domain.freshservice.com/api/v2/
```

### 2. Initialize the System

Run the initialization script:
```bash
python scripts/init_ticket_tracking.py
```

This will:
- Create the necessary database tables
- Sync user mappings from `IDs.txt`
- Import today's and yesterday's ticket closure data

### 3. Set Up Automated Sync (Optional)

For automatic hourly updates, add a cron job that runs more frequently (the script internally handles rate limiting):
```bash
# Run every hour during business hours (8 AM to 6 PM)
0 8-18 * * * cd /path/to/yam && python scripts/sync_daily_closures.py >> logs/ticket_sync.log 2>&1

# Alternative: Run every 30 minutes (script will respect hourly rate limits)
*/30 * * * * cd /path/to/yam && python scripts/sync_daily_closures.py >> logs/ticket_sync.log 2>&1
```

## Usage

### YAM Dashboard

1. Navigate to the YAM Dashboard
2. View the "Daily Ticket Closures" section
3. Real user names and actual ticket counts will be displayed
4. Use time period buttons to view different date ranges
5. Click the sync button (🔄) to manually refresh data

### Admin Features (Non-User Roles Only)

Admins, managers, and developers will see additional features:

1. **Admin Stats Button (⚙️)**: Click to open detailed sync statistics modal
2. **Comprehensive Dashboard**: View sync history, database stats, and recent activity
3. **Force Sync**: Bypass hourly rate limiting for immediate data refresh
4. **User Mapping Management**: Refresh Freshworks user mappings
5. **Database Insights**: See total records, mapped users, and sync history

#### Admin Modal Features

The admin statistics modal provides:

**Sync Status Section:**
- Last sync time and next available sync time
- Number of syncs performed today
- Total tickets processed today

**Database Statistics:**
- Total closure records in database
- Number of mapped Freshworks users
- Days with closure data available
- Total sync operations performed

**Recent Activity:**
- Last 10 sync operations with timestamps
- Tickets processed per sync
- Time since each sync operation

**Admin Actions:**
- **Force Sync**: Immediately sync data bypassing hourly rate limit
- **Refresh User Mappings**: Update Freshworks user ID mappings from IDs.txt
- **Export Data**: Export database statistics (coming soon)

### API Endpoints

The system provides several API endpoints:

- `GET /api/tickets/closures/today` - Today's ticket closures
- `GET /api/tickets/closures/period?period=week` - Period-based closures
- `POST /api/tickets/sync` - Manual sync trigger (respects hourly rate limiting)
- `GET /api/tickets/sync-status` - Check sync status and rate limiting
- `GET /api/tickets/top-performers` - Top performers for a date
- `GET /api/tickets/stats` - Overall statistics

#### Admin-Only Endpoints
- `GET /api/tickets/admin-stats` - Comprehensive admin statistics and database info
- `POST /api/tickets/force-sync` - Force sync bypassing rate limits (admin only)

### Rate Limiting Behavior

- **Hourly Sync Limit**: Only one sync per hour per date
- **Server Restart Safe**: Rate limiting persists across server restarts by checking database
- **Smart Button**: Sync button shows clock icon when rate limited
- **API Response**: Returns rate limiting info including minutes until next sync
- **Persistent Tracking**: Database stores sync timestamps and prevents duplicate calls
- **Force Override**: Admins can bypass rate limits using force sync feature

#### How Rate Limiting Works
1. Every sync attempt checks `ticket_sync_metadata` table for last sync time
2. If less than 1 hour has passed, sync is blocked (unless force sync)
3. Rate limiting persists even if server restarts because it's database-based
4. Each successful sync updates the metadata table with new timestamp
5. Rate limiting is per-date, so each date has independent hourly limits

### Manual Data Sync

To manually sync data for a specific date:
```python
from app.utils.freshworks_service import freshworks_service
from datetime import date

# Sync specific date
freshworks_service.sync_daily_closures_with_tickets(date(2025, 1, 15))

# Sync user mappings
freshworks_service.sync_user_mappings()
```

## Database Schema

### ticket_closure
- `id` - Primary key
- `user_id` - References local user
- `freshworks_user_id` - Freshworks responder ID
- `date` - Date of closures
- `tickets_closed` - Number of tickets closed
- `created_at` / `updated_at` - Timestamps

### freshworks_user_mapping
- `id` - Primary key
- `user_id` - References local user
- `freshworks_user_id` - Freshworks user ID (unique)
- `freshworks_username` - Name from IDs.txt
- `created_at` / `updated_at` - Timestamps

### ticket_sync_metadata
- `id` - Primary key
- `sync_date` - Date being synced (unique)
- `last_sync_time` - Timestamp of last sync
- `sync_count` - Number of times synced for this date
- `tickets_processed` - Total tickets processed
- `created_at` / `updated_at` - Timestamps

## User Mapping

The system uses `app/Freshworks/IDs.txt` to map Freshworks user IDs to names:
```
Oscar S. - 12345
AJ Thompson - 67890
Cole O'Grady - 11111
```

The mapping logic:
1. Tries exact username match
2. Falls back to partial name matching (e.g., "Oscar S." → "oscar.solis")
3. Creates mapping entries for successful matches

## Troubleshooting

### No Data Displayed
1. Check that Freshworks API credentials are correct
2. Verify `IDs.txt` file exists and has correct format
3. Run manual sync: click sync button or run init script
4. Check browser console for API errors

### API Errors
1. Verify Freshworks API endpoint URL
2. Check API rate limits
3. Ensure GROUP_ID (18000294963) is correct for your organization

### User Mapping Issues
1. Update `IDs.txt` with correct Freshworks user IDs and names
2. Run user mapping sync: `freshworks_service.sync_user_mappings()`
3. Check that local usernames match expected patterns

## File Structure

```
app/
├── utils/freshworks_service.py     # Main Freshworks integration service
├── blueprints/tickets_api/         # API endpoints
│   ├── __init__.py
│   └── routes.py
├── models/base.py                  # Database models (TicketClosure, FreshworksUserMapping)
├── templates/components/yam/
│   ├── yam_user_tickets_section.html    # UI components
│   └── yam_user_tickets_scripts.html    # Frontend JavaScript
└── Freshworks/
    ├── IDs.txt                     # User ID mappings
    └── leaderboard.py              # Original leaderboard script (reference)

scripts/
├── init_ticket_tracking.py        # Initialization script
└── sync_daily_closures.py         # Daily sync script
```

## Integration Points

This system integrates with:
- **Freshworks API**: Fetches ticket data using same logic as `leaderboard.py`
- **YAM Dashboard**: Replaces dummy data in Daily Ticket Closures graph
- **User System**: Maps Freshworks users to local user accounts
- **Database**: Persistent storage for historical tracking

The graph now shows real user names (e.g., "Oscar S.") with actual ticket closure counts, and the "Top Closer" section displays the user who has closed the most tickets.