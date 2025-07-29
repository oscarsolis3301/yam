import queue
import base64
import numpy as np
from app.utils.logger import setup_logging
from app.utils.helpers import asr_model
from app.extensions import socketio

logger = setup_logging()

# Global transcription queue
transcribe_queue = queue.Queue()
recent_snippets = []
AGENT_NS = '/agent'

def transcriber():
    """Background thread for audio transcription"""
    if asr_model is None:
        logger.warning("ASR model unavailable, transcription disabled.")
        return

    SAMPLE_RATE = 16000
    BYTES_PER_SAMPLE = 2
    CHUNK_SEC = 2   # every 2 seconds
    buffer = b''

    logger.info("Transcription thread started")

    while True:
        try:
            # Get chunk from queue
            chunk = transcribe_queue.get()
            buffer += chunk

            # Process when we have enough audio
            if len(buffer) >= SAMPLE_RATE * BYTES_PER_SAMPLE * CHUNK_SEC:
                try:
                    # Convert to float32 audio
                    audio_int16 = np.frombuffer(buffer, dtype=np.int16)
                    audio = audio_int16.astype(np.float32) / 32768.0

                    # Transcribe
                    result = asr_model.transcribe(audio)
                    text = result.get('text', '').strip()

                    if text:
                        # Emit transcript
                        socketio.emit('transcript', {'text': text}, namespace=AGENT_NS)

                        # Build context for AI suggestion
                        recent_snippets.append(text)
                        if len(recent_snippets) > 10:  # Keep last 10 snippets
                            recent_snippets.pop(0)
                        
                        prompt = "Agent said:\n" + "\n".join(recent_snippets)

                        # Get AI suggestion (if model available)
                        from app.utils.helpers import model
                        if model:
                            suggestion = model.generate(prompt, max_tokens=50)
                            socketio.emit('suggestion', {'text': suggestion}, namespace=AGENT_NS)

                except Exception as e:
                    logger.error(f"ASR processing error: {e}")

                finally:
                    # Reset buffer
                    buffer = b''
                    
        except Exception as e:
            logger.error(f"Transcription thread error: {e}")

def add_audio_chunk(chunk_b64):
    """Add audio chunk to transcription queue"""
    if chunk_b64:
        transcribe_queue.put(base64.b64decode(chunk_b64)) 