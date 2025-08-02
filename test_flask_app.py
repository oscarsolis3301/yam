#!/usr/bin/env python3
"""
Test script to verify Flask application startup and FreshService routes
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_flask_imports():
    """Test if we can import the Flask application"""
    try:
        from app import create_app
        print("✓ Successfully imported Flask app")
        return True
    except ImportError as e:
        print(f"✗ Failed to import Flask app: {e}")
        return False

def test_freshservice_blueprint():
    """Test if the FreshService blueprint is properly registered"""
    try:
        from app import create_app
        from app.blueprints.freshservice.routes import bp as freshservice_bp
        
        app = create_app()
        
        # Check if the blueprint is registered
        registered_blueprints = [bp.name for bp in app.blueprints.values()]
        if 'freshservice' in registered_blueprints:
            print("✓ FreshService blueprint is registered")
            return True
        else:
            print("✗ FreshService blueprint is not registered")
            print(f"Registered blueprints: {registered_blueprints}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to test FreshService blueprint: {e}")
        return False

def test_database_connection():
    """Test database connection through the Flask app context"""
    try:
        from app import create_app
        from app.blueprints.freshservice.routes import get_freshservice_db
        
        app = create_app()
        
        with app.app_context():
            conn = get_freshservice_db()
            cursor = conn.cursor()
            
            # Test a simple query
            cursor.execute("SELECT COUNT(*) FROM tickets")
            count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"✓ Database connection successful - {count} tickets found")
            return True
            
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_api_endpoints():
    """Test if the API endpoints are accessible"""
    try:
        from app import create_app
        from app.blueprints.freshservice.routes import get_tickets
        
        app = create_app()
        
        with app.test_client() as client:
            # Test the tickets page route
            response = client.get('/freshservice/tickets')
            if response.status_code == 302:  # Redirect to login
                print("✓ Tickets page route exists (redirects to login as expected)")
            else:
                print(f"⚠ Tickets page returned status {response.status_code}")
            
            # Test the API endpoint
            response = client.get('/freshservice/api/tickets')
            if response.status_code == 302:  # Redirect to login
                print("✓ API endpoint exists (redirects to login as expected)")
            else:
                print(f"⚠ API endpoint returned status {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"✗ API endpoint test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Flask Application and FreshService Integration")
    print("=" * 60)
    
    tests = [
        ("Flask App Import", test_flask_imports),
        ("FreshService Blueprint", test_freshservice_blueprint),
        ("Database Connection", test_database_connection),
        ("API Endpoints", test_api_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! FreshService should work correctly.")
    else:
        print("✗ Some tests failed. Please check the issues above.") 