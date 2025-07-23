from flask import render_template
from flask_login import login_required
from app.blueprints.tracking import bp
from extensions import db

@bp.route('/', methods=['GET', 'POST'])
@login_required
def tracking():
    return render_template('tracking.html', active_page='tracking') 