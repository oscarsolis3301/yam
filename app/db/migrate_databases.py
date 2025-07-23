#!/usr/bin/env python3
"""
Database Migration and Management Script

This script helps manage the centralized database directory and ensures
all databases are properly located and configured.
"""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple

class DatabaseManager:
    def __init__(self, db_dir: Path):
        self.db_dir = db_dir
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
    def list_databases(self) -> List[Path]:
        """List all database files in the directory."""
        db_files = []
        for ext in ['*.db', '*.sqlite', '*.sqlite3']:
            db_files.extend(self.db_dir.glob(ext))
        return sorted(db_files)
    
    def get_database_info(self, db_path: Path) -> Dict:
        """Get information about a database file."""
        info = {
            'name': db_path.name,
            'size': db_path.stat().st_size,
            'modified': db_path.stat().st_mtime,
            'tables': []
        }
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                info['tables'] = [table[0] for table in tables]
        except Exception as e:
            info['error'] = str(e)
            
        return info
    
    def backup_database(self, db_path: Path) -> Path:
        """Create a backup of a database file."""
        backup_dir = self.db_dir / 'backup'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = int(db_path.stat().st_mtime)
        backup_name = f"{db_path.stem}_{timestamp}{db_path.suffix}"
        backup_path = backup_dir / backup_name
        
        shutil.copy2(db_path, backup_path)
        return backup_path
    
    def migrate_database(self, source_path: Path, target_name: str) -> bool:
        """Migrate a database from another location to the centralized directory."""
        target_path = self.db_dir / target_name
        
        if target_path.exists():
            # Backup existing database
            self.backup_database(target_path)
            
        try:
            shutil.move(str(source_path), str(target_path))
            print(f"✓ Migrated {source_path} to {target_path}")
            return True
        except Exception as e:
            print(f"✗ Failed to migrate {source_path}: {e}")
            return False
    
    def validate_database(self, db_path: Path) -> bool:
        """Validate that a database file is accessible and not corrupted."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception as e:
            print(f"✗ Database validation failed for {db_path}: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 5):
        """Remove old backup files, keeping only the most recent ones."""
        backup_dir = self.db_dir / 'backup'
        if not backup_dir.exists():
            return
            
        backup_files = list(backup_dir.glob('*.db'))
        backup_files.extend(list(backup_dir.glob('*.sqlite')))
        
        if len(backup_files) > keep_count:
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove old backups
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                print(f"Removed old backup: {old_backup.name}")

def main():
    """Main function to run database management operations."""
    # Get the database directory
    script_dir = Path(__file__).parent
    db_manager = DatabaseManager(script_dir)
    
    print("🔍 Database Management Tool")
    print("=" * 50)
    
    # List all databases
    databases = db_manager.list_databases()
    print(f"\n📁 Found {len(databases)} database(s) in {script_dir}:")
    
    total_size = 0
    for db_path in databases:
        info = db_manager.get_database_info(db_path)
        size_mb = info['size'] / (1024 * 1024)
        total_size += size_mb
        
        print(f"\n📊 {db_path.name}")
        print(f"   Size: {size_mb:.2f} MB")
        print(f"   Tables: {len(info['tables'])}")
        if info['tables']:
            print(f"   Table names: {', '.join(info['tables'][:5])}{'...' if len(info['tables']) > 5 else ''}")
        
        # Validate database
        if db_manager.validate_database(db_path):
            print("   Status: ✓ Valid")
        else:
            print("   Status: ✗ Invalid/Corrupted")
    
    print(f"\n📈 Total database size: {total_size:.2f} MB")
    
    # Cleanup old backups
    print("\n🧹 Cleaning up old backups...")
    db_manager.cleanup_old_backups()
    
    print("\n✅ Database management complete!")

if __name__ == "__main__":
    main() 