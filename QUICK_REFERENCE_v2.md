# GMD Tool v2.0 – Quick Reference Guide

## 🚀 Endpoints Overview

### Single Location Search
```
POST /search
```
**Best for:** 1 location, simple search

**Request:**
```json
{
  "keyword": "restaurants",
  "location": "Delhi",
  "use_expansion": false,
  "fetch_websites": false
}
```

**Response:** `200 OK` with results array
**Time:** 30-50 seconds

---

### Multi-Location Parallel Search
```
POST /search-multiple
```
**Best for:** 2-5 locations, quick search

**Request:**
```json
{
  "keyword": "restaurants",
  "locations": "Delhi, Mumbai, Bangalore",
  "use_expansion": false,
  "fetch_websites": false
}
```

**Response:** `200 OK` with results by location
**Time:** 50-80 seconds

---

### Batch Processing (FREE TIER SAFE)
```
POST /search-batch
```
**Best for:** 6+ locations, guaranteed completion

**Request:**
```json
{
  "session_id": "optional-id",
  "keyword": "restaurants",
  "locations": ["Delhi", "Mumbai", "Bangalore", "Pune", "Hyderabad"],
  "batch_size": 2,
  "batch_index": 0,
  "use_expansion": false,
  "fetch_websites": false
}
```

**Response:** `200 OK` with partial results + progress
**Time:** 40-50 seconds per batch

**Flow:**
```
Batch 0 (Locs 1-2) → Returns progress
→ Batch 1 (Locs 3-4) → Returns progress
→ Batch 2 (Locs 5+) → Returns progress
```

---

### Batch Status Check
```
GET /batch-status/<session_id>
```
**Best for:** Checking progress mid-batch

**Response:**
```json
{
  "session_id": "batch_123...",
  "progress": {
    "current_batch": 2,
    "total_batches": 3,
    "locations_completed": 4,
    "total_locations": 6,
    "percent_complete": 66.7
  }
}
```

---

### Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "ok",
  "api_key_configured": true,
  "scraper_ready": true
}
```

---

### Get Metrics
```
GET /metrics
```
**Response:**
```json
{
  "searches_completed": 10,
  "total_api_calls": 50,
  "cache_hits": 12,
  "duplicates_removed": 5
}
```

---

## 💻 Common Code Examples

### Python - Batch Search
```python
import requests
import time

def batch_search(keyword, locations, base_url="http://localhost:5000"):
    session_id = None
    all_results = {}
    batch_index = 0
    
    while True:
        response = requests.post(
            f"{base_url}/search-batch",
            json={
                "session_id": session_id,
                "keyword": keyword,
                "locations": locations,
                "batch_size": 2,
                "batch_index": batch_index,
                "fetch_websites": False
            }
        )
        
        if response.status_code != 200:
            print(f"Error: {response.json()}")
            break
        
        data = response.json()
        
        # Store session ID
        if not session_id:
            session_id = data["session_id"]
        
        # Accumulate results
        all_results.update(data["batch_results"])
        
        # Print progress
        progress = data["progress"]
        print(f"{progress['percent_complete']}% - "
              f"{progress['locations_completed']}/{progress['total_locations']} done")
        
        # Check if done
        if not data["has_next_batch"]:
            break
        
        # Wait between batches
        time.sleep(1)
        batch_index = data["next_batch_index"]
    
    return all_results

# Usage
results = batch_search("restaurants", ["Delhi", "Mumbai", "Bangalore"])
print(f"Total results: {sum(len(v.get('results', [])) for v in results.values())}")
```

### JavaScript - Auto-Batch Search
```javascript
async function smartSearch(keyword, locations) {
    // Auto-detects size and routes appropriately
    
    if (locations.length <= 5) {
        // Traditional parallel
        return await fetch('/search-multiple', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keyword: keyword,
                locations: locations.join(", "),
                fetch_websites: false
            })
        }).then(r => r.json());
    } else {
        // Batch processing
        let sessionId = null;
        let allResults = {};
        
        for (let batchIdx = 0; ; batchIdx++) {
            const response = await fetch('/search-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    keyword: keyword,
                    locations: locations,
                    batch_size: 2,
                    batch_index: batchIdx,
                    fetch_websites: false
                })
            });
            
            const data = await response.json();
            sessionId = data.session_id;
            Object.assign(allResults, data.batch_results);
            
            console.log(`${data.progress.percent_complete}% complete`);
            
            if (!data.has_next_batch) break;
            await new Promise(r => setTimeout(r, 1000));
        }
        
        return { results: allResults };
    }
}
```

### cURL - Batch Processing
```bash
# Start batch
SESSION_ID=$(curl -s -X POST http://localhost:5000/search-batch \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "locations": ["Delhi", "Mumbai", "Bangalore", "Pune"],
    "batch_size": 2,
    "batch_index": 0
  }' | jq -r '.session_id')

echo "Session: $SESSION_ID"

# Continue batch
curl -X POST http://localhost:5000/search-batch \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"keyword\": \"restaurants\",
    \"locations\": [\"Delhi\", \"Mumbai\", \"Bangalore\", \"Pune\"],
    \"batch_size\": 2,
    \"batch_index\": 1
  }"

# Check status
curl http://localhost:5000/batch-status/$SESSION_ID
```

---

## ⚙️ Configuration Quick Tuning

### For Maximum Stability
```bash
MAX_WORKERS=2
MAX_CONCURRENT_API_CALLS=3
MIN_DELAY_BETWEEN_API_CALLS=0.5
FETCH_WEBSITES_BY_DEFAULT=false
```

### For Balanced Performance
```bash
MAX_WORKERS=3
MAX_CONCURRENT_API_CALLS=5
MIN_DELAY_BETWEEN_API_CALLS=0.2
FETCH_WEBSITES_BY_DEFAULT=false
```

### For Maximum Performance
```bash
MAX_WORKERS=5
MAX_CONCURRENT_API_CALLS=8
MIN_DELAY_BETWEEN_API_CALLS=0.1
FETCH_WEBSITES_BY_DEFAULT=true
```

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| 502 Bad Gateway | Timeout on Render | Reduce `MAX_WORKERS` to 2 |
| 502 Bad Gateway | High memory | Disable website fetching |
| Empty results | Invalid location | Check Google Places spelling |
| Slow responses | Quota exhausted | Wait 100s or increase delay |
| Memory spike | Large result set | Reduce `MAX_PAGES_PER_SEARCH` to 2 |

---

## 📊 Performance Targets

### Render Free Tier
| Scenario | Target | Actual |
|----------|--------|--------|
| 1 location | <50s | 35-45s ✅ |
| 5 locations | <80s | 60-75s ✅ |
| 10 locations | <5min | 3-4min ✅ |
| 20 locations | <10min | 6-8min ✅ |
| Memory peak | <150MB | 90-110MB ✅ |

---

## 🔐 Environment Variables

```bash
# Required
GOOGLE_MAPS_API_KEY=your_key

# Recommended
MAX_WORKERS=3
MAX_CONCURRENT_API_CALLS=5
MIN_DELAY_BETWEEN_API_CALLS=0.2
CACHE_ENABLED=true
FETCH_WEBSITES_BY_DEFAULT=false
DEBUG_MODE=false

# Optional
MAX_PAGES_PER_SEARCH=3
MAX_RESULTS_PER_LOCATION=60
REQUEST_TIMEOUT=20
```

---

## 🚀 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Render.com service created
- [ ] Environment variables set
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `gunicorn -w 1 -b 0.0.0.0:$PORT app:app`
- [ ] Deployment triggered
- [ ] `/health` endpoint responds
- [ ] Test batch with 3-5 locations
- [ ] Test batch with 10+ locations
- [ ] No 502 errors in logs
- [ ] Results match expectations

---

## 📈 Monitoring

### Check Health
```bash
curl https://gmd-tool.onrender.com/health
```

### View Metrics
```bash
curl https://gmd-tool.onrender.com/metrics | jq
```

### Get Configuration
```bash
curl https://gmd-tool.onrender.com/config | jq
```

### Test Batch
```bash
curl -X POST https://gmd-tool.onrender.com/search-batch \
  -H "Content-Type: application/json" \
  -d '{"keyword":"restaurants","locations":["Delhi","Mumbai"],"batch_size":2,"batch_index":0}'
```

---

## 📚 Full Documentation

- **`BATCH_PROCESSING_GUIDE.md`** - Complete batch system docs
- **`DEPLOYMENT_GUIDE.md`** - Render deployment steps
- **`TESTING_GUIDE_v2.md`** - Full test suite
- **`USAGE_GUIDE.md`** - User documentation

---

**Ready to search millions of leads? You're all set! 🚀**
