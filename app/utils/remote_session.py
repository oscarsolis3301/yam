"""
Remote session utilities for browser-based remote access.

This module provides utilities for launching and managing remote sessions
including Dameware, RDP, and browser-based remote access solutions.
"""

import subprocess
import platform
import socket
import re
from typing import Dict, Optional, Tuple
from flask import current_app
import logging
from cryptography.fernet import Fernet
import base64
import os
from cryptography.fernet import InvalidToken

logger = logging.getLogger(__name__)

# Securely generate or load a key (should be stored securely in production)
try:
    FERNET_KEY = os.environ.get('FERNET_KEY')
    if not FERNET_KEY:
        FERNET_KEY = base64.urlsafe_b64encode(os.urandom(32))
        # In production, persist this key securely
    fernet = Fernet(FERNET_KEY)

    def encrypt_password(plain_password: str) -> bytes:
        return fernet.encrypt(plain_password.encode())

    def decrypt_password(encrypted_password: bytes) -> str:
        try:
            return fernet.decrypt(encrypted_password).decode()
        except InvalidToken:
            import logging
            logging.warning('Failed to decrypt Dameware password: InvalidToken. The password may be corrupted or encrypted with a different key.')
            return None
        except Exception as e:
            import logging
            logging.warning(f'Failed to decrypt Dameware password: {e}')
            return None
except ImportError:
    # Fallback if cryptography is not available
    logger.warning("cryptography module not available, password encryption disabled")
    
    def encrypt_password(plain_password: str) -> bytes:
        return plain_password.encode()
    
    def decrypt_password(encrypted_password: bytes) -> str:
        return encrypted_password.decode()


def check_dameware_availability() -> bool:
    """
    Check if Dameware Remote Support is available on the system.
    
    Returns:
        bool: True if Dameware appears to be available, False otherwise
    """
    try:
        # Check for Dameware executable in common installation paths
        dameware_paths = [
            r"C:\Program Files\SolarWinds\DameWare Mini Remote Control\DWRCC.exe",
            r"C:\Program Files (x86)\SolarWinds\DameWare Mini Remote Control\DWRCC.exe",
            r"C:\Program Files\SolarWinds\DameWare Remote Support\DWRCC.exe",
            r"C:\Program Files (x86)\SolarWinds\DameWare Remote Support\DWRCC.exe"
        ]
        
        for path in dameware_paths:
            try:
                result = subprocess.run(
                    [path, "/?"],  # Help command to test if executable exists
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 or "DameWare" in result.stdout:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        # Alternative: check registry for Dameware installation
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\SolarWinds\DameWare") as key:
                return True
        except (FileNotFoundError, OSError):
            pass
            
        return False
        
    except Exception as e:
        logger.warning(f"Error checking Dameware availability: {e}")
        return False


def launch_dameware_session(hostname: str, ip_address: Optional[str] = None) -> Dict[str, any]:
    """
    Launch a Dameware remote session to the specified device.
    
    Args:
        hostname: The target device hostname
        ip_address: Optional IP address (used if hostname resolution fails)
        
    Returns:
        Dict containing success status and any error messages
    """
    target = hostname or ip_address
    if not target:
        return {
            'success': False,
            'error': 'No valid hostname or IP address provided'
        }
    
    try:
        # Validate target format
        if not re.match(r'^[a-zA-Z0-9\-\.]+$', target):
            return {
                'success': False,
                'error': 'Invalid hostname or IP address format'
            }
        
        # Try to resolve hostname to IP if only hostname provided
        if not ip_address and hostname:
            try:
                ip_address = socket.gethostbyname(hostname)
            except socket.gaierror:
                ip_address = None
        
        # Try multiple Dameware launch methods
        launch_methods = [
            # Method 1: Direct executable call with correct parameters
            lambda: subprocess.Popen([
                r"C:\Program Files\SolarWinds\DameWare Mini Remote Control\DWRCC.exe",
                f"-h:{target}",
                "-c:full-control",
                "-m:1",
                "-v:1"
            ]),
            
            # Method 2: Alternative path with correct parameters
            lambda: subprocess.Popen([
                r"C:\Program Files (x86)\SolarWinds\DameWare Mini Remote Control\DWRCC.exe",
                f"-h:{target}",
                "-c:full-control",
                "-m:1",
                "-v:1"
            ]),
            
            # Method 3: 64-bit version
            lambda: subprocess.Popen([
                r"C:\Program Files\SolarWinds\Dameware Mini Remote Control x64\DWRCC.exe",
                f"-h:{target}",
                "-c:full-control",
                "-m:1",
                "-v:1"
            ]),
            
            # Method 4: URL scheme (fallback)
            lambda: subprocess.Popen([
                "start", f"dwrcc://full-control?machine={target}"
            ], shell=True)
        ]
        
        for i, launch_method in enumerate(launch_methods):
            try:
                process = launch_method()
                if process and process.poll() is None:  # Process started successfully
                    return {
                        'success': True,
                        'method': f'method_{i+1}',
                        'target': target,
                        'pid': process.pid
                    }
            except Exception as e:
                logger.debug(f"Dameware launch method {i+1} failed: {e}")
                continue
        
        return {
            'success': False,
            'error': 'Failed to launch Dameware session',
            'target': target
        }
        
    except Exception as e:
        logger.error(f"Error launching Dameware session: {e}")
        return {
            'success': False,
            'error': str(e),
            'target': target
        }


def launch_rdp_session(hostname: str, ip_address: Optional[str] = None) -> Dict[str, any]:
    """
    Launch an RDP session to the specified device.
    
    Args:
        hostname: The target device hostname
        ip_address: Optional IP address
        
    Returns:
        Dict containing success status and any error messages
    """
    target = hostname or ip_address
    if not target:
        return {
            'success': False,
            'error': 'No valid hostname or IP address provided'
        }
    
    try:
        if platform.system().lower() != "windows":
            return {
                'success': False,
                'error': 'RDP is only available on Windows systems'
            }
        
        # Launch Remote Desktop Connection
        process = subprocess.Popen([
            "mstsc", "/v:" + target
        ])
        
        return {
            'success': True,
            'method': 'mstsc',
            'target': target,
            'pid': process.pid
        }
        
    except Exception as e:
        logger.error(f"Error launching RDP session: {e}")
        return {
            'success': False,
            'error': str(e),
            'target': target
        }


def check_device_connectivity(hostname: str, ip_address: Optional[str] = None) -> Dict[str, any]:
    """
    Check if a device is reachable and what services are available.
    
    Args:
        hostname: The target device hostname
        ip_address: Optional IP address
        
    Returns:
        Dict containing connectivity status and available services
    """
    target = hostname or ip_address
    if not target:
        return {
            'success': False,
            'error': 'No valid hostname or IP address provided'
        }
    
    try:
        # Check basic connectivity
        ping_result = ping_device(target)
        
        # Check common remote access ports
        ports_to_check = {
            22: 'SSH',
            23: 'Telnet',
            3389: 'RDP',
            5900: 'VNC',
            5901: 'VNC-1',
            5902: 'VNC-2'
        }
        
        open_ports = []
        if ping_result['success']:
            for port, service in ports_to_check.items():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((target, port))
                    sock.close()
                    if result == 0:
                        open_ports.append({'port': port, 'service': service})
                except Exception:
                    continue
        
        return {
            'success': True,
            'target': target,
            'ping': ping_result,
            'open_ports': open_ports,
            'rdp_available': any(p['service'] == 'RDP' for p in open_ports),
            'vnc_available': any(p['service'].startswith('VNC') for p in open_ports)
        }
        
    except Exception as e:
        logger.error(f"Error checking device connectivity: {e}")
        return {
            'success': False,
            'error': str(e),
            'target': target
        }


def ping_device(hostname: str) -> Dict[str, any]:
    """
    Ping a device and return detailed status information.
    
    Args:
        hostname: The target device hostname
        
    Returns:
        Dict containing ping results and latency information
    """
    try:
        import time
        
        start_time = time.time()
        
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "2000", hostname],
                capture_output=True,
                text=True,
                timeout=3
            )
            success = "TTL=" in result.stdout
        else:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", hostname],
                capture_output=True,
                text=True,
                timeout=3
            )
            success = result.returncode == 0
        
        end_time = time.time()
        latency = round((end_time - start_time) * 1000, 1)
        
        if success:
            # Extract actual ping time from output
            try:
                if platform.system().lower() == "windows":
                    time_match = re.search(r'time[=<](\d+)ms', result.stdout)
                else:
                    time_match = re.search(r'time=(\d+\.?\d*) ms', result.stdout)
                
                if time_match:
                    latency = float(time_match.group(1))
            except (ValueError, AttributeError):
                pass
            
            return {
                'success': True,
                'latency': latency,
                'status': 'online'
            }
        else:
            return {
                'success': False,
                'error': 'Device not responding',
                'status': 'offline'
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Ping timeout',
            'status': 'timeout'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'status': 'error'
        }


def get_remote_access_options(hostname: str, ip_address: Optional[str] = None) -> Dict[str, any]:
    """
    Get available remote access options for a device.
    
    Args:
        hostname: The target device hostname
        ip_address: Optional IP address
        
    Returns:
        Dict containing available remote access methods and their status
    """
    target = hostname or ip_address
    if not target:
        return {
            'success': False,
            'error': 'No valid hostname or IP address provided'
        }
    
    try:
        # Check connectivity first
        connectivity = check_device_connectivity(hostname, ip_address)
        
        # Check available tools
        dameware_available = check_dameware_availability()
        
        return {
            'success': True,
            'target': target,
            'connectivity': connectivity,
            'remote_access_methods': {
                'dameware': {
                    'available': dameware_available,
                    'description': 'Dameware Remote Support',
                    'priority': 1
                },
                'rdp': {
                    'available': True,  # RDP is built into Windows
                    'description': 'Remote Desktop Protocol',
                    'priority': 2
                },
                'browser_vnc': {
                    'available': connectivity.get('vnc_available', False),
                    'description': 'Browser-based VNC',
                    'priority': 3
                },
                'ssh': {
                    'available': any(p['service'] == 'SSH' for p in connectivity.get('open_ports', [])),
                    'description': 'Secure Shell',
                    'priority': 4
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting remote access options: {e}")
        return {
            'success': False,
            'error': str(e),
            'target': target
        } 