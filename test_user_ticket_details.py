#!/usr/bin/env python3
"""
Test script for the user ticket details API endpoint
"""

import requests
import json
from datetime import date

def test_user_ticket_details():
    """Test the user ticket details API endpoint"""
    print("🧪 Testing User Ticket Details API Endpoint")
    print("=" * 50)
    
    # Test the API endpoint for a user we know has tickets
    try:
        # Test with Doug who has 2 tickets
        username = "Doug"
        target_date = date.today().isoformat()
        
        print(f"📊 Testing ticket details for: {username}")
        print(f"📅 Date: {target_date}")
        
        # Test the ticket details endpoint
        response = requests.get(f'http://localhost:5000/api/tickets/user-details/{username}?date={target_date}')
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✅ API returned success")
                print(f"👤 User: {data['user']['username']}")
                print(f"📅 Date: {data['date']}")
                print(f"🎫 Total tickets: {data['total_tickets']}")
                print(f"📋 Summary: {data['summary']}")
                
                if data['tickets']:
                    print(f"\n📋 Ticket Details:")
                    for i, ticket in enumerate(data['tickets'], 1):
                        print(f"  {i}. {ticket['ticket_number']} - {ticket['subject']}")
                        print(f"     Status: {ticket['status']}, Priority: {ticket['priority']}")
                else:
                    print("❌ No tickets found")
                    
            else:
                print(f"❌ API returned error: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_user_ticket_details() 