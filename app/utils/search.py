"""app.utils.search – search-related database helpers

This module centralises the small helper functions that were previously
implemented directly inside ``app/spark.py`` so they can be reused by any
blueprint without having to import the *monolithic* Spark application
module (which would create circular-import issues).

The helpers continue to work exactly the same as before – they still use
``Config.DB_PATH`` from ``app.config`` for the underlying SQLite file –
but have been pulled out to improve modularity and testability.
"""

from __future__ import annotations

import sqlite3
from typing import List

from app.config import Config

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def init_search_table() -> None:
    """Ensure the *searches* table exists inside the **admin_dashboard.db**.

    This replicates the CREATE TABLE logic that was previously at module
    level in *spark.py*.
    """
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT UNIQUE
        )
        """
    )
    conn.commit()
    conn.close()


def save_search(query: str | None) -> None:
    """Insert *query* into the **searches** table (if not empty/duplicate)."""
    if not query:
        return

    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        # Ignore duplicates thanks to the UNIQUE constraint
        cursor.execute("INSERT OR IGNORE INTO searches (query) VALUES (?)", (query,))
        conn.commit()
        conn.close()
    except Exception as exc:  # pragma: no cover  (purely defensive)
        # Keep the original print-based error handling for now – the caller
        # already logs in their context.
        print(f"[ERROR] Failed to save search: {exc}")


def get_search_suggestions(query: str) -> List[str]:
    """Return a list of user *name* suggestions matching the supplied *query*."""
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()

    # Using LIKE for quick substring matches – this mirrors the original code.
    cursor.execute("SELECT name FROM users WHERE name LIKE ?", (f"%{query}%",))
    suggestions = [row[0] for row in cursor.fetchall()]

    conn.close()
    return suggestions 