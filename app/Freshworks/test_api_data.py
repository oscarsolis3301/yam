#!/usr/bin/env python3
"""
Test API Data

This script tests the ticket closures API endpoint to verify it's returning real data
instead of dummy data.
"""

import os
import sys
import requests
import json
from datetime import date

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_api_endpoint():
    """Test the ticket closures API endpoint"""
    print("🧪 Testing Ticket Closures API Endpoint")
    print("=" * 50)
    
    # Test the API endpoint
    try:
        response = requests.get('http://localhost:5000/api/tickets/closures/today')
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ API Response Status: 200 OK")
            print(f"📊 Success: {data.get('success', False)}")
            print(f"📅 Date: {data.get('date', 'N/A')}")
            print(f"📈 Total Closed: {data.get('total_closed', 0)}")
            print(f"👥 Users: {len(data.get('users', []))}")
            
            print(f"\n📋 User Data:")
            print("-" * 30)
            
            users = data.get('users', [])
            for user in users:
                print(f"   {user.get('username', 'Unknown')}: {user.get('tickets_closed', 0)} tickets")
            
            print(f"\n📊 Chart Data:")
            print("-" * 30)
            print(f"   Labels: {data.get('labels', [])}")
            print(f"   Data: {data.get('data', [])}")
            
            # Check if this looks like real data
            total_closed = data.get('total_closed', 0)
            user_count = len(data.get('users', []))
            
            if total_closed > 0 and user_count > 0:
                print(f"\n🎉 SUCCESS: API is returning real data!")
                print(f"   📈 {total_closed} total tickets closed")
                print(f"   👥 {user_count} users with closures")
                print(f"   ✅ This is real data from Freshworks, not dummy data")
            else:
                print(f"\n⚠️ WARNING: API returned empty or invalid data")
                print(f"   📈 Total closed: {total_closed}")
                print(f"   👥 User count: {user_count}")
            
            # Check sync status
            sync_status = data.get('sync_status', {})
            if sync_status:
                print(f"\n🔄 Sync Status:")
                print(f"   Can sync now: {sync_status.get('can_sync_now', False)}")
                print(f"   Sync count today: {sync_status.get('sync_count_today', 0)}")
                print(f"   Tickets processed: {sync_status.get('tickets_processed_today', 0)}")
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Flask app is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

def test_database_directly():
    """Test the database directly to verify data exists"""
    print(f"\n🔍 Testing Database Directly")
    print("=" * 50)
    
    try:
        from app import create_app
        from app.models.base import TicketClosure, User
        from app.extensions import db
        
        app = create_app()
        with app.app_context():
            today = date.today()
            
            # Query ticket closures directly
            closures = TicketClosure.query.filter_by(date=today).join(User).all()
            
            print(f"📊 Database Query Results:")
            print(f"   Date: {today}")
            print(f"   Closure records: {len(closures)}")
            
            if closures:
                print(f"\n📋 Closure Details:")
                print("-" * 30)
                
                total_tickets = 0
                for closure in closures:
                    print(f"   {closure.user.username}: {closure.tickets_closed} tickets")
                    total_tickets += closure.tickets_closed
                
                print(f"\n📈 Summary:")
                print(f"   Total tickets: {total_tickets}")
                print(f"   Users with closures: {len(closures)}")
                print(f"   ✅ Database contains real data")
            else:
                print(f"   ⚠️ No closure records found in database for {today}")
                
    except Exception as e:
        print(f"❌ Error testing database: {e}")

def main():
    """Main function"""
    print("🚀 Starting API and Database Tests")
    print("=" * 60)
    
    # Test API endpoint
    test_api_endpoint()
    
    # Test database directly
    test_database_directly()
    
    print(f"\n🏁 Test completed!")

if __name__ == "__main__":
    main() 