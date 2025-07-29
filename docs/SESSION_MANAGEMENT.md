# YAM Session Management

This document describes the session management system in YAM and how to handle common issues.

## Overview

YAM uses Flask-Login with filesystem-based sessions for user authentication. Sessions are stored in the `sessions/` directory and have a 2-hour lifetime.

## Session Configuration

- **Session Type**: Filesystem-based sessions
- **Lifetime**: 2 hours (configurable)
- **Storage**: `sessions/` directory
- **Cookie Name**: `yam_session`

## Common Issues and Solutions

### 1. Redirect Loop After Server Restart

**Problem**: After restarting the server, users get stuck in a redirect loop between the main page and login page.

**Cause**: Session data persists but Flask-Login can't properly authenticate the user, causing authentication middleware to reject requests.

**Solutions**:

#### Automatic Fix
The server now automatically detects server restarts and clears stale sessions:
- Server startup time is tracked and compared with session creation time
- Stale sessions are automatically cleared on first request
- Force session reset markers are created during server startup

#### Manual Fix
If automatic clearing doesn't work:

1. **Use the session clearance tool**:
   ```bash
   scripts/clear_sessions.bat
   ```

2. **Call the force logout endpoint**:
   ```bash
   curl -X POST http://localhost:5000/force-logout
   ```

3. **Clear browser storage** (if using web browser):
   - Open browser console on login page
   - Run: `window.clearYAMStorage()`
   - Refresh the page

4. **Manual file cleanup**:
   - Delete `sessions/` directory
   - Delete `force_session_reset.txt` if it exists
   - Restart the server

### 2. Session Health Checks

The system includes comprehensive session health checks:

- **Server restart detection**: Sessions created before server startup are invalidated
- **Activity timeout**: Sessions inactive for more than 2 hours are cleared
- **User presence validation**: Users marked as offline are re-authenticated
- **Session data integrity**: Missing session data is automatically initialized

### 3. Debugging Session Issues

#### Debug Endpoints

- **Session Status**: `GET /debug/session`
  - Shows current session data
  - Displays authentication status
  - Shows server startup time
  - Indicates if force reset marker exists

- **Force Logout**: `POST /force-logout`
  - Clears all sessions
  - Creates force reset marker
  - Redirects to login page

- **Health Check**: `GET /api/health`
  - Basic system health
  - Session health status

#### Log Analysis

Look for these log messages:
- `"Invalidating session for user X - server restarted"`
- `"Force session reset marker detected - clearing all sessions"`
- `"Re-authenticated user X from session data"`
- `"Session expired for user X"`

## Session Management Commands

### Server Startup
```bash
# Normal startup with session clearing
app/server.bat

# Manual session clearing before startup
scripts/clear_sessions.bat
```

### Emergency Session Clearing
```bash
# Clear all sessions via API
curl -X POST http://localhost:5000/force-logout

# Admin session clearing (requires admin login)
curl -X POST http://localhost:5000/admin/clear-sessions
```

### Browser Storage Clearing
```javascript
// Clear all YAM-related storage
window.clearYAMStorage();

// Manual clearing
sessionStorage.clear();
localStorage.clear();
```

## Session File Locations

- **Primary**: `sessions/` (project root)
- **Secondary**: `app/sessions/`
- **Instance**: `instance/` (Flask default)
- **Flask-Session**: `flask_session/`

## Best Practices

1. **Always restart the server using `server.bat`** - it includes automatic session cleanup
2. **Use the session clearance tool** if you encounter redirect loops
3. **Check the debug endpoint** (`/debug/session`) to diagnose session issues
4. **Clear browser storage** if using web interface and experiencing issues
5. **Monitor logs** for session-related messages

## Troubleshooting Checklist

If you're experiencing session issues:

- [ ] Restart server using `server.bat`
- [ ] Check `/debug/session` endpoint
- [ ] Run `scripts/clear_sessions.bat`
- [ ] Clear browser storage (`window.clearYAMStorage()`)
- [ ] Check server logs for session messages
- [ ] Verify no stale session files exist
- [ ] Ensure database is accessible

## Technical Details

### Session Middleware Flow

1. **Before Request**:
   - Check for force reset markers
   - Validate server startup time
   - Check session health
   - Update activity timestamps

2. **Authentication Check**:
   - Verify Flask-Login authentication
   - Check session data integrity
   - Re-authenticate if needed
   - Clear invalid sessions

3. **After Request**:
   - Update session activity
   - Mark session as modified
   - Clean up stale sessions periodically

### Force Reset Mechanism

The system uses a `force_session_reset.txt` marker file to force session clearing:

1. Created during server startup
2. Created during force logout
3. Detected by before_request handler
4. Automatically removed after use
5. Forces all sessions to be cleared

This ensures that even if session files persist, they will be invalidated on the next request. 