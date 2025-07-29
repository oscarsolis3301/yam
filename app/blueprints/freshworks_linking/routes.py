import logging
from datetime import datetime, timedelta
from flask import render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, and_
from . import bp
from app.extensions import db
from app.models.base import User, FreshworksUserMapping, TicketClosure
from app.utils.freshworks_service import freshworks_service

logger = logging.getLogger(__name__)

def require_non_user_role():
    """Decorator to require non-user role access"""
    if not current_user.is_authenticated or current_user.role == 'user':
        return jsonify({'error': 'Access denied. Elevated privileges required.'}), 403
    return None

@bp.route('/')
@login_required
def dashboard():
    """Main Freshworks linking dashboard page"""
    auth_check = require_non_user_role()
    if auth_check:
        return auth_check
    
    return render_template('freshworks_linking/dashboard.html')

@bp.route('/api/mappings', methods=['GET'])
@login_required
def get_mappings():
    """Get all Freshworks user mappings with detailed information"""
    auth_check = require_non_user_role()
    if auth_check:
        return auth_check
    
    try:
        # Get all mappings
        mappings = FreshworksUserMapping.query.all()
        
        # Get all users for linking
        users = User.query.filter(User.role != 'user').all()
        
        # Get ticket statistics for each mapping
        mapping_data = []
        for mapping in mappings:
            # Get user info if linked
            user_info = None
            if mapping.user_id:
                user = User.query.get(mapping.user_id)
                if user:
                    user_info = {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role
                    }
            
            # Get ticket statistics
            ticket_stats = get_ticket_stats_for_mapping(mapping)
            
            mapping_data.append({
                'id': mapping.id,
                'freshworks_user_id': mapping.freshworks_user_id,
                'freshworks_username': mapping.freshworks_username,
                'user_id': mapping.user_id,
                'user_info': user_info,
                'status': 'linked' if mapping.user_id else 'unlinked',
                'ticket_stats': ticket_stats,
                'created_at': mapping.created_at.isoformat(),
                'updated_at': mapping.updated_at.isoformat()
            })
        
        # Get available users for linking
        available_users = [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        } for user in users]
        
        return jsonify({
            'success': True,
            'mappings': mapping_data,
            'available_users': available_users,
            'stats': {
                'total_mappings': len(mapping_data),
                'linked_count': len([m for m in mapping_data if m['status'] == 'linked']),
                'unlinked_count': len([m for m in mapping_data if m['status'] == 'unlinked'])
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching mappings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/mappings/<int:mapping_id>', methods=['PUT'])
@login_required
def update_mapping(mapping_id):
    """Update a Freshworks user mapping"""
    auth_check = require_non_user_role()
    if auth_check:
        return auth_check
    
    try:
        data = request.get_json()
        mapping = FreshworksUserMapping.query.get_or_404(mapping_id)
        
        # Update user link
        if 'user_id' in data:
            if data['user_id']:
                # Link to user
                user = User.query.get(data['user_id'])
                if not user:
                    return jsonify({'success': False, 'error': 'User not found'}), 404
                mapping.user_id = data['user_id']
            else:
                # Unlink user
                mapping.user_id = None
        
        mapping.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Get updated mapping data
        user_info = None
        if mapping.user_id:
            user = User.query.get(mapping.user_id)
            if user:
                user_info = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                }
        
        ticket_stats = get_ticket_stats_for_mapping(mapping)
        
        return jsonify({
            'success': True,
            'mapping': {
                'id': mapping.id,
                'freshworks_user_id': mapping.freshworks_user_id,
                'freshworks_username': mapping.freshworks_username,
                'user_id': mapping.user_id,
                'user_info': user_info,
                'status': 'linked' if mapping.user_id else 'unlinked',
                'ticket_stats': ticket_stats,
                'updated_at': mapping.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating mapping: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/mappings/sync', methods=['POST'])
@login_required
def sync_mappings():
    """Sync Freshworks user mappings from the service"""
    auth_check = require_non_user_role()
    if auth_check:
        return auth_check
    
    try:
        # Sync mappings from Freshworks service
        freshworks_service.sync_user_mappings()
        
        return jsonify({
            'success': True,
            'message': 'User mappings synced successfully'
        })
        
    except Exception as e:
        logger.error(f"Error syncing mappings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/mappings/auto-link', methods=['POST'])
@login_required
def auto_link_mappings():
    """Automatically link unmapped users based on username similarity"""
    auth_check = require_non_user_role()
    if auth_check:
        return auth_check
    
    try:
        # Get unmapped mappings
        unmapped_mappings = FreshworksUserMapping.query.filter_by(user_id=None).all()
        linked_count = 0
        
        for mapping in unmapped_mappings:
            # Use the service's matching logic
            local_user = freshworks_service._find_matching_user(mapping.freshworks_username)
            
            if local_user:
                mapping.user_id = local_user.id
                mapping.updated_at = datetime.utcnow()
                linked_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully auto-linked {linked_count} users',
            'linked_count': linked_count
        })
        
    except Exception as e:
        logger.error(f"Error auto-linking mappings: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/tickets/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_tickets(user_id):
    """Get detailed ticket information for a specific user"""
    auth_check = require_non_user_role()
    if auth_check:
        return auth_check
    
    try:
        # Get date range from query params
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get ticket closures for the user
        closures = TicketClosure.query.filter(
            and_(
                TicketClosure.user_id == user_id,
                TicketClosure.date >= start_date,
                TicketClosure.date <= end_date
            )
        ).order_by(TicketClosure.date.desc()).all()
        
        # Format the data
        ticket_data = []
        for closure in closures:
            ticket_numbers = []
            if closure.ticket_numbers:
                import json
                try:
                    ticket_numbers = json.loads(closure.ticket_numbers)
                except:
                    ticket_numbers = []
            
            ticket_data.append({
                'date': closure.date.isoformat(),
                'tickets_closed': closure.tickets_closed,
                'ticket_numbers': ticket_numbers,
                'freshworks_user_id': closure.freshworks_user_id
            })
        
        # Get user info
        user = User.query.get(user_id)
        user_info = None
        if user:
            user_info = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        
        return jsonify({
            'success': True,
            'user_info': user_info,
            'tickets': ticket_data,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching user tickets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_ticket_stats_for_mapping(mapping):
    """Get ticket statistics for a specific mapping"""
    try:
        if not mapping.user_id:
            return {
                'total_tickets': 0,
                'this_month': 0,
                'this_week': 0,
                'last_activity': None
            }
        
        # Get date ranges
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get total tickets
        total_tickets = db.session.query(func.sum(TicketClosure.tickets_closed)).filter(
            TicketClosure.user_id == mapping.user_id
        ).scalar() or 0
        
        # Get this month's tickets
        this_month = db.session.query(func.sum(TicketClosure.tickets_closed)).filter(
            and_(
                TicketClosure.user_id == mapping.user_id,
                TicketClosure.date >= month_start.date()
            )
        ).scalar() or 0
        
        # Get this week's tickets
        this_week = db.session.query(func.sum(TicketClosure.tickets_closed)).filter(
            and_(
                TicketClosure.user_id == mapping.user_id,
                TicketClosure.date >= week_start.date()
            )
        ).scalar() or 0
        
        # Get last activity
        last_activity = db.session.query(TicketClosure.date).filter(
            TicketClosure.user_id == mapping.user_id
        ).order_by(TicketClosure.date.desc()).first()
        
        return {
            'total_tickets': total_tickets,
            'this_month': this_month,
            'this_week': this_week,
            'last_activity': last_activity[0].isoformat() if last_activity else None
        }
        
    except Exception as e:
        logger.error(f"Error getting ticket stats for mapping {mapping.id}: {e}")
        return {
            'total_tickets': 0,
            'this_month': 0,
            'this_week': 0,
            'last_activity': None
        } 