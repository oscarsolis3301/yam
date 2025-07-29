import os
import logging
import requests
from pathlib import Path
from datetime import datetime
import re
import threading
import html as _html
import difflib
import shutil

from flask import jsonify, request, current_app, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import text
from flask_cors import cross_origin

from app.extensions import db
from app.utils.ai_helpers import (
    store_qa,
    find_semantic_qa,
    get_cached_response,
    set_cached_response,
    generate_cache_key,
    answer_query,
    evaluate_arithmetic,
)
from app.utils.ai_utils import process_document
from app.utils.models import get_model, get_embedder, FallbackModel
from app.utils.kb_import import import_docs_folder
from app.utils.log import log_upload, get_user_history

from . import bp  # Blueprint instance

logger = logging.getLogger('spark')

# ---------------------------------------------------------------------------
# Helper – shared embedder instance (if available)
# ---------------------------------------------------------------------------
embedder = get_embedder()

# ---------------------------------------------------------------------------
# Page route
# ---------------------------------------------------------------------------

@bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Render the Jarvis AI dashboard page."""
    return render_template('jarvis.html', active_page='jarvis')

# ---------------------------------------------------------------------------
# Status API
# ---------------------------------------------------------------------------

@bp.route('/status', methods=['GET'])
@login_required
def status():
    """Return the current health for the Jarvis AI service.

    The previous logic considered the assistant *offline* whenever the
    application was running with the lightweight *FallbackModel*. While that
    accurately reflects the absence of the full-featured LLM, from a user
    perspective the agent is still able to answer questions (albeit with
    limited capabilities).  We therefore treat **any** available model –
    including the fallback – as *online* and expose an extra *mode* field so
    the front-end can differentiate between *remote* and *local* execution
    when desired.
    """

    model = get_model()

    if model is None:
        # Something went really wrong – no model at all.
        return jsonify({'online': False})

    mode = 'remote' if not isinstance(model, FallbackModel) else 'local'
    return jsonify({'online': True, 'mode': mode})

# ---------------------------------------------------------------------------
# Chat history API
# ---------------------------------------------------------------------------

@bp.route('/history', methods=['GET'])
@login_required
def history():
    try:
        records = get_user_history()
        history_payload = [
            {
                'question': r[0],
                'answer': r[1],
                'feedback': r[2],
                'timestamp': r[3],
            }
            for r in records
        ]
        return jsonify(history_payload)
    except Exception as exc:
        logger.error("Failed to fetch chat history: %s", exc)
        return jsonify({'error': str(exc)}), 500

# ---------------------------------------------------------------------------
# Document upload API
# ---------------------------------------------------------------------------

@bp.route('/upload', methods=['POST'])
@login_required
def upload_doc():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext not in {'pdf', 'docx', 'txt'}:
        return jsonify({'error': 'Unsupported file type'}), 400

    try:
        docs_dir = os.path.join(current_app.root_path, 'static', 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        save_path = os.path.join(docs_dir, filename)
        file.save(save_path)

        # Log upload for audit purposes – now records *username* as well
        try:
            log_upload(request.remote_addr, filename, current_user.username)
        except Exception:
            pass

        # Note: the file is already saved directly inside *static/docs*, so
        # no further action is required here.

        # Kick off import in a background thread so the user does not need
        # to stay on the page while the (potentially slow) text extraction
        # and KB update run.  The *import_docs_folder* routine already uses
        # a lock file so concurrent calls are safe.

        def _run_import(app):
            # Ensure Flask application context within the thread
            with app.app_context():
                from app.utils.kb_import import import_docs_folder
                import_docs_folder(force=True)

        threading.Thread(
            target=_run_import,
            args=(current_app._get_current_object(),),  # Pass actual app instance
            daemon=True,
        ).start()

        return jsonify({'success': True, 'filename': filename})
    except Exception as exc:
        logger.error("Failed to upload/import document: %s", exc)
        return jsonify({'error': str(exc)}), 500

# ---------------------------------------------------------------------------
# Chat endpoint (main Jarvis brain)
# ---------------------------------------------------------------------------

@bp.route('', methods=['POST'])
@cross_origin()  # Allow public cross-origin calls
@login_required
def chat():  # noqa: C901 – complex but legacy logic retained
    try:
        # ------------------------------------------------------------------
        # Early *store-only* path: when the client already has an answer (e.g.
        # fetched from Cloudflare directly) it can POST both *question* and
        # *answer* so we simply persist the pair without re-processing.
        # ------------------------------------------------------------------
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Fast-track: persist Q&A only (skip all further processing)
        if data.get('question') and data.get('answer') and (data.get('file') is None):
            try:
                store_qa(current_user.username, data['question'].strip(), data['answer'].strip())
                return jsonify({'status': 'stored'}), 201
            except Exception as store_exc:
                logger.error('Store-only path failed: %s', store_exc)
                return jsonify({'error': 'Failed to store QA'}), 500

        # ---------------------------------------------------------------
        # ️👋  Friendly greeting shortcut --------------------------------
        # ---------------------------------------------------------------
        question_text = (data.get('question') or '').strip()
        if question_text:
            greet_match = re.match(r"\s*(hi|hello|hey|good\s*morn(?:ing)?|good\s*afternoon|good\s*evening)\s+jarvis[!. ,]*$", question_text, re.IGNORECASE)
            if greet_match:
                answer = f"Hi {current_user.username.title()}! How can I assist you today?"
                try:
                    store_qa(current_user.username, question_text, answer)
                except Exception:
                    pass
                return jsonify({'answer': answer})

        # Flag to disable expensive processing – front-end sets this when it
        # only wants an *existing* answer (DB/cache) without triggering the
        # local LLM or Cloudflare fallback.
        db_only = bool(data.get('db_only'))

        # ------------------------------------------------------------------
        # 1) If a file is included, process it via document handler
        # ------------------------------------------------------------------
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
                upload_dir.mkdir(parents=True, exist_ok=True)
                filepath = upload_dir / filename
                file.save(filepath)
                try:
                    result = process_document(str(filepath))

                    # ------------------------------------------------------------------
                    # Helper – basic HTML formatting for extracted text
                    # ------------------------------------------------------------------
                    def _format_text(txt: str) -> str:
                        if not txt:
                            return ''
                        # First escape HTML to avoid XSS, then enrich formatting
                        txt_escaped = _html.escape(txt)
                        # Bold enumerated step numbers ("1.", "2.")
                        txt_escaped = re.sub(r'(\b\d+\.)', r'<strong>\1</strong>', txt_escaped)
                        # Highlight NOTE sections
                        txt_escaped = re.sub(r'\bNOTE\s*:', r'<em>Note:</em>', txt_escaped, flags=re.IGNORECASE)
                        # Preserve paragraphs/newlines
                        txt_escaped = txt_escaped.replace('\n', '<br>')
                        # Collapse sequences of 3+ <br> to just two to avoid large vertical gaps
                        txt_escaped = re.sub(r'(?:<br>\s*){3,}', '<br><br>', txt_escaped)
                        return txt_escaped

                    def _select_top_questions(candidates: list[str], limit: int = 3) -> list[str]:
                        banned = {'select', 'click', 'choose', 'tab', 'follow', 'continue'}
                        # Filter trivial questions
                        useful = [q.strip() for q in candidates if len(q.split()) >= 4 and not any(word in q.lower().split() for word in banned)]
                        if not useful:
                            useful = [q.strip() for q in candidates]

                        # Deduplicate by semantic similarity (>= 0.8 via SequenceMatcher)
                        deduped: list[str] = []
                        for q in useful:
                            if any(difflib.SequenceMatcher(None, q.lower(), ex.lower()).ratio() >= 0.8 for ex in deduped):
                                continue
                            deduped.append(q)
                        # Sort by descending token count to prefer detailed questions
                        deduped.sort(key=lambda s: len(s.split()), reverse=True)
                        return deduped[:limit]

                    full_text_raw = result.get('text') or ''
                    # Use full text for question generation ---------------------------------
                    questions_all: list[str] = []
                    from app.utils.models import get_model, FallbackModel
                    _model = get_model()
                    if _model and not isinstance(_model, FallbackModel):
                        try:
                            prompt_q = (
                                "You are a helpful assistant creating FAQ-style questions. "
                                "Provide exactly three concise, relevant questions a user might ask after reading the following instructions. "
                                "Do NOT number the questions.\n\nINSTRUCTIONS:\n" + full_text_raw[:3500] +  # 3.5k chars safety limit
                                "\n\nQUESTIONS:\n"
                            )
                            raw_q = _model.generate(prompt_q, max_tokens=90)
                            questions_all = [q.strip("-• \t") for q in raw_q.splitlines() if q.strip()]
                        except Exception:
                            questions_all = result.get('questions', [])
                    else:
                        questions_all = result.get('questions', [])

                    # 1) Try local full model first ------------------------------------------------
                    if _model and not isinstance(_model, FallbackModel):
                        try:
                            raw_q = _model.generate(prompt_q, max_tokens=90)
                            questions_all = [q.strip("-• \t") for q in raw_q.splitlines() if q.strip()]
                        except Exception:
                            questions_all = []

                    # 2) Cloudflare worker fallback if we still don't have 3 useful questions -------
                    if len(questions_all) < 3:
                        try:
                            cf_worker_url = (
                                current_app.config.get('CLOUD_AI_ENDPOINT')
                                or os.getenv('CF_WORKER_URL')
                                or os.getenv('CLOUD_AI_ENDPOINT')
                                or 'https://spark.oscarsolis3301.workers.dev/'
                            )
                            resp = requests.post(
                                cf_worker_url.rstrip('/') + '/jarvis',
                                json={'question': prompt_q},
                                timeout=current_app.config.get('CLOUD_AI_TIMEOUT', 15)
                            )
                            if resp.ok:
                                data_cf = resp.json()
                                answer_cf = data_cf.get('answer') or data_cf.get('response') or ''
                                questions_all = [q.strip("-• \t") for q in answer_cf.splitlines() if q.strip()]
                        except Exception as cf_err:
                            logger.debug("Cloudflare question generation failed: %s", cf_err)

                    # 3) Heuristic fallback
                    if not questions_all:
                        questions_all = result.get('questions', [])

                    questions = _select_top_questions(questions_all)

                    # formatted_text = _format_text(full_text_raw)
                    summary_raw = result.get('summary') or ''
                    summary = _format_text(summary_raw)

                    html_parts = []
                    if summary:
                        # Show the *full* plain-language explanation immediately – no preview truncation needed
                        html_parts.append(
                            '<p><strong>Explanation (simplified):</strong> '
                            f'{summary}'
                            '</p>'
                        )

                    # ------------------------------------------------------
                    # *Do NOT* include the full extracted text by default – it
                    # can be lengthy and overwhelms the chat.  We keep it on
                    # the server for follow-up Q&A but omit it from the UI to
                    # satisfy the new requirement.
                    # ------------------------------------------------------
                    # If administrators still want access it can be re-enabled
                    # behind a feature flag or an *admin-only* toggle.

                    answer_html = ''.join(html_parts) or "I could not extract useful information from the file."

                    # ------------------------------------------------------------------
                    # Duplicate the uploaded file into the central *static/docs* directory
                    # so it is immediately visible on the admin dashboard.  Persist the
                    # uploader's username for full audit traceability.
                    # ------------------------------------------------------------------
                    try:
                        docs_dir = Path(current_app.root_path) / 'static' / 'docs'
                        docs_dir.mkdir(parents=True, exist_ok=True)
                        dest = docs_dir / filename
                        shutil.copy2(filepath, dest)

                        # Record the upload with username (new optional arg)
                        try:
                            log_upload(request.remote_addr, filename, current_user.username)
                        except Exception:
                            pass
                    except Exception as copy_err:
                        logger.warning("Jarvis chat: failed to copy file to docs dir – %s", copy_err)

                    return jsonify({'answer': answer_html})
                finally:
                    if filepath.exists():
                        filepath.unlink()

        # ------------------------------------------------------------------
        # 2) Standard question flow
        # ------------------------------------------------------------------
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        question = data.get('question', '').strip()
        if not question:
            return jsonify({'error': 'No question provided'}), 400

        # Holds any citation metadata returned by the Cloudflare worker so
        # we can surface them back to the client even when the answer is
        # later overridden (e.g. by the local model fallback).
        sources: list[dict] = []

        # ------------------------------------------------------------------
        # Greeting shortcuts – handle salutations such as:
        #   "Hi", "Hi Jarvis", "Hello there", "Good morning Jarvis" …
        # ------------------------------------------------------------------
        GREETING_RE = re.compile(
            r'^(hi|hello(?:\s+there)?|hey|greetings|good\s+(morning|afternoon|evening))(\s+jarvis)?[.!?\s]*$',
            re.IGNORECASE,
        )

        SMALL_TALK_RE = re.compile(
            r'^(how\s+are\s+you(?:\s+doing)?|how\'?s\s+it\s+going)(\s+jarvis)?[.!?\s]*$',
            re.IGNORECASE,
        )

        # --------------------------------------------------------------
        # New: readily answer *"What day is it today?"* without costly
        # look-ups so technicians receive an immediate, deterministic
        # response.
        # --------------------------------------------------------------
        DAY_RE = re.compile(r'^(what\s+is\s+the\s+day\s+today|what\s+day\s+is\s+it(?:\s+today)?)[?!.]*$', re.IGNORECASE)

        if GREETING_RE.match(question):
            # Personalised greeting using the caller's display name
            user_name = getattr(current_user, 'username', 'there') or 'there'
            answer = f"Hi {user_name}! How may I assist you today?"
            store_qa(current_user.username, question, answer)
            return jsonify({'answer': answer, 'question': question})

        if SMALL_TALK_RE.match(question):
            # Friendly status response
            answer = (
                "I'm operating optimally and ready to help! "
                "How can I assist you today?"
            )
            store_qa(current_user.username, question, answer)
            return jsonify({'answer': answer, 'question': question})

        if DAY_RE.match(question):
            today_str = datetime.utcnow().strftime('%A, %B %d, %Y')
            answer = f"Today is {today_str}."
            store_qa(current_user.username, question, answer)
            return jsonify({'answer': answer, 'question': question})

        # ------------------------------------------------------------------
        # Quick arithmetic evaluation (e.g., "What is 20+20")
        # ------------------------------------------------------------------
        math_res = evaluate_arithmetic(question)
        if math_res is not None:
            answer = math_res
            store_qa(current_user.username, question, answer)
            return jsonify({'answer': answer, 'question': question})

        # ------------------------------------------------------------------
        # Quick natural language checks – answer factual, deterministic
        # questions locally before incurring DB lookups or external API hits.
        # ------------------------------------------------------------------
        TIME_RE = re.compile(r"^what\s+time\s+is\s+it\s+in\s+([a-zA-Z\s]+)[?!.]*$", re.IGNORECASE)
        m_time = TIME_RE.match(question)
        if m_time:
            # Normalise the captured city name to map it to a timezone
            city_raw = m_time.group(1).strip().lower()
            city_to_tz = {
                'los angeles': 'America/Los_Angeles',
                'la': 'America/Los_Angeles',
                'new york': 'America/New_York',
                'nyc': 'America/New_York',
                'chicago': 'America/Chicago',
                'denver': 'America/Denver',
                'london': 'Europe/London',
                'paris': 'Europe/Paris',
                'tokyo': 'Asia/Tokyo',
                'sydney': 'Australia/Sydney',
                'berlin': 'Europe/Berlin',
                'seattle': 'America/Los_Angeles',
                'san francisco': 'America/Los_Angeles',
                'houston': 'America/Chicago',
                'phoenix': 'America/Phoenix',
            }
            tz_name = city_to_tz.get(city_raw)
            if tz_name:
                try:
                    import pytz
                    now_city = datetime.now(pytz.timezone(tz_name))
                    answer = f"The current time in {city_raw.title()} is {now_city.strftime('%I:%M %p on %A, %B %d, %Y')}."
                except Exception as tz_err:
                    logger.warning("Timezone lookup failed: %s", tz_err)
                    answer = "I'm sorry, I couldn't determine the time right now."
            else:
                # If city is unknown, fall back to WorldTimeAPI for broader support
                try:
                    # Use globally imported *requests* module to avoid Python
                    # treating it as a local variable, which previously caused
                    # the "local variable 'requests' referenced before
                    # assignment" UnboundLocalError.
                    r = requests.get("http://worldtimeapi.org/api/timezone", timeout=5)
                    if r.ok:
                        zones = r.json()
                        # naive search: pick first zone that ends with the city name capitalised correctly
                        matches = [z for z in zones if z.lower().endswith('/' + city_raw.replace(' ', '_'))]
                        if matches:
                            tz_name = matches[0]
                            r2 = requests.get(f"http://worldtimeapi.org/api/timezone/{tz_name}", timeout=5)
                            if r2.ok:
                                data = r2.json()
                                dt = datetime.fromisoformat(data['datetime'].rstrip('Z'))
                                answer = f"The current time in {city_raw.title()} is {dt.strftime('%I:%M %p on %A, %B %d, %Y')}."
                            else:
                                answer = "I'm sorry, I couldn't get the current time right now."
                        else:
                            answer = "I'm not sure which timezone that city belongs to."
                    else:
                        answer = "I'm sorry, I couldn't fetch the time information."
                except Exception as web_err:
                    logger.warning("WorldTimeAPI lookup failed: %s", web_err)
                    answer = "I'm sorry, I couldn't determine the time right now."
            store_qa(current_user.username, question, answer)
            return jsonify({'answer': answer, 'question': question})

        cache_key = generate_cache_key(question, '')

        # 0) Exact match in DB
        try:
            row = db.session.execute(
                text('SELECT answer FROM chat_qa WHERE lower(question) = :q ORDER BY timestamp DESC LIMIT 1'),
                {'q': question.lower()},
            ).fetchone()
            if row and row[0]:
                answer = row[0]
                set_cached_response(cache_key, answer)
                # --------------------------------------------------------------
                # Log the exact source used so administrators can see in the
                # terminal whether the response came from the *QA database*.
                # --------------------------------------------------------------
                logger.info("[Jarvis] Source=QA_DB user=%s question=%s", current_user.username, question)
                return jsonify({'answer': answer, 'question': question})
        except Exception as lookup_err:
            logger.warning("Exact QA lookup failed: %s", lookup_err)

        # 1) Cache lookup
        cached = get_cached_response(cache_key)
        if cached:
            return jsonify({'answer': cached, 'question': question})

        # 2) Semantic similar QA
        similar = find_semantic_qa(question, fuzzy_threshold=100)
        if similar:
            set_cached_response(cache_key, similar)
            store_qa(current_user.username, question, similar)
            # --------------------------------------------------------------
            # Log the exact source used so administrators can see in the
            # terminal whether the response came from the *QA database*.
            # --------------------------------------------------------------
            logger.info("[Jarvis] Source=QA_DB (semantic) user=%s question=%s", current_user.username, question)
            return jsonify({'answer': similar, 'question': question})

        # If the caller requested *db_only*, bail out early so the front-end
        # can decide what to do (e.g. call Cloudflare directly).
        if db_only:
            return jsonify({'answer': '', 'question': question})

        # ---------------------- PERFORMANCE FAST-PATH ----------------------
        # When running offline or when administrators explicitly disable
        # cloud look-ups via *USE_CLOUD_AI=False*, skip the network calls that
        # can add ~30 s latency and fall back directly to the local model.
        # -------------------------------------------------------------------
        if current_app.config.get('OFFLINE_MODE') or not current_app.config.get('USE_CLOUD_AI', True):
            logger.info("[Jarvis] Cloud AI disabled – using local model for question from %s", current_user.username)
            answer = answer_query(question, user=current_user.username)
            store_qa(current_user.username, question, answer)
            set_cached_response(cache_key, answer)
            return jsonify({'answer': answer, 'question': question})

        # We still want to try the cloud endpoint even when the local model is
        # a lightweight fallback.  The remote worker often provides far
        # better answers with only a minor latency penalty (<1 s when the
        # service is reachable).  If it fails or times-out we'll gracefully
        # fall back to the local rule-based engine further down.

        # 3) External worker (Cloudflare) fallback
        answer = None
        cf_worker_url = (
            current_app.config.get('CLOUD_AI_ENDPOINT')
            or os.getenv('CF_WORKER_URL')
            or os.getenv('CLOUD_AI_ENDPOINT')
            or 'https://spark.oscarsolis3301.workers.dev/'
        )

        def _call_worker(base_url: str) -> dict | None:
            """Call the Cloudflare worker and return a dict with at least an 'answer' key.

            The helper now preserves additional metadata (e.g. 'sources', 'usage') when
            available so the front-end can display richer information just like the
            native Cloudflare chat widget.
            """
            # 1) Modern /jarvis endpoint (preferred)
            modern_url = base_url.rstrip('/') + '/jarvis'
            try:
                resp = requests.post(
                    modern_url,
                    json={"question": question},
                    timeout=current_app.config.get('CLOUD_AI_TIMEOUT', 10),
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and (
                    'answer' in data or 'response' in data
                ):
                    # Normalise field so downstream logic can always use 'answer'
                    if 'answer' not in data and 'response' in data:
                        data['answer'] = data['response']
                    return data
            except Exception as modern_err:
                logger.debug("Modern worker call via %s failed: %s", modern_url, modern_err)

            # 2) Legacy root endpoint – returns list[{{ response: {{ response: str }} }}]
            legacy_payload = {"inputs": [{"prompt": question}]}
            try:
                resp = requests.post(
                    base_url,
                    json=legacy_payload,
                    timeout=current_app.config.get('CLOUD_AI_TIMEOUT', 10),
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list) and data:
                    legacy_answer = data[0].get("response", {}).get("response")
                    if legacy_answer:
                        return {"answer": legacy_answer, "sources": []}
            except Exception as legacy_err:
                logger.debug("Legacy worker call via %s failed: %s", base_url, legacy_err)

            return None

        # 3a) Normal DNS resolution first
        worker_data = _call_worker(cf_worker_url)

        if worker_data:
            answer = worker_data.get('answer')
            sources = worker_data.get('sources', [])
            logger.info("[Jarvis] Source=CLOUDFLARE user=%s question=%s", current_user.username, question)
        else:
            answer = None
            sources = []

        # 3b) If DNS failed (NameResolutionError) attempt DoH fallback
        if answer is None:
            try:
                host = requests.utils.urlparse(cf_worker_url).hostname
                doh_resp = requests.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": host, "type": "A"},
                    headers={"accept": "application/dns-json"},
                    timeout=3,
                )
                doh_data = doh_resp.json()
                ip = None
                for ans in doh_data.get("Answer", []):
                    if ans.get("type") == 1:  # A record
                        ip = ans.get("data")
                        break
                if ip:
                    ip_url = cf_worker_url.replace(host, ip)
                    worker_data = _call_worker(ip_url)
                    if worker_data:
                        answer = worker_data.get('answer')
                        sources = worker_data.get('sources', [])
                        logger.info("[Jarvis] Source=CLOUDFLARE user=%s question=%s", current_user.username, question)
                    else:
                        answer = None
                        sources = []
            except Exception as dns_exc:
                logger.debug("DoH DNS fallback failed: %s", dns_exc)

        # 4) Local model fallback
        if not answer:
            logger.info("[Jarvis] Attempting LOCAL_MODEL fallback for question from %s", current_user.username)
            answer = answer_query(question, user=current_user.username)
            try:
                from app.utils.models import get_model, FallbackModel
                model_inst = get_model()
                model_type = (
                    "FALLBACK_MODEL" if isinstance(model_inst, FallbackModel) else
                    getattr(model_inst, 'model_name', model_inst.__class__.__name__)
                )
            except Exception:
                model_type = "LOCAL_MODEL"
            logger.info("[Jarvis] Source=%s user=%s question=%s", model_type, current_user.username, question)

        # Persist and cache
        store_qa(current_user.username, question, answer)
        set_cached_response(cache_key, answer)

        return jsonify({'answer': answer, 'question': question, 'sources': sources})

    except Exception as exc:
        logger.error("Error in Jarvis chat endpoint: %s", exc)
        return jsonify({'error': str(exc)}), 500

# ---------------------------------------------------------------------------
# Knowledge documents listing
# ---------------------------------------------------------------------------

@bp.route('/docs', methods=['GET'])
@login_required
def docs_list():
    """Return a list of documents currently available to Jarvis."""
    docs_dir = Path(current_app.root_path) / 'static' / 'docs'
    docs_info = []

    # ------------------------------------------------------------------
    # Build a mapping *filename -> (user_name, timestamp)* from the uploads
    # log so we can expose **who** uploaded each document.
    # ------------------------------------------------------------------
    uploads_meta: dict[str, tuple[str | None, str | None]] = {}
    try:
        import sqlite3
        from log import DB_PATH as LOG_DB_PATH  # Re-use existing logging DB
        with sqlite3.connect(LOG_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT filename, user_name, timestamp FROM uploads ORDER BY timestamp DESC")
            for fname, uname, ts in cur.fetchall():
                # Store first (most recent) entry only
                if fname not in uploads_meta:
                    uploads_meta[fname] = (uname, ts)
    except Exception as meta_err:
        logger.debug("Failed to read uploads metadata: %s", meta_err)

    if docs_dir.exists():
        for path in docs_dir.rglob('*'):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {'.pdf', '.docx', '.txt'}:
                continue
            try:
                uploader, ts_uploaded = uploads_meta.get(path.name, (None, None))
                info = {
                    'name': path.name,
                    'relative_path': str(path.relative_to(docs_dir).as_posix()),
                    'size_kb': round(path.stat().st_size / 1024, 1),
                    'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds'),
                    'uploaded_by': uploader,
                    'uploaded_at': ts_uploaded,
                }
                docs_info.append(info)
            except Exception:
                # Skip any file that causes issues
                continue
    return jsonify(docs_info) 