"""
API Routes for Private Messages
RESTful endpoints for private messaging between users
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from app.models.private_messages import (
    PrivateMessage, PrivateMessageSession,
    get_conversation_messages, get_user_conversations,
    mark_messages_as_read, get_unread_count
)
from app.models.base import User

logger = logging.getLogger(__name__)

# Create blueprint
private_messages_bp = Blueprint('private_messages', __name__)


@private_messages_bp.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for the current user."""
    try:
        conversations = get_user_conversations(current_user.id)
        
        # Format conversations with other user info
        formatted_conversations = []
        for conv in conversations:
            # Determine the other user in the conversation
            other_user_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
            other_user = User.query.get(other_user_id)
            
            if other_user:
                formatted_conversations.append({
                    'session_id': conv.id,
                    'other_user': {
                        'id': other_user.id,
                        'username': other_user.username,
                        'email': other_user.email,
                        'is_online': getattr(other_user, 'is_online', False)
                    },
                    'last_message_at': conv.last_message_at.isoformat(),
                    'unread_count': conv.unread_count_user2 if conv.user1_id == current_user.id else conv.unread_count_user1
                })
        
        return jsonify({
            'success': True,
            'conversations': formatted_conversations,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get conversations',
            'message': str(e)
        }), 500


@private_messages_bp.route('/messages/<int:other_user_id>', methods=['GET'])
@login_required
def get_messages(other_user_id):
    """Get messages between current user and another user."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Mark messages as read
        mark_messages_as_read(other_user_id, current_user.id)
        
        # Get messages
        messages = get_conversation_messages(current_user.id, other_user_id, limit, offset)
        
        return jsonify({
            'success': True,
            'messages': [msg.to_dict() for msg in messages],
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get messages',
            'message': str(e)
        }), 500


@private_messages_bp.route('/messages', methods=['POST'])
@login_required
def send_message():
    """Send a private message to another user."""
    try:
        data = request.get_json()
        recipient_id = data.get('recipient_id')
        message_text = data.get('message', '').strip()
        
        if not recipient_id:
            return jsonify({
                'success': False,
                'error': 'Recipient ID is required'
            }), 400
        
        if not message_text:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400
        
        # Check if recipient exists
        recipient = User.query.get(recipient_id)
        if not recipient:
            return jsonify({
                'success': False,
                'error': 'Recipient not found'
            }), 404
        
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
        
        return jsonify({
            'success': True,
            'message': message.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to send message',
            'message': str(e)
        }), 500


@private_messages_bp.route('/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """Delete a private message (soft delete)."""
    try:
        message = PrivateMessage.query.get_or_404(message_id)
        
        # Only allow users to delete their own messages
        if message.sender_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Permission denied'
            }), 403
        
        # Soft delete
        message.is_deleted = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Message deleted successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to delete message',
            'message': str(e)
        }), 500


@private_messages_bp.route('/unread', methods=['GET'])
@login_required
def get_unread_messages():
    """Get unread message count for current user."""
    try:
        unread_count = get_unread_count(current_user.id)
        
        return jsonify({
            'success': True,
            'unread_count': unread_count,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get unread count',
            'message': str(e)
        }), 500


@private_messages_bp.route('/mark-read/<int:sender_id>', methods=['POST'])
@login_required
def mark_conversation_read(sender_id):
    """Mark all messages from a sender as read."""
    try:
        mark_messages_as_read(sender_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': 'Messages marked as read',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error marking messages as read: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark messages as read',
            'message': str(e)
        }), 500 