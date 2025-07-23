from flask import Blueprint

# Shared Blueprint instance for the *devices* module.  Register this with the
# application in `app/spark.py` (or wherever the factory lives).
bp = Blueprint('devices', __name__)

# Import routes at module load-time so that the decorators see the **same**
# `bp` object.  Doing this here avoids circular-import issues where
# `app.blueprints.devices.routes` might be imported *before* the `bp` symbol
# is defined, which led to a `NameError`.

# The import must be at the end to ensure `bp` is already defined when the
# route decorators execute inside the *routes* module.
from . import routes  # noqa: E402  (import after blueprint definition is intentional) 