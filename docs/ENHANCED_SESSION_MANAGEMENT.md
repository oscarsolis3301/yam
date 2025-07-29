# Enhanced Session Management for YAM

This document describes the enhanced session management system in YAM that allows multiple sessions from the same user and prevents infinite loading errors after server restarts.

## Overview

The enhanced session management system addresses the common issue where users experience infinite loading errors after server restarts due to session conflicts. It allows multiple concurrent sessions from the same user and provides better session conflict resolution.

## Key Features

### 🔀 Multiple Sessions Support
- **Multiple browser tabs/windows**: Users can log in with the same account in multiple browser tabs or windows
- **Concurrent sessions**: All sessions remain active simultaneously
- **Session isolation**: Each session operates independently without conflicts

### 🛡️ Session Conflict Resolution
- **Automatic conflict detection**: System detects and resolves session conflicts
- **Session re-initialization**: Damaged sessions are automatically repaired
- **Graceful degradation**: System continues working even with session issues

### ⏰ Extended Session Lifetime
- **4-hour sessions**: When multiple sessions are enabled, sessions last 4 hours instead of 2
- **Activity-based renewal**: Sessions are automatically renewed with user activity
- **Flexible timeout**: Different timeout periods for different session modes

### 🔄 Enhanced Server Restart Handling
- **No infinite loading**: Server restarts no longer cause infinite loading errors
- **Automatic session clearing**: Old sessions are properly cleared on restart
- **Seamless re-authentication**: Users can log in immediately after restart

## How to Enable Multiple Sessions

### Method 1: Using Enhanced Server.bat (Recommended)
```bash
# Run the enhanced server.bat file
app/server.bat
```

The enhanced `server.bat` automatically:
- Enables multiple sessions mode
- Sets up session conflict resolution
- Creates necessary marker files
- Starts the server with enhanced session management

### Method 2: Manual Server Start
```bash
# Start server with multiple sessions enabled
python app/server.py --allow-multiple-sessions --debug
```

### Method 3: Environment Variables
```bash
# Set environment variables
set YAM_ALLOW_MULTIPLE_SESSIONS=1
set YAM_SESSION_CONFLICT_RESOLUTION=1

# Start server normally
python app/server.py --debug
```

## Configuration Options

### Environment Variables
- `YAM_ALLOW_MULTIPLE_SESSIONS=1`: Enables multiple sessions mode
- `YAM_SESSION_CONFLICT_RESOLUTION=1`: Enables session conflict resolution

### Command Line Arguments
- `--allow-multiple-sessions`: Enables multiple sessions mode
- `--debug`: Enables debug mode with hot reloading

### Session Lifetime
- **Single session mode**: 2 hours
- **Multiple sessions mode**: 4 hours

## Testing Multiple Sessions

### Using the Test Script
```bash
# Run the test script to verify multiple sessions work
python scripts/test_multiple_sessions.py
```

The test script verifies:
- Multiple login sessions
- Session status checking
- Protected endpoint access
- Session activity tracking
- Proper logout functionality

### Manual Testing
1. Start the server with multiple sessions enabled
2. Open two browser tabs/windows
3. Log in with the same user in both
4. Verify both sessions work independently
5. Restart the server
6. Verify you can log in immediately without infinite loading

## Session Management Features

### Automatic Session Health Checks
- **Session validation**: Each request validates session health
- **Automatic repair**: Damaged sessions are automatically repaired
- **Graceful handling**: System continues working even with session issues

### Session Activity Tracking
- **Activity monitoring**: Tracks user activity across all sessions
- **Automatic renewal**: Sessions are renewed with user activity
- **Timeout management**: Sessions timeout after inactivity

### Session Conflict Resolution
- **Conflict detection**: Automatically detects session conflicts
- **Session re-initialization**: Repairs damaged session data
- **User presence management**: Manages user online/offline status

## Troubleshooting

### Common Issues

#### Infinite Loading After Server Restart
**Problem**: Users get stuck in infinite loading after server restart
**Solution**: Use the enhanced `server.bat` or start with `--allow-multiple-sessions`

#### Session Conflicts
**Problem**: Multiple sessions from same user cause conflicts
**Solution**: Multiple sessions mode automatically resolves conflicts

#### Session Expiration
**Problem**: Sessions expire too quickly
**Solution**: Multiple sessions mode extends session lifetime to 4 hours

### Debug Commands

#### Check Session Status
```bash
# Check current session status
curl http://localhost:5000/api/session/time-remaining
```

#### Force Session Reset
```bash
# Force reset all sessions
curl -X POST http://localhost:5000/force-logout
```

#### Check Server Configuration
```bash
# Check server configuration
curl http://localhost:5000/api/server-info
```

### Log Analysis
Look for these log messages:
- `"Multiple sessions mode enabled"`
- `"Session conflict resolution enabled"`
- `"Re-initialized session for user X (multiple sessions mode)"`
- `"Session conflict resolved"`

## Best Practices

### For Development
1. **Always use enhanced server.bat**: It automatically enables multiple sessions
2. **Test with multiple tabs**: Verify multiple sessions work correctly
3. **Monitor logs**: Check for session-related messages
4. **Use test script**: Run the test script to verify functionality

### For Production
1. **Enable multiple sessions**: Use `--allow-multiple-sessions` flag
2. **Monitor session health**: Check session status regularly
3. **Set appropriate timeouts**: Adjust session lifetime as needed
4. **Handle session cleanup**: Ensure proper session cleanup on shutdown

## Technical Details

### Session Storage
- **Filesystem-based**: Sessions stored in `sessions/` directory
- **Persistent storage**: Sessions survive server restarts
- **Automatic cleanup**: Stale sessions are automatically cleaned up

### Session Validation
- **Server startup time**: Sessions are validated against server startup time
- **Activity timestamps**: Sessions are validated against last activity
- **User presence**: Sessions are validated against user online status

### Session Conflict Resolution
- **Session re-initialization**: Damaged sessions are automatically repaired
- **Data integrity**: Session data is validated and repaired
- **Graceful degradation**: System continues working with session issues

## Migration from Single Sessions

If you're upgrading from single session mode:

1. **Backup sessions**: Backup existing session data if needed
2. **Enable multiple sessions**: Use enhanced server.bat or command line flag
3. **Test functionality**: Verify multiple sessions work correctly
4. **Monitor performance**: Check for any performance impact
5. **Update documentation**: Update any custom documentation

## Performance Considerations

### Memory Usage
- **Multiple sessions**: Slightly higher memory usage with multiple sessions
- **Session cleanup**: Automatic cleanup prevents memory leaks
- **Efficient storage**: Sessions are stored efficiently on filesystem

### Network Performance
- **Session validation**: Minimal network overhead for session validation
- **Activity tracking**: Lightweight activity tracking
- **Conflict resolution**: Efficient conflict resolution algorithms

## Security Considerations

### Session Security
- **Secure cookies**: Sessions use secure cookie settings
- **Session isolation**: Sessions are properly isolated
- **Automatic logout**: Sessions automatically logout on timeout

### Access Control
- **Authentication required**: All protected endpoints require authentication
- **Session validation**: Sessions are validated on each request
- **User presence**: User online status is tracked and validated

## Conclusion

The enhanced session management system provides a robust solution for handling multiple user sessions and preventing infinite loading errors. It's designed to be:

- **User-friendly**: Seamless experience for users
- **Developer-friendly**: Easy to enable and configure
- **Production-ready**: Robust and reliable for production use
- **Backward compatible**: Works with existing single session setups

By using the enhanced session management system, you can eliminate the infinite loading errors that occur after server restarts and provide a better user experience with support for multiple concurrent sessions. 