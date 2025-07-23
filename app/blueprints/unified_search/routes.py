from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from flask import jsonify, request
from flask_login import login_required
from rapidfuzz import fuzz, process

from . import bp  # Blueprint defined in __init__.py

# ---------------------------------------------------------------------------
# External helpers / shared dependencies
# ---------------------------------------------------------------------------

# DataFrame with office information lives in the *offices* blueprint – import
# it directly so we can reuse the already-loaded CSV instead of reading it
# again.
from app.blueprints.offices.routes import df  # type: ignore  # pylint: disable=import-error

from app.config import Config
from app.utils.device import load_devices_cache

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper – lightweight SQLite connection (read-only) for user search
# ---------------------------------------------------------------------------

def _get_db_connection() -> sqlite3.Connection:  # pragma: no cover
    """Return a SQLite connection to the main application DB."""
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# API Route – unified global search (offices, workstations, users)
# ---------------------------------------------------------------------------

@bp.route('/unified_search')
@login_required
def unified_search():  # noqa: C901  (complexity acceptable as is)
    """Perform global search across offices, devices and users.

    The logic is migrated from *app/spark.py* to this dedicated blueprint so it
    can evolve independently from the monolithic application file while
    preserving the original public URL (**/unified_search**).
    """
    query: str = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({'offices': [], 'workstations': [], 'users': []})

    results: Dict[str, List[Any]] = {
        'offices': [],
        'workstations': [],
        'users': []
    }

    # ---------------- Offices ----------------
    number_query: str | None = query if query.isdigit() else None

    if number_query:
        # Direct and prefix number matches
        number_matches = df[df['Number'].astype(str) == number_query]
        if number_matches.empty:
            number_matches = df[df['Number'].astype(str).str.startswith(number_query)]

        if not number_matches.empty:
            results['offices'] = number_matches[[
                'Internal Name', 'Location', 'Phone', 'Address',
                'Operations Manager', 'Mnemonic', 'IP', 'Number'
            ]].rename(columns={'Operations Manager': 'Manager'}).to_dict(orient='records')
    else:
        # Text and fuzzy search across pre-computed search strings
        text_matches = df[
            (df['search_string'].str.contains(query, case=False, na=False)) |
            (df['Mnemonic'].str.contains(query, case=False, na=False))
        ]

        if not text_matches.empty:
            results['offices'] = text_matches[[
                'Internal Name', 'Location', 'Phone', 'Address',
                'Operations Manager', 'Mnemonic', 'IP', 'Number'
            ]].rename(columns={'Operations Manager': 'Manager'}).to_dict(orient='records')
        else:
            # Fuzzy fallback – use *partial_ratio* for tolerant matching
            search_strings = df['search_string'].tolist()
            partial_results = process.extract(query, search_strings, scorer=fuzz.partial_ratio, limit=5)
            matched_indices = [i for _, score, i in partial_results if score > 70]
            if matched_indices:
                matches = df.iloc[matched_indices]
                results['offices'] = matches[[
                    'Internal Name', 'Location', 'Phone', 'Address',
                    'Operations Manager', 'Mnemonic', 'IP', 'Number'
                ]].rename(columns={'Operations Manager': 'Manager'}).to_dict(orient='records')

    # ---------------- Workstations ----------------
    try:
        devices = load_devices_cache()
        device_names = [d.get('Device name', '') for d in devices]
        matches = process.extract(query, device_names, scorer=fuzz.WRatio, limit=10)
        for name, score, idx in matches:
            if score > 40:
                device = devices[idx]
                results['workstations'].append({
                    'name': device.get('Device name', ''),
                    'managed_by': device.get('Managed by', ''),
                    'user': device.get('Primary user UPN', ''),
                    'os': device.get('OS', ''),
                    'os_version': device.get('OS version', ''),
                    'compliance': device.get('Compliance', '')
                })
        
        # Also search by user name if no device name matches found
        if not results['workstations']:
            user_matches = []
            for device in devices:
                user_name = device.get('Primary user UPN', '').lower()
                if query in user_name:
                    user_matches.append(device)
            
            # Add user matches to results
            for device in user_matches[:5]:
                results['workstations'].append({
                    'name': device.get('Device name', ''),
                    'managed_by': device.get('Managed by', ''),
                    'user': device.get('Primary user UPN', ''),
                    'os': device.get('OS', ''),
                    'os_version': device.get('OS version', ''),
                    'compliance': device.get('Compliance', '')
                })
                
    except Exception as exc:  # pragma: no cover
        # Do **not** fail the entire endpoint if workstation search errors out
        logger.debug("Error searching workstations: %s", exc)

    # ---------------- Users ----------------
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM users WHERE name LIKE ? OR name LIKE ? LIMIT 5",
            (f"%{query}%", f"%{query}%")
        )
        results['users'] = [{'name': row[0]} for row in cursor.fetchall()]
        conn.close()
    except Exception as exc:  # pragma: no cover
        logger.debug("Error searching users: %s", exc)

    return jsonify(results)


# ---------------------------------------------------------------------------
# API Route – user autocomplete (migrated from *app/spark.py*)
# ---------------------------------------------------------------------------

@bp.route('/autocomplete', methods=['GET'])
def autocomplete():  # pragma: no cover
    """Return simple username auto-complete suggestions.

    Behaviour identical to the original implementation that lived in
    *app/spark.py*. The endpoint path remains **/autocomplete** because the
    *unified_search* blueprint is registered WITHOUT a URL prefix.
    """
    query: str = request.args.get('query', '')
    if len(query) < 3:
        return jsonify([])

    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM users WHERE name LIKE ? LIMIT 10",
        (f"%{query}%",),
    )
    results = cursor.fetchall()
    conn.close()

    return jsonify([{'name': row['name']} for row in results])


# ---------------------------------------------------------------------------
# API Route – preload search data (workstations + offices)
# ---------------------------------------------------------------------------

@bp.route('/api/preload_search_data')
@login_required
def preload_search_data():  # pragma: no cover
    """Return pre-computed data used by the front-end global search widget."""
    try:
        # --- Workstations ---
        devices = load_devices_cache()
        workstations = [
            {
                'Name': device.get('Device name', ''),
                'OS': device.get('OS', ''),
                'Version': device.get('OS version', ''),
                'User': device.get('Primary user UPN', ''),
                'ManagedBy': device.get('Managed by', ''),
                'Compliance': device.get('Compliance', ''),
            }
            for device in devices
        ]

        # --- Offices --- (use the *df* DataFrame imported above)
        offices = (
            df[
                [
                    'Internal Name', 'Location', 'Phone', 'Address',
                    'Operations Manager', 'Mnemonic', 'IP', 'Number',
                ]
            ]
            .rename(columns={'Operations Manager': 'Manager'})
            .to_dict(orient='records')
        )

        return jsonify({'workstations': workstations, 'offices': offices})
    except Exception as exc:  # pragma: no cover
        logger.debug("Error preloading search data: %s", exc)
        return jsonify({'error': str(exc)}), 500 