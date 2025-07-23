import time
import logging
from flask import jsonify, request
from flask_login import login_required, current_user
from . import bp

logger = logging.getLogger(__name__)

@bp.route('/stats')
@login_required
def cache_stats():
    """Get comprehensive cache statistics"""
    try:
        from app.utils.enhanced_cache import enhanced_cache
        from app.utils.cache_warming import get_warming_stats
        
        # Get enhanced cache stats
        cache_stats = enhanced_cache.get_stats()
        
        # Get cache warming stats
        warming_stats = get_warming_stats()
        
        # Combine all statistics
        stats = {
            'cache_performance': cache_stats,
            'cache_warming': warming_stats,
            'timestamp': time.time()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve cache statistics'
        }), 500

@bp.route('/clear', methods=['POST'])
@login_required
def clear_cache():
    """Clear cache data (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        from app.utils.enhanced_cache import enhanced_cache
        
        data = request.get_json() or {}
        cache_type = data.get('type', 'all')  # 'all', 'memory', 'disk', or specific tags
        
        if cache_type == 'all':
            enhanced_cache.clear_all()
            message = 'All cache data cleared'
        elif cache_type == 'memory':
            with enhanced_cache.memory_lock:
                enhanced_cache.memory_cache.clear()
            message = 'Memory cache cleared'
        elif cache_type.startswith('tag:'):
            tag = cache_type[4:]  # Remove 'tag:' prefix
            count = enhanced_cache.invalidate_by_tag(tag)
            message = f'Cleared {count} items with tag "{tag}"'
        else:
            return jsonify({'error': 'Invalid cache type'}), 400
        
        logger.info(f"Cache cleared by admin user {current_user.username}: {cache_type}")
        
        return jsonify({
            'success': True,
            'message': message,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to clear cache'
        }), 500

@bp.route('/warm', methods=['POST'])
@login_required
def warm_cache_manually():
    """Manually trigger cache warming (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        from app.utils.cache_warming import cache_warmer
        
        data = request.get_json() or {}
        strategies = data.get('strategies')  # None for all, or list of strategy names
        
        # Start cache warming
        cache_warmer.warm_cache_async(strategies)
        
        logger.info(f"Manual cache warming triggered by admin user {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Cache warming started',
            'strategies': strategies or 'all',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Failed to trigger cache warming: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to start cache warming'
        }), 500 