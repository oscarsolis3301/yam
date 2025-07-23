from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required, current_user
from extensions import db
from app.models import KBArticle
from app.utils.ai_utils import generate_summary, get_similar_articles
from . import bp
import logging
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger('spark')

@bp.route('/')
@login_required
def kb():
    """Render the knowledge base page"""
    return render_template('kb/index.html')

@bp.route('/<int:article_id>')
@login_required
def view_article(article_id):
    """View a specific knowledge base article"""
    try:
        article = KBArticle.query.get_or_404(article_id)
        return render_template('kb/article.html', article=article)
    except Exception as e:
        logger.error(f"Error viewing article {article_id}: {str(e)}")
        return render_template('404.html'), 404

@bp.route('/api/articles', methods=['GET'])
@login_required
def get_articles():
    """Get all knowledge base articles"""
    try:
        articles = KBArticle.query.all()
        return jsonify([{
            'id': article.id,
            'title': article.title,
            'content': article.content,
            'created_at': article.created_at.isoformat(),
            'updated_at': article.updated_at.isoformat()
        } for article in articles])
    except Exception as e:
        logger.error(f"Error getting articles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/articles', methods=['POST'])
@login_required
def create_article():
    """Create a new knowledge base article"""
    try:
        data = request.get_json()
        article = KBArticle(
            title=data['title'],
            content=data['content']
        )
        db.session.add(article)
        db.session.commit()
        return jsonify({
            'id': article.id,
            'title': article.title,
            'content': article.content,
            'created_at': article.created_at.isoformat(),
            'updated_at': article.updated_at.isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Error creating article: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/articles/<int:article_id>', methods=['PUT'])
@login_required
def update_article(article_id):
    """Update a knowledge base article"""
    try:
        article = KBArticle.query.get_or_404(article_id)
        data = request.get_json()
        
        if 'title' in data:
            article.title = data['title']
        if 'content' in data:
            article.content = data['content']
            
        db.session.commit()
        return jsonify({
            'id': article.id,
            'title': article.title,
            'content': article.content,
            'created_at': article.created_at.isoformat(),
            'updated_at': article.updated_at.isoformat()
        })
    except Exception as e:
        logger.error(f"Error updating article: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/articles/<int:article_id>', methods=['DELETE'])
@login_required
def delete_article(article_id):
    """Delete a knowledge base article"""
    try:
        article = KBArticle.query.get_or_404(article_id)
        db.session.delete(article)
        db.session.commit()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting article: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/articles/<int:article_id>/summary', methods=['POST'])
@login_required
def generate_article_summary(article_id):
    """Generate a summary for an article"""
    try:
        article = KBArticle.query.get_or_404(article_id)
        summary = generate_summary(article.content)
        return jsonify({'summary': summary})
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/articles/similar', methods=['POST'])
@login_required
def find_similar_articles():
    """Find similar articles based on query"""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
            
        articles = get_similar_articles(query)
        return jsonify({'articles': articles})
    except Exception as e:
        logger.error(f"Error finding similar articles: {str(e)}")
        return jsonify({'error': str(e)}), 500 