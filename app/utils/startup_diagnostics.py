"""
Startup Diagnostics Utility

This module provides functionality to diagnose and fix common Flask startup issues,
particularly in Electron desktop mode.
"""

import os
import sys
import logging
import psutil
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class StartupDiagnostics:
    """Diagnose and fix common Flask/Electron startup issues"""
    
    def __init__(self):
        self.issues_found: List[str] = []
        self.fixes_applied: List[str] = []
    
    def run_diagnostics(self) -> Dict[str, any]:
        """Run comprehensive startup diagnostics"""
        logger.info("Running startup diagnostics...")
        
        results = {
            'environment': self._check_environment(),
            'processes': self._check_processes(),
            'threads': self._check_threads(),
            'werkzeug': self._check_werkzeug_config(),
            'electron': self._check_electron_mode(),
            'issues_found': self.issues_found,
            'fixes_applied': self.fixes_applied
        }
        
        logger.info(f"Diagnostics complete. Found {len(self.issues_found)} issues, applied {len(self.fixes_applied)} fixes")
        return results
    
    def _check_environment(self) -> Dict[str, any]:
        """Check environment variables and configuration"""
        env_info = {
            'python_version': sys.version,
            'platform': sys.platform,
            'electron_mode': os.getenv('ELECTRON_MODE'),
            'flask_port': os.getenv('FLASK_PORT'),
            'werkzeug_run_main': os.getenv('WERKZEUG_RUN_MAIN'),
            'werkzeug_server_fd': os.getenv('WERKZEUG_SERVER_FD')
        }
        
        # Check for problematic environment variables
        if os.getenv('WERKZEUG_SERVER_FD') and os.getenv('WERKZEUG_SERVER_FD') != '':
            self.issues_found.append("WERKZEUG_SERVER_FD is set to problematic value")
            # Fix it
            os.environ['WERKZEUG_SERVER_FD'] = ''
            self.fixes_applied.append("Set WERKZEUG_SERVER_FD to empty string")
        
        return env_info
    
    def _check_processes(self) -> Dict[str, any]:
        """Check for conflicting processes"""
        processes = []
        flask_processes = []
        electron_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cmdline': ' '.join(proc_info['cmdline'] or [])
                    })
                    
                    # Check for Flask processes
                    if 'python' in proc_info['name'].lower() and proc_info['cmdline']:
                        cmdline = ' '.join(proc_info['cmdline'])
                        if 'YAM.py' in cmdline or 'flask' in cmdline.lower():
                            flask_processes.append(proc_info)
                    
                    # Check for Electron processes
                    if 'electron' in proc_info['name'].lower():
                        electron_processes.append(proc_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning(f"Error checking processes: {e}")
        
        # Check for multiple Flask instances
        if len(flask_processes) > 1:
            self.issues_found.append(f"Multiple Flask processes detected ({len(flask_processes)})")
        
        return {
            'total_processes': len(processes),
            'flask_processes': flask_processes,
            'electron_processes': electron_processes
        }
    
    def _check_threads(self) -> Dict[str, any]:
        """Check thread status and configuration"""
        threads = []
        daemon_threads = []
        
        try:
            for thread in threading.enumerate():
                thread_info = {
                    'name': thread.name,
                    'daemon': getattr(thread, 'daemon', False),
                    'alive': thread.is_alive(),
                    'ident': getattr(thread, 'ident', None)
                }
                threads.append(thread_info)
                
                if thread_info['daemon']:
                    daemon_threads.append(thread_info)
        except Exception as e:
            logger.warning(f"Error checking threads: {e}")
        
        return {
            'total_threads': len(threads),
            'daemon_threads': len(daemon_threads),
            'threads': threads
        }
    
    def _check_werkzeug_config(self) -> Dict[str, any]:
        """Check Werkzeug server configuration"""
        config = {
            'werkzeug_run_main': os.getenv('WERKZEUG_RUN_MAIN'),
            'werkzeug_server_fd': os.getenv('WERKZEUG_SERVER_FD'),
            'flask_debug': os.getenv('FLASK_DEBUG'),
            'flask_env': os.getenv('FLASK_ENV')
        }
        
        # Apply Werkzeug fixes for Electron mode
        if os.getenv('ELECTRON_MODE') == '1':
            fixes_needed = []
            
            if os.getenv('WERKZEUG_RUN_MAIN') != 'true':
                os.environ['WERKZEUG_RUN_MAIN'] = 'true'
                fixes_needed.append("Set WERKZEUG_RUN_MAIN=true")
            
            if os.getenv('WERKZEUG_SERVER_FD') is None or os.getenv('WERKZEUG_SERVER_FD') != '':
                os.environ['WERKZEUG_SERVER_FD'] = ''
                fixes_needed.append("Set WERKZEUG_SERVER_FD=''")
            
            if os.getenv('FLASK_DEBUG') != '0':
                os.environ['FLASK_DEBUG'] = '0'
                fixes_needed.append("Set FLASK_DEBUG=0")
            
            # Fix: Ensure FLASK_PORT is never empty
            flask_port = os.getenv('FLASK_PORT', '5000')
            if not flask_port or flask_port.strip() == '':
                os.environ['FLASK_PORT'] = '5000'
                fixes_needed.append("Set FLASK_PORT=5000 (was empty)")
            
            self.fixes_applied.extend(fixes_needed)
        
        return config
    
    def _check_electron_mode(self) -> Dict[str, any]:
        """Check Electron mode configuration"""
        is_electron = os.getenv('ELECTRON_MODE') == '1'
        
        electron_info = {
            'detected': is_electron,
            'flask_port': os.getenv('FLASK_PORT'),
            'pythonpath': os.getenv('PYTHONPATH'),
            'optimizations_applied': False
        }
        
        if is_electron:
            # Apply Electron-specific optimizations
            optimizations = []
            
            if not os.getenv('PYTHONDONTWRITEBYTECODE'):
                os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
                optimizations.append("Set PYTHONDONTWRITEBYTECODE=1")
            
            if not os.getenv('PYTHONUNBUFFERED'):
                os.environ['PYTHONUNBUFFERED'] = '1'
                optimizations.append("Set PYTHONUNBUFFERED=1")
            
            if not os.getenv('FLASK_SKIP_DOTENV'):
                os.environ['FLASK_SKIP_DOTENV'] = '1'
                optimizations.append("Set FLASK_SKIP_DOTENV=1")
            
            self.fixes_applied.extend(optimizations)
            electron_info['optimizations_applied'] = len(optimizations) > 0
        
        return electron_info
    
    def apply_emergency_fixes(self):
        """Apply emergency fixes for critical startup issues"""
        logger.info("Applying emergency startup fixes...")
        
        # Clear problematic environment variables
        problematic_vars = ['WERKZEUG_SERVER_FD']
        for var in problematic_vars:
            if var in os.environ:
                old_value = os.environ[var]
                os.environ[var] = ''
                logger.info(f"Cleared {var} (was: {old_value})")
        
        # Set required variables for Electron mode
        if os.getenv('ELECTRON_MODE') == '1':
            required_vars = {
                'WERKZEUG_RUN_MAIN': 'true',
                'FLASK_DEBUG': '0',
                'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONUNBUFFERED': '1'
            }
            
            # Ensure FLASK_PORT is set properly
            flask_port = os.getenv('FLASK_PORT', '5000')
            if not flask_port or flask_port.strip() == '':
                required_vars['FLASK_PORT'] = '5000'
            
            for var, value in required_vars.items():
                if os.getenv(var) != value:
                    os.environ[var] = value
                    logger.info(f"Set {var}={value}")


# Global instance
startup_diagnostics = StartupDiagnostics()

def run_startup_diagnostics() -> Dict[str, any]:
    """Run startup diagnostics and return results"""
    return startup_diagnostics.run_diagnostics()

def apply_startup_fixes():
    """Apply startup fixes"""
    startup_diagnostics.apply_emergency_fixes() 