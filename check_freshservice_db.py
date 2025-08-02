import sqlite3
import os

def check_freshservice_db():
    db_path = 'app/Freshworks/tickets.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tickets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets';")
        if cursor.fetchone():
            print("✓ Tickets table exists")
            
            # Get table schema
            cursor.execute("PRAGMA table_info(tickets);")
            columns = cursor.fetchall()
            print(f"Table columns: {[col[1] for col in columns]}")
            
            # Count tickets
            cursor.execute("SELECT COUNT(*) FROM tickets;")
            count = cursor.fetchone()[0]
            print(f"Total tickets: {count}")
            
            if count > 0:
                # Get a sample ticket
                cursor.execute("SELECT * FROM tickets LIMIT 1;")
                sample = cursor.fetchone()
                print(f"Sample ticket: {sample}")
            else:
                print("No tickets found in database")
        else:
            print("✗ Tickets table does not exist")
            
            # List all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"Available tables: {[table[0] for table in tables]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_freshservice_db() 