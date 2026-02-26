# GMD Tool v2.0 – Comprehensive Testing Guide

## 🧪 Overview

This guide provides comprehensive tests to validate the batch processing system, performance optimizations, and free-tier compatibility.

---

## ✅ Pre-Deployment Tests (Local)

### Test 1: Single Location Search
**Objective**: Verify basic search functionality

```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "location": "Delhi",
    "use_expansion": false,
    "fetch_websites": false
  }'
```

**Expected:**
- Status: 200 OK
- Response includes "results" array
- Results contain: name, rating, reviews_count
- Execution time: 30-45 seconds

---

### Test 2: Single Location with Expansion
**Objective**: Verify geo-grid expansion works

```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "location": "Delhi",
    "use_expansion": true,
    "fetch_websites": false
  }'
```

**Expected:**
- Status: 200 OK
- Response includes "expanded_locations" array (9 areas)
- "total_unique_results" > 60
- Execution time: 3-5 minutes

---

### Test 3: Batch Processing - First Batch
**Objective**: Verify new batch endpoint

```bash
curl -X POST http://localhost:5000/search-batch \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "locations": ["Delhi", "Mumbai", "Bangalore"],
    "batch_size": 2,
    "batch_index": 0,
    "use_expansion": false,
    "fetch_websites": false
  }'
```

**Expected:**
- Status: 200 OK
- Response includes "session_id"
- "batch_results" contains 2 locations (Delhi, Mumbai)
- "progress" shows: current_batch=1, total_batches=2
- "has_next_batch": true
- Execution time: 35-45 seconds

---

### Test 4: Batch Processing - Second Batch
**Objective**: Verify batch continuation

```bash
curl -X POST http://localhost:5000/search-batch \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session-id-from-test-3>",
    "keyword": "restaurants",
    "locations": ["Delhi", "Mumbai", "Bangalore"],
    "batch_size": 2,
    "batch_index": 1,
    "use_expansion": false,
    "fetch_websites": false
  }'
```

**Expected:**
- Status: 200 OK
- "batch_results" contains 1 location (Bangalore)
- "progress" shows: current_batch=2, total_batches=2
- "has_next_batch": false
- "next_batch_index": null

---

### Test 5: Batch Status Check
**Objective**: Verify session status endpoint

```bash
curl http://localhost:5000/batch-status/<session-id>
```

**Expected:**
- Status: 200 OK
- Response includes "progress" with current stats
- "metadata" contains original request parameters

---

### Test 6: Traditional Search-Multiple
**Objective**: Verify fallback for small requests

```bash
curl -X POST http://localhost:5000/search-multiple \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "locations": "Delhi, Mumbai",
    "use_expansion": false,
    "fetch_websites": false
  }'
```

**Expected:**
- Status: 200 OK
- "locations_completed": 2
- "results" contains both locations
- Execution time: 50-70 seconds

---

### Test 7: Health Check
**Objective**: Verify system is ready

```bash
curl http://localhost:5000/health
```

**Expected:**
```json
{
  "status": "ok",
  "version": "2.0",
  "api_key_configured": true,
  "scraper_ready": true,
  "features": {
    "geo_expansion": true,
    "caching": true,
    "website_fetching": false,
    "parallel_requests": true
  }
}
```

---

### Test 8: Metrics
**Objective**: Verify metrics collection

```bash
curl http://localhost:5000/metrics
```

**Expected:**
```json
{
  "searches_completed": 3,
  "total_api_calls": 12,
  "total_results_fetched": 150,
  "duplicates_removed": 25,
  "cache_hits": 2,
  "api_calls_per_minute": 4.5,
  "cache_stats": {...}
}
```

---

### Test 9: Caching Verification
**Objective**: Verify cache improves performance

```bash
# First search - cache miss
time curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "location": "Delhi",
    "use_expansion": false
  }'
# Expected: ~35s

# Second search - cache hit
time curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "location": "Delhi",
    "use_expansion": false
  }'
# Expected: ~0.5s (from cache)
```

---

## 📊 Performance Tests

### Test 10: Memory Usage Under Load
**Objective**: Verify memory stays under 150MB on free tier

```python
import requests
import psutil
import os
import time

process = psutil.Process(os.getpid())

def get_memory_mb():
    return process.memory_info().rss / 1024 / 1024

# Monitor during batch search
initial_memory = get_memory_mb()
print(f"Initial memory: {initial_memory:.1f}MB")

# Make batch requests
for batch in range(3):
    response = requests.post('http://localhost:5000/search-batch', json={
        "keyword": "restaurants",
        "locations": ["Delhi", "Mumbai", "Bangalore", "Pune", "Hyderabad"],
        "batch_size": 2,
        "batch_index": batch,
        "fetch_websites": False
    })
    
    current_memory = get_memory_mb()
    print(f"Batch {batch}: {current_memory:.1f}MB (delta: {current_memory-initial_memory:+.1f}MB)")
    time.sleep(1)

final_memory = get_memory_mb()
print(f"Final memory: {final_memory:.1f}MB")
print(f"Peak increase: {final_memory-initial_memory:.1f}MB")
```

**Expected:**
- Peak memory < 150MB
- GC keeps memory stable
- No memory leaks across batches

---

### Test 11: Response Time Under Load
**Objective**: Verify batch processing meets timeout requirements

```python
import requests
import time

locations = ["Delhi", "Mumbai", "Bangalore", "Pune", "Hyderabad", 
             "Kolkata", "Chennai", "Jaipur", "Lucknow"]

session_id = None
total_time = 0

for batch_index in range(5):
    start = time.time()
    
    response = requests.post('http://localhost:5000/search-batch', json={
        "session_id": session_id,
        "keyword": "restaurants",
        "locations": locations,
        "batch_size": 2,
        "batch_index": batch_index,
        "fetch_websites": False
    })
    
    batch_time = time.time() - start
    total_time += batch_time
    data = response.json()
    
    if not session_id:
        session_id = data['session_id']
    
    print(f"Batch {batch_index + 1}: {batch_time:.1f}s - {data['progress']['percent_complete']}% complete")

print(f"Total time for 9 locations: {total_time:.1f}s")
```

**Expected:**
- Each batch: 35-45 seconds (< 120s timeout)
- Total for 9 locations: 3-4.5 minutes
- All batches complete successfully

---

### Test 12: Quota Handling
**Objective**: Verify exponential backoff on quota limit

```python
import requests
import time

# Keep sending requests until quota limit hit
for i in range(30):
    print(f"Request {i + 1}...", end=" ", flush=True)
    
    response = requests.post('http://localhost:5000/search', json={
        "keyword": f"restaurants_{i}",
        "location": "Delhi",
        "use_expansion": False,
        "fetch_websites": False
    })
    
    if response.status_code == 200:
        print("OK")
    else:
        print(f"Error: {response.status_code}")
    
    time.sleep(1)
```

**Expected:**
- First 60 requests: All succeed
- After quota: API responds with OVER_QUERY_LIMIT
- Backend automatically backs off
- Requests eventually recover after backoff

---

## 🌐 Frontend Tests

### Test 13: Single Location Search (UI)
**Objective**: Verify UI for 1 location

1. Open `http://localhost:5000`
2. Enter: Keyword "restaurants", Location "Delhi"
3. Click "Search"

**Expected:**
- Results appear after 40-50s
- No loader spinner after completion
- Results show name, rating, reviews
- Website link appears if available

---

### Test 14: Small Batch (UI)
**Objective**: Verify UI uses traditional search for small batches

1. Open `http://localhost:5000`
2. Enter: Keyword "restaurants", Locations "Delhi, Mumbai, Bangalore"
3. Click "Search Multiple"

**Expected:**
- Uses `/search-multiple` endpoint
- All results appear within 60-80 seconds
- No 502 errors
- Results table shows all locations

---

### Test 15: Large Batch (UI)
**Objective**: Verify UI uses batch processing for large requests

1. Open `http://localhost:5000`
2. Enter: Keyword "restaurants", Locations "Delhi, Mumbai, Bangalore, Pune, Hyderabad, Kolkata, Chennai, Jaipur" (8 locations)
3. Click "Search Multiple"

**Expected:**
- Uses `/search-batch` endpoint automatically
- Progress updates show: "X/8 locations (Batch Y/Z)"
- Results progressively appear
- No 502 errors
- Complete results within 3-5 minutes

---

### Test 16: Progress Tracking (UI)
**Objective**: Verify progress indicator accuracy

During large batch search:
1. Watch progress text update
2. Verify percentage increases
3. Verify result count increases progressively
4. Verify completion percentage reaches 100%

**Expected:**
- Progress text updates every 1-2 seconds
- Percentage is accurate (actual/total * 100)
- More results appear as batches complete

---

### Test 17: Error Handling (UI)
**Objective**: Verify error messages appear correctly

1. Try search with invalid location (e.g., "ZZZZZNotALocationZZZZ")
2. Watch for error message

**Expected:**
- Error alert appears after 30-40 seconds
- Message: "No results found" or similar
- UI remains responsive
- Can try again

---

### Test 18: Website Link Extraction (UI)
**Objective**: Verify website links are extracted

1. Enable "Fetch Websites" in results
2. Run search for 1-2 locations
3. Check results for website URLs

**Expected:**
- Website column shows URLs
- URLs are clickable links
- Some businesses have websites, some don't
- Links work when clicked

---

## 🚀 Load Tests

### Test 19: Concurrent Batch Requests
**Objective**: Verify system handles multiple concurrent batch requests

```python
import requests
import threading
import time

def run_batch_search(location_group, group_id):
    try:
        response = requests.post('http://localhost:5000/search-batch', json={
            "keyword": "restaurants",
            "locations": location_group,
            "batch_size": 2,
            "batch_index": 0,
            "fetch_websites": False
        })
        print(f"Group {group_id}: {response.status_code} - {len(response.json().get('batch_results', {}))} results")
    except Exception as e:
        print(f"Group {group_id}: Error - {e}")

# Run 3 batch searches concurrently
threads = []
for i in range(3):
    locations = ["Delhi", "Mumbai"] if i % 2 == 0 else ["Bangalore", "Pune"]
    t = threading.Thread(target=run_batch_search, args=(locations, i))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("All concurrent requests completed")
```

**Expected:**
- All requests complete successfully
- No request hangs
- No 502 errors
- Results are accurate for each request

---

### Test 20: Connection Pool Effectiveness
**Objective**: Verify connection pooling improves performance

```python
import requests
import time

session = requests.Session()

# First request (creates connections)
start = time.time()
for i in range(5):
    response = session.post('http://localhost:5000/search-batch', json={
        "keyword": f"restaurants_{i}",
        "locations": ["Delhi", "Mumbai"],
        "batch_size": 2,
        "batch_index": 0,
        "fetch_websites": False
    })
first_batch_time = time.time() - start

# Second request (reuses connections)
start = time.time()
for i in range(5, 10):
    response = session.post('http://localhost:5000/search-batch', json={
        "keyword": f"restaurants_{i}",
        "locations": ["Delhi", "Mumbai"],
        "batch_size": 2,
        "batch_index": 0,
        "fetch_websites": False
    })
second_batch_time = time.time() - start

print(f"First batch (new connections): {first_batch_time:.1f}s")
print(f"Second batch (reused connections): {second_batch_time:.1f}s")
print(f"Improvement: {(first_batch_time/second_batch_time - 1) * 100:.1f}% faster")
```

**Expected:**
- Second batch at least 10-20% faster
- Connection reuse working effectively

---

## ✅ Post-Deployment Tests (Render)

### Test 21: Health Check on Render
```bash
curl https://gmd-tool.onrender.com/health
```

**Expected:**
- Status: 200 OK
- All features enabled
- No errors

---

### Test 22: Batch Processing on Render
```bash
curl -X POST https://gmd-tool.onrender.com/search-batch \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "locations": ["Delhi", "Mumbai", "Bangalore"],
    "batch_size": 2,
    "batch_index": 0,
    "fetch_websites": false
  }'
```

**Expected:**
- Status: 200 OK
- Results returned
- No 502 errors
- Execution time: 40-60 seconds

---

### Test 23: Large Batch on Render
**Objective**: Verify free tier can handle unlimited locations

```bash
# Test 15 locations
curl -X POST https://gmd-tool.onrender.com/search-batch \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "locations": [
      "Delhi", "Mumbai", "Bangalore", "Pune", "Hyderabad",
      "Kolkata", "Chennai", "Jaipur", "Lucknow", "Kanpur",
      "Ahmedabad", "Surat", "Vadodara", "Indore", "Nagpur"
    ],
    "batch_size": 2,
    "batch_index": 0,
    "fetch_websites": false
  }'
```

**Expected:**
- Status: 200 OK
- First batch completes in <50 seconds
- No 502/504 errors
- Can continue to next batches

---

## 📝 Test Results Template

```markdown
# GMD Tool v2.0 Test Results

## Environment
- **Deployment**: Local / Render.com
- **Date**: YYYY-MM-DD
- **API Key**: ✅ Configured

## Basic Tests
- [ ] Test 1: Single Location Search - PASS/FAIL
- [ ] Test 2: Single Location with Expansion - PASS/FAIL
- [ ] Test 3: Batch Processing - PASS/FAIL
- [ ] Test 4: Batch Continuation - PASS/FAIL
- [ ] Test 5: Batch Status - PASS/FAIL
- [ ] Test 6: Traditional Multi-Search - PASS/FAIL
- [ ] Test 7: Health Check - PASS/FAIL
- [ ] Test 8: Metrics - PASS/FAIL

## Performance Tests
- [ ] Test 9: Caching - PASS/FAIL
- [ ] Test 10: Memory Usage - PASS/FAIL (Peak: ___MB)
- [ ] Test 11: Response Time - PASS/FAIL (Avg: ___s per batch)
- [ ] Test 12: Quota Handling - PASS/FAIL

## UI Tests
- [ ] Test 13: Single Location UI - PASS/FAIL
- [ ] Test 14: Small Batch UI - PASS/FAIL
- [ ] Test 15: Large Batch UI - PASS/FAIL
- [ ] Test 16: Progress Tracking - PASS/FAIL
- [ ] Test 17: Error Handling - PASS/FAIL
- [ ] Test 18: Website Extraction - PASS/FAIL

## Load Tests
- [ ] Test 19: Concurrent Requests - PASS/FAIL
- [ ] Test 20: Connection Pooling - PASS/FAIL (Speedup: ___%)

## Deployment Tests
- [ ] Test 21: Health Check on Render - PASS/FAIL
- [ ] Test 22: Batch on Render - PASS/FAIL
- [ ] Test 23: Large Batch on Render - PASS/FAIL

## Summary
- **Total Tests**: 23
- **Passed**: __
- **Failed**: __
- **Success Rate**: ___%

## Notes
(Any issues, observations, or improvements noted)
```

---

## 🎯 Success Criteria

✅ **All tests pass** when:
- No 502/504 errors
- All batches complete within timeout
- Memory stays < 150MB
- Results are complete and accurate
- UI is responsive
- Performance is acceptable

---

## 📞 Debugging Failed Tests

If a test fails:

1. **Check health endpoint**
   ```bash
   curl http://localhost:5000/health
   ```

2. **Review logs**
   - Local: Terminal output
   - Render: Dashboard → Logs

3. **Check API key**
   ```bash
   echo $GOOGLE_MAPS_API_KEY
   ```

4. **Check memory**
   ```bash
   ps aux | grep gunicorn  # or
   top  # and look for python process
   ```

5. **Test with simpler request**
   ```bash
   curl http://localhost:5000/health  # Simple test
   ```

---

**🎉 All tests passing? Your GMD Tool is production-ready!**
