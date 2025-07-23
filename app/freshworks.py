import requests
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urlencode

# ── Load API credentials ─────────────────────────────────────────────
load_dotenv()
FRESH_API = os.getenv('FRESH_API')
FRESH_ENDPOINT = os.getenv('FRESH_ENDPOINT')

headers = {
    "Content-Type": "application/json"
}

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "Freshworks")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_GROUP_ID = 18000305996
TARGET_STATUS   = 10  # Awaiting Vendor

DEFAULT_TIMEOUT = 15  # seconds – tweak as necessary to avoid long blocking calls
MAX_RETRIES     = 3   # basic retry logic for transient errors

session = requests.Session()
# Enable HTTP keep-alive + retry logic at the *session* level for better efficiency
adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
session.mount("https://", adapter)
session.mount("http://",  adapter)

# Ensure stdout/stderr can emit Unicode even when redirected to a PIPE on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        # Fallback – ignore if the method is unsupported or fails
        pass

def today_iso():
    return datetime.utcnow().strftime('%Y-%m-%dT00:00:00Z')

def today_date():
    return datetime.utcnow().strftime('%Y-%m-%d')

def fetch_all_today_tickets():
    tickets, page = [], 1
    while True:
        params = {"updated_since": today_iso(), "per_page": 100, "page": page}
        url    = f"{FRESH_ENDPOINT}tickets?{urlencode(params)}"
        try:
            r = session.get(url,
                            auth=(FRESH_API, "X"),
                            headers=headers,
                            timeout=DEFAULT_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            print(f"[ERROR] Network error while fetching page {page}: {exc}")
            # On any network-level issue we break so the caller can decide next steps
            break

        if r.status_code != 200:
            print(f"[ERROR] Page {page}: {r.status_code} – {r.text}")
            break

        batch = r.json().get("tickets", [])
        print(f"[DEBUG] Page {page} returned {len(batch)} tickets")
        if not batch:
            break

        tickets.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return tickets

def fetch_notes(ticket_id):
    """Fetch private notes (not public replies) for a ticket."""
    url = f"{FRESH_ENDPOINT}tickets/{ticket_id}/conversations"
    try:
        r = session.get(url,
                        auth=(FRESH_API, "X"),
                        headers=headers,
                        timeout=DEFAULT_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        print(f"[WARN] Could not fetch notes for ticket {ticket_id}: {exc}")
        return []

    if r.status_code != 200:
        return []

    return [
        note.get("body_text", "").strip()
        for note in r.json().get("conversations", [])
        if note.get("private") is True
    ]

def filter_tickets(tickets):
    today = today_date()
    return [
        t for t in tickets
        if t.get("status")    == TARGET_STATUS
        and t.get("group_id") == TARGET_GROUP_ID
        and t.get("created_at", "").startswith(today)
    ]

def save_tickets(tickets):
    today     = today_date()
    filename  = os.path.join(OUTPUT_DIR, f"{today}.txt")

    # ── 1) Read existing ticket IDs ──────────────────────────────
    existing_ids = set()
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Ticket #"):
                    try:
                        existing_ids.add(int(line.split("#")[1].strip()))
                    except ValueError:
                        pass                    # malformed line – just ignore

    # ── 2) Keep only the tickets we haven't stored yet ───────────
    new_tickets = [t for t in tickets if t["id"] not in existing_ids]
    if not new_tickets:
        print("✅ No new tickets to add – file already current.")
        return

    # ── 3) Append the new tickets ───────────────────────────────
    with open(filename, "a", encoding="utf-8") as f:
        for t in new_tickets:
            ticket_id    = t["id"]
            subject      = t.get("subject", "")
            description  = t.get("description_text", "").strip()
            group_id     = t.get("group_id", "None")
            responder_id = t.get("responder_id", "Unassigned")
            created_at   = t.get("created_at", "")
            status       = t.get("status", "")
            notes        = fetch_notes(ticket_id)

            f.write(f"Ticket #{ticket_id}\n")
            f.write(f"Ticket-Title : {subject}\n")
            f.write(f"Group ID     : {group_id}\n")
            f.write(f"Assigned To  : {responder_id}\n")
            f.write(f"Created At   : {created_at}\n")
            f.write(f"Status       : {status}\n")
            f.write(f"Ticket-Description:\n{description}\n")
            if notes:
                f.write("\nNotes:\n")
                for idx, note in enumerate(notes, 1):
                    f.write(f"  [{idx}] {note}\n")
            f.write("-" * 60 + "\n")

    print(f"✅ Added {len(new_tickets)} new ticket(s) to {filename}")

# ── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_tix  = fetch_all_today_tickets()
    filt_tix = filter_tickets(all_tix)

    print(f"\nFound {len(filt_tix)} ticket(s) with status {TARGET_STATUS}, group {TARGET_GROUP_ID}, created today.\n")
    save_tickets(filt_tix)
