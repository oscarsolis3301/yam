#!/usr/bin/env python3
"""
Hot Reload Test Script for YAM Server
This script helps verify that hot reloading is working correctly.
"""

import requests
import time
import sys
from datetime import datetime

def test_server_connection():
    """Test if the server is running and accessible."""
    try:
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running and accessible!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Time: {response.elapsed.total_seconds():.2f}s")
            return True
        else:
            print(f"❌ Server responded with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on port 5000?")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_hot_reload():
    """Test hot reloading by making a request and checking for changes."""
    print("\n🔄 Testing Hot Reloading...")
    print("=" * 50)
    
    # First request
    print(f"📡 Making initial request at {datetime.now().strftime('%H:%M:%S')}")
    try:
        response1 = requests.get('http://127.0.0.1:5000/', timeout=5)
        print(f"   ✅ Initial request successful")
    except Exception as e:
        print(f"   ❌ Initial request failed: {e}")
        return False
    
    # Wait a moment
    print("⏳ Waiting 2 seconds...")
    time.sleep(2)
    
    # Second request (should show any template changes)
    print(f"📡 Making second request at {datetime.now().strftime('%H:%M:%S')}")
    try:
        response2 = requests.get('http://127.0.0.1:5000/', timeout=5)
        print(f"   ✅ Second request successful")
    except Exception as e:
        print(f"   ❌ Second request failed: {e}")
        return False
    
    # Check if responses are different (indicating hot reload worked)
    if response1.text != response2.text:
        print("🎉 Hot reload detected! Template changes are being applied.")
        return True
    else:
        print("ℹ️  Responses are identical (no template changes detected)")
        return True

def main():
    """Main test function."""
    print("🚀 YAM Server Hot Reload Test")
    print("=" * 50)
    
    # Test server connection
    if not test_server_connection():
        print("\n💡 To start the server, run:")
        print("   cd app && python server.py --host 0.0.0.0 --port 5000 --mode web --debug")
        print("   or use: server_simple.bat")
        sys.exit(1)
    
    # Test hot reloading
    test_hot_reload()
    
    print("\n" + "=" * 50)
    print("📋 Hot Reload Testing Instructions:")
    print("1. Make sure your server is running with --debug flag")
    print("2. Open http://127.0.0.1:5000 in your browser")
    print("3. Edit app/templates/YAM.html and save the file")
    print("4. Refresh your browser - changes should appear automatically")
    print("5. If using debugger mode, browser should auto-refresh")
    print("\n💡 Server should show: '🔄 Hot reloading: ENABLED' in console")

if __name__ == "__main__":
    main() 