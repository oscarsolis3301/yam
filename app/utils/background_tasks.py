import threading
import time
import queue
import psutil
from datetime import datetime
from app.utils.logger import setup_logging

logger = setup_logging()

# Global state for background tasks
_background_tasks_started = False
_background_threads = {}

def start_background_tasks(app, socketio):
    """Start all background tasks - call this once at startup"""
    global _background_tasks_started
    
    if _background_tasks_started:
        logger.warning("Background tasks already started, skipping...")
        return
    
    _background_tasks_started = True
    
    # Start system status emitter
    start_system_status_emitter(socketio)
    
    # Start transcription thread
    start_transcription_thread()
    
    logger.info("All background tasks started")

def start_system_status_emitter(socketio):
    """Start background task to emit system status updates"""
    def status_emitter():
        while True:
            try:
                cpu = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                # Only log if values exceed thresholds
                if cpu > 80 or memory > 80 or disk > 80:
                    logger.warning(f"High resource usage - CPU: {cpu}%, Memory: {memory}%, Disk: {disk}%")
                
                socketio.emit('system_status', {
                    'cpu': cpu,
                    'memory': memory,
                    'disk': disk,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                time.sleep(5)  # Emit every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in status emitter: {e}")
                time.sleep(5)
    
    thread = threading.Thread(target=status_emitter, daemon=True, name="SystemStatusEmitter")
    thread.start()
    _background_threads['status_emitter'] = thread
    logger.info("System status emitter started")

def start_transcription_thread():
    """Start the audio transcription thread"""
    # Import here to avoid circular imports
    from app.utils.transcription import transcriber
    
    thread = threading.Thread(target=transcriber, daemon=True, name="Transcriber")
    thread.start()
    _background_threads['transcriber'] = thread
    logger.info("Transcription thread started")

def check_resources():
    """Monitor system resources and return True if OK to proceed"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 95:
            logger.warning(f"High resource usage - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking resources: {e}")
        return True

def get_background_tasks_status():
    """Get status of all background tasks"""
    status = {}
    for name, thread in _background_threads.items():
        status[name] = {
            'alive': thread.is_alive(),
            'daemon': thread.daemon
        }
    return status 