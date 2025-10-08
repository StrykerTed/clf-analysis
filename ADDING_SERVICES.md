# Adding Additional Services to defect-detector-services

This guide explains how to add additional Python services (or other services) to the `defect-detector-services` Docker Compose stack.

## Overview

The `defect-detector-services` stack currently contains:
- **defect-detect-fe**: React frontend (Nginx) on port 6200
- **database-python-handler**: Python Flask backend on port 6100 (referenced from another repo)
- **mssql**: SQL Server database (external, part of `defectdetect-database` stack)

All services communicate over the `defectdetect-database_default` Docker network.

## Prerequisites

Before adding a new service, ensure you have:
- Docker and Docker Compose installed
- The `defectdetect-database_default` network exists
- A working service in its own repository (with working Dockerfile)
- Decided on an available port (e.g., 6300, 6400, etc. to avoid conflicts)

## Step-by-Step Guide

### Step 1: Create Your Python Service

In a separate repository (e.g., `my-python-service`):

#### 1.1 Create a Dockerfile

```dockerfile
# Example Python service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (choose an unused port in 6000 range)
EXPOSE 6300

# Run the application
CMD ["python", "app.py"]
# OR for Flask:
# CMD ["flask", "run", "--host=0.0.0.0", "--port=6300"]
# OR for FastAPI:
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6300"]
```

#### 1.2 Create requirements.txt

```txt
flask==3.1.0
# OR
fastapi==0.115.0
uvicorn[standard]==0.32.0
# Add other dependencies
requests==2.32.3
python-dotenv==1.0.1
```

#### 1.3 Test Locally

```bash
# In your service repository
docker build -t my-python-service:latest .
docker run -p 6300:6300 my-python-service:latest
```

### Step 2: Build and Tag Your Service Image

Once your service works locally, build and tag it:

```bash
# In your service repository
cd /path/to/my-python-service
docker build -t my-python-service:latest .
```

### Step 3: Add Service to docker-compose.yml

In the **defect-detect-fe** repository, update `docker-compose.yml`:

```yaml
version: "3.8"

name: defect-detector-services

services:
  defect-detect-fe:
    build: .
    container_name: defect-detect-fe
    ports:
      - "6200:6200"
    networks:
      - defectdetect-database_default
    restart: unless-stopped

  # NEW SERVICE - Add this block
  my-python-service:
    image: my-python-service:latest  # Use the pre-built image
    container_name: my-python-service
    ports:
      - "6300:6300"  # Host:Container port mapping
    environment:
      # Add any environment variables your service needs
      DATABASE_URL: "mssql://mssql:1433/database"
      API_KEY: "your-api-key"
      FLASK_ENV: "production"
    networks:
      - defectdetect-database_default
    restart: unless-stopped
    # Optional: If your service depends on the database
    external_links:
      - mssql:mssql
    # Optional: Add volumes for persistent data or development
    # volumes:
    #   - ./data:/app/data

networks:
  defectdetect-database_default:
    external: true
```

### Step 4: Update Documentation

Update the `README.md` to document the new service:

```markdown
### Access the Application

- **Frontend**: http://localhost:6200
- **Backend API**: http://localhost:6100
- **My Python Service**: http://localhost:6300
```

### Step 5: Deploy the New Service

```bash
# In defect-detect-fe repository
cd /path/to/defect-detect-fe

# Build your service image first (if not already built)
# This should be done in your service's repository
cd /path/to/my-python-service
docker build -t my-python-service:latest .

# Return to defect-detect-fe
cd /path/to/defect-detect-fe

# Start only your new service (if others are already running)
docker-compose up -d my-python-service

# OR restart the entire stack
docker-compose up -d --build
```

### Step 6: Verify the Service

```bash
# Check if container is running
docker ps | grep my-python-service

# View logs
docker-compose logs -f my-python-service

# Test the service
curl http://localhost:6300/health
# or visit http://localhost:6300 in your browser
```

## Port Selection Guidelines

Choose ports in the **6000 range** to avoid conflicts:

| Service | Port | Status |
|---------|------|--------|
| database-python-handler | 6100 | ✅ In use |
| defect-detect-fe | 6200 | ✅ In use |
| my-python-service | 6300 | 🟢 Available |
| another-service | 6400 | 🟢 Available |
| yet-another-service | 6500 | 🟢 Available |

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

### Flask Example

```python
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# Allow requests from frontend
CORS(app, origins=[
    "http://localhost:6200",      # Frontend Docker
    "http://localhost:5176",      # Frontend dev server
    "http://127.0.0.1:6200",
    "http://127.0.0.1:5176",
])
```

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
# Start only your new service
docker-compose up -d my-python-service

# Start multiple specific services
docker-compose up -d defect-detect-fe my-python-service
```

### View logs for specific services

```bash
# Single service
docker-compose logs -f my-python-service

# Multiple services
docker-compose logs -f defect-detect-fe my-python-service
```

### Restart a service

```bash
# Restart after code changes
docker-compose restart my-python-service

# Rebuild and restart
docker-compose up -d --build my-python-service
```

### Stop specific services

```bash
docker-compose stop my-python-service
```

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs my-python-service

# Check if port is already in use
lsof -i :6300  # macOS/Linux
netstat -ano | findstr :6300  # Windows

# Verify image exists
docker images | grep my-python-service
```

### Service can't connect to database

```bash
# Verify network connectivity
docker exec my-python-service ping mssql

# Check if on correct network
docker network inspect defectdetect-database_default
```

### Service can't be reached from host

```bash
# Verify port mapping
docker ps | grep my-python-service

# Check if service is listening
docker exec my-python-service netstat -tlnp | grep 6300
```

### CORS issues

- Ensure your service allows the frontend origin (`http://localhost:6200`)
- Check browser console for specific CORS error messages
- Test API directly with curl first (bypasses CORS)

## Best Practices

1. **Keep services in separate repositories** - Each service should have its own repo with Dockerfile
2. **Build images before deploying** - Build and tag images in their respective repos
3. **Use consistent naming** - Follow the pattern: `service-name:latest`
4. **Document your ports** - Keep track of which ports are used
5. **Use environment variables** - Don't hardcode secrets or configuration
6. **Add health checks** - Makes it easier to monitor service status
7. **Test locally first** - Always test your service standalone before adding to compose
8. **Update README** - Document new services and their purposes

## Example: Adding a FastAPI Service

Complete example for adding a FastAPI-based ML service:

### 1. Service Repository Structure

```
ml-inference-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   └── routes.py
├── requirements.txt
├── Dockerfile
└── README.md
```

### 2. main.py (FastAPI app)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ML Inference Service")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:6200", "http://localhost:5176"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/predict")
def predict(data: dict):
    # Your ML inference logic
    return {"prediction": "result"}
```

### 3. docker-compose.yml addition

```yaml
  ml-inference-service:
    image: ml-inference-service:latest
    container_name: ml-inference-service
    ports:
      - "6400:6400"
    environment:
      MODEL_PATH: /app/models
      BACKEND_URL: http://database-python-handler:6100
    networks:
      - defectdetect-database_default
    restart: unless-stopped
```

### 4. Deploy

```bash
# Build in service repo
cd /path/to/ml-inference-service
docker build -t ml-inference-service:latest .

# Deploy from defect-detect-fe repo
cd /path/to/defect-detect-fe
docker-compose up -d ml-inference-service
```

## Summary

Adding a new Python service to the stack involves:

1. ✅ Create and test your service in its own repository
2. ✅ Build and tag the Docker image
3. ✅ Add service definition to `docker-compose.yml`
4. ✅ Choose an available port (6300+)
5. ✅ Configure environment variables and CORS if needed
6. ✅ Deploy with `docker-compose up -d`
7. ✅ Verify and test the service
8. ✅ Update documentation

Your new service will automatically join the `defectdetect-database_default` network and be able to communicate with all other services! 🚀
