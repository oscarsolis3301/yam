from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db
import psutil
import json


class Outage(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # active, resolved
    ticket_id = db.Column(db.String(50), nullable=True)
    affected_systems = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(20), nullable=True, default='medium')
    duration = db.Column(db.Float, nullable=True, default=1.0)  # Duration in hours
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'ticket_id': self.ticket_id,
            'affected_systems': self.affected_systems,
            'severity': self.severity,
            'duration': self.duration,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    password_plain = db.Column(db.String(128))  # For admin viewing only
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', or 'dev'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    profile_picture = db.Column(db.String(255), default='default.png')
    okta_verified = db.Column(db.Boolean, default=False)
    teams_notifications = db.Column(db.Boolean, default=True)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    windows_username = db.Column(db.String(100), unique=True, nullable=True)  # Windows domain username
    requires_password_change = db.Column(db.Boolean, default=True)  # Track if user needs to change password
    
    # Relationships
    search_history = db.relationship('SearchHistory', backref='user', lazy=True)
    notes = db.relationship('Note', backref='user', lazy=True)
    activities = db.relationship('Activity', backref='user', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False)
    documents = db.relationship('Document', backref='user', lazy=True)
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.password_plain = password  # Store plain text for admin viewing
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_seen(self):
        self.last_seen = datetime.utcnow()
        self.is_online = True
        db.session.commit()
    
    def set_offline(self):
        self.is_online = False
        db.session.commit()
    
    def mark_password_changed(self):
        """Mark that the user has changed their password"""
        self.requires_password_change = False
        db.session.commit()
    
    def is_first_time_login(self):
        """Check if this is the user's first time logging in"""
        return self.requires_password_change and self.password_plain == 'password'
    
    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        """Serialize the user model with commonly-used public fields.

        Sensitive attributes such as password hashes are *never* exposed. The
        method intentionally keeps the payload lightweight so it can be safely
        returned by API endpoints and used by the front-end profile modal.
        """
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'profile_picture': self.profile_picture or 'default.png',
        }

        # Lightweight stats – these calls are safe even when relationships are empty
        try:
            data['search_history_count'] = len(self.search_history or [])
            data['notes_count'] = len(self.notes or [])
        except Exception:
            # Relationship may not be loaded – fail silently to avoid breaking the API
            pass

        return data

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(500), nullable=False)
    search_type = db.Column(db.String(50), nullable=False)  # Type of search (e.g., 'User', 'Office', 'Workstation')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SearchHistory {self.query}>'

class SystemSettings(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    maintenance_mode = db.Column(db.Boolean, default=False)
    allow_registration = db.Column(db.Boolean, default=True)
    max_upload_size = db.Column(db.Integer, default=50)  # in MB
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemSettings {self.id}>'

class UserSettings(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    theme = db.Column(db.String(20), default='light')
    notifications_enabled = db.Column(db.Boolean, default=True)
    email_notifications = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Appearance settings
    accent_color = db.Column(db.String(7), default='#007bff')
    font_size = db.Column(db.String(10), default='medium')  # small, medium, large
    
    # Notification settings
    browser_notifications = db.Column(db.Boolean, default=True)
    notification_frequency = db.Column(db.String(20), default='realtime')  # realtime, daily, weekly
    
    # Privacy settings
    save_search_history = db.Column(db.Boolean, default=True)
    track_activity = db.Column(db.Boolean, default=True)
    allow_data_collection = db.Column(db.Boolean, default=True)
    dameware_username = db.Column(db.String(120))
    dameware_domain = db.Column(db.String(120))
    dameware_password_encrypted = db.Column(db.LargeBinary)

class Note(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(7), default='#ffffff')  # Hex color code
    position_x = db.Column(db.Integer, default=0)
    position_y = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    share_token = db.Column(db.String(12), unique=True)  # Unique token for public sharing
    is_public = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(500))  # Tags for search and categorization

    def __repr__(self):
        return f'<Note {self.title}>'

    def to_dict(self):
        """Return a JSON-serialisable representation used by the REST API and Socket.IO."""
        return {
            'id': self.id,
            'title': self.title if (self.title and self.title.strip() and self.title != 'Untitled') else '',  # Empty string for frontend placeholder handling
            'content': self.content,
            'user_id': self.user_id,
            'is_public': self.is_public,
            'share_token': self.share_token,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

class Activity(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Activity {self.action} at {self.timestamp}>'

class Document(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(500))

class KBArticle(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    tags = db.Column(db.String(200))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    helpful_count = db.Column(db.Integer, default=0)
    not_helpful_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    import_status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    is_public = db.Column(db.Boolean, default=True)
    file_path = db.Column(db.String(500))
    preview_image = db.Column(db.String(500))  # Path to preview image (PNG)
    summary = db.Column(db.Text)  # Short text summary for fast display
    
    @property
    def author(self):
        if self.author_id:
            user = User.query.get(self.author_id)
            return user.username if user else 'Unknown'
        return 'Unknown'

class KBAttachment(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('kb_article.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100))
    file_size = db.Column(db.Integer)  # Size in bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    uploader = db.relationship('User', backref=db.backref('kb_attachments', lazy=True))

class SharedLink(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('kb_article.id'), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    views = db.Column(db.Integer, default=0)
    
    article = db.relationship('KBArticle', backref=db.backref('shared_links', lazy=True))
    creator = db.relationship('User', backref=db.backref('shared_links', lazy=True))

class KBFeedback(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('kb_article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'helpful' or 'not_helpful'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('kb_feedback', lazy=True))

class UserPresence(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(50), default='online')  # online, away, busy, offline
    
    user = db.relationship('User', backref=db.backref('presence', uselist=False))
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.last_seen = datetime.utcnow()
        self.is_online = True
        self.status = 'online'
    
    def update_presence(self):
        self.last_seen = datetime.utcnow()
        self.is_online = True
    
    def set_offline(self):
        self.is_online = False
        self.status = 'offline'

class TimeEntry(db.Model):
    __tablename__ = 'time_entries'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    clock_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    notes = db.Column(db.Text)
    
    user = db.relationship('User', backref=db.backref('time_entries', lazy=True))
    
    def __repr__(self):
        return f'<TimeEntry {self.user_id} at {self.clock_in}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'clock_in': self.clock_in.isoformat() if self.clock_in else None,
            'clock_out': self.clock_out.isoformat() if self.clock_out else None,
            'status': self.status,
            'notes': self.notes
        }

class ChatQA(db.Model):
    __tablename__ = 'chat_qa'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255))
    image_caption = db.Column(db.Text)
    embedding = db.Column(db.LargeBinary)

class APICache(db.Model):
    __tablename__ = 'api_cache'
    __table_args__ = {'extend_existing': True}
    
    query = db.Column(db.String(255), primary_key=True)
    raw_json = db.Column(db.Text)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<APICache {self.query}>'

class UserMapping(db.Model):
    """Map Freshworks user IDs to names and link to actual user accounts for Patterson system."""
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    freshworks_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    role = db.Column(db.String(50), default='technician')
    region = db.Column(db.String(100))  # Added region field
    
    # Link to actual user account
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    linked_user = db.relationship('User', backref='patterson_mappings')
    
    # Tracking fields
    total_tickets_handled = db.Column(db.Integer, default=0)
    tickets_this_month = db.Column(db.Integer, default=0)
    tickets_this_week = db.Column(db.Integer, default=0)
    last_ticket_date = db.Column(db.DateTime)
    average_resolution_time = db.Column(db.Float)  # in hours
    success_rate = db.Column(db.Float, default=100.0)  # percentage
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)  # Email verification status
    notes = db.Column(db.Text)  # Admin notes about this mapping
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserMapping {self.freshworks_id}: {self.name}>'
    
    def to_dict(self):
        """Convert mapping to dictionary format for API responses."""
        return {
            'id': self.id,
            'freshworks_id': self.freshworks_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'region': self.region,
            'user_id': self.user_id,
            'linked_username': self.linked_user.username if self.linked_user else None,
            'linked_email': self.linked_user.email if self.linked_user else None,
            'total_tickets_handled': self.total_tickets_handled,
            'tickets_this_month': self.tickets_this_month,
            'tickets_this_week': self.tickets_this_week,
            'last_ticket_date': self.last_ticket_date.isoformat() if self.last_ticket_date else None,
            'average_resolution_time': self.average_resolution_time,
            'success_rate': self.success_rate,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def update_ticket_stats(self):
        """Update ticket statistics for this mapping."""
        from datetime import datetime, timedelta
        
        # Get all tickets for this Freshworks ID - check both technician_id and freshworks_id
        tickets = PattersonTicket.query.filter(
            db.or_(
                PattersonTicket.technician_id == self.freshworks_id,
                PattersonTicket.freshworks_id == self.freshworks_id
            )
        ).all()
        
        if not tickets:
            return
        
        # Update total tickets
        self.total_tickets_handled = len(tickets)
        
        # Calculate this month's tickets
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.tickets_this_month = len([t for t in tickets if t.created_at >= month_start])
        
        # Calculate this week's tickets
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        self.tickets_this_week = len([t for t in tickets if t.created_at >= week_start])
        
        # Update last ticket date
        latest_ticket = max(tickets, key=lambda t: t.created_at)
        self.last_ticket_date = latest_ticket.created_at
        
        # Calculate average resolution time (simplified - could be enhanced)
        completed_tickets = [t for t in tickets if t.stage == 'completed']
        if completed_tickets:
            total_time = 0
            for ticket in completed_tickets:
                if ticket.created_at and ticket.updated_at:
                    duration = (ticket.updated_at - ticket.created_at).total_seconds() / 3600  # hours
                    total_time += duration
            self.average_resolution_time = total_time / len(completed_tickets)
        
        # Calculate success rate (simplified - could be enhanced based on ticket outcomes)
        if tickets:
            completed_count = len([t for t in tickets if t.stage == 'completed'])
            self.success_rate = (completed_count / len(tickets)) * 100

class PattersonTicket(db.Model):
    """Patterson dispatch tickets stored in database for persistence."""
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    freshworks_id = db.Column(db.String(50), unique=True)  # Freshworks ticket ID
    ticket_number = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200))  # Clean title extracted from subject
    office_name = db.Column(db.String(200), nullable=False)
    technician = db.Column(db.String(200))
    technician_id = db.Column(db.Integer)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='Medium')
    urgency = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(50), default='Scheduled')
    scheduled_date = db.Column(db.Date)
    scheduled_time = db.Column(db.String(10))
    estimated_duration = db.Column(db.String(50), default='2 hours')
    stage = db.Column(db.String(20), default='scheduled')  # in_progress, scheduled, completed
    category = db.Column(db.String(100))
    source = db.Column(db.String(50), default='freshworks')  # freshworks, local, calendar_event
    notes = db.Column(db.Text)  # JSON string of notes array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_patterson_tickets')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='updated_patterson_tickets')
    
    def to_dict(self):
        """Convert ticket to dictionary format for API responses."""
        notes_list = []
        if self.notes:
            try:
                notes_list = json.loads(self.notes)
            except (json.JSONDecodeError, TypeError):
                notes_list = []
        
        return {
            'id': self.id,
            'freshworks_id': self.freshworks_id,
            'ticket_number': self.ticket_number,
            'title': self.title,
            'office_name': self.office_name,
            'technician': self.technician,
            'technician_id': self.technician_id,
            'description': self.description,
            'priority': self.priority,
            'urgency': self.urgency,
            'status': self.status,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'scheduled_time': self.scheduled_time,
            'estimated_duration': self.estimated_duration,
            'stage': self.stage,
            'category': self.category,
            'source': self.source,
            'notes': notes_list,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    def __repr__(self):
        return f'<PattersonTicket {self.ticket_number}: {self.office_name}>'

class PattersonCalendarEvent(db.Model):
    """Calendar events for Patterson dispatch system."""
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    office = db.Column(db.String(200), default='General')
    technician_id = db.Column(db.Integer)
    technician_name = db.Column(db.String(200))
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.String(10), default='09:00')
    duration = db.Column(db.String(50), default='1 hour')
    priority = db.Column(db.String(20), default='Medium')
    urgency = db.Column(db.String(20), default='Medium')
    ticket_id = db.Column(db.Integer, db.ForeignKey('patterson_ticket.id'))  # Link to ticket
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    creator = db.relationship('User', backref='created_calendar_events')
    ticket = db.relationship('PattersonTicket', backref='calendar_events')
    
    def to_dict(self):
        """Convert calendar event to dictionary format for API responses."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'office': self.office,
            'technician_id': self.technician_id,
            'technician_name': self.technician_name,
            'event_date': self.event_date.isoformat(),
            'event_time': self.event_time,
            'duration': self.duration,
            'priority': self.priority,
            'urgency': self.urgency,
            'ticket_id': self.ticket_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by
        }
    
    def __repr__(self):
        return f'<PattersonCalendarEvent {self.title}: {self.event_date}>'

class SearchIndex(db.Model):
    """Persistent search index for fast startup and searching."""
    __tablename__ = 'search_index'
    __table_args__ = (
        db.Index('idx_content_lookup', 'content_type', 'content_id'),
        db.Index('idx_searchable_text', 'searchable_text'),
        {'extend_existing': True}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.String(100), nullable=False, index=True)  # e.g., "kb_123", "outage_456"
    content_type = db.Column(db.String(50), nullable=False, index=True)  # e.g., "kb_article", "outage"
    title = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    author = db.Column(db.String(100))
    tags = db.Column(db.Text)
    category = db.Column(db.String(100))
    status = db.Column(db.String(50))
    url = db.Column(db.String(500))
    section = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    priority = db.Column(db.Float, default=1.0)
    views = db.Column(db.Integer, default=0)
    searchable_text = db.Column(db.Text, nullable=False)
    last_indexed = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SearchIndex {self.content_type}:{self.content_id}>'

# --- Lightweight User Cache (for Universal Search personalization) ---
class UserCache(db.Model):
    """Cache of stable user attributes for fast personalization.

    This table intentionally stores *only* non-volatile data so cached
    information remains valid even when the authoritative source (Active
    Directory / Okta) changes dynamic fields such as *account_locked* status.
    It is **never** used to bypass or replace the live PowerShell lookup – its
    sole purpose is to enrich the UI while the background query is running.
    """

    __tablename__ = 'user_cache'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    clock_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    job_title = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional helper for serialising to JSON
    def to_dict(self):
        return {
            'clock_id': self.clock_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'email': self.email,
            'job_title': self.job_title
        }

    def __repr__(self):  # pragma: no cover – cosmetic only
        return f'<UserCache {self.clock_id} ({self.username})>'

class NoteCollaborator(db.Model):
    """Mapping table that grants individual users access to a given note."""
    __tablename__ = 'note_collaborator'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    can_edit = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    note = db.relationship('Note', backref=db.backref('collaborators', cascade='all, delete-orphan', lazy=True))
    user = db.relationship('User', backref='collaborations')

class NoteVersion(db.Model):
    """Stores a full snapshot of a note every time it changes for version history."""
    __tablename__ = 'note_version'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    note = db.relationship('Note', backref=db.backref('versions', cascade='all, delete-orphan', lazy=True))
    user = db.relationship('User', backref='note_versions')

class AllowedWindowsUser(db.Model):
    """Track Windows usernames that are allowed to access the application."""
    __tablename__ = 'allowed_windows_users'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    windows_username = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200))  # Full name for display
    email = db.Column(db.String(200))  # Email address
    department = db.Column(db.String(100))  # Department/team
    role = db.Column(db.String(50), default='user')  # Role in the system
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)  # Admin notes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_attempt = db.Column(db.DateTime)  # Track last login attempt
    login_count = db.Column(db.Integer, default=0)  # Track successful logins
    
    # Link to actual user account if one exists
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    linked_user = db.relationship('User', backref='windows_user_mapping')
    
    def __repr__(self):
        return f'<AllowedWindowsUser {self.windows_username}>'
    
    def to_dict(self):
        """Return a JSON-serializable representation."""
        return {
            'id': self.id,
            'windows_username': self.windows_username,
            'display_name': self.display_name,
            'email': self.email,
            'department': self.department,
            'role': self.role,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login_attempt': self.last_login_attempt.isoformat() if self.last_login_attempt else None,
            'login_count': self.login_count,
            'user_id': self.user_id
        }
    
    def update_login_attempt(self, success=True):
        """Update login attempt tracking."""
        self.last_login_attempt = datetime.utcnow()
        if success:
            self.login_count += 1
        db.session.commit()

class TicketClosure(db.Model):
    """Track daily ticket closures by user for persistent storage and reporting"""
    __tablename__ = 'ticket_closure'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freshworks_user_id = db.Column(db.Integer, nullable=True)  # Freshworks responder ID
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    tickets_closed = db.Column(db.Integer, nullable=False, default=0)
    ticket_numbers = db.Column(db.Text, nullable=True)  # JSON string of ticket IDs that were closed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add a unique constraint to prevent duplicate entries for the same user/date
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date_closure'),
        {'extend_existing': True}
    )
    
    # Relationship
    user = db.relationship('User', backref='ticket_closures')
    
    def to_dict(self):
        import json
        ticket_numbers_list = []
        if self.ticket_numbers:
            try:
                ticket_numbers_list = json.loads(self.ticket_numbers)
            except (json.JSONDecodeError, TypeError):
                ticket_numbers_list = []
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'freshworks_user_id': self.freshworks_user_id,
            'date': self.date.isoformat(),
            'tickets_closed': self.tickets_closed,
            'ticket_numbers': ticket_numbers_list,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class FreshworksUserMapping(db.Model):
    """Map Freshworks user IDs to local users for ticket closure tracking"""
    __tablename__ = 'freshworks_user_mapping'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null for unmapped users
    freshworks_user_id = db.Column(db.Integer, nullable=False, unique=True)
    freshworks_username = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='freshworks_mapping')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'freshworks_user_id': self.freshworks_user_id,
            'freshworks_username': self.freshworks_username,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TicketSyncMetadata(db.Model):
    """Track ticket sync metadata and timestamps for rate limiting"""
    __tablename__ = 'ticket_sync_metadata'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    sync_date = db.Column(db.Date, nullable=False, unique=True)
    last_sync_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sync_count = db.Column(db.Integer, nullable=False, default=0)
    tickets_processed = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sync_date': self.sync_date.isoformat(),
            'last_sync_time': self.last_sync_time.isoformat(),
            'sync_count': self.sync_count,
            'tickets_processed': self.tickets_processed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def can_sync_now(target_date=None):
        """Check if we can sync now (more than 1 hour since last sync)"""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        metadata = TicketSyncMetadata.query.filter_by(sync_date=target_date).first()
        if not metadata:
            return True  # No previous sync for this date
        
        # Check if at least 1 hour has passed
        now = datetime.utcnow()
        time_diff = now - metadata.last_sync_time
        return time_diff.total_seconds() >= 3600  # 1 hour = 3600 seconds
    
    @staticmethod
    def update_sync_metadata(target_date, tickets_processed=0):
        """Update sync metadata for a given date"""
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        metadata = TicketSyncMetadata.query.filter_by(sync_date=target_date).first()
        if metadata:
            # Update existing record
            metadata.last_sync_time = datetime.utcnow()
            metadata.sync_count += 1
            metadata.tickets_processed += tickets_processed
            metadata.updated_at = datetime.utcnow()
        else:
            # Create new record
            metadata = TicketSyncMetadata(
                sync_date=target_date,
                last_sync_time=datetime.utcnow(),
                sync_count=1,
                tickets_processed=tickets_processed
            )
            db.session.add(metadata)
        
        db.session.commit()
        return metadata

class TicketClosureHistory(db.Model):
    """Track historical ticket closures with hourly updates and time markers"""
    __tablename__ = 'ticket_closure_history'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freshworks_user_id = db.Column(db.Integer, nullable=True)  # Freshworks responder ID
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    hour = db.Column(db.Integer, nullable=False, default=datetime.utcnow().hour)  # Hour of the day (0-23)
    tickets_closed = db.Column(db.Integer, nullable=False, default=0)
    ticket_numbers = db.Column(db.Text, nullable=True)  # JSON string of ticket IDs that were closed
    sync_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add a unique constraint to prevent duplicate entries for the same user/date/hour
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', 'hour', name='unique_user_date_hour_closure'),
        {'extend_existing': True}
    )
    
    # Relationship
    user = db.relationship('User', backref='ticket_closure_history')
    
    def to_dict(self):
        import json
        ticket_numbers_list = []
        if self.ticket_numbers:
            try:
                ticket_numbers_list = json.loads(self.ticket_numbers)
            except (json.JSONDecodeError, TypeError):
                ticket_numbers_list = []
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'freshworks_user_id': self.freshworks_user_id,
            'date': self.date.isoformat(),
            'hour': self.hour,
            'tickets_closed': self.tickets_closed,
            'ticket_numbers': ticket_numbers_list,
            'sync_timestamp': self.sync_timestamp.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TicketClosureDaily(db.Model):
    """Daily aggregated ticket closures for quick access"""
    __tablename__ = 'ticket_closure_daily'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freshworks_user_id = db.Column(db.Integer, nullable=True)  # Freshworks responder ID
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    tickets_closed = db.Column(db.Integer, nullable=False, default=0)
    ticket_numbers = db.Column(db.Text, nullable=True)  # JSON string of all ticket IDs for the day
    last_sync_hour = db.Column(db.Integer, nullable=True)  # Last hour when data was synced
    sync_count = db.Column(db.Integer, nullable=False, default=0)  # Number of syncs for this day
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add a unique constraint to prevent duplicate entries for the same user/date
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date_daily_closure'),
        {'extend_existing': True}
    )
    
    # Relationship
    user = db.relationship('User', backref='ticket_closure_daily')
    
    def to_dict(self):
        import json
        ticket_numbers_list = []
        if self.ticket_numbers:
            try:
                ticket_numbers_list = json.loads(self.ticket_numbers)
            except (json.JSONDecodeError, TypeError):
                ticket_numbers_list = []
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'freshworks_user_id': self.freshworks_user_id,
            'date': self.date.isoformat(),
            'tickets_closed': self.tickets_closed,
            'ticket_numbers': ticket_numbers_list,
            'last_sync_hour': self.last_sync_hour,
            'sync_count': self.sync_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

def init_db():
    # Create all tables
    # db.create_all()
    
    # Check if we need to add new columns to the User table
    conn = db.engine.connect()
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    # Add new columns if they don't exist
    if 'profile_picture' not in columns:
        conn.execute('ALTER TABLE user ADD COLUMN profile_picture VARCHAR(255) DEFAULT "default.png"')
    if 'okta_verified' not in columns:
        conn.execute('ALTER TABLE user ADD COLUMN okta_verified BOOLEAN DEFAULT FALSE')
    if 'teams_notifications' not in columns:
        conn.execute('ALTER TABLE user ADD COLUMN teams_notifications BOOLEAN DEFAULT TRUE')
    if 'requires_password_change' not in columns:
        conn.execute('ALTER TABLE user ADD COLUMN requires_password_change BOOLEAN DEFAULT TRUE')
    
    # Check if we need to add search_type to SearchHistory table
    search_history_columns = [col['name'] for col in inspector.get_columns('search_history')]
    if 'search_type' not in search_history_columns:
        conn.execute('ALTER TABLE search_history ADD COLUMN search_type VARCHAR(50) DEFAULT "General"')
    
    conn.close()
    
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(email='admin@pdshealth.com').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@pdshealth.com',
            role='admin',
            is_active=True,
            profile_picture='default.png',
            okta_verified=False,
            teams_notifications=True
        )
        admin.set_password('admin123')  # Set a default password
        db.session.add(admin)
        db.session.commit()
    
    # Create default system settings if none exist
    if not SystemSettings.query.first():
        settings = SystemSettings()
        db.session.add(settings)
        db.session.commit() 