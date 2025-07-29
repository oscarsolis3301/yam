from flask import jsonify, request
from datetime import datetime, date, timedelta
from . import tickets_api_bp
from app.utils.freshworks_service import freshworks_service
from app.models.base import TicketClosure, User, FreshworksUserMapping, TicketSyncMetadata
from app.extensions import db
from app.utils.logger import setup_logging
import os

logger = setup_logging()

@tickets_api_bp.route('/api/tickets/closures/today', methods=['GET'])
def get_todays_closures():
    """Get today's ticket closures by user with enhanced error handling"""
    try:
        today = date.today()
        logger.info(f"Fetching ticket closures for date: {today}")
        
        # Get from database first
        closures = TicketClosure.query.filter_by(date=today).join(User).all()
        logger.info(f"Found {len(closures)} closure records in database for {today}")
        
        if not closures:
            # If no data in database, check if we can sync
            can_sync, time_until_next = freshworks_service._check_sync_availability(today)
            logger.info(f"Can sync: {can_sync}, time until next: {time_until_next}")
            
            if can_sync:
                logger.info("No closure data found for today, syncing from Freshworks...")
                success = freshworks_service.sync_daily_closures(today)
                if success:
                    closures = TicketClosure.query.filter_by(date=today).join(User).all()
                    logger.info(f"After sync: found {len(closures)} closure records")
                else:
                    logger.warning("Failed to sync data from Freshworks")
            else:
                minutes_left = int(time_until_next / 60)
                logger.info(f"Rate limited - cannot sync yet. Next sync in {minutes_left} minutes.")
        
        # Format data for the chart - sort by tickets closed (descending)
        users_details = []
        
        for closure in closures:
            users_details.append({
                'username': closure.user.username,
                'tickets_closed': closure.tickets_closed,
                'role': closure.user.role,
                'profile_picture': closure.user.profile_picture,
                'user_id': closure.user.id
            })
        
        # Sort by tickets closed (descending) so highest performers appear first
        users_details.sort(key=lambda x: x['tickets_closed'], reverse=True)
        
        # Extract labels and data in sorted order
        labels = [user['username'] for user in users_details]
        data = [user['tickets_closed'] for user in users_details]
        
        # Calculate total and top performer
        total_closed = sum(data) if data else 0
        top_performer = max(users_details, key=lambda x: x['tickets_closed']) if users_details else None
        
        # Get sync status
        sync_status = get_sync_status_info(today)
        
        response_data = {
            'success': True,
            'date': today.isoformat(),
            'labels': labels,
            'data': data,
            'total_closed': total_closed,
            'top_performer': top_performer,
            'users': users_details,
            'sync_status': sync_status
        }
        
        logger.info(f"Returning ticket closure data: {total_closed} total tickets, {len(users_details)} users")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching today's closures: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/closures/period', methods=['GET'])
def get_period_closures():
    """Get ticket closures for a specific period (today, yesterday, week, month)"""
    try:
        period = request.args.get('period', 'today')
        
        if period == 'today':
            target_date = date.today()
            start_date = end_date = target_date
        elif period == 'yesterday':
            target_date = date.today() - timedelta(days=1)
            start_date = end_date = target_date
        elif period == 'week':
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
        else:
            return jsonify({'success': False, 'error': 'Invalid period'}), 400
        
        if period in ['today', 'yesterday']:
            # Single day data
            closures = TicketClosure.query.filter_by(date=target_date).join(User).all()
            
            if not closures and period == 'today':
                # Check if we can sync today's data
                can_sync, time_until_next = freshworks_service._check_sync_availability(target_date)
                if can_sync:
                    success = freshworks_service.sync_daily_closures(target_date)
                    if success:
                        closures = TicketClosure.query.filter_by(date=target_date).join(User).all()
            
            users_details = []
            
            for closure in closures:
                users_details.append({
                    'username': closure.user.username,
                    'tickets_closed': closure.tickets_closed,
                    'role': closure.user.role,
                    'profile_picture': closure.user.profile_picture
                })
            
            # Sort by tickets closed (descending)
            users_details.sort(key=lambda x: x['tickets_closed'], reverse=True)
            
            # Extract labels and data in sorted order
            labels = [user['username'] for user in users_details]
            data = [user['tickets_closed'] for user in users_details]
        else:
            # Period data (sum over multiple days)
            user_totals = freshworks_service.get_closure_data_for_period(start_date, end_date)
            
            labels = list(user_totals.keys())
            data = list(user_totals.values())
            
            # Get user details
            users_details = []
            for username, total in user_totals.items():
                user = User.query.filter_by(username=username).first()
                if user:
                    users_details.append({
                        'username': username,
                        'tickets_closed': total,
                        'role': user.role,
                        'profile_picture': user.profile_picture
                    })
        
        # Calculate statistics
        total_closed = sum(data) if data else 0
        top_performer = max(users_details, key=lambda x: x['tickets_closed']) if users_details else None
        
        return jsonify({
            'success': True,
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'labels': labels,
            'data': data,
            'total_closed': total_closed,
            'top_performer': top_performer,
            'users': users_details
        })
        
    except Exception as e:
        logger.error(f"Error fetching period closures: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/sync', methods=['POST'])
def sync_ticket_data():
    """
    Manually trigger ticket data sync with rate limiting
    """
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        target_date = request.json.get('date', date.today().isoformat())
        force_sync = request.json.get('force', False)
        
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Check rate limiting unless force sync
        if not force_sync:
            can_sync, time_until_next = freshworks_service._check_sync_availability(target_date)
            if not can_sync:
                minutes_left = int(time_until_next / 60)
                return jsonify({
                    'success': False, 
                    'error': f'Rate limited. Next sync available in {minutes_left} minutes.',
                    'time_until_next': time_until_next
                }), 429
        
        # Perform sync
        success = freshworks_service.sync_daily_closures(target_date, force_sync=force_sync)
        
        if success:
            # Get updated data
            closures = TicketClosure.query.filter_by(date=target_date).join(User).all()
            total_tickets = sum(closure.tickets_closed for closure in closures)
            
            return jsonify({
                'success': True,
                'message': f'Successfully synced {total_tickets} tickets for {target_date}',
                'date': target_date.isoformat(),
                'tickets_processed': total_tickets
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to sync ticket data'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in manual sync: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/top-performers', methods=['GET'])
def get_top_performers():
    """Get top performers for today"""
    try:
        today = date.today()
        limit = request.args.get('limit', 10, type=int)
        
        closures = TicketClosure.query.filter_by(date=today)\
            .join(User)\
            .order_by(TicketClosure.tickets_closed.desc())\
            .limit(limit)\
            .all()
        
        performers = []
        for closure in closures:
            performers.append({
                'username': closure.user.username,
                'tickets_closed': closure.tickets_closed,
                'role': closure.user.role,
                'profile_picture': closure.user.profile_picture
            })
        
        return jsonify({
            'success': True,
            'date': today.isoformat(),
            'performers': performers
        })
        
    except Exception as e:
        logger.error(f"Error fetching top performers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/user-mappings', methods=['GET'])
def get_user_mappings():
    """Get user mappings with detailed information"""
    try:
        mappings = FreshworksUserMapping.query.all()
        
        mapping_data = []
        for mapping in mappings:
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
            
            mapping_data.append({
                'freshworks_id': mapping.freshworks_user_id,
                'freshworks_name': mapping.freshworks_username,
                'user_id': mapping.user_id,
                'user_info': user_info,
                'status': 'mapped' if mapping.user_id else 'unmapped',
                'created_at': mapping.created_at.isoformat(),
                'updated_at': mapping.updated_at.isoformat()
            })
        
        # Get unmapped users info
        unmapped_info = freshworks_service.get_unmapped_users_info()
        
        return jsonify({
            'success': True,
            'mappings': mapping_data,
            'unmapped_users': unmapped_info,
            'total_mappings': len(mapping_data),
            'mapped_count': len([m for m in mapping_data if m['status'] == 'mapped']),
            'unmapped_count': len([m for m in mapping_data if m['status'] == 'unmapped'])
        })
        
    except Exception as e:
        logger.error(f"Error fetching user mappings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/stats', methods=['GET'])
def get_ticket_stats():
    """Get overall ticket statistics"""
    try:
        today = date.today()
        
        # Today's stats
        today_closures = TicketClosure.query.filter_by(date=today).all()
        today_total = sum(closure.tickets_closed for closure in today_closures)
        
        # This week's stats
        week_start = today - timedelta(days=today.weekday())
        week_closures = TicketClosure.query.filter(
            TicketClosure.date >= week_start,
            TicketClosure.date <= today
        ).all()
        week_total = sum(closure.tickets_closed for closure in week_closures)
        
        # This month's stats
        month_start = today.replace(day=1)
        month_closures = TicketClosure.query.filter(
            TicketClosure.date >= month_start,
            TicketClosure.date <= today
        ).all()
        month_total = sum(closure.tickets_closed for closure in month_closures)
        
        # Total stats
        total_closures = TicketClosure.query.all()
        total_tickets = sum(closure.tickets_closed for closure in total_closures)
        
        # Top performer today
        if today_closures:
            top_today = max(today_closures, key=lambda x: x.tickets_closed)
            top_performer = {
                'username': top_today.user.username,
                'tickets_closed': top_today.tickets_closed
            }
        else:
            top_performer = None
        
        return jsonify({
            'success': True,
            'stats': {
                'total_tickets': total_tickets,
                'today_total': today_total,
                'this_week': week_total,
                'this_month': month_total
            },
            'top_performer': top_performer,
            'date': today.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching ticket stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/user-stats', methods=['GET'])
def get_user_ticket_stats():
    """Get ticket statistics by user"""
    try:
        # Get all ticket closures with user information
        closures = db.session.query(TicketClosure, User).join(User).all()
        
        # Group by user
        user_stats = {}
        for closure, user in closures:
            if user.id not in user_stats:
                user_stats[user.id] = {
                    'user_id': user.id,
                    'username': user.username,
                    'total_tickets': 0,
                    'this_month': 0,
                    'this_week': 0,
                    'last_activity': None
                }
            
            user_stats[user.id]['total_tickets'] += closure.tickets_closed
            
            # Check if this month
            if closure.date >= date.today().replace(day=1):
                user_stats[user.id]['this_month'] += closure.tickets_closed
            
            # Check if this week
            week_start = date.today() - timedelta(days=date.today().weekday())
            if closure.date >= week_start:
                user_stats[user.id]['this_week'] += closure.tickets_closed
            
            # Track last activity
            if not user_stats[user.id]['last_activity'] or closure.date > user_stats[user.id]['last_activity']:
                user_stats[user.id]['last_activity'] = closure.date
        
        # Convert to list and sort by total tickets
        user_stats_list = list(user_stats.values())
        user_stats_list.sort(key=lambda x: x['total_tickets'], reverse=True)
        
        return jsonify({
            'success': True,
            'user_stats': user_stats_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching user ticket stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/sync-status', methods=['GET'])
def get_sync_status():
    """Get sync status and when next sync is available"""
    try:
        today = date.today()
        can_sync, time_until_next = freshworks_service._check_sync_availability(today)
        
        metadata = TicketSyncMetadata.query.filter_by(sync_date=today).first()
        
        sync_info = {
            'can_sync_now': can_sync,
            'time_until_next_sync': time_until_next,
            'minutes_until_next': int(time_until_next / 60) if time_until_next > 0 else 0,
            'last_sync_time': None,
            'sync_count_today': 0,
            'tickets_processed_today': 0
        }
        
        if metadata:
            sync_info.update({
                'last_sync_time': metadata.last_sync_time.isoformat(),
                'sync_count_today': metadata.sync_count,
                'tickets_processed_today': metadata.tickets_processed
            })
        
        return jsonify({
            'success': True,
            'date': today.isoformat(),
            'sync_info': sync_info
        })
        
    except Exception as e:
        logger.error(f"Error fetching sync status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/admin-stats', methods=['GET'])
def get_admin_stats():
    """Get comprehensive admin statistics for sync and database info"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        today = date.today()
        
        # Enhanced sync status for today
        can_sync, time_until_next = freshworks_service._check_sync_availability(today)
        last_metadata = TicketSyncMetadata.query.filter_by(sync_date=today).first()
        
        # Database statistics
        total_closure_records = TicketClosure.query.count()
        mapped_users_count = FreshworksUserMapping.query.count()
        linked_mappings_count = FreshworksUserMapping.query.filter(FreshworksUserMapping.user_id.isnot(None)).count()
        
        # Days with data
        unique_dates = db.session.query(TicketClosure.date).distinct().count()
        
        # Total syncs across all dates
        total_syncs = db.session.query(db.func.sum(TicketSyncMetadata.sync_count)).scalar() or 0
        
        # Recent activity (last 7 days of sync metadata)
        recent_syncs = TicketSyncMetadata.query.filter(
            TicketSyncMetadata.sync_date >= today - timedelta(days=7)
        ).order_by(TicketSyncMetadata.last_sync_time.desc()).limit(10).all()
        
        recent_activity = []
        for sync in recent_syncs:
            time_ago = datetime.utcnow() - sync.last_sync_time
            if time_ago.days > 0:
                time_str = f"{time_ago.days} day{'s' if time_ago.days > 1 else ''} ago"
            elif time_ago.seconds > 3600:
                hours = time_ago.seconds // 3600
                time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = time_ago.seconds // 60
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            
            recent_activity.append({
                'date': sync.sync_date.isoformat(),
                'time': sync.last_sync_time.strftime('%H:%M'),
                'tickets_processed': sync.tickets_processed,
                'sync_count': sync.sync_count,
                'time_ago': time_str
            })
        
        # Enhanced sync info
        sync_info = {
            'can_sync_now': can_sync,
            'time_until_next_sync': time_until_next,
            'minutes_until_next': int(time_until_next / 60) if time_until_next > 0 else 0,
            'last_sync_time': None,
            'next_sync_time': None,
            'sync_count_today': 0,
            'tickets_processed_today': 0
        }
        
        if last_metadata:
            sync_info.update({
                'last_sync_time': last_metadata.last_sync_time.isoformat(),
                'next_sync_time': (last_metadata.last_sync_time + timedelta(hours=1)).isoformat() if not can_sync else datetime.utcnow().isoformat(),
                'sync_count_today': last_metadata.sync_count,
                'tickets_processed_today': last_metadata.tickets_processed
            })
        
        # Top performers today
        today_closures = TicketClosure.query.filter_by(date=today).join(User).order_by(
            TicketClosure.tickets_closed.desc()
        ).limit(5).all()
        
        top_performers = []
        for closure in today_closures:
            top_performers.append({
                'username': closure.user.username,
                'tickets_closed': closure.tickets_closed,
                'role': closure.user.role
            })
        
        # Unmapped users info
        unmapped_info = freshworks_service.get_unmapped_users_info()
        
        response = {
            'success': True,
            'current_time': datetime.utcnow().isoformat(),
            'sync_info': sync_info,
            'database_stats': {
                'total_closure_records': total_closure_records,
                'mapped_users_count': mapped_users_count,
                'linked_mappings_count': linked_mappings_count,
                'unmapped_mappings_count': mapped_users_count - linked_mappings_count,
                'days_with_data': unique_dates,
                'total_syncs': total_syncs
            },
            'recent_activity': recent_activity,
            'top_performers_today': top_performers,
            'unmapped_users': unmapped_info
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/force-sync', methods=['POST'])
def force_sync():
    """Force sync ticket data (bypasses rate limiting)"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        target_date = request.json.get('date', date.today().isoformat())
        
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Force sync (bypasses rate limiting)
        success = freshworks_service.sync_daily_closures(target_date, force_sync=True)
        
        if success:
            # Get updated data
            closures = TicketClosure.query.filter_by(date=target_date).join(User).all()
            total_tickets = sum(closure.tickets_closed for closure in closures)
            
            return jsonify({
                'success': True,
                'message': f'Force sync completed. {total_tickets} tickets processed for {target_date}',
                'date': target_date.isoformat(),
                'tickets_processed': total_tickets
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to force sync ticket data'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in force sync: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/unmapped-users', methods=['GET'])
def get_unmapped_users():
    """Get detailed information about unmapped users for debugging"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        # Get unmapped users info from service
        unmapped_info = freshworks_service.get_unmapped_users_info()
        
        # Get additional details about unmapped users
        detailed_unmapped = []
        
        for info in unmapped_info:
            # Get any tickets closed by this user today
            today = date.today()
            tickets_closed = 0
            
            # Check if there are any ticket closures for this user ID
            closure = TicketClosure.query.filter_by(
                freshworks_user_id=info['freshworks_id'],
                date=today
            ).first()
            
            if closure:
                tickets_closed = closure.tickets_closed
            
            detailed_unmapped.append({
                'freshworks_id': info['freshworks_id'],
                'freshworks_name': info['freshworks_name'],
                'status': info['status'],
                'suggestion': info['suggestion'],
                'tickets_closed_today': tickets_closed,
                'mapping_created_at': None,
                'last_activity': None
            })
        
        # Get mapping details
        for item in detailed_unmapped:
            mapping = FreshworksUserMapping.query.filter_by(
                freshworks_user_id=item['freshworks_id']
            ).first()
            
            if mapping:
                item['mapping_created_at'] = mapping.created_at.isoformat()
                item['last_activity'] = mapping.updated_at.isoformat()
        
        return jsonify({
            'success': True,
            'unmapped_users': detailed_unmapped,
            'total_unmapped': len(detailed_unmapped),
            'total_mappings': FreshworksUserMapping.query.count(),
            'linked_mappings': FreshworksUserMapping.query.filter(FreshworksUserMapping.user_id.isnot(None)).count(),
            'debug_info': {
                'ids_file_path': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'Freshworks', 'IDs.txt'),
                'suggestion': 'Add missing users to IDs.txt in "Name - ID" format or create local users with matching usernames'
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching unmapped users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/test-db', methods=['GET'])
def test_database():
    """Test endpoint to check database connectivity and ticket closure data"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        today = date.today()
        
        # Test database connectivity
        try:
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            # Check ticket closure table
            ticket_closure_exists = 'ticket_closure' in tables
            user_exists = 'user' in tables
            
            # Get some sample data
            total_closures = TicketClosure.query.count()
            total_users = User.query.count()
            
            # Get today's data
            today_closures = TicketClosure.query.filter_by(date=today).all()
            
            # Get recent closures (last 7 days)
            week_ago = today - timedelta(days=7)
            recent_closures = TicketClosure.query.filter(TicketClosure.date >= week_ago).all()
            
            return jsonify({
                'success': True,
                'database_status': {
                    'tables_exist': {
                        'ticket_closure': ticket_closure_exists,
                        'user': user_exists
                    },
                    'total_tables': len(tables),
                    'available_tables': tables
                },
                'data_counts': {
                    'total_closures': total_closures,
                    'total_users': total_users,
                    'today_closures': len(today_closures),
                    'recent_closures': len(recent_closures)
                },
                'today_data': [
                    {
                        'id': c.id,
                        'user_id': c.user_id,
                        'freshworks_user_id': c.freshworks_user_id,
                        'date': c.date.isoformat(),
                        'tickets_closed': c.tickets_closed,
                        'username': c.user.username if c.user else 'Unknown'
                    } for c in today_closures
                ],
                'test_date': today.isoformat()
            })
            
        except Exception as db_error:
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}',
                'database_status': 'failed'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in test database endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/sync-user-mappings', methods=['POST'])
def sync_user_mappings():
    """Sync user mappings from Freshworks service"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager', 'developer']:
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        success = freshworks_service.sync_user_mappings()
        
        if success:
            return jsonify({'success': True, 'message': 'User mappings synced successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to sync user mappings'}), 500
            
    except Exception as e:
        logger.error(f"Error syncing user mappings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/sync-from-ids', methods=['POST'])
def sync_from_ids_file():
    """Sync user mappings from IDs.txt file"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager', 'developer']:
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        # Load and sync from IDs.txt
        id_name_map = freshworks_service.load_id_name_mapping()
        
        mappings_created = 0
        mappings_updated = 0
        
        for freshworks_id, freshworks_name in id_name_map.items():
            # Check if mapping already exists
            existing_mapping = FreshworksUserMapping.query.filter_by(
                freshworks_user_id=freshworks_id
            ).first()
            
            if existing_mapping:
                # Update existing mapping if name changed
                if existing_mapping.freshworks_username != freshworks_name:
                    existing_mapping.freshworks_username = freshworks_name
                    existing_mapping.updated_at = datetime.utcnow()
                    mappings_updated += 1
            else:
                # Create new mapping
                mapping = FreshworksUserMapping(
                    freshworks_user_id=freshworks_id,
                    freshworks_username=freshworks_name
                )
                db.session.add(mapping)
                mappings_created += 1
        
        try:
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'User mappings synced from IDs.txt: {mappings_created} created, {mappings_updated} updated'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error syncing from IDs.txt: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/user-mappings/<int:freshworks_id>', methods=['GET'])
def get_user_mapping(freshworks_id):
    """Get a specific user mapping"""
    try:
        mapping = FreshworksUserMapping.query.filter_by(freshworks_user_id=freshworks_id).first()
        
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
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
        
        return jsonify({
            'success': True,
            'mapping': {
                'freshworks_id': mapping.freshworks_user_id,
                'freshworks_name': mapping.freshworks_username,
                'user_id': mapping.user_id,
                'user_info': user_info,
                'created_at': mapping.created_at.isoformat(),
                'updated_at': mapping.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching user mapping: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/user-mappings/<int:freshworks_id>', methods=['PUT'])
def update_user_mapping(freshworks_id):
    """Update a user mapping"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager', 'developer']:
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        mapping = FreshworksUserMapping.query.filter_by(freshworks_user_id=freshworks_id).first()
        
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
        data = request.get_json()
        
        if 'freshworks_name' in data:
            mapping.freshworks_username = data['freshworks_name']
        
        if 'user_id' in data:
            mapping.user_id = data['user_id'] if data['user_id'] else None
        
        mapping.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Mapping updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Error updating user mapping: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/user-mappings/<int:freshworks_id>', methods=['DELETE'])
def delete_user_mapping(freshworks_id):
    """Delete a user mapping"""
    try:
        from flask_login import current_user
        
        # Check if user has admin privileges
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager', 'developer']:
            return jsonify({'success': False, 'error': 'Unauthorized - Admin access required'}), 403
        
        mapping = FreshworksUserMapping.query.filter_by(freshworks_user_id=freshworks_id).first()
        
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404
        
        db.session.delete(mapping)
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Mapping deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting user mapping: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_api_bp.route('/api/tickets/user-details/<username>', methods=['GET'])
def get_user_ticket_details(username):
    """Get detailed ticket information for a specific user on a specific date"""
    try:
        target_date_str = request.args.get('date')
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            target_date = date.today()
        
        logger.info(f"Fetching ticket details for user '{username}' on {target_date}")
        
        # Find the user mapping
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Find the Freshworks mapping for this user
        mapping = FreshworksUserMapping.query.filter_by(user_id=user.id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'User not mapped to Freshworks'}), 404
        
        freshworks_user_id = mapping.freshworks_user_id
        
        # First, try to get stored ticket numbers from the database
        closure_record = TicketClosure.query.filter_by(
            user_id=user.id,
            date=target_date
        ).first()
        
        if closure_record and closure_record.ticket_numbers:
            # Use stored ticket numbers from database - NO API CALLS
            import json
            try:
                stored_ticket_ids = json.loads(closure_record.ticket_numbers)
                logger.info(f"Found {len(stored_ticket_ids)} stored ticket IDs for {username} on {target_date}")
                
                # Create basic ticket information from stored IDs without API calls
                tickets = []
                for ticket_id in stored_ticket_ids:
                    # Create basic ticket info from stored ID only
                    basic_ticket = {
                        'id': ticket_id,
                        'ticket_number': f"INC-{ticket_id}",
                        'subject': f"Ticket #{ticket_id}",
                        'description': f"Ticket closed by {username} on {target_date}",
                        'status': 4,  # Assume closed since these are closure records
                        'priority': 2,  # Default to medium priority
                        'urgency': 2,   # Default to medium urgency
                        'created_at': target_date.isoformat(),
                        'updated_at': target_date.isoformat(),
                        'resolved_at': target_date.isoformat(),
                        'tags': ['closed', 'daily-closure'],
                        'type': 'incident'
                    }
                    tickets.append(basic_ticket)
                
                logger.info(f"Created {len(tickets)} basic ticket records from stored IDs")
                
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error parsing stored ticket numbers: {e}")
                tickets = []
        else:
            # No stored ticket numbers found - return empty list
            logger.info(f"No stored ticket numbers found for user {username} on {target_date}")
            tickets = []
        
        if not tickets:
            return jsonify({
                'success': True,
                'user': {
                    'username': username,
                    'freshworks_id': freshworks_user_id,
                    'freshworks_name': mapping.freshworks_username
                },
                'date': target_date.isoformat(),
                'tickets': [],
                'total_tickets': 0,
                'summary': {
                    'total_closed': 0,
                    'total_open': 0,
                    'high_priority': 0,
                    'urgent': 0
                },
                'message': f'No tickets found for {username} on {target_date}'
            })
        
        # Format ticket data
        formatted_tickets = []
        for ticket in tickets:
            formatted_ticket = {
                'id': ticket.get('id'),
                'ticket_number': f"INC-{ticket.get('id')}",
                'subject': ticket.get('subject', 'No Subject'),
                'description': ticket.get('description_text', ''),
                'status': ticket.get('status'),
                'priority': ticket.get('priority'),
                'source': ticket.get('source'),
                'category': ticket.get('category'),
                'sub_category': ticket.get('sub_category'),
                'created_at': ticket.get('created_at'),
                'updated_at': ticket.get('updated_at'),
                'resolved_at': ticket.get('resolved_at'),
                'due_by': ticket.get('due_by'),
                'group_id': ticket.get('group_id'),
                'responder_id': ticket.get('responder_id'),
                'requester_id': ticket.get('requester_id'),
                'tags': ticket.get('tags', []),
                'type': ticket.get('type'),
                'urgency': ticket.get('urgency')
            }
            formatted_tickets.append(formatted_ticket)
        
        # Sort tickets by updated_at (most recent first)
        formatted_tickets.sort(key=lambda x: x['updated_at'] or '', reverse=True)
        
        return jsonify({
            'success': True,
            'user': {
                'username': username,
                'freshworks_id': freshworks_user_id,
                'freshworks_name': mapping.freshworks_username,
                'role': user.role,
                'profile_picture': user.profile_picture
            },
            'date': target_date.isoformat(),
            'tickets': formatted_tickets,
            'total_tickets': len(formatted_tickets),
            'summary': {
                'total_closed': len([t for t in formatted_tickets if t['status'] == 4]),
                'total_open': len([t for t in formatted_tickets if t['status'] != 4]),
                'high_priority': len([t for t in formatted_tickets if t['priority'] in [1, 2]]),
                'urgent': len([t for t in formatted_tickets if t['urgency'] == 4])
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching user ticket details: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_sync_status_info(target_date):
    """Helper function to get sync status information"""
    can_sync, time_until_next = freshworks_service._check_sync_availability(target_date)
    metadata = TicketSyncMetadata.query.filter_by(sync_date=target_date).first()
    
    return {
        'can_sync_now': can_sync,
        'time_until_next_sync': time_until_next,
        'minutes_until_next': int(time_until_next / 60) if time_until_next > 0 else 0,
        'last_sync_time': metadata.last_sync_time.isoformat() if metadata else None,
        'sync_count_today': metadata.sync_count if metadata else 0,
        'tickets_processed_today': metadata.tickets_processed if metadata else 0
    }