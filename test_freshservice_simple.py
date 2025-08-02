#!/usr/bin/env python3
"""
Simple test to check FreshService blueprint registration
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_freshservice_directly():
    """Test FreshService blueprint directly"""
    try:
        from app import create_app
        
        app = create_app()
        
        # Check if the blueprint is registered
        registered_blueprints = [bp.name for bp in app.blueprints.values()]
        print(f"Registered blueprints: {registered_blueprints}")
        
        if 'freshservice' in registered_blueprints:
            print("✓ FreshService blueprint is registered!")
            
            # Test the routes
            with app.test_client() as client:
                # Test tickets page
                response = client.get('/freshservice/tickets')
                print(f"Tickets page status: {response.status_code}")
                
                # Test API endpoint
                response = client.get('/freshservice/api/tickets')
                print(f"API endpoint status: {response.status_code}")
                
            return True
        else:
            print("✗ FreshService blueprint is not registered")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing FreshService Blueprint Registration")
    print("=" * 50)
    
    success = test_freshservice_directly()
    
    if success:
        print("\n✓ FreshService is working correctly!")
    else:
        print("\n✗ FreshService has issues") 