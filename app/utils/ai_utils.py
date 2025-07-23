import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from gpt4all import GPT4All
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import re
from collections import Counter
from app.config import Config

logger = logging.getLogger(__name__)

# Global model instances
_language_model: Optional[GPT4All] = None
_embedder: Optional[SentenceTransformer] = None
_image_processor: Optional[BlipProcessor] = None
_image_model: Optional[BlipForConditionalGeneration] = None

def initialize_ai_models() -> Dict[str, bool]:
    """
    Initialize AI models with proper error handling.
    Returns a dictionary indicating which models were successfully initialized.
    """
    results = {
        'language_model': False,
        'embedder': False,
        'image_models': False
    }
    
    try:
        # Initialize language model
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'orca-mini-3b-gguf.gguf')
        if os.path.exists(model_path):
            global _language_model
            _language_model = GPT4All(model_path)
            results['language_model'] = True
            logger.info("Language model initialized successfully")
        else:
            logger.warning(f"Language model file not found at {model_path}")
    except Exception as e:
        logger.error(f"Error initializing language model: {str(e)}")

    try:
        # Initialize sentence transformer
        global _embedder
        _embedder = SentenceTransformer('all-MiniLM-L6-v2')
        results['embedder'] = True
        logger.info("Sentence transformer initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing sentence transformer: {str(e)}")

    try:
        # Initialize image models
        global _image_processor, _image_model
        _image_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _image_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        results['image_models'] = True
        logger.info("Image models initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing image models: {str(e)}")

    return results

def get_language_model() -> Optional[GPT4All]:
    """Return a language model instance shared across the application.

    This helper now delegates to :pyfunc:`app.utils.models.get_model` so that the
    entire codebase follows a **single** code-path for model discovery,
    download and caching.  By doing so we automatically pick up whichever GGUF
    file is present under *data/models/* (e.g. *orca-mini-3b.gguf* or
    *orca-mini-3b.Q4_K_M.gguf*) without hard-coding the file name here.
    The central helper already implements an in-memory singleton, therefore
    repeated calls are effectively free.
    """
    try:
        # Import locally to avoid circular dependency on module load
        from app.utils.models import get_model

        model_instance = get_model()

        # ------------------------------------------------------------------
        # Prefer a **local GPT4All** instance when available so that
        # summarisation stays fully on-prem without invoking the CloudAI
        # backend.  This is especially important for large file uploads where
        # latency and privacy are a concern.
        # ------------------------------------------------------------------
        from app.utils.models import CloudAIModel  # Imported here to avoid cycles

        if isinstance(model_instance, CloudAIModel):
            # Detect any *.gguf/*.bin model under the configured directory
            from pathlib import Path
            candidates = list(Path(Config.MODELS_DIR).glob("**/*.gguf")) + list(Path(Config.MODELS_DIR).glob("**/*.bin"))
            if candidates:
                try:
                    from gpt4all import GPT4All
                    # Load the first candidate; administrators can control the
                    # exact file via Config.MODEL_NAME if required.
                    local_file = candidates[0]
                    logger.info(f"Initialising local GPT4All model from {local_file} for summarisation")
                    try:
                        # Always specify model_type="llama" for .gguf/.bin files to avoid auto-detect issues
                        model_instance = GPT4All(model_name=local_file.name, model_path=str(local_file.parent), model_type="llama")
                    except Exception as local_err:
                        logger.warning("Failed to load local GPT4All model (%s). Continuing with CloudAIModel.", local_err)
                except Exception as local_err:
                    logger.warning("Failed to load local GPT4All model (%s). Continuing with CloudAIModel.", local_err)

        # Cache locally so other functions inside *ai_utils* can reference the
        # global variable without additional imports – useful for type checks
        # like ``isinstance(_language_model, FallbackModel)`` that appear in
        # legacy code paths.
        global _language_model  # noqa: PLW0603 (intentional module-level cache)
        _language_model = model_instance

        return model_instance
    except Exception as e:
        logger.error(f"Failed to obtain language model from central registry: {e}")

        # Graceful degradation – ensure callers still receive a usable object
        from app.utils.models import FallbackModel
        fallback = FallbackModel()
        _language_model = fallback
        return fallback

def get_embedder() -> Optional[SentenceTransformer]:
    """Get the initialized sentence transformer instance"""
    return _embedder

def get_image_models() -> tuple[Optional[BlipProcessor], Optional[BlipForConditionalGeneration]]:
    """Get the initialized image model instances"""
    return _image_processor, _image_model

def get_similar_articles(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Find similar articles using semantic search"""
    if not _embedder:
        logger.error("Embedder not initialized")
        return []
    
    try:
        # Get query embedding
        query_embedding = _embedder.encode(query)
        
        # TODO: Implement article similarity search
        # This is a placeholder - implement actual article search logic
        return []
    except Exception as e:
        logger.error(f"Error finding similar articles: {str(e)}")
        return []

def generate_summary(text: str, max_sentences: int = 3) -> str:
    """Return a *plain-language* summary of *text* limited to *max_sentences* sentences.

    When the primary language model is available we ask it directly to generate
    an accessible explanation ("dumb it down") so that non-technical readers can
    quickly grasp the main ideas.  In fallback/offline scenarios we build a quick
    heuristic summary by returning the first *max_sentences* sentences of the
    document.  The caller can choose how detailed the explanation should be via
    the *max_sentences* argument (defaults to a concise three-sentence overview).
    """
    from app.utils.models import FallbackModel

    # ------------------------------------------------------------------
    # 1) If a *real* LLM is available, use it to craft a concise summary.
    # ------------------------------------------------------------------
    model = get_language_model()

    if model and not isinstance(model, FallbackModel):
        try:
            # Feed a larger context window (up to ~10k characters) so the
            # explanation covers the *entire* document whenever possible.
            MAX_INPUT_CHARS = 10000

            def _query_llm(style_hint: str, sentences: int) -> str:
                """Internal helper that sends *style_hint* to the LLM and
                returns the trimmed single-line response."""
                prompt_llm = (
                    f"Explain the following content in VERY simple terms, {style_hint}. "
                    f"Provide between 2 and {sentences} short sentences and avoid jargon.\n\nTEXT:\n" +
                    text[:MAX_INPUT_CHARS] +
                    "\n\nSIMPLE SUMMARY:"
                )
                max_tokens = sentences * 55  # generous budget per sentence
                raw = model.generate(prompt_llm, max_tokens=max_tokens)
                return ' '.join(raw.strip().split())

            # 1️⃣  First attempt – neutral style
            summary = _query_llm("as if you were speaking to someone with no technical knowledge", max_sentences)

            # ------------------------------------------------------------------
            # Validate – ensure we actually received *multiple* sentences and a
            # reasonable character length (avoid cases like "Hire me.")
            # ------------------------------------------------------------------
            def _is_too_short(s: str) -> bool:
                # Fewer than ~8 words or one sentence → likely useless.
                if len(s.split()) < 8:
                    return True
                # Count sentence terminators (.!?); require at least 2.
                if sum(s.count(c) for c in '.!?') < 2:
                    return True
                return False

            if _is_too_short(summary):
                # 2️⃣  Retry with explicit *three* sentence requirement
                summary_retry = _query_llm("make it very clear and beginner-friendly", 3)
                if not _is_too_short(summary_retry):
                    summary = summary_retry

            if not _is_too_short(summary):
                return summary
            # If still short → continue to cloud or heuristic fallbacks below
            logger.debug("LLM summary too short; switching to fallback pipeline")
        except Exception as gen_err:
            logger.warning("LLM summary generation failed – falling back. %s", gen_err)

    # ------------------------------------------------------------------
    # 2) Cloud-based summarisation when local LLM is unavailable. We reuse
    #    the Cloudflare worker already leveraged elsewhere in the codebase
    #    so we do not introduce new infrastructure requirements.
    # ------------------------------------------------------------------
    cf_worker_url = (
        os.getenv('CF_WORKER_URL') or
        os.getenv('CLOUD_AI_ENDPOINT') or
        getattr(Config, 'CLOUD_AI_ENDPOINT', None) or
        'https://spark.oscarsolis3301.workers.dev/'
    )

    prompt_remote = (
        "Explain the following content in VERY simple terms, as if "
        "you were speaking to someone with NO technical knowledge. "
        f"Use at most {max_sentences} short sentences and avoid jargon.\n\nTEXT:\n" + text[:10000] +
        "\n\nSIMPLE SUMMARY:"
    )

    try:
        import requests
        resp = requests.post(
            cf_worker_url.rstrip('/') + '/jarvis',
            json={'question': prompt_remote},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            remote_answer = data.get('answer') or data.get('response')
            if remote_answer:
                # Compact whitespace
                return ' '.join(remote_answer.strip().split())
    except Exception as remote_err:
        # Do not log at ERROR to avoid noise when offline; DEBUG is enough.
        logger.debug("Remote summarisation failed: %s", remote_err)

    # ------------------------------------------------------------------
    # 3) Extractive heuristic fallback – choose the *most informative*
    #    sentences by simple word-frequency scoring so we avoid returning the
    #    very first lines of the document (which are often boilerplate).
    # ------------------------------------------------------------------
    import re
    from collections import Counter

    # Basic sentence splitting (handles both whitespace and newlines)
    raw_sentences = re.split(r'(?<=[.!?])[\s\n]+', text.strip())

    # ------------------------------------------------------------------
    # Filter out very short/boilerplate lines (titles, menu items, etc.).
    # Heuristics: at least 6 words AND at least one lowercase letter to avoid
    # headers in ALL CAPS, exclude lines that are mostly digits/punctuation.
    # ------------------------------------------------------------------
    def _is_informative(s: str) -> bool:
        words = s.split()
        if len(words) < 6:
            return False
        if sum(1 for c in s if c.islower()) < 3:  # virtually no lowercase => likely header
            return False
        # Exclude if > 60 % characters are non-letters (tables, menu structure)
        non_alpha_ratio = sum(1 for c in s if not c.isalpha()) / max(len(s), 1)
        if non_alpha_ratio > 0.6:
            return False
        return True

    sentences = [s.strip() for s in raw_sentences if _is_informative(s.strip())]

    if not sentences:
        sentences = raw_sentences  # fallback to unfiltered if everything was removed

    if len(sentences) <= max_sentences:
        return ' '.join(sentences)

    # Tokenise & build frequency table (lower-case alphanumerics only)
    WORD_RE = re.compile(r"[A-Za-z][A-Za-z']+")
    STOPWORDS = {
        'the','and','for','are','with','that','this','from','have','has','was','were',
        'will','shall','must','should','can','could','would','may','might','to','of',
        'in','on','at','by','an','a','be','is','it','as','or','if','into','using',
        'your','our','their','its','not','but','about','after','before','below','above'
    }

    word_freq: Counter[str] = Counter()
    sent_tokens: list[list[str]] = []
    for sent in sentences:
        tokens = [w.lower() for w in WORD_RE.findall(sent) if w.lower() not in STOPWORDS]
        sent_tokens.append(tokens)
        word_freq.update(tokens)

    if not word_freq:
        # Fallback to first sentences if tokenisation failed
        return ' '.join(sentences[:max_sentences])

    # Normalise frequencies
    max_count = max(word_freq.values())
    for w in word_freq:
        word_freq[w] /= max_count

    # Score each sentence
    sent_scores = [sum(word_freq.get(tok, 0) for tok in toks) for toks in sent_tokens]

    # Pick top-N sentences, preserving original order
    ranked_idx = sorted(range(len(sentences)), key=lambda i: sent_scores[i], reverse=True)
    selected_idx = sorted(ranked_idx[:max_sentences])
    summary = ' '.join(sentences[i] for i in selected_idx)

    # Compress if excessively long
    MAX_CHARS = max_sentences * 180  # give room for 2-3 full sentences
    if len(summary) > MAX_CHARS:
        cutoff = summary.rfind(' ', 0, MAX_CHARS)
        summary = summary[:cutoff if cutoff != -1 else MAX_CHARS].rstrip() + ' …'

    return summary

def generate_questions(text: str, max_questions: int = 20) -> List[str]:
    """Generate a list of common questions that someone might ask based on *text*.

    The function relies on the primary language model initialised for the
    application.  If that model is unavailable we fall back to a simple
    heuristic that extracts the most frequent noun phrases and formats them
    into generic *"What is …?"* questions so that the calling code always
    receives at least a few suggestions instead of an empty list.
    """
    if not text:
        return []

    model = get_language_model()

    # If we are running in offline/fallback mode, skip the prompt-based
    # approach entirely and fall back to the heuristic below – otherwise we
    # risk receiving the generic "minimal offline assistant" response.
    from app.utils.models import FallbackModel
    if not isinstance(model, FallbackModel):
        try:
            # ------------------------------------------------------------------
            # Ask the model directly – this yields higher-quality, contextual
            # questions when the full LLM is available.
            # ------------------------------------------------------------------
            prompt = (
                "You are a helpful assistant that creates FAQ style questions. "
                f"Based on the following text, list up to {max_questions} common "
                "questions a user might ask. Return each question on its own line "
                "without numbering.\n\nTEXT:\n" + text[:4000] +  # Truncate to avoid overly long prompts
                "\n\nQUESTIONS:\n"
            )
            raw = model.generate(prompt, max_tokens=max_questions * 25)
            # Split by newlines & cleanup
            questions = [q.strip("- •\t ") for q in raw.splitlines() if q.strip()]
            # Deduplicate while preserving order
            seen = set()
            uniq = []
            for q in questions:
                if q not in seen:
                    uniq.append(q)
                    seen.add(q)
            # If we managed to get *relevant* looking questions, return them
            if uniq and not any("minimal offline" in q.lower() for q in uniq):
                return uniq[:max_questions]
        except Exception as lerr:
            logger.warning("Question generation via LLM failed: %s", lerr)

    # ----------------------------------------------------------------------
    # Improved heuristic fallback – extract key phrases (1–3 words) and
    # craft more informative questions.
    # ----------------------------------------------------------------------
    STOPWORDS = {
        'the','and','for','are','with','that','this','from','have','has','was','were',
        'will','shall','must','should','can','could','would','may','might','to','of',
        'in','on','at','by','an','a','be','is','it','as','or','if','into','using',
        'your','our','their','its','not','but','about','after','before','below','above'
    }

    # Split into sentences
    sentences = re.split(r'[.!?]\s+', text)

    # Build list of candidate phrases (1–3 words) excluding stopwords
    phrase_counter = Counter()
    for sent in sentences:
        tokens = re.findall(r"[A-Za-z']{3,}", sent.lower())
        cleaned = [t for t in tokens if t not in STOPWORDS]
        # Generate n-grams
        for n in (3,2,1):
            for i in range(len(cleaned)-n+1):
                gram = ' '.join(cleaned[i:i+n])
                if len(gram.split()) != n:
                    continue
                phrase_counter[gram] += 1

    # Pick top unique phrases (longer grams preferred)
    ranked_phrases = [p for p,_ in phrase_counter.most_common(50) if len(p.split()[0])>2]
    unique_phrases = []
    for ph in ranked_phrases:
        if not any(ph in existing for existing in unique_phrases):
            unique_phrases.append(ph)
        if len(unique_phrases) >= max_questions*2:
            break

    # Craft questions – prefer How/Why/What templates
    questions = []
    for ph in unique_phrases:
        words = ph.split()
        if not words:
            continue
        first = words[0]
        if first in { 'how','why','what','when','where' }:
            q = ph.capitalize() + '?'
        else:
            # Heuristic: verbs list
            VERBS = {'install','configure','enroll','set','access','use','open','update','connect','create'}
            if first in VERBS:
                q = f"How do I {ph}?"
            else:
                q = f"What is {ph}?"
        questions.append(q.capitalize())
        if len(questions) == max_questions:
            break

    return questions

def process_document(file_path: str) -> Dict[str, Any]:
    """Process a document and extract relevant information"""
    try:
        from .document import extract_text, get_file_metadata
        
        # Extract text and metadata
        text = extract_text(file_path)
        metadata = get_file_metadata(file_path)
        
        # Generate summary & potential questions (use summary for relevancy)
        # Produce a concise plain-language summary (≈3 sentences) so users get
        # an immediate, easy-to-digest explanation of the document.
        summary = generate_summary(text, max_sentences=3) if text else None
        base_for_q = summary if summary else text
        questions = generate_questions(base_for_q) if base_for_q else []
        
        return {
            'text': text,
            'metadata': metadata,
            'summary': summary,
            'questions': questions,
        }
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return {
            'text': None,
            'metadata': None,
            'summary': None,
            'questions': [],
            'error': str(e)
        } 