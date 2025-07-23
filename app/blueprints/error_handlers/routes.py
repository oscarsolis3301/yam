import logging
from flask import render_template, current_app
from app import db
from . import bp

logger = logging.getLogger(__name__)

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403 