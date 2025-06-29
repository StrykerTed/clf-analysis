#!/bin/bash

# CLF Analysis Web App Startup Script
# This script ensures Flask always runs on port 5000 using the virtual environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
WEB_APP_PATH="$SCRIPT_DIR/web_app"

echo -e "${BLUE}🚀 CLF Analysis Web App Startup${NC}"
echo -e "${BLUE}================================${NC}"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment not found at: $VENV_PATH${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_PATH"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}📦 Installing Flask and dependencies...${NC}"
    pip install -r "$WEB_APP_PATH/requirements.txt"
fi

# Function to kill process using port 5000
kill_port_5000() {
    echo -e "${YELLOW}🔍 Checking for processes using port 5000...${NC}"
    
    # Find process using port 5000
    PID=$(lsof -ti:5000 2>/dev/null || true)
    
    if [ ! -z "$PID" ]; then
        echo -e "${RED}⚠️  Port 5000 is in use by process: $PID${NC}"
        echo -e "${YELLOW}🔪 Killing process $PID...${NC}"
        kill -9 $PID 2>/dev/null || true
        sleep 2
        
        # Double check if process is killed
        PID_CHECK=$(lsof -ti:5000 2>/dev/null || true)
        if [ ! -z "$PID_CHECK" ]; then
            echo -e "${RED}❌ Failed to kill process on port 5000${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Port 5000 is now free${NC}"
    else
        echo -e "${GREEN}✅ Port 5000 is available${NC}"
    fi
}

# Kill any process using port 5000
kill_port_5000

# Change to web app directory
cd "$WEB_APP_PATH"

# Start Flask application
echo -e "${GREEN}🌐 Starting Flask application on port 5000...${NC}"
echo -e "${BLUE}📱 Access the app at: http://localhost:5000${NC}"
echo -e "${YELLOW}🛑 Press Ctrl+C to stop the server${NC}"
echo ""

# Export Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Start Flask with error handling
python app.py
