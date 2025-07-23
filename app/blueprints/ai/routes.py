from flask import Blueprint, jsonify, request, current_app, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from app.utils.ai_helpers import (
    store_qa,
    find_semantic_qa,
    get_cached_response,
    set_cached_response,
    generate_cache_key,
    answer_query
)
from app.utils.ai_utils import (
    get_similar_articles,
    generate_summary,
    process_document
)
import logging
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from app.blueprints.utils.ai import (
    extract_text,
    get_user_history,
    get_all_past_questions,
    update_feedback,
)
from app.utils.models import get_embedder
from app.models import User
import requests  # Added for external AI calls
from sqlalchemy import text  # Added for direct SQL text queries

logger = logging.getLogger('spark')
from . import bp  # Import the blueprint instead of redefining it

# Re-use the central embedder initialised at app start-up
embedder = get_embedder()

@bp.route('/ask', methods=['POST'])
@login_required
def ask():
    """Handle AI chat questions"""
    try:
        data = request.get_json()
        question = data.get('question')
        context = data.get('context', '')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
            
        # Check cache first
        cache_key = generate_cache_key(question, context)
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return jsonify({'answer': cached_response})
            
        # Check for similar questions
        similar_answer = find_semantic_qa(question)
        if similar_answer:
            # Cache the response
            set_cached_response(cache_key, similar_answer)
            return jsonify({'answer': similar_answer})
            
        # Generate new response
        # TODO: Implement actual AI response generation
        answer = "I'm sorry, I don't have an answer for that yet."
        
        # Store the Q&A pair
        store_qa(current_user.username, question, answer)
        
        # Cache the response
        set_cached_response(cache_key, answer)
        
        return jsonify({'answer': answer})
        
    except Exception as e:
        logger.error(f"Error in ask endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/summarize', methods=['POST'])
@login_required
def summarize():
    """Generate a summary of the provided text"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
            
        summary = generate_summary(text)
        return jsonify({'summary': summary})
        
    except Exception as e:
        logger.error(f"Error in summarize endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/process-document', methods=['POST'])
@login_required
def process_document_route():
    """Process an uploaded document"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Save the file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the document
            result = process_document(filepath)
            return jsonify(result)
        finally:
            # Clean up the temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
                
    except Exception as e:
        logger.error(f"Error in process-document endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/similar-articles', methods=['POST'])
@login_required
def similar_articles():
    """Find similar articles based on query"""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
            
        articles = get_similar_articles(query)
        return jsonify({'articles': articles})
        
    except Exception as e:
        logger.error(f"Error in similar-articles endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/jarvis', methods=['POST'])
@login_required
def jarvis():
    from flask import redirect, url_for
    # Permanent redirect (preserve POST) to the new Jarvis blueprint endpoint
    return redirect(url_for('jarvis.chat'), code=307)

@bp.route('/')
@login_required
def ai():
    return jsonify({
        'status': 'ok',
        'message': 'AI endpoints are available'
    })

@bp.route('/')
@login_required
def ai_status():
    """AI service status endpoint"""
    try:
        model = get_model()
        embedder = get_embedder()
        
        status = {
            'model_initialized': model is not None,
            'embedder_initialized': embedder is not None,
            'features': {
                'question_answering': model is not None,
                'semantic_search': embedder is not None,
                'image_analysis': False  # TODO: Implement image analysis
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error in AI status endpoint: {str(e)}")
        return jsonify({
            'error': 'Error checking AI service status',
            'status': 'error'
        }), 500

@bp.route('/suggest')
def suggest():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify(suggestions=[])
    try:
        past = get_all_past_questions()
    except Exception as err:
        logger.error(f"Failed to load past questions: {err}")
        past = []
    # Support both legacy tuple format (q, a) and new dict format
    questions = []
    for item in past:
        if isinstance(item, dict):
            questions.append(item.get('question', ''))
        elif isinstance(item, (list, tuple)) and len(item):
            questions.append(item[0])
    # Deduplicate & remove empty strings
    questions = [s for s in dict.fromkeys(questions) if s]
    if not questions or embedder is None:
        return jsonify(suggestions=[])

    try:
        emb = embedder.encode(questions)
        qv = embedder.encode([q])[0]
    except Exception as enc_err:
        logger.warning(f"Embedder failed: {enc_err}")
        return jsonify(suggestions=[])
    sims = [(questions[i], float((qv@emb[i]) / (((qv@qv)**0.5 * (emb[i]@emb[i])**0.5)+1e-8))) for i in range(len(questions))]
    sims.sort(key=lambda x: x[1], reverse=True)
    return jsonify(suggestions=[s for s,_ in sims[:5]])

@bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    try:
        # Persist temporarily so downstream helpers can read the file
        file.save(filepath)

        # --------------------------------------------------------------
        # Use the *centralised* document pipeline which already handles
        # text extraction, summarisation ("dumbed-down"), and FAQ generation.
        # --------------------------------------------------------------
        result = process_document(filepath)

        # For backwards-compatibility return only the summary when the
        # front-end does not expect the richer structure.
        if request.args.get('summary_only') == '1':
            return jsonify(summary=result.get('summary'))

        return jsonify(result)
    finally:
        # Always clean up the temporary upload to avoid filling the disk
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as cleanup_err:
            logger.warning(f"Failed to remove temp upload {filepath}: {cleanup_err}")

@bp.route('/history', methods=['GET'])
def history():
    return jsonify(history=get_user_history())

@bp.route('/feedback', methods=['POST'])
def feedback():
    data = request.get_json() or {}
    if not all(k in data for k in ('question', 'rating')):
        return jsonify(error="Missing data"), 400
    update_feedback(data['question'], data['rating'])
    return jsonify(status="success") 