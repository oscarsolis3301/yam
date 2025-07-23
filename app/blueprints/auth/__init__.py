from flask import Blueprint

bp = Blueprint('auth', __name__)

from . import routes

def init_auth_blueprint(app):
    app.register_blueprint(bp) 