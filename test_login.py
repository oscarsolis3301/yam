#!/usr/bin/env python3
"""
Simple test script to verify login functionality
"""

import requests
import time

def test_login():
    base_url = "http://127.0.0.1:5000"
    
    print("Testing login functionality...")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/login-ready", timeout=5)
        print(f"✓ Server is running (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"✗ Server is not running: {e}")
        return False
    
    # Test 2: Check login page
    try:
        response = requests.get(f"{base_url}/login", timeout=5)
        if response.status_code == 200:
            print("✓ Login page is accessible")
        else:
            print(f"✗ Login page returned status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot access login page: {e}")
        return False
    
    # Test 3: Test login with admin credentials
    try:
        login_data = {
            'email': 'admin',
            'password': 'admin'
        }
        response = requests.post(f"{base_url}/login", data=login_data, timeout=10, allow_redirects=False)
        
        if response.status_code == 302:  # Redirect after successful login
            print("✓ Login successful (redirected)")
            print(f"  Redirect location: {response.headers.get('Location', 'Unknown')}")
        elif response.status_code == 200:
            print("⚠ Login page returned (might be successful or failed)")
        else:
            print(f"✗ Login failed with status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Login request failed: {e}")
        return False
    
    print("\nLogin test completed!")
    return True

if __name__ == "__main__":
    test_login() 