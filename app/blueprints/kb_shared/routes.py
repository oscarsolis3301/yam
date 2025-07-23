from datetime import datetime

from flask import render_template, jsonify
from flask_login import current_user  # not strictly necessary but kept for potential future use

from extensions import db
from app.models import SharedLink

from . import bp


@bp.route('/shared/<string:short_code>')
def view_shared_article(short_code: str):
    """Render a shared KB article via its short code.

    Mirrors the original /kb/shared/<short_code> route from app/spark.py
    while moving the implementation into a dedicated blueprint.
    """
    shared_link = SharedLink.query.filter_by(short_code=short_code).first_or_404()

    # Check expiry
    if shared_link.expires_at and shared_link.expires_at < datetime.utcnow():
        return render_template('error.html', message='This shared link has expired.'), 410

    # Increment view counter
    shared_link.views += 1
    db.session.commit()

    return render_template('shared_article.html', article=shared_link.article) 