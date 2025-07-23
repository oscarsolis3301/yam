from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/admin')

from . import routes

def init_admin_blueprint(app):
    app.register_blueprint(bp) 