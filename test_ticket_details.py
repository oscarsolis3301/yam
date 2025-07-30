#!/usr/bin/env python3
"""
Test script to verify ticket closure service functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.ticket_closure_service import ticket_closure_service
from app.models.base import User, TicketClosure, TicketClosureDaily
from datetime import date, datetime

def test_ticket_closure_service():
    """Test the ticket closure service functionality"""
    print("🧪 Testing Ticket Closure Service...")
    
    app = create_app()
    
    with app.app_context():
        # Test 1: Check if users exist
        users = User.query.all()
        print(f"📊 Found {len(users)} users in database")
        
        if not users:
            print("❌ No users found in database")
            return
        
        # Test 2: Check ticket closure data
        today = date.today()
        legacy_closures = TicketClosure.query.filter_by(date=today).all()
        daily_closures = TicketClosureDaily.query.filter_by(date=today).all()
        
        print(f"📊 Legacy closures for today: {len(legacy_closures)}")
        print(f"📊 Daily closures for today: {len(daily_closures)}")
        
        # Test 3: Test user ticket details for a user with data
        test_user = None
        for user in users:
            # Check if user has any closure data
            legacy_data = TicketClosure.query.filter_by(user_id=user.id).first()
            daily_data = TicketClosureDaily.query.filter_by(user_id=user.id).first()
            
            if legacy_data or daily_data:
                test_user = user
                break
        
        if test_user:
            print(f"🧪 Testing with user: {test_user.username}")
            
            # Test daily details
            result = ticket_closure_service.get_user_ticket_details(test_user.username, today)
            if result and result.get('success'):
                print(f"✅ Daily details found: {result.get('total_tickets', 0)} tickets")
            else:
                print("❌ No daily details found")
            
            # Test period details
            result = ticket_closure_service.get_user_ticket_details_for_period(test_user.username, 'week')
            if result and result.get('success'):
                print(f"✅ Week period details found: {result.get('total_tickets', 0)} tickets")
            else:
                print("❌ No week period details found")
        else:
            print("⚠️ No users with ticket closure data found")
        
        # Test 4: Check database info
        db_info = ticket_closure_service.get_database_info()
        print(f"📊 Database info: {db_info}")

if __name__ == "__main__":
    test_ticket_closure_service() 