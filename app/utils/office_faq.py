"""Utility to generate and seed office-specific FAQ entries.

This helper loads *Offices/offices.csv* and *Offices/offices_info.csv* then
creates concise Q&A pairs (e.g. phone number, manager, address, IP) so Jarvis
can respond instantly without expensive model inference.

The generated questions follow simple, deterministic patterns so fuzzy token
matching remains reliable (e.g. "What is the phone number for Irvine?",
"Who is the manager for office 63?", etc.).  We insert each pair into the
`chat_qa` table **only if** an identical question is not already present to
avoid duplicates when the application restarts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
from sqlalchemy import text
from flask import current_app
from pandas.errors import EmptyDataError

from extensions import db
from app.utils.ai_helpers import store_qa, ensure_chat_qa_table

import logging
logger = logging.getLogger('spark')

# Attempt to import openpyxl so pandas can read Excel files. If unavailable,
# reading *.xlsx* will silently fall back to an **empty** DataFrame so the
# rest of the logic keeps working.
try:
    import openpyxl  # noqa: F401 – imported for its side-effects only
except ModuleNotFoundError:  # pragma: no-cover – optional dependency
    openpyxl = None  # type: ignore

__all__ = [
    "load_office_dataframe",
    "seed_office_faq",
]

_OFFICE_DF_CACHE: Optional[pd.DataFrame] = None


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _safe_read_csv(path: Path) -> pd.DataFrame:
    """Return *path* as a DataFrame or an **empty** frame on failure."""
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _safe_read_excel(path: Path) -> pd.DataFrame:
    """Return the Excel *path* as DataFrame or empty DataFrame on failure."""
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_excel(path, engine="openpyxl" if openpyxl else None)
    except (EmptyDataError, ImportError, ValueError, FileNotFoundError):
        # Any issue (missing openpyxl, corrupted file, etc.) – return empty
        return pd.DataFrame()


def load_office_dataframe() -> pd.DataFrame:
    """Load and merge *offices.csv* with *offices_info.csv* (if available).

    The merge key is the first column "#" (office number).  The resulting
    DataFrame keeps all original columns from *offices.csv* and appends
    *Mnemonic* and *IP* from *offices_info.csv* when present.
    """
    global _OFFICE_DF_CACHE
    if _OFFICE_DF_CACHE is not None:
        return _OFFICE_DF_CACHE

    offices_dir = Path("Offices")
    csv_main = offices_dir / "offices.csv"
    csv_info = offices_dir / "offices_info.csv"
    xlsx_dir = offices_dir / "offices_directory.xlsx"

    # Load individual sources ------------------------------------------------
    df_main = _safe_read_csv(csv_main)
    df_info = _safe_read_csv(csv_info)[["#", "Mnemonic", "IP"]] if csv_info.exists() else pd.DataFrame()
    df_xlsx = _safe_read_excel(xlsx_dir)

    # Normalise *xlsx* DataFrame – make sure it uses the same primary key (#)
    if not df_xlsx.empty:
        if "#" not in df_xlsx.columns:
            # Some spreadsheets use "Number" instead of "#"
            if "Number" in df_xlsx.columns:
                df_xlsx = df_xlsx.rename(columns={"Number": "#"})

    # Merge all sources on primary key --------------------------------------
    df = df_main
    if "#" in df.columns and not df_info.empty:
        df = pd.merge(df, df_info, on="#", how="left", suffixes=("", "_info"))
    if "#" in df.columns and not df_xlsx.empty:
        df = pd.merge(df, df_xlsx, on="#", how="left", suffixes=("", "_dir"))

    # Normalise string columns – replace NaNs with empty strings -----------
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna("").astype(str)

    _OFFICE_DF_CACHE = df
    return df


# ---------------------------------------------------------------------------
# FAQ seeding
# ---------------------------------------------------------------------------

def _qa_pairs_for_office(row: pd.Series) -> List[Tuple[str, str]]:
    """Return a list of (question, answer) tuples for the given *row*."""
    office_number = str(row.get("#", "")).strip()
    internal_name = str(row.get("Internal Name") or row.get("Name") or "").strip()
    if not internal_name:
        return []

    phone = row.get("Phone", "").strip()
    manager = row.get("Operations Manager", "").strip()
    address_parts = [
        row.get("Address", "").strip(),
        row.get("City", "").strip(),
        row.get("State", "").strip(),
        str(row.get("Zip", "")).strip(),
    ]
    address = ", ".join([p for p in address_parts if p])
    mnemonic = row.get("Mnemonic", "").strip()
    ip_addr = row.get("IP", "").strip()
    fax = row.get("Fax", "").strip()
    after_hours = row.get("After Hrs Phone", "").strip()
    if not after_hours:  # alternate column names found in some datasets
        after_hours = row.get("After Hours Phone", "").strip()
    region = row.get("Region Name", "").strip() or row.get("Region", "").strip()
    city = row.get("City", "").strip()
    state = row.get("State", "").strip()
    zip_code = str(row.get("Zip", "")).strip()

    qa: List[Tuple[str, str]] = []

    # ------------------------------------------------------------------
    # PHONE NUMBER – include several paraphrases for robust matching
    # ------------------------------------------------------------------
    if phone:
        phone_templates = [
            "What is the phone number for {x}?",
            "Phone number of {x}?",
            "What's the phone for {x}?",
            "How do I call {x}?",
            "Call {x} phone?",
            "Contact number for {x}?",
        ]

        for tpl in phone_templates:
            qa.append((tpl.format(x=internal_name), phone))

        if office_number:
            for tpl in phone_templates:
                qa.append((tpl.format(x=f"office {office_number}"), phone))

        if mnemonic:
            for tpl in phone_templates:
                qa.append((tpl.format(x=mnemonic), phone))

    # ------------------------------------------------------------------
    # MANAGER – broader phrasing
    # ------------------------------------------------------------------
    if manager:
        mgr_templates = [
            "Who is the manager for {x}?",
            "Who manages {x}?",
            "Who is the operations manager for {x}?",
            "Manager of {x}?",
            "Who is {x}'s manager?",
        ]
        for tpl in mgr_templates:
            qa.append((tpl.format(x=internal_name), manager))

        if office_number:
            for tpl in mgr_templates:
                qa.append((tpl.format(x=f"office {office_number}"), manager))

        if mnemonic:
            for tpl in mgr_templates:
                qa.append((tpl.format(x=mnemonic), manager))

    # ------------------------------------------------------------------
    # ADDRESS – include "where" style queries
    # ------------------------------------------------------------------
    if address:
        addr_templates = [
            "What is the address for {x}?",
            "Address of {x}?",
            "Where is {x} located?",
            "Location of {x}?",
        ]
        for tpl in addr_templates:
            qa.append((tpl.format(x=internal_name), address))

        if office_number or mnemonic:
            target_list = []
            if office_number:
                target_list.append(f"office {office_number}")
            if mnemonic:
                target_list.append(mnemonic)
            for t in target_list:
                for tpl in addr_templates:
                    qa.append((tpl.format(x=t), address))

    # Mnemonic -----------------------------------------------------------
    if mnemonic:
        qa.append((f"What is the mnemonic for {internal_name}?", mnemonic))
        qa.append((f"What is the mnemonic for office {office_number}?", mnemonic))

    # Fax ---------------------------------------------------------------
    if fax:
        qa.append((f"What is the fax number for {internal_name}?", fax))
        if office_number:
            qa.append((f"What is the fax number for office {office_number}?", fax))
        if mnemonic:
            qa.append((f"What is the fax number for {mnemonic}?", fax))

    # After-hours phone ---------------------------------------------------
    if after_hours:
        qa.append((f"What is the after-hours phone number for {internal_name}?", after_hours))
        if office_number:
            qa.append((f"What is the after-hours phone number for office {office_number}?", after_hours))
        if mnemonic:
            qa.append((f"What is the after-hours phone number for {mnemonic}?", after_hours))

    # Region -------------------------------------------------------------
    if region:
        qa.append((f"Which region is {internal_name} in?", region))
        if mnemonic:
            qa.append((f"Which region is {mnemonic} in?", region))

    # City, State, Zip ----------------------------------------------------
    if city:
        qa.append((f"What city is {internal_name} located in?", city))
    if state:
        qa.append((f"What state is {internal_name} in?", state))
    if zip_code and zip_code.lower() != "nan":
        qa.append((f"What is the ZIP code for {internal_name}?", zip_code))

    # Office number ------------------------------------------------------
    if office_number and internal_name:
        qa.append((f"What is the office number for {internal_name}?", office_number))

    # IP address ---------------------------------------------------------
    if ip_addr:
        qa.append((f"What is the IP address for {internal_name}?", ip_addr))
        if mnemonic:
            qa.append((f"What is the IP address for {mnemonic}?", ip_addr))

    return qa


def seed_office_faq(max_entries_per_office: int = 0) -> int:
    """Insert office Q&A pairs into *chat_qa* table.

    Args:
        max_entries_per_office: Optionally limit how many questions are
            generated for each office (0 = no limit).

    Returns:
        Number of **new** Q&A pairs inserted.
    """
    df = load_office_dataframe()
    if df.empty:
        return 0

    inserted = 0
    with current_app.app_context():
        # Prepare list for bulk insert -----------------------------------
        bulk_rows: list[dict] = []

        for _, row in df.iterrows():
            pairs = _qa_pairs_for_office(row)
            if max_entries_per_office > 0:
                pairs = pairs[:max_entries_per_office]

            for question, answer in pairs:
                # Skip duplicates first (cheap index lookup)
                exists = db.session.execute(
                    text("SELECT 1 FROM chat_qa WHERE lower(question)=:q LIMIT 1"),
                    {"q": question.lower()},
                ).fetchone()
                if exists:
                    continue

                bulk_rows.append({
                    "user": "Jarvis",
                    "question": question,
                    "answer": answer,
                })

        if bulk_rows:
            try:
                ensure_chat_qa_table()
                db.session.execute(
                    text(
                        """
                        INSERT INTO chat_qa (user, question, answer, timestamp)
                        VALUES (:user, :question, :answer, datetime('now'))
                        """
                    ),
                    bulk_rows,
                )
                db.session.commit()
                inserted = len(bulk_rows)

                # Invalidate chat history cache so new entries appear instantly
                try:
                    from app.blueprints.admin.routes import _invalidate_chat_history_cache
                    _invalidate_chat_history_cache()
                except Exception:
                    pass
            except Exception as exc:
                db.session.rollback()
                logger.warning(f"Office FAQ bulk insert failed: {exc}")

    return inserted 