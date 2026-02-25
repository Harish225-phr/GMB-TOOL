# Development & Testing Guide - GMD Tool v2.0

## 🧪 Testing the System

### Phase 1: Installation & Setup

#### 1.1 Prerequisites Check
```bash
# Check Python version
python --version  # Should be 3.8+

# Check pip
pip --version

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or source .venv/bin/activate  # Mac/Linux
```

#### 1.2 Install Dependencies
```bash
# Install from requirements.txt
pip install -r requirements.txt

# Verify installation
python -c "import requests; import flask; print('✅ All dependencies installed')"
```

#### 1.3 Configure API Key
```bash
# Create .env file
echo GOOGLE_MAPS_API_KEY=your_actual_key_here > .env

# Verify it's loaded
python -c "from scraper.config import config; print(f'API Key: {config.GOOGLE_API_KEY[:10]}...')"
```

### Phase 2: Unit Testing

#### 2.1 Test Config Module
```python
# test_config.py
from scraper.config import config, GeoGridAreas

def test_config_loaded():
    """Test configuration is loaded."""
    assert config.GOOGLE_API_KEY != ""
    assert config.MAX_WORKERS > 0
    assert config.MAX_CONCURRENT_API_CALLS > 0
    print("✅ Config test passed")

def test_geo_grids():
    """Test geo-grid definitions."""
    assert GeoGridAreas.has_geo_grid("delhi")
    assert GeoGridAreas.has_geo_grid("mumbai")
    
    delhi_areas = GeoGridAreas.get_areas("delhi")
    assert len(delhi_areas) > 0
    print(f"✅ Geo-grid test passed ({len(delhi_areas)} areas for Delhi)")

if __name__ == "__main__":
    test_config_loaded()
    test_geo_grids()
```

#### 2.2 Test Models
```python
# test_models.py
from scraper.models import BusinessLead, SearchResult

def test_business_lead():
    """Test BusinessLead model."""
    lead = BusinessLead(
        name="Test Restaurant",
        rating=4.5,
        reviews_count=100,
        website="https://example.com"
    )
    
    assert lead.name == "Test Restaurant"
    assert lead.rating == 4.5
    
    dedup_key = lead.get_dedup_key()
    assert len(dedup_key) > 0
    print(f"✅ BusinessLead test passed (dedup_key: {dedup_key[:30]}...)")

def test_search_result():
    """Test SearchResult model."""
    lead1 = BusinessLead(name="Restaurant 1", rating=4.5)
    lead2 = BusinessLead(name="Restaurant 2", rating=4.0)
    
    result = SearchResult(
        keyword="restaurants",
        location="Delhi",
        results=[lead1, lead2],
        total_results_found=2
    )
    
    assert len(result.results) == 2
    result_dict = result.to_dict()
    assert "results" in result_dict
    print("✅ SearchResult test passed")

if __name__ == "__main__":
    test_business_lead()
    test_search_result()
```

#### 2.3 Test API Client
```python
# test_api_client.py
from scraper.api_client import GooglePlacesAPIClient

def test_api_client_init():
    """Test API client initialization."""
    try:
        client = GooglePlacesAPIClient()
        assert client.api_key != ""
        print("✅ API client initialization passed")
    except ValueError as e:
        print(f"❌ API key not configured: {e}")

def test_rate_limiter():
    """Test rate limiter."""
    from scraper.rate_limiter import RateLimiter
    
    limiter = RateLimiter(calls_per_second=10)
    
    # Should not block for first call
    limiter.wait_if_needed()
    
    # Check internals
    assert limiter.tokens <= limiter.max_burst
    print("✅ Rate limiter test passed")

if __name__ == "__main__":
    test_api_client_init()
    test_rate_limiter()
```

#### 2.4 Test Deduplicator
```python
# test_deduplicator.py
from scraper.models import BusinessLead
from scraper.deduplicator import ResultDeduplicator

def test_deduplication():
    """Test deduplication logic."""
    
    # Create duplicate leads
    lead1 = BusinessLead(
        name="ABC Restaurant",
        rating=4.5,
        website="https://abcrestaurant.com"
    )
    lead2 = BusinessLead(
        name="ABC Restaurant",  # Same name
        rating=4.0,
        website="https://abcrestaurant.com"  # Same website
    )
    lead3 = BusinessLead(
        name="XYZ Restaurant",
        rating=3.5,
        website="https://xyzrestaurant.com"
    )
    
    # Group by location
    leads_by_location = {
        "Area1": [lead1, lead3],
        "Area2": [lead2]
    }
    
    dedup = ResultDeduplicator()
    unique, stats = dedup.deduplicate(leads_by_location)
    
    assert len(unique) == 2  # Should have 2 unique (lead2 is dupe of lead1)
    assert stats["duplicates_removed"] == 1
    print(f"✅ Deduplication test passed (removed {stats['duplicates_removed']} duplicates)")

if __name__ == "__main__":
    test_deduplication()
```

### Phase 3: Integration Testing

#### 3.1 Test Geo-Grid Expansion
```python
# test_geo_grid.py
from scraper.geo_grid import GeoGridExpander, SearchLocationManager

def test_geo_grid_expansion():
    """Test geographic grid expansion."""
    
    expander = GeoGridExpander(enable_expansion=True)
    
    # Test automatic expansion
    locations = expander.expand_location("Delhi")
    assert len(locations) > 1
    print(f"✅ Delhi expanded to {len(locations)} locations")
    
    # Test custom grid
    expander.add_custom_grid("TestCity", ["Area1", "Area2", "Area3"])
    locations = expander.expand_location("TestCity")
    assert len(locations) == 4  # TestCity + 3 areas
    print(f"✅ Custom grid test passed ({len(locations)} locations)")
    
    # Test location manager
    manager = SearchLocationManager(expander)
    all_locations = manager.get_search_locations("Mumbai", use_expansion=True)
    assert len(all_locations) > 1
    print(f"✅ Location manager test passed ({len(all_locations)} locations)")

if __name__ == "__main__":
    test_geo_grid_expansion()
```

#### 3.2 Test Caching
```python
# test_cache.py
from scraper.cache_manager import SearchResultCache, CacheKey
import time

def test_cache_basic():
    """Test cache functionality."""
    
    cache = SearchResultCache(default_ttl=2)
    
    # Generate key
    key = CacheKey.generate_search_key("restaurants", "Delhi")
    
    # Set value
    data = {"results": [{"name": "Test"}], "total": 1}
    cache.set(key, data)
    
    # Get value
    result = cache.get(key)
    assert result == data
    print("✅ Cache set/get test passed")
    
    # Test expiration
    time.sleep(2.1)
    result = cache.get(key)
    assert result is None
    print("✅ Cache expiration test passed")
    
    # Test stats
    stats = cache.get_stats()
    assert "hit_ratio_percent" in stats
    print(f"✅ Cache stats test passed (hits: {stats['hits']}, misses: {stats['misses']})")

if __name__ == "__main__":
    test_cache_basic()
```

### Phase 4: System Testing

#### 4.1 Start Flask Server
```bash
# Terminal 1: Start server
python app.py
# Should output: Running on http://127.0.0.1:5000
```

#### 4.2 Health Check
```bash
# Terminal 2: Test health endpoint
curl http://localhost:5000/health

# Expected response:
# {
#   "status": "ok",
#   "version": "2.0",
#   "features": {...}
# }
```

#### 4.3 Configuration Check
```bash
# Get current config
curl http://localhost:5000/config

# Expected: Configuration details
```

#### 4.4 Single Location Search
```bash
# Simple search
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "restaurants",
    "location": "Austin",
    "use_expansion": false,
    "fetch_websites": true
  }'

# Expected: List of restaurants with ratings and websites
```

#### 4.5 Geo-Grid Expansion Search
```bash
# Search with expansion
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "coffee shops",
    "location": "Mumbai",
    "use_expansion": true,
    "fetch_websites": false
  }'

# Expected: Many results from 9 areas, deduplicated
```

#### 4.6 Multi-Location Search
```bash
# Multiple locations in parallel
curl -X POST http://localhost:5000/search-multiple \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "dentists",
    "locations": "Austin, San Antonio, Houston"
  }'

# Expected: Results from 3 locations in one request
```

#### 4.7 Performance Metrics
```bash
# Check performance
curl http://localhost:5000/metrics

# Expected:
# {
#   "searches_completed": X,
#   "cache_hits": Y,
#   "cache_stats": {...}
# }
```

#### 4.8 Cache Management
```bash
# Clear cache
curl -X POST http://localhost:5000/cache/clear

# Expected: {"message": "Caches cleared successfully"}
```

### Phase 5: Performance Testing

#### 5.1 Speed Benchmark
```python
# benchmark.py
import time
from scraper import LeadScraperEngine

def benchmark_single_search():
    """Benchmark single location search."""
    engine = LeadScraperEngine()
    
    start = time.time()
    result = engine.search_single_location(
        "restaurants",
        "Austin",
        fetch_websites=True
    )
    elapsed = time.time() - start
    
    print(f"📊 Single search: {elapsed:.2f}s ({len(result.results)} results)")
    
    # Repeat for cache hit
    start = time.time()
    result2 = engine.search_single_location(
        "restaurants",
        "Austin"
    )
    cache_elapsed = time.time() - start
    
    print(f"📊 Cache hit: {cache_elapsed:.4f}s (speedup: {elapsed/cache_elapsed:.0f}x)")

def benchmark_expanded_search():
    """Benchmark geo-grid expansion."""
    engine = LeadScraperEngine()
    
    start = time.time()
    result = engine.search_with_expansion(
        "restaurants",
        "London",
        fetch_websites=False
    )
    elapsed = time.time() - start
    
    areas = len(result.expanded_locations)
    print(f"📊 Expansion search ({areas} areas): {elapsed:.2f}s ({len(result.results)} unique results)")
    print(f"📊 Deduplication: removed {result.dedup_count} duplicates")

def benchmark_parallelism():
    """Test parallelism benefits."""
    # This would require multiple requests to verify thread pool is actually parallel
    print("📊 Parallelism benchmark would require concurrent load testing")

if __name__ == "__main__":
    print("🚀 Performance Benchmarking\n")
    benchmark_single_search()
    print()
    benchmark_expanded_search()
```

Run benchmark:
```bash
python benchmark.py
```

### Phase 6: Stress Testing

#### 6.1 Rapid Successive Requests
```python
# stress_test.py
import time
from scraper import search_leads

def stress_test_caching():
    """Test rapid successive requests (should use cache)."""
    keyword = "restaurants"
    location = "Austin"
    
    print("🔥 Stress Testing: Rapid Successive Requests\n")
    
    # First request (API call)
    start = time.time()
    for i in range(5):
        result = search_leads(keyword, location, use_expansion=False)
        elapsed = time.time() - start
        print(f"Request {i+1}: {elapsed:.3f}s")
    
    # Results after request 1 should be <100ms (cached)
    if time.time() - start < 1.0:
        print("✅ Caching is working!")
    else:
        print("⚠️  Caching might not be working")

if __name__ == "__main__":
    stress_test_caching()
```

### Phase 7: Error Handling Testing

#### 7.1 Handle API Errors
```python
# test_errors.py
from scraper import LeadScraperEngine

def test_invalid_location():
    """Test invalid location handling."""
    engine = LeadScraperEngine()
    
    try:
        result = engine.search_single_location(
            "restaurants",
            "InvalidLocationXYZ123"
        )
        # Should still return, but maybe empty
        print(f"✅ Invalid location handled: {len(result.results)} results")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_network_error_simulation():
    """Test network error handling."""
    # This would require mocking the requests library
    print("⚠️  Network error simulation requires mock testing")

if __name__ == "__main__":
    test_invalid_location()
```

## 🔍 Validation Checklist

- [ ] Installation successful (pip show flask, requests)
- [ ] API key configured (.env found, not empty)
- [ ] Health endpoint responds (GET /health returns 200)
- [ ] Config endpoint shows settings (GET /config)
- [ ] Simple search works (POST /search returns results)
- [ ] Expansion search works (results include expanded_locations)
- [ ] Multi-location search works (POST /search-multiple)
- [ ] Website fetching works (website URLs in results)
- [ ] Caching works (repeated search is <200ms)
- [ ] Metrics endpoint works (GET /metrics shows stats)
- [ ] Deduplication works (dedup_count > 0 on expansion)
- [ ] Error handling works (invalid input returns 400)
- [ ] Rate limiting works (no quota errors)
- [ ] Performance is acceptable (see benchmarks)

## 📊 Sample Test Data

### Test Query 1 (Simple)
```json
{
  "keyword": "coffee",
  "location": "Austin"
}
```

### Test Query 2 (With Expansion)
```json
{
  "keyword": "restaurants",
  "location": "Delhi",
  "use_expansion": true
}
```

### Test Query 3 (Fast Mode)
```json
{
  "keyword": "plumbers",
  "location": "London",
  "fetch_websites": false
}
```

### Test Query 4 (Multiple Locations)
```json
{
  "keyword": "dentists",
  "locations": "Manhattan, Brooklyn, Queens"
}
```

## 🐛 Debugging Tips

### Enable Debug Mode
```bash
export DEBUG_MODE=true
python app.py
```

### Check Logs
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Cache
```python
from scraper import LeadScraperEngine
engine = LeadScraperEngine()
cache_info = engine.cache.cache.get_cache_info()
print(cache_info)
```

### Monitor API Calls
```python
from scraper.rate_limiter import get_api_tracker
tracker = get_api_tracker()
print(f"Calls per minute: {tracker.get_calls_per_minute()}")
print(f"Total calls: {tracker.get_call_count()}")
```

## ✅ Final Validation

After all tests pass:
1. ✅ Core functionality working
2. ✅ Performance acceptable
3. ✅ Error handling robust
4. ✅ Caching effective
5. ✅ Geo-expansion working
6. ✅ Deduplication accurate
7. ✅ Rate limiting preventing quota issues
8. ✅ Ready for production!

## 📞 Troubleshooting

| Issue | Debug Step |
|-------|-----------|
| "API key not found" | Check .env file, verify GOOGLE_MAPS_API_KEY |
| Slow requests | Check `fetch_websites` flag, verify rate limiter |
| Empty results | Try different keyword/location, check proxy |
| Quota exceeded | Reduce MAX_WORKERS, increase MIN_DELAY |
| Cache not working | Verify CACHE_ENABLED=true, check TTL |

---

**Ready to test?** Start with Phase 1, then work through each phase sequentially! 🚀
