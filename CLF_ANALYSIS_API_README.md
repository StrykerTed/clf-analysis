# CLF Analysis API Service

A Flask-based REST API service for analyzing CLF/ABP build files and generating platform paths shape analysis.

## Overview

This service provides API endpoints to run the `get_platform_paths_shapes_shapely.py` analysis tool, which:

- Analyzes CLF (Common Layer Format) files from ABP builds
- Generates platform paths and shape visualizations
- Detects holes and closed shapes
- Creates comprehensive analysis reports

## Docker Deployment (Recommended)

### Prerequisites

- Docker and Docker Compose installed
- The `defectdetect-database_default` network exists (created by the database stack)
- MIDAS data directory available at `/Users/ted.tedford/Documents/MIDAS` (macOS) or `C:/public/shared/DefectDetectorBuilds` (Windows)

### Quick Start with Docker

#### 1. Build the Service Image

```bash
# In the clf-analysis directory
docker build -t clf-abp-path-analysis:latest .
```

#### 2. Start the Service

```bash
# Start the clf-abp-path-analysis service
docker-compose up -d

# The service joins the defect-detector-services stack
# alongside defect-detect-fe (6200) and database-python-handler (6100)
```

#### 3. Verify the Service

```bash
# Check if container is running
docker ps | grep clf-abp-path-analysis

# View logs
docker-compose logs -f

# Test the health endpoint
curl http://localhost:6300/health
```

### Docker Configuration

**Architecture Note:** This service is part of the `defect-detector-services` stack. Each service has its own repository with its own `docker-compose.yml`, but they all use the same stack name and network, allowing them to work together:

- **defect-detect-fe** (port 6200) - React frontend
- **database-python-handler** (port 6100) - Database API
- **clf-abp-path-analysis** (port 6300) - CLF Analysis API (this service)
- **mssql** - SQL Server (external network)

The service is configured in `docker-compose.yml`:

```yaml
version: "3.8"

name: defect-detector-services

services:
  clf-abp-path-analysis:
    build: .
    container_name: clf-abp-path-analysis
    ports:
      - "6300:6300"
    environment:
      FLASK_ENV: production
      FLASK_DEBUG: "False"
      PORT: 6300
    volumes:
      - "/Users/ted.tedford/Documents/MIDAS:/Users/ted.tedford/Documents/MIDAS"
    networks:
      - defectdetect-database_default
    restart: unless-stopped
    external_links:
      - mssql:mssql

networks:
  defectdetect-database_default:
    external: true
```

### Docker Management Commands

```bash
# Start the service (joins the defect-detector-services stack)
docker-compose up -d

# Stop the service
docker-compose stop

# Restart the service
docker-compose restart

# View logs (follow mode)
docker-compose logs -f

# View logs (last 100 lines)
docker-compose logs --tail=100

# Rebuild and restart
docker-compose up -d --build

# Remove the service
docker-compose down

# Shell into the container
docker exec -it clf-abp-path-analysis bash
```

## Service Architecture

```
defect-detector-services Stack (shared network)
┌─────────────────────────────────────────────────────┐
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  defect-detect-fe (Port 6200)                │   │
│  │  React Frontend                              │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  database-python-handler (Port 6100)         │   │
│  │  Database API Service                        │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  clf-abp-path-analysis (Port 6300)           │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │   Flask API Endpoints                  │  │   │
│  │  │   - /health                            │  │   │
│  │  │   - /api/analyze                       │  │   │
│  │  │   - /api/builds/{id}/analyze           │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  │              │                                │   │
│  │              ▼                                │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │  get_platform_paths_shapes_shapely     │  │   │
│  │  │  - run_analysis()                      │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  │              │                                │   │
│  │              ▼                                │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │  CLF Processing Utilities              │  │   │
│  │  │  - CLFFile parsing                     │  │   │
│  │  │  - Shape analysis                      │  │   │
│  │  │  - Visualization generation            │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  External: mssql (database)                          │
│                                                       │
└─────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│  MIDAS Data Directory                                │
│  /Users/ted.tedford/Documents/MIDAS                  │
│  - Build folders                                     │
│  - ABP files                                         │
│  - Analysis outputs                                  │
└─────────────────────────────────────────────────────┘
```

### Platform-Specific Volume Mounts

**macOS:**

```yaml
volumes:
  - "/Users/ted.tedford/Documents/MIDAS:/Users/ted.tedford/Documents/MIDAS"
```

**Windows:**

```yaml
volumes:
  - "C:/public/shared/DefectDetectorBuilds:/Users/ted.tedford/Documents/MIDAS"
```

## API Endpoints

### 1. Root Endpoint

```
GET /
```

Returns service information and available endpoints.

**Response:**

```json
{
  "service": "CLF Analysis API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "analyze": "/api/analyze",
    "analyze_by_build": "/api/builds/<build_id>/analyze"
  }
}
```

### 2. Health Check

```
GET /health
```

Check if the service is running.

**Response:**

```json
{
  "status": "healthy",
  "service": "clf-abp-path-analysis",
  "timestamp": "2025-10-08T10:30:00"
}
```

### 3. Run Analysis (POST with JSON body)

```
POST /api/analyze
Content-Type: application/json
```

**Request Body:**

```json
{
  "build_id": "271360",
  "holes_interval": 10,
  "create_composite_views": false
}
```

**Parameters:**

- `build_id` (required): The build ID to analyze (e.g., "271360")
- `holes_interval` (optional): Interval in mm for creating holes views (default: 10)
- `create_composite_views` (optional): Whether to create composite platform views (default: false)

**Success Response (200):**

```json
{
  "status": "success",
  "result": {
    "success": true,
    "build_id": "271360",
    "duration_seconds": 45.32,
    "summary_path": "/Users/ted.tedford/Documents/MIDAS/271360/clf_analysis/platform_info.json",
    "output_dir": "/Users/ted.tedford/Documents/MIDAS/271360/clf_analysis",
    "holes_interval": 10,
    "create_composite_views": false
  }
}
```

**Error Response (400/500):**

```json
{
  "status": "error",
  "message": "build_id is required"
}
```

### 4. Run Analysis by Build ID (URL parameter)

```
POST /api/builds/{build_id}/analyze
Content-Type: application/json
```

**URL Parameter:**

- `build_id`: The build ID to analyze (e.g., "271360")

**Request Body (optional):**

```json
{
  "holes_interval": 10,
  "create_composite_views": false
}
```

**Example:**

```bash
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{"holes_interval": 15, "create_composite_views": true}'
```

## Usage Examples

### Using curl

```bash
# Health check
curl http://localhost:6300/health

# Run analysis with build_id in body
curl -X POST http://localhost:6300/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "271360",
    "holes_interval": 10,
    "create_composite_views": false
  }'

# Run analysis with build_id in URL
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "holes_interval": 15
  }'
```

### Using Python requests

```python
import requests

# Health check
response = requests.get('http://localhost:6300/health')
print(response.json())

# Run analysis
response = requests.post(
    'http://localhost:6300/api/analyze',
    json={
        'build_id': '271360',
        'holes_interval': 10,
        'create_composite_views': False
    }
)
result = response.json()
print(result)
```

### Using JavaScript/fetch

```javascript
// Health check
fetch("http://localhost:6300/health")
  .then((response) => response.json())
  .then((data) => console.log(data));

// Run analysis
fetch("http://localhost:6300/api/analyze", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    build_id: "271360",
    holes_interval: 10,
    create_composite_views: false,
  }),
})
  .then((response) => response.json())
  .then((data) => console.log(data));
```

## Output Structure

Analysis results are saved to the MIDAS directory:

```
/Users/ted.tedford/Documents/MIDAS/
└── {build_id}/
    └── clf_analysis/
        ├── platform_info.json          # Analysis summary
        ├── output/                     # Main output directory
        ├── layer_partials/            # Layer-by-layer partials
        ├── composite_platforms/       # Composite views
        ├── identifier_views/          # Identifier-specific views
        ├── clean_platforms/           # Clean platform images
        └── holes_views/               # Hole detection views
```

## Troubleshooting

### Container won't start

```bash
# Check logs for errors
docker-compose logs clf-abp-path-analysis

# Verify image was built
docker images | grep clf-analysis

# Rebuild the image
docker-compose build clf-abp-path-analysis
docker-compose up -d clf-abp-path-analysis
```

### Port 6300 already in use

```bash
# Find what's using the port
lsof -ti:6300

# Kill the process
lsof -ti:6300 | xargs kill -9

# Or change the port in docker-compose.yml
ports:
  - "6301:6300"  # Use 6301 on host instead
```

### Volume mount issues

```bash
# Verify MIDAS directory exists
ls -la /Users/ted.tedford/Documents/MIDAS

# Check Docker has permissions
# On macOS: System Preferences → Security & Privacy → Privacy → Files and Folders
# Ensure Docker has access to the MIDAS directory
```

### Analysis fails

```bash
# Check the logs
docker-compose logs -f clf-abp-path-analysis

# Verify build files exist
docker exec -it clf-abp-path-analysis ls /Users/ted.tedford/Documents/MIDAS/271360

# Shell into container for debugging
docker exec -it clf-abp-path-analysis bash
```

## Development Mode

For local development without Docker:

### Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run Locally

```bash
# Run with default settings
python clf_analysis_api.py

# Run with custom port
PORT=5000 python clf_analysis_api.py

# Run in debug mode
FLASK_DEBUG=True python clf_analysis_api.py
```

## Service Architecture

This section moved to the top - see "Docker Configuration" section above.

## Port Allocation

| Service                 | Port | Status       |
| ----------------------- | ---- | ------------ |
| database-python-handler | 6100 | ✅ In use    |
| defect-detect-fe        | 6200 | ✅ In use    |
| clf-abp-path-analysis   | 6300 | ✅ In use    |
| (available)             | 6400 | 🟢 Available |

## Access Points

Once deployed, the service is accessible at:

- **API Endpoint**: http://localhost:6300
- **Health Check**: http://localhost:6300/health
- **API Documentation**: http://localhost:6300/

## Related Services

This service is part of the `defect-detector-services` stack:

- **mssql**: SQL Server database (external network)
- **database-python-handler**: Database API (port 6100) - in separate repo
- **defect-detect-fe**: React Frontend (port 6200) - in separate repo
- **clf-abp-path-analysis**: CLF Analysis API (port 6300) - **this service**

All services share the `defectdetect-database_default` network and combine into a single Docker Compose stack despite being in separate repositories.

## Notes

- The service requires read/write access to the MIDAS directory
- Analysis can take several minutes depending on build size
- Results are saved to `{MIDAS}/{build_id}/clf_analysis/`
- The service supports concurrent analysis requests
- All analysis parameters from `get_platform_paths_shapes_shapely.py` are supported

## Support

For issues or questions:

1. Check the logs: `docker-compose logs -f clf-abp-path-analysis`
2. Verify the health endpoint: `curl http://localhost:6300/health`
3. Review the MIDAS directory permissions
4. Ensure the build files exist in the expected location
