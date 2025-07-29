#!/usr/bin/env python3
"""
Test script to verify the Freshworks API endpoint works correctly
"""

import requests
import json

def test_freshworks_endpoint():
    """Test the freshworks-users endpoint"""
    base_url = "http://localhost:5000"  # Adjust if your server runs on a different port
    
    # Test the freshworks-users endpoint
    url = f"{base_url}/freshworks-linking/api/freshworks-users"
    
    print(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
            print(f"✅ Success! Found {len(data.get('freshworks_users', []))} Freshworks users")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Flask server is running")
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: Request took too long")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    test_freshworks_endpoint() 