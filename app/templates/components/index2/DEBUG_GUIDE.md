# Index2 Debugging Guide

## Overview
This guide helps you identify and resolve issues with Index2 components. The debugging system includes comprehensive error handling, logging, and validation.

## Debug Tools

### 1. Debug Panel
- **Access**: Click the bug icon (🐛) in the bottom-right corner
- **Auto-show**: Automatically appears on localhost/development
- **Features**:
  - Component Status
  - Error Log
  - Performance Metrics
  - Network Status

### 2. Test Page
- **URL**: `/test-index2`
- **Purpose**: Isolated testing environment for Index2 components
- **Features**:
  - Test controls for all components
  - Real-time component status
  - Debug information display

## Common Issues and Solutions

### 1. Component Not Loading
**Symptoms**: Component doesn't appear or function
**Debug Steps**:
1. Check browser console for errors
2. Verify component element exists in DOM
3. Check if required dependencies are loaded
4. Use debug panel to see component status

**Solutions**:
```javascript
// Check if component is loaded
console.log('MainLayout:', !!window.mainLayout);
console.log('OutageBanner:', !!window.outageBanner);
console.log('WelcomeBanner:', !!window.welcomeBanner);
console.log('UsersOnline:', !!window.usersOnline);
```

### 2. CSS Conflicts
**Symptoms**: Styling issues, components not displaying correctly
**Debug Steps**:
1. Check debug panel for CSS conflict warnings
2. Inspect element styles in browser dev tools
3. Look for `!important` declarations

**Solutions**:
```css
/* Add more specific selectors */
.index2-component .specific-element {
    /* styles */
}

/* Use CSS custom properties for theming */
:root {
    --index2-primary: #667eea;
    --index2-secondary: #764ba2;
}
```

### 3. JavaScript Errors
**Symptoms**: Console errors, functionality not working
**Debug Steps**:
1. Check browser console for error messages
2. Use debug panel error log
3. Verify all required functions exist

**Solutions**:
```javascript
// Add error boundaries
try {
    // Component code
} catch (error) {
    console.error('Component error:', error);
    // Fallback behavior
}
```

### 4. WebSocket Issues
**Symptoms**: Real-time updates not working
**Debug Steps**:
1. Check network status in debug panel
2. Verify WebSocket connection
3. Check server-side WebSocket implementation

**Solutions**:
```javascript
// Check WebSocket status
if (window.socketState && window.socketState.socket) {
    console.log('WebSocket connected:', window.socketState.socket.connected);
} else {
    console.warn('WebSocket not available');
}
```

## Debugging Commands

### Console Commands
```javascript
// Show debug information
showDebugInfo();

// Toggle debug panel
toggleDebugPanel();

// Get component debug info
getMainLayoutDebugInfo();

// Test components
testOutageBanner();
testToast('success');
```

### Browser Dev Tools
1. **Elements Tab**: Check DOM structure
2. **Console Tab**: View error logs and debug output
3. **Network Tab**: Monitor API calls and WebSocket connections
4. **Performance Tab**: Check for performance issues

## Component-Specific Debugging

### Outage Banner
```javascript
// Check outage banner status
if (window.outageBanner) {
    console.log('Outage banner debug info:', window.outageBanner.getDebugInfo());
}

// Test outage banner
showOutageBanner('Test Outage', 'Test Description');
hideOutageBanner();
```

### Welcome Banner
```javascript
// Check welcome banner status
if (window.welcomeBanner) {
    console.log('Welcome banner debug info:', window.welcomeBanner.getDebugInfo());
}

// Test time updates
// Time updates automatically every second
```

### Users Online
```javascript
// Check users online status
if (window.usersOnline) {
    console.log('Users online debug info:', window.usersOnline.getDebugInfo());
}

// Refresh users
if (window.usersOnline && window.usersOnline.refreshUsers) {
    window.usersOnline.refreshUsers();
}
```

## Performance Monitoring

### Memory Usage
```javascript
// Check memory usage
if (window.performance && window.performance.memory) {
    const memory = window.performance.memory;
    console.log('Memory usage:', {
        used: Math.round(memory.usedJSHeapSize / 1024 / 1024) + 'MB',
        total: Math.round(memory.totalJSHeapSize / 1024 / 1024) + 'MB',
        limit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024) + 'MB'
    });
}
```

### Load Times
```javascript
// Check page load performance
if (window.performance && window.performance.timing) {
    const timing = window.performance.timing;
    console.log('Load times:', {
        loadTime: timing.loadEventEnd - timing.navigationStart + 'ms',
        domReady: timing.domContentLoadedEventEnd - timing.navigationStart + 'ms'
    });
}
```

## Error Recovery

### Automatic Recovery
- Components automatically retry failed operations
- Fallback behaviors for missing dependencies
- Graceful degradation for network issues

### Manual Recovery
```javascript
// Reinitialize components
if (window.mainLayout) {
    window.mainLayout.init();
}

// Clear error logs
if (window.index2Debugger) {
    window.index2Debugger.clearLogs();
}
```

## Testing Checklist

### Before Deployment
- [ ] All components load without errors
- [ ] Debug panel shows no critical errors
- [ ] WebSocket connections work
- [ ] Toast notifications function
- [ ] User interactions work properly
- [ ] Responsive design works on mobile
- [ ] Performance metrics are acceptable

### After Deployment
- [ ] Monitor error logs
- [ ] Check performance metrics
- [ ] Verify real-time updates
- [ ] Test user interactions
- [ ] Monitor memory usage

## Troubleshooting Tips

1. **Clear Browser Cache**: Hard refresh (Ctrl+F5) to clear cached files
2. **Check Network**: Ensure all CDN resources load properly
3. **Disable Extensions**: Some browser extensions can interfere
4. **Test in Incognito**: Isolate issues from browser extensions/cache
5. **Check Console**: Always check browser console for errors first

## Support

If issues persist after following this guide:
1. Collect debug information using `showDebugInfo()`
2. Check the error log in the debug panel
3. Note the specific error messages and steps to reproduce
4. Check browser console for additional details

## Debug Panel Features

### Component Status
- Shows which components are loaded
- Displays initialization status
- Highlights missing or failed components

### Error Log
- Captures all JavaScript errors
- Shows error timestamps and details
- Displays stack traces for debugging

### Performance Metrics
- Page load times
- Memory usage
- Component initialization times

### Network Status
- WebSocket connection status
- API request monitoring
- Network error tracking 

## Modal Interactivity Issues - FIXED

### Previous Issues
- Modals were not interactive due to z-index conflicts
- Missing modal backdrop
- Incomplete Bootstrap integration
- No click-outside-to-close functionality

### Solutions Implemented

#### 1. Enhanced Modal Structure
```html
<!-- User Details Modal -->
<div class="modal fade" id="userDetailsModal" tabindex="-1" aria-labelledby="userDetailsModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="userDetailsModalLabel">User Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body" id="userDetailsContent">
                <!-- User details will be populated here -->
            </div>
        </div>
    </div>
</div>

<!-- Custom Modal Backdrop -->
<div id="modalBackdrop" class="modal-backdrop" style="display: none;"></div>
```

#### 2. Proper Z-Index Management
```css
.modal {
    z-index: 1055 !important;
    pointer-events: auto !important;
}

.modal-dialog {
    z-index: 1056 !important;
    pointer-events: auto !important;
}

.modal-content {
    z-index: 1057 !important;
    pointer-events: auto !important;
}

.modal-backdrop {
    z-index: 1054 !important;
    pointer-events: auto !important;
}
```

#### 3. Enhanced JavaScript Functionality
- Proper Bootstrap integration with fallback
- Click outside to close
- Escape key to close
- Body scroll locking
- Smooth animations

#### 4. Global Modal Utilities
```javascript
// Show any modal
window.showModal('modalId', content);

// Hide any modal
window.hideModal('modalId');

// Test modal functionality
window.testModal();
```

### Testing Modal Functionality

#### Console Commands
```javascript
// Test user modal
testUserModal();

// Test global modal
testModal();

// Close modal
testModalClose();

// Check modal elements
console.log('Modal:', document.getElementById('userDetailsModal'));
console.log('Backdrop:', document.getElementById('modalBackdrop'));
```

#### Manual Testing Steps
1. Click on any user in the users list
2. Verify modal opens with user details
3. Test close button (X)
4. Test clicking outside modal (backdrop)
5. Test pressing Escape key
6. Verify modal closes properly
7. Test global modal with test button

#### Debug Panel
- Check "Component Status" for modal-related errors
- Monitor "Error Log" for modal interaction issues
- Verify "Network Status" for API calls

### Common Modal Issues and Solutions

#### Modal Not Opening
**Check:**
1. Bootstrap JS loaded properly
2. Modal element exists in DOM
3. No JavaScript errors in console
4. Z-index conflicts resolved

#### Modal Not Interactive
**Check:**
1. `pointer-events: auto` on modal elements
2. Proper z-index stacking
3. No overlapping elements
4. Event handlers properly attached

#### Modal Not Closing
**Check:**
1. Close button event handlers
2. Backdrop click handlers
3. Escape key handlers
4. Bootstrap modal instance

#### Modal Styling Issues
**Check:**
1. CSS specificity conflicts
2. Bootstrap CSS loaded
3. Custom styles not overriding
4. Responsive design issues 