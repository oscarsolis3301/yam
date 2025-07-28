#!/usr/bin/env python3
"""
Script to start the YAM server without debug mode to prevent terminal spam
"""

import os
import sys
import subprocess

def start_server():
    """Start the server without debug mode."""
    print("🚀 Starting YAM Server (No Debug Mode)...")
    print("=" * 50)
    
    # Change to the app directory
    os.chdir('app')
    
    # Start server without debug mode
    cmd = [
        sys.executable, 'server.py',
        '--host', '127.0.0.1',
        '--port', '5000',
        '--mode', 'web',
        '--no-reloader'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("=" * 50)
    
    try:
        # Start the server process
        process = subprocess.Popen(cmd, cwd='app')
        
        print("✅ Server started successfully!")
        print("🌐 Access the application at: http://127.0.0.1:5000")
        print("📝 Press Ctrl+C to stop the server")
        
        # Wait for the process to complete
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    start_server() 