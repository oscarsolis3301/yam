#!/usr/bin/env python3
"""
Test script for FreshService database connection and ticket retrieval
"""

import sqlite3
import os
from datetime import datetime

def test_database_connection():
    """Test the database connection and basic functionality"""
    
    # Try to find the database file
    possible_paths = [
        'app/Freshworks/tickets.db',
        'Freshworks/tickets.db',
        'tickets.db',
        '../app/Freshworks/tickets.db',
        '../Freshworks/tickets.db'
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            print(f"Found database at: {path}")
            break
    
    if not db_path:
        print("ERROR: Could not find tickets.db file")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the tickets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
        if not cursor.fetchone():
            print("ERROR: 'tickets' table not found in database")
            return False
        
        # Get table schema
        cursor.execute("PRAGMA table_info(tickets)")
        columns = cursor.fetchall()
        print(f"Tickets table has {len(columns)} columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Count total tickets
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = cursor.fetchone()[0]
        print(f"Total tickets in database: {total_tickets}")
        
        # Get a sample of tickets
        cursor.execute("SELECT id, subject, status, priority, created_at FROM tickets LIMIT 5")
        sample_tickets = cursor.fetchall()
        
        print("\nSample tickets:")
        for ticket in sample_tickets:
            print(f"  ID: {ticket[0]}, Subject: {ticket[1][:50]}..., Status: {ticket[2]}, Priority: {ticket[3]}, Created: {ticket[4]}")
        
        # Test the status and priority mappings
        print("\nStatus distribution:")
        cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
        status_counts = cursor.fetchall()
        for status, count in status_counts:
            print(f"  Status {status}: {count} tickets")
        
        print("\nPriority distribution:")
        cursor.execute("SELECT priority, COUNT(*) FROM tickets GROUP BY priority")
        priority_counts = cursor.fetchall()
        for priority, count in priority_counts:
            print(f"  Priority {priority}: {count} tickets")
        
        conn.close()
        print("\nDatabase connection test PASSED")
        return True
        
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        return False

def test_user_mapping():
    """Test user ID to name mapping"""
    
    # Try to find the IDs.txt file
    possible_paths = [
        'app/Freshworks/IDs.txt',
        'Freshworks/IDs.txt',
        'IDs.txt',
        '../app/Freshworks/IDs.txt',
        '../Freshworks/IDs.txt'
    ]
    
    ids_file = None
    for path in possible_paths:
        if os.path.exists(path):
            ids_file = path
            print(f"Found IDs.txt at: {path}")
            break
    
    if not ids_file:
        print("WARNING: Could not find IDs.txt file")
        return False
    
    try:
        mapping = {}
        with open(ids_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ' - ' in line:
                    name, user_id = line.split(' - ', 1)
                    try:
                        mapping[int(user_id)] = name.strip()
                    except ValueError:
                        continue
        
        print(f"Loaded {len(mapping)} user mappings")
        print("Sample mappings:")
        for i, (user_id, name) in enumerate(list(mapping.items())[:5]):
            print(f"  {user_id}: {name}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to load user mapping: {e}")
        return False

if __name__ == "__main__":
    print("Testing FreshService Database Connection")
    print("=" * 50)
    
    db_success = test_database_connection()
    print("\n" + "=" * 50)
    
    mapping_success = test_user_mapping()
    print("\n" + "=" * 50)
    
    if db_success and mapping_success:
        print("All tests PASSED - FreshService should work correctly")
    else:
        print("Some tests FAILED - Please check the issues above") 