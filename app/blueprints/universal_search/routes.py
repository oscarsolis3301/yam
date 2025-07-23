"""
Universal Search API Routes

This module provides the API endpoints for the universal search functionality,
allowing users to search across all content types in the application using
the optimized database-based search engine.
"""

from flask import request, jsonify, current_app, render_template
from flask_login import login_required, current_user
from typing import List, Dict, Any
import logging

# Import the optimized search engine
from app.utils.optimized_search_engine import optimized_search_engine
from app.models import SearchHistory
from extensions import db

logger = logging.getLogger(__name__)

# Import the blueprint from __init__.py
from . import bp

@bp.route('/', methods=['GET'])
@login_required
def search():
    """
    Universal search endpoint that searches across all content types using
    the optimized database-based search engine.
    
    Query parameters:
    - q: Search query string
    - limit: Maximum number of results (default: 20)
    - content_types: Comma-separated list of content types to search in
    - section: Specific section to search in
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))
        content_types_str = request.args.get('content_types', '')
        section = request.args.get('section', '')
        
        if not query:
            return jsonify({
                'results': [],
                'total': 0,
                'query': query,
                'suggestions': []
            })
        
        # Parse content types filter
        content_types = None
        if content_types_str:
            content_types = [ct.strip() for ct in content_types_str.split(',') if ct.strip()]
        
        # Use the optimized search engine
        results = optimized_search_engine.search(query, limit, content_types)
        suggestions = optimized_search_engine.get_suggestions(query, 5)
        
        # Log search for analytics
        try:
            search_history = SearchHistory(
                user_id=current_user.id,
                query=query,
                search_type='universal'
            )
            db.session.add(search_history)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log search history: {e}")
            try:
                db.session.rollback()
            except:
                pass
        
        # Group results by content type
        grouped_results = {}
        for result in results:
            content_type = result['content_type']
            if content_type not in grouped_results:
                grouped_results[content_type] = []
            grouped_results[content_type].append(result)
        
        return jsonify({
            'results': results,
            'grouped_results': grouped_results,
            'total': len(results),
            'query': query,
            'suggestions': suggestions,
            'content_types': content_types,
            'section': section
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({
            'error': 'Search failed',
            'message': str(e)
        }), 500

@bp.route('/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """Get search suggestions based on partial query."""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({'suggestions': []})
        
        # Use the optimized search engine for suggestions
        suggestions = optimized_search_engine.get_suggestions(query, limit)
        
        return jsonify({
            'suggestions': suggestions,
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return jsonify({
            'error': 'Failed to get suggestions',
            'message': str(e)
        }), 500

@bp.route('/quick-search', methods=['GET'])
@login_required
def quick_search():
    """Quick search for real-time results."""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 5))
        
        if not query:
            return jsonify({'results': []})
        
        # Use the optimized search engine for quick search
        results = optimized_search_engine.search(query, limit)
        
        return jsonify({
            'results': results,
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Quick search error: {e}")
        return jsonify({
            'error': 'Quick search failed',
            'message': str(e)
        }), 500

@bp.route('/rebuild-index', methods=['POST'])
@login_required
def rebuild_index():
    """Rebuild the entire search index (admin only)."""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Use the optimized search engine to rebuild index
        optimized_search_engine.rebuild_index()
        
        return jsonify({
            'message': 'Search index rebuild completed',
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Index rebuild error: {e}")
        return jsonify({
            'error': 'Index rebuild failed',
            'message': str(e)
        }), 500

@bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get search system statistics (admin only)."""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get stats from the optimized search engine
        from app.utils.init_search import get_search_stats
        stats = get_search_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            'error': 'Failed to get stats',
            'message': str(e)
        }), 500

@bp.route('/content-types', methods=['GET'])
@login_required
def get_content_types():
    """Get available content types for filtering."""
    content_types = [
        {
            'id': 'kb_article',
            'name': 'Knowledge Base Articles',
            'description': 'Search in knowledge base articles and documentation',
            'icon': 'bi-journal-text'
        },
        {
            'id': 'outage',
            'name': 'Outages',
            'description': 'Search in system outages and announcements',
            'icon': 'bi-exclamation-triangle'
        },
        {
            'id': 'user',
            'name': 'Users',
            'description': 'Search in user profiles and information',
            'icon': 'bi-person'
        },
        {
            'id': 'office',
            'name': 'Offices',
            'description': 'Search in office locations and information',
            'icon': 'bi-building'
        },
        {
            'id': 'workstation',
            'name': 'Workstations',
            'description': 'Search in workstation and device information',
            'icon': 'bi-laptop'
        },
        {
            'id': 'document',
            'name': 'Documents',
            'description': 'Search in uploaded documents and files',
            'icon': 'bi-file-earmark-text'
        },
        {
            'id': 'note',
            'name': 'Notes',
            'description': 'Search in user notes and comments',
            'icon': 'bi-sticky'
        }
    ]
    
    return jsonify({'content_types': content_types})

@bp.route('/sections', methods=['GET'])
@login_required
def get_sections():
    """Get available sections for filtering."""
    sections = [
        {
            'id': 'Knowledge Base',
            'name': 'Knowledge Base',
            'description': 'Documentation and articles',
            'icon': 'bi-journal-text'
        },
        {
            'id': 'Outages',
            'name': 'System Status',
            'description': 'Outages and system announcements',
            'icon': 'bi-exclamation-triangle'
        },
        {
            'id': 'Users',
            'name': 'Users',
            'description': 'User profiles and information',
            'icon': 'bi-person'
        },
        {
            'id': 'Offices',
            'name': 'Offices',
            'description': 'Office locations and information',
            'icon': 'bi-building'
        },
        {
            'id': 'Workstations',
            'name': 'Workstations',
            'description': 'Device and workstation information',
            'icon': 'bi-laptop'
        },
        {
            'id': 'Documents',
            'name': 'Documents',
            'description': 'Uploaded files and documents',
            'icon': 'bi-file-earmark-text'
        },
        {
            'id': 'Notes',
            'name': 'Notes',
            'description': 'User notes and comments',
            'icon': 'bi-sticky'
        }
    ]
    
    return jsonify({'sections': sections}) 