import os
import requests
import sqlite3
import time
import json
import re
from tqdm import tqdm, trange
from pathlib import Path
from datetime import datetime
import traceback
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)
load_dotenv()

API_KEY = os.getenv('FRESH_API')
FRESHSERVICE_DOMAIN = os.getenv('FRESH_ENDPOINT')
HEADERS = {"Content-Type": "application/json"}
AUTH = (API_KEY, "X")

SAVE_DIR = Path("tickets")
SAVE_DIR.mkdir(exist_ok=True)
LOG_FILE = "ticket_log.txt"
CHECKPOINT_FILE = "ticket_checkpoint.txt"
DB_FILE = "tickets.db"
LOG_DB_FILE = "log_tracking.db"
SLEEP_BETWEEN_CALLS = .5

def log(msg, level="INFO"):
    full_msg = timestamped(msg)
    print(full_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")
    log_to_db(level, msg)

def timestamped(msg):
    return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"

def log_to_db(level, message):
    conn_log = sqlite3.connect(LOG_DB_FILE)
    c_log = conn_log.cursor()
    c_log.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            message TEXT
        )
    """)
    c_log.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
                  (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level, message))
    conn_log.commit()
    conn_log.close()

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    subject TEXT,
    description TEXT,
    status TEXT,
    priority TEXT,
    requester_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    category TEXT,
    sub_category TEXT,
    item_category TEXT,
    full_text TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    body TEXT,
    incoming BOOLEAN,
    private BOOLEAN,
    created_at TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    name TEXT,
    url TEXT,
    local_path TEXT
)
""")
conn.commit()

def retry_with_backoff(func, *args, max_attempts=10, **kwargs):
    delay = 10
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log(Fore.RED + f"Attempt {attempt+1}/{max_attempts} failed: {e}", level="ERROR")
            traceback.print_exc()
            if "Rate limited" in str(e):
                log(Fore.YELLOW + "Rate limited detected. Waiting 5 minutes...", level="WARNING")
                time.sleep(300)
            else:
                time.sleep(delay)
                delay = min(delay * 2, 300)
    raise Exception(f"Max retries exceeded for function {func.__name__}")

def get_last_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        return None
    with open(CHECKPOINT_FILE, "r") as f:
        return f.read().strip()

def save_checkpoint(ticket_id):
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(ticket_id))

def get_tickets():
    page = 1
    per_page = 100
    last_checkpoint = get_last_checkpoint()
    found_checkpoint = not last_checkpoint

    while True:
        url = f"{FRESHSERVICE_DOMAIN}tickets?page={page}&per_page={per_page}"

        def _fetch():
            response = requests.get(url, auth=AUTH, headers=HEADERS)
            if response.status_code == 429:
                raise Exception("Rate limited")
            response.raise_for_status()
            return response

        try:
            response = retry_with_backoff(_fetch)
        except Exception as e:
            log(Fore.RED + f"Failed to fetch tickets page {page}: {e}", level="ERROR")
            break

        data = response.json()
        tickets = data.get("tickets", [])
        if not tickets:
            break

        log(Fore.CYAN + f"\n\nProcessing page {page} with {len(tickets)} tickets...\n\n")
        for i in trange(len(tickets), desc=f"Page {page} - Ticket", leave=False):
            ticket = tickets[i]
            ticket_id = str(ticket["id"])
            folder = SAVE_DIR / f"INC-{ticket_id}"

            if not found_checkpoint:
                if ticket_id == last_checkpoint:
                    found_checkpoint = True
                continue

            if all((folder / f"INC-{ticket_id}{suffix}").exists() for suffix in [".json", ".txt", "_FULL.txt"]):
                log(Fore.BLUE + f"Skipping existing ticket INC-{ticket_id}")
                continue

            save_checkpoint(ticket_id)
            yield ticket
            time.sleep(SLEEP_BETWEEN_CALLS)
        page += 1

def save_ticket_data(ticket):
    ticket_id = ticket["id"]
    folder = SAVE_DIR / f"INC-{ticket_id}"
    folder.mkdir(exist_ok=True)

    log(Fore.GREEN + f"\n\nWorking on INC-{ticket_id}\n\n")

    summary_file = folder / f"INC-{ticket_id}.txt"
    full_file = folder / f"INC-{ticket_id}_FULL.txt"
    json_file = folder / f"INC-{ticket_id}.json"

    full_text_content = []

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"# Ticket Summary\n\n")
        for key in ["subject", "status", "priority", "requester_id", "created_at", "updated_at", "category", "sub_category", "item_category"]:
            value = ticket.get(key, '')
            f.write(f"**{key.replace('_', ' ').title()}:** {value}\n\n")
            full_text_content.append(f"{key}: {value}")
        f.write("## Description\n\n")
        desc = re.sub(r'<[^>]+>', '', ticket.get("description", ""))
        f.write(desc + "\n")
        full_text_content.append(f"Description: {desc}")

    with open(full_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(ticket, indent=2))

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(ticket, f, indent=2)

    try:
        conversations = retry_with_backoff(get_conversations, ticket_id)
    except Exception as e:
        log(Fore.RED + f"Failed to fetch conversations for ticket {ticket_id}: {e}", level="ERROR")
        conversations = []

    if conversations:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("\n## Conversations\n")
            for convo in conversations:
                if convo.get("private"):
                    continue
                body = re.sub(r'<[^>]+>', '', convo.get("body", ""))
                if body.strip():
                    f.write(f"\n---\n\n{body}\n")
                    full_text_content.append(f"Conversation: {body}")

    try:
        attachments = retry_with_backoff(get_attachments, ticket_id)
    except Exception as e:
        log(Fore.RED + f"Failed to fetch attachments for ticket {ticket_id}: {e}", level="ERROR")
        attachments = []

    for attachment in attachments:
        name = attachment.get("name")
        url = attachment.get("attachment_url")
        if not name or not url:
            continue
        file_path = folder / name

        if not file_path.exists():
            for attempt in range(2):
                try:
                    r = requests.get(url, auth=AUTH)
                    if r.status_code == 429:
                        log(Fore.RED + f"Rate limited downloading attachment {url}. Sleeping 20 seconds...", level="WARNING")
                        time.sleep(20)
                        continue
                    r.raise_for_status()
                    with open(file_path, 'wb') as out:
                        out.write(r.content)
                    break
                except Exception as e:
                    if attempt == 1:
                        log(Fore.RED + f"Failed to download {url}: {e}", level="ERROR")
                    else:
                        time.sleep(20)

        log(Fore.GREEN + f"Downloaded attachment '{name}' for ticket {ticket_id}", level="INFO")
        with open(folder / "attachment_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Downloaded: {name}\n")

        c.execute("""
            INSERT OR IGNORE INTO attachments (id, ticket_id, name, url, local_path)
            VALUES (?, ?, ?, ?, ?)
        """, (attachment["id"], ticket_id, name, url, str(file_path)))
        conn.commit()

    c.execute("""
        INSERT OR REPLACE INTO tickets (id, subject, description, status, priority, requester_id, created_at, updated_at, category, sub_category, item_category, full_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_id,
        ticket.get("subject"),
        ticket.get("description"),
        ticket.get("status"),
        ticket.get("priority"),
        ticket.get("requester_id"),
        ticket.get("created_at"),
        ticket.get("updated_at"),
        ticket.get("category"),
        ticket.get("sub_category"),
        ticket.get("item_category"),
        "\n".join(full_text_content)
    ))
    conn.commit()

def get_conversations(ticket_id):
    url = f"{FRESHSERVICE_DOMAIN}tickets/{ticket_id}/conversations"
    response = requests.get(url, auth=AUTH, headers=HEADERS)
    if response.status_code == 429:
        raise Exception("Rate limited fetching conversations")
    if response.status_code != 200:
        raise Exception(f"Failed to fetch conversations: {response.status_code}")
    return response.json().get("conversations", [])

def get_attachments(ticket_id):
    url = f"{FRESHSERVICE_DOMAIN}tickets/{ticket_id}/conversations"
    response = requests.get(url, auth=AUTH, headers=HEADERS)
    if response.status_code == 429:
        raise Exception("Rate limited fetching attachments")
    if response.status_code != 200:
        raise Exception(f"Failed to fetch attachments: {response.status_code}")
    attachments = []
    for convo in response.json().get("conversations", []):
        for att in convo.get("attachments", []):
            att["ticket_id"] = ticket_id
            attachments.append(att)
    return attachments

def main():
    total = 0
    failures = 0
    log(Fore.CYAN + "Rehydrating database with all current tickets...")
    for ticket in tqdm(get_tickets(), desc="Processing tickets"):
        try:
            save_ticket_data(ticket)
            total += 1
        except Exception as e:
            log(Fore.RED + f"Unhandled error saving ticket {ticket['id']}: {e}", level="ERROR")
            traceback.print_exc()
            failures += 1
            continue
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    log(Fore.GREEN + f"\nSummary:\nTotal Processed: {total}\nFailures: {failures}\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(Fore.RED + f"Fatal error in main execution: {e}", level="CRITICAL")
        traceback.print_exc()
        while True:
            log(Fore.YELLOW + "Sleeping 5 minutes before retrying main loop...", level="WARNING")
            time.sleep(300)
            try:
                main()
                break
            except Exception as e:
                log(Fore.RED + f"Retry failed: {e}", level="ERROR")
                traceback.print_exc()
