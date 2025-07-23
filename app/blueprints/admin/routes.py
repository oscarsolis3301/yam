from flask import jsonify, request, render_template, redirect, url_for, flash, current_app, has_app_context
from flask_login import login_required, current_user
from flask_socketio import emit
from extensions import db, socketio
from app.models import User, Outage, Document, Activity, KBArticle, ChatQA
from datetime import datetime, timedelta
import json
import logging
from . import bp  # Re-use the Blueprint created in app.blueprints.admin.__init__
from app.utils.ai_helpers import generate_cache_key, set_cached_response  # Cache helpers
from sqlalchemy.sql import text
import time
from app.blueprints.utils.db import safe_commit

logger = logging.getLogger('spark')

# ---------------------------------------------------------------------------
# Chat history caching helpers – avoid expensive queries on every page load
# ---------------------------------------------------------------------------

# Simple in-memory cache (process-wide).  Because gunicorn/eventlet workers run
# in separate processes this is **not** shared cluster-wide which is fine for
# the current single-process dev setup.  The cache expires after
# ``CHAT_HISTORY_TTL`` seconds or when an entry is added/updated/deleted.

_CHAT_HISTORY_CACHE: list | None = None  # cached list of ChatQA ORM objects
_CHAT_HISTORY_CACHE_TS: float = 0.0       # Unix timestamp of last refresh
CHAT_HISTORY_TTL = 60 * 2                 # 2-minute cache – tweak as needed


def _invalidate_chat_history_cache() -> None:
    """Invalidate the in-memory chat history cache."""
    global _CHAT_HISTORY_CACHE, _CHAT_HISTORY_CACHE_TS
    _CHAT_HISTORY_CACHE = None
    _CHAT_HISTORY_CACHE_TS = 0.0


def _get_chat_history_cached() -> list:
    """Return full chat history, served from an in-process cache when fresh."""
    global _CHAT_HISTORY_CACHE, _CHAT_HISTORY_CACHE_TS

    now = time.time()
    if _CHAT_HISTORY_CACHE is not None and (now - _CHAT_HISTORY_CACHE_TS) < CHAT_HISTORY_TTL:
        return _CHAT_HISTORY_CACHE  # Return cached copy

    # Cache miss or expired – fetch from DB
    history = ChatQA.query.order_by(ChatQA.timestamp.desc()).all()
    _CHAT_HISTORY_CACHE = history
    _CHAT_HISTORY_CACHE_TS = now
    return history

@bp.route('/')
@login_required
def admin():
    """Admin landing page - redirects to dashboard"""
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/dashboard')
@login_required
def admin_dashboard():
    """Render the admin dashboard"""
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    return render_template('admin/admin_dashboard.html', name=current_user.username)

@bp.route('/users')
@login_required
def users():
    """Render the users management page"""
    return render_template('admin/users.html')

@bp.route('/documents')
@login_required
def documents():
    """Render the documents management page"""
    return render_template('admin/documents.html')

@bp.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        } for user in users])
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update a user"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
            
        db.session.commit()
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user"""
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/documents', methods=['GET'])
@login_required
def get_documents():
    """Get all documents"""
    try:
        documents = Document.query.all()
        return jsonify([{
            'id': doc.id,
            'title': doc.title,
            'content': doc.content,
            'created_at': doc.created_at.isoformat()
        } for doc in documents])
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/documents', methods=['POST'])
@login_required
def create_document():
    """Create a new document"""
    try:
        data = request.get_json()
        document = Document(
            title=data['title'],
            content=data['content']
        )
        db.session.add(document)
        db.session.commit()
        return jsonify({
            'id': document.id,
            'title': document.title,
            'content': document.content,
            'created_at': document.created_at.isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/documents/<int:document_id>', methods=['PUT'])
@login_required
def update_document(document_id):
    """Update a document"""
    try:
        document = Document.query.get_or_404(document_id)
        data = request.get_json()
        
        if 'title' in data:
            document.title = data['title']
        if 'content' in data:
            document.content = data['content']
            
        db.session.commit()
        return jsonify({
            'id': document.id,
            'title': document.title,
            'content': document.content,
            'created_at': document.created_at.isoformat()
        })
    except Exception as e:
        logger.error(f"Error updating document: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/documents/<int:document_id>', methods=['DELETE'])
@login_required
def delete_document(document_id):
    """Delete a document"""
    try:
        document = Document.query.get_or_404(document_id)
        db.session.delete(document)
        db.session.commit()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dashboard')
@login_required
def admin_dashboard_data():
    # Get system statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_outages = Outage.query.count()
    active_outages = Outage.query.filter_by(status='active').count()
    total_documents = Document.query.count()
    total_kb_articles = KBArticle.query.count()
    
    # Get recent activity
    recent_activity = Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()
    activity_data = [{
        'id': activity.id,
        'user': activity.user.username,
        'action': activity.action,
        'details': activity.details,
        'timestamp': activity.timestamp.isoformat()
    } for activity in recent_activity]
    
    return jsonify({
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'total_outages': total_outages,
            'active_outages': active_outages,
            'total_documents': total_documents,
            'total_kb_articles': total_kb_articles
        },
        'recent_activity': activity_data
    })

@bp.route('/api/system-status')
@login_required
def admin_system_status():
    # Get system status information
    system_status = {
        'uptime': get_system_uptime(),
        'memory_usage': get_memory_usage(),
        'cpu_usage': get_cpu_usage(),
        'disk_usage': get_disk_usage(),
        'active_connections': get_active_connections()
    }
    return jsonify(system_status)

@bp.route('/api/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'last_login': user.last_login.isoformat() if user.last_login else None
        } for user in users])
    
    elif request.method == 'POST':
        data = request.get_json()
        user = User(
            username=data['username'],
            email=data['email'],
            is_admin=data.get('is_admin', False)
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User created successfully'}), 201

@bp.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def admin_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'last_login': user.last_login.isoformat() if user.last_login else None
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.is_active = data.get('is_active', user.is_active)
        user.is_admin = data.get('is_admin', user.is_admin)
        if 'password' in data:
            user.set_password(data['password'])
        db.session.commit()
        return jsonify({'message': 'User updated successfully'})
    
    elif request.method == 'DELETE':
        db.session.delete(user)
        db.session.commit()
        return '', 204

@bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.set_password(data['password'])
    db.session.commit()
    return jsonify({'message': 'Password reset successfully'})

@bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if request.method == 'GET':
        # Get current settings from database or configuration
        settings = {
            'system_name': 'SPARK',
            'maintenance_mode': False,
            'max_upload_size': 10,  # MB
            'allowed_file_types': ['pdf', 'doc', 'docx', 'txt'],
            'session_timeout': 30,  # minutes
            'backup_frequency': 'daily'
        }
        return jsonify(settings)
    
    elif request.method == 'POST':
        data = request.get_json()
        # Update settings in database or configuration
        # Implementation depends on how settings are stored
        return jsonify({'message': 'Settings updated successfully'})

@bp.route('/api/activity')
@login_required
def admin_activity():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    activities = Activity.query.order_by(Activity.timestamp.desc())\
        .paginate(page=page, per_page=per_page)
    
    return jsonify({
        'activities': [{
            'id': activity.id,
            'user': activity.user.username,
            'action': activity.action,
            'details': activity.details,
            'timestamp': activity.timestamp.isoformat()
        } for activity in activities.items],
        'total': activities.total,
        'pages': activities.pages,
        'current_page': activities.page
    })

@bp.route('/chat-history')
@bp.route('/chat-history/')
@login_required
def chat_history():
    """View all stored Chat Q&A records. Admin only."""
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    _ensure_cache_loaded()  # Warm cache for fast JSON delivery
    return render_template('admin/chat_history.html', active_page='chat_history')

@bp.route('/chat-history/delete/<int:qa_id>', methods=['DELETE'])
@login_required
def delete_chat_history_entry(qa_id):
    """DELETE handler to remove a ChatQA record (admin only)."""
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get the record to delete
        qa = ChatQA.query.get_or_404(qa_id)

        # Delete the record
        db.session.delete(qa)
        
        # Use safe commit pattern for better error handling
        if safe_commit(db.session):
            _remove_from_cache(qa_id)  # Remove from cache only after commit
            current_app.logger.info(f"Successfully deleted ChatQA {qa_id}")
            return jsonify({'status': 'deleted'})
        else:
            current_app.logger.error(f"Failed to commit deletion of ChatQA {qa_id}")
            return jsonify({'error': 'Deletion failed - database commit error'}), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete ChatQA {qa_id}: {e}")
        return jsonify({'error': f'Deletion failed: {str(e)}'}), 500
    finally:
        # Ensure session is properly cleaned up
        try:
            db.session.close()
        except Exception as cleanup_error:
            current_app.logger.warning(f"Error during session cleanup: {cleanup_error}")

@bp.route('/chat-history/update/<int:qa_id>', methods=['PUT'])
@login_required
def update_chat_history_entry(qa_id):
    """PUT handler to update ChatQA fields (admin only). Accepts JSON."""
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        qa = ChatQA.query.get_or_404(qa_id)
        data = request.get_json() or {}
        qa.user = data.get('user', qa.user)
        qa.question = data.get('question', qa.question)
        qa.answer = data.get('answer', qa.answer)
        
        # Flush pending updates so the new values are written but the object
        # remains bound to the active session. This avoids the *Instance not
        # bound to a Session* error raised when accessing attributes after
        # commit (SQLAlchemy expires instances on commit by default).
        db.session.flush()
        _refresh_cache_record(qa)
        
        # Use safe commit pattern for better error handling
        if safe_commit(db.session):
            # Refresh AI response cache so the updated answer is served immediately
            try:
                cache_key = generate_cache_key(qa.question, '')
                set_cached_response(cache_key, qa.answer)
            except Exception as cache_err:
                current_app.logger.warning(f"Failed to refresh cache for ChatQA {qa_id}: {cache_err}")

            current_app.logger.info(f"Successfully updated ChatQA {qa_id}")
            return jsonify({'status': 'updated'})
        else:
            current_app.logger.error(f"Failed to commit update of ChatQA {qa_id}")
            return jsonify({'error': 'Update failed - database commit error'}), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update ChatQA {qa_id}: {e}")
        return jsonify({'error': f'Update failed: {str(e)}'}), 500
    finally:
        # Ensure session is properly cleaned up
        try:
            db.session.close()
        except Exception as cleanup_error:
            current_app.logger.warning(f"Error during session cleanup: {cleanup_error}")

@bp.route('/chat-history/add', methods=['POST'])
@login_required
def add_chat_history_entry():
    """POST handler to create a new ChatQA record from the admin UI."""
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    question = (data.get('question') or '').strip()
    answer   = (data.get('answer') or '').strip()
    user     = (data.get('user') or 'Jarvis').strip() or 'Jarvis'

    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400

    # Persist via helper so embedding + socket broadcast are handled centrally
    try:
        from app.utils.ai_helpers import store_qa, generate_cache_key, set_cached_response
        store_qa(user, question, answer)
        # Grab the freshly-inserted record (highest id)
        from app.models import ChatQA
        latest = ChatQA.query.order_by(ChatQA.id.desc()).first()
        qa_id = latest.id if latest else None
        ts = latest.timestamp if latest else datetime.utcnow()
        # Append to cache so next page load is instant
        if latest:
            _append_to_cache(latest)

        # Prime the cache so Jarvis can answer immediately
        cache_key = generate_cache_key(question, '')
        set_cached_response(cache_key, answer)

        # Broadcast with id so tables in other tabs can add the record inline.
        # python-socketio v6 removed the *broadcast* kwarg; omitting *to*/*room* parameters
        # achieves a global broadcast which matches the previous behaviour.
        try:
            socketio.emit('chatqa_new', {
                'id': qa_id,
                'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                'user': user,
                'question': question,
                'answer': answer,
            })
        except Exception as emit_err:
            current_app.logger.warning(f"Failed to emit chatqa_new (add): {emit_err}")

        return jsonify({
            'id': qa_id,
            'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
            'user': user,
            'question': question,
            'answer': answer
        }), 201
    except Exception as e:
        current_app.logger.error(f"Failed to create ChatQA: {e}")
        db.session.rollback()
        return jsonify({'error': 'Creation failed'}), 500

# Helper functions
def get_system_uptime():
    # Implementation depends on system
    return "24 hours"

def get_memory_usage():
    # Implementation depends on system
    return {
        'total': 8192,  # MB
        'used': 4096,   # MB
        'free': 4096    # MB
    }

def get_cpu_usage():
    # Implementation depends on system
    return {
        'usage_percent': 45.5
    }

def get_disk_usage():
    # Implementation depends on system
    return {
        'total': 102400,  # MB
        'used': 51200,    # MB
        'free': 51200     # MB
    }

def get_active_connections():
    # Implementation depends on system
    return 150

# ---------------------------------------------------------------------------
# Lightweight JSON API used by DataTables to lazy-load the remaining entries
# ---------------------------------------------------------------------------

@bp.route('/chat-history/data')
@login_required
def chat_history_data():
    """Return full ChatQA history as JSON (admin-only).

    The response is cached in-memory for a short period so multiple users / tabs
    can reuse the same dataset without hammering the database.
    """
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    # -------------------------------------------------------------------
    # Optimised server-side pagination for DataTables                    
    # -------------------------------------------------------------------
    # When DataTables initialises with ``serverSide: true`` it sends
    # a ``draw`` parameter along with ``start`` and ``length``. Detect
    # this to switch to paginated output so we never serialise the full
    # table for every request. On legacy requests (no ``draw`` present)
    # we fall back to the previous behaviour which returns the complete
    # dataset – useful for scripts that still expect the old response.
    # -------------------------------------------------------------------

    if 'draw' in request.args:
        # ---- DataTables standard parameters ----
        draw   = int(request.args.get('draw', 1))
        start  = int(request.args.get('start', 0))
        length = int(request.args.get('length', 10))

        # ---- Global search term ----
        search_value = (request.args.get('search[value]', '') or '').strip()

        # ---- Column-specific search – we only care about the *User* column ----
        # DataTables sends `columns[<idx>][search][value]` for each column when
        # `column.search()` is used client-side. Index 1 corresponds to the
        # *User* column in the table.
        user_filter = (request.args.get('columns[1][search][value]', '') or '').strip()
        if user_filter.startswith('^') and user_filter.endswith('$'):
            # Strip the regex anchors added by the client helper so we can do
            # an *exact* equality comparison instead of LIKE.
            user_filter = user_filter[1:-1]

        base_query = ChatQA.query

        # Apply user filter first (exact match for best index utilisation)
        if user_filter:
            base_query = base_query.filter(ChatQA.user == user_filter)

        # Apply global text search across other columns
        if search_value:
            like = f"%{search_value}%"
            base_query = base_query.filter(
                ChatQA.user.ilike(like) |
                ChatQA.question.ilike(like) |
                ChatQA.answer.ilike(like)
            )

        records_filtered = base_query.count()

        # ---- Ordering ----
        order_col = int(request.args.get('order[0][column]', 0))
        order_dir = request.args.get('order[0][dir]', 'desc')

        if order_col == 0:  # Date column
            if order_dir == 'asc':
                base_query = base_query.order_by(ChatQA.timestamp.asc())
            else:
                base_query = base_query.order_by(ChatQA.timestamp.desc())
        else:
            # Fallback – maintain default newest-first order
            base_query = base_query.order_by(ChatQA.timestamp.desc())

        # ---- Pagination ----
        page_qs = base_query.offset(start).limit(length).all()

        rows = []
        for qa in page_qs:
            user_obj = User.query.filter_by(username=qa.user).first()
            if user_obj and user_obj.profile_picture and user_obj.profile_picture.lower() not in ('', 'none', 'default.png'):
                pic = url_for('static', filename=f'uploads/profile_pictures/{user_obj.profile_picture}')
            else:
                pic = url_for('static', filename='uploads/profile_pictures/default.png')

            # Build array so existing front-end parser can stay unchanged
            rows.append([
                qa.timestamp.isoformat() if qa.timestamp else '',
                f'<img src="{pic}" alt="pfp" data-avatar> {qa.user}',
                qa.question,
                qa.answer,
                f'<div class="action-buttons"><button class="btn btn-sm btn-outline-light btn-action edit-qa" data-id="{qa.id}" title="Edit"><i class="bi bi-pencil"></i></button>'
                f'<button class="btn btn-sm btn-outline-danger btn-action delete-qa" data-id="{qa.id}" title="Delete"><i class="bi bi-trash"></i></button></div>'
            ])

        return jsonify({
            'draw': draw,
            'recordsTotal': ChatQA.query.count(),
            'recordsFiltered': records_filtered,
            'data': rows
        })

    # -------------------------------------------------------------------
    # Legacy full-dataset response (no pagination)                       
    # -------------------------------------------------------------------

    records = _get_chat_history_cached()

    rows = []
    for qa in records:
        user_obj = User.query.filter_by(username=qa.user).first()
        if user_obj and user_obj.profile_picture and user_obj.profile_picture.lower() not in ('', 'none', 'default.png'):
            pic = url_for('static', filename=f'uploads/profile_pictures/{user_obj.profile_picture}')
        else:
            pic = url_for('static', filename='uploads/profile_pictures/default.png')

        rows.append({
            'id': qa.id,
            'timestamp': qa.timestamp.isoformat() if qa.timestamp else '',
            'user': qa.user,
            'question': qa.question,
            'answer': qa.answer,
            'profile_picture': pic
        })

    return jsonify(rows)

# ---------------------------------------------------------------------------
# Cache maintenance helpers – keep cache warm so page loads instantly
# ---------------------------------------------------------------------------

def _ensure_cache_loaded():
    """Ensure the in-memory chat history cache is populated."""
    _get_chat_history_cached()


def _append_to_cache(record):
    """Append a newly-created ChatQA SQLAlchemy instance to the cache list."""
    global _CHAT_HISTORY_CACHE_TS
    if _CHAT_HISTORY_CACHE is not None:
        _CHAT_HISTORY_CACHE.insert(0, record)  # newest first
        _CHAT_HISTORY_CACHE_TS = time.time()


def _remove_from_cache(qa_id: int):
    """Remove a record from the cache by id (if present)."""
    global _CHAT_HISTORY_CACHE, _CHAT_HISTORY_CACHE_TS
    if _CHAT_HISTORY_CACHE is None:
        return
    _CHAT_HISTORY_CACHE = [qa for qa in _CHAT_HISTORY_CACHE if qa.id != qa_id]
    _CHAT_HISTORY_CACHE_TS = time.time()


def _refresh_cache_record(updated_qa):
    """Replace a record in the cache with the updated instance."""
    global _CHAT_HISTORY_CACHE, _CHAT_HISTORY_CACHE_TS
    if _CHAT_HISTORY_CACHE is None:
        return
    for idx, qa in enumerate(_CHAT_HISTORY_CACHE):
        if qa.id == updated_qa.id:
            _CHAT_HISTORY_CACHE[idx] = updated_qa
            _CHAT_HISTORY_CACHE_TS = time.time()
            break

# Pre-warm cache once on first request so subsequent hits are instant
@bp.before_app_request
def _prewarm_chat_history_cache():
    """Pre-warm the chat history cache with proper Flask app context checking."""
    try:
        # Only run if we have a proper Flask app context with SQLAlchemy initialized
        if not hasattr(current_app, '_got_first_request') or current_app._got_first_request:
            # Check if SQLAlchemy is properly initialized
            if not has_app_context():
                return  # No app context available
                
            # Test database connectivity before attempting cache operations
            try:
                db.session.execute(text('SELECT 1'))
                # Only proceed if database is accessible
                _ensure_cache_loaded()
            except Exception as db_err:
                # Database not ready yet, skip cache warming
                current_app.logger.debug(f"Database not ready for cache warming: {db_err}")
                return
                
    except Exception as e:
        # Log the error but don't fail the request
        if hasattr(current_app, 'logger'):
            current_app.logger.debug(f"Cache pre-warming skipped due to context issue: {e}")
        # Don't raise the exception - let the request continue 

# ---------------------------------------------------------------------------
# Auxiliary API – distinct user list (for filter dropdown)                   
# ---------------------------------------------------------------------------

@bp.route('/chat-history/users')
@login_required
def chat_history_distinct_users():
    """Get distinct users from chat history"""
    try:
        users = db.session.query(ChatQA.user).distinct().all()
        return jsonify([user[0] for user in users if user[0]])
    except Exception as e:
        logger.error(f"Error getting chat history users: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
# User Cache Management
# ---------------------------------------------------------------------------

@bp.route('/cache-management')
@login_required
def cache_management():
    """Render the cache management page"""
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    return render_template('admin/cache_management.html')

@bp.route('/clock-id-cache')
@login_required
def clock_id_cache():
    """Render the Clock ID cache management page"""
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    return render_template('admin/clock_id_cache.html', active_page='clock_id_cache')

@bp.route('/api/cache/stats')
@login_required
def admin_cache_stats():
    """Get cache statistics for admin dashboard"""
    try:
        from app.models import UserCache
        total_entries = UserCache.query.count()
        recent_entries = UserCache.query.filter(
            UserCache.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        # Get some sample entries for display
        sample_entries = UserCache.query.order_by(UserCache.created_at.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'total_entries': total_entries,
            'recent_entries': recent_entries,
            'cache_size_mb': total_entries * 0.001,  # Rough estimate
            'sample_entries': [{
                'clock_id': entry.clock_id,
                'first_name': entry.first_name,
                'last_name': entry.last_name,
                'username': entry.username,
                'email': entry.email,
                'job_title': entry.job_title,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            } for entry in sample_entries]
        }), 200
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return jsonify({'error': 'Failed to get cache stats.'}), 500

@bp.route('/api/cache/populate', methods=['POST'])
@login_required
def admin_populate_cache():
    """Populate cache with clock IDs (admin-only)"""
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    clock_ids = data.get('clock_ids', [])
    
    if not clock_ids:
        return jsonify({'error': 'No clock IDs provided'}), 400

    from app.models import UserCache
    results = {'success': [], 'failed': [], 'existing': []}
    
    for clock_id in clock_ids:
        try:
            # Check if already cached
            normalized_id = str(clock_id).lstrip('0')
            existing = UserCache.query.filter_by(clock_id=normalized_id).first()
            if existing:
                results['existing'].append(clock_id)
                continue

            # Perform AD lookup
            from pathlib import Path
            script_path = Path(__file__).resolve().parents[4] / 'scripts' / 'user_lookup.ps1'
            
            if not script_path.exists():
                results['failed'].append({'clock_id': clock_id, 'error': 'Lookup script not found'})
                continue

            import subprocess
            import json
            
            cmd = [
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', str(script_path), str(clock_id)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data_json = json.loads(result.stdout.strip())
                    if isinstance(data_json, dict) and len(data_json) > 0:
                        # Extract and cache user data
                        full_name = data_json.get('FullName') or ''
                        first_name, last_name = '', ''
                        if full_name:
                            parts = full_name.strip().split()
                            first_name = parts[0]
                            last_name = parts[-1] if len(parts) > 1 else ''

                        cached = UserCache(
                            clock_id=normalized_id,
                            first_name=first_name,
                            last_name=last_name,
                            username=data_json.get('Username'),
                            email=data_json.get('Email'),
                            job_title=data_json.get('Title'),
                        )
                        db.session.add(cached)
                        results['success'].append(clock_id)
                    else:
                        results['failed'].append({'clock_id': clock_id, 'error': 'User not found'})
                except (json.JSONDecodeError, Exception) as e:
                    results['failed'].append({'clock_id': clock_id, 'error': f'Parse error: {str(e)}'})
            else:
                results['failed'].append({'clock_id': clock_id, 'error': 'Lookup failed'})
                
        except Exception as e:
            results['failed'].append({'clock_id': clock_id, 'error': str(e)})

    # Commit all successful additions
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to commit cache entries: {str(e)}'}), 500

    return jsonify({
        'success': True,
        'results': results,
        'summary': {
            'total_processed': len(clock_ids),
            'successful': len(results['success']),
            'failed': len(results['failed']),
            'already_existed': len(results['existing'])
        }
    }), 200

@bp.route('/api/cache/clear', methods=['POST'])
@login_required
def admin_clear_cache():
    """Clear all cache entries (admin-only)"""
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from app.models import UserCache
        deleted_count = UserCache.query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Cleared {deleted_count} cache entries'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Cache clear error: {e}")
        return jsonify({'error': 'Failed to clear cache'}), 500 