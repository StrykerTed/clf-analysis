# CLF Analysis Web App

A Flask-based web application for analyzing CLF/ABP build files.

## Quick Start

### Starting the Application

#### Option 1: Using the Python Startup Script (Recommended)

```bash
./start_web_app.py
```

#### Option 2: Using the Bash Startup Script

```bash
./start_web_app.sh
```

#### Option 3: Manual Start

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
cd web_app
pip install -r requirements.txt

# Start Flask app
python app.py
```

### Stopping the Application

#### Option 1: Using the Stop Script

```bash
./stop_web_app.py
```

#### Option 2: Using Ctrl+C
Press `Ctrl+C` in the terminal where the application is running

#### Option 3: Manual Stop

```bash
# Find and kill process using port 5000
lsof -ti:5000 | xargs kill -SIGTERM
```

## Features

- 🏗️ **Build Selection**: Browse and select from available ABP build folders
- 📏 **Height Input**: Specify analysis height (0-9999.99 mm, 2 decimal places)
- 🎨 **Professional UI**: Stryker/Digital R&D branded interface
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🔄 **Real-time Feedback**: Live validation and status updates
- 🛡️ **Error Handling**: Comprehensive error handling and user feedback

## Automatic Features

The startup scripts automatically:

- ✅ Use the virtual environment (`venv/`)
- ✅ Install/update dependencies from `requirements.txt`
- ✅ Kill any process using port 5000
- ✅ Start Flask on port 5000 (always)
- ✅ Set appropriate Flask environment variables

## API Endpoints

- `GET /` - Main web interface
- `GET /health` - Health check endpoint
- `GET /api/builds` - List available build folders
- `POST /api/builds/<build_number>/analyze` - Analyze a build with height parameter

## Port Management

The application **always** uses port 5000. If port 5000 is occupied by another process, the startup scripts will automatically:

1. Identify the conflicting process
2. Terminate it safely
3. Start Flask on port 5000

## Access

Once started, access the application at:
**http://localhost:5000**

## Directory Structure

```
clf_analysis_clean/
├── start_web_app.py          # Python startup script (recommended)
├── start_web_app.sh          # Bash startup script
├── stop_web_app.py           # Python stop script
├── venv/                     # Virtual environment
├── web_app/                  # Flask application
│   ├── app.py               # Main Flask app
│   ├── requirements.txt     # Python dependencies
│   ├── static/              # CSS, JS, assets
│   ├── templates/           # HTML templates
│   └── assets/              # Logos, favicon
└── abp_contents/            # ABP build folders (data source)
```

## Troubleshooting

### Port Issues

If you encounter port conflicts, the startup scripts handle this automatically. If manual intervention is needed:

```bash
# Check what's using port 5000
lsof -i :5000

# Kill specific process
kill -9 <PID>
```

### Virtual Environment Issues

If the virtual environment is corrupted:

```bash
# Remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r web_app/requirements.txt
```

### Dependencies Issues

```bash
# Update dependencies
source venv/bin/activate
pip install --upgrade -r web_app/requirements.txt
```
