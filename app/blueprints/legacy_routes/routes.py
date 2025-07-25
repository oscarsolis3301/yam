import logging
import requests
from flask import jsonify, request, redirect, url_for, render_template_string, render_template, current_app
from flask_login import login_required, current_user
from . import bp

logger = logging.getLogger(__name__)

# Legacy login route removed to prevent conflicts with auth blueprint
# The auth blueprint handles /auth/login correctly

@bp.route('/dashboard')
@login_required
def _legacy_dashboard_route():
    """Backward-compatibility alias for the admin dashboard (``/admin/dashboard``).

    Older front-end code may still reference the top-level
    ``/dashboard`` URL. If
    the current user is an admin we forward them to the admin dashboard inside
    the *admin* blueprint; otherwise we simply send them to the generic index
    page. This prevents unnecessary *404 Not Found* responses that were showing
    up in the logs.
    """
    if current_user.is_authenticated and getattr(current_user, 'role', 'user') == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('core.index'))

@bp.route('/logout')
@login_required
def _legacy_logout_route():
    """Backward-compatibility alias for the logout page (``/auth/logout``).

    Some templates and external bookmarks still point to the top-level
    ``/logout`` URL. We proxy the request to the canonical auth.logout view so
    the current session is terminated and the user is redirected to the login
    page without a 404.
    """
    from app.blueprints.auth.routes import logout as auth_logout
    return auth_logout()

@bp.route('/notes')
@login_required
def notes():
    """Render the notes page - redirect to collab_notes blueprint."""
    return redirect(url_for('collab_notes.notes_home'))

@bp.route('/kb')
@login_required
def kb():
    """Render the Knowledge Base page (unchanged behaviour)."""
    return render_template('kb.html', active_page='kb')

@bp.route('/search')
@login_required
def universal_search_page():
    """Render the universal search page."""
    query = request.args.get('q', '')
    return render_template('universal_search_page.html', query=query)

@bp.route('/universal-search')
@login_required
def universal_search_page_alias():
    """Alias to maintain backwards-compatibility with the new Universal Search
    full-results link ("View All"). It renders the existing
    *universal_search_page.html* template so we avoid a hard 404 when the
    JavaScript redirects to ``/universal-search``.
    """
    query = request.args.get('q', '')
    return render_template('universal_search_page.html', query=query)

@bp.route('/app/jarvis', methods=['POST'])
@login_required
def jarvis_app_proxy():
    from app.blueprints.jarvis.routes import chat as jarvis_chat_handler
    return jarvis_chat_handler()

@bp.route('/ai/spark', methods=['POST'])
@login_required
def spark_proxy():
    """Proxy requests to Cloudflare's AI service through our backend."""
    try:
        data = request.get_json()
        if not data or 'inputs' not in data or not isinstance(data['inputs'], list) or len(data['inputs']) == 0:
            return jsonify({'error': 'Invalid request format - expected {inputs: [{prompt: "..."}]}'}), 400

        # Extract prompt from the first input
        prompt = data['inputs'][0].get('prompt')
        if not prompt:
            return jsonify({'error': 'Missing prompt in request'}), 400

        # Forward request to Cloudflare
        response = requests.post(
            'https://spark.oscarsolis3301.workers.dev/jarvis',
            json={
                'inputs': [{
                    'prompt': prompt
                }]
            },
            timeout=30  # 30 second timeout
        )

        if not response.ok:
            logger.error(f"Cloudflare request failed: {response.status_code} - {response.text}")
            return jsonify({'error': 'Cloudflare service unavailable'}), 502

        # Parse Cloudflare response
        cloudflare_data = response.json()
        if not isinstance(cloudflare_data, list) or len(cloudflare_data) == 0:
            return jsonify({'error': 'Invalid response from Cloudflare'}), 502

        # Return the response in the same format as Cloudflare
        return jsonify(cloudflare_data)

    except requests.exceptions.RequestException as e:
        logger.error(f"Cloudflare request failed: {str(e)}")
        return jsonify({'error': 'Failed to reach Cloudflare service'}), 502
    except Exception as e:
        logger.error(f"Unexpected error in spark proxy: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 

@bp.route('/test-search-fixed')
@login_required
def test_search_fixed():
    """Test page for verifying search functionality."""
    return render_template('test_search_fixed.html') 