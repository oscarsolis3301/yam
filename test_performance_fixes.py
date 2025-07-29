#!/usr/bin/env python3
"""
Test Performance Fixes
This script tests the performance improvements made to the YAM dashboard
"""

import requests
import time
import json
from datetime import datetime

def test_session_activity_endpoint():
    """Test the optimized session activity endpoint"""
    print("🧪 Testing Session Activity Endpoint")
    print("=" * 50)
    
    url = "http://localhost:5000/api/session/activity"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test multiple rapid requests to see throttling
    start_time = time.time()
    responses = []
    
    for i in range(5):
        try:
            response = requests.post(url, headers=headers, json={
                'timestamp': int(time.time() * 1000),
                'connection_id': f'test_{i}',
                'last_activity': int(time.time() * 1000)
            })
            responses.append({
                'request': i + 1,
                'status': response.status_code,
                'response_time': response.elapsed.total_seconds()
            })
            print(f"Request {i+1}: Status {response.status_code}, Time: {response.elapsed.total_seconds():.3f}s")
        except Exception as e:
            print(f"Request {i+1}: Error - {e}")
    
    total_time = time.time() - start_time
    print(f"\nTotal time for 5 requests: {total_time:.3f}s")
    print(f"Average response time: {total_time/5:.3f}s")
    
    return responses

def test_ticket_closures_endpoint():
    """Test the ticket closures endpoint with caching"""
    print("\n🧪 Testing Ticket Closures Endpoint")
    print("=" * 50)
    
    url = "http://localhost:5000/api/tickets/closures/today"
    headers = {
        'Accept': 'application/json'
    }
    
    # Test first request (should be slower)
    print("First request (cache miss):")
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers)
        first_time = time.time() - start_time
        print(f"Status: {response.status_code}, Time: {first_time:.3f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Data received: {len(data.get('labels', []))} users, {data.get('total_closed', 0)} tickets")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Test second request (should be faster due to caching)
    print("\nSecond request (cache hit):")
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers)
        second_time = time.time() - start_time
        print(f"Status: {response.status_code}, Time: {second_time:.3f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Data received: {len(data.get('labels', []))} users, {data.get('total_closed', 0)} tickets")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    print(f"\nPerformance improvement: {((first_time - second_time) / first_time * 100):.1f}% faster")

def test_session_time_remaining():
    """Test the session time remaining endpoint"""
    print("\n🧪 Testing Session Time Remaining Endpoint")
    print("=" * 50)
    
    url = "http://localhost:5000/api/session/time-remaining"
    headers = {
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            print(f"Time remaining: {data.get('time_remaining_seconds', 0)} seconds")
            print(f"Session healthy: {data.get('session_healthy', False)}")
        elif response.status_code == 500:
            print("❌ Server error - check if import error is fixed")
        else:
            print(f"Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all performance tests"""
    print("🚀 YAM Dashboard Performance Fixes Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test session time remaining first (should fix import error)
    test_session_time_remaining()
    
    # Test session activity endpoint
    test_session_activity_endpoint()
    
    # Test ticket closures endpoint
    test_ticket_closures_endpoint()
    
    print("\n✅ Performance tests completed!")
    print("\nExpected improvements:")
    print("- Session activity polling reduced from every 3s to every 30s")
    print("- Session health checks reduced from every 30s to every 2-5 minutes")
    print("- Ticket closure data cached for 5 minutes")
    print("- Database updates throttled to every 60 seconds")
    print("- Import error in session time remaining fixed")

if __name__ == "__main__":
    main() 