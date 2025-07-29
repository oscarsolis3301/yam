"""
Private Messages Model for YAM
Persistent storage for private messages between users
"""

from datetime import datetime
from app.extensions import db
from app.models.base import User


class PrivateMessage(db.Model):
    """Private messages between users."""
    __tablename__ = 'private_messages'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    
    def to_dict(self):
        """Convert message to dictionary for API responses."""
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'sender_name': self.sender.username if self.sender else 'Unknown',
            'recipient_name': self.recipient.username if self.recipient else 'Unknown',
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'is_deleted': self.is_deleted
        }
    
    def __repr__(self):
        return f'<PrivateMessage {self.sender_id} -> {self.recipient_id}: {self.message[:50]}...>'


class PrivateMessageSession(db.Model):
    """Track active private message sessions."""
    __tablename__ = 'private_message_sessions'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    unread_count_user1 = db.Column(db.Integer, default=0)
    unread_count_user2 = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])
    
    def to_dict(self):
        """Convert session to dictionary for API responses."""
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'user1_name': self.user1.username if self.user1 else 'Unknown',
            'user2_name': self.user2.username if self.user2 else 'Unknown',
            'last_message_at': self.last_message_at.isoformat(),
            'unread_count_user1': self.unread_count_user1,
            'unread_count_user2': self.unread_count_user2,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<PrivateMessageSession {self.user1_id} <-> {self.user2_id}>'


def get_conversation_messages(user1_id, user2_id, limit=50, offset=0):
    """Get messages between two users."""
    return PrivateMessage.query.filter(
        db.or_(
            db.and_(PrivateMessage.sender_id == user1_id, PrivateMessage.recipient_id == user2_id),
            db.and_(PrivateMessage.sender_id == user2_id, PrivateMessage.recipient_id == user1_id)
        ),
        PrivateMessage.is_deleted == False
    ).order_by(PrivateMessage.created_at.desc()).limit(limit).offset(offset).all()


def get_user_conversations(user_id):
    """Get all conversations for a user."""
    # Get all sessions where the user is involved
    sessions = PrivateMessageSession.query.filter(
        db.or_(
            PrivateMessageSession.user1_id == user_id,
            PrivateMessageSession.user2_id == user_id
        )
    ).order_by(PrivateMessageSession.last_message_at.desc()).all()
    
    return sessions


def mark_messages_as_read(sender_id, recipient_id):
    """Mark messages as read from sender to recipient."""
    PrivateMessage.query.filter_by(
        sender_id=sender_id,
        recipient_id=recipient_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()


def get_unread_count(user_id):
    """Get total unread messages for a user."""
    return PrivateMessage.query.filter_by(
        recipient_id=user_id,
        is_read=False,
        is_deleted=False
    ).count() 