"""
Socket.IO Handlers for Private Messages
Real-time private messaging between users
"""

import logging
from datetime import datetime
from flask import current_app, request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app.extensions import socketio, db
from app.models.private_messages import (
    PrivateMessage, PrivateMessageSession,
    get_conversation_messages, get_user_conversations,
    mark_messages_as_read, get_unread_count
)
from app.models.base import User

logger = logging.getLogger(__name__)

@socketio.on('join_private_chat')
def handle_join_private_chat(data):
    """Handle user joining a private chat room."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        other_user_id = data.get('other_user_id')
        if not other_user_id:
            emit('error', {'message': 'Other user ID is required'})
            return
        
        # Create a unique room name for the conversation
        room_name = f"private_chat_{min(current_user.id, other_user_id)}_{max(current_user.id, other_user_id)}"
        
        # Join the room
        join_room(room_name)
        
        # Mark messages as read
        mark_messages_as_read(other_user_id, current_user.id)
        
        # Send conversation history
        messages = get_conversation_messages(current_user.id, other_user_id, limit=50)
        emit('private_chat_history', {
            'messages': [msg.to_dict() for msg in messages],
            'room': room_name
        })
        
        logger.info(f"User {current_user.username} joined private chat with user {other_user_id}")
        
    except Exception as e:
        logger.error(f"Error joining private chat: {e}")
        emit('error', {'message': 'Failed to join private chat'})

@socketio.on('leave_private_chat')
def handle_leave_private_chat(data):
    """Handle user leaving a private chat room."""
    try:
        if not current_user.is_authenticated:
            return
        
        other_user_id = data.get('other_user_id')
        if other_user_id:
            room_name = f"private_chat_{min(current_user.id, other_user_id)}_{max(current_user.id, other_user_id)}"
            leave_room(room_name)
            logger.info(f"User {current_user.username} left private chat with user {other_user_id}")
        
    except Exception as e:
        logger.error(f"Error leaving private chat: {e}")

@socketio.on('private_message')
def handle_private_message(data):
    """Handle incoming private message."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        recipient_id = data.get('recipient_id')
        message_text = data.get('message', '').strip()
        
        if not recipient_id:
            emit('error', {'message': 'Recipient ID is required'})
            return
        
        if not message_text:
            emit('error', {'message': 'Message cannot be empty'})
            return
        
        # Check if recipient exists
        recipient = User.query.get(recipient_id)
        if not recipient:
            emit('error', {'message': 'Recipient not found'})
            return
        
        # Create the message
        message = PrivateMessage(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            message=message_text,
            created_at=datetime.utcnow()
        )
        db.session.add(message)
        
        # Update or create conversation session
        session = PrivateMessageSession.query.filter(
            db.or_(
                db.and_(PrivateMessageSession.user1_id == current_user.id, PrivateMessageSession.user2_id == recipient_id),
                db.and_(PrivateMessageSession.user1_id == recipient_id, PrivateMessageSession.user2_id == current_user.id)
            )
        ).first()
        
        if session:
            # Update existing session
            session.last_message_at = datetime.utcnow()
            if session.user1_id == current_user.id:
                session.unread_count_user2 += 1
            else:
                session.unread_count_user1 += 1
        else:
            # Create new session
            session = PrivateMessageSession(
                user1_id=current_user.id,
                user2_id=recipient_id,
                last_message_at=datetime.utcnow(),
                unread_count_user2=1
            )
            db.session.add(session)
        
        db.session.commit()
        
        # Create room name for the conversation
        room_name = f"private_chat_{min(current_user.id, recipient_id)}_{max(current_user.id, recipient_id)}"
        
        # Broadcast message to the room
        message_data = message.to_dict()
        emit('private_message', message_data, room=room_name)
        
        # Emit to sender for confirmation
        emit('private_message_sent', {
            'success': True,
            'message': message_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Private message from {current_user.username} to {recipient.username}: {message_text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error handling private message: {e}")
        db.session.rollback()
        emit('error', {'message': 'Failed to send message'})

@socketio.on('mark_private_messages_read')
def handle_mark_private_messages_read(data):
    """Handle marking private messages as read."""
    try:
        if not current_user.is_authenticated:
            return
        
        sender_id = data.get('sender_id')
        if sender_id:
            mark_messages_as_read(sender_id, current_user.id)
            
            # Emit read receipt
            emit('private_messages_read', {
                'sender_id': sender_id,
                'read_by': current_user.id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"User {current_user.username} marked messages from {sender_id} as read")
        
    except Exception as e:
        logger.error(f"Error marking private messages as read: {e}")

@socketio.on('get_private_unread_count')
def handle_get_private_unread_count():
    """Handle getting unread private message count."""
    try:
        if not current_user.is_authenticated:
            return
        
        unread_count = get_unread_count(current_user.id)
        
        emit('private_unread_count', {
            'count': unread_count,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting private unread count: {e}")

@socketio.on('typing_private')
def handle_private_typing(data):
    """Handle typing indicator in private chat."""
    try:
        if not current_user.is_authenticated:
            return
        
        recipient_id = data.get('recipient_id')
        is_typing = data.get('is_typing', False)
        
        if recipient_id:
            room_name = f"private_chat_{min(current_user.id, recipient_id)}_{max(current_user.id, recipient_id)}"
            
            emit('private_typing', {
                'user_id': current_user.id,
                'username': current_user.username,
                'is_typing': is_typing
            }, room=room_name, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling private typing: {e}") 