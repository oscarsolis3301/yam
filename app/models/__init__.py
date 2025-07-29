from app.extensions import db
from .base import (
    User,
    Outage,
    Document,
    Activity,
    KBArticle,
    KBAttachment,
    KBFeedback,
    SearchHistory,
    SystemSettings,
    UserSettings,
    Note,
    NoteCollaborator,
    NoteVersion,
    UserPresence,
    TimeEntry,
    SharedLink,
    ChatQA,
    APICache,
    UserMapping,
    PattersonTicket,
    PattersonCalendarEvent,
    UserCache,
    SearchIndex,
    AllowedWindowsUser,
    FreshworksUserMapping,
    TicketClosure,
    init_db
)
from .chat import (
    TeamChatMessage,
    TeamChatSession,
    TeamChatTyping,
    TeamChatSettings,
    get_recent_messages,
    get_active_participants,
    get_typing_users,
    cleanup_stale_sessions,
    cleanup_stale_typing
)
from .clock_id_cache import (
    ClockIDCache,
    SearchStats,
    get_clock_id_user,
    search_clock_ids,
    update_search_stats,
    get_popular_searches,
    get_cache_stats,
    ensure_cache_tables
)
from .private_messages import (
    PrivateMessage,
    PrivateMessageSession,
    get_conversation_messages,
    get_user_conversations,
    mark_messages_as_read,
    get_unread_count
)

def cleanup_model_registry():
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
                    print(f"Removed duplicate table registration: {table_name}")
        
        return True
    except Exception as e:
        print(f"Warning: Model registry cleanup failed: {e}")
        return False

# Ensure all models are properly registered with SQLAlchemy
# This prevents the "Multiple classes found for path" error
def ensure_model_registration():
    """Ensure all models are properly registered with SQLAlchemy to prevent conflicts."""
    try:
        # First clean up any existing registrations
        cleanup_model_registry()
        
        # Force SQLAlchemy to register all models
        db.Model.metadata.create_all(db.engine, checkfirst=True)
        return True
    except Exception as e:
        print(f"Warning: Model registration check failed: {e}")
        return False

def resolve_searchhistory_conflicts():
    """Specifically resolve SearchHistory model conflicts."""
    try:
        from sqlalchemy import inspect
        
        # Clear any existing SearchHistory registrations from the metadata
        if 'search_history' in db.Model.metadata.tables:
            # Remove the table from metadata to force re-registration
            db.Model.metadata.remove(db.Model.metadata.tables['search_history'])
            print("Removed existing SearchHistory table from metadata")
        
        # Force re-registration of SearchHistory
        if hasattr(SearchHistory, '__table__'):
            # Ensure the table is properly registered
            SearchHistory.__table__.create(db.engine, checkfirst=True)
            print("SearchHistory table re-registered successfully")
        
        # Verify the table exists in the database
        try:
            inspector = inspect(db.engine)
            if 'search_history' in inspector.get_table_names():
                print("SearchHistory table verified in database")
            else:
                print("Warning: SearchHistory table not found in database")
        except Exception as e:
            print(f"Warning: Could not verify SearchHistory table: {e}")
        
        return True
    except Exception as e:
        print(f"Warning: SearchHistory conflict resolution failed: {e}")
        return False

def initialize_models_safely():
    """Initialize all models with comprehensive error handling."""
    try:
        # First, clean up any existing registrations
        cleanup_model_registry()
        
        # Then ensure basic model registration
        ensure_model_registration()
        
        # Then specifically handle SearchHistory conflicts
        resolve_searchhistory_conflicts()
        
        # Finally, initialize the database
        init_db()
        
        print("Models initialized successfully")
        return True
    except Exception as e:
        print(f"Error during model initialization: {e}")
        return False

__all__ = [
    'db',
    'User',
    'Outage',
    'Document',
    'Activity',
    'KBArticle',
    'KBAttachment',
    'KBFeedback',
    'SearchHistory',
    'SystemSettings',
    'UserSettings',
    'Note',
    'NoteCollaborator',
    'NoteVersion',
    'UserPresence',
    'TimeEntry',
    'SharedLink',
    'ChatQA',
    'APICache',
    'UserMapping',
    'PattersonTicket',
    'PattersonCalendarEvent',
    'UserCache',
    'SearchIndex',
    'AllowedWindowsUser',
    'FreshworksUserMapping',
    'TicketClosure',
    'TeamChatMessage',
    'TeamChatSession',
    'TeamChatTyping',
    'TeamChatSettings',
    'get_recent_messages',
    'get_active_participants',
    'get_typing_users',
    'cleanup_stale_sessions',
    'cleanup_stale_typing',
    'ClockIDCache',
    'SearchStats',
    'get_clock_id_user',
    'search_clock_ids',
    'update_search_stats',
    'get_popular_searches',
    'get_cache_stats',
    'ensure_cache_tables',
    'PrivateMessage',
    'PrivateMessageSession',
    'get_conversation_messages',
    'get_user_conversations',
    'mark_messages_as_read',
    'get_unread_count',
    'init_db',
    'cleanup_model_registry',
    'ensure_model_registration',
    'resolve_searchhistory_conflicts',
    'initialize_models_safely'
] 