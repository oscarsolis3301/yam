from flask import Blueprint

bp = Blueprint('offices', __name__)

def init_offices_blueprint(app):
    from . import routes
    app.register_blueprint(bp, url_prefix='/offices') 