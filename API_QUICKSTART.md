# CLF Analysis API - Quick Start

## 🚀 Quick Deploy with Docker

```bash
# 1. Build the image
docker build -t clf-abp-path-analysis:latest .

# 2. Start the service (joins defect-detector-services stack)
docker-compose up -d

# 3. Test it works
curl http://localhost:6300/health
```

## 📡 API Quick Reference

### Run Analysis

```bash
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{"holes_interval": 10}'
```

### Check Health

```bash
curl http://localhost:6300/health
```

## 🛠️ Common Commands

```bash
# View logs
docker-compose logs -f

# Restart service
docker-compose restart

# Stop service
docker-compose stop

# Rebuild and restart
docker-compose up -d --build
```

## 🏗️ Architecture

Part of `defect-detector-services` stack:
- Port 6100: database-python-handler
- Port 6200: defect-detect-fe
- Port 6300: clf-abp-path-analysis (this service)

## 📚 Full Documentation

See [CLF_ANALYSIS_API_README.md](CLF_ANALYSIS_API_README.md) for complete documentation.
