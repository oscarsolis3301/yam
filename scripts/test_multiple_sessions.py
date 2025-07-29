#!/usr/bin/env python3
"""
Test script for YAM multiple sessions functionality
This script helps verify that multiple sessions from the same user are working correctly.
"""

import requests
import time
import json
from datetime import datetime

def test_multiple_sessions():
    """Test multiple sessions functionality."""
    
    base_url = "http://127.0.0.1:5000"
    session1 = requests.Session()
    session2 = requests.Session()
    
    print("=" * 60)
    print("🧪 TESTING YAM MULTIPLE SESSIONS FUNCTIONALITY")
    print("=" * 60)
    
    # Test 1: Login with first session
    print("\n[TEST 1] Logging in with first session...")
    login_data = {
        'login_id': 'admin',
        'password': 'admin'
    }
    
    try:
        response = session1.post(f"{base_url}/login", data=login_data)
        if response.status_code == 200 or response.status_code == 302:
            print("✅ First session login successful")
        else:
            print(f"❌ First session login failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error during first session login: {e}")
        return False
    
    # Test 2: Login with second session (should work with multiple sessions enabled)
    print("\n[TEST 2] Logging in with second session...")
    try:
        response = session2.post(f"{base_url}/login", data=login_data)
        if response.status_code == 200 or response.status_code == 302:
            print("✅ Second session login successful")
        else:
            print(f"❌ Second session login failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error during second session login: {e}")
        return False
    
    # Test 3: Check session status for both sessions
    print("\n[TEST 3] Checking session status for both sessions...")
    
    try:
        # Check first session
        response1 = session1.get(f"{base_url}/api/session/time-remaining")
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"✅ First session active: {data1.get('time_remaining', 'Unknown')} seconds remaining")
        else:
            print(f"❌ First session check failed: {response1.status_code}")
        
        # Check second session
        response2 = session2.get(f"{base_url}/api/session/time-remaining")
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"✅ Second session active: {data2.get('time_remaining', 'Unknown')} seconds remaining")
        else:
            print(f"❌ Second session check failed: {response2.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking session status: {e}")
    
    # Test 4: Access protected endpoint with both sessions
    print("\n[TEST 4] Accessing protected endpoints with both sessions...")
    
    try:
        # First session
        response1 = session1.get(f"{base_url}/api/health")
        if response1.status_code == 200:
            print("✅ First session can access protected endpoints")
        else:
            print(f"❌ First session access failed: {response1.status_code}")
        
        # Second session
        response2 = session2.get(f"{base_url}/api/health")
        if response2.status_code == 200:
            print("✅ Second session can access protected endpoints")
        else:
            print(f"❌ Second session access failed: {response2.status_code}")
            
    except Exception as e:
        print(f"❌ Error accessing protected endpoints: {e}")
    
    # Test 5: Check server configuration
    print("\n[TEST 5] Checking server configuration...")
    
    try:
        response = requests.get(f"{base_url}/api/server-info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server info retrieved")
            print(f"   • Server mode: {data.get('mode', 'Unknown')}")
            print(f"   • Session lifetime: {data.get('session_lifetime', 'Unknown')}")
            print(f"   • Multiple sessions: {data.get('multiple_sessions', 'Unknown')}")
        else:
            print(f"❌ Server info check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking server info: {e}")
    
    # Test 6: Test session activity tracking
    print("\n[TEST 6] Testing session activity tracking...")
    
    try:
        # Update activity for first session
        response1 = session1.post(f"{base_url}/api/session/activity", json={'activity': 'test'})
        if response1.status_code == 200:
            print("✅ First session activity updated")
        else:
            print(f"❌ First session activity update failed: {response1.status_code}")
        
        # Update activity for second session
        response2 = session2.post(f"{base_url}/api/session/activity", json={'activity': 'test'})
        if response2.status_code == 200:
            print("✅ Second session activity updated")
        else:
            print(f"❌ Second session activity update failed: {response2.status_code}")
            
    except Exception as e:
        print(f"❌ Error updating session activity: {e}")
    
    # Test 7: Logout both sessions
    print("\n[TEST 7] Logging out both sessions...")
    
    try:
        # Logout first session
        response1 = session1.get(f"{base_url}/logout")
        if response1.status_code == 200 or response1.status_code == 302:
            print("✅ First session logged out successfully")
        else:
            print(f"❌ First session logout failed: {response1.status_code}")
        
        # Logout second session
        response2 = session2.get(f"{base_url}/logout")
        if response2.status_code == 200 or response2.status_code == 302:
            print("✅ Second session logged out successfully")
        else:
            print(f"❌ Second session logout failed: {response2.status_code}")
            
    except Exception as e:
        print(f"❌ Error during logout: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 MULTIPLE SESSIONS TEST COMPLETED")
    print("=" * 60)
    print("If all tests passed, multiple sessions are working correctly!")
    print("You can now:")
    print("  • Open multiple browser tabs/windows")
    print("  • Log in with the same user in each")
    print("  • Use them simultaneously without conflicts")
    print("  • Restart the server without infinite loading errors")
    print("=" * 60)
    
    return True

def check_server_status():
    """Check if the YAM server is running."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print("🔍 Checking if YAM server is running...")
    
    if not check_server_status():
        print("❌ YAM server is not running!")
        print("Please start the server first using:")
        print("   app/server.bat")
        print("   or")
        print("   python app/server.py --allow-multiple-sessions")
        exit(1)
    
    print("✅ YAM server is running")
    test_multiple_sessions() 