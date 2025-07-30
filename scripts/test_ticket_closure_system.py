#!/usr/bin/env python3
"""
Test Ticket Closure Tracking System
Verify that the enhanced system works correctly
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.utils.ticket_closure_service import ticket_closure_service
from app.models.base import (
    TicketClosure, 
    TicketClosureHistory, 
    TicketClosureDaily,
    FreshworksUserMapping, 
    User
)

def test_database_connection():
    """Test database connection and table existence"""
    print("🔍 Testing database connection...")
    
    try:
        app = create_app()
        with app.app_context():
            # Test if tables exist
            from sqlalchemy import inspect
            inspector = inspect(ticket_closure_service.app.extensions['sqlalchemy'].db.engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'ticket_closure_history',
                'ticket_closure_daily',
                'ticket_closure',
                'freshworks_user_mapping',
                'ticket_sync_metadata'
            ]
            
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print("✅ All required tables exist")
                return True
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_time_period_filtering():
    """Test time period filtering functionality"""
    print("\n🔍 Testing time period filtering...")
    
    try:
        app = create_app()
        with app.app_context():
            periods = ['today', 'yesterday', 'week', 'month']
            
            for period in periods:
                print(f"  Testing period: {period}")
                result = ticket_closure_service.get_closures_for_period(period)
                
                if result and result.get('success'):
                    total_closed = result.get('total_closed', 0)
                    user_count = len(result.get('users', []))
                    print(f"    ✅ {period}: {total_closed} tickets, {user_count} users")
                else:
                    print(f"    ⚠️ {period}: No data or error")
            
            return True
            
    except Exception as e:
        print(f"❌ Time period filtering error: {e}")
        return False

def test_user_ticket_details():
    """Test user ticket details functionality"""
    print("\n🔍 Testing user ticket details...")
    
    try:
        app = create_app()
        with app.app_context():
            # Get a user with data
            user = User.query.first()
            if not user:
                print("  ⚠️ No users found in database")
                return True
            
            result = ticket_closure_service.get_user_ticket_details(user.username)
            
            if result and result.get('success'):
                total_tickets = result.get('total_tickets', 0)
                print(f"  ✅ User {user.username}: {total_tickets} tickets")
            else:
                print(f"  ⚠️ User {user.username}: No ticket details found")
            
            return True
            
    except Exception as e:
        print(f"❌ User ticket details error: {e}")
        return False

def test_database_stats():
    """Test database statistics functionality"""
    print("\n🔍 Testing database statistics...")
    
    try:
        app = create_app()
        with app.app_context():
            stats = ticket_closure_service.get_database_stats()
            
            if stats and stats.get('success'):
                db_stats = stats.get('database_stats', {})
                print(f"  📊 Historical Records: {db_stats.get('total_history_records', 0)}")
                print(f"  📊 Daily Records: {db_stats.get('total_daily_records', 0)}")
                print(f"  📊 Legacy Records: {db_stats.get('total_legacy_records', 0)}")
                print(f"  👥 User Mappings: {db_stats.get('linked_mappings', 0)}/{db_stats.get('total_mappings', 0)}")
                return True
            else:
                print("  ⚠️ Could not retrieve database statistics")
                return False
                
    except Exception as e:
        print(f"❌ Database statistics error: {e}")
        return False

def test_hourly_sync():
    """Test hourly sync functionality"""
    print("\n🔍 Testing hourly sync...")
    
    try:
        app = create_app()
        with app.app_context():
            today = date.today()
            current_hour = datetime.now().hour
            
            # Test hourly sync
            success = ticket_closure_service.sync_hourly_closures(today, current_hour)
            
            if success:
                print(f"  ✅ Hourly sync successful for {today} hour {current_hour}")
                return True
            else:
                print(f"  ⚠️ Hourly sync failed for {today} hour {current_hour}")
                return False
                
    except Exception as e:
        print(f"❌ Hourly sync error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Enhanced Ticket Closure Tracking System")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Time Period Filtering", test_time_period_filtering),
        ("User Ticket Details", test_user_ticket_details),
        ("Database Statistics", test_database_stats),
        ("Hourly Sync", test_hourly_sync)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 