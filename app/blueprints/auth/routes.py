import os
import sys
import getpass
from pathlib import Path

from flask import render_template, redirect, url_for, flash, request, current_app, jsonify, session, abort
from flask_login import login_user, current_user, login_required, logout_user
from datetime import datetime
from app.models import User, Activity
from app.utils.helpers import safe_commit
from app.utils.user_activity import update_user_status, emit_online_users
from app.utils.windows_auth import authenticate_windows_user, get_windows_auth_status
from . import bp
from app.extensions import db
from app.shared_state import _app_initialized

def hydrate_user_session(user):
    """Hydrate session with user data and ensure it stays active."""
    try:
        # Make session permanent BEFORE setting data
        session.permanent = True
        
        # Set session data
        session['user_id'] = user.id
        session['username'] = user.username
        session['last_activity'] = datetime.utcnow().isoformat()
        session['session_start'] = datetime.utcnow().isoformat()
        session['request_count'] = session.get('request_count', 0) + 1
        
        # Store user preferences if available
        try:
            if hasattr(user, 'settings') and user.settings is not None:
                if hasattr(user.settings, 'to_dict'):
                    session['user_settings'] = user.settings.to_dict()
                else:
                    session['user_settings'] = {}
            else:
                session['user_settings'] = {}
        except Exception as e:
            current_app.logger.warning(f"Error storing user settings: {e}")
            session['user_settings'] = {}
        
        # Force session to be saved
        session.modified = True
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error hydrating session: {e}")
        return False

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Add debugging information (reduced verbosity)
    if current_app.debug:
        print(f"Login route accessed - Method: {request.method}")
        print(f"Current user authenticated: {current_user.is_authenticated}")
        print(f"Session data: {dict(session)}")
    
    if current_user.is_authenticated:
        # Check if user is marked as offline in the database
        # This prevents redirect loops when server restarts
        if hasattr(current_user, 'is_online') and not current_user.is_online:
            username = current_user.username if hasattr(current_user, 'username') else 'Unknown'
            if current_app.debug:
                print(f"User {username} is authenticated but marked offline - clearing session")
            # Clear the session and force re-authentication
            try:
                from flask_login import logout_user
                session.clear()
                logout_user()
                if current_app.debug:
                    print(f"Session cleared for offline user {username}")
                flash('Your session has expired. Please log in again.', 'info')
                return render_template('login.html', year=datetime.utcnow().year)
            except Exception as e:
                current_app.logger.error(f"Error clearing session for offline user: {e}")
                # Fallback: clear session and redirect
                session.clear()
                return redirect(url_for('auth.login'))
        
        if current_app.debug:
            print(f"User already authenticated, redirecting to main.index")
        session.pop('redirect_loop_protection', None)
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Get form data
        login_id = (request.form.get('email') or '').strip()
        password = request.form.get('password')
        
        if current_app.debug:
            print(f"Login attempt - login_id: {login_id}, password: {'***' if password else 'None'}")

        # Validate input
        if not login_id:
            flash('Please enter your email or username', 'warning')
            return render_template('login.html', year=datetime.utcnow().year)

        if not password:
            flash('Please enter your password', 'warning')
            return render_template('login.html', year=datetime.utcnow().year)

        try:
            # Convert to lowercase for case-insensitive comparison
            login_id_lower = login_id.lower()
            
            # Try to find user by email first (case-insensitive)
            user = User.query.filter(db.func.lower(User.email) == login_id_lower).first()
            
            # If not found by email, try username (case-insensitive)
            if not user:
                user = User.query.filter(db.func.lower(User.username) == login_id_lower).first()

            if current_app.debug:
                print(f"User found: {user.username if user else 'None'}")

            # Check if user exists and password is correct
            if user and user.check_password(password):
                if current_app.debug:
                    print(f"Password check passed for user: {user.username}")
                
                # Check if user is active
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                    return render_template('login.html', year=datetime.utcnow().year)
                
                # Check if this is first-time login and requires password change
                if user.is_first_time_login():
                    if current_app.debug:
                        print(f"First-time login detected for user: {user.username}")
                    
                    # Store user info in session for password change
                    session['temp_user_id'] = user.id
                    session['temp_username'] = user.username
                    session['temp_email'] = user.email
                    session['first_time_login'] = True
                    
                    # Redirect to password change page
                    return render_template('login.html', 
                                         year=datetime.utcnow().year,
                                         first_time_login=True,
                                         username=user.username)
                
                if current_app.debug:
                    print(f"Logging in user: {user.username}")
                
                # IMPORTANT: Set session as permanent BEFORE login_user
                session.permanent = True
                
                # Login the user with Flask-Login
                login_user(user, remember=True)
                
                # Verify login was successful
                if current_app.debug:
                    print(f"After login_user - authenticated: {current_user.is_authenticated}")
                    print(f"After login_user - user_id: {current_user.get_id() if current_user.is_authenticated else 'None'}")
                
                # Hydrate session with user data
                success = hydrate_user_session(user)
                if current_app.debug:
                    print(f"Session hydration result: {success}")
                
                # Clear any redirect loop protection
                session.pop('redirect_loop_protection', None)

                # Immediately mark online
                try:
                    update_user_status(user.id, online=True)
                    emit_online_users()
                except Exception as e:
                    current_app.logger.error(f"Error marking user online: {e}")

                user.last_login = datetime.utcnow()
                safe_commit(db.session)

                # Log activity
                try:
                    act = Activity(
                        user_id=user.id,
                        action='login',
                        details=f'Logged in from {request.remote_addr}'
                    )
                    db.session.add(act)
                    safe_commit(db.session)
                except Exception as e:
                    current_app.logger.error(f"Error logging login activity: {e}")
                    db.session.rollback()

                # Get the next page from the request args, defaulting to main.index (which renders dashboard.html)
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('main.index')  # This will render dashboard.html for authenticated users
                
                print(f"Final session data before redirect: {dict(session)}")
                print(f"Redirecting to: {next_page}")
                print(f"Current user authenticated: {current_user.is_authenticated}")
                print(f"Current user ID: {current_user.get_id() if current_user.is_authenticated else 'None'}")
                
                # Force session to be saved
                session.modified = True
                
                # Add a small delay to ensure session is saved
                import time
                time.sleep(0.1)
                
                # Force session to be saved again
                session.modified = True
                
                print(f"About to redirect to: {next_page}")
                print(f"Session data at redirect: {dict(session)}")
                
                return redirect(next_page)
            else:
                print(f"Login failed - user: {user.username if user else 'None'}, password_check: {user.check_password(password) if user else 'N/A'}")
                flash('Invalid email/username or password', 'danger')
                return render_template('login.html', year=datetime.utcnow().year)

        except Exception as e:
            print(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'danger')
            return render_template('login.html', year=datetime.utcnow().year)

    # GET request - show login form
    print(f"Showing login form")
    try:
        return render_template('login.html', year=datetime.utcnow().year)
    except Exception as template_error:
        print(f"Template error: {template_error}")
        # Fallback to simple HTML if template fails
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Login</title></head>
        <body>
            <h1>Login</h1>
            <form method="POST" action="{url_for('auth.login')}">
                <input type="text" name="email" placeholder="Email or Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        """

@bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Handle first-time password change for new users."""
    # Check if user is in first-time login session
    if not session.get('first_time_login') or not session.get('temp_user_id'):
        flash('Invalid password change request', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not new_password or not confirm_password:
            flash('Please fill in all password fields', 'warning')
            return render_template('login.html', 
                                 year=datetime.utcnow().year,
                                 first_time_login=True,
                                 username=session.get('temp_username'))
        
        if new_password != confirm_password:
            flash('Passwords do not match', 'warning')
            return render_template('login.html', 
                                 year=datetime.utcnow().year,
                                 first_time_login=True,
                                 username=session.get('temp_username'))
        
        # Get user info for validation
        username = session.get('temp_username', '')
        first_name = username.split()[0] if username else ''
        last_name = ' '.join(username.split()[1:]) if len(username.split()) > 1 else ''
        
        # Validate password strength
        from app.utils.password_validation import validate_password
        is_valid, errors = validate_password(new_password, username, first_name, last_name)
        
        if not is_valid:
            error_message = '<br>'.join(errors)
            flash(f'Password does not meet requirements:<br>{error_message}', 'warning')
            return render_template('login.html', 
                                 year=datetime.utcnow().year,
                                 first_time_login=True,
                                 username=session.get('temp_username'))
        
        try:
            # Get user and update password
            user = User.query.get(session.get('temp_user_id'))
            if not user:
                flash('User not found', 'danger')
                return redirect(url_for('auth.login'))
            
            # Update password and mark as changed
            user.set_password(new_password)
            user.mark_password_changed()
            
            # Clear temporary session data
            session.pop('temp_user_id', None)
            session.pop('temp_username', None)
            session.pop('temp_email', None)
            session.pop('first_time_login', None)
            
            # Log the user in properly
            session.permanent = True
            login_user(user, remember=True)
            
            # Hydrate session
            hydrate_user_session(user)
            
            # Mark user as online
            try:
                update_user_status(user.id, online=True)
                emit_online_users()
            except Exception as e:
                current_app.logger.error(f"Error marking user online: {e}")
            
            # Update last login
            user.last_login = datetime.utcnow()
            safe_commit(db.session)
            
            # Log activity
            try:
                act = Activity(
                    user_id=user.id,
                    action='password_change',
                    details='First-time password change completed'
                )
                db.session.add(act)
                safe_commit(db.session)
            except Exception as e:
                current_app.logger.error(f"Error logging password change activity: {e}")
                db.session.rollback()
            
            flash('Password changed successfully! Welcome to YAM.', 'success')
            return redirect(url_for('main.index'))
            
        except Exception as e:
            current_app.logger.error(f"Error changing password: {e}")
            flash('An error occurred while changing your password. Please try again.', 'danger')
            return render_template('login.html', 
                                 year=datetime.utcnow().year,
                                 first_time_login=True,
                                 username=session.get('temp_username'))
    
    # GET request - show password change form
    return render_template('login.html', 
                         year=datetime.utcnow().year,
                         first_time_login=True,
                         username=session.get('temp_username'))

@bp.route('/logout')
@login_required
def logout():
    """Complete logout that clears all sessions and user presence."""
    try:
        user_id = current_user.id
        username = current_user.username
        
        # Phase 1: Mark user offline in presence service (real-time)
        try:
            from app.services.user_presence import UserPresenceService
            presence_service = UserPresenceService()
            presence_service._mark_offline_immediately(user_id)
            
            # Broadcast update to all clients
            from flask_socketio import emit
            from app.extensions import socketio
            users_list = presence_service.get_online_users(include_details=True)
            socketio.emit('online_users_update', users_list)
            current_app.logger.info(f"User {username} marked offline and broadcast sent")
        except Exception as e:
            current_app.logger.error(f"Error marking user offline on logout: {e}")
        
        # Phase 2: Log activity
        try:
            act = Activity(
                user_id=user_id,
                action='logout',
                details=f'Logged out from {request.remote_addr}'
            )
            db.session.add(act)
            safe_commit(db.session)
            current_app.logger.info(f"Logout activity logged for user {username}")
        except Exception as e:
            current_app.logger.error(f"Error logging logout activity: {e}")
            db.session.rollback()
        
        # Phase 3: Clear all session data completely
        try:
            # Clear Flask session
            session.clear()
            
            # Clear persistent session files
            from pathlib import Path
            session_dir = Path(current_app.config.get('SESSION_FILE_DIR', 'sessions'))
            if session_dir.exists():
                session_file = session_dir / f"user_{user_id}.json"
                if session_file.exists():
                    session_file.unlink()
                    current_app.logger.info(f"Cleared session file for user {username}")
        except Exception as e:
            current_app.logger.error(f"Error clearing session files: {e}")
        
        # Phase 4: Clear enhanced session manager data
        try:
            from app.utils.enhanced_session_manager import EnhancedSessionManager
            enhanced_manager = EnhancedSessionManager()
            enhanced_manager.force_logout()
            current_app.logger.info(f"Enhanced session manager cleared for user {username}")
        except Exception as e:
            current_app.logger.warning(f"Error clearing enhanced session data: {e}")
        
        # Phase 5: Clear user presence from memory
        try:
            from app.utils.auth_middleware import clear_user_sessions
            clear_user_sessions(user_id)
            current_app.logger.info(f"User presence cleared from memory for {username}")
        except Exception as e:
            current_app.logger.warning(f"Error clearing user presence: {e}")
        
        # Phase 6: Force logout user
        logout_user()
        
        # Phase 7: Create response with cache control headers
        response = redirect(url_for('auth.login'))
        
        # Clear all cookies
        response.delete_cookie('session')
        response.delete_cookie('yam_session')
        response.delete_cookie('csrf_token')
        response.delete_cookie('remember_token')
        
        # Set cache control headers to prevent caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        flash('You have been logged out successfully.', 'info')
        current_app.logger.info(f"Complete logout successful for user {username}")
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error during logout: {e}")
        flash('An error occurred during logout.', 'danger')
        return redirect(url_for('auth.login'))
