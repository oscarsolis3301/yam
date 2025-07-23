from flask import render_template, jsonify, request, current_app
from flask_login import login_required
import sqlite3

from . import bp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    """Create a short-lived SQLite connection using the application's DB_PATH."""
    db_path = current_app.config.get('DB_PATH')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

# ---------------------------------------------------------------------------
# Routes (moved from app/spark.py)
# ---------------------------------------------------------------------------

@bp.route('/agent')
@login_required
def agent_page():
    """Render the Agent page."""
    return render_template('agent.html')


@bp.route('/users', methods=['GET'])
# NOTE: This endpoint intentionally has no login requirement – it is used by
#       public JS fetches for quick user look-ups.
#       Keep the signature identical to the original implementation so that
#       existing front-end calls like */users?query=...* continue to work.
# ---------------------------------------------------------------------------
def search_users():
    """Light-weight user directory search returning name + clockId JSON."""
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE name LIKE ?",
        (f'%{query}%',)
    )
    results = cursor.fetchall()
    conn.close()

    return jsonify([
        {'name': row['name'], 'clockId': row['clock_id']} for row in results
    ]) 