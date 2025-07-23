"""
Chat Models for YAM Team Chat System
Persistent storage that won't be wiped by reset_db.py
"""

from datetime import datetime
from extensions import db
from app.models.base import User


class TeamChatMessage(db.Model):
    """Persistent team chat messages that survive database resets."""
    __tablename__ = 'team_chat_messages'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)  # Store username for persistence
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, system, notification
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', backref='team_chat_messages')
    
    def to_dict(self):
        """Convert message to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'message': self.message,
            'message_type': self.message_type,
            'timestamp': self.timestamp.isoformat(),
            'is_deleted': self.is_deleted
        }
    
    def __repr__(self):
        return f'<TeamChatMessage {self.username}: {self.message[:50]}...>'


class TeamChatSession(db.Model):
    """Track active chat sessions and participants."""
    __tablename__ = 'team_chat_sessions'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)  # Socket.IO session ID
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='team_chat_sessions')
    
    def to_dict(self):
        """Convert session to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'joined_at': self.joined_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<TeamChatSession {self.user.username}: {self.session_id}>'


class TeamChatTyping(db.Model):
    """Track typing indicators for real-time feedback."""
    __tablename__ = 'team_chat_typing'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='team_chat_typing')
    
    def to_dict(self):
        """Convert typing indicator to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'started_at': self.started_at.isoformat(),
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<TeamChatTyping {self.username}>'


class TeamChatSettings(db.Model):
    """Global chat settings and configuration."""
    __tablename__ = 'team_chat_settings'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert setting to dictionary for API responses."""
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<TeamChatSettings {self.setting_key}: {self.setting_value}>'


# Chat utility functions
def get_recent_messages(limit=50, offset=0):
    """Get recent chat messages."""
    return TeamChatMessage.query.filter_by(is_deleted=False)\
        .order_by(TeamChatMessage.timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()


def get_active_participants():
    """Get currently active chat participants."""
    return TeamChatSession.query.filter_by(is_active=True)\
        .join(User)\
        .with_entities(User.id, User.username, TeamChatSession.last_activity)\
        .all()


def get_typing_users():
    """Get users currently typing."""
    return TeamChatTyping.query.filter_by(is_active=True)\
        .with_entities(TeamChatTyping.user_id, TeamChatTyping.username)\
        .all()


def cleanup_stale_sessions():
    """Clean up stale chat sessions (older than 30 minutes)."""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(minutes=30)
    stale_sessions = TeamChatSession.query.filter(
        TeamChatSession.last_activity < cutoff_time,
        TeamChatSession.is_active == True
    ).all()
    
    for session in stale_sessions:
        session.is_active = False
    
    db.session.commit()
    return len(stale_sessions)


def cleanup_stale_typing():
    """Clean up stale typing indicators (older than 10 seconds)."""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(seconds=10)
    stale_typing = TeamChatTyping.query.filter(
        TeamChatTyping.started_at < cutoff_time,
        TeamChatTyping.is_active == True
    ).all()
    
    for typing in stale_typing:
        typing.is_active = False
    
    db.session.commit()
    return len(stale_typing) 