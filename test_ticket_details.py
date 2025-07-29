#!/usr/bin/env python3
"""
Test script for the new ticket details API endpoint
"""

import requests
import json
from datetime import date

def test_ticket_details_api():
    """Test the new ticket details API endpoint"""
    print("🧪 Testing Ticket Details API Endpoint")
    print("=" * 50)
    
    # Test the API endpoint
    try:
        # First, get today's closures to see available users
        response = requests.get('http://localhost:5000/api/tickets/closures/today')
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success') and data.get('users'):
                # Get the first user to test with
                first_user = data['users'][0]
                username = first_user['username']
                
                print(f"✅ Found user: {username}")
                print(f"📊 Testing ticket details for: {username}")
                
                # Test the ticket details endpoint
                details_response = requests.get(f'http://localhost:5000/api/tickets/user-details/{username}')
                
                if details_response.status_code == 200:
                    details_data = details_response.json()
                    
                    if details_data.get('success'):
                        print("✅ Ticket details API working!")
                        print(f"📋 User: {details_data['user']['username']}")
                        print(f"📅 Date: {details_data['date']}")
                        print(f"🎟️ Total tickets: {details_data['total_tickets']}")
                        print(f"📊 Summary: {details_data['summary']}")
                        
                        if details_data['tickets']:
                            print(f"\n📋 Sample ticket:")
                            ticket = details_data['tickets'][0]
                            print(f"   Number: {ticket['ticket_number']}")
                            print(f"   Subject: {ticket['subject']}")
                            print(f"   Status: {ticket['status']}")
                            print(f"   Priority: {ticket['priority']}")
                        else:
                            print("📭 No tickets found for this user on this date")
                    else:
                        print(f"❌ API returned error: {details_data.get('error')}")
                else:
                    print(f"❌ Ticket details API failed: {details_response.status_code}")
                    print(f"Response: {details_response.text}")
            else:
                print("⚠️ No users found in closures data")
        else:
            print(f"❌ Closures API failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_ticket_details_api() 