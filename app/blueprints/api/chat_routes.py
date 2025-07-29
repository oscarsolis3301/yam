"""
API Routes for YAM Team Chat
RESTful endpoints for chat functionality
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.chat import (
    TeamChatMessage, TeamChatSession, TeamChatTyping,
    get_recent_messages, get_active_participants, get_typing_users
)

logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/messages', methods=['GET'])
@login_required
def get_messages():
    """Get recent chat messages."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get recent messages
        messages = get_recent_messages(limit=limit, offset=offset)
        
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


@chat_bp.route('/messages', methods=['POST'])
@login_required
def create_message():
    """Create a new chat message."""
    try:
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400
        
        # Create the message
        chat_message = TeamChatMessage(
            user_id=current_user.id,
            username=current_user.username,
            message=message_text,
            message_type='text',
            timestamp=datetime.utcnow()
        )
        db.session.add(chat_message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': chat_message.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to create message',
            'message': str(e)
        }), 500


@chat_bp.route('/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """Delete a chat message (soft delete)."""
    try:
        message = TeamChatMessage.query.get_or_404(message_id)
        
        # Only allow users to delete their own messages or admins
        if message.user_id != current_user.id and not current_user.is_admin:
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


@chat_bp.route('/participants', methods=['GET'])
@login_required
def get_participants():
    """Get active chat participants."""
    try:
        participants = get_active_participants()
        
        return jsonify({
            'success': True,
            'participants': [
                {
                    'id': p.id,
                    'username': p.username,
                    'last_activity': p.last_activity.isoformat()
                } for p in participants
            ],
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting participants: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get participants',
            'message': str(e)
        }), 500


@chat_bp.route('/typing', methods=['GET'])
@login_required
def get_typing_users():
    """Get users currently typing."""
    try:
        typing_users = get_typing_users()
        
        return jsonify({
            'success': True,
            'typing_users': [
                {
                    'user_id': t.user_id,
                    'username': t.username
                } for t in typing_users
            ],
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting typing users: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get typing users',
            'message': str(e)
        }), 500


@chat_bp.route('/typing', methods=['POST'])
@login_required
def start_typing():
    """Start typing indicator."""
    try:
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
        
        return jsonify({
            'success': True,
            'message': 'Typing indicator started',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error starting typing indicator: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to start typing indicator',
            'message': str(e)
        }), 500


@chat_bp.route('/typing', methods=['DELETE'])
@login_required
def stop_typing():
    """Stop typing indicator."""
    try:
        # Update typing indicator
        typing = TeamChatTyping.query.filter_by(
            user_id=current_user.id
        ).first()
        
        if typing:
            typing.is_active = False
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Typing indicator stopped',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error stopping typing indicator: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to stop typing indicator',
            'message': str(e)
        }), 500


@chat_bp.route('/stats', methods=['GET'])
@login_required
def get_chat_stats():
    """Get chat statistics."""
    try:
        # Get message count
        message_count = TeamChatMessage.query.filter_by(is_deleted=False).count()
        
        # Get active participants count
        participant_count = TeamChatSession.query.filter_by(is_active=True).count()
        
        # Get typing users count
        typing_count = TeamChatTyping.query.filter_by(is_active=True).count()
        
        # Get today's message count
        today = datetime.utcnow().date()
        today_messages = TeamChatMessage.query.filter(
            TeamChatMessage.is_deleted == False,
            db.func.date(TeamChatMessage.timestamp) == today
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_messages': message_count,
                'active_participants': participant_count,
                'typing_users': typing_count,
                'today_messages': today_messages
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting chat stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get chat stats',
            'message': str(e)
        }), 500


@chat_bp.route('/search', methods=['GET'])
@login_required
def search_messages():
    """Search chat messages."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        # Search messages
        messages = TeamChatMessage.query.filter(
            TeamChatMessage.is_deleted == False,
            TeamChatMessage.message.ilike(f'%{query}%')
        ).order_by(TeamChatMessage.timestamp.desc()).limit(50).all()
        
        return jsonify({
            'success': True,
            'messages': [msg.to_dict() for msg in messages],
            'query': query,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search messages',
            'message': str(e)
        }), 500 