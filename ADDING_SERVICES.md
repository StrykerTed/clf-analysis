# Adding Additional Services to defect-detector-services

This guide explains how to add additional Python services (or other services) to the `defect-detector-services` Docker Compose stack using a **multi-repo architecture pattern**.

## Architecture Overview

The `defect-detector-services` stack uses a **multi-repository approach** where:
- Each service has its **own repository** with its own `docker-compose.yml`
- All `docker-compose.yml` files use the **same stack name**: `defect-detector-services`
- Services automatically join the shared stack and can communicate via the external `defectdetect-database_default` network

### Current Services

| Service | Port | Repository | Status |
|---------|------|------------|--------|
| **mssql** | 1433 | defectdetect-database | ✅ External stack |
| **database-python-handler** | 6100 | database-python-handler | ✅ Active |
| **defect-detect-fe** | 6200 | defect-detect-fe | ✅ Active |
| **clf-abp-path-analysis** | 6300 | clf-analysis | ✅ Active |

All services communicate over the `defectdetect-database_default` Docker network.

## Multi-Repo Architecture Pattern

**Key Principle**: Each repository contains its own `docker-compose.yml` with `name: defect-detector-services`. Docker Compose automatically merges all services with the same stack name into a single logical stack.

### Benefits
✅ Each service is independently deployable  
✅ Service repositories are self-contained  
✅ No need to modify other repos when adding new services  
✅ Services can be started/stopped independently  
✅ Easier CI/CD and version control  

## Prerequisites

Before adding a new service, ensure you have:
- Docker and Docker Compose installed
- The `defectdetect-database_default` network exists (created by defectdetect-database stack)
- A working service in its own repository
- Decided on an available port (e.g., 6400, 6500, etc. to avoid conflicts)

## Step-by-Step Guide: Real Example (clf-abp-path-analysis)

This section documents the actual process used to add the **clf-abp-path-analysis** service, which wraps `get_platform_paths_shapes_shapely.py` in a REST API.

### Step 1: Create Your Service Repository

In your service repository (e.g., `clf-analysis`):

#### 1.1 Create the Flask API Wrapper

Create `clf_analysis_api.py`:

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import uuid
from datetime import datetime

# Import your existing analysis function
from tools.get_platform_paths_shapes_shapely import run_analysis

app = Flask(__name__)

# Configure CORS for frontend access
CORS(app, origins=[
    "http://localhost:6200",      # Production frontend
    "http://127.0.0.1:6200",
    "http://defect-detect-fe:6200",
    "http://localhost:5176",      # Development frontend
])

# In-memory job tracking
jobs = {}

def run_analysis_async(job_id, build_id, holes_interval=10.0, create_composite_views=True):
    """Run analysis in background thread"""
    try:
        jobs[job_id]['status'] = 'running'
        jobs[job_id]['started_at'] = datetime.now().isoformat()
        
        # Run the actual analysis
        run_analysis(build_id, holes_interval, create_composite_views)
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['completed_at'] = datetime.now().isoformat()
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['completed_at'] = datetime.now().isoformat()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'service': 'clf-abp-path-analysis',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/builds/<build_id>/analyze', methods=['POST'])
def analyze_build(build_id):
    """Trigger analysis for a build (async)"""
    job_id = str(uuid.uuid4())
    
    # Get optional parameters
    data = request.get_json() or {}
    holes_interval = data.get('holes_interval', 10.0)
    create_composite_views = data.get('create_composite_views', True)
    
    # Initialize job
    jobs[job_id] = {
        'job_id': job_id,
        'build_id': build_id,
        'status': 'accepted',
        'created_at': datetime.now().isoformat()
    }
    
    # Start background thread
    thread = threading.Thread(
        target=run_analysis_async,
        args=(job_id, build_id, holes_interval, create_composite_views)
    )
    thread.start()
    
    return jsonify({
        'status': 'accepted',
        'job_id': job_id,
        'build_id': build_id,
        'message': 'Analysis started. Poll /api/jobs/{job_id} for status.'
    }), 202

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Check job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(jobs[job_id])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6300, debug=False)
```

**Key Design Decisions:**
- ✅ **Async Processing**: Returns job_id immediately (202 Accepted), runs analysis in background thread
- ✅ **CORS Configuration**: Allows frontend to make cross-origin requests
- ✅ **Health Check**: Enables Docker health monitoring
- ✅ **Job Tracking**: In-memory job status (sufficient for single-instance deployment)

#### 1.2 Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose service port
EXPOSE 6300

# Run the Flask API
CMD ["python", "clf_analysis_api.py"]
```

**Important Notes:**
- Use `python:3.12-slim` for Python 3.12 support
- Install system dependencies needed by your Python packages (e.g., OpenCV needs `libgl1`)
- Use `libgl1` not `libgl1-mesa-glx` (unavailable in Debian Trixie)

#### 1.3 Update requirements.txt

```txt
# API Framework
flask==3.0.0
flask-cors==4.0.0

# Data Processing (ensure Python 3.12 compatibility)
numpy==1.26.4  # NOT 1.24.3 - needs pre-built wheels for Python 3.12
matplotlib==3.10.0
opencv-python==4.10.0.84
shapely==2.0.6

# HTTP
requests==2.32.3

# Add your existing dependencies...
```

**Python 3.12 Compatibility:**
- Use `numpy>=1.26.4` (1.24.3 requires building from source)
- Check PyPI for Python 3.12 wheel availability before pinning versions

#### 1.4 Test Locally (Optional)

```bash
# In your service repository
docker build -t clf-abp-path-analysis:latest .
docker run -p 6300:6300 clf-abp-path-analysis:latest

# Test health check
curl http://localhost:6300/health
```

### Step 2: Create docker-compose.yml (Multi-Repo Pattern)

**CRITICAL**: Create `docker-compose.yml` in **YOUR SERVICE REPOSITORY** (not in defect-detect-fe):

```yaml
version: "3.8"

# THIS IS THE KEY: Use the same stack name across all repos
name: defect-detector-services

services:
  clf-abp-path-analysis:
    build: .
    container_name: clf-abp-path-analysis
    ports:
      - "6300:6300"
    volumes:
      # Mount MIDAS data directory
      - /Users/ted.tedford/Documents/MIDAS:/Users/ted.tedford/Documents/MIDAS:rw
    networks:
      - defectdetect-database_default
    restart: unless-stopped

networks:
  defectdetect-database_default:
    external: true
```

**Key Points:**
- ✅ **Stack Name**: `name: defect-detector-services` - MUST match other repos
- ✅ **Container Name**: Unique name for your service
- ✅ **Port**: Choose available port (6300, 6400, 6500, etc.)
- ✅ **Network**: Use `external: true` for `defectdetect-database_default`
- ✅ **Volumes**: Mount any required data directories (e.g., MIDAS path)

**Why This Works:**
Docker Compose sees all services with `name: defect-detector-services` as part of the same stack, even if they're in different repositories. When you run `docker-compose up` in any repo, it joins the existing stack.

### Step 3: Build and Deploy Your Service

```bash
# In YOUR service repository (e.g., clf-analysis)
cd /path/to/clf-analysis

# Build and start the service
docker-compose up -d --build

# Docker will:
# 1. Build your Dockerfile
# 2. Create/update the container
# 3. Join it to the defect-detector-services stack
# 4. Connect it to defectdetect-database_default network
```

### Step 4: Verify the Service

```bash
# Check if container is running
docker ps | grep clf-abp-path-analysis

# View all services in the stack
docker compose -p defect-detector-services ps

# View logs
docker-compose logs -f clf-abp-path-analysis

# Test the service
curl http://localhost:6300/health

# Should return:
# {"service":"clf-abp-path-analysis","status":"healthy","timestamp":"..."}
```

### Step 5: Test Cross-Service Communication

Services can communicate using container names:

```bash
# From another container in the stack
docker exec database-python-handler curl http://clf-abp-path-analysis:6300/health

# From your host machine
curl http://localhost:6300/health
```

### Step 6: Update Service and Redeploy

```bash
# After making code changes
cd /path/to/clf-analysis

# Rebuild and restart
docker-compose up -d --build

# Or restart without rebuilding
docker-compose restart clf-abp-path-analysis
```

## Complete Example: clf-abp-path-analysis Repository Structure

```
clf-analysis/
├── clf_analysis_api.py          # Flask API wrapper
├── docker-compose.yml            # Service definition (stack: defect-detector-services)
├── Dockerfile                    # Container definition
├── requirements.txt              # Python dependencies
├── README.md                     # Service documentation
├── CLF_ANALYSIS_API_README.md   # API documentation
├── API_ASYNC_GUIDE.md           # Async workflow guide
├── ADDING_SERVICES.md           # This file
├── src/                         # Source code
│   └── tools/
│       └── get_platform_paths_shapes_shapely.py  # Original analysis script
└── ...
```

## Viewing the Complete Stack

From any repository with `name: defect-detector-services`:

```bash
# List all services in the stack
docker compose -p defect-detector-services ps

# View logs for entire stack
docker compose -p defect-detector-services logs -f

# Stop entire stack (from any repo)
docker compose -p defect-detector-services down

# Restart specific service (from its repo)
cd /path/to/clf-analysis
docker-compose restart clf-abp-path-analysis
```

## Port Selection Guidelines

Choose ports in the **6000 range** to avoid conflicts:

| Service | Port | Repository | Status |
|---------|------|------------|--------|
| database-python-handler | 6100 | database-python-handler | ✅ In use |
| defect-detect-fe | 6200 | defect-detect-fe | ✅ In use |
| clf-abp-path-analysis | 6300 | clf-analysis | ✅ In use |
| *your-new-service* | 6400 | *your-repo* | 🟢 Available |
| *another-service* | 6500 | *another-repo* | 🟢 Available |

## Common Patterns and Configuration

### Pattern 1: Long-Running Analysis Service (Async)

**Use Case**: Analysis/processing that takes several minutes

**Implementation**: 
- Return job_id immediately (HTTP 202 Accepted)
- Run analysis in background thread
- Provide status endpoint for polling

```python
# See clf_analysis_api.py for full example
@app.route('/api/builds/<build_id>/analyze', methods=['POST'])
def analyze_build(build_id):
    job_id = str(uuid.uuid4())
    thread = threading.Thread(target=run_analysis_async, args=(job_id, build_id))
    thread.start()
    return jsonify({'job_id': job_id}), 202
```

### Pattern 2: Quick Response Service (Sync)

**Use Case**: Fast lookups or queries

```python
@app.route('/api/data/<id>', methods=['GET'])
def get_data(id):
    result = fetch_data(id)
    return jsonify(result), 200
```

## Common Configuration Options

### Environment Variables

```yaml
environment:
  # Database connection
  DB_HOST: mssql
  DB_PORT: 1433
  DB_NAME: scanalyserdatabase
  DB_USER: sa
  DB_PASSWORD: ${DB_PASSWORD}  # From .env file
  
  # Service configuration
  SERVICE_PORT: 6300
  LOG_LEVEL: INFO
  DEBUG: "false"
  
  # External service URLs (inter-service communication)
  BACKEND_URL: http://database-python-handler:6100
  FRONTEND_URL: http://defect-detect-fe:6200
```

### Volumes (for development)

```yaml
volumes:
  # Mount source code for development (hot reload)
  - /path/to/my-python-service:/app
  
  # Persistent data storage
  - ./data:/app/data
  
  # Logs
  - ./logs:/app/logs
```

### Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:6300/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Dependencies

```yaml
depends_on:
  - database-python-handler  # Wait for backend to start first
```

## Inter-Service Communication

Services within the same Docker network can communicate using **container names**:

```python
# In your Python service, connect to other services:
import requests

# Connect to backend
response = requests.get('http://database-python-handler:6100/api/data')

# Connect to database
connection_string = 'mssql+pyodbc://sa:password@mssql:1433/database'

# NOTE: From outside Docker (browser/host), use localhost:
# http://localhost:6100, http://localhost:6300, etc.
```

## CORS Configuration

If your service needs to accept requests from the frontend, configure CORS:

### Flask Example (from clf-abp-path-analysis)

```python
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# Allow requests from frontend (production and development)
CORS(app, origins=[
    "http://localhost:6200",      # Frontend Docker container
    "http://127.0.0.1:6200",      # Alternative localhost
    "http://defect-detect-fe:6200",  # Docker internal network
    "http://localhost:5176",      # Frontend dev server (Vite)
])
```

**Important**: Always include both production (6200) and development (5176) origins for flexibility.

### FastAPI Example

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:6200",
        "http://localhost:5176",
        "http://127.0.0.1:6200",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Managing Multiple Services

### Start specific services

```bash
# Start only your service (from its repository)
cd /path/to/your-service-repo
docker-compose up -d

# Rebuild and start
docker-compose up -d --build
```

### View logs for specific services

```bash
# Single service (from its repository)
docker-compose logs -f

# Or by name from any repo
docker logs -f clf-abp-path-analysis
```

### Restart a service

```bash
# From the service's repository
docker-compose restart

# Or from anywhere by name
docker restart clf-abp-path-analysis

# Rebuild and restart
cd /path/to/service-repo
docker-compose up -d --build
```

### Stop specific services

```bash
# From the service's repository
docker-compose down

# Or stop without removing
docker-compose stop
```

### View entire stack

```bash
# From any repository with name: defect-detector-services
docker compose -p defect-detector-services ps

# Or use docker ps
docker ps --filter "network=defectdetect-database_default"
```

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs

# Or by container name
docker logs clf-abp-path-analysis

# Check if port is already in use
lsof -i :6300  # macOS/Linux
netstat -ano | findstr :6300  # Windows

# Verify image was built
docker images | grep clf-abp-path-analysis
```

### Service can't connect to database

```bash
# Verify network connectivity
docker exec clf-abp-path-analysis ping mssql

# Check if on correct network
docker network inspect defectdetect-database_default

# Verify container is on the network
docker inspect clf-abp-path-analysis | grep Networks -A 10
```

### Service can't be reached from host

```bash
# Verify port mapping
docker ps | grep clf-abp-path-analysis

# Check if service is listening inside container
docker exec clf-abp-path-analysis netstat -tlnp | grep 6300

# Test from inside the network
docker exec database-python-handler curl http://clf-abp-path-analysis:6300/health
```

### CORS issues

- Ensure your service allows the frontend origin (`http://localhost:6200` and `http://localhost:5176`)
- Check browser console for specific CORS error messages
- Test API directly with curl first (bypasses CORS)

```bash
# Test without CORS (from terminal)
curl http://localhost:6300/api/builds/271360/analyze -X POST

# Test with CORS headers (simulating browser)
curl -H "Origin: http://localhost:6200" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     http://localhost:6300/api/builds/271360/analyze
```

### Docker Compose stack name conflicts

```bash
# If services aren't joining the same stack, verify:
# 1. All docker-compose.yml files have: name: defect-detector-services
grep "^name:" docker-compose.yml

# 2. View all stacks
docker compose ls

# 3. If wrong stack name, update and redeploy
docker-compose down
# Edit docker-compose.yml
docker-compose up -d
```

### Python package compatibility issues

**Symptom**: `pip install` fails during Docker build

**Common Causes**:
- Package doesn't have pre-built wheels for Python 3.12
- Missing system dependencies

**Solutions**:
```dockerfile
# Update package versions to ones with Python 3.12 wheels
# Example: numpy==1.26.4 (not 1.24.3)

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ \
    python3-dev \
    # Add others as needed
```

### Volume mount issues

```bash
# Verify volume is mounted correctly
docker inspect clf-abp-path-analysis | grep Mounts -A 20

# Test access inside container
docker exec clf-abp-path-analysis ls -la /Users/ted.tedford/Documents/MIDAS

# Ensure path exists on host
ls -la /Users/ted.tedford/Documents/MIDAS
```

## Best Practices

1. **Each service in its own repository** - Use multi-repo pattern with same stack name
2. **Use same stack name** - All `docker-compose.yml` files must have `name: defect-detector-services`
3. **Build images in service repos** - Keep Dockerfile and source code together
4. **Use consistent naming** - Container names should match service purpose
5. **Document your ports** - Update this guide when adding new services
6. **Use environment variables** - Don't hardcode secrets or configuration
7. **Add health checks** - Enables Docker to monitor service health
8. **Test locally first** - Always test service standalone before adding to stack
9. **Configure CORS properly** - Include both production and dev origins
10. **Use external network** - All services use `defectdetect-database_default` (external: true)
11. **Implement async for long tasks** - Return job_id immediately, process in background
12. **Version Python packages carefully** - Ensure Python 3.12 compatibility (check for pre-built wheels)

## Multi-Repo Deployment Workflow

1. **Develop your service** in its own repository
2. **Create docker-compose.yml** with `name: defect-detector-services`
3. **Build and test** locally: `docker-compose up -d --build`
4. **Verify** service joins the stack: `docker compose -p defect-detector-services ps`
5. **Test inter-service communication** using container names
6. **Update documentation** in your service's README and this guide
7. **Deploy** in production by running `docker-compose up -d` in each service repo

## Quick Reference: Adding a New Service

```bash
# 1. In YOUR new service repository:
cd /path/to/your-new-service

# 2. Create docker-compose.yml with:
#    - name: defect-detector-services
#    - networks: defectdetect-database_default (external: true)
#    - ports: "6XXX:6XXX" (choose available port)

# 3. Build and deploy
docker-compose up -d --build

# 4. Verify
docker ps | grep your-service-name
docker logs your-service-name
curl http://localhost:6XXX/health

# 5. Check it joined the stack
docker compose -p defect-detector-services ps
```

## Summary

The **multi-repo Docker Compose pattern** makes adding services to `defect-detector-services` straightforward:

### Key Steps:
1. ✅ Create your service in its own repository
2. ✅ Create `docker-compose.yml` with `name: defect-detector-services`
3. ✅ Use `networks: defectdetect-database_default` with `external: true`
4. ✅ Choose an available port (6400, 6500, etc.)
5. ✅ Build and deploy: `docker-compose up -d --build`
6. ✅ Verify service joins the stack: `docker compose -p defect-detector-services ps`
7. ✅ Configure CORS if frontend access needed
8. ✅ Implement async processing for long-running tasks
9. ✅ Update documentation

### Critical Points:
- **Stack Name**: Must be `defect-detector-services` in ALL repos
- **Network**: Must use external `defectdetect-database_default` network
- **Ports**: Choose available ports in 6000 range
- **Independence**: Each service deploys from its own repo
- **Communication**: Services use container names (e.g., `http://clf-abp-path-analysis:6300`)

### Real Example:
See **clf-abp-path-analysis** service in the `clf-analysis` repository for a complete working implementation of this pattern.

Your new service will automatically join the stack and communicate with all other services! 🚀
