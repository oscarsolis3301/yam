"""app.models.time – compatibility shim
Re-export the main TimeEntry model defined in ``app.models.base`` so that
imports like ``from app.models.time import TimeEntry`` continue to work
without introducing a second table definition.
"""

from app.models.base import TimeEntry  # noqa: F401
from extensions import db
__all__ = ["TimeEntry"] 