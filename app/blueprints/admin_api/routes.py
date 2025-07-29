from __future__ import annotations

import os
import random
import string
from datetime import datetime, timezone, timedelta
from typing import List

import psutil
from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    session,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Activity, Document, User, AllowedWindowsUser
from app.utils.windows_auth import add_windows_user_to_allowed_list, remove_windows_user_from_allowed_list
from app.utils.helpers import safe_commit
from . import bp

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: set[str] = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "pdf",
    "doc",
    "docx",
    "txt",
}


def _allowed_file(filename: str) -> bool:
    """Return *True* if *filename* has an allowed extension."""

    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------


@bp.route("/system-status")
@login_required
def system_status():
    """Return basic system metrics similar to the legacy implementation."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        net = psutil.net_io_counters()
        network = "OK" if net.bytes_sent > 0 or net.bytes_recv > 0 else "Disconnected"

        return jsonify(
            {
                "CPU Usage": f"{cpu}%",
                "Memory Usage": f"{memory}%",
                "Disk Usage": f"{disk}%",
                "Network": network,
            }
        )
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Users CRUD
# ---------------------------------------------------------------------------


@bp.route("/users", methods=["GET", "POST"])
@login_required
def admin_users():
    """List users or create a new one (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == "GET":
        q: str = request.args.get("q", "").strip().lower()
        query = User.query
        if q:
            like_expr = f"%{q}%"
            query = query.filter(
                (User.username.ilike(like_expr))
                | (User.email.ilike(like_expr))
                | (User.role.ilike(like_expr))
            )
        users: List[User] = query.all()
        return jsonify(
            [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role,
                    "profile_picture": u.profile_picture or "default.png",
                    "is_online": u.is_online,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "is_active": u.is_active,
                    "phone": getattr(u, "phone", ""),
                    "birthday": getattr(u, "birthday", ""),
                }
                for u in users
            ]
        )

    # --- POST (create) ------------------------------------------------------
    data = request.get_json() or {}

    # Validate required fields
    for field in ("username", "email", "password"):
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Check uniqueness
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 400
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    try:
        user = User(
            username=data["username"],
            email=data["email"],
            role=data.get("role", "user"),
            is_active=True,
            profile_picture="default.png",
            created_at=datetime.utcnow(),
        )
        user.set_password(data["password"])

        db.session.add(user)
        db.session.commit()

        activity = Activity(
            user_id=current_user.id,
            action="create_user",
            details=f"Created new user: {user.username}",
        )
        db.session.add(activity)
        db.session.commit()

        return (
            jsonify({"success": True, "message": "User created successfully", "user_id": user.id}),
            201,
        )
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error creating user: {str(exc)}"}), 500


@bp.route("/users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def admin_user(user_id: int):
    """Retrieve, update or delete a specific user (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    if request.method == "GET":
        return jsonify(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "profile_picture": user.profile_picture or "default.png",
                "is_online": user.is_online,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "is_active": user.is_active,
            }
        )


@bp.route("/users/<int:user_id>/stats", methods=["GET"])
@login_required
def admin_user_stats(user_id: int):
    """Get detailed statistics for a specific user (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)
    
    try:
        # Calculate user statistics
        from datetime import datetime, timedelta
        
        # Get ticket statistics
        tickets_created = 0
        tickets_resolved = 0
        if hasattr(user, 'tickets'):
            tickets_created = len(user.tickets)
            tickets_resolved = len([t for t in user.tickets if getattr(t, 'status', '') == 'resolved'])
        
        # Get login statistics
        login_count = 0
        last_login_days = 'N/A'
        if hasattr(user, 'activities'):
            login_activities = [a for a in user.activities if getattr(a, 'action', '') == 'login']
            login_count = len(login_activities)
            
            if user.last_login:
                days_since = (datetime.utcnow() - user.last_login).days
                last_login_days = f"{days_since} days"
        
        # Get recent activity count
        recent_activity_count = 0
        if hasattr(user, 'activities'):
            recent_activities = [a for a in user.activities 
                               if a.timestamp and (datetime.utcnow() - a.timestamp).days <= 7]
            recent_activity_count = len(recent_activities)
        
        return jsonify({
            "tickets_created": tickets_created,
            "tickets_resolved": tickets_resolved,
            "login_count": login_count,
            "last_login_days": last_login_days,
            "recent_activity_count": recent_activity_count,
            "account_age_days": (datetime.utcnow() - user.created_at).days if user.created_at else 0,
            "is_online": user.is_online,
            "last_seen": user.last_seen.isoformat() if user.last_seen else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user stats for user {user_id}: {e}")
        return jsonify({"error": "Failed to retrieve user statistics"}), 500

    if request.method == "PUT":
        data = request.get_json() or {}

        try:
            if username := data.get("username"):
                if username != user.username and User.query.filter(
                    User.username == username, User.id != user_id
                ).first():
                    return jsonify({"error": "Username already exists"}), 400
                user.username = username

            if email := data.get("email"):
                if email != user.email and User.query.filter(
                    User.email == email, User.id != user_id
                ).first():
                    return jsonify({"error": "Email already exists"}), 400
                user.email = email

            if "role" in data:
                user.role = data["role"]
            if "is_active" in data:
                user.is_active = data["is_active"]
            if password := data.get("password"):
                user.set_password(password)

            db.session.commit()

            activity = Activity(
                user_id=current_user.id,
                action="update_user",
                details=f"Updated user: {user.username}",
            )
            db.session.add(activity)
            db.session.commit()

            return jsonify({"success": True, "message": "User updated successfully"})
        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            return jsonify({"error": f"Error updating user: {str(exc)}"}), 500

    # --- DELETE ------------------------------------------------------------
    if user.id == current_user.id:
        return jsonify({"error": "Cannot delete your own account"}), 400

    try:
        activity = Activity(
            user_id=current_user.id,
            action="delete_user",
            details=f"Deleted user: {user.username}",
        )
        db.session.add(activity)
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error deleting user: {str(exc)}"}), 500


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
def admin_reset_password(user_id: int):
    """Generate a new random password for the specified user."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    try:
        new_password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
        user.set_password(new_password)
        db.session.commit()

        activity = Activity(
            user_id=current_user.id,
            action="reset_password",
            details=f"Reset password for user: {user.username}",
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({"success": True, "new_password": new_password})
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error resetting password: {str(exc)}"}), 500


# ---------------------------------------------------------------------------
# Documents CRUD
# ---------------------------------------------------------------------------


@bp.route("/documents", methods=["GET", "POST"])
@login_required
def admin_documents():
    """Handle listing and uploading of documents via multipart/form-data."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == "GET":
        docs = Document.query.all()
        return jsonify(
            [
                {
                    "id": d.id,
                    "title": d.title,
                    "content": d.content,
                    "file_path": d.file_path,
                    "file_type": d.file_type,
                    "created_at": d.created_at.isoformat(),
                    "updated_at": d.updated_at.isoformat(),
                    "user_id": d.user_id,
                    "is_public": d.is_public,
                    "tags": d.tags,
                }
                for d in docs
            ]
        )

    # --- POST (upload) ------------------------------------------------------
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file_storage = request.files["file"]
    if file_storage.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file_storage.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file_storage.filename)
    base_upload_folder: str = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
    filepath = os.path.join(base_upload_folder, "documents", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_storage.save(filepath)

    document = Document(
        title=request.form.get("title", filename),
        content=request.form.get("content", ""),
        file_path=filepath,
        file_type=file_storage.content_type,
        user_id=current_user.id,
        is_public=request.form.get("is_public", "false").lower() == "true",
        tags=request.form.get("tags", "").split(","),
    )

    db.session.add(document)
    db.session.commit()

    return (
        jsonify({"success": True, "message": "Document uploaded successfully", "document_id": document.id}),
        201,
    )


@bp.route("/documents/<int:document_id>", methods=["PUT", "DELETE"])
@login_required
def admin_document(document_id: int):
    """Update or delete a single document."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    document = Document.query.get_or_404(document_id)

    if request.method == "PUT":
        data = request.get_json() or {}

        if "title" in data:
            document.title = data["title"]
        if "content" in data:
            document.content = data["content"]
        if "is_public" in data:
            document.is_public = data["is_public"]
        if "tags" in data:
            document.tags = data["tags"]

        document.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "message": "Document updated successfully"})

    # --- DELETE ------------------------------------------------------------
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)

    db.session.delete(document)
    db.session.commit()

    return jsonify({"success": True, "message": "Document deleted successfully"})


# ---------------------------------------------------------------------------
# User Presence API Endpoints
# ---------------------------------------------------------------------------

@bp.route("/active_users")
@login_required
def get_active_users():
    """
    Get comprehensive list of all users with their online status and activity details.
    This is the main endpoint for real-time user presence tracking.
    """
    try:
        from app.services.user_presence import presence_service
        
        # Get detailed user data including session info for admins
        include_details = getattr(current_user, "is_admin", False)
        users_data = presence_service.get_online_users(include_details=include_details)
        
        # Add presence statistics
        stats = presence_service.get_presence_stats()
        
        return jsonify({
            "users": users_data,
            "stats": {
                "total_users": stats.get("total_users", 0),
                "online_users": stats.get("online_users", 0),
                "active_sessions": stats.get("active_sessions", 0)
            },
            "last_updated": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_active_users: {e}")
        return jsonify({"error": "Failed to retrieve user data"}), 500


@bp.route("/user_status/<int:user_id>")
@login_required
def get_user_status(user_id: int):
    """
    Get detailed status information for a specific user.
    Includes last seen time, online status, and session details.
    """
    try:
        from app.services.user_presence import presence_service
        
        # Only allow users to see their own status, or admins to see any status
        if not getattr(current_user, "is_admin", False) and current_user.id != user_id:
            return jsonify({"error": "Unauthorized"}), 403
        
        status = presence_service.get_user_status(user_id)
        
        if "error" in status:
            return jsonify(status), 404 if status["error"] == "User not found" else 500
            
        return jsonify(status)
        
    except Exception as e:
        current_app.logger.error(f"Error getting user status for {user_id}: {e}")
        return jsonify({"error": "Failed to retrieve user status"}), 500


@bp.route("/dashboard")
@login_required 
def enhanced_dashboard():
    """
    Optimized admin dashboard with comprehensive data in a single API call.
    Returns all dashboard data including users, outages, activity, and metrics.
    """
    try:
        # Debug session information
        current_app.logger.info(f"Dashboard request from user {current_user.id} ({current_user.username})")
        current_app.logger.info(f"Session user_id: {session.get('user_id')}")
        current_app.logger.info(f"Session last_activity: {session.get('last_activity')}")
        current_app.logger.info(f"User authenticated: {current_user.is_authenticated}")
        
        from app.services.user_presence import presence_service
        from app.models.base import Outage, Document, KBArticle, Activity
        from datetime import datetime, timedelta
        
        # Get presence data (this is the most important part)
        users_data = presence_service.get_online_users(include_details=True)
        presence_stats = presence_service.get_presence_stats()
        
        # Calculate online users count from presence data
        online_users_count = len([user for user in users_data if user.get('is_online', False)])
        
        # Get system statistics with error handling
        try:
            # Use more efficient queries
            active_outages = Outage.query.filter_by(status='active').count()
            total_outages = Outage.query.count()
            total_documents = Document.query.count()
            total_kb_articles = KBArticle.query.count()
        except Exception as db_err:
            current_app.logger.warning(f"Error getting database metrics: {db_err}")
            active_outages = total_outages = total_documents = total_kb_articles = 0
        
        # Get recent activity with error handling
        try:
            # Get recent activity (last 24 hours, limited to 10)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_activity = Activity.query.filter(
                Activity.timestamp >= yesterday
            ).order_by(Activity.timestamp.desc()).limit(10).all()
            
            activity_data = []
            for activity in recent_activity:
                try:
                    activity_data.append({
                        'id': activity.id,
                        'user': {
                            'id': activity.user.id if activity.user else None,
                            'name': activity.user.username if activity.user else 'Unknown',
                            'profile_picture': getattr(activity.user, 'profile_picture', 'default.png') if activity.user else 'default.png'
                        },
                        'action': activity.action,
                        'details': activity.details,
                        'timestamp': activity.timestamp.isoformat() if activity.timestamp else None
                    })
                except Exception as user_err:
                    current_app.logger.warning(f"Error processing activity user: {user_err}")
                    continue
                    
        except Exception as activity_err:
            current_app.logger.warning(f"Error getting recent activity: {activity_err}")
            activity_data = []
        
        # Get outages data
        try:
            outages_data = []
            active_outages_list = Outage.query.filter_by(status='active').order_by(Outage.created_at.desc()).limit(5).all()
            
            for outage in active_outages_list:
                outages_data.append({
                    'id': outage.id,
                    'title': outage.title,
                    'description': outage.description,
                    'status': outage.status,
                    'ticket_id': outage.ticket_id,
                    'created_at': outage.created_at.isoformat() if outage.created_at else None,
                    'updated_at': outage.updated_at.isoformat() if outage.updated_at else None
                })
        except Exception as outage_err:
            current_app.logger.warning(f"Error getting outages: {outage_err}")
            outages_data = []
        
        # Compile comprehensive response
        dashboard_data = {
            # Core metrics
            'open_tickets': 0,  # TODO: Connect to ticketing system
            'active_outages': active_outages,
            'online_users_count': online_users_count,
            
            # User data
            'online_users': users_data,
            
            # System statistics
            'stats': {
                'total_users': presence_stats.get("total_users", 0),
                'online_users': online_users_count,
                'active_sessions': presence_stats.get("active_sessions", 0),
                'total_outages': total_outages,
                'active_outages': active_outages,
                'total_documents': total_documents,
                'total_kb_articles': total_kb_articles
            },
            
            # Activity and outages
            'recent_activity': activity_data,
            'outages': outages_data,
            
            # Presence information
            'presence_stats': presence_stats,
            
            # Timestamp
            'last_updated': datetime.utcnow().isoformat(),
            
            # Performance metrics
            'load_time': datetime.utcnow().timestamp(),
            
            # Debug information
            'debug': {
                'user_id': current_user.id,
                'username': current_user.username,
                'session_user_id': session.get('user_id'),
                'session_last_activity': session.get('last_activity'),
                'authenticated': current_user.is_authenticated
            }
        }
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in enhanced_dashboard: {e}")
        # Return fallback data instead of error
        return jsonify({
            'open_tickets': 0,
            'active_outages': 0,
            'online_users_count': 1,
            'online_users': [],
            'stats': {
                'total_users': 1,
                'online_users': 1,
                'active_sessions': 1,
                'total_outages': 0,
                'active_outages': 0,
                'total_documents': 0,
                'total_kb_articles': 0
            },
            'recent_activity': [],
            'outages': [],
            'presence_stats': {
                'total_users': 1,
                'online_users': 1,
                'active_sessions': 1,
                'last_cleanup': datetime.utcnow().isoformat()
            },
            'last_updated': datetime.utcnow().isoformat(),
            'load_time': datetime.utcnow().timestamp(),
            'error': str(e),
            'debug': {
                'user_id': current_user.id if current_user.is_authenticated else None,
                'username': current_user.username if current_user.is_authenticated else None,
                'session_user_id': session.get('user_id'),
                'session_last_activity': session.get('last_activity'),
                'authenticated': current_user.is_authenticated
            }
        })

@bp.route("/debug/session")
@login_required
def debug_session():
    """Debug endpoint to check session status"""
    try:
        from datetime import datetime
        
        session_info = {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'last_activity': session.get('last_activity'),
            'session_start': session.get('session_start'),
            'request_count': session.get('request_count', 0),
            'authenticated': current_user.is_authenticated,
            'current_user_id': current_user.id if current_user.is_authenticated else None,
            'current_username': current_user.username if current_user.is_authenticated else None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Try to parse last_activity
        if session.get('last_activity'):
            try:
                last_activity = datetime.fromisoformat(session.get('last_activity').replace('Z', '+00:00'))
                time_diff = datetime.utcnow() - last_activity
                session_info['last_activity_parsed'] = last_activity.isoformat()
                session_info['time_since_last_activity_seconds'] = time_diff.total_seconds()
                session_info['time_since_last_activity_minutes'] = time_diff.total_seconds() / 60
            except Exception as e:
                session_info['last_activity_parse_error'] = str(e)
        
        return jsonify(session_info)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route("/presence_stats")
@login_required
def get_presence_stats():
    """
    Get detailed presence statistics for monitoring and debugging.
    Admin-only endpoint for system monitoring.
    """
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403
        
    try:
        from app.services.user_presence import presence_service
        
        stats = presence_service.get_presence_stats()
        
        return jsonify({
            "presence_stats": stats,
            "service_config": {
                "heartbeat_interval": presence_service.HEARTBEAT_INTERVAL,
                "activity_timeout": presence_service.ACTIVITY_TIMEOUT,
                "stale_cleanup_interval": presence_service.STALE_CLEANUP_INTERVAL,
                "disconnect_grace_period": presence_service.DISCONNECT_GRACE_PERIOD
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting presence stats: {e}")
        return jsonify({"error": "Failed to retrieve presence statistics"}), 500


@bp.route("/force_user_offline/<int:user_id>", methods=["POST"])
@login_required
def force_user_offline(user_id: int):
    """
    Force a user offline immediately (admin action).
    Useful for administrative purposes or troubleshooting.
    """
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403
        
    try:
        from app.services.user_presence import presence_service
        
        # Don't allow forcing yourself offline
        if user_id == current_user.id:
            return jsonify({"error": "Cannot force yourself offline"}), 400
        
        success = presence_service.force_user_offline(user_id)
        
        if success:
            # Log the admin action
            activity = Activity(
                user_id=current_user.id,
                action="force_user_offline",
                details=f"Forced user {user_id} offline"
            )
            db.session.add(activity)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"User {user_id} forced offline",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"error": "Failed to force user offline"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error forcing user {user_id} offline: {e}")
        return jsonify({"error": "Failed to force user offline"}), 500


@bp.route("/cleanup_stale_users", methods=["POST"])
@login_required
def cleanup_stale_users():
    """
    Manually trigger cleanup of stale user sessions.
    Admin-only endpoint for maintenance purposes.
    """
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403
        
    try:
        from app.services.user_presence import presence_service
        
        cleaned_count = presence_service.cleanup_stale_users()
        
        # Log the admin action
        activity = Activity(
            user_id=current_user.id,
            action="cleanup_stale_users",
            details=f"Cleaned up {cleaned_count} stale user sessions"
        )
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"Cleaned up {cleaned_count} stale users",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in cleanup_stale_users: {e}")
        return jsonify({"error": "Failed to cleanup stale users"}), 500


# ---------------------------------------------------------------------------
# Windows Users CRUD
# ---------------------------------------------------------------------------

@bp.route("/windows-users", methods=["GET", "POST"])
@login_required
def admin_windows_users():
    """List Windows users or create a new one (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == "GET":
        q: str = request.args.get("q", "").strip().lower()
        query = AllowedWindowsUser.query
        if q:
            like_expr = f"%{q}%"
            query = query.filter(
                (AllowedWindowsUser.windows_username.ilike(like_expr))
                | (AllowedWindowsUser.display_name.ilike(like_expr))
                | (AllowedWindowsUser.email.ilike(like_expr))
                | (AllowedWindowsUser.department.ilike(like_expr))
            )
        windows_users: List[AllowedWindowsUser] = query.all()
        return jsonify([windows_user.to_dict() for windows_user in windows_users])

    # --- POST (create) ------------------------------------------------------
    data = request.get_json() or {}

    # Validate required fields
    if not data.get("windows_username"):
        return jsonify({"error": "Missing required field: windows_username"}), 400

    # Check uniqueness
    if AllowedWindowsUser.query.filter_by(windows_username=data["windows_username"].lower()).first():
        return jsonify({"error": "Windows username already exists"}), 400

    try:
        windows_user = AllowedWindowsUser(
            windows_username=data["windows_username"].lower(),
            display_name=data.get("display_name", data["windows_username"]),
            email=data.get("email"),
            department=data.get("department"),
            role=data.get("role", "user"),
            notes=data.get("notes"),
            is_active=data.get("is_active", True)
        )

        db.session.add(windows_user)
        db.session.commit()

        activity = Activity(
            user_id=current_user.id,
            action="create_windows_user",
            details=f"Created new Windows user: {windows_user.windows_username}",
        )
        db.session.add(activity)
        db.session.commit()

        return (
            jsonify({"success": True, "message": "Windows user created successfully", "windows_user_id": windows_user.id}),
            201,
        )
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error creating Windows user: {str(exc)}"}), 500


@bp.route("/windows-users/<int:windows_user_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def admin_windows_user(windows_user_id: int):
    """Retrieve, update or delete a specific Windows user (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    windows_user = AllowedWindowsUser.query.get_or_404(windows_user_id)

    if request.method == "GET":
        return jsonify(windows_user.to_dict())

    if request.method == "PUT":
        data = request.get_json() or {}

        try:
            if windows_username := data.get("windows_username"):
                if windows_username.lower() != windows_user.windows_username and AllowedWindowsUser.query.filter(
                    AllowedWindowsUser.windows_username == windows_username.lower(), 
                    AllowedWindowsUser.id != windows_user_id
                ).first():
                    return jsonify({"error": "Windows username already exists"}), 400
                windows_user.windows_username = windows_username.lower()

            if display_name := data.get("display_name"):
                windows_user.display_name = display_name
            if email := data.get("email"):
                windows_user.email = email
            if department := data.get("department"):
                windows_user.department = department
            if "role" in data:
                windows_user.role = data["role"]
            if "is_active" in data:
                windows_user.is_active = data["is_active"]
            if notes := data.get("notes"):
                windows_user.notes = notes

            db.session.commit()

            activity = Activity(
                user_id=current_user.id,
                action="update_windows_user",
                details=f"Updated Windows user: {windows_user.windows_username}",
            )
            db.session.add(activity)
            db.session.commit()

            return jsonify({"success": True, "message": "Windows user updated successfully"})
        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            return jsonify({"error": f"Error updating Windows user: {str(exc)}"}), 500

    # --- DELETE ------------------------------------------------------------
    try:
        username = windows_user.windows_username
        db.session.delete(windows_user)
        db.session.commit()

        activity = Activity(
            user_id=current_user.id,
            action="delete_windows_user",
            details=f"Deleted Windows user: {username}",
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({"success": True, "message": "Windows user deleted successfully"})
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error deleting Windows user: {str(exc)}"}), 500


@bp.route("/windows-users/<int:windows_user_id>/link-user", methods=["POST"])
@login_required
def link_windows_user_to_account(windows_user_id: int):
    """Link a Windows user to an existing user account (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    windows_user = AllowedWindowsUser.query.get_or_404(windows_user_id)
    data = request.get_json() or {}

    if not data.get("user_id"):
        return jsonify({"error": "Missing required field: user_id"}), 400

    try:
        user = User.query.get_or_404(data["user_id"])
        
        # Update the Windows user record
        windows_user.user_id = user.id
        windows_user.updated_at = datetime.utcnow()
        
        # Update the user record with Windows username
        user.windows_username = windows_user.windows_username
        
        db.session.commit()

        activity = Activity(
            user_id=current_user.id,
            action="link_windows_user",
            details=f"Linked Windows user {windows_user.windows_username} to account {user.username}",
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({"success": True, "message": "Windows user linked successfully"})
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error linking Windows user: {str(exc)}"}), 500


@bp.route("/windows-users/<int:windows_user_id>/unlink-user", methods=["POST"])
@login_required
def unlink_windows_user_from_account(windows_user_id: int):
    """Unlink a Windows user from its user account (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    windows_user = AllowedWindowsUser.query.get_or_404(windows_user_id)

    try:
        # Remove Windows username from user account if it matches
        if windows_user.user_id:
            user = User.query.get(windows_user.user_id)
            if user and user.windows_username == windows_user.windows_username:
                user.windows_username = None
        
        # Clear the link
        windows_user.user_id = None
        windows_user.updated_at = datetime.utcnow()
        
        db.session.commit()

        activity = Activity(
            user_id=current_user.id,
            action="unlink_windows_user",
            details=f"Unlinked Windows user {windows_user.windows_username} from account",
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({"success": True, "message": "Windows user unlinked successfully"})
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error unlinking Windows user: {str(exc)}"}), 500


@bp.route("/windows-users/<int:windows_user_id>/toggle-status", methods=["POST"])
@login_required
def toggle_windows_user_status(windows_user_id: int):
    """Toggle the active status of a Windows user (admin-only)."""

    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Unauthorized"}), 403

    windows_user = AllowedWindowsUser.query.get_or_404(windows_user_id)
    data = request.get_json() or {}

    try:
        # Toggle the status
        new_status = data.get("is_active", not windows_user.is_active)
        windows_user.is_active = new_status
        windows_user.updated_at = datetime.utcnow()
        
        db.session.commit()

        action = "authorized" if new_status else "unauthorized"
        activity = Activity(
            user_id=current_user.id,
            action="toggle_windows_user_status",
            details=f"{action.capitalize()} Windows user: {windows_user.windows_username}",
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": f"Windows user {action} successfully",
            "is_active": new_status
        })
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        return jsonify({"error": f"Error toggling Windows user status: {str(exc)}"}), 500 

@bp.route("/users/online")
@login_required 
def get_online_users():
    """Get list of online users for admin dashboard."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get users who have been active in the last 5 minutes
        from datetime import datetime, timedelta
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        
        online_users = User.query.filter(
            User.last_seen >= five_minutes_ago,
            User.is_active == True
        ).order_by(User.last_seen.desc()).all()
        
        users_data = []
        for user in online_users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_online': True,
                'last_seen': user.last_seen.isoformat() if user.last_seen else None,
                'profile_picture': user.profile_picture or 'boy.png'
            })
        
        return jsonify(users_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting online users: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route("/users/cleanup", methods=['POST'])
@login_required 
def cleanup_users():
    """Trigger manual cleanup of user statuses."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        from datetime import datetime, timedelta
        
        # Mark users as offline if they haven't been seen in 10 minutes
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        
        offline_users = User.query.filter(
            User.last_seen < ten_minutes_ago,
            User.is_online == True
        ).all()
        
        for user in offline_users:
            user.is_online = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Marked {len(offline_users)} users as offline',
            'offline_count': len(offline_users)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during user cleanup: {e}")
        return jsonify({'error': str(e)}), 500 