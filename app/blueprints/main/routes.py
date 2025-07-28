from flask import render_template, request, jsonify, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from . import bp
from datetime import datetime

def detect_client_type():
    """Detect if the request is from YAM client or web browser."""
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # Check for YAM client indicators
    yam_indicators = [
        'yam',
        'electron',
        'python-requests',
        'aiohttp',
        'requests'
    ]
    
    # Check for browser indicators
    browser_indicators = [
        'mozilla',
        'chrome',
        'safari',
        'firefox',
        'edge',
        'opera'
    ]
    
    # Check if it's a YAM client request
    for indicator in yam_indicators:
        if indicator in user_agent:
            return 'yam_client'
    
    # Check if it's a browser request
    for indicator in browser_indicators:
        if indicator in user_agent:
            return 'web_browser'
    
    # Check for API requests (Accept header)
    accept_header = request.headers.get('Accept', '')
    if 'application/json' in accept_header:
        return 'yam_client'
    
    # Default to web browser for unknown clients
    return 'web_browser'

@bp.route('/')
def index():
    """Root route that handles both authenticated and unauthenticated users."""
    client_type = detect_client_type()
    
    # Add debugging information
    print(f"=== MAIN INDEX ROUTE ACCESSED ===")
    print(f"Client type: {client_type}")
    print(f"Request method: {request.method}")
    print(f"Request URL: {request.url}")
    print(f"Session data: {dict(session)}")
    
    # Prevent redirect loops by checking session state
    redirect_loop_protection = session.get('redirect_loop_protection', 0)
    print(f"Redirect loop protection counter: {redirect_loop_protection}")
    
    if redirect_loop_protection > 5:
        # Reset the counter and show an error page
        session['redirect_loop_protection'] = 0
        print(f"REDIRECT LOOP DETECTED - Showing error page")
        return render_template('error.html', 
                             error_message="Redirect loop detected. Please clear your browser cookies and try again.",
                             error_code="REDIRECT_LOOP"), 500
    
    try:
        from flask_login import current_user
        
        if current_app.debug:
            print(f"Current user authenticated: {current_user.is_authenticated}")
            if hasattr(current_user, 'username'):
                print(f"Current user username: {current_user.username}")
        
        if current_user.is_authenticated:
            # Reset redirect loop protection on successful authentication
            session['redirect_loop_protection'] = 0
            if current_app.debug:
                print(f"User authenticated - resetting redirect loop protection")
            
            # User is authenticated - show main page
            if client_type == 'yam_client':
                # YAM client - return JSON response
                user = current_user.username
                email = current_user.email
                name = user.split('.')[0].title() if '.' in user else user.title()
                
                if current_app.debug:
                    print(f"Returning JSON response for YAM client")
                return jsonify({
                    'status': 'authenticated',
                    'user': {
                        'username': user,
                        'email': email,
                        'name': name
                    },
                    'client_type': 'yam_client',
                    'page': 'main_index',
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                # Web browser - render HTML template
                user = current_user.username
                email = current_user.email
                name = user.split('.')[0].title() if '.' in user else user.title()
                if current_app.debug:
                    print(f"*******************************")
                    print(f"**** {user.title()} has logged in. ({email}) ****")
                    print(f"*******************************")
                    print(f"Rendering YAM.html template for web browser (main dashboard)")
                
                # Mark user as online using presence service
                try:
                    from app.services.user_presence import presence_service
                    session_data = {
                        'ip_address': request.environ.get('REMOTE_ADDR', 'unknown'),
                        'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
                        'login_time': datetime.utcnow().isoformat(),
                        'login_method': 'web_login'
                    }
                    presence_service.mark_user_online(current_user.id, session_data)
                    if current_app.debug:
                        print(f"Marked user {current_user.id} as online via main route")
                except Exception as e:
                    if current_app.debug:
                        print(f"Error marking user online: {e}")
                
                # Pass current_user for template imports/components
                return render_template('YAM.html', user=user, user_email=email, name=name,
                                      current_user=current_user,
                                      active_page='home')
        else:
            # User is not authenticated, redirect to login page
            # Increment redirect loop protection counter
            session['redirect_loop_protection'] = redirect_loop_protection + 1
            if current_app.debug:
                print(f"User not authenticated - redirecting to login (counter: {session['redirect_loop_protection']})")
            
            if client_type == 'yam_client':
                return jsonify({
                    'status': 'unauthenticated',
                    'redirect': url_for('auth.login'),
                    'client_type': 'yam_client',
                    'timestamp': datetime.now().isoformat()
                }), 401
            else:
                # For web browsers, always redirect to login page
                return redirect(url_for('auth.login'))
                
    except Exception as e:
        if current_app.debug:
            print(f"Error in root route: {e}")
            import traceback
            traceback.print_exc()
        
        # Increment redirect loop protection counter
        session['redirect_loop_protection'] = redirect_loop_protection + 1
        if current_app.debug:
            print(f"Exception occurred - redirecting to login (counter: {session['redirect_loop_protection']})")
        
        # Fallback to simple template instead of redirecting to login
        if client_type == 'yam_client':
            return jsonify({
                'status': 'error',
                'message': 'Server error, redirecting to login',
                'redirect': url_for('auth.login'),
                'client_type': 'yam_client',
                'timestamp': datetime.now().isoformat()
            }), 500
        else:
            # For web browsers, try to render simple template as fallback
            try:
                user = current_user.username if current_user.is_authenticated else 'Unknown'
                email = current_user.email if current_user.is_authenticated else 'unknown@example.com'
                name = user.split('.')[0].title() if '.' in user else user.title()
                return render_template('YAM.html', user=user, user_email=email, name=name,
                                       current_user=current_user, active_page='home')
            except Exception as fallback_error:
                print(f"Fallback template also failed: {fallback_error}")
                # Ultimate fallback - redirect to login
                return redirect(url_for('auth.login'))

@bp.route('/menu')
@login_required
def menu_page():
    """Render the outages menu page (moved from app/spark.py)."""
    return render_template('outages_menu.html')

@bp.route('/test')
def test_route():
    """Simple test route to verify server is working."""
    return jsonify({
        'status': 'ok',
        'message': 'Main blueprint is working',
        'timestamp': datetime.now().isoformat(),
        'session_data': dict(session),
        'hasattr_available': 'hasattr' in globals(),
        'user_authenticated': current_user.is_authenticated if current_user else False,
        'user_info': {
            'username': current_user.username if current_user and current_user.is_authenticated else None,
            'email': current_user.email if current_user and current_user.is_authenticated else None,
            'role': getattr(current_user, 'role', None) if current_user and current_user.is_authenticated else None
        }
    })

@bp.route('/test-template')
def test_template():
    """Test route to verify template rendering works."""
    try:
        # Test a simple template render with current timestamp
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result = render_template('test_simple.html', user='test_user', current_time=current_time)
        return result
    except Exception as e:
        return jsonify({
            'error': 'Template rendering failed',
            'message': str(e),
            'traceback': str(e.__traceback__)
        }), 500

@bp.route('/dashboard-simple')
@login_required
def dashboard_simple():
    """Dashboard route using Index2 components."""
    try:
        user = current_user.username
        email = current_user.email
        name = user.split('.')[0].title() if '.' in user else user.title()
        
        return render_template('dashboard.html', user=user, user_email=email, name=name,
                               active_page='home')
    except Exception as e:
        return jsonify({
            'error': 'Dashboard rendering failed',
            'message': str(e)
        }), 500

@bp.route('/test-dashboard')
@login_required
def test_dashboard():
    """Test route for the new dashboard template"""
    try:
        user = current_user.username
        email = current_user.email
        name = user.split('.')[0].title() if '.' in user else user.title()
        
        return render_template('dashboard.html', user=user, user_email=email, name=name,
                               current_user=current_user, active_page='home')
    except Exception as e:
        return jsonify({
            'error': 'Dashboard test failed',
            'message': str(e),
            'traceback': str(e.__traceback__)
        }), 500

@bp.route('/test-index2')
@login_required
def test_index2():
    """Test route for Index2 components debugging"""
    try:
        # Get current user info
        current_user = get_current_user()
        name = current_user.username if current_user and current_user.username else 'User'
        
        # Test data for debugging
        test_data = {
            'user': {
                'name': name,
                'role': current_user.role if current_user else 'User',
                'authenticated': current_user.is_authenticated if current_user else False
            },
            'components': {
                'outage_banner': True,
                'welcome_banner': True,
                'users_online': True,
                'debug_panel': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return render_template('test_index2.html', 
                             name=name, 
                             current_user=current_user,
                             test_data=test_data)
                             
    except Exception as e:
        app.logger.error(f"Error in test_index2 route: {str(e)}")
        return render_template('error.html', 
                             error="Failed to load Index2 test page",
                             details=str(e))

@bp.route('/yam-simple')
@login_required
def yam_simple():
    """Test route for simple YAM template"""
    try:
        user = current_user.username
        email = current_user.email
        name = user.split('.')[0].title() if '.' in user else user.title()
        
        return render_template('YAM_simple.html', 
                             user=user, 
                             user_email=email, 
                             name=name,
                             current_user=current_user)
                             
    except Exception as e:
        app.logger.error(f"Error in yam_simple route: {str(e)}")
        return jsonify({
            'error': 'YAM Simple template failed',
            'message': str(e)
        }), 500

# @bp.route('/notes')
# @login_required
# def notes():
#     """Render the sticky notes page (moved from spark.py)."""
#     return render_template('notes.html', active_page='notes') 