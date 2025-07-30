"""
Ticket Closure Tracking Service
Handles hourly updates, historical data, and time period filtering for ticket closures
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import func, and_, or_
from app import create_app
from app.models.base import (
    TicketClosure, 
    TicketClosureHistory, 
    TicketClosureDaily,
    FreshworksUserMapping, 
    TicketSyncMetadata,
    User
)
from app.extensions import db
from app.utils.freshworks_service import freshworks_service
from app.utils.logger import setup_logging

logger = setup_logging()

class TicketClosureService:
    """Enhanced service for ticket closure tracking with historical data"""
    
    def __init__(self):
        self.app = create_app()
        self.freshworks_service = freshworks_service
    
    def sync_hourly_closures(self, target_date=None, target_hour=None):
        """
        Sync ticket closures for a specific hour with historical tracking
        """
        if target_date is None:
            target_date = date.today()
        if target_hour is None:
            target_hour = datetime.now().hour
        
        logger.info(f"🔄 Syncing hourly closures for {target_date} at hour {target_hour}")
        
        try:
            # Get fresh data from Freshworks
            tickets = self.freshworks_service.get_tickets_for_date(target_date)
            if not tickets:
                logger.warning(f"No tickets found for {target_date}")
                return False
            
            # Process tickets and group by responder
            closure_data = defaultdict(lambda: {'count': 0, 'ticket_numbers': []})
            
            for ticket in tickets:
                if not isinstance(ticket, dict):
                    continue
                
                # Check if ticket was updated in the target hour
                updated_at_str = ticket.get('updated_at')
                if not updated_at_str:
                    continue
                
                try:
                    updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ")
                    if updated_at.date() == target_date and updated_at.hour == target_hour:
                        responder_id = ticket.get('responder_id')
                        if responder_id:
                            closure_data[responder_id]['count'] += 1
                            closure_data[responder_id]['ticket_numbers'].append(ticket.get('id'))
                except Exception as e:
                    logger.warning(f"Error parsing ticket update time: {e}")
                    continue
            
            # Update database with hourly data
            success_count = 0
            for freshworks_id, data in closure_data.items():
                count = data['count']
                ticket_numbers = data['ticket_numbers']
                
                # Find user mapping
                mapping = FreshworksUserMapping.query.filter_by(
                    freshworks_user_id=freshworks_id
                ).first()
                
                if mapping and mapping.user_id:
                    # Update or create hourly record
                    hourly_record = TicketClosureHistory.query.filter_by(
                        user_id=mapping.user_id,
                        date=target_date,
                        hour=target_hour
                    ).first()
                    
                    ticket_numbers_json = json.dumps(ticket_numbers) if ticket_numbers else None
                    
                    if hourly_record:
                        # Update existing hourly record
                        hourly_record.tickets_closed = count
                        hourly_record.ticket_numbers = ticket_numbers_json
                        hourly_record.sync_timestamp = datetime.utcnow()
                        hourly_record.updated_at = datetime.utcnow()
                        logger.info(f"🔄 Updated hourly record: {mapping.freshworks_username} - {count} tickets at hour {target_hour}")
                    else:
                        # Create new hourly record
                        hourly_record = TicketClosureHistory(
                            user_id=mapping.user_id,
                            freshworks_user_id=freshworks_id,
                            date=target_date,
                            hour=target_hour,
                            tickets_closed=count,
                            ticket_numbers=ticket_numbers_json,
                            sync_timestamp=datetime.utcnow()
                        )
                        db.session.add(hourly_record)
                        logger.info(f"➕ Created hourly record: {mapping.freshworks_username} - {count} tickets at hour {target_hour}")
                    
                    success_count += 1
            
            # Update daily aggregated data
            self._update_daily_aggregation(target_date)
            
            # Update sync metadata
            self._update_sync_metadata(target_date, target_hour, success_count)
            
            db.session.commit()
            logger.info(f"✅ Hourly sync completed: {success_count} users updated for {target_date} hour {target_hour}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Error during hourly sync: {e}")
            return False
    
    def _update_daily_aggregation(self, target_date):
        """Update daily aggregated data from hourly records"""
        try:
            # Get all hourly records for the date
            hourly_records = TicketClosureHistory.query.filter_by(date=target_date).all()
            
            # Group by user
            user_totals = defaultdict(lambda: {'total': 0, 'ticket_numbers': [], 'sync_count': 0})
            
            for record in hourly_records:
                user_totals[record.user_id]['total'] += record.tickets_closed
                user_totals[record.user_id]['sync_count'] += 1
                
                if record.ticket_numbers:
                    try:
                        numbers = json.loads(record.ticket_numbers)
                        user_totals[record.user_id]['ticket_numbers'].extend(numbers)
                    except:
                        pass
            
            # Update daily records
            for user_id, data in user_totals.items():
                daily_record = TicketClosureDaily.query.filter_by(
                    user_id=user_id,
                    date=target_date
                ).first()
                
                ticket_numbers_json = json.dumps(data['ticket_numbers']) if data['ticket_numbers'] else None
                last_sync_hour = max([r.hour for r in hourly_records if r.user_id == user_id], default=None)
                
                if daily_record:
                    # Update existing daily record
                    daily_record.tickets_closed = data['total']
                    daily_record.ticket_numbers = ticket_numbers_json
                    daily_record.last_sync_hour = last_sync_hour
                    daily_record.sync_count = data['sync_count']
                    daily_record.updated_at = datetime.utcnow()
                else:
                    # Create new daily record
                    daily_record = TicketClosureDaily(
                        user_id=user_id,
                        date=target_date,
                        tickets_closed=data['total'],
                        ticket_numbers=ticket_numbers_json,
                        last_sync_hour=last_sync_hour,
                        sync_count=data['sync_count']
                    )
                    db.session.add(daily_record)
            
            logger.info(f"✅ Daily aggregation updated for {target_date}")
            
        except Exception as e:
            logger.error(f"❌ Error updating daily aggregation: {e}")
    
    def _update_sync_metadata(self, target_date, target_hour, success_count):
        """Update sync metadata for tracking"""
        try:
            metadata = TicketSyncMetadata.query.filter_by(sync_date=target_date).first()
            
            if metadata:
                metadata.sync_count += 1
                metadata.last_sync_time = datetime.utcnow()
                metadata.tickets_processed += success_count
            else:
                metadata = TicketSyncMetadata(
                    sync_date=target_date,
                    sync_count=1,
                    last_sync_time=datetime.utcnow(),
                    tickets_processed=success_count
                )
                db.session.add(metadata)
            
        except Exception as e:
            logger.error(f"❌ Error updating sync metadata: {e}")
    
    def get_closures_for_period(self, period='today', target_date=None):
        """
        Get ticket closures for a specific time period
        """
        if target_date is None:
            target_date = date.today()
        
        try:
            if period == 'today':
                return self._get_daily_closures(target_date)
            elif period == 'yesterday':
                return self._get_daily_closures(target_date - timedelta(days=1))
            elif period == 'week':
                return self._get_period_closures(target_date - timedelta(days=7), target_date)
            elif period == 'month':
                return self._get_period_closures(target_date - timedelta(days=30), target_date)
            else:
                logger.error(f"Invalid period: {period}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting closures for period {period}: {e}")
            return None
    
    def _get_daily_closures(self, target_date):
        """Get daily closures for a specific date"""
        try:
            # Try daily aggregated data first
            daily_records = TicketClosureDaily.query.filter_by(date=target_date).join(User).all()
            
            if daily_records:
                users_details = []
                for record in daily_records:
                    users_details.append({
                        'username': record.user.username,
                        'tickets_closed': record.tickets_closed,
                        'role': record.user.role,
                        'profile_picture': record.user.profile_picture,
                        'user_id': record.user.id,
                        'last_sync_hour': record.last_sync_hour,
                        'sync_count': record.sync_count
                    })
                
                # Sort by tickets closed (descending)
                users_details.sort(key=lambda x: x['tickets_closed'], reverse=True)
                
                return {
                    'success': True,
                    'date': target_date.isoformat(),
                    'labels': [user['username'] for user in users_details],
                    'data': [user['tickets_closed'] for user in users_details],
                    'total_closed': sum([user['tickets_closed'] for user in users_details]),
                    'top_performer': max(users_details, key=lambda x: x['tickets_closed']) if users_details else None,
                    'users': users_details,
                    'period': 'daily'
                }
            
            # Fallback to legacy TicketClosure table
            legacy_records = TicketClosure.query.filter_by(date=target_date).join(User).all()
            
            if legacy_records:
                users_details = []
                for record in legacy_records:
                    users_details.append({
                        'username': record.user.username,
                        'tickets_closed': record.tickets_closed,
                        'role': record.user.role,
                        'profile_picture': record.user.profile_picture,
                        'user_id': record.user.id
                    })
                
                users_details.sort(key=lambda x: x['tickets_closed'], reverse=True)
                
                return {
                    'success': True,
                    'date': target_date.isoformat(),
                    'labels': [user['username'] for user in users_details],
                    'data': [user['tickets_closed'] for user in users_details],
                    'total_closed': sum([user['tickets_closed'] for user in users_details]),
                    'top_performer': max(users_details, key=lambda x: x['tickets_closed']) if users_details else None,
                    'users': users_details,
                    'period': 'daily',
                    'source': 'legacy'
                }
            
            return {
                'success': True,
                'date': target_date.isoformat(),
                'labels': [],
                'data': [],
                'total_closed': 0,
                'top_performer': None,
                'users': [],
                'period': 'daily'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting daily closures: {e}")
            return None
    
    def _get_period_closures(self, start_date, end_date):
        """Get closures for a date range"""
        try:
            # Get daily records for the period
            daily_records = TicketClosureDaily.query.filter(
                and_(
                    TicketClosureDaily.date >= start_date,
                    TicketClosureDaily.date <= end_date
                )
            ).join(User).all()
            
            # Aggregate by user
            user_totals = defaultdict(lambda: {
                'username': '',
                'tickets_closed': 0,
                'role': '',
                'profile_picture': '',
                'user_id': None,
                'ticket_numbers': []
            })
            
            for record in daily_records:
                user_key = record.user_id
                user_totals[user_key]['username'] = record.user.username
                user_totals[user_key]['role'] = record.user.role
                user_totals[user_key]['profile_picture'] = record.user.profile_picture
                user_totals[user_key]['user_id'] = record.user_id
                user_totals[user_key]['tickets_closed'] += record.tickets_closed
                
                if record.ticket_numbers:
                    try:
                        numbers = json.loads(record.ticket_numbers)
                        user_totals[user_key]['ticket_numbers'].extend(numbers)
                    except:
                        pass
            
            # Convert to list and sort
            users_details = list(user_totals.values())
            users_details.sort(key=lambda x: x['tickets_closed'], reverse=True)
            
            return {
                'success': True,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'labels': [user['username'] for user in users_details],
                'data': [user['tickets_closed'] for user in users_details],
                'total_closed': sum([user['tickets_closed'] for user in users_details]),
                'top_performer': max(users_details, key=lambda x: x['tickets_closed']) if users_details else None,
                'users': users_details,
                'period': 'range'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting period closures: {e}")
            return None
    
    def get_user_ticket_details(self, username, target_date=None):
        """Get detailed ticket information for a specific user and date"""
        if target_date is None:
            target_date = date.today()
        
        try:
            user = User.query.filter_by(username=username).first()
            if not user:
                return None
            
            # Get daily record
            daily_record = TicketClosureDaily.query.filter_by(
                user_id=user.id,
                date=target_date
            ).first()
            
            if not daily_record:
                return None
            
            # Get ticket numbers
            ticket_numbers = []
            if daily_record.ticket_numbers:
                try:
                    ticket_numbers = json.loads(daily_record.ticket_numbers)
                except:
                    pass
            
            # Create ticket details from stored numbers
            tickets = []
            for ticket_id in ticket_numbers:
                tickets.append({
                    'id': ticket_id,
                    'ticket_number': f"INC-{ticket_id}",
                    'subject': f"Ticket #{ticket_id}",
                    'description': f"Ticket closed by {username} on {target_date}",
                    'status': 4,  # Assume closed
                    'priority': 2,  # Default to medium
                    'urgency': 2,   # Default to medium
                    'created_at': target_date.isoformat(),
                    'updated_at': target_date.isoformat(),
                    'resolved_at': target_date.isoformat(),
                    'tags': ['closed', 'daily-closure'],
                    'type': 'incident'
                })
            
            return {
                'success': True,
                'user': {
                    'username': username,
                    'role': user.role,
                    'profile_picture': user.profile_picture
                },
                'tickets': tickets,
                'total_tickets': len(tickets),
                'summary': {
                    'total_closed': daily_record.tickets_closed,
                    'total_open': 0,
                    'high_priority': 0
                },
                'date': target_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting user ticket details: {e}")
            return None
    
    def get_database_stats(self):
        """Get comprehensive database statistics"""
        try:
            today = date.today()
            
            # Count records
            total_history = TicketClosureHistory.query.count()
            total_daily = TicketClosureDaily.query.count()
            total_legacy = TicketClosure.query.count()
            total_mappings = FreshworksUserMapping.query.count()
            linked_mappings = FreshworksUserMapping.query.filter(
                FreshworksUserMapping.user_id.isnot(None)
            ).count()
            
            # Today's data
            today_history = TicketClosureHistory.query.filter_by(date=today).count()
            today_daily = TicketClosureDaily.query.filter_by(date=today).count()
            
            # Recent activity
            recent_syncs = TicketSyncMetadata.query.filter(
                TicketSyncMetadata.sync_date >= today - timedelta(days=7)
            ).all()
            
            recent_activity = []
            for sync in recent_syncs:
                recent_activity.append({
                    'description': f"Sync for {sync.sync_date}: {sync.tickets_processed} tickets processed",
                    'timestamp': sync.last_sync_time.isoformat()
                })
            
            return {
                'success': True,
                'database_stats': {
                    'total_history_records': total_history,
                    'total_daily_records': total_daily,
                    'total_legacy_records': total_legacy,
                    'total_mappings': total_mappings,
                    'linked_mappings': linked_mappings,
                    'today_history_records': today_history,
                    'today_daily_records': today_daily
                },
                'recent_activity': recent_activity
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return None

# Global instance
ticket_closure_service = TicketClosureService() 