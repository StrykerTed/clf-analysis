#!/usr/bin/env python3
"""
CLF Analysis Web App Startup Script
This script ensures Flask always runs on port 5000 using the virtual environment
"""

import os
import sys
import subprocess
import time
import signal
import platform
from pathlib import Path

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

def get_script_dir():
    """Get the directory where this script is located"""
    return Path(__file__).parent.absolute()

def check_and_kill_port_5000():
    """Check for and kill any process using port 5000"""
    print_colored("🔍 Checking for processes using port 5000...", Colors.YELLOW)
    
    try:
        if platform.system() == "Windows":
            # Windows command
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if ':5000 ' in line and 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        print_colored(f"⚠️  Port 5000 is in use by process: {pid}", Colors.RED)
                        print_colored(f"🔪 Killing process {pid}...", Colors.YELLOW)
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        time.sleep(2)
                        break
        else:
            # Unix/Linux/macOS command
            result = subprocess.run(['lsof', '-ti:5000'], capture_output=True, text=True)
            if result.stdout.strip():
                pid = result.stdout.strip()
                print_colored(f"⚠️  Port 5000 is in use by process: {pid}", Colors.RED)
                print_colored(f"🔪 Killing process {pid}...", Colors.YELLOW)
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    time.sleep(2)
                    # Force kill if still running
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already dead
                except ProcessLookupError:
                    pass  # Process already dead
                
                print_colored("✅ Port 5000 is now free", Colors.GREEN)
            else:
                print_colored("✅ Port 5000 is available", Colors.GREEN)
                
    except Exception as e:
        print_colored(f"⚠️  Could not check port 5000: {e}", Colors.YELLOW)

def setup_virtual_environment(script_dir):
    """Setup and activate virtual environment"""
    venv_path = script_dir / "venv"
    
    if not venv_path.exists():
        print_colored("❌ Virtual environment not found", Colors.RED)
        print_colored("Creating virtual environment...", Colors.YELLOW)
        subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], check=True)
        print_colored("✅ Virtual environment created", Colors.GREEN)
    
    # Determine the correct python executable path
    if platform.system() == "Windows":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    return python_exe, pip_exe

def install_requirements(pip_exe, web_app_path):
    """Install requirements if needed"""
    requirements_file = web_app_path / "requirements.txt"
    
    if requirements_file.exists():
        print_colored("📦 Installing/updating dependencies...", Colors.YELLOW)
        subprocess.run([str(pip_exe), 'install', '-r', str(requirements_file)], check=True)
        print_colored("✅ Dependencies installed", Colors.GREEN)
    else:
        print_colored("⚠️  No requirements.txt found", Colors.YELLOW)

def start_flask_app(python_exe, web_app_path):
    """Start the Flask application"""
    print_colored("🌐 Starting Flask application on port 5000...", Colors.GREEN)
    print_colored("📱 Access the app at: http://localhost:5000", Colors.BLUE)
    print_colored("🛑 Press Ctrl+C to stop the server", Colors.YELLOW)
    print()
    
    # Set environment variables
    env = os.environ.copy()
    env['FLASK_APP'] = 'app.py'
    env['FLASK_ENV'] = 'development'
    env['FLASK_DEBUG'] = '1'
    
    # Change to web app directory and start Flask
    os.chdir(web_app_path)
    
    try:
        subprocess.run([str(python_exe), 'app.py'], env=env, check=True)
    except KeyboardInterrupt:
        print_colored("\n🛑 Shutting down Flask application...", Colors.YELLOW)
        print_colored("✅ Application stopped", Colors.GREEN)
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Flask application failed: {e}", Colors.RED)
        sys.exit(1)

def main():
    """Main function"""
    print_colored("🚀 CLF Analysis Web App Startup", Colors.BLUE)
    print_colored("================================", Colors.BLUE)
    
    script_dir = get_script_dir()
    web_app_path = script_dir / "web_app"
    
    # Check if web app directory exists
    if not web_app_path.exists():
        print_colored(f"❌ Web app directory not found: {web_app_path}", Colors.RED)
        sys.exit(1)
    
    # Kill any process using port 5000
    check_and_kill_port_5000()
    
    # Setup virtual environment
    print_colored("🔧 Setting up virtual environment...", Colors.YELLOW)
    python_exe, pip_exe = setup_virtual_environment(script_dir)
    
    # Install requirements
    install_requirements(pip_exe, web_app_path)
    
    # Start Flask application
    start_flask_app(python_exe, web_app_path)

if __name__ == "__main__":
    main()
