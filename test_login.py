#!/usr/bin/env python3
"""
Simple test script to debug login issues
"""

import requests
import json
import time

def test_login():
    """Test the login functionality"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== Testing Login Functionality ===")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/debug/session", timeout=5)
        print(f"✓ Server is running (Status: {response.status_code})")
    except Exception as e:
        print(f"✗ Server is not running: {e}")
        return
    
    # Test 2: Check session status before login
    try:
        response = requests.get(f"{base_url}/debug/session", timeout=5)
        session_data = response.json()
        print(f"✓ Session status before login: {session_data}")
    except Exception as e:
        print(f"✗ Could not get session status: {e}")
    
    # Test 3: Test login form
    try:
        response = requests.get(f"{base_url}/login", timeout=5)
        print(f"✓ Login form accessible (Status: {response.status_code})")
    except Exception as e:
        print(f"✗ Login form not accessible: {e}")
    
    # Test 4: Test actual login
    try:
        login_data = {
            'email': 'admin',
            'password': 'admin'  # Replace with actual password
        }
        
        # First get the login page to get any CSRF tokens if needed
        session = requests.Session()
        response = session.get(f"{base_url}/login", timeout=5)
        
        # Now attempt login
        response = session.post(f"{base_url}/login", data=login_data, timeout=10, allow_redirects=False)
        print(f"✓ Login attempt completed (Status: {response.status_code})")
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', '')
            print(f"✓ Redirect URL: {redirect_url}")
            
            # Follow the redirect
            response = session.get(f"{base_url}{redirect_url}", timeout=5)
            print(f"✓ Redirect followed (Status: {response.status_code})")
            
            # Check if we're now authenticated
            response = session.get(f"{base_url}/debug/session", timeout=5)
            session_data = response.json()
            print(f"✓ Session after login: {session_data}")
            
            if session_data.get('user_authenticated'):
                print("✓ SUCCESS: User is authenticated!")
            else:
                print("✗ FAILED: User is not authenticated after login")
        else:
            print(f"✗ Login failed - expected 302 redirect, got {response.status_code}")
            print(f"Response content: {response.text[:200]}...")
            
    except Exception as e:
        print(f"✗ Login test failed: {e}")
    
    # Test 5: Test main index route
    try:
        response = session.get(f"{base_url}/", timeout=5)
        print(f"✓ Main index route (Status: {response.status_code})")
        if response.status_code == 200:
            print("✓ SUCCESS: Can access main page after login!")
        else:
            print(f"✗ FAILED: Cannot access main page (Status: {response.status_code})")
    except Exception as e:
        print(f"✗ Main index test failed: {e}")

if __name__ == "__main__":
    test_login() 