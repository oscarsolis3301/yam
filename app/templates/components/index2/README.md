# Index2 Components

A clean, minimal implementation of the dashboard components focused on core functionality without CSS conflicts.

## Components

### 1. Outage Banner (`outage_banner.html`)
- Fixed position banner that appears at the top of the page
- Shows active outages with close functionality
- Automatically adjusts main content padding when visible
- Real-time updates via WebSocket
- Clean, minimal styling with no conflicts

### 2. Welcome Banner (`welcome_banner.html`)
- Personalized welcome message with user name
- Real-time date and time display
- Connection status indicator
- User role badge
- Responsive design for all screen sizes

### 3. Users Online (`users_online.html`)
- Displays team members currently online
- Clickable user items that show detailed modal
- Real-time status updates
- Refresh functionality
- User count display
- Clean modal implementation

### 4. Main Layout (`main_layout.html`)
- Combines all components in a clean layout
- Handles global styling and interactions
- Provides utility functions for toasts and loading states
- Responsive design with proper z-index management

## Features

### Clean CSS Architecture
- No conflicting styles
- Scoped CSS within each component
- Proper z-index management
- Responsive design
- Accessibility support

### Interactive Elements
- All buttons and clickable elements work properly
- Modal dialogs function correctly
- Hover and active states
- Proper event handling

### Real-time Updates
- WebSocket integration for live data
- Automatic refresh mechanisms
- Status indicators
- Connection monitoring

### Performance
- Minimal JavaScript
- Efficient DOM manipulation
- Debounced updates
- Clean memory management

## Usage

```html
<!-- In your main template -->
{% from 'components.index2.outage_banner' import render_outage_banner %}
{% from 'components.index2.welcome_banner' import render_welcome_banner %}
{% from 'components.index2.users_online' import render_users_online %}
{% from 'components.index2.main_layout' import render_main_layout %}

{{ render_main_layout(name, current_user) }}
```

## API Endpoints Used

- `/api/outages/active` - Get active outages
- `/api/admin/users/online` - Get online users
- `/api/admin/users/{id}/stats` - Get user statistics

## WebSocket Events

- `outage_created` - New outage created
- `outage_resolved` - Outage resolved
- `online_users_update` - Online users list updated
- `user_status_change` - Individual user status changed

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile responsive
- Accessibility compliant
- Reduced motion support

## Dependencies

- Bootstrap Icons (for icons)
- Bootstrap (for modals)
- Inter font family
- WebSocket connection (via socketState)

## Migration from Original Index

This implementation addresses the issues with the original index components:

1. **CSS Conflicts**: Each component has scoped styles
2. **Non-interactive Elements**: All elements have proper event handlers
3. **Z-index Issues**: Proper layering for modals and overlays
4. **Performance**: Simplified and optimized code
5. **Maintainability**: Clean, modular structure

## Testing

To test the components:

1. Load the page and verify all elements are interactive
2. Test outage banner functionality
3. Verify user list updates and modal functionality
4. Check responsive design on different screen sizes
5. Test WebSocket connectivity and real-time updates 