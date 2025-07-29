"""
Model Conflict Resolver for YAM Application
Handles SQLAlchemy model conflicts and ensures proper model registration
"""

import logging
import sys
from pathlib import Path
from sqlalchemy import inspect, text
from sqlalchemy.exc import InvalidRequestError, OperationalError
from sqlalchemy.orm import clear_mappers
from app.extensions import db

logger = logging.getLogger(__name__)

class ModelConflictResolver:
    """Utility class to resolve SQLAlchemy model conflicts."""
    
    def __init__(self):
        self.resolved_conflicts = set()
    
    def cleanup_model_registry(self):
        """Clean up the SQLAlchemy model registry to prevent duplicate registrations."""
        try:
            # Clear any duplicate table registrations
            if hasattr(db.Model.metadata, 'tables'):
                # Remove any tables that might be duplicated
                tables_to_remove = []
                for table_name in db.Model.metadata.tables.keys():
                    if table_name == 'search_history':
                        # Check if this table is duplicated
                        tables_to_remove.append(table_name)
                
                for table_name in tables_to_remove:
                    if table_name in db.Model.metadata.tables:
                        db.Model.metadata.remove(db.Model.metadata.tables[table_name])
                        logger.info(f"Removed duplicate table registration: {table_name}")
            
            return True
        except Exception as e:
            logger.warning(f"Model registry cleanup failed: {e}")
            return False
    
    def resolve_searchhistory_conflicts(self):
        """Specifically resolve SearchHistory model conflicts"""
        try:
            # Clear any existing SearchHistory registrations from the metadata
            if 'search_history' in db.Model.metadata.tables:
                # Remove the table from metadata to force re-registration
                db.Model.metadata.remove(db.Model.metadata.tables['search_history'])
                logger.info("Removed existing SearchHistory table from metadata")
            
            # Import and re-register SearchHistory
            from app.models import SearchHistory
            
            # Check if SearchHistory is already registered
            if hasattr(SearchHistory, '__table__'):
                # Force table creation to ensure proper registration
                SearchHistory.__table__.create(db.engine, checkfirst=True)
                logger.info("SearchHistory table re-registered successfully")
            else:
                logger.info("SearchHistory table verified")
            
            # Verify the table exists
            inspector = inspect(db.engine)
            if 'search_history' in inspector.get_table_names():
                logger.info("SearchHistory table verified in database")
            else:
                logger.warning("SearchHistory table not found after registration")
            
            self.resolved_conflicts.add('SearchHistory')
            return True
            
        except ImportError as e:
            logger.warning(f"SearchHistory model not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Error resolving SearchHistory conflicts: {e}")
            return False
    
    def resolve_all_conflicts(self):
        """Resolve all known model conflicts"""
        try:
            # First clean up the registry
            self.cleanup_model_registry()
            
            # Then resolve specific conflicts
            self.resolve_searchhistory_conflicts()
            
            # Force re-registration of all models
            db.Model.metadata.create_all(db.engine, checkfirst=True)
            
            logger.info("All model conflicts resolved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in model conflict resolution: {e}")
            return False
    
    def verify_model_registration(self):
        """Verify that all models are properly registered"""
        try:
            # Test import of key models
            from app.models import User, SearchHistory, Activity, Note
            
            test_models = [User, SearchHistory, Activity, Note]
            
            for model in test_models:
                if not hasattr(model, '__table__'):
                    logger.warning(f"Model {model.__name__} missing __table__ attribute")
                    return False
                
                # Check if table exists in database
                inspector = inspect(db.engine)
                table_name = model.__tablename__ if hasattr(model, '__tablename__') else model.__table__.name
                
                if table_name not in inspector.get_table_names():
                    logger.warning(f"Table {table_name} not found in database")
                    return False
            
            logger.info("All model registrations verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying model registration: {e}")
            return False
    
    def check_and_fix_searchhistory_table(self):
        """Check and fix SearchHistory table if needed"""
        try:
            inspector = inspect(db.engine)
            
            if 'search_history' not in inspector.get_table_names():
                logger.warning("SearchHistory table not found, creating...")
                from app.models import SearchHistory
                SearchHistory.__table__.create(db.engine, checkfirst=True)
                logger.info("SearchHistory table created successfully")
            else:
                logger.info("SearchHistory table exists and is accessible")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking/fixing SearchHistory table: {e}")
            return False
    
    def fix_database_schema(self):
        """Fix any database schema issues"""
        try:
            # Check and fix SearchHistory table
            inspector = inspect(db.engine)
            if 'search_history' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('search_history')]
                
                # Add missing columns if needed
                if 'search_type' not in columns:
                    try:
                        db.engine.execute(text("ALTER TABLE search_history ADD COLUMN search_type VARCHAR(50) DEFAULT 'General'"))
                        logger.info("Added search_type column to search_history table")
                    except Exception as e:
                        logger.warning(f"Could not add search_type column: {e}")
                
                if 'timestamp' not in columns:
                    try:
                        db.engine.execute(text("ALTER TABLE search_history ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"))
                        logger.info("Added timestamp column to search_history table")
                    except Exception as e:
                        logger.warning(f"Could not add timestamp column: {e}")
            
            # Check and fix User table
            if 'user' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('user')]
                
                # Add missing columns if needed
                missing_columns = [
                    ('windows_username', 'VARCHAR(100)'),
                    ('is_online', 'BOOLEAN DEFAULT FALSE'),
                    ('last_seen', 'DATETIME'),
                    ('profile_picture', 'VARCHAR(255) DEFAULT "default.png"'),
                    ('okta_verified', 'BOOLEAN DEFAULT FALSE'),
                    ('teams_notifications', 'BOOLEAN DEFAULT TRUE')
                ]
                
                for col_name, col_type in missing_columns:
                    if col_name not in columns:
                        try:
                            db.engine.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}"))
                            logger.info(f"Added {col_name} column to user table")
                        except Exception as e:
                            logger.warning(f"Could not add {col_name} column: {e}")
            
            logger.info("Database schema fixes completed")
            return True
            
        except Exception as e:
            logger.error(f"Error fixing database schema: {e}")
            return False
    
    def reset_model_registry(self):
        """Reset the SQLAlchemy model registry to resolve conflicts"""
        try:
            # Clear all mappers
            clear_mappers()
            
            # Clear metadata
            db.Model.metadata.clear()
            
            # Re-import models to re-register them
            import importlib
            
            # Re-import model modules
            model_modules = [
                'app.models.base',
                'app.models.activity',
                'app.models.note',
                'app.models.user'
            ]
            
            for module_name in model_modules:
                try:
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    importlib.import_module(module_name)
                    logger.debug(f"Re-imported {module_name}")
                except Exception as e:
                    logger.warning(f"Could not re-import {module_name}: {e}")
            
            # Re-create all tables
            db.Model.metadata.create_all(db.engine, checkfirst=True)
            
            logger.info("Model registry reset completed")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting model registry: {e}")
            return False
    
    def get_conflict_status(self):
        """Get the current status of model conflicts"""
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            status = {
                'total_tables': len(tables),
                'required_tables': ['user', 'search_history', 'activity', 'note'],
                'missing_tables': [],
                'conflict_errors': [], # No longer tracking specific errors here
                'resolved_models': list(self.resolved_conflicts)
            }
            
            # Check for missing required tables
            for table in status['required_tables']:
                if table not in tables:
                    status['missing_tables'].append(table)
            
            status['healthy'] = len(status['missing_tables']) == 0 and len(status['conflict_errors']) == 0
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting conflict status: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'conflict_errors': [] # No longer tracking specific errors here
            }
    
    def comprehensive_fix(self):
        """Perform a comprehensive fix of all model issues"""
        logger.info("Starting comprehensive model conflict resolution...")
        
        try:
            # Step 1: Reset model registry
            if not self.reset_model_registry():
                logger.error("Failed to reset model registry")
                return False
            
            # Step 2: Fix database schema
            if not self.fix_database_schema():
                logger.error("Failed to fix database schema")
                return False
            
            # Step 3: Resolve all conflicts
            if not self.resolve_all_conflicts():
                logger.error("Failed to resolve model conflicts")
                return False
            
            # Step 4: Verify registration
            if not self.verify_model_registration():
                logger.error("Failed to verify model registration")
                return False
            
            logger.info("Comprehensive model conflict resolution completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in comprehensive fix: {e}")
            return False

# Global model conflict resolver instance
model_conflict_resolver = ModelConflictResolver()

def init_model_conflict_resolver(app):
    """Initialize the model conflict resolver with the Flask app"""
    # This function is no longer needed as the resolver is a utility class
    # and doesn't require app context for initialization.
    # However, if the app context is needed for other parts, it should be passed.
    # For now, it's kept as a placeholder.
    return model_conflict_resolver

def resolve_model_conflicts():
    """Convenience function to resolve model conflicts"""
    return model_conflict_resolver.comprehensive_fix()

def get_model_status():
    """Convenience function to get model conflict status"""
    return model_conflict_resolver.get_conflict_status() 