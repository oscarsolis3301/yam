"""
Socket.IO Handlers for YAM Team Chat
Real-time communication with persistent storage
"""

import logging
from datetime import datetime
from flask import current_app
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app.extensions import socketio, db
from app.models.chat import (
    TeamChatMessage, TeamChatSession, TeamChatTyping,
    get_recent_messages, get_active_participants, get_typing_users,
    cleanup_stale_sessions, cleanup_stale_typing
)

logger = logging.getLogger(__name__)

# Global chat room name
TEAM_CHAT_ROOM = 'team_chat'

@socketio.on('join_team_chat')
def handle_join_team_chat(data):
    """Handle user joining the team chat."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        # Join the chat room
        join_room(TEAM_CHAT_ROOM)
        
        # Create or update chat session
        session = TeamChatSession.query.filter_by(
            user_id=current_user.id,
            session_id=request.sid
        ).first()
        
        if not session:
            session = TeamChatSession(
                user_id=current_user.id,
                session_id=request.sid,
                joined_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                is_active=True
            )
            db.session.add(session)
        else:
            session.is_active = True
            session.last_activity = datetime.utcnow()
        
        db.session.commit()
        
        # Send recent messages to the user
        recent_messages = get_recent_messages(limit=50)
        emit('chat_history', {
            'messages': [msg.to_dict() for msg in recent_messages]
        })
        
        # Send current participants
        participants = get_active_participants()
        emit('chat_participants', {
            'participants': [
                {
                    'id': p.id,
                    'username': p.username,
                    'last_activity': p.last_activity.isoformat()
                } for p in participants
            ]
        })
        
        # Notify others that user joined
        emit('user_joined_chat', {
            'user_id': current_user.id,
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=TEAM_CHAT_ROOM, include_self=False)
        
        logger.info(f"User {current_user.username} joined team chat")
        
    except Exception as e:
        logger.error(f"Error joining team chat: {e}")
        emit('error', {'message': 'Failed to join chat'})


@socketio.on('leave_team_chat')
def handle_leave_team_chat(data):
    """Handle user leaving the team chat."""
    try:
        if not current_user.is_authenticated:
            return
        
        # Leave the chat room
        leave_room(TEAM_CHAT_ROOM)
        
        # Update session status
        session = TeamChatSession.query.filter_by(
            user_id=current_user.id,
            session_id=request.sid
        ).first()
        
        if session:
            session.is_active = False
            session.last_activity = datetime.utcnow()
            db.session.commit()
        
        # Notify others that user left
        emit('user_left_chat', {
            'user_id': current_user.id,
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=TEAM_CHAT_ROOM, include_self=False)
        
        logger.info(f"User {current_user.username} left team chat")
        
    except Exception as e:
        logger.error(f"Error leaving team chat: {e}")


@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle incoming chat message."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        message_text = data.get('message', '').strip()
        if not message_text:
            emit('error', {'message': 'Message cannot be empty'})
            return
        
        # Create and save the message
        chat_message = TeamChatMessage(
            user_id=current_user.id,
            username=current_user.username,
            message=message_text,
            message_type='text',
            timestamp=datetime.utcnow()
        )
        db.session.add(chat_message)
        db.session.commit()
        
        # Update user's last activity
        session = TeamChatSession.query.filter_by(
            user_id=current_user.id,
            session_id=request.sid
        ).first()
        if session:
            session.last_activity = datetime.utcnow()
            db.session.commit()
        
        # Broadcast message to all users in the chat room
        message_data = chat_message.to_dict()
        emit('chat_message', message_data, room=TEAM_CHAT_ROOM)
        
        logger.info(f"Chat message from {current_user.username}: {message_text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        emit('error', {'message': 'Failed to send message'})


@socketio.on('user_typing')
def handle_user_typing(data):
    """Handle user typing indicator."""
    try:
        if not current_user.is_authenticated:
            return
        
        # Create or update typing indicator
        typing = TeamChatTyping.query.filter_by(
            user_id=current_user.id
        ).first()
        
        if not typing:
            typing = TeamChatTyping(
                user_id=current_user.id,
                username=current_user.username,
                started_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(typing)
        else:
            typing.is_active = True
            typing.started_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify others that user is typing
        emit('user_typing', {
            'user_id': current_user.id,
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=TEAM_CHAT_ROOM, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling typing indicator: {e}")


@socketio.on('user_stopped_typing')
def handle_user_stopped_typing(data):
    """Handle user stopped typing indicator."""
    try:
        if not current_user.is_authenticated:
            return
        
        # Update typing indicator
        typing = TeamChatTyping.query.filter_by(
            user_id=current_user.id
        ).first()
        
        if typing:
            typing.is_active = False
            db.session.commit()
        
        # Notify others that user stopped typing
        emit('user_stopped_typing', {
            'user_id': current_user.id,
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=TEAM_CHAT_ROOM, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling stopped typing indicator: {e}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection."""
    try:
        if not current_user.is_authenticated:
            return
        
        # Update session status
        session = TeamChatSession.query.filter_by(
            user_id=current_user.id,
            session_id=request.sid
        ).first()
        
        if session:
            session.is_active = False
            session.last_activity = datetime.utcnow()
            db.session.commit()
        
        # Remove typing indicator
        typing = TeamChatTyping.query.filter_by(
            user_id=current_user.id
        ).first()
        
        if typing:
            typing.is_active = False
            db.session.commit()
        
        # Notify others that user disconnected
        emit('user_disconnected', {
            'user_id': current_user.id,
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=TEAM_CHAT_ROOM, include_self=False)
        
        logger.info(f"User {current_user.username} disconnected from team chat")
        
    except Exception as e:
        logger.error(f"Error handling disconnect: {e}")


def cleanup_chat_data():
    """Clean up stale chat data (called periodically)."""
    try:
        # Clean up stale sessions
        stale_sessions = cleanup_stale_sessions()
        
        # Clean up stale typing indicators
        stale_typing = cleanup_stale_typing()
        
        if stale_sessions > 0 or stale_typing > 0:
            logger.info(f"Cleaned up {stale_sessions} stale sessions and {stale_typing} stale typing indicators")
        
    except Exception as e:
        logger.error(f"Error cleaning up chat data: {e}")


# Import request for session ID access
from flask import request 