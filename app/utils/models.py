import os
import logging
import queue
import numpy as np
from flask import current_app
from app.extensions import Config
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer
from contextlib import nullcontext
import requests  # Added for Cloud AI HTTP requests

logger = logging.getLogger('spark')

# Constants
API_URL = "http://localhost:5000/api"
AGENT_NS = '/agent'
MODEL_ID = "orca-mini-3b-gguf"  # Default model ID

# Global model instances
_model = None
_embedder = None
_processor = None
_caption_model = None
transcribe_queue = queue.Queue()
recent_snippets = []

class FallbackEmbedder:
    """A simple fallback embedder that uses basic text features"""
    def __init__(self):
        self.dim = 128  # Fixed dimension for embeddings
        
    def encode(self, texts):
        """Generate simple embeddings based on text features"""
        if isinstance(texts, str):
            texts = [texts]
            
        embeddings = []
        for text in texts:
            # Create a simple embedding based on character frequencies
            embedding = np.zeros(self.dim)
            for i, char in enumerate(text.lower()):
                if i < self.dim:
                    embedding[i] = ord(char) / 255.0
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            embeddings.append(embedding)
            
        return np.array(embeddings)

class FallbackModel:
    """A minimal rule-based fallback model that provides quick answers to very
    simple queries so the application remains usable even when the real LLM
    is unavailable.  It tries to recognise a handful of common intents such
    as greetings, basic arithmetic, date/time requests and generic tests.
    Any unrecognised input results in a short default message so that the UI
    never shows an error.
    """

    # --- Internal helpers -------------------------------------------------
    def _handle_math(self, text: str):
        """Evaluate very simple arithmetic expressions like '2+2' or
        'what is 10 * 5?'.  We only allow numbers and the operators +-*/()."""
        import re, math
        # extract expression portion
        m = re.search(r"([-+/*().\d ]+)", text)
        if not m:
            return None
        expr = m.group(1)
        # validate expression contains only allowed characters
        if not re.fullmatch(r"[\d+\-*/(). ]+", expr):
            return None
        try:
            # WARNING: using eval is normally unsafe – here we operate on a
            # heavily sanitised whitelist to keep it secure.
            result = eval(expr, {"__builtins__": {}}, {})
            return str(result)
        except Exception:
            return None

    def _respond(self, text: str) -> str:
        """Generate a deterministic response for *very* simple prompts."""
        import datetime, re
        txt = text.strip().lower()

        # If the prompt follows the pattern "... Question: <q>\nAnswer:"
        if "question:" in txt:
            # Split by last occurrence to handle few-shot prompts
            q_part = txt.rsplit("question:", 1)[-1]
            # Remove any trailing 'answer:' marker
            q_part = q_part.split("answer:", 1)[0]
            txt = q_part.strip()

        # Greetings / chitchat ------------------------------------------------
        if any(word in txt for word in ("hello", "hi", "hey")):
            return "Hello! How can I assist you today?"
        if "how are you" in txt:
            return "I'm functioning within offline mode but ready to help!"

        # Quick connectivity / test probes -----------------------------------
        if txt in ("test", "ping", "are you there?"):
            return "Test successful – your assistant is online.";

        # Date / time ---------------------------------------------------------
        if ("time" in txt and "?" in txt) or txt.startswith("time"):
            now = datetime.datetime.now().strftime("%H:%M:%S")
            return f"The current time is {now}."

        # Recognise requests for today's date or day of week
        if ("date" in txt or ("day" in txt and "today" in txt)):
            today_date = datetime.date.today()
            readable = today_date.strftime("%A, %B %d, %Y")
            return f"Today is {readable}."

        # Simple maths --------------------------------------------------------
        math_result = self._handle_math(txt)
        if math_result is not None:
            return f"The answer is {math_result}."

        # Fallback ------------------------------------------------------------
        return (
            "I'm a minimal offline assistant with limited knowledge. "
            "Please ask a simple factual or greeting question."
        )

    # --- Public API compatible with GPT4All ---------------------------------
    def generate(self, prompt: str, max_tokens: int = 100, temp: float = None,
                 temperature: float = 0.7, streaming: bool = False, **kwargs):
        """Mimic GPT4All's generate method signature while ignoring advanced
        parameters that are not relevant to the rule-based engine."""
        return self._respond(prompt)

    # Some callers use a chat-completion style API with a list of messages ----
    def chat_completion(self, messages, max_tokens: int = 100, temperature: float = 0.7, **kwargs):
        # Extract the last user message if possible
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict):
                prompt = last.get("content", "")
            else:
                prompt = str(last)
        else:
            prompt = str(messages)
        return self._respond(prompt)

    # GPT4All exposes a `chat_session` context manager.  We replicate the
    # interface by returning a `nullcontext` that simply yields *self*.
    def chat_session(self):  # noqa: N802 (match GPT4All camelCase)
        """Return a no-op context manager so callers can write
        `with model.chat_session(): ...` regardless of whether we're using the
        real GPT4All model or the lightweight fallback.
        """
        return nullcontext(self)

class CloudAIModel:
    """Thin wrapper that forwards prompts to a remote HTTP service (e.g. Cloudflare Workers AI).

    The remote service is expected to accept a JSON payload of the form
        { "inputs": [ { "prompt": "<user prompt>" } ] }
    and respond with a JSON list where the first element contains the key
    ``response`` holding the model's answer.  This matches the example
    Cloudflare Worker included by the repository owner.
    """

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip('/') + '/'  # Normalise
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Compatibility helpers so existing code can treat this like GPT4All
    # ------------------------------------------------------------------
    def chat_session(self):
        """Return a no-op context manager so callers can write
        ``with model.chat_session():`` regardless of backend type."""
        from contextlib import nullcontext
        return nullcontext(self)

    def _doh_fallback(self, url: str, json_payload: dict):
        host = requests.utils.urlparse(url).hostname or ""
        if not host:
            return None
        try:
            doh = self.session.get(
                "https://cloudflare-dns.com/dns-query",
                params={"name": host, "type": "A"},
                headers={"accept": "application/dns-json"},
                timeout=10,
            )
            ip = None
            for ans in doh.json().get("Answer", []):
                if ans.get("type") == 1:
                    ip = ans.get("data")
                    break
            if not ip:
                return None
            ip_url = url.replace(host, ip)
            resp_ip = self.session.post(ip_url, json=json_payload, timeout=45, verify=False, headers={"Host": host})
            resp_ip.raise_for_status()
            data_ip = resp_ip.json()
            if isinstance(data_ip, dict):
                return str(data_ip.get("answer") or data_ip.get("response") or data_ip)
            if isinstance(data_ip, list) and data_ip:
                return str(data_ip[0].get("response", ""))
        except Exception as _:
            return None

    def generate(self, prompt: str, max_tokens: int = None, **kwargs) -> str:
        """Send *prompt* to the remote endpoint and return the assistant's reply."""
        # Prefer the modern /jarvis endpoint that returns a concise JSON
        modern_url = self.endpoint.rstrip('/') + '/jarvis'
        modern_payload = {"question": prompt}
        legacy_payload = {"inputs": [{"prompt": prompt}]}
        timeout = Config.CLOUD_AI_TIMEOUT
        try:
            # 1️⃣  First attempt modern endpoint -----------------------------------
            resp = self.session.post(modern_url, json=modern_payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                # Expected { "answer": "..." } or { "response": "..." }
                return str(data.get("answer") or data.get("response") or data)
            # Fallback if worker returned the legacy list format by mistake
            if isinstance(data, list) and data:
                return str(data[0].get("response", ""))
            return str(data)
        except requests.exceptions.RequestException as modern_exc:
            # Try DoH fallback for modern endpoint once before switching.
            answer_via_doh = self._doh_fallback(modern_url, modern_payload)
            if answer_via_doh is not None:
                return answer_via_doh
            # Otherwise continue to legacy attempt below.

        # 2️⃣  Legacy root endpoint ---------------------------------------------
        try:
            resp = self.session.post(self.endpoint, json=legacy_payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return str(data[0].get("response", ""))
            if isinstance(data, dict):
                return str(data.get("response", data))
            return str(data)
        except requests.exceptions.RequestException as exc:
            # Handle DNS resolution errors by attempting DoH lookup
            host = requests.utils.urlparse(self.endpoint).hostname or ""
            if host:
                try:
                    doh = self.session.get(
                        "https://cloudflare-dns.com/dns-query",
                        params={"name": host, "type": "A"},
                        headers={"accept": "application/dns-json"},
                        timeout=10,
                    )
                    ip = None
                    for ans in doh.json().get("Answer", []):
                        if ans.get("type") == 1:
                            ip = ans.get("data")
                            break
                    if ip:
                        ip_url = self.endpoint.replace(host, ip)
                        resp2 = self.session.post(ip_url, json=legacy_payload, timeout=60, verify=False, headers={"Host": host})
                        resp2.raise_for_status()
                        data2 = resp2.json()
                        if isinstance(data2, list) and data2:
                            return str(data2[0].get("response", ""))
                        if isinstance(data2, dict):
                            return str(data2.get("response", data2))
                        return str(data2)
                except Exception as doh_exc:
                    logger.debug("DoH fallback failed: %s", doh_exc)
            logger.error(f"CloudAIModel request failed: {exc}")
            return (
                "I'm sorry, but I couldn't reach the cloud AI service right now. "
                "Please try again later."
            )

def get_model():
    """Get or initialize the language model.

    In OFFLINE_MODE we skip all network-dependent logic and immediately fall back to the
    lightweight placeholder model.  This guarantees that application start-up never
    blocks on a failed download attempt or tries to read an unavailable local model
    file.  When OFFLINE_MODE is disabled we still try to load a local file first and
    only then attempt to download the model.
    """

    if hasattr(get_model, 'model'):
        return get_model.model  # Already initialised--return cached instance

    # -------------------- STEP 0: Cloud-backend ------------------------------
    try:
        if Config.USE_CLOUD_AI:
            logger.info("USE_CLOUD_AI=True – Initialising CloudAIModel backend")
            get_model.model = CloudAIModel(Config.CLOUD_AI_ENDPOINT)
            return get_model.model
    except Exception as c_exc:
        logger.error(f"Failed to initialise CloudAIModel: {c_exc}")

    # ---------------------------------------------------------------------------
    # OFFLINE MODE – never attempt network downloads of large language models   
    # ---------------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # Helper: return first existing *.gguf or *.bin under MODELS_DIR --------
    # ----------------------------------------------------------------------
    def _find_local_file() -> Path | None:  # noqa: ANN001 (Py<3.10 fallback ok)
        search_dirs = [Path(Config.MODELS_DIR), Path(__file__).resolve().parent.parent / 'data' / 'models']
        for d in search_dirs:
            if not d.exists():
                continue
            for pattern in ("**/*.gguf", "**/*.bin"):
                found = list(d.glob(pattern))
                if not found:
                    continue
                # Prefer the *exact* file specified in MODEL_NAME if present
                for f in found:
                    if f.name == Path(Config.MODEL_PATH).name:
                        return f
                # Otherwise return first match
                return found[0]
        return None

    if Config.OFFLINE_MODE:
        local_path = Path(Config.MODEL_PATH)
        # If the configured path is missing, attempt to discover any local model file
        if not local_path.exists():
            alt = _find_local_file()
            if alt:
                local_path = alt
                logger.info("Discovered local model %s – will load instead of downloading", alt)

        if local_path.exists():
            try:
                logger.info("OFFLINE_MODE=True – Loading local model from %s", local_path)
                from gpt4all import GPT4All
                # Always specify model_type="llama" for .gguf/.bin files to avoid auto-detect issues
                get_model.model = GPT4All(
                    model_name=local_path.name,
                    model_path=str(local_path.parent),
                    model_type="llama",
                )
                return get_model.model
            except Exception as e:
                logger.warning("Local model load failed (%s). Using fallback.", e)

        # Either the file doesn't exist or failed to load → fallback instantly
        logger.info("OFFLINE_MODE=True and no usable local model found → Falling back to lightweight model")
        get_model.model = FallbackModel()
        return get_model.model

    # --- STEP 1: try to use a **local** model file (ONLINE mode) -------------
    try:
        local_path = Path(Config.MODEL_PATH)

        # If the configured path does not exist, look for any *.gguf/*.bin file
        # in the models directory so we reuse manually downloaded models.
        if not local_path.exists():
            alt = _find_local_file()
            if alt:
                logger.info("Found existing model %s – will use it instead of downloading", alt)
                local_path = alt

        if local_path.exists():
            logger.info(f"Loading language model from local path: {local_path}")
            try:
                from gpt4all import GPT4All
                # Always specify model_type="llama" for .gguf/.bin files to avoid auto-detect issues
                get_model.model = GPT4All(
                    model_name=local_path.name,
                    model_path=str(local_path.parent),
                    model_type="llama",
                )
                return get_model.model
            except Exception as e:
                logger.warning(f"Local model load failed ({e}). Will attempt alternative initialisation.")
        else:
            # Attempt manual download ------------------------------------------------------
            try:
                logger.info("Local model not found – downloading directly from HuggingFace…")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                import requests, shutil
                with requests.get(Config.MODEL_DOWNLOAD_URL, stream=True, timeout=300) as r:
                    r.raise_for_status()
                    with open(local_path, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
                logger.info("Model downloaded to %s (%.1f MB)", local_path, local_path.stat().st_size / (1024*1024))
                # Recursively call get_model to load the freshly downloaded file
                return get_model()
            except Exception as dl_exc:
                logger.error(f"Direct model download failed: {dl_exc}")
    except Exception as e:
        # Catch unexpected issues like incorrect file permissions, etc.
        logger.error(f"Error whilst attempting to load local model file: {e}")

    # --- STEP 2: if OFFLINE_MODE is set, *skip* any remote download attempts -------------
    if Config.OFFLINE_MODE:
        logger.info("OFFLINE_MODE=True and no usable local model found → Falling back to lightweight model")
        get_model.model = FallbackModel()
        return get_model.model

    # --- STEP 3: attempt to download the model (ONLINE mode only) -----------------------
    try:
        logger.info("Attempting to download language model from GPT4All hub…")
        from gpt4all import GPT4All
        # GPT4All hub recognises the file extension and may reject an explicit
        # model_type; therefore omit it here to let the client decide.
        get_model.model = GPT4All(model_name=Config.MODEL_NAME)
        # Optionally create the models directory so the file can be cached for future offline use
        Path(Config.MODELS_DIR).mkdir(parents=True, exist_ok=True)
        return get_model.model
    except Exception as e:
        logger.error(f"Failed to download language model: {e}")

    # --- STEP 4: last-resort fallback ---------------------------------------------------
    logger.info("All attempts to load a language model failed → Using fallback implementation")
    get_model.model = FallbackModel()
    return get_model.model

def get_embedder():
    """Return a `SentenceTransformer` instance if a local copy is available.

    The production environment no longer allows outbound HTTPS (or the model
    lives behind a new internal artefact store).  We therefore *only* look for
    a **fully-materialised** model directory on disk and never attempt a remote
    download.  If that directory is missing or corrupted we immediately fall
    back to the lightweight in-memory implementation so that application start-up
    always succeeds.
    """

    # Re-use the already-initialised singleton if present --------------------------------------------------
    if hasattr(get_embedder, "model"):
        return get_embedder.model

    local_path = Path(Config.EMBEDDER_PATH)

    # 🔹 1. Try to load the model from disk ---------------------------------------------------------------
    if local_path.exists():
        try:
            logger.info(f"Attempting to load local embedder from: {local_path}")
            # Use strictly local files; SentenceTransformer will not fetch from the hub because
            # we pass an explicit path instead of a model name.
            get_embedder.model = SentenceTransformer(str(local_path))
            logger.info("Local embedder initialised successfully [OK]")
            return get_embedder.model
        except Exception as e:
            logger.warning(f"Local embedder at '{local_path}' could not be loaded ({e}). Falling back.")

    # 🔹 2.  Fallback: minimal NumPy-based embedder -------------------------------------------------------
    logger.info("Falling back to internal lightweight embedder implementation")
    get_embedder.model = FallbackEmbedder()
    return get_embedder.model

def get_processor():
    """Get the image processor with fallback"""
    try:
        from transformers import AutoImageProcessor
        return AutoImageProcessor.from_pretrained(Config.IMAGE_MODEL)
    except Exception as e:
        logger.warning(f"Failed to load image processor: {e}")
        return None

def get_caption_model():
    """Get the image captioning model with fallback"""
    try:
        from transformers import BlipForConditionalGeneration
        return BlipForConditionalGeneration.from_pretrained(Config.IMAGE_MODEL)
    except Exception as e:
        logger.warning(f"Failed to load caption model: {e}")
        return None

def initialize_models():
    """Initialize all models"""
    try:
        # Validate configuration
        if not Config.validate():
            logger.error("Invalid configuration")
            return False
        
        # Initialize embedder
        embedder = get_embedder()
        if embedder is None:
            logger.error("Failed to initialize embedder")
            return False
        logger.info("Embedder initialized successfully")
        
        # Initialize language model
        model = get_model()
        if model is None:
            logger.error("Failed to initialize language model")
            return False
        logger.info("Language model initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing models: {str(e)}")
        return False 