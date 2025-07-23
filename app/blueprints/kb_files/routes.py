"""Custom file-serving routes for Knowledge-Base related PDFs.

These routes replicate the behaviour originally implemented in *app/spark.py*
while keeping the URL structure identical (/static/...).  They supersede the
default Flask static handler for the specific sub-paths we need.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import current_app, jsonify, send_from_directory
from flask_login import login_required

from . import bp

# ---------------------------------------------------------------------------
# /static/uploads/pending-articles/<path:filename>
# ---------------------------------------------------------------------------

@bp.route('/uploads/pending-articles/<path:filename>')
@login_required
def serve_pending_pdf(filename: str):
    """Serve PDFs that are still pending KB import."""
    upload_root = Path(current_app.config['UPLOAD_FOLDER']) / 'pending-articles'
    try:
        return send_from_directory(upload_root, filename)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Error serving pending PDF {filename}: {exc}")
        return jsonify({'error': 'File not found'}), 404


# ---------------------------------------------------------------------------
# /static/docs/<path:filename>
# ---------------------------------------------------------------------------

@bp.route('/docs/<path:filename>')
@login_required
def serve_doc_pdf(filename: str):
    """Serve knowledge-base PDFs from the docs folder, with fallbacks.

    This mirrors the original *serve_doc_pdf* logic including safety checks and
    recursive search when the file is nested in sub-directories.
    """
    # Guard against path traversal
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        current_app.logger.error(f"[PDF SERVE] Invalid filename: {filename}")
        return jsonify({'error': 'Invalid filename'}), 404

    # Get the correct path to the docs directory
    # The server runs from YAM/ but the docs are in app/static/docs
    current_dir = Path(__file__).parent.parent.parent.parent
    docs_root = current_dir / 'app' / 'static' / 'docs'
    found_path: Path | None = None

    direct_path = docs_root / filename
    if direct_path.exists():
        found_path = direct_path
    else:
        # Recursive search for the file
        if docs_root.exists():
            for root, _dirs, files in os.walk(docs_root):
                if filename in files:
                    found_path = Path(root) / filename
                    break

    if not found_path or not found_path.exists():
        current_app.logger.error(f"[PDF SERVE] File not found (recursive): {filename}")
        return jsonify({'error': 'File not found', 'path': str(docs_root / filename)}), 404

    rel_dir = os.path.relpath(found_path.parent, docs_root)
    current_app.logger.info(f"[PDF SERVE] Serving file: {found_path} from {rel_dir}")

    try:
        return send_from_directory(docs_root / rel_dir, filename)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"[PDF SERVE] Error serving file: {exc}")
        return jsonify({'error': 'Error serving file'}), 500 