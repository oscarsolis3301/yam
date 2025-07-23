"""Package aggregating Socket.IO event handlers.

Importing this package will register all event handlers with the global
``socketio`` instance exposed via :pymod:`extensions`.
"""

# Import sub-modules so that their decorators execute at import time
from . import device_search  # noqa: F401 
from . import admin_presence  # noqa: F401  (user presence & dashboard events)
from . import connection  # noqa: F401  (connect/disconnect handlers)
# from . import collab_notes  # noqa: F401  (collaborative notes handlers)