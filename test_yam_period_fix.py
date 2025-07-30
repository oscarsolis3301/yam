#!/usr/bin/env python3
"""
Test script to verify YAM period fix for user ticket details
"""

import requests
import json
from datetime import date, timedelta

def test_yam_period_fix():
    """Test the YAM period fix for user ticket details"""
    print("🧪 Testing YAM Period Fix for User Ticket Details")
    print("=" * 60)
    
    # Test parameters
    test_username = "Nick"  # Using Nick as mentioned in the issue
    base_url = "http://localhost:5000"
    
    # Test different periods
    periods = ['today', 'yesterday', 'week', 'month']
    
    for period in periods:
        print(f"\n📅 Testing period: {period}")
        print("-" * 30)
        
        # Calculate target date based on period
        today = date.today()
        if period == 'today':
            target_date = today
        elif period == 'yesterday':
            target_date = today - timedelta(days=1)
        else:
            target_date = today  # For week/month, use today as base
        
        # Test the user ticket details endpoint
        api_url = f"{base_url}/api/tickets/user-details/{test_username}"
        params = {
            'date': target_date.isoformat(),
            'period': period
        }
        
        print(f"🌐 API URL: {api_url}")
        print(f"📊 Parameters: {params}")
        
        try:
            response = requests.get(api_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    total_tickets = data.get('total_tickets', 0)
                    tickets = data.get('tickets', [])
                    
                    print(f"✅ Success: {total_tickets} tickets found")
                    print(f"📋 Ticket count: {len(tickets)}")
                    
                    if tickets:
                        print(f"📋 Sample tickets:")
                        for i, ticket in enumerate(tickets[:3], 1):  # Show first 3 tickets
                            print(f"  {i}. {ticket.get('ticket_number', 'N/A')} - {ticket.get('subject', 'N/A')}")
                        if len(tickets) > 3:
                            print(f"  ... and {len(tickets) - 3} more")
                    else:
                        print("📋 No individual tickets returned")
                        
                else:
                    print(f"❌ API returned error: {data.get('error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error testing API: {e}")
    
    print(f"\n🎯 Test Summary:")
    print("=" * 30)
    print("✅ If you see different ticket counts for different periods,")
    print("   the period fix is working correctly!")
    print("✅ The 'yesterday' period should show yesterday's data,")
    print("   not today's data when clicked on user bars.")

if __name__ == "__main__":
    test_yam_period_fix() 