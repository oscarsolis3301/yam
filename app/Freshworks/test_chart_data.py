#!/usr/bin/env python3
"""
Test Chart Data

This script tests the chart data to ensure all users are being returned properly
for the bar graph display.
"""

import os
import sys
from datetime import date

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.models.base import TicketClosure, User
from app.extensions import db

def test_chart_data():
    """Test the chart data to ensure all users are included"""
    print("🧪 Testing Chart Data for Bar Graph")
    print("=" * 50)
    
    try:
        app = create_app()
        with app.app_context():
            today = date.today()
            
            # Query ticket closures directly
            closures = TicketClosure.query.filter_by(date=today).join(User).all()
            
            print(f"📊 Found {len(closures)} closure records for {today}")
            
            if closures:
                print(f"\n📋 All Users with Ticket Closures:")
                print("-" * 40)
                
                # Sort by tickets closed (descending)
                closures_sorted = sorted(closures, key=lambda x: x.tickets_closed, reverse=True)
                
                total_tickets = 0
                for i, closure in enumerate(closures_sorted, 1):
                    print(f"   {i:2d}. {closure.user.username:15s}: {closure.tickets_closed:2d} tickets")
                    total_tickets += closure.tickets_closed
                
                print(f"\n📈 Summary:")
                print(f"   Total users: {len(closures)}")
                print(f"   Total tickets: {total_tickets}")
                print(f"   Average per user: {total_tickets / len(closures):.1f}")
                
                # Test the data format that would be sent to the chart
                labels = [closure.user.username for closure in closures_sorted]
                data = [closure.tickets_closed for closure in closures_sorted]
                
                print(f"\n📊 Chart Data Format:")
                print(f"   Labels: {labels}")
                print(f"   Data: {data}")
                
                # Verify each user has a value
                print(f"\n✅ Verification:")
                for i, (label, value) in enumerate(zip(labels, data)):
                    print(f"   User {i+1}: {label} -> {value} tickets (bar height)")
                
                if len(labels) == len(data) and len(labels) > 0:
                    print(f"\n🎉 SUCCESS: All {len(labels)} users have chart data!")
                    print(f"   Each user will have a bar in the graph")
                    print(f"   Bar heights range from {min(data)} to {max(data)} tickets")
                else:
                    print(f"\n❌ ERROR: Data mismatch!")
                    print(f"   Labels count: {len(labels)}")
                    print(f"   Data count: {len(data)}")
                
            else:
                print(f"⚠️ No closure records found for {today}")
                
    except Exception as e:
        print(f"❌ Error testing chart data: {e}")
        import traceback
        traceback.print_exc()

def test_user_mappings():
    """Test user mappings to ensure all users are properly linked"""
    print(f"\n🔍 Testing User Mappings")
    print("=" * 40)
    
    try:
        app = create_app()
        with app.app_context():
            from app.models.base import FreshworksUserMapping
            
            mappings = FreshworksUserMapping.query.all()
            linked_mappings = [m for m in mappings if m.user_id]
            
            print(f"📊 User Mappings:")
            print(f"   Total mappings: {len(mappings)}")
            print(f"   Linked mappings: {len(linked_mappings)}")
            print(f"   Unlinked mappings: {len(mappings) - len(linked_mappings)}")
            
            if linked_mappings:
                print(f"\n📋 Linked Users:")
                print("-" * 30)
                for mapping in linked_mappings[:10]:  # Show first 10
                    user = User.query.get(mapping.user_id)
                    if user:
                        print(f"   ✅ {mapping.freshworks_username} -> {user.username}")
                    else:
                        print(f"   ❌ {mapping.freshworks_username} -> User ID {mapping.user_id} not found")
                
                if len(linked_mappings) > 10:
                    print(f"   ... and {len(linked_mappings) - 10} more")
                
    except Exception as e:
        print(f"❌ Error testing user mappings: {e}")

def main():
    """Main function"""
    print("🚀 Starting Chart Data Tests")
    print("=" * 60)
    
    # Test chart data
    test_chart_data()
    
    # Test user mappings
    test_user_mappings()
    
    print(f"\n🏁 Chart data tests completed!")

if __name__ == "__main__":
    main() 