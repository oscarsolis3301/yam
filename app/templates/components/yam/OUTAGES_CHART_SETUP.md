# Outages Chart Integration

This document explains how the outages chart in YAM.html is connected to the outages data from outages.html.

## Overview

The outages chart in YAM.html now properly displays real outage data from the `/api/admin/outages` endpoint. The integration includes:

1. **Real-time data loading** from the outages API
2. **Chart visualization** using Chart.js
3. **Statistics display** (active, total, average duration)
4. **Current outages list** with detailed information
5. **Time period controls** (3D, 7D, 14D, 30D, Custom)

## Files Modified

### 1. `yam_core_scripts.html`
- Made `outageChart` variable global
- Added better error handling and debugging
- Improved chart initialization

### 2. `yam_data_scripts.html`
- Enhanced `loadOutagesData()` function with better error handling
- Improved `updateOutageStats()` with visual indicators
- Enhanced `updateCurrentOutages()` with better formatting
- Added real-time update functionality
- Added Socket.io integration for live updates

### 3. `yam_chart_and_management_scripts.html`
- Improved `updateOutageChart()` function
- Better data processing for chart visualization
- Enhanced outage overlap detection

## API Integration

The chart connects to the `/api/admin/outages?all=true` endpoint which returns:
```json
[
  {
    "id": 1,
    "title": "Outage Title",
    "description": "Outage Description",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T12:00:00Z",
    "status": "resolved",
    "affected_systems": "System Name"
  }
]
```

## Testing the Integration

### 1. Check Console for Debug Information
Open browser console and look for:
- "YAM Core Scripts: DOM Content Loaded"
- "Found outage chart canvas, initializing..."
- "Outage chart initialized successfully"
- "Loading outages data for period: 7d"
- "Received outages data: [...]"

### 2. Manual Testing Functions
In browser console, you can run:

```javascript
// Test with sample data
testOutageChart();

// Check chart status
checkChartStatus();

// Manually load outages data
loadOutagesData('7d');

// Check if chart is accessible
console.log(outageChart);
```

### 3. Verify Chart Updates
- Click time period buttons (3D, 7D, 14D, 30D)
- Check that chart data updates
- Verify statistics update correctly
- Confirm current outages list shows active outages

## Real-time Updates

The chart automatically updates:
- Every 30 seconds via polling
- Every 10 seconds for real-time updates
- Immediately when Socket.io events are received

## Troubleshooting

### Chart Not Displaying
1. Check console for "Outage chart canvas not found"
2. Verify `#outageChart` element exists in DOM
3. Ensure Chart.js is loaded

### No Data Showing
1. Check console for API errors
2. Verify `/api/admin/outages?all=true` returns data
3. Check network tab for failed requests

### Chart Not Updating
1. Verify `outageChart` variable is global
2. Check that `updateOutageChart()` function is called
3. Ensure data processing is working correctly

## Features

### Chart Visualization
- Line chart showing outage frequency over time
- Responsive design with dark theme
- Smooth animations and transitions
- Hover effects and tooltips

### Statistics Panel
- Active outages count (with color coding)
- Total outages count
- Average resolution time

### Current Outages List
- Real-time display of active outages
- Duration tracking
- Affected systems information
- Visual status indicators

### Time Controls
- Multiple time periods (3D, 7D, 14D, 30D)
- Custom date range selection
- Automatic data refresh

## Future Enhancements

1. **Multiple chart types** (bar, area, pie)
2. **Advanced filtering** (by system, severity, etc.)
3. **Export functionality** (CSV, PDF)
4. **Predictive analytics** (outage patterns)
5. **Integration with other systems** (monitoring tools) 