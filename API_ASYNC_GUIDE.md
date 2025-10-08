# 🚀 CLF ABP Path Analysis API - Usage Guide (ASYNC)

## 🎯 New Async Workflow

The API now uses **asynchronous processing**. When you trigger an analysis:
1. You get an **immediate response** with a `job_id`
2. The analysis runs in the **background**
3. You **check the status** using the `job_id`

This allows the frontend to:
- Know the analysis was successfully triggered
- Not wait for the long-running process
- Check status and get results when ready

---

## Service Status ✅

- **URL**: http://localhost:6300
- **CORS**: Configured for defect-detect-fe (port 6200)
- **Processing**: Asynchronous (non-blocking)

---

## 📡 API Endpoints

### 1. Trigger Analysis (Returns Immediately)

**Method 1: Build ID in URL (Recommended)**
```bash
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Method 2: Build ID in JSON Body**
```bash
curl -X POST http://localhost:6300/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "271360",
    "holes_interval": 10,
    "create_composite_views": false
  }'
```

**Response (HTTP 202 Accepted):**
```json
{
  "status": "accepted",
  "job_id": "1af4b0c8-3daf-49f5-9773-7f8718265476",
  "build_id": "271360",
  "message": "Analysis started for build 271360",
  "check_status_url": "/api/jobs/1af4b0c8-3daf-49f5-9773-7f8718265476"
}
```

### 2. Check Job Status

```bash
curl http://localhost:6300/api/jobs/{job_id}
```

**Example:**
```bash
curl http://localhost:6300/api/jobs/1af4b0c8-3daf-49f5-9773-7f8718265476
```

**Response (Queued):**
```json
{
  "status": "success",
  "job": {
    "job_id": "1af4b0c8-3daf-49f5-9773-7f8718265476",
    "build_id": "271360",
    "status": "queued",
    "started_at": "2025-10-08T21:24:54.428518",
    "holes_interval": 10,
    "create_composite_views": false
  }
}
```

**Response (Running):**
```json
{
  "status": "success",
  "job": {
    "job_id": "1af4b0c8-3daf-49f5-9773-7f8718265476",
    "build_id": "271360",
    "status": "running",
    "started_at": "2025-10-08T21:24:54.428518",
    "holes_interval": 10,
    "create_composite_views": false
  }
}
```

**Response (Completed):**
```json
{
  "status": "success",
  "job": {
    "job_id": "1af4b0c8-3daf-49f5-9773-7f8718265476",
    "build_id": "271360",
    "status": "completed",
    "started_at": "2025-10-08T21:24:54.428518",
    "holes_interval": 10,
    "create_composite_views": false,
    "result": {
      "success": true,
      "build_id": "271360",
      "duration_seconds": 145.23,
      "output_dir": "/Users/ted.tedford/Documents/MIDAS/271360/clf_analysis",
      "summary_path": "/Users/ted.tedford/Documents/MIDAS/271360/clf_analysis/platform_info.json"
    }
  }
}
```

**Response (Failed):**
```json
{
  "status": "success",
  "job": {
    "job_id": "1af4b0c8-3daf-49f5-9773-7f8718265476",
    "build_id": "271360",
    "status": "failed",
    "started_at": "2025-10-08T21:24:54.428518",
    "error": "ABP file not found: /Users/ted.tedford/Documents/MIDAS/271360/preprocess build-271360.abp"
  }
}
```

### 3. List All Jobs

```bash
curl http://localhost:6300/api/jobs
```

**Response:**
```json
{
  "status": "success",
  "count": 3,
  "jobs": [
    {
      "job_id": "uuid-1",
      "build_id": "271360",
      "status": "completed",
      "started_at": "2025-10-08T21:20:00"
    },
    {
      "job_id": "uuid-2",
      "build_id": "271726",
      "status": "running",
      "started_at": "2025-10-08T21:24:54"
    }
  ]
}
```

### 4. Health Check

```bash
curl http://localhost:6300/health
```

---

## 🔄 Typical Workflow

### Frontend Integration

```javascript
// 1. Trigger analysis
const triggerResponse = await fetch('http://localhost:6300/api/builds/271360/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ holes_interval: 10 })
});

const { job_id, status } = await triggerResponse.json();

if (status === 'accepted') {
  console.log('Analysis started!', job_id);
  
  // 2. Poll for status (every 5 seconds)
  const intervalId = setInterval(async () => {
    const statusResponse = await fetch(`http://localhost:6300/api/jobs/${job_id}`);
    const { job } = await statusResponse.json();
    
    console.log('Status:', job.status);
    
    if (job.status === 'completed') {
      clearInterval(intervalId);
      console.log('Analysis complete!', job.result);
      // Update UI with results
    } else if (job.status === 'failed') {
      clearInterval(intervalId);
      console.error('Analysis failed:', job.error);
      // Show error to user
    }
  }, 5000); // Poll every 5 seconds
}
```

### Python Integration

```python
import requests
import time

# 1. Trigger analysis
response = requests.post(
    'http://localhost:6300/api/builds/271360/analyze',
    json={'holes_interval': 10}
)

data = response.json()
job_id = data['job_id']

print(f"Analysis started: {job_id}")

# 2. Poll for completion
while True:
    status_response = requests.get(f'http://localhost:6300/api/jobs/{job_id}')
    job_data = status_response.json()['job']
    
    print(f"Status: {job_data['status']}")
    
    if job_data['status'] == 'completed':
        print("Analysis complete!")
        print(f"Output: {job_data['result']['output_dir']}")
        break
    elif job_data['status'] == 'failed':
        print(f"Analysis failed: {job_data['error']}")
        break
    
    time.sleep(5)  # Wait 5 seconds before checking again
```

---

## 📊 Job Status States

| Status | Description |
|--------|-------------|
| `queued` | Job created, waiting to start |
| `running` | Analysis is currently running |
| `completed` | Analysis finished successfully |
| `failed` | Analysis encountered an error |

---

## 🎯 Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `build_id` | ✅ Yes | - | Build ID (e.g., "271360") |
| `holes_interval` | No | 10 | Interval in mm for holes views |
| `create_composite_views` | No | false | Create composite platform views |

---

## 📍 Output Location

Results saved to: `/Users/ted.tedford/Documents/MIDAS/{build_id}/clf_analysis/`

---

## 🌐 CORS Configuration

The API is configured to accept requests from:
- `http://localhost:6200` (defect-detect-fe)
- `http://127.0.0.1:6200`
- `http://defect-detect-fe:6200` (Docker network)

---

## 🧪 Testing

### Quick Test
```bash
# 1. Trigger
curl -X POST http://localhost:6300/api/builds/271360/analyze \
  -H "Content-Type: application/json" \
  -d '{}'

# Response: {"job_id": "...", "status": "accepted", ...}

# 2. Check status (use job_id from above)
curl http://localhost:6300/api/jobs/{job_id}
```

### Test from Frontend
```bash
# From defect-detect-fe, this should work without CORS errors:
fetch('http://localhost:6300/api/builds/271360/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({})
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## ⚡ Advantages of Async Processing

1. **Immediate Feedback** - Frontend knows the job started immediately
2. **No Timeout Issues** - Long-running analyses don't cause HTTP timeouts
3. **Better UX** - Can show progress/status to users
4. **Scalability** - Multiple analyses can run concurrently
5. **Error Handling** - Can check for errors after the fact

---

## 💡 Best Practices

1. **Poll, don't spam** - Check status every 5-10 seconds, not every second
2. **Handle all states** - queued, running, completed, failed
3. **Timeout eventually** - If no completion after X minutes, assume failure
4. **Store job_id** - Save it in your app state/database for tracking
5. **User feedback** - Show loading indicator while `running`

---

## 🐛 Troubleshooting

### Job stays in "queued" forever
```bash
# Check logs
docker-compose logs -f

# The analysis thread might not have started
```

### Job not found
```bash
# Job IDs are stored in memory - they're lost if container restarts
# Store job_id in your database if you need persistence
```

### CORS errors from frontend
```bash
# Verify the frontend is on port 6200
# Check browser console for the exact origin
# If needed, add more origins to clf_analysis_api.py
```

---

## 📚 See Also

- [CLF_ANALYSIS_API_README.md](CLF_ANALYSIS_API_README.md) - Full documentation
- [API_QUICKSTART.md](API_QUICKSTART.md) - Quick reference
