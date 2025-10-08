# 🚀 CLF ABP Path Analysis API - Quick Usage Guide

## ⚡ Important: Async Processing

The API uses **asynchronous processing**:

1. POST request returns immediately with a `job_id` (HTTP 202)
2. Analysis runs in the background
3. Check status using GET `/api/jobs/{job_id}`

**See [API_ASYNC_GUIDE.md](API_ASYNC_GUIDE.md) for complete async workflow documentation.**

---

## Service is Running! ✅

The service is now available at **http://localhost:6300**

**CORS Enabled** for defect-detect-fe (port 6200) ✅

---

## How to Call the API

### Method 1: Build ID in URL (Recommended)

This is the simplest way - just put the build_id in the URL:

```bash
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (Immediate - HTTP 202):**

```json
{
  "status": "accepted",
  "job_id": "1af4b0c8-3daf-49f5-9773-7f8718265476",
  "build_id": "271360",
  "message": "Analysis started for build 271360",
  "check_status_url": "/api/jobs/1af4b0c8-3daf-49f5-9773-7f8718265476"
}
```

**Then check status:**

```bash
curl http://localhost:6300/api/jobs/1af4b0c8-3daf-49f5-9773-7f8718265476
```

**With optional parameters:**

```bash
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "holes_interval": 10,
    "create_composite_views": false
  }'
```

### Method 2: Build ID in JSON Body

```bash
curl -X POST http://localhost:6300/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "271360",
    "holes_interval": 10,
    "create_composite_views": false
  }'
```

## Parameters

| Parameter                | Type    | Required | Default | Description                                        |
| ------------------------ | ------- | -------- | ------- | -------------------------------------------------- |
| `build_id`               | string  | ✅ Yes   | -       | The build ID to analyze (e.g., "271360", "271726") |
| `holes_interval`         | number  | No       | 10      | Interval in mm for creating holes views            |
| `create_composite_views` | boolean | No       | false   | Whether to create composite platform views         |

## Example Calls

### Minimal - Just analyze a build

```bash
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{}'
```

### With holes interval

```bash
curl -X POST http://localhost:6300/api/builds/271726/analyze \
  -H "Content-Type: application/json" \
  -d '{"holes_interval": 15}'
```

### Full parameters

```bash
curl -X POST http://localhost:6300/api/builds/271979/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "holes_interval": 20,
    "create_composite_views": true
  }'
```

## Response Format

### Success Response

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

### Error Response

```json
{
  "status": "error",
  "message": "ABP file not found: /Users/ted.tedford/Documents/MIDAS/271360/preprocess build-271360.abp"
}
```

## Output Location

Results are saved to:

```
/Users/ted.tedford/Documents/MIDAS/{build_id}/clf_analysis/
```

For example, for build 271360:

```
/Users/ted.tedford/Documents/MIDAS/271360/
└── clf_analysis/
    ├── platform_info.json          # Analysis summary
    ├── output/                     # Main output directory
    ├── layer_partials/            # Layer-by-layer partials
    ├── composite_platforms/       # Composite views
    ├── identifier_views/          # Identifier-specific views
    ├── clean_platforms/           # Clean platform images
    └── holes_views/               # Hole detection views
```

## Using from Python

```python
import requests

# Simple analysis
response = requests.post(
    'http://localhost:6300/api/builds/271360/analyze',
    json={}
)

print(response.json())

# With parameters
response = requests.post(
    'http://localhost:6300/api/builds/271726/analyze',
    json={
        'holes_interval': 15,
        'create_composite_views': True
    }
)

result = response.json()
if result['status'] == 'success':
    print(f"Analysis completed in {result['result']['duration_seconds']:.2f} seconds")
    print(f"Output: {result['result']['output_dir']}")
else:
    print(f"Error: {result['message']}")
```

## Using from JavaScript

```javascript
// Simple analysis
fetch("http://localhost:6300/api/builds/271360/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({}),
})
  .then((res) => res.json())
  .then((data) => console.log(data));

// With parameters
fetch("http://localhost:6300/api/builds/271726/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    holes_interval: 15,
    create_composite_views: true,
  }),
})
  .then((res) => res.json())
  .then((data) => {
    if (data.status === "success") {
      console.log("Analysis completed:", data.result);
    } else {
      console.error("Error:", data.message);
    }
  });
```

## Health Check

Always available to check if the service is running:

```bash
curl http://localhost:6300/health
```

Response:

```json
{
  "status": "healthy",
  "service": "clf-abp-path-analysis",
  "timestamp": "2025-10-08T21:17:47.767376"
}
```

## Service Management

```bash
# View logs
docker-compose logs -f

# Restart service
docker-compose restart

# Stop service
docker-compose stop

# Start service
docker-compose up -d
```

## Tips

1. **Analysis time**: Analysis can take several minutes depending on build size
2. **Build files**: Ensure the build folder exists at `/Users/ted.tedford/Documents/MIDAS/{build_id}/`
3. **ABP file**: The service looks for `preprocess build-{build_id}.abp`
4. **Concurrent requests**: The service supports multiple concurrent analyses
5. **Timeout**: Set appropriate timeout in your HTTP client (suggest 10+ minutes)

## Troubleshooting

### Build not found

```bash
# Check if build folder exists
ls -la /Users/ted.tedford/Documents/MIDAS/271360/

# Check for ABP file
ls -la /Users/ted.tedford/Documents/MIDAS/271360/*.abp
```

### Service not responding

```bash
# Check if container is running
docker ps | grep clf-abp-path-analysis

# Check logs
docker-compose logs

# Restart service
docker-compose restart
```

### Permission errors

```bash
# Verify MIDAS directory permissions
ls -la /Users/ted.tedford/Documents/MIDAS/
```
