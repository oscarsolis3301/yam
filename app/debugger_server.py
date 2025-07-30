"""
Debugger Server Module for YAM
Provides file monitoring and hot reloading functionality for development mode.
"""

import os
import hashlib
import time
import threading
from pathlib import Path
from typing import Dict, List, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class DebuggerFileMonitor:
    """
    File monitor for development mode that watches for file changes
    and triggers browser refresh and real-time updates.
    """
    
    def __init__(self, app_dir: Path, check_interval: float = 1.0):
        """
        Initialize the file monitor.
        
        Args:
            app_dir: Path to the application directory to monitor
            check_interval: How often to check for file changes (seconds)
        """
        self.app_dir = Path(app_dir)
        self.check_interval = check_interval
        self.file_hashes: Dict[str, str] = {}
        self.change_callbacks: List[Callable] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Define file types to monitor
        self.monitored_extensions = {
            '.html': 'template',
            '.css': 'static',
            '.js': 'static',
            '.py': 'python',
            '.json': 'config',
            '.xml': 'config',
            '.yaml': 'config',
            '.yml': 'config'
        }
        
        # Define directories to monitor
        self.monitored_dirs = [
            'templates',
            'static',
            'blueprints',
            'models',
            'utils'
        ]
        
        # Define directories to ignore
        self.ignored_dirs = [
            '__pycache__',
            '.git',
            'node_modules',
            'venv',
            'env',
            '.pytest_cache',
            '.vscode',
            '.idea'
        ]
        
        logger.info(f"DebuggerFileMonitor initialized for directory: {self.app_dir}")
    
    def add_change_callback(self, callback: Callable):
        """
        Add a callback function to be called when files change.
        
        Args:
            callback: Function to call with (file_path, file_type) arguments
        """
        self.change_callbacks.append(callback)
        logger.info(f"Added file change callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def _get_file_type(self, file_path: Path) -> str:
        """
        Determine the type of file based on its extension and location.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type string (template, static, python, config, etc.)
        """
        suffix = file_path.suffix.lower()
        
        # Check if it's a template file
        if 'templates' in str(file_path):
            return 'template'
        
        # Check if it's a static file
        if 'static' in str(file_path):
            return 'static'
        
        # Check extension-based types
        return self.monitored_extensions.get(suffix, 'other')
    
    def _should_monitor_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be monitored.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file should be monitored
        """
        # Skip directories
        if file_path.is_dir():
            return False
        
        # Skip ignored directories
        for ignored in self.ignored_dirs:
            if ignored in str(file_path):
                return False
        
        # Check if file is in monitored directories
        file_str = str(file_path)
        for monitored_dir in self.monitored_dirs:
            if monitored_dir in file_str:
                return True
        
        # Check if file has monitored extension
        suffix = file_path.suffix.lower()
        if suffix in self.monitored_extensions:
            return True
        
        return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash string
        """
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return ""
    
    def _scan_files(self) -> Dict[str, str]:
        """
        Scan all files in the monitored directories and calculate their hashes.
        
        Returns:
            Dictionary mapping file paths to their hashes
        """
        file_hashes = {}
        
        try:
            for root, dirs, files in os.walk(self.app_dir):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    if self._should_monitor_file(file_path):
                        file_hash = self._calculate_file_hash(file_path)
                        if file_hash:
                            file_hashes[str(file_path)] = file_hash
            
            logger.debug(f"Scanned {len(file_hashes)} files for monitoring")
            return file_hashes
            
        except Exception as e:
            logger.error(f"Error scanning files: {e}")
            return {}
    
    def _check_for_changes(self):
        """
        Check for file changes and trigger callbacks.
        """
        current_hashes = self._scan_files()
        
        # Check for new or modified files
        for file_path, current_hash in current_hashes.items():
            old_hash = self.file_hashes.get(file_path)
            
            if old_hash is None:
                # New file
                logger.info(f"New file detected: {file_path}")
                self._trigger_callbacks(file_path, 'new')
            elif old_hash != current_hash:
                # Modified file
                logger.info(f"File modified: {file_path}")
                file_type = self._get_file_type(Path(file_path))
                self._trigger_callbacks(file_path, file_type)
        
        # Check for deleted files
        for file_path in list(self.file_hashes.keys()):
            if file_path not in current_hashes:
                logger.info(f"File deleted: {file_path}")
                self._trigger_callbacks(file_path, 'deleted')
        
        # Update stored hashes
        self.file_hashes = current_hashes
    
    def _trigger_callbacks(self, file_path: str, file_type: str):
        """
        Trigger all registered callbacks for a file change.
        
        Args:
            file_path: Path to the changed file
            file_type: Type of the file change
        """
        for callback in self.change_callbacks:
            try:
                callback(file_path, file_type)
            except Exception as e:
                logger.error(f"Error in file change callback: {e}")
    
    def _monitor_loop(self):
        """
        Main monitoring loop that runs in a separate thread.
        """
        logger.info("File monitoring loop started")
        
        while not self.stop_event.is_set():
            try:
                self._check_for_changes()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
        
        logger.info("File monitoring loop stopped")
    
    def start_monitoring(self):
        """
        Start file monitoring in a background thread.
        """
        if self.monitoring:
            logger.warning("File monitoring is already running")
            return
        
        self.monitoring = True
        self.stop_event.clear()
        
        # Initial scan
        self.file_hashes = self._scan_files()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="DebuggerFileMonitor"
        )
        self.monitor_thread.start()
        
        logger.info("File monitoring started")
    
    def stop_monitoring(self):
        """
        Stop file monitoring.
        """
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("File monitoring stopped")
    
    def get_monitored_files(self) -> List[Dict]:
        """
        Get list of currently monitored files.
        
        Returns:
            List of dictionaries with file information
        """
        files = []
        for file_path, file_hash in self.file_hashes.items():
            files.append({
                'path': file_path,
                'hash': file_hash[:8],  # Short hash for display
                'type': self._get_file_type(Path(file_path))
            })
        return files
    
    def get_status(self) -> Dict:
        """
        Get current monitoring status.
        
        Returns:
            Dictionary with monitoring status information
        """
        return {
            'monitoring': self.monitoring,
            'file_count': len(self.file_hashes),
            'callback_count': len(self.change_callbacks),
            'check_interval': self.check_interval,
            'app_dir': str(self.app_dir)
        }


# Convenience function to create a file monitor
def create_file_monitor(app_dir: str, **kwargs) -> DebuggerFileMonitor:
    """
    Create a new file monitor instance.
    
    Args:
        app_dir: Path to the application directory
        **kwargs: Additional arguments to pass to DebuggerFileMonitor
        
    Returns:
        DebuggerFileMonitor instance
    """
    return DebuggerFileMonitor(Path(app_dir), **kwargs) 