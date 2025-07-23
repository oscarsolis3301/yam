from flask import Blueprint

bp = Blueprint('tracking', __name__)

from . import routes

def init_tracking_blueprint(app):
    app.register_blueprint(bp, url_prefix='/tracking') 