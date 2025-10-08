# 🚀 CLF Analysis API - Deployment Summary

## ✅ What's Been Created

### 1. **API Service** (`clf_analysis_api.py`)

- Flask REST API with 3 endpoints:
  - `GET /health` - Health check
  - `POST /api/analyze` - Run analysis with JSON body
  - `POST /api/builds/{build_id}/analyze` - Run analysis with URL parameter
- Wraps the existing `run_analysis()` function from `get_platform_paths_shapes_shapely.py`
- Accepts parameters: `build_id`, `holes_interval`, `create_composite_views`

### 2. **Docker Configuration**

- **Dockerfile** - Python 3.12 slim with all dependencies
- **docker-compose.yml** - Service definition for `clf-abp-path-analysis` on port 6300
- **.dockerignore** - Optimized build context

**Important Architecture Note:**  
This service joins the `defect-detector-services` stack. Each service (defect-detect-fe, database-python-handler, clf-abp-path-analysis) has its own repository with its own `docker-compose.yml`, but they all use the same stack name and shared network, which allows Docker Compose to combine them automatically.

**Stack Services:**
- Port 6100: database-python-handler (separate repo)
- Port 6200: defect-detect-fe (separate repo)
- Port 6300: clf-abp-path-analysis (this repo)

### 3. **Dependencies** (`requirements.txt`)

- Added Flask, Flask-CORS, and requests
- Consolidated all existing dependencies

### 4. **Documentation**

- **CLF_ANALYSIS_API_README.md** - Comprehensive API documentation
- **API_QUICKSTART.md** - Quick reference guide
- **test_api.py** - API testing script
- **README.md** - Updated with Docker deployment info

## 🎯 How to Deploy

### Step 1: Build the Docker Image

```bash
cd /Users/ted.tedford/Public/MyLocalRepos/dockerized-defect-detect/clf-analysis
docker build -t clf-abp-path-analysis:latest .
```

### Step 2: Start the Service

```bash
# Start the service - it will join the defect-detector-services stack
docker-compose up -d

# Verify all services in the stack
docker ps --filter "name=defect-detector-services"
```

### Step 3: Verify It's Running

```bash
# Check container status
docker ps | grep clf-abp-path-analysis

# Check logs
docker-compose logs -f

# Test health endpoint
curl http://localhost:6300/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "clf-abp-path-analysis",
  "timestamp": "2025-10-08T..."
}
```

## 🧪 Testing the API

### Quick Test

```bash
curl http://localhost:6300/health
```

### Run Test Suite

```bash
python test_api.py
```

### Test Analysis (with your build_id)

```bash
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "holes_interval": 10,
    "create_composite_views": false
  }'
```

**Note:** Replace `271360` with your actual build ID. The analysis may take several minutes.

## 📡 API Endpoints

| Endpoint                   | Method | Description                          |
| -------------------------- | ------ | ------------------------------------ |
| `/health`                  | GET    | Health check                         |
| `/api/analyze`             | POST   | Run analysis (build_id in JSON body) |
| `/api/builds/{id}/analyze` | POST   | Run analysis (build_id in URL)       |

## 🔧 Configuration

### Port

- **Host Port:** 6300
- **Container Port:** 6300
- Change in `docker-compose.yml` if needed

### Volume Mounts

- **MIDAS Data:** `/Users/ted.tedford/Documents/MIDAS` (macOS)
- **Code:** `.:/app` (for development)

**For Windows:** Change volume mount to:

```yaml
- "C:/public/shared/DefectDetectorBuilds:/Users/ted.tedford/Documents/MIDAS"
```

### Environment Variables

```yaml
FLASK_ENV: production
FLASK_DEBUG: "False"
PORT: 6300
```

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs clf-abp-path-analysis

# Rebuild
docker-compose build clf-abp-path-analysis
docker-compose up -d clf-abp-path-analysis
```

### Port already in use

```bash
# Find what's using port 6300
lsof -ti:6300

# Kill it
lsof -ti:6300 | xargs kill -9
```

### Can't connect to API

```bash
# Verify container is running
docker ps | grep clf-abp-path-analysis

# Check if port is exposed
docker port clf-abp-path-analysis

# Test from inside container
docker exec -it clf-abp-path-analysis curl http://localhost:6300/health
```

### Analysis fails

```bash
# Check if build files exist
docker exec -it clf-abp-path-analysis ls /Users/ted.tedford/Documents/MIDAS/271360

# Check permissions
docker exec -it clf-abp-path-analysis ls -la /Users/ted.tedford/Documents/MIDAS

# View detailed logs
docker-compose logs -f clf-abp-path-analysis
```

## 📊 Service Status

Once running, the service is part of the `defect-detector-services` stack:

| Service                 | Port | Status      |
| ----------------------- | ---- | ----------- |
| database-python-handler | 6100 | ✅ Existing |
| clf-abp-path-analysis        | 6300 | ✅ **NEW**  |

Both services share the `defectdetect-database_default` network.

## 🔄 Common Operations

```bash
# Start service
docker-compose up -d clf-abp-path-analysis

# Stop service
docker-compose stop clf-abp-path-analysis

# Restart service
docker-compose restart clf-abp-path-analysis

# View logs (follow)
docker-compose logs -f clf-abp-path-analysis

# View logs (last 50 lines)
docker-compose logs --tail=50 clf-abp-path-analysis

# Rebuild and restart
docker-compose up -d --build clf-abp-path-analysis

# Remove service
docker-compose down clf-abp-path-analysis

# Shell into container
docker exec -it clf-abp-path-analysis bash
```

## 🎉 Next Steps

1. **Build the image** ⬆️ (Step 1 above)
2. **Start the service** ⬆️ (Step 2 above)
3. **Test it works** ⬆️ (Step 3 above)
4. **Run your first analysis** 🚀

Example:

```bash
curl -X POST http://localhost:6300/api/builds/YOUR_BUILD_ID/analyze \
  -H "Content-Type: application/json" \
  -d '{"holes_interval": 10}'
```

## 📚 Full Documentation

- **Complete API Docs:** [CLF_ANALYSIS_API_README.md](CLF_ANALYSIS_API_README.md)
- **Quick Reference:** [API_QUICKSTART.md](API_QUICKSTART.md)
- **Main README:** [README.md](README.md)
- **Docker Guide:** [ADDING_SERVICES.md](ADDING_SERVICES.md)

## ✨ Features

✅ RESTful API with JSON responses  
✅ Docker containerized  
✅ Port 6300 (configurable)  
✅ Automatic restarts  
✅ CORS enabled  
✅ Health check endpoint  
✅ Comprehensive error handling  
✅ Volume mounts for MIDAS data  
✅ Network integration with other services  
✅ Production-ready configuration

## 🤝 Integration Example

```python
import requests

# From another service
response = requests.post(
    'http://clf-abp-path-analysis:6300/api/analyze',
    json={'build_id': '271360', 'holes_interval': 10}
)

if response.status_code == 200:
    result = response.json()
    print(f"Analysis complete: {result['result']['output_dir']}")
else:
    print(f"Error: {response.json()['message']}")
```

---

**Questions or issues?** Check the logs: `docker-compose logs -f clf-abp-path-analysis`
