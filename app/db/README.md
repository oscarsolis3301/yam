# Centralized Database Directory

This directory contains all database files for the PDSI application, ensuring persistence across sessions and easy backup to GitHub.

## Database Files

### Core Application Databases
- **`app.db`** - Main application database (SQLAlchemy)
- **`admin_dashboard.db`** - Admin dashboard and system management data
- **`freshworks.db`** - Freshworks/Freshdesk integration data
- **`servicedesk_ai.db`** - Service desk AI and question handling

### Chat and AI Databases
- **`chat_qa.db`** - Jarvis chat history and Q&A data
- **`interactions.log.sqlite`** - User interaction logging

### User Management Databases
- **`clock_id_cache.db`** - Clock ID to user mapping cache

## Backup Directory
- **`backup/`** - Contains previous versions of database files

## Database Management

### Adding New Databases
1. Place all new `.db` and `.sqlite` files in this directory
2. Update configuration in `app/config.py` to reference the new database
3. Ensure the database is included in version control (not ignored in `.gitignore`)

### Backup Strategy
- All database files are tracked in Git for persistence across sessions
- Database files are backed up to GitHub automatically
- Previous versions are stored in the `backup/` directory

### Database Paths in Configuration
All database paths are configured in `app/config.py`:
```python
DB_DIR = BASE_DIR / 'app' / 'db'  # Centralized database directory
DB_PATH = str(DB_DIR / 'admin_dashboard.db')
QUESTIONS_DB = str(DB_DIR / 'servicedesk_ai.db')
CHAT_QA_DB = str(DB_DIR / 'chat_qa.db')
FRESHWORKS_DB = str(DB_DIR / 'freshworks.db')
```

## Migration Notes
- Previously scattered databases have been centralized here
- Old `db/` directory has been removed
- YAM `clock_id_cache.db` has been moved to this location
- All configuration files have been updated to reference the new paths 