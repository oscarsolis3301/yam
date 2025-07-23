import uuid
from datetime import datetime
import traceback
from functools import wraps

from flask import render_template, request, jsonify, abort, current_app
from flask_login import login_required, current_user

from extensions import db
from app.models import Note, NoteCollaborator, NoteVersion

from app.blueprints.collab_notes import bp

# Import search integration - use optimized search engine directly
search_engine = None

def initialize_search_engine():
    """Initialize the search engine with proper application context."""
    global search_engine
    if search_engine is not None:
        return search_engine
        
    try:
        from app.utils.optimized_search_engine import optimized_search_engine
        search_engine = optimized_search_engine
        if current_app:
            current_app.logger.info("Optimized search engine loaded successfully")
        else:
            print("Optimized search engine loaded successfully")
        return search_engine
    except ImportError as e:
        if current_app:
            current_app.logger.warning(f"Optimized search engine not available: {e}")
        else:
            print(f"Optimized search engine not available: {e}")
        search_engine = None
        return None
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Search engine initialization failed: {e}")
        else:
            print(f"Search engine initialization failed: {e}")
        search_engine = None
        return None


def handle_errors(f):
    """Decorator to handle errors gracefully in all API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Error in {f.__name__}: {str(e)}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return a user-friendly error response
            return jsonify({
                'error': 'An unexpected error occurred',
                'details': str(e),
                'function': f.__name__
            }), 500
    return decorated_function


def safe_index_note(note_id, action='index'):
    """Safely index a note with proper application context."""
    engine = initialize_search_engine()
    if not engine:
        if current_app:
            current_app.logger.warning(f"Search engine not available, skipping indexing for note {note_id}")
        else:
            print(f"Search engine not available, skipping indexing for note {note_id}")
        return  # Skip indexing if search engine is not available
        
    try:
        if action == 'index':
            # Index the note
            engine.index_single_item('note', note_id)
            if current_app:
                current_app.logger.info(f"Successfully indexed note {note_id}")
            else:
                print(f"Successfully indexed note {note_id}")
        elif action == 'delete':
            # Remove the note from search index
            engine.delete_item('note', note_id)
            if current_app:
                current_app.logger.info(f"Successfully removed note {note_id} from search index")
            else:
                print(f"Successfully removed note {note_id} from search index")
        else:
            if current_app:
                current_app.logger.warning(f"Unknown indexing action: {action}")
            else:
                print(f"Unknown indexing action: {action}")
    except Exception as e:
        # Log error but don't break the main functionality
        try:
            if current_app:
                current_app.logger.error(f"Error indexing note {note_id} with action '{action}': {e}")
            else:
                print(f"Error indexing note {note_id} with action '{action}': {e}")
        except:
            print(f"Error indexing note {note_id} with action '{action}': {e}")


def rebuild_notes_index():
    """Rebuild the entire notes index to ensure consistency."""
    engine = initialize_search_engine()
    if not engine:
        if current_app:
            current_app.logger.warning("Search engine not available, skipping notes index rebuild")
        else:
            print("Search engine not available, skipping notes index rebuild")
        return False
        
    try:
        current_app.logger.info("Starting notes index rebuild...")
        
        # Get all public notes
        public_notes = Note.query.filter_by(is_public=True).all()
        current_app.logger.info(f"Found {len(public_notes)} public notes to index")
        
        # Clear existing note index entries
        from app.models import SearchIndex
        SearchIndex.query.filter_by(content_type='note').delete()
        db.session.commit()
        current_app.logger.info("Cleared existing note index entries")
        
        # Rebuild the notes index
        engine._index_notes()
        if current_app:
            current_app.logger.info("Notes index rebuild completed successfully")
        else:
            print("Notes index rebuild completed successfully")
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error rebuilding notes index: {e}")
        return False


def resolve_model_conflicts():
    """Resolve SQLAlchemy model conflicts by ensuring proper registration."""
    try:
        # Force SQLAlchemy to resolve any model conflicts
        db.Model.metadata.create_all(db.engine, checkfirst=True)
        return True
    except Exception as e:
        current_app.logger.warning(f"Model conflict resolution failed: {e}")
        return False


def safe_query_notes(user_id):
    """Safely query notes with comprehensive error handling and fallbacks."""
    try:
        # First, try to resolve any model conflicts
        resolve_model_conflicts()
        
        # Attempt the normal query
        notes = Note.query.filter_by(user_id=user_id).order_by(Note.updated_at.desc()).all()
        return notes, None
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f"Primary note query failed: {error_msg}")
        
        # Check if it's a SearchHistory conflict
        if "Multiple classes found for path" in error_msg and "SearchHistory" in error_msg:
            current_app.logger.info("Detected SearchHistory conflict, attempting resolution...")
            
            try:
                # Try to resolve the conflict by clearing the registry
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                
                # Force a fresh query with explicit model reference
                notes = db.session.query(Note).filter(
                    Note.user_id == user_id
                ).order_by(Note.updated_at.desc()).all()
                
                current_app.logger.info("SearchHistory conflict resolved successfully")
                return notes, None
                
            except Exception as e2:
                current_app.logger.error(f"SearchHistory conflict resolution failed: {e2}")
                
                # Final fallback: try raw SQL query
                try:
                    result = db.session.execute(
                        "SELECT * FROM note WHERE user_id = :user_id ORDER BY updated_at DESC",
                        {"user_id": user_id}
                    )
                    
                    # Convert raw results to Note objects
                    notes = []
                    for row in result:
                        note = Note()
                        for column in row._mapping.keys():
                            if hasattr(note, column):
                                setattr(note, column, row._mapping[column])
                        notes.append(note)
                    
                    current_app.logger.info("Raw SQL fallback successful")
                    return notes, None
                    
                except Exception as e3:
                    current_app.logger.error(f"Raw SQL fallback failed: {e3}")
                    return [], f"All query methods failed: {error_msg}"
        
        return [], error_msg


# ---------------------------------------------------------------------------
# Page Routes
# ---------------------------------------------------------------------------

@bp.route('/')
@login_required
def notes_home():
    """Render the main notes page."""
    return render_template('collab_notes.html', active_page='notes')

@bp.route('/workspace')
@login_required
def workspace_home():
    """Render the collaborative notes workspace page (alias for main route)."""
    return render_template('collab_notes.html', active_page='workspace')


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@bp.route('/api/notes', methods=['GET', 'POST'])
@login_required
@handle_errors
def notes_collection():
    if request.method == 'GET':
        try:
            # Use the safe query function with comprehensive error handling
            notes, error = safe_query_notes(current_user.id)
            
            if error:
                current_app.logger.error(f"Error fetching notes for user {current_user.id}: {error}")
                return jsonify({'error': 'Failed to fetch notes', 'details': error}), 500
            
            # Convert notes to dictionary format safely
            notes_data = []
            for note in notes:
                try:
                    notes_data.append(note.to_dict())
                except Exception as e:
                    current_app.logger.warning(f"Error converting note {note.id} to dict: {e}")
                    # Create a basic dict if to_dict() fails
                    notes_data.append({
                        'id': getattr(note, 'id', 0),
                        'title': getattr(note, 'title', 'Unknown'),
                        'content': getattr(note, 'content', ''),
                        'user_id': getattr(note, 'user_id', current_user.id),
                        'is_public': getattr(note, 'is_public', False),
                        'share_token': getattr(note, 'share_token', ''),
                        'tags': getattr(note, 'tags', ''),
                        'created_at': getattr(note, 'created_at', datetime.utcnow()).isoformat() if getattr(note, 'created_at', None) else None,
                        'updated_at': getattr(note, 'updated_at', datetime.utcnow()).isoformat() if getattr(note, 'updated_at', None) else None,
                    })
            
            current_app.logger.info(f"User {current_user.id} fetched {len(notes_data)} notes")
            return jsonify(notes_data)
            
        except Exception as e:
            current_app.logger.error(f"Unexpected error fetching notes for user {current_user.id}: {str(e)}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': 'Failed to fetch notes', 'details': str(e)}), 500

    # POST – create a new note
    try:
        data = request.get_json() or {}
        title = data.get('title', '').strip() or 'Untitled'  # Handle empty titles
        content = data.get('content', '{}')  # Quill JSON string
        is_public = data.get('is_public', True)
        tags = data.get('tags', '')

        # Ensure model conflicts are resolved before creating
        resolve_model_conflicts()

        note = Note(
            user_id=current_user.id,
            title=title,
            content=content,
            share_token=str(uuid.uuid4())[:12],
            is_public=is_public,
            tags=tags,
        )
        db.session.add(note)
        db.session.commit()
        
        current_app.logger.info(f"User {current_user.id} created note {note.id}: {title}")
        
        # Index the note immediately for Universal Search based on privacy status
        if note.is_public:
            safe_index_note(note.id, 'index')
            current_app.logger.info(f"Note {note.id} indexed as public")
        else:
            current_app.logger.info(f"Note {note.id} created as private - not indexed")
        
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating note for user {current_user.id}: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to create note', 'details': str(e)}), 500


@bp.route('/api/notes/<int:note_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@handle_errors
def note_detail(note_id: int):
    try:
        # Resolve model conflicts before querying
        resolve_model_conflicts()
        
        note = db.session.get(Note, note_id)
        if not note:
            abort(404)

        # Authorization check – only owner can access
        if note.user_id != current_user.id:
            abort(403)

        if request.method == 'GET':
            return jsonify(note.to_dict())

        if request.method == 'PUT':
            data = request.get_json() or {}
            
            # Update fields if provided
            if 'title' in data:
                # Handle empty titles by using 'Untitled' as fallback
                note.title = data['title'].strip() or 'Untitled'
            if 'content' in data:
                note.content = data['content']
            if 'is_public' in data:
                note.is_public = data['is_public']
            if 'tags' in data:
                note.tags = data['tags']
            
            note.updated_at = datetime.utcnow()
            
            # Save version for history
            try:
                db.session.add(NoteVersion(
                    note_id=note.id, 
                    content=note.content, 
                    created_by=current_user.id
                ))
            except Exception as e:
                current_app.logger.warning(f"Failed to save note version: {e}")
                # Continue without version history if it fails
            
            db.session.commit()
            
            # Update search index based on privacy status
            if note.is_public:
                safe_index_note(note.id, 'index')
                current_app.logger.info(f"Note {note.id} updated and indexed as public")
            else:
                safe_index_note(note.id, 'delete')
                current_app.logger.info(f"Note {note.id} updated and removed from search index (now private)")
            
            return jsonify(note.to_dict())

        # DELETE
        # Remove from search index when deleted
        safe_index_note(note.id, 'delete')
        current_app.logger.info(f"Note {note.id} deleted and removed from search index")
        
        db.session.delete(note)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in note_detail for note {note_id}: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to process note', 'details': str(e)}), 500


# ---------------------------------------------------------------------------
# Search Integration
# ---------------------------------------------------------------------------

@bp.route('/api/notes/search', methods=['GET'])
@login_required
@handle_errors
def search_notes():
    """Search through user's notes."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify([])
        
        # Resolve model conflicts before querying
        resolve_model_conflicts()
        
        # Simple text search in title, content, and tags
        notes = Note.query.filter(
            Note.user_id == current_user.id,
            db.or_(
                Note.title.ilike(f'%{query}%'),
                Note.content.ilike(f'%{query}%'),
                Note.tags.ilike(f'%{query}%')
            )
        ).order_by(Note.updated_at.desc()).limit(20).all()
        
        return jsonify([n.to_dict() for n in notes])
        
    except Exception as e:
        current_app.logger.error(f"Error searching notes: {str(e)}")
        return jsonify({'error': 'Search failed', 'details': str(e)}), 500


# ---------------------------------------------------------------------------
# Public Note Access
# ---------------------------------------------------------------------------

@bp.route('/api/notes/public/<int:note_id>', methods=['GET'])
@login_required
@handle_errors
def get_public_note(note_id: int):
    """Get a public note by ID - accessible to all authenticated users."""
    try:
        resolve_model_conflicts()
        
        note = db.session.get(Note, note_id)
        if not note:
            abort(404)
        
        # Only allow access to public notes
        if not note.is_public:
            abort(403)
        
        # Return note data with author info for public viewing
        note_data = note.to_dict()
        note_data['author'] = {
            'id': note.user.id,
            'username': note.user.username
        }
        
        return jsonify(note_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting public note {note_id}: {str(e)}")
        return jsonify({'error': 'Failed to get public note', 'details': str(e)}), 500


# ---------------------------------------------------------------------------
# Tags API
# ---------------------------------------------------------------------------

@bp.route('/api/notes/tags', methods=['GET'])
@login_required
@handle_errors
def get_user_tags():
    """Get all unique tags used by the current user."""
    try:
        resolve_model_conflicts()
        
        notes = Note.query.filter_by(user_id=current_user.id).all()
        all_tags = set()
        
        for note in notes:
            if note.tags:
                tags = [tag.strip() for tag in note.tags.split(',') if tag.strip()]
                all_tags.update(tags)
        
        return jsonify(list(all_tags))
        
    except Exception as e:
        current_app.logger.error(f"Error getting user tags: {str(e)}")
        return jsonify({'error': 'Failed to get tags', 'details': str(e)}), 500


@bp.route('/api/notes/tags/<tag>', methods=['GET'])
@login_required
@handle_errors
def get_notes_by_tag(tag):
    """Get all notes with a specific tag."""
    try:
        resolve_model_conflicts()
        
        notes = Note.query.filter(
            Note.user_id == current_user.id,
            Note.tags.ilike(f'%{tag}%')
        ).order_by(Note.updated_at.desc()).all()
        
        return jsonify([n.to_dict() for n in notes])
        
    except Exception as e:
        current_app.logger.error(f"Error getting notes by tag {tag}: {str(e)}")
        return jsonify({'error': 'Failed to get notes by tag', 'details': str(e)}), 500


# ---------------------------------------------------------------------------
# Note Statistics
# ---------------------------------------------------------------------------

@bp.route('/api/notes/stats', methods=['GET'])
@login_required
@handle_errors
def note_stats():
    """Get statistics about user's notes."""
    try:
        resolve_model_conflicts()
        
        total_notes = Note.query.filter_by(user_id=current_user.id).count()
        public_notes = Note.query.filter_by(user_id=current_user.id, is_public=True).count()
        private_notes = total_notes - public_notes
        
        # Get recent activity
        recent_notes = Note.query.filter_by(user_id=current_user.id)\
            .order_by(Note.updated_at.desc())\
            .limit(5).all()
        
        return jsonify({
            'total_notes': total_notes,
            'public_notes': public_notes,
            'private_notes': private_notes,
            'recent_notes': [n.to_dict() for n in recent_notes]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting note stats: {str(e)}")
        return jsonify({'error': 'Failed to get note statistics', 'details': str(e)}), 500


@bp.route('/api/debug', methods=['GET'])
@login_required  
@handle_errors
def debug_info():
    """Debug endpoint to check if authentication and data access works."""
    try:
        resolve_model_conflicts()
        
        user_notes = Note.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'authenticated': True,
            'user_id': current_user.id,
            'username': current_user.username,
            'total_notes': len(user_notes),
            'notes_sample': [{'id': n.id, 'title': n.title} for n in user_notes[:3]],
            'model_conflicts_resolved': True
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'authenticated': current_user.is_authenticated if current_user else False,
            'model_conflicts_resolved': False
        }), 500


@bp.route('/api/admin/rebuild-notes-index', methods=['POST'])
@login_required
@handle_errors
def admin_rebuild_notes_index():
    """Admin endpoint to rebuild the notes search index."""
    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        success = rebuild_notes_index()
        if success:
            return jsonify({
                'success': True,
                'message': 'Notes index rebuilt successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to rebuild notes index'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in admin rebuild notes index: {str(e)}")
        return jsonify({'error': 'Admin rebuild failed', 'details': str(e)}), 500


@bp.route('/api/admin/sync-notes-index', methods=['POST'])
@login_required
@handle_errors
def admin_sync_notes_index():
    """Admin endpoint to sync the notes search index with the database."""
    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        engine = initialize_search_engine()
        if not engine:
            return jsonify({
                'success': False,
                'message': 'Search engine not available'
            }), 500
        
        sync_stats = engine.sync_notes_index()
        
        if 'error' in sync_stats:
            return jsonify({
                'success': False,
                'message': 'Failed to sync notes index',
                'error': sync_stats['error']
            }), 500
        else:
            return jsonify({
                'success': True,
                'message': 'Notes index synced successfully',
                'stats': sync_stats
            })
            
    except Exception as e:
        current_app.logger.error(f"Error in admin sync notes index: {str(e)}")
        return jsonify({'error': 'Admin sync failed', 'details': str(e)}), 500 