from __future__ import annotations

"""Socket.IO network-scanner & outage handlers.

This module encapsulates the IP-scanner logic (full subnet & AP-only
scans), related Socket.IO event handlers, and a lightweight
``before_request`` hook that logs each user interaction.  Import
``init_network_scan`` from *spark.py* (or any other Flask factory) and
call it **once** after the application instance has been created to
wire everything up.
"""

import subprocess
import threading
import socket as _socket
from typing import Dict

from flask import request, current_app
from flask_socketio import emit

from app.extensions import socketio  # shared Socket.IO instance
from app.utils.user_activity import log_user_activity

__all__ = [
    "init_network_scan",
]

# ---------------------------------------------------------------------------
# Internal state shared by concurrent scans
# ---------------------------------------------------------------------------

scans: Dict[str, Dict[str, bool | str]] = {}
scans_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def validate_subnet(subnet: str) -> bool:
    """Return *True* when *subnet* looks like ``XXX.YYY.ZZZ``.

    A *very* small helper that validates we received exactly three
    octets (the 4th is appended when generating individual IPs) and
    that each octet is in the valid IPv4 range 0-255.
    """
    parts = subnet.split(".")
    return len(parts) == 3 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def _run_scan(subnet: str, sid: str, only_aps: bool = False) -> None:
    """Background task that pings every host in *subnet*.

    When *only_aps* is *True* we skip everything except the hard-coded
    access-point addresses ``.17`` and ``.18`` to speed things up.
    """
    ips = [f"{subnet}.{i}" for i in ([17, 18] if only_aps else range(1, 256))]

    for ip in ips:
        # Gracefully abort when the client asked us to stop.
        with scans_lock:
            entry = scans.get(sid)
            if not entry or entry["stop"]:
                break

        socketio.emit("scanning", {"ip": ip}, room=sid)

        proc = subprocess.run(
            ["ping", "-n", "1", "-w", "500", ip], capture_output=True, text=True
        )
        online = "TTL=" in proc.stdout  # Windows-specific success marker

        try:
            hostname = _socket.gethostbyaddr(ip)[0]
        except Exception:  # pragma: no cover – reverse lookup failures are expected
            hostname = ""

        is_ap = only_aps and ("AP" in hostname.upper())

        socketio.emit(
            "scan_result",
            {"ip": ip, "hostname": hostname, "online": online, "isAP": is_ap},
            room=sid,
        )

        socketio.sleep(0.01)  # yield to other greenlets (eventlet)

    # Clean-up and final notification
    with scans_lock:
        entry = scans.pop(sid, None)

    if entry and not entry["stop"]:
        socketio.emit("scan_complete", room=sid)
    else:
        socketio.emit("scan_cancelled", room=sid)


# ---------------------------------------------------------------------------
# Socket.IO event handlers
# ---------------------------------------------------------------------------

@socketio.on("start_scan")
def _handle_full_scan(data):  # noqa: D401 (imperative mood)
    sid = request.sid  # unique Socket.IO session ID
    subnet = data.get("subnet", "")

    if not validate_subnet(subnet):
        return emit("scan_error", {"message": "Invalid subnet format. Use X.Y.Z"})

    with scans_lock:
        # Abort any existing scan initiated by this client.
        if sid in scans:
            scans[sid]["stop"] = True
        scans[sid] = {"stop": False, "type": "full"}

    socketio.start_background_task(_run_scan, subnet, sid, False)


@socketio.on("start_scan_aps")
def _handle_aps_scan(data):  # noqa: D401
    sid = request.sid
    subnet = data.get("subnet", "")

    if not validate_subnet(subnet):
        return emit("scan_error", {"message": "Invalid subnet format. Use X.Y.Z"})

    with scans_lock:
        existing = scans.get(sid)
        if existing and existing["type"] == "aps" and not existing["stop"]:
            return  # duplicate request while one is already running
        if existing:
            existing["stop"] = True
        scans[sid] = {"stop": False, "type": "aps"}

    socketio.start_background_task(_run_scan, subnet, sid, True)


@socketio.on("stop_scan")
def _handle_stop_scan():  # noqa: D401
    sid = request.sid
    with scans_lock:
        entry = scans.get(sid)
        if entry:
            entry["stop"] = True
    emit("scan_cancelled")


@socketio.on("outage_announcement")
def handle_outage_announcement(data):  # noqa: D401, N802 (keep original name)
    """Broadcast an outage announcement to **all** connected clients."""
    socketio.emit("new_outage_announcement", data)


@socketio.on("connect", namespace="/stream")
def on_stream_connect():
    current_app.logger.info("[STREAM] connected")


# ---------------------------------------------------------------------------
# Flask integration helper
# ---------------------------------------------------------------------------

def _before_request_hook():
    """Thin wrapper so we can register *log_user_activity* dynamically."""
    log_user_activity()


def init_network_scan(app):  # noqa: D401 (imperative mood)
    """Attach the *before_request* hook to *app*.

    Import this function and call it **once** after creating your Flask
    application to ensure the user-activity logger runs on every
    request.  The Socket.IO handlers are registered at *import* time so
    no extra steps are required for them.
    """
    app.before_request(_before_request_hook) 