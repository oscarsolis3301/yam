#!/usr/bin/env python3
"""
Simple test to check FreshService blueprint registration
"""

from flask import Flask
from app.blueprints.freshservice import bp as freshservice_bp

def test_blueprint():
    """Test blueprint registration"""
    try:
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-key'
        
        # Register the blueprint
        app.register_blueprint(freshservice_bp)
        
        # Check if it's registered
        registered_blueprints = [bp.name for bp in app.blueprints.values()]
        print(f"Registered blueprints: {registered_blueprints}")
        
        if 'freshservice' in registered_blueprints:
            print("✓ FreshService blueprint registered successfully!")
            return True
        else:
            print("✗ FreshService blueprint not registered")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing FreshService Blueprint Registration")
    print("=" * 50)
    
    success = test_blueprint()
    
    if success:
        print("\n✓ FreshService blueprint works!")
    else:
        print("\n✗ FreshService blueprint has issues") 