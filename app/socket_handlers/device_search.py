"""Socket.IO handler for live device search suggestions.

This logic used to live inside *app/spark.py* but has been extracted into its
own module so it can be maintained and tested independently.
"""

from __future__ import annotations

import csv as _csv
from pathlib import Path
from typing import Any, List

from flask_socketio import emit
from rapidfuzz import fuzz, process

from app.extensions import socketio  # Reuse the global instance initialised in *extensions.py*
from app.utils.device import get_devices_csv_path

# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------

@socketio.on("search_device")
def handle_search_device(data: dict[str, Any]):
    """Emit a list of up-to-five fuzzy-matched device names.

    The client sends ``data = {"query": "..."}`` and we respond with the event
    ``device_suggestions`` containing an array of matching device names.
    """
    query: str = data.get("query", "").strip()
    if not query:
        return emit("device_suggestions", [])

    csv_path: str = get_devices_csv_path()

    try:
        with Path(csv_path).open(newline="", encoding="utf-8") as f:
            names: List[str] = [row["Device name"] for row in _csv.DictReader(f)]
    except FileNotFoundError:
        return emit("device_suggestions", [])

    matches = process.extract(query, names, scorer=fuzz.WRatio, limit=5)
    suggestions = [name for name, score, _ in matches if score > 30]
    emit("device_suggestions", suggestions) 