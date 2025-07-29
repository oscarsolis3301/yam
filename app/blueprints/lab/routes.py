from flask import render_template
from flask_login import login_required

from . import bp  # Import the shared blueprint instance
from app.extensions import db


@bp.route('/', methods=['GET'])
@login_required
def lab_page():
    """Render the Lab page (formerly defined directly in app/spark.py)."""
    return render_template('lab.html', active_page='lab')
