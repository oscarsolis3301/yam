from flask import jsonify, request, current_app, url_for, send_from_directory, send_file
from flask_login import login_required, current_user
from app.extensions import db
from . import bp
import logging
from app.models import KBArticle, SharedLink, KBAttachment, KBFeedback
from datetime import datetime, timezone, timedelta
import os
from app.utils.helpers import summarize_text, generate_short_code, extract_pdf_details
from werkzeug.utils import secure_filename
import time
from app.blueprints.utils.db import safe_commit
from app.extensions import socketio
from app.utils.kb_import import import_docs_folder
from app.utils.cache import _articles_cache_lock, _articles_cache  # shared cache

logger = logging.getLogger('spark')

# --- Helper function imports ---
# These imports are done inside the route handlers to avoid circular-import issues
# with app.spark during application bootstrapping.


def _get_kb_helpers():
    """Import KB helper functions on-demand to avoid circular imports."""
    # Cache utilities live in a standalone module with no heavy dependencies,
    # so they can be imported safely at runtime.
    from app.utils.cache import (
        load_articles_cache,
        _articles_cache_lock,
        _articles_cache,
    )

    # These two helpers are now in app.utils.helpers
    from app.utils.helpers import verify_file_exists, get_document_text  # local import to avoid early circular refs

    return load_articles_cache, verify_file_exists, get_document_text, _articles_cache_lock, _articles_cache


# ---------------------------------------------------------------------------
# Public KB endpoint (no auth)
# ---------------------------------------------------------------------------

@bp.route('/test', methods=['GET'])
def test_kb_api():
    """Simple test endpoint to verify the kb_api blueprint is working."""
    return jsonify({
        'status': 'ok',
        'message': 'kb_api blueprint is working',
        'blueprint': 'kb_api',
        'url_prefix': '/api'
    })

@bp.route('/kb_public', methods=['GET'])
def get_kb_articles_public():
    """Public endpoint that lists KB articles with optional query filtering."""

    # Lazy-import to avoid circular dependency with app.spark at import time
    load_articles_cache, verify_file_exists, get_document_text, *_ = _get_kb_helpers()

    articles = load_articles_cache()
    query = request.args.get('q', '').strip().lower()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    # Filter articles based on query and file existence
    filtered_articles = []
    for article in articles:
        # Check if file exists
        file_missing = False
        if article.get('file_path'):
            if not verify_file_exists(article['file_path']):
                file_missing = True
        # Get text content for searching
        content = get_document_text(article)
        if query:
            # Search in title, content and tags
            if (
                query not in (article.get('title') or '').lower()
                and query not in content.lower()
                and not any(query in (tag or '').lower() for tag in article.get('tags', []))
            ):
                continue
        # Add file_missing flag
        article_out = dict(article)
        article_out['file_missing'] = file_missing
        filtered_articles.append(article_out)

    total = len(filtered_articles)
    paged = filtered_articles[(page - 1) * per_page : page * per_page]

    return jsonify({
        'articles': paged,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


# ---------------------------------------------------------------------------
# Admin utilities
# ---------------------------------------------------------------------------


@bp.route('/kb/force_all_public_approved', methods=['POST'])
@login_required
def force_all_kb_public_approved():
    """Force-approve all KB articles and make them public (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    # Lazy import helpers/resources
    load_articles_cache, _, _, _articles_cache_lock, _articles_cache = _get_kb_helpers()
    try:
        updated = (
            KBArticle.query.filter(
                (KBArticle.status != 'approved') | (KBArticle.is_public != True)
            ).update({
                KBArticle.status: 'approved',
                KBArticle.is_public: True,
            }, synchronize_session=False)
        )
        db.session.commit()

        # Clear cache so changes are reflected immediately
        with _articles_cache_lock:
            _articles_cache.clear()

        logger.info(
            f"[ADMIN] Forced all KB articles to public/approved. Updated: {updated}"
        )
        return jsonify({'success': True, 'updated': updated})
    except Exception as e:
        db.session.rollback()
        logger.error(f"[ADMIN] Error forcing all KB public/approved: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/kb/check-new-documents', methods=['POST'])
@login_required
def check_and_import_new_documents():
    """Check for new documents and import them if found.
    
    This endpoint is designed to be called when users want to refresh the KB
    or when new documents might have been added. It only imports if there
    are actually new or modified documents.
    """
    try:
        from app.utils.kb_import import check_for_new_documents, import_docs_folder
        
        # Check if there are new documents
        has_new_documents = check_for_new_documents()
        
        if has_new_documents:
            # Import the new documents
            import_docs_folder()
            
            # Clear cache to reflect new articles
            try:
                with _articles_cache_lock:
                    _articles_cache.clear()
            except Exception:
                pass
            
            socketio.emit('kb_update', {'type': 'refresh', 'message': 'New documents imported'})
            
            return jsonify({
                'success': True,
                'message': 'New documents found and imported',
                'has_new_documents': True
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No new documents found',
                'has_new_documents': False
            })
            
    except Exception as exc:
        logger.error(f"Error checking for new documents: {exc}")
        return jsonify({'error': str(exc)}), 500


@bp.route('/kb/refresh_cache', methods=['POST'])
@login_required
def refresh_kb_cache():
    """Refresh the KB cache without importing documents."""
    try:
        # Clear the cache
        with _articles_cache_lock:
            _articles_cache.clear()
        
        # Reload the cache
        from app.utils.cache import load_articles_cache
        load_articles_cache(force_reload=True)
        
        socketio.emit('kb_update', {'type': 'refresh', 'message': 'Cache refreshed'})
        
        return jsonify({
            'success': True,
            'message': 'KB cache refreshed successfully'
        })
        
    except Exception as exc:
        logger.error(f"Error refreshing KB cache: {exc}")
        return jsonify({'error': str(exc)}), 500


@bp.route('/kb/<int:article_id>', methods=['GET'])
def get_kb_article(article_id):
    """Return full KB article data (public). Matches original /api/kb/<id> route."""
    article = KBArticle.query.get_or_404(article_id)

    # Article still importing?
    if article.import_status == 'pending':
        return jsonify({'error': 'Article is still being imported', 'status': 'pending'}), 202

    # Visibility check
    if not article.is_public:
        return jsonify({'error': 'Article is not available', 'status': 'not_public'}), 403

    # Increment view counter in DB
    article.views += 1
    db.session.commit()

    # Collect attachment info
    attachments = []
    if article.attachments:
        for att in article.attachments:
            attachments.append({
                'id': att.id,
                'name': att.filename,
                'url': url_for('static', filename=f'uploads/{att.filename}', _external=True),
                'type': getattr(att, 'mime_type', att.file_type if hasattr(att, 'file_type') else 'application/octet-stream')
            })

    return jsonify({
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'description': article.description,
        'category': article.category,
        'tags': article.tags,
        'author': article.author,
        'created_at': article.created_at.isoformat(),
        'updated_at': article.updated_at.isoformat(),
        'views': article.views,
        'helpful_count': article.helpful_count,
        'not_helpful_count': article.not_helpful_count,
        'import_status': article.import_status,
        'status': article.status,
        'attachments': attachments,
    })


@bp.route('/kb/make_all_public', methods=['POST'])
@login_required
def make_all_kb_articles_public():
    """Bulk-update: mark every KB article public & approved (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    start_time = datetime.utcnow()
    logger = current_app.logger
    logger.info("Starting bulk update of KB articles to public")

    total_articles = KBArticle.query.count()

    try:
        # Transactional bulk updates
        updated_non_public = KBArticle.query.filter(KBArticle.is_public == False).update(  # noqa: E712
            {KBArticle.is_public: True}, synchronize_session=False
        )
        updated_pending_pdfs = KBArticle.query.filter(
            KBArticle.file_path.like('%.pdf'), KBArticle.status != 'approved'
        ).update({KBArticle.status: 'approved'}, synchronize_session=False)
        db.session.commit()

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Bulk update completed in {duration:.2f}s – {updated_non_public} non-public, {updated_pending_pdfs} pending PDFs"
        )

        return jsonify({
            'success': True,
            'updated': updated_non_public + updated_pending_pdfs,
            'total_articles': total_articles,
            'non_public_updated': updated_non_public,
            'pending_pdf_updated': updated_pending_pdfs,
            'duration_seconds': duration,
        })

    except Exception as exc:
        db.session.rollback()
        logger.error(f"Database error during bulk update: {exc}")
        return jsonify({'error': 'Database error during update', 'details': str(exc)}), 500


# ---------------------------------------------------------------------------
# Article summary & sharing endpoints (moved from app/spark.py)
# ---------------------------------------------------------------------------

@bp.route('/kb/<int:article_id>/summary', methods=['POST'])
@login_required
def generate_article_summary(article_id):
    """Return a short summary for the requested KB article (auth required)."""
    article = KBArticle.query.get_or_404(article_id)
    text = article.content or ""
    summary = summarize_text(text, max_tokens=150)
    return jsonify({'success': True, 'summary': summary})


@bp.route('/kb/<int:article_id>/share', methods=['POST'])
@login_required
def create_shared_link(article_id):
    """Create a time-limited public share link for a KB article (auth required)."""
    # Ensure article exists (404 otherwise)
    KBArticle.query.get_or_404(article_id)

    expires_in = request.json.get('expires_in', 7)  # days
    shared_link = SharedLink(
        article_id=article_id,
        short_code=generate_short_code(),
        expires_at=datetime.utcnow() + timedelta(days=expires_in),
        created_by=current_user.id,
    )

    db.session.add(shared_link)
    db.session.commit()

    return jsonify({
        'success': True,
        'short_url': f'/kb/shared/{shared_link.short_code}',
    })


# ---------------------------------------------------------------------------
# KB management routes (migrated from app/spark.py)
# ---------------------------------------------------------------------------

def _get_spark_resources():
    """Return references to objects/functions defined in app.spark lazily.

    This indirection prevents circular-import issues that would otherwise be
    triggered during application boot when app.spark imports this blueprint.
    """
    from app.previous import YAM as spark_mod  # local import at call-time

    return {
        'load_articles_cache': getattr(spark_mod, 'load_articles_cache'),
        'articles_cache_lock': getattr(spark_mod, '_articles_cache_lock'),
        'articles_cache': getattr(spark_mod, '_articles_cache'),
        'allowed_file': getattr(spark_mod, 'allowed_file'),
    }


# ---------------------------------------------------------------------------
# GET /api/kb  – List KB articles for authenticated users (with cache)
# ---------------------------------------------------------------------------

@bp.route('/kb', methods=['GET'])
@login_required
def get_kb_articles():
    res = _get_spark_resources()
    load_articles_cache = res['load_articles_cache']

    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    # Retrieve cached list and filter if necessary
    articles = load_articles_cache()
    if query:
        q = query.lower()
        articles = [
            a for a in articles
            if q in (a.get('title') or '').lower()
            or q in (a.get('description') or '').lower()
            or any(q in (tag or '').lower() for tag in a.get('tags', []))
        ]

    total = len(articles)
    paged = articles[(page - 1) * per_page : page * per_page]

    return jsonify({
        'articles': paged,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


# ---------------------------------------------------------------------------
# GET /api/kb/pending  – Admin-only list of pending / importing articles
# ---------------------------------------------------------------------------

@bp.route('/kb/pending', methods=['GET'])
@login_required
def get_pending_kb_articles():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    articles = (
        KBArticle.query.filter(
            db.or_(KBArticle.status == 'pending', KBArticle.import_status != 'completed')
        )
        .order_by(KBArticle.created_at.desc())
        .all()
    )

    return jsonify([
        {
            'id': a.id,
            'title': a.title,
            'content': a.content,
            'category': a.category,
            'tags': a.tags.split(',') if a.tags else [],
            'author': a.author.username if a.author else 'System',
            'created_at': a.created_at.isoformat(),
            'updated_at': a.updated_at.isoformat(),
            'import_status': a.import_status,
            'attachments': [
                {
                    'id': att.id,
                    'name': att.filename,
                    'type': att.file_type,
                }
                for att in a.attachments
            ],
        }
        for a in articles
    ])


# ---------------------------------------------------------------------------
# POST /api/kb/<id>/approve  – Admin approve
# ---------------------------------------------------------------------------

@bp.route('/kb/<int:article_id>/approve', methods=['POST'])
@login_required
def approve_kb_article(article_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    article = KBArticle.query.get_or_404(article_id)
    article.status = 'approved'
    db.session.commit()

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# POST /api/kb/<id>/deny  – Admin deny & delete associated files
# ---------------------------------------------------------------------------

@bp.route('/kb/<int:article_id>/deny', methods=['POST'])
@login_required
def deny_kb_article(article_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    article = KBArticle.query.get_or_404(article_id)

    # Delete any stored attachments from disk
    upload_folder = current_app.config['UPLOAD_FOLDER']
    for att in article.attachments:
        try:
            # Inline images
            if att.file_type and str(att.file_type).startswith('image'):
                img_path = os.path.join(upload_folder, 'kb_images', att.filename)
                if os.path.exists(img_path):
                    os.remove(img_path)
            # Generic files
            file_path = os.path.join(upload_folder, 'kb', att.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as exc:
            logger.warning(f"[KB] Failed to remove file for denied article: {exc}")

    db.session.delete(article)
    db.session.commit()

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# POST /api/kb  – Create a new KB article (pending)
# ---------------------------------------------------------------------------

@bp.route('/kb', methods=['POST'])
@login_required
def create_kb_article():
    data = request.form

    article = KBArticle(
        title=data['title'],
        content=data['content'],
        category=data['category'],
        tags=data.get('tags', ''),
        author_id=current_user.id,
        status='pending',
    )

    db.session.add(article)
    db.session.commit()

    # Handle (optional) file attachments
    sp_res = _get_spark_resources()
    allowed_file = sp_res['allowed_file']

    if 'attachments' in request.files:
        for f in request.files.getlist('attachments'):
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                kb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'kb')
                os.makedirs(kb_dir, exist_ok=True)
                file_path = os.path.join(kb_dir, filename)
                f.save(file_path)

                attachment = KBAttachment(
                    article_id=article.id,
                    filename=filename,
                    file_type=f.content_type,
                )
                db.session.add(attachment)

    db.session.commit()

    # Bust cache
    lock = sp_res['articles_cache_lock']
    cache_ref = sp_res['articles_cache']
    with lock:
        cache_ref.clear()

    socketio.emit('kb_update', {'type': 'new', 'article': {'id': article.id, 'title': article.title}})

    return jsonify({'id': article.id})


# ---------------------------------------------------------------------------
# PUT /api/kb/<id>  – Update article details & add attachments
# ---------------------------------------------------------------------------

@bp.route('/kb/<int:article_id>', methods=['PUT'])
@login_required
def update_kb_article(article_id):
    article = KBArticle.query.get_or_404(article_id)
    data = request.form

    article.title = data['title']
    article.content = data['content']
    article.category = data['category']
    article.tags = data.get('tags', '')
    article.updated_at = datetime.utcnow()

    # New attachments
    sp_res = _get_spark_resources()
    allowed_file = sp_res['allowed_file']

    if 'attachments' in request.files:
        for f in request.files.getlist('attachments'):
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                kb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'kb')
                os.makedirs(kb_dir, exist_ok=True)
                file_path = os.path.join(kb_dir, filename)
                f.save(file_path)

                attachment = KBAttachment(
                    article_id=article.id,
                    filename=filename,
                    file_type=f.content_type,
                )
                db.session.add(attachment)

    db.session.commit()

    # Cache clear
    lock = sp_res['articles_cache_lock']
    cache_ref = sp_res['articles_cache']
    with lock:
        cache_ref.clear()

    socketio.emit('kb_update', {'type': 'update', 'article': {'id': article.id, 'title': article.title}})

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# DELETE /api/kb/<id>  – Remove an article & its attachments
# ---------------------------------------------------------------------------

@bp.route('/kb/<int:article_id>', methods=['DELETE'])
@login_required
def delete_kb_article(article_id):
    article = KBArticle.query.get_or_404(article_id)

    upload_folder = current_app.config['UPLOAD_FOLDER']

    for att in article.attachments:
        try:
            file_path = os.path.join(upload_folder, 'kb', att.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.delete(att)
        except Exception as exc:
            logger.warning(f"[KB] Failed to delete attachment file: {exc}")

    db.session.delete(article)
    db.session.commit()

    # Cache clear
    sp_res = _get_spark_resources()
    with sp_res['articles_cache_lock']:
        sp_res['articles_cache'].clear()

    socketio.emit('kb_update', {'type': 'delete', 'article_id': article_id})

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# POST /api/kb/upload  – Upload a file & create pending article
# ---------------------------------------------------------------------------

@bp.route('/kb/upload', methods=['POST'])
@login_required
def upload_kb_attachment():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    sp_res = _get_spark_resources()
    allowed_file = sp_res['allowed_file']

    if not (file and allowed_file(file.filename)):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        filename = secure_filename(file.filename)

        # Ensure unique filename
        if KBArticle.query.filter_by(file_path=filename).first():
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"

        docs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        file_path = os.path.join(docs_dir, filename)
        file.save(file_path)

        # Progress feedback
        socketio.emit('kb_upload_progress', {'status': 'Processing file...', 'progress': 0.5})

        title = request.form.get('title', os.path.splitext(filename)[0])
        tags = request.form.get('tags', '')

        article = KBArticle(
            title=title,
            content='',  # populated later
            category='Document',
            tags=tags,
            author_id=current_user.id,
            status='pending',
            import_status='processing',
            file_path=filename,
            is_public=True,
        )

        db.session.add(article)
        if not safe_commit(db.session):
            raise Exception('Database error while saving article')

        # Emit progress
        socketio.emit('kb_upload_progress', {'status': 'Importing document...', 'progress': 0.75})

        # Delay to ensure disk write
        time.sleep(1)

        # Import document (delegated to shared importer utility)
        try:
            from app.utils.kb_import import import_docs_folder
            import_docs_folder()
            article.import_status = 'completed'
            db.session.commit()

            socketio.emit('kb_upload_progress', {'status': 'Done', 'done': True, 'progress': 1.0})
            socketio.emit('kb_update', {'type': 'new', 'article': {'id': article.id, 'title': article.title}})

            return jsonify({'success': True, 'article_id': article.id})
        except Exception as exc:
            logging.error(f"Error importing document: {exc}")
            article.import_status = 'failed'
            db.session.commit()
            raise Exception('Failed to process document')

    except Exception as exc:
        logging.error(f"Upload error: {exc}")
        # Cleanup on failure
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# GET /api/kb/attachments/<id>  – Download attachment
# ---------------------------------------------------------------------------

@bp.route('/kb/attachments/<int:attachment_id>', methods=['GET'])
@login_required
def get_kb_attachment(attachment_id):
    attachment = KBAttachment.query.get_or_404(attachment_id)
    return send_file(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'kb', attachment.filename),
        as_attachment=True,
    )


# ---------------------------------------------------------------------------
# POST /api/kb/<id>/feedback  – Record user feedback
# ---------------------------------------------------------------------------

@bp.route('/kb/<int:article_id>/feedback', methods=['POST'])
@login_required
def submit_kb_feedback(article_id):
    data = request.json or {}
    fb = KBFeedback(
        article_id=article_id,
        user_id=current_user.id,
        rating=data.get('rating'),
        comment=data.get('comment', ''),
    )
    db.session.add(fb)
    db.session.commit()

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# GET /api/kb/graph  – Return graph of article relationships
# ---------------------------------------------------------------------------

@bp.route('/kb/graph', methods=['GET'])
@login_required
def get_kb_graph():
    articles = KBArticle.query.all()
    nodes = []
    edges = []

    for a in articles:
        nodes.append({'id': a.id, 'label': a.title, 'group': a.category})
        if a.tags:
            for tag in [t.strip() for t in a.tags.split(',') if t.strip()]:
                related = KBArticle.query.filter(
                    KBArticle.id != a.id, KBArticle.tags.like(f'%{tag}%')
                ).all()
                for rel in related:
                    edges.append({'from': a.id, 'to': rel.id, 'label': tag})

    return jsonify({'nodes': nodes, 'edges': edges})


# ---------------------------------------------------------------------------
# POST /api/kb/upload-pdf  – Upload & auto-approve a PDF document
# ---------------------------------------------------------------------------

@bp.route('/kb/upload-pdf', methods=['POST'])
@login_required
def upload_pdf_article():
    """Handle PDF uploads and create *approved* KB articles immediately.

    This endpoint mirrors the legacy `/api/kb/upload-pdf` route that previously
    lived inside *app.spark* but is now part of the *kb_api* blueprint. It
    stores the uploaded PDF under *static/docs*, extracts its text contents
    using *extract_pdf_details* and inserts a fully-approved public KBArticle
    record in the database. Real-time progress updates are broadcast via
    Socket.IO so the front-end can display a status bar.
    """

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files allowed'}), 400

    try:
        filename = secure_filename(file.filename)

        # Save under static/docs ensuring uniqueness
        docs_dir = os.path.join(current_app.root_path, 'static', 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        pdf_path = os.path.join(docs_dir, filename)

        if os.path.exists(pdf_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"
            pdf_path = os.path.join(docs_dir, filename)

        file.save(pdf_path)

        # Feedback – processing
        socketio.emit('kb_upload_progress', {'status': 'Processing PDF...', 'progress': 0.5})

        # Extract PDF text & images (delegated helper)
        content, _meta = extract_pdf_details(pdf_path)

        title = request.form.get('title', os.path.splitext(filename)[0])
        tags = request.form.get('tags', 'pdf,imported')

        article = KBArticle(
            title=title,
            content=content,
            category='PDF',
            tags=tags,
            author_id=current_user.id,
            status='approved',  # Auto-approve
            import_status='completed',
            file_path=filename,  # store just filename
            is_public=True,
        )

        db.session.add(article)
        if not safe_commit(db.session):
            logger.error("[ERROR] Could not commit uploaded article %s from %s", title, pdf_path)
            try:
                os.remove(pdf_path)
            except Exception:
                pass
            return jsonify({'error': 'Database error. Please try again.'}), 500

        # Clear in-memory cache to reflect new article
        try:
            from app.utils.cache import _articles_cache_lock, _articles_cache  # shared cache
            with _articles_cache_lock:
                _articles_cache.clear()
        except Exception:
            pass

        socketio.emit('kb_update', {'type': 'new', 'article': {'id': article.id, 'title': article.title}})
        socketio.emit('kb_upload_progress', {'status': 'Done', 'done': True, 'progress': 1.0})

        return jsonify({'success': True, 'article_id': article.id})

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Error uploading PDF: %s", exc)
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:  # pragma: no cover
                pass
        return jsonify({'error': str(exc)}), 500 