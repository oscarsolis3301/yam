#!/usr/bin/env python3
"""
Test script to verify that the fixes work
"""

import requests
import json
from datetime import datetime

def test_server_health():
    """Test basic server health"""
    try:
        response = requests.get('http://localhost:5000/api/health')
        print(f"Server health: {response.status_code}")
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print("❌ Server health check failed")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def test_login():
    """Test login functionality"""
    try:
        login_data = {
            'login_id': 'admin',
            'password': 'admin'
        }
        response = requests.post('http://localhost:5000/login', data=login_data)
        print(f"Login response: {response.status_code}")
        
        if response.status_code == 302:  # Redirect after successful login
            print("✅ Login successful")
            return True
        else:
            print("❌ Login failed")
            return False
    except Exception as e:
        print(f"❌ Login test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    try:
        # Test users endpoint
        response = requests.get('http://localhost:5000/api/users')
        print(f"Users API: {response.status_code}")
        
        # Test ticket closures endpoint
        response = requests.get('http://localhost:5000/api/tickets/closures/today')
        print(f"Ticket closures API: {response.status_code}")
        
        # Test ticket stats endpoint
        response = requests.get('http://localhost:5000/api/tickets/stats')
        print(f"Ticket stats API: {response.status_code}")
        
        print("✅ API endpoints are accessible")
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_database_connectivity():
    """Test database connectivity"""
    try:
        response = requests.get('http://localhost:5000/api/tickets/test-db')
        print(f"Database test: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Database connectivity: {data.get('success', False)}")
            if data.get('success'):
                db_status = data.get('database_status', {})
                print(f"   Tables exist: {db_status.get('tables_exist', {})}")
                print(f"   Total closures: {data.get('data_counts', {}).get('total_closures', 0)}")
            return True
        else:
            print("❌ Database test failed")
            return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing YAM Server Fixes")
    print("=" * 50)
    
    tests = [
        ("Server Health", test_server_health),
        ("Login", test_login),
        ("API Endpoints", test_api_endpoints),
        ("Database Connectivity", test_database_connectivity),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The fixes are working.")
    else:
        print("⚠️  Some tests failed. Check the server logs for more details.")

if __name__ == "__main__":
    main() 