"""
Clock ID Cache Model

This model provides fast, persistent storage for Clock ID lookups
without requiring PowerShell scripts on every search.
"""

from datetime import datetime
from extensions import db
import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ClockIDCache(db.Model):
    """Persistent cache for Clock ID lookups."""
    
    __tablename__ = 'clock_id_cache'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    clock_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    full_name = db.Column(db.String(200))
    username = db.Column(db.String(80), index=True)
    email = db.Column(db.String(120), index=True)
    job_title = db.Column(db.String(120))
    department = db.Column(db.String(100))
    display_name = db.Column(db.String(200))
    user_principal_name = db.Column(db.String(200))
    immutable_id = db.Column(db.String(100))
    account_status = db.Column(db.String(50))
    locked_out = db.Column(db.Boolean, default=False)
    password_expired = db.Column(db.Boolean, default=False)
    password_last_reset = db.Column(db.String(50))
    bad_logon_count = db.Column(db.Integer, default=0)
    last_logon = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'clock_id': self.clock_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'username': self.username,
            'email': self.email,
            'job_title': self.job_title,
            'department': self.department,
            'display_name': self.display_name,
            'user_principal_name': self.user_principal_name,
            'immutable_id': self.immutable_id,
            'account_status': self.account_status,
            'locked_out': self.locked_out,
            'password_expired': self.password_expired,
            'password_last_reset': self.password_last_reset,
            'bad_logon_count': self.bad_logon_count,
            'last_logon': self.last_logon,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ClockIDCache {self.clock_id}: {self.full_name}>'

class SearchStats(db.Model):
    """Track search statistics for Clock IDs."""
    
    __tablename__ = 'search_stats'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    clock_id = db.Column(db.String(10), db.ForeignKey('clock_id_cache.clock_id'), nullable=False)
    search_count = db.Column(db.Integer, default=1)
    first_searched = db.Column(db.DateTime, default=datetime.utcnow)
    last_searched = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('ClockIDCache', backref=db.backref('search_stats', lazy=True))
    
    def __repr__(self):
        return f'<SearchStats {self.clock_id}: {self.search_count} searches>'

def get_cache_db_connection():
    """Get connection to the Clock ID cache database."""
    try:
        # Use the same database as the main app
        db_path = Path(__file__).parent.parent.parent / 'app' / 'db' / 'clock_id_cache.db'
        return sqlite3.connect(str(db_path))
    except Exception as e:
        logger.error(f"Failed to connect to cache database: {e}")
        return None

def get_clock_id_user(clock_id):
    """Get user data from Clock ID cache."""
    try:
        conn = get_cache_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        cursor.execute('''
            SELECT clock_id, first_name, last_name, full_name, username, email,
                   job_title, department, display_name, user_principal_name,
                   immutable_id, account_status, locked_out, password_expired,
                   password_last_reset, bad_logon_count, last_logon
            FROM clock_id_cache 
            WHERE clock_id = ?
        ''', (clock_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'clock_id': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'full_name': row[3],
                'username': row[4],
                'email': row[5],
                'job_title': row[6],
                'department': row[7],
                'display_name': row[8],
                'user_principal_name': row[9],
                'immutable_id': row[10],
                'account_status': row[11],
                'locked_out': bool(row[12]),
                'password_expired': bool(row[13]),
                'password_last_reset': row[14],
                'bad_logon_count': row[15],
                'last_logon': row[16]
            }
        return None
        
    except Exception as e:
        logger.error(f"Error getting Clock ID user {clock_id}: {e}")
        return None

def search_clock_ids(query, limit=10):
    """Search Clock IDs by partial match on name, username, or email."""
    try:
        conn = get_cache_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor()
        
        # Search in multiple fields
        search_pattern = f'%{query}%'
        cursor.execute('''
            SELECT clock_id, first_name, last_name, full_name, username, email, job_title
            FROM clock_id_cache 
            WHERE full_name LIKE ? OR username LIKE ? OR email LIKE ? OR clock_id LIKE ?
            ORDER BY 
                CASE 
                    WHEN clock_id LIKE ? THEN 1
                    WHEN full_name LIKE ? THEN 2
                    WHEN username LIKE ? THEN 3
                    ELSE 4
                END,
                full_name
            LIMIT ?
        ''', (search_pattern, search_pattern, search_pattern, search_pattern,
              f'{query}%', f'{query}%', f'{query}%', limit))
        
        results = []
        for row in cursor.fetchall():
            clock_id, first_name, last_name, full_name, username, email, job_title = row
            results.append({
                'clock_id': clock_id,
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'username': username,
                'email': email,
                'job_title': job_title
            })
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Error searching Clock IDs for '{query}': {e}")
        return []

def update_search_stats(clock_id):
    """Update search statistics for a Clock ID."""
    try:
        conn = get_cache_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Check if stats exist
        cursor.execute('SELECT id, search_count FROM search_stats WHERE clock_id = ?', (clock_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing stats
            cursor.execute('''
                UPDATE search_stats 
                SET search_count = search_count + 1, last_searched = CURRENT_TIMESTAMP
                WHERE clock_id = ?
            ''', (clock_id,))
        else:
            # Create new stats
            cursor.execute('''
                INSERT INTO search_stats (clock_id, search_count, first_searched, last_searched)
                VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (clock_id,))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating search stats for {clock_id}: {e}")
        return False

def get_popular_searches(limit=10):
    """Get most frequently searched Clock IDs."""
    try:
        conn = get_cache_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.clock_id, s.search_count, c.full_name, c.username
            FROM search_stats s
            JOIN clock_id_cache c ON s.clock_id = c.clock_id
            ORDER BY s.search_count DESC, s.last_searched DESC
            LIMIT ?
        ''', (limit,))
        
        results = []
        for row in cursor.fetchall():
            clock_id, search_count, full_name, username = row
            results.append({
                'clock_id': clock_id,
                'search_count': search_count,
                'full_name': full_name,
                'username': username
            })
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Error getting popular searches: {e}")
        return []

def get_cache_stats():
    """Get cache statistics."""
    try:
        conn = get_cache_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM clock_id_cache')
        total_users = cursor.fetchone()[0]
        
        # Users with email
        cursor.execute('SELECT COUNT(*) FROM clock_id_cache WHERE email IS NOT NULL AND email != ""')
        users_with_email = cursor.fetchone()[0]
        
        # Users with job title
        cursor.execute('SELECT COUNT(*) FROM clock_id_cache WHERE job_title IS NOT NULL AND job_title != ""')
        users_with_title = cursor.fetchone()[0]
        
        # Total searches
        cursor.execute('SELECT COUNT(*) FROM search_stats')
        total_searches = cursor.fetchone()[0]
        
        # Most recent update
        cursor.execute('SELECT MAX(created_at) FROM clock_id_cache')
        last_updated = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'users_with_email': users_with_email,
            'users_with_title': users_with_title,
            'total_searches': total_searches,
            'last_updated': last_updated
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return None

def ensure_cache_tables():
    """Ensure cache tables exist in the database."""
    try:
        conn = get_cache_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clock_id_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clock_id TEXT UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                full_name TEXT,
                username TEXT,
                email TEXT,
                job_title TEXT,
                department TEXT,
                display_name TEXT,
                user_principal_name TEXT,
                immutable_id TEXT,
                account_status TEXT,
                locked_out BOOLEAN DEFAULT FALSE,
                password_expired BOOLEAN DEFAULT FALSE,
                password_last_reset TEXT,
                bad_logon_count INTEGER DEFAULT 0,
                last_logon TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clock_id TEXT NOT NULL,
                search_count INTEGER DEFAULT 1,
                first_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clock_id) REFERENCES clock_id_cache (clock_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clock_id ON clock_id_cache (clock_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON clock_id_cache (username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON clock_id_cache (email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_full_name ON clock_id_cache (full_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_stats_clock_id ON search_stats (clock_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_stats_count ON search_stats (search_count DESC)')
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring cache tables: {e}")
        return False 