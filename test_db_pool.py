#!/usr/bin/env python3
"""
Database Connection Pool Test Script

This script tests the database connection pool configuration and monitors
its status to help diagnose connection exhaustion issues.
"""

import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

from app.extensions import db, Config
from app.models import User
from flask import Flask

def test_db_pool():
    """Test the database connection pool configuration"""
    
    # Create a minimal Flask app for testing
    app = Flask(__name__)
    app.config.from_object(Config)
    
    with app.app_context():
        # Initialize the database
        db.init_app(app)
        
        print("=== Database Connection Pool Test ===")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Engine Options: {app.config['SQLALCHEMY_ENGINE_OPTIONS']}")
        
        # Test basic connectivity
        try:
            # Test a simple query
            result = db.session.execute(db.text('SELECT 1')).scalar()
            print(f"✓ Basic connectivity test: {result}")
            
            # Get pool statistics
            pool = db.engine.pool
            print(f"\n=== Pool Statistics ===")
            print(f"Pool size: {pool.size()}")
            print(f"Checked in: {pool.checkedin()}")
            print(f"Checked out: {pool.checkedout()}")
            print(f"Overflow: {pool.overflow()}")
            print(f"Invalid: {pool.invalid()}")
            
            utilization = (pool.checkedout() / pool.size()) * 100 if pool.size() > 0 else 0
            print(f"Utilization: {utilization:.2f}%")
            
            # Test concurrent connections
            print(f"\n=== Concurrent Connection Test ===")
            connections = []
            max_connections = min(10, pool.size() + pool.overflow())
            
            try:
                for i in range(max_connections):
                    conn = db.engine.connect()
                    connections.append(conn)
                    print(f"✓ Created connection {i+1}/{max_connections}")
                    time.sleep(0.1)
                
                print(f"✓ Successfully created {len(connections)} connections")
                
                # Test queries on each connection
                for i, conn in enumerate(connections):
                    result = conn.execute(db.text('SELECT 1')).scalar()
                    print(f"✓ Connection {i+1} query result: {result}")
                
            finally:
                # Close all connections
                for conn in connections:
                    conn.close()
                print(f"✓ Closed all {len(connections)} connections")
            
            # Check final pool state
            print(f"\n=== Final Pool State ===")
            print(f"Pool size: {pool.size()}")
            print(f"Checked in: {pool.checkedin()}")
            print(f"Checked out: {pool.checkedout()}")
            print(f"Overflow: {pool.overflow()}")
            print(f"Invalid: {pool.invalid()}")
            
            final_utilization = (pool.checkedout() / pool.size()) * 100 if pool.size() > 0 else 0
            print(f"Final utilization: {final_utilization:.2f}%")
            
            print(f"\n✓ Database connection pool test completed successfully!")
            
        except Exception as e:
            print(f"✗ Database test failed: {e}")
            return False
        
        return True

if __name__ == "__main__":
    success = test_db_pool()
    sys.exit(0 if success else 1) 