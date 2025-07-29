# Freshworks Users Linking Dashboard

## Overview

The Freshworks Users Linking Dashboard is a modern, responsive web interface that allows administrators and elevated users to link Freshworks responder IDs to website members and track ticket closures. This dashboard provides comprehensive ticket tracking and user management capabilities.

## Features

### 🔗 User Linking
- **Manual Linking**: Link Freshworks users to website members through an intuitive interface
- **Auto-Linking**: Automatically link users based on username similarity
- **Unlinking**: Remove links between Freshworks users and website members
- **Real-time Updates**: See changes immediately after linking/unlinking

### 📊 Ticket Tracking
- **Total Tickets**: Track total tickets closed by each user
- **Monthly Statistics**: View tickets closed this month
- **Weekly Statistics**: View tickets closed this week
- **Detailed History**: View individual ticket numbers and dates
- **Last Activity**: See when each user last closed tickets

### 🎯 Dashboard Statistics
- **Total Mappings**: Number of Freshworks user mappings
- **Linked Users**: Number of successfully linked users
- **Unlinked Users**: Number of users awaiting linking
- **Total Tickets**: Combined ticket count across all users

### 🔄 Data Management
- **Sync Mappings**: Refresh Freshworks user mappings from the service
- **Auto-Link**: Automatically link unmapped users based on name matching
- **Real-time Refresh**: Update data without page reload

## Access Control

### User Roles
- **Admin**: Full access to all features
- **Elevated Users** (non-user roles): Full access to all features
- **Regular Users**: No access (redirected with error message)

### Security Features
- Role-based access control
- CSRF protection
- Input validation
- Secure API endpoints

## User Interface

### Modern Design
- **Gradient Backgrounds**: Beautiful purple gradient theme
- **Glass Morphism**: Translucent cards with backdrop blur
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Smooth Animations**: Hover effects and transitions
- **Loading States**: Visual feedback during operations

### Interactive Elements
- **Status Badges**: Color-coded linked/unlinked status
- **Action Buttons**: Clear call-to-action buttons
- **Modal Dialogs**: Clean, modern modal interfaces
- **Toast Notifications**: Real-time feedback messages

## API Endpoints

### GET `/freshworks-linking/api/mappings`
Returns all Freshworks user mappings with detailed information.

**Response:**
```json
{
  "success": true,
  "mappings": [
    {
      "id": 1,
      "freshworks_user_id": 18014125885,
      "freshworks_username": "Oscar Solis",
      "user_id": 1,
      "user_info": {
        "id": 1,
        "username": "Oscar",
        "email": "oscar@pdshealth.com",
        "role": "admin"
      },
      "status": "linked",
      "ticket_stats": {
        "total_tickets": 45,
        "this_month": 12,
        "this_week": 3,
        "last_activity": "2025-07-29T10:30:00"
      }
    }
  ],
  "available_users": [...],
  "stats": {
    "total_mappings": 18,
    "linked_count": 15,
    "unlinked_count": 3
  }
}
```

### PUT `/freshworks-linking/api/mappings/<mapping_id>`
Update a Freshworks user mapping (link/unlink users).

**Request:**
```json
{
  "user_id": 1  // null to unlink
}
```

### POST `/freshworks-linking/api/mappings/sync`
Sync Freshworks user mappings from the service.

### POST `/freshworks-linking/api/mappings/auto-link`
Automatically link unmapped users based on username similarity.

### GET `/freshworks-linking/api/tickets/user/<user_id>`
Get detailed ticket information for a specific user.

**Query Parameters:**
- `days`: Number of days to look back (default: 30)

## Database Models

### FreshworksUserMapping
```python
class FreshworksUserMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    freshworks_user_id = db.Column(db.Integer, nullable=False, unique=True)
    freshworks_username = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### TicketClosure
```python
class TicketClosure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freshworks_user_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    tickets_closed = db.Column(db.Integer, nullable=False)
    ticket_numbers = db.Column(db.Text)  # JSON string of ticket numbers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Usage Examples

### Linking Oscar to Admin Account
1. Navigate to the Freshworks Linking Dashboard
2. Find "Oscar Solis" in the mappings table
3. Click the "Link" button
4. Select "Admin" from the dropdown
5. Click "Link User"
6. Oscar's tickets will now be tracked under the Admin account

### Viewing Ticket Details
1. Find a linked user in the mappings table
2. Click "View Details" in the Ticket Statistics column
3. View detailed ticket information including:
   - Individual ticket numbers
   - Daily ticket counts
   - Date ranges
   - User information

### Auto-Linking Users
1. Click the "Auto-Link" button in the dashboard header
2. The system will automatically match unmapped users based on username similarity
3. View the results in the mappings table

## Integration with Existing Systems

### Freshworks Service
The dashboard integrates with the existing `freshworks_service.py` to:
- Sync user mappings from Freshworks
- Match users based on username similarity
- Track ticket closures

### User Management
- Uses existing User model and authentication system
- Respects role-based permissions
- Integrates with existing user profiles

### Ticket Tracking
- Leverages existing TicketClosure model
- Maintains historical ticket data
- Provides comprehensive reporting

## Technical Implementation

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with gradients and animations
- **JavaScript**: Vanilla JS with async/await
- **Bootstrap 5**: Responsive framework
- **Bootstrap Icons**: Consistent iconography

### Backend
- **Flask**: Web framework
- **SQLAlchemy**: Database ORM
- **Blueprint Architecture**: Modular code organization
- **RESTful APIs**: Clean API design
- **Error Handling**: Comprehensive error management

### Security
- **Authentication**: Flask-Login integration
- **Authorization**: Role-based access control
- **Input Validation**: Server-side validation
- **CSRF Protection**: Built-in CSRF tokens

## Future Enhancements

### Planned Features
- **Bulk Operations**: Link multiple users at once
- **Advanced Filtering**: Filter by date ranges, ticket counts, etc.
- **Export Functionality**: Export data to CSV/Excel
- **Email Notifications**: Notify users of new links
- **Audit Trail**: Track who made what changes when

### Performance Optimizations
- **Caching**: Cache frequently accessed data
- **Pagination**: Handle large datasets efficiently
- **Background Jobs**: Process sync operations asynchronously
- **Database Indexing**: Optimize query performance

## Troubleshooting

### Common Issues

**"Access denied" error**
- Ensure user has elevated privileges (admin or non-user role)
- Check user authentication status

**No mappings displayed**
- Run the "Sync Mappings" function
- Check Freshworks service connectivity
- Verify database contains mapping data

**Ticket statistics not updating**
- Ensure user is properly linked
- Check ticket closure data exists
- Verify date ranges are correct

**Auto-linking not working**
- Check username similarity between Freshworks and website users
- Verify Freshworks service is working
- Check database for existing mappings

### Debug Mode
Enable debug logging by setting the log level to DEBUG in the application configuration.

## Support

For technical support or feature requests, please contact the development team or create an issue in the project repository. 