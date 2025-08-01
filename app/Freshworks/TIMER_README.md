# 🕐 YAM Leaderboard Auto-Timer

## Overview
**AUTOMATIC** real-time timer and monitoring system for the Freshworks Leaderboard sync process. **No user interaction required** - starts automatically with the server.

## 🚀 Auto-Start Features
- ✅ **Automatic startup** with server.bat
- ✅ **No user interaction** required
- ✅ **Optimal 60-minute intervals** for maximum efficiency
- ✅ **Background operation** (minimized window)
- ✅ **Real-time countdown** to next sync
- ✅ **Progress bar** showing sync progress
- ✅ **Status indicators** (Ready/Approaching/Waiting)
- ✅ **Auto-cleanup** on server shutdown

## 🎯 How It Works

### Automatic Startup
When you run `server.bat`, the leaderboard timer automatically starts with:
- **60-minute sync intervals** (optimal for Freshworks API)
- **Background operation** (minimized window)
- **No user prompts** or configuration needed
- **Automatic cleanup** when server stops

### Timer Window
- Look for **"YAM Leaderboard Timer"** in your Windows taskbar
- Window is minimized by default
- Click to view real-time countdown and status
- Press Ctrl+C in timer window to stop manually

## 📊 Timer Display
```
🕐 YAM Leaderboard Auto-Timer
==================================================
⏰ Auto-Started: 2025-08-01 07:47:13
🔄 Sync Interval: 60 minutes (optimal)
🎯 Mode: Automatic (no user interaction)
==================================================
📊 Last Sync: 2025-08-01 14:37:25
⏱️ Time Since Last: 9 minutes ago
🔄 Sync Count Today: 2
🎫 Tickets Processed: 100
==================================================
⏰ Next Sync: 2025-08-01 15:37:25
⏳ Time Remaining: 00:50:12
📈 Progress: [████████████████████████████░░░░] 75.0%
🟡 Status: Approaching sync time
==================================================
💡 Press Ctrl+C to exit
💡 Timer runs automatically - no action needed
```

## 🎮 Manual Control (Optional)

### Quick Status Check
```bash
python app/Freshworks/sync_timer.py --quick
```

### Manual Timer Start
```bash
python app/Freshworks/auto_timer.py
```

### Manual Leaderboard Sync
```bash
python app/Freshworks/leaderboard.py --interval 60
```

## 🔧 Server Integration

### Automatic Startup
The timer is automatically integrated into `server.bat`:
1. **Server starts** → Timer starts automatically
2. **60-minute intervals** → Optimal for API efficiency
3. **Background operation** → No interference with server
4. **Server stops** → Timer stops automatically

### Status Indicators
- 🟢 **Ready for sync** (less than 5 minutes)
- 🟡 **Approaching sync time** (less than 30 minutes)
- 🔴 **Waiting for sync** (more than 30 minutes)

## 📈 Efficiency Features

### Optimal Settings
- **60-minute intervals** - Balances freshness with API efficiency
- **Background operation** - No interference with server performance
- **Auto-cleanup** - Proper shutdown when server stops
- **Error recovery** - Automatic retry on failures

### Real-time Updates
- Updates every 10 seconds
- Shows current time, last sync, and next sync
- Displays sync count and tickets processed
- Progress bar with percentage completion

## 🎯 Usage Examples

### Normal Operation (Recommended)
```bash
# Just run the server - timer starts automatically
server.bat
```

### Check Timer Status
```bash
# Quick status check
python app/Freshworks/sync_timer.py --quick
```

### Manual Timer (if needed)
```bash
# Start manual timer
python app/Freshworks/auto_timer.py
```

## 🚨 Troubleshooting

### Timer Not Starting
1. Check if `server.bat` is running from the correct directory
2. Look for "YAM Leaderboard Timer" in Windows taskbar
3. Check Windows Task Manager for Python processes

### Timer Window Missing
1. Check Windows taskbar for minimized window
2. Look for "YAM Leaderboard Timer" process
3. Restart server if needed

### Sync Issues
1. Check Freshworks API connectivity
2. Verify user mappings in `IDs.txt`
3. Check database connectivity
4. Review server logs for errors

## 🎉 Benefits

### For Users
- ✅ **Zero configuration** required
- ✅ **Automatic operation** - set and forget
- ✅ **Real-time monitoring** available
- ✅ **No interference** with server operation

### For System
- ✅ **Optimal API usage** (60-minute intervals)
- ✅ **Background operation** (minimal resource usage)
- ✅ **Automatic cleanup** (proper shutdown)
- ✅ **Error recovery** (automatic retry)

## 📝 Technical Details

### Files
- `server.bat` - Main server startup (includes timer)
- `auto_timer.py` - Standalone auto timer
- `sync_timer.py` - Manual timer with options
- `leaderboard.py` - Main sync script with timer

### Process Management
- Timer runs as separate Windows process
- Minimized window for background operation
- Automatic cleanup on server shutdown
- Error recovery and retry logic

### Database Integration
- Reads sync metadata from database
- Shows real-time sync statistics
- Tracks sync count and tickets processed
- Monitors last sync time and next sync availability 