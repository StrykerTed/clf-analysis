#!/usr/bin/env python3
"""
CLF Analysis Web App Stop Script
This script stops the Flask application running on port 5000
"""

import subprocess
import platform
import signal
import os

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(message, color):
    """Print colored message"""
    print(f"{color}{message}{Colors.NC}")

def stop_flask_app():
    """Stop Flask application running on port 5000"""
    print_colored("🛑 CLF Analysis Web App Stop", Colors.BLUE)
    print_colored("============================", Colors.BLUE)
    
    try:
        if platform.system() == "Windows":
            # Windows command
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            killed = False
            for line in lines:
                if ':5000 ' in line and 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        print_colored(f"🔍 Found Flask app with PID: {pid}", Colors.YELLOW)
                        print_colored(f"🔪 Stopping process {pid}...", Colors.YELLOW)
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        killed = True
                        break
        else:
            # Unix/Linux/macOS command
            result = subprocess.run(['lsof', '-ti:5000'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                killed = False
                for pid in pids:
                    if pid.strip():
                        print_colored(f"🔍 Found Flask app with PID: {pid.strip()}", Colors.YELLOW)
                        print_colored(f"🔪 Stopping process {pid.strip()}...", Colors.YELLOW)
                        try:
                            # First try graceful termination
                            os.kill(int(pid.strip()), signal.SIGTERM)
                            killed = True
                        except (ProcessLookupError, ValueError):
                            pass
            else:
                killed = False
        
        if killed:
            print_colored("✅ Flask application stopped successfully", Colors.GREEN)
        else:
            print_colored("ℹ️  No Flask application found running on port 5000", Colors.BLUE)
            
    except Exception as e:
        print_colored(f"❌ Error stopping Flask application: {e}", Colors.RED)

if __name__ == "__main__":
    stop_flask_app()
