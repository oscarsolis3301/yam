"""
Windows Username Authentication Utility

This module provides functionality to:
1. Detect the current Windows username
2. Check if the username is allowed to access the application
3. Integrate with the existing Flask authentication system
4. Display Windows username on the splash screen
"""

import os
import getpass
import platform
import subprocess
from datetime import datetime
from typing import Dict, Optional, Tuple
from flask import current_app
from app.models import User, AllowedWindowsUser
from extensions import db


def get_windows_username() -> str:
    """
    Get the current Windows username using multiple methods for reliability.
    
    Returns:
        str: The current Windows username
    """
    try:
        # Method 1: Environment variables
        username = os.environ.get('USERNAME') or os.environ.get('USER')
        if username:
            return username.lower()
        
        # Method 2: getpass module
        username = getpass.getuser()
        if username:
            return username.lower()
        
        # Method 3: Windows API (if on Windows)
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(['whoami'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    username = result.stdout.strip()
                    # Remove domain prefix if present (e.g., "DOMAIN\\username" -> "username")
                    if '\\' in username:
                        username = username.split('\\')[-1]
                    return username.lower()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
        
        # Fallback: Unknown user
        return 'unknown'
        
    except Exception as e:
        current_app.logger.error(f"Error getting Windows username: {e}")
        return 'unknown'


def get_windows_domain_info() -> Dict[str, str]:
    """
    Get additional Windows domain information.
    
    Returns:
        Dict containing domain, computer name, and user profile path
    """
    info = {
        'domain': 'unknown',
        'computer_name': 'unknown',
        'user_profile': 'unknown'
    }
    
    try:
        if platform.system() == 'Windows':
            # Get computer name
            info['computer_name'] = os.environ.get('COMPUTERNAME', 'unknown')
            
            # Get user profile path
            info['user_profile'] = os.environ.get('USERPROFILE', 'unknown')
            
            # Try to get domain from whoami /upn
            try:
                result = subprocess.run(['whoami', '/upn'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and '@' in result.stdout:
                    domain = result.stdout.strip().split('@')[-1]
                    info['domain'] = domain
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
                
    except Exception as e:
        current_app.logger.error(f"Error getting Windows domain info: {e}")
    
    return info


def is_windows_username_allowed(username: str) -> Tuple[bool, Optional[AllowedWindowsUser]]:
    """
    Check if a Windows username is allowed to access the application.
    
    Args:
        username: The Windows username to check
        
    Returns:
        Tuple of (is_allowed, allowed_user_record)
    """
    try:
        # Check in AllowedWindowsUser table
        allowed_user = AllowedWindowsUser.query.filter(
            db.func.lower(AllowedWindowsUser.windows_username) == username.lower(),
            AllowedWindowsUser.is_active == True
        ).first()
        
        if allowed_user:
            return True, allowed_user
        
        # Also check if there's a User record with this Windows username
        user = User.query.filter(
            db.func.lower(User.windows_username) == username.lower(),
            User.is_active == True
        ).first()
        
        if user:
            return True, None
            
        return False, None
        
    except Exception as e:
        current_app.logger.error(f"Error checking if Windows username is allowed: {e}")
        return False, None


def get_or_create_user_from_windows_username(username: str, allowed_user: Optional[AllowedWindowsUser] = None) -> Optional[User]:
    """
    Get or create a User record based on Windows username and allowed users list.
    
    Args:
        username: The Windows username
        allowed_user: Optional AllowedWindowsUser record
        
    Returns:
        User record if found/created, None otherwise
    """
    try:
        # First, try to find existing user with this Windows username
        user = User.query.filter(
            db.func.lower(User.windows_username) == username.lower()
        ).first()
        
        if user:
            return user
        
        # If we have an allowed user record, try to link to existing user
        if allowed_user and allowed_user.user_id:
            user = User.query.get(allowed_user.user_id)
            if user:
                # Update the user's Windows username
                user.windows_username = username
                db.session.commit()
                return user
        
        # Create new user if we have allowed user info
        if allowed_user:
            user = User(
                username=allowed_user.display_name or username,
                email=allowed_user.email or f"{username}@pdshealth.com",
                windows_username=username,
                role=allowed_user.role or 'user',
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # Update the allowed user record to link to this user
            allowed_user.user_id = user.id
            db.session.commit()
            
            return user
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"Error getting/creating user from Windows username: {e}")
        db.session.rollback()
        return None


def authenticate_windows_user() -> Dict[str, any]:
    """
    Authenticate the current Windows user.
    
    Returns:
        Dict containing authentication status and user information
    """
    try:
        # Get current Windows username
        username = get_windows_username()
        domain_info = get_windows_domain_info()
        
        # Check if username is allowed
        is_allowed, allowed_user = is_windows_username_allowed(username)
        
        if not is_allowed:
            return {
                'authenticated': False,
                'username': username,
                'domain_info': domain_info,
                'message': 'Windows username not authorized',
                'error': 'unauthorized'
            }
        
        # Get or create user record
        user = get_or_create_user_from_windows_username(username, allowed_user)
        
        if not user:
            return {
                'authenticated': False,
                'username': username,
                'domain_info': domain_info,
                'message': 'Failed to create user record',
                'error': 'user_creation_failed'
            }
        
        # Update login attempt tracking for allowed users
        if allowed_user:
            allowed_user.update_login_attempt(success=True)
        
        return {
            'authenticated': True,
            'username': username,
            'domain_info': domain_info,
            'user': user,
            'message': 'Windows authentication successful'
        }
        
    except Exception as e:
        current_app.logger.error(f"Error in Windows authentication: {e}")
        return {
            'authenticated': False,
            'username': 'unknown',
            'domain_info': {},
            'message': f'Authentication error: {str(e)}',
            'error': 'authentication_error'
        }


def get_windows_auth_status() -> Dict[str, any]:
    """
    Get Windows authentication status for display on splash screen.
    
    Returns:
        Dict containing status information for the splash screen
    """
    try:
        username = get_windows_username()
        domain_info = get_windows_domain_info()
        is_allowed, allowed_user = is_windows_username_allowed(username)
        
        status = {
            'windows_username': username,
            'computer_name': domain_info.get('computer_name', 'unknown'),
            'domain': domain_info.get('domain', 'unknown'),
            'is_authorized': is_allowed,
            'display_name': username,
            'status': 'authorized' if is_allowed else 'unauthorized'
        }
        
        if allowed_user:
            status['display_name'] = allowed_user.display_name or username
            status['email'] = allowed_user.email
            status['department'] = allowed_user.department
            status['role'] = allowed_user.role
        
        return status
        
    except Exception as e:
        current_app.logger.error(f"Error getting Windows auth status: {e}")
        return {
            'windows_username': 'unknown',
            'computer_name': 'unknown',
            'domain': 'unknown',
            'is_authorized': False,
            'display_name': 'Unknown User',
            'status': 'error',
            'error': str(e)
        }


def add_windows_user_to_allowed_list(username: str, display_name: str = None, 
                                   email: str = None, department: str = None, 
                                   role: str = 'user', notes: str = None) -> bool:
    """
    Add a Windows username to the allowed users list.
    
    Args:
        username: Windows username to add
        display_name: Full name for display
        email: Email address
        department: Department/team
        role: Role in the system
        notes: Admin notes
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if already exists
        existing = AllowedWindowsUser.query.filter(
            db.func.lower(AllowedWindowsUser.windows_username) == username.lower()
        ).first()
        
        if existing:
            # Update existing record
            existing.display_name = display_name or existing.display_name
            existing.email = email or existing.email
            existing.department = department or existing.department
            existing.role = role or existing.role
            existing.notes = notes or existing.notes
            existing.updated_at = datetime.utcnow()
        else:
            # Create new record
            allowed_user = AllowedWindowsUser(
                windows_username=username.lower(),
                display_name=display_name or username,
                email=email,
                department=department,
                role=role,
                notes=notes
            )
            db.session.add(allowed_user)
        
        db.session.commit()
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error adding Windows user to allowed list: {e}")
        db.session.rollback()
        return False


def remove_windows_user_from_allowed_list(username: str) -> bool:
    """
    Remove a Windows username from the allowed users list.
    
    Args:
        username: Windows username to remove
        
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_user = AllowedWindowsUser.query.filter(
            db.func.lower(AllowedWindowsUser.windows_username) == username.lower()
        ).first()
        
        if allowed_user:
            allowed_user.is_active = False
            allowed_user.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        
        return False
        
    except Exception as e:
        current_app.logger.error(f"Error removing Windows user from allowed list: {e}")
        db.session.rollback()
        return False 