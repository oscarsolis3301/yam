import logging
from extensions import db
from app.config import Config
import sqlite3
import hashlib
import json
from datetime import datetime
from sqlalchemy import text
from flask import current_app
import numpy as np
from app.utils.models import get_embedder, FallbackEmbedder, get_model, FallbackModel
from extensions import socketio  # Emits events so admin UI updates instantly
import re
from rapidfuzz import fuzz
from app.models import KBArticle
from sklearn.metrics.pairwise import cosine_similarity
import ast  # Needed for safe arithmetic evaluation

logger = logging.getLogger('spark')

# Cache management
_cached_responses = {}

def ensure_cache_table():
    """Ensure the cache table exists"""
    try:
        with current_app.app_context():
            db.session.execute(text('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.session.commit()
            return True
    except Exception as e:
        logger.error(f"Error ensuring cache table: {str(e)}")
        db.session.rollback()
        return False

def get_cached_response(cache_key):
    """Get a cached response if it exists and is not expired"""
    try:
        with current_app.app_context():
            ensure_cache_table()  # Ensure table exists
            result = db.session.execute(
                text('SELECT value FROM cache WHERE key = :key AND timestamp > datetime("now", "-1 hour")'),
                {'key': cache_key}
            ).fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting cached response: {str(e)}")
        return None

def set_cached_response(cache_key, value):
    """Cache a response with the given key"""
    try:
        with current_app.app_context():
            ensure_cache_table()  # Ensure table exists
            db.session.execute(
                text('INSERT OR REPLACE INTO cache (key, value) VALUES (:key, :value)'),
                {'key': cache_key, 'value': value}
            )
            db.session.commit()
            return True
    except Exception as e:
        logger.error(f"Error setting cached response: {str(e)}")
        db.session.rollback()
        return False

def generate_cache_key(text, context: str = "") -> str:
    """Return a hash that is stable across minor paraphrasing.

    The input strings are first normalised so *"what's"* and *"what is"* map to
    the same cache key, drastically improving hit-rate while still keeping the
    key short and deterministic.
    """
    key_string = f"{_normalize(text)}:{_normalize(context)}"
    return hashlib.md5(key_string.encode()).hexdigest()

# ---------------------------------------------------------------------------
# Arithmetic evaluation helper
# ---------------------------------------------------------------------------

_SAFE_ARITH_CHARS = set("0123456789+-*/(). ")

def _evaluate_arithmetic(question: str):
    """Return a string result if *question* looks like a simple arithmetic
    expression like "what is 10+10".  Otherwise return *None* so the normal
    pipeline can proceed.

    The implementation strips common lead-in words ("what is", "calculate",
    etc.), replaces basic English operators ("plus", "minus", "times",
    "divided by") with symbols, validates the remaining string only contains
    safe characters, then evaluates it with ``ast`` to avoid the security
    risks of raw ``eval``.
    """

    if not question:
        return None

    q = question.lower()
    # Replace some word operators with symbols for convenience
    replacements = {
        " plus ": "+",
        " minus ": "-",
        " times ": "*",
        " x ": "*",
        " divided by ": "/",
        " multiply by ": "*",
    }
    for k, v in replacements.items():
        q = q.replace(k, v)

    # Remove common leading words / punctuation
    q = q.replace("what is", "").replace("what's", "").replace("calculate", "")
    q = q.replace("?", " ").replace("=", " ").strip()

    # Collapse whitespace
    q = re.sub(r"\s+", "", q)

    # Quick sanity check – must contain at least one operator or be purely numeric
    if not any(op in q for op in "+-*/"):
        return None

    # Validate characters
    if not all(ch in _SAFE_ARITH_CHARS for ch in q):
        return None

    try:
        node = ast.parse(q, mode="eval")
        # Ensure only a safe subset of AST node types are present
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Num,
            ast.Constant,  # Py>=3.8
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.Load,
            ast.USub,
            ast.UAdd,
            ast.FloorDiv,
            ast.LShift,
            ast.RShift,
            ast.BitOr,
            ast.BitXor,
            ast.BitAnd,
        )
        for n in ast.walk(node):
            if not isinstance(n, allowed_nodes):
                return None

        result = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {})
        # Convert to int when the result is an integer value like 20.0 → 20
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)
    except Exception:
        return None

# Public wrapper so other modules can import without accessing the leading underscore function name.
def evaluate_arithmetic(question: str):
    """Return the arithmetic evaluation result as *str* or *None* if the
    prompt is not a simple maths query.  Thin wrapper around the internal
    helper so external callers don't rely on a private name.
    """
    return _evaluate_arithmetic(question)

# ---------------------------------------------------------------------------
# Database management helpers
# ---------------------------------------------------------------------------

CHAT_QA_DB = "chat_qa.db"

# Memoisation flag so we don't re-run DDL on every call (saves ~100 ms per
# insert during large seed operations and avoids log spam).
_chat_qa_ready: bool = False


def ensure_chat_qa_table() -> bool:
    """Create *chat_qa* table **once** and return ``True`` when ready.

    Subsequent calls become instant no-ops thanks to the module-level flag.
    We also create an index on *lower(question)* so look-ups via
    ``find_semantic_qa`` remain fast even with tens of thousands of rows.
    """

    global _chat_qa_ready
    if _chat_qa_ready:
        return True

    try:
        # Ensure we have a proper Flask app context
        from flask import has_app_context, current_app
        if not has_app_context():
            logger.debug("No app context available for chat QA table creation")
            return False
            
        # Test database connectivity before proceeding
        try:
            db.session.execute(text('SELECT 1'))
        except Exception as db_test_err:
            logger.debug(f"Database not ready for chat QA table creation: {db_test_err}")
            return False

        # ------------------------------------------------------------------
        # 1) Persistent **unique** Q&A table used for semantic lookup
        # ------------------------------------------------------------------
        # Create table if it doesn't exist ---------------------------------
        db.session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS chat_qa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    image_path TEXT,
                    image_caption TEXT,
                    embedding BLOB
                )
                """
            )
        )

        # ------------------------------------------------------------------
        # 2) Raw chat_history table – stores *all* interactions verbatim even
        # if they duplicate previous ones.  This keeps a full audit trail for
        # analytics / troubleshooting while the assistant works exclusively
        # with the de-duplicated *chat_qa* table.
        # ------------------------------------------------------------------

        db.session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    image_path TEXT,
                    image_caption TEXT
                )
                """
            )
        )

        # ------------------------------------------------------------------
        # Remove duplicates in *chat_qa* so each (question, answer) pair is
        # unique (case-insensitive). We keep the earliest *id*.
        # ------------------------------------------------------------------

        db.session.execute(
            text(
                """
                DELETE FROM chat_qa
                WHERE id NOT IN (
                    SELECT MIN(id) FROM chat_qa GROUP BY lower(question), lower(answer)
                )
                """
            )
        )

        # Helpful index for fast *question* equality searches --------------
        db.session.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_chatqa_question
                ON chat_qa (lower(question));
                """
            )
        )

        db.session.commit()
        _chat_qa_ready = True
        logger.info("Chat QA table verified/ready")
        return True

    except Exception as e:
        logger.error(f"Error ensuring chat QA table: {e}")
        db.session.rollback()
        return False

def store_qa(user, question, answer, image_path=None, image_caption=None):
    """Persist a *(question, answer)* pair.

    We serialise the embedding (``float32`` NumPy array → bytes) so that it can
    be read back efficiently without re-computing for every similarity check.
    """
    try:
        with current_app.app_context():
            ensure_chat_qa_table()

            # Compute embedding if possible – fall back to *None*.
            embedding_blob = None
            try:
                emb = get_embedder()
                if emb and not isinstance(emb, FallbackEmbedder):
                    embedding_blob = emb.encode([question])[0].astype('float32').tobytes()
            except Exception as enc_err:
                logger.warning(f"Embedding generation failed: {enc_err}")

            # Skip if answer is clearly generic / unhelpful ----------------
            if _is_generic_answer(answer):
                logger.debug("Generic answer detected – skipping DB insert: %s", answer[:40])
                return True

            # Insert into chat_history unconditionally (full log) ----------
            try:
                db.session.execute(
                    text(
                        """
                        INSERT INTO chat_history (user, question, answer, image_path, image_caption, timestamp)
                        VALUES (:user, :question, :answer, :image_path, :image_caption, datetime('now'))
                        """
                    ),
                    {
                        'user': str(user),
                        'question': question,
                        'answer': answer,
                        'image_path': image_path,
                        'image_caption': image_caption,
                    },
                )
            except Exception as hist_exc:
                logger.warning(f"Failed to write to chat_history: {hist_exc}")

            # ------------------------------------------------------------------
            # Deduplication logic for chat_qa (unique knowledge base)
            # ------------------------------------------------------------------

            dup = db.session.execute(
                text(
                    """
                    SELECT 1 FROM chat_qa
                    WHERE lower(question)=:q AND lower(answer)=:a
                    LIMIT 1
                    """
                ),
                {"q": question.lower(), "a": answer.lower()},
            ).fetchone()

            if dup is None:
                db.session.execute(
                    text(
                        """
                        INSERT INTO chat_qa (user, question, answer, image_path, image_caption, embedding, timestamp)
                        VALUES (:user, :question, :answer, :image_path, :image_caption, :embedding, datetime('now'))
                        """
                    ),
                    {
                        'user': str(user),
                        'question': question,
                        'answer': answer,
                        'image_path': image_path,
                        'image_caption': image_caption,
                        'embedding': embedding_blob
                    }
                )
                db.session.commit()

                # Invalidate in-memory admin cache so next AJAX fetch returns
                # the freshly-inserted record without waiting for TTL expiry.
                try:
                    from app.blueprints.admin.routes import _invalidate_chat_history_cache
                    _invalidate_chat_history_cache()
                except Exception as inv_err:
                    logger.debug(f"Cache invalidation skipped: {inv_err}")

                # Only emit socket event on *new* insert so the front-end doesn't
                # append duplicates in real-time.
                try:
                    socketio.emit(
                        "chatqa_new",
                        {
                            "timestamp": datetime.utcnow().isoformat(),
                            "user": str(user),
                            "question": question,
                            "answer": answer,
                        },
                    )
                except Exception as emit_err:
                    logger.warning(f"Failed to emit chatqa_new event: {emit_err}")
            else:
                # Duplicate detected – silently skip insert without raising.
                logger.debug("Duplicate Q&A detected – skipping DB insert: %s", question)
                return True

            return True
    except Exception as e:
        logger.error(f"Error storing Q&A: {str(e)}")
        db.session.rollback()
        return False

# ---------------------------------------------------------------------------
# Text normalisation helpers – collapse redundant whitespace, lowercase, and
# expand a handful of common contractions so *"what's"* matches *"what is"*.
# ---------------------------------------------------------------------------

_CONTRACTIONS = {
    "what's": "what is",
    "who's": "who is",
    "where's": "where is",
    "when's": "when is",
    "why's": "why is",
    "how's": "how is",
    "it's": "it is",
    "that's": "that is",
    "there's": "there is",
    "can't": "cannot",
    "won't": "will not",
    "n't": " not",  # generic negation (don't -> do not)
}


def _normalize(text: str) -> str:
    """Return a simplified representation of *text* for robust matching."""
    if not text:
        return ""
    text_lc = text.lower()
    for contr, full in _CONTRACTIONS.items():
        text_lc = text_lc.replace(contr, full)
    # Remove punctuation – keep intra-word apostrophes already expanded above
    text_lc = re.sub(r"[^a-z0-9\s]", " ", text_lc)
    # Collapse consecutive whitespace
    return re.sub(r"\s+", " ", text_lc).strip()

def find_semantic_qa(question, threshold: float = 0.85, fuzzy_threshold: int = 90):
    """Lightweight lookup for *question* based **only** on fuzzy token matching.

    The previous implementation relied on dense embeddings which proved too
    permissive and often returned loosely-related answers.  Per recent feedback
    semantic search has been **disabled** to prioritise precision.  We now use
    a simple token-set ratio (RapidFuzz) so only near-identical phrasings are
    considered a match.

    Args:
        question:  The incoming user query.
        threshold: *Unused* – kept for backward-compatibility.
        fuzzy_threshold: Minimum RapidFuzz score (0-100) to treat two
            questions as equivalent.

    Returns:
        The stored *answer* if a close match is found, otherwise *None*.
    """

    # ----------------------------------------------------------------------------------
    # NOTE: Embedding-based comparisons have been removed.  The variables *threshold*
    # and *use_embeddings* below are kept to avoid NameErrors elsewhere but are no
    # longer utilised.
    # ----------------------------------------------------------------------------------

    use_embeddings = False  # Explicitly disabled
    # Make sure the table exists so the SELECT below doesn't fail on a fresh DB
    ensure_chat_qa_table()

    embedder = get_embedder()
    # Retain the old flag for completeness but it is forced to *False* above.

    try:
        with current_app.app_context():
            rows = db.session.execute(text('SELECT id, question, answer, embedding FROM chat_qa')).fetchall()

        if not rows:
            return None

        # ------------------------------------------------------------------
        # STRICT MATCH ONLY – we now return an answer **only** when the
        # *normalised* question matches exactly (case-insensitive, punctuation
        # & whitespace ignored). This prevents loosely related answers from
        # being served.
        # ------------------------------------------------------------------
        norm_q = _normalize(question)

        for row in rows:
            try:
                q_text = row.question
                a_text = row.answer
            except AttributeError:
                q_text = row['question']
                a_text = row['answer']

            if _normalize(q_text) == norm_q:
                return a_text

        # No exact match found
        return None

    except Exception as e:
        logger.error(f"Error finding semantic QA: {e}")
        return None

def answer_query(question, context="", user="anonymous", image_path=None, image_caption=None):
    """Generate an answer for a question"""
    # Check cache first
    cache_key = generate_cache_key(question, context)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        return cached_response

    try:
        # ------------------------------------------------------------------
        # 🧮  Quick deterministic arithmetic path ---------------------------
        # ------------------------------------------------------------------
        arith_ans = _evaluate_arithmetic(question)
        if arith_ans is not None:
            # Respect existing caching/persistence pipeline so future repeats
            # are answered instantly without re-evaluating the expression.
            set_cached_response(cache_key, arith_ans)
            store_qa(user, question, arith_ans, image_path, image_caption)
            return arith_ans

        # Get model instance – this now returns a *CloudAIModel* when the
        # application is running in online mode, otherwise it transparently
        # falls back to a local GPT4All model and finally to the minimal
        # *FallbackModel*.  This layered strategy ensures we always attempt
        # the remote API when the question is not found in the chat-QA cache.

        model = get_model()
        if model is None:
            return "I apologize, but the AI model is not properly initialized. Please try again later."

        # Try semantic search if embedder is available
        similar_answer = find_semantic_qa(question)
        if similar_answer:
            store_qa(user, question, similar_answer, image_path, image_caption)
            return similar_answer

        # FAST-PATH: when running with the lightweight FallbackModel, skip
        # expensive knowledge-base retrieval and prompt construction. The
        # rule-based engine responds instantly so we can return its answer
        # immediately for better perceived performance in offline mode.
        if isinstance(model, FallbackModel):
            # Try to serve answer directly from Knowledge-Base context so the
            # offline assistant can still be helpful for uploaded documents.
            kb_ctx = _get_kb_context(question)
            if kb_ctx:
                # Heuristic: return the first two sentences of the most
                # relevant snippet so technicians get a concise but precise
                # answer without requiring the heavyweight LLM.
                import re
                sentences = re.split(r"(?<=[.!?])\s+", kb_ctx.strip())
                answer = " ".join(sentences[:2]).strip()
                if not answer:
                    answer = kb_ctx.strip()[:350] + "…"
            else:
                # Fall back to rule-based engine when no context was found
                answer = model.generate(question)

            set_cached_response(cache_key, answer)
            store_qa(user, question, answer, image_path, image_caption)
            return answer

        # --------------------------------------------------------------
        # Compose prompt with *dynamic* knowledge-base context
        # --------------------------------------------------------------

        kb_context = _get_kb_context(question)

        prompt = (
            "You are a helpful AI assistant. Provide clear, concise, and accurate responses.\n"
            "Guidelines:\n"
            "1. Be direct and to the point\n"
            "2. If unsure, acknowledge uncertainty\n"
            "3. Use simple, clear language\n"
            "4. Focus on being helpful and practical\n"
        )

        combined_context = "\n".join([c for c in (context, kb_context) if c])
        if combined_context:
            prompt += f"\nContext:\n{combined_context[:1500]}\n"
        
        prompt += f"\nQuestion: {question}\nAnswer:"

        # Generate response
        response = model.generate(
            prompt,
            max_tokens=Config.MAX_TOKENS,
            temp=Config.TEMPERATURE,
            streaming=False
        )
        
        # Clean up response
        answer = response.strip()
        if answer.startswith("Answer:"):
            answer = answer[7:].strip()
        
        # Validate response
        if not answer or len(answer) < 8:
            answer = "I apologize, but I couldn't generate a meaningful response. Could you please rephrase your question?"
        elif answer.lower() in ["i don't know", "i do not know", "not sure"]:
            answer = "I don't have enough information to provide a confident answer. Could you provide more context or clarify your question?"
        elif "i need more information" in answer.lower():
            answer = "To better assist you, could you provide more details about what you're looking for?"
        
        # Cache and store
        set_cached_response(cache_key, answer)
        store_qa(user, question, answer, image_path, image_caption)
        
        return answer
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I encountered an error while processing your question. Please try again or rephrase your question."

def summarize_text(text_block, max_tokens=200):
    if not text_block:
        return ""
    try:
        if model is None:
            return "Error: AI model not initialized"
        
        prompt = f"Summarize the following text in {max_tokens} tokens or less:\n\n{text_block}\n\nSummary:"
        summary = model.generate(prompt, max_tokens=max_tokens, temp=0.7)
        return summary.strip()
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return f"Error summarizing text: {str(e)}"

# ---------------------------------------------------------------------------
# Knowledge-Base retrieval helpers
# ---------------------------------------------------------------------------

def _get_kb_context(question: str, top_n: int = 3, max_chars: int = 1500) -> str:
    """Return a condensed text block from the Knowledge Base relevant to *question*.

    The function prefers dense-embedding similarity when a SentenceTransformer
    instance is available; it gracefully falls back to fuzzy-token matching so
    we always return something meaningful even in offline mode.

    Parameters
    ----------
    question : str
        The incoming user query.
    top_n : int, optional
        Maximum number of distinct articles to include.  Defaults to *3*.
    max_chars : int, optional
        Rough upper-bound for the cumulative length of the returned context.
        Text is stripped down to the first *max_chars* characters per article
        to avoid excessively long prompts.
    """

    try:
        # --- Retrieve candidate approved, public articles (limit to 200 for speed) ---
        articles = (
            KBArticle.query
            .filter(KBArticle.status == 'approved', KBArticle.is_public.is_(True))
            .order_by(KBArticle.created_at.desc())
            .limit(200)
            .all()
        )

        if not articles:
            return ""

        embedder = get_embedder()

        scored = []  # type: list[tuple[float, str]]  # (score, snippet)

        if embedder and not isinstance(embedder, FallbackEmbedder):
            # --- Embedding cosine similarity ---
            try:
                q_emb = embedder.encode([question])[0]
            except Exception as enc_err:
                logger.warning("Embedding generation for KB search failed: %s", enc_err)
                embedder = None  # Fallback to fuzzy below

        # ------------------------------------------------------------------
        # 1) Embedding-based scoring when possible
        # ------------------------------------------------------------------
        if embedder and not isinstance(embedder, FallbackEmbedder):
            # Batch-encode candidate snippets (use title + description + intro)
            snippets = []
            meta = []
            for art in articles:
                snippet_text = (art.title or "") + "\n" + (art.description or "") + "\n" + (art.content[:512] if art.content else "")
                snippets.append(snippet_text)
                meta.append(snippet_text)

            try:
                art_embs = embedder.encode(snippets)
                sims = cosine_similarity([q_emb], art_embs)[0]
                scored = list(zip(sims, meta))
            except Exception as sim_err:
                logger.warning("Cosine similarity failed: %s", sim_err)

        # ------------------------------------------------------------------
        # 2) Token-based fuzzy matching fallback
        # ------------------------------------------------------------------
        if not scored:
            q_norm = _normalize(question)
            for art in articles:
                text_block = f"{art.title} {art.description}".strip()
                score = fuzz.token_set_ratio(q_norm, _normalize(text_block))
                snippet_text = (art.content[:512] if art.content else text_block)
                scored.append((score / 100.0, snippet_text))  # normalise to 0-1

        # Sort descending, keep top_n
        scored.sort(key=lambda x: x[0], reverse=True)
        top_snippets = [snip[:max_chars] for _, snip in scored[:top_n]]

        return "\n---\n".join(top_snippets)
    except Exception as exc:
        logger.warning("KB context retrieval failed: %s", exc)
        return ""

# ---------------------------------------------------------------------------
# Generic / boiler-plate answers we DO NOT want to store.  These phrases often
# appear when the Cloudflare worker cannot answer or when the greeting handler
# responds.  Each entry is **lower-case** so comparisons can be done with
# ``str.lower()`` for speed.
# ---------------------------------------------------------------------------
_GENERIC_ANSWER_PATTERNS = [
    r"^spark\s+is\s+pds\s+health'?s",           # corporate boiler-plate
    r"^hello[.!\s]*$",                          # plain hello
    r"^hi\b",                                   # hi/hey only
    r"^i\s+(?:am|'m)\s+sorry",                 # generic apology templates
    r"^how\s+can\s+i\s+assist",                # canned assistant prompt
    r"^i\s+apologize",                           # apology variants
]

# Pre-compile regexes once
_GENERIC_ANSWER_REGEX = [re.compile(p, re.IGNORECASE) for p in _GENERIC_ANSWER_PATTERNS]


def _is_generic_answer(ans: str) -> bool:
    """Return *True* when *ans* looks like a generic boiler-plate response.

    We treat answers shorter than ~12 characters as non-informative as well
    (e.g., "Hello!").
    """
    if not ans or len(ans.strip()) < 12:
        return True
    low = ans.strip().lower()
    return any(r.match(low) for r in _GENERIC_ANSWER_REGEX) 