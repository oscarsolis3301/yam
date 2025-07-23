"""app.utils.device – helpers for device CSV paths and simple JSON cache.

These functions were moved out of *spark.py* to keep the main application
file small and focused on routing while the reusable helpers live in the
``app.utils`` package.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Disk-space / device JSON cache helpers
# ---------------------------------------------------------------------------

def cache_storage(device_name: str, data: dict[str, Any]) -> None:
    """Persist *data* for *device_name* to *cache/storage_<device>.json*."""
    path = CACHE_DIR / f"storage_{device_name}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump({"cached_at": datetime.utcnow().isoformat(), "data": data}, f)


def load_cached_storage(device_name: str) -> dict[str, Any] | None:
    """Return cached storage info for *device_name* or *None* if unavailable."""
    path = CACHE_DIR / f"storage_{device_name}.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# ---------------------------------------------------------------------------
# CSV helper – robust path resolution
# ---------------------------------------------------------------------------

def _resolve_devices_dir() -> Path:
    """Return the absolute *Devices/* directory inside the *app* package.

    The folder lives at *<project>/app/Devices/*.  We resolve it dynamically
    from the current file location so it works no matter where the working
    directory is when the Flask app starts (e.g. `flask run`, gunicorn, unit
    tests, etc.).
    """

    # Current file: <project>/app/utils/device.py → parent = *utils*, parent
    # of that is *app*.
    app_dir = Path(__file__).resolve().parent.parent
    devices_dir = app_dir / "Devices"

    # Fallback to legacy location at repository root if moved.
    if not devices_dir.exists():
        repo_root = app_dir.parent  # one level above *app*
        devices_dir = repo_root / "Devices"

    return devices_dir


def get_devices_csv_path(filename: Optional[str] = None) -> str:
    """Return an **absolute** path to a devices CSV file.

    Parameters
    ----------
    filename
        Specific file name inside the *Devices/* directory.  When *None* we
        attempt to locate a sensible default in this order:

        1. **Today's** file – ``MMDDYYYYDevices.csv``.
        2. The **newest** ``*Devices.csv`` file present.
        3. Return today's path even if the file does not yet exist so callers
           can handle the *FileNotFoundError* themselves.
    """

    devices_dir: Path = _resolve_devices_dir()

    # Ensure directory exists (do *not* raise – caller handles missing file).
    devices_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        return str(devices_dir / filename)

    # 1️⃣  Today's file
    today_fmt = datetime.now().strftime("%m%d%Y")
    todays_file = devices_dir / f"{today_fmt}Devices.csv"
    if todays_file.exists():
        return str(todays_file)

    # 2️⃣  Newest CSV in the directory
    csv_files = sorted(devices_dir.glob("*Devices.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if csv_files:
        return str(csv_files[0])

    # 3️⃣  Fall back to today's *path* (may not exist)
    return str(todays_file)

# ---------------------------------------------------------------------------
# Delegated cache loader (compatibility shim)
# ---------------------------------------------------------------------------

# NOTE: The canonical implementation of *load_devices_cache* lives in
# ``app.utils.cache``.  To maintain backward-compatibility with older code that
# still performs ``from app.utils.device import load_devices_cache`` we expose
# a thin wrapper here that simply forwards the call.  This avoids import errors
# without duplicating logic in multiple places.

def load_devices_cache(force_reload: bool = False):
    """Return workstation/device records, delegating to the shared cache util."""
    # Import here to avoid circular dependency
    from app.utils.cache import load_devices_cache as _load_devices_cache
    return _load_devices_cache(force_reload) 