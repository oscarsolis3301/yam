#!/usr/bin/env python3
"""
Test script to verify the search functionality in the tickets API
"""

import requests
import json

def test_search_functionality():
    """Test the search functionality of the tickets API"""
    
    # Base URL for the API
    base_url = "http://localhost:5000/api/tickets"
    
    print("Testing Tickets API Search Functionality")
    print("=" * 50)
    
    # Test 1: Get all tickets (no filters)
    print("\n1. Testing: Get all tickets (no filters)")
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: Found {data.get('total', 0)} tickets")
            print(f"  Page: {data.get('page', 1)}/{data.get('total_pages', 1)}")
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")
    
    # Test 2: Search with a specific term
    print("\n2. Testing: Search for 'network'")
    try:
        response = requests.get(f"{base_url}?search=network")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: Found {data.get('total', 0)} tickets matching 'network'")
            if data.get('tickets'):
                print(f"  First ticket: {data['tickets'][0].get('subject', 'N/A')}")
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")
    
    # Test 3: Search with status filter
    print("\n3. Testing: Search for 'open' status")
    try:
        response = requests.get(f"{base_url}?status=open")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: Found {data.get('total', 0)} open tickets")
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")
    
    # Test 4: Combined search and status filter
    print("\n4. Testing: Search for 'email' in open tickets")
    try:
        response = requests.get(f"{base_url}?search=email&status=open")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: Found {data.get('total', 0)} open tickets matching 'email'")
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")
    
    # Test 5: Test pagination
    print("\n5. Testing: Pagination (page 1, 5 per page)")
    try:
        response = requests.get(f"{base_url}?page=1&per_page=5")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: Page {data.get('page', 1)} of {data.get('total_pages', 1)}")
            print(f"  Showing {len(data.get('tickets', []))} tickets")
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")

if __name__ == "__main__":
    test_search_functionality() 