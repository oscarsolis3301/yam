import logging
from flask import Blueprint

logger = logging.getLogger('spark')

bp = Blueprint('jarvis', __name__, url_prefix='/jarvis')

from . import routes  # noqa 