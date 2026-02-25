# Quick Reference Guide - GMD Tool v2.0

## 📦 Project Structure

```
GMD-Tool/
├── app.py                      # Flask application (6 endpoints)
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (create this)
├── README.md                   # Quick start guide
├── ARCHITECTURE.md             # Detailed system design
├── USAGE_GUIDE.md             # API & code examples
├── UPGRADE_SUMMARY.md         # v1→v2 migration guide
├── QUICK_REFERENCE.md         # This file
├── Procfile                   # Render deployment
├── render.yaml                # Render configuration
└── scraper/                   # Main package
    ├── __init__.py            # Package exports
    ├── config.py              # Configuration & geo-grids
    ├── models.py              # Data classes
    ├── api_client.py          # Google API wrapper
    ├── rate_limiter.py        # Concurrency control
    ├── geo_grid.py            # Area expansion
    ├── deduplicator.py        # Result merging
    ├── website_extractor.py   # Website fetching
    ├── cache_manager.py       # TTL caching
    └── lead_scraper.py        # Main orchestrator
```

## 🎯 Core Modules at a Glance

| Module | Purpose | Key Classes |
|--------|---------|------------|
| **config.py** | Configuration management | `AppConfig`, `GeoGridAreas` |
| **models.py** | Type-safe data structures | `BusinessLead`, `SearchResult` |
| **api_client.py** | Google Places API wrapper | `GooglePlacesAPIClient` |
| **rate_limiter.py** | Concurrency & rate control | `RateLimiter`, `ConcurrencyController` |
| **geo_grid.py** | Geographic expansion | `GeoGridExpander`, `SearchLocationManager` |
| **deduplicator.py** | Result deduplication | `ResultDeduplicator`, `PrecisionMatcher` |
| **website_extractor.py** | Website extraction | `WebsiteExtractor`, `OptionalWebsiteFetcher` |
| **cache_manager.py** | TTL-based caching | `SearchResultCache`, `SmartSearchCache` |
| **lead_scraper.py** | Main orchestrator | `LeadScraperEngine` |

## 🚀 Common Tasks

### Task 1: Search for Leads
```python
from scraper import LeadScraperEngine

engine = LeadScraperEngine()
result = engine.search_single_location("restaurants", "Delhi")

for lead in result.results:
    print(f"{lead.name} - {lead.website}")
```

### Task 2: Search with Geo-Grid Expansion
```python
# Auto-expand "Delhi" to 9 areas
result = engine.search_with_expansion("restaurants", "Delhi")
print(f"Unique results: {result.total_unique_results}")
print(f"Duplicates removed: {result.dedup_count}")
```

### Task 3: Fast Search (Skip Websites)
```python
result = engine.search_single_location(
    "restaurants",
    "Delhi",
    fetch_websites=False  # Skip for 50% speed boost
)
```

### Task 4: Make HTTP Request
```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"keyword":"restaurants","location":"Delhi","use_expansion":true}'
```

### Task 5: Get Performance Metrics
```python
metrics = engine.get_metrics()
print(f"Cache hit ratio: {metrics['cache_stats']['hit_ratio_percent']}%")
print(f"Duplicates removed: {metrics['duplicates_removed']}")
```

### Task 6: Clear Cache
```python
engine.clear_caches()
```

### Task 7: Add Custom Geo-Grid
```python
from scraper import GeoGridExpander

expander = GeoGridExpander()
expander.add_custom_grid("Paris", ["1st", "2nd", "3rd", ...])
```

## 🔗 API Endpoints Summary

| Endpoint | Method | Purpose | Request |
|----------|--------|---------|---------|
| `/search` | POST | Search single/expanded | `{keyword, location, use_expansion?}` |
| `/search-multiple` | POST | Parallel multi-location | `{keyword, locations}` |
| `/health` | GET | System status | - |
| `/metrics` | GET | Performance stats | - |
| `/config` | GET | Current configuration | - |
| `/cache/clear` | POST | Clear caches | - |

## ⚙️ Configuration Variables

```bash
# API
GOOGLE_MAPS_API_KEY=sk-...

# Performance
MAX_WORKERS=3                      # Thread pool
MAX_CONCURRENT_API_CALLS=5         # Concurrent requests
REQUEST_TIMEOUT=15                 # Seconds
MIN_DELAY_BETWEEN_API_CALLS=0.2   # Rate limiting

# Search
MAX_PAGES_PER_SEARCH=3            # Pages = 60 results
MAX_RESULTS_PER_LOCATION=60

# Features
DEBUG_MODE=false
CACHE_ENABLED=true
FETCH_WEBSITES_BY_DEFAULT=true
```

## 🗺️ Supported Geo-Grids

```python
from scraper.config import GeoGridAreas

# These expand automatically:
GeoGridAreas.CITY_AREAS["delhi"]      # 9 areas
GeoGridAreas.CITY_AREAS["mumbai"]     # 9 areas
GeoGridAreas.CITY_AREAS["bangalore"]  # 8 areas
GeoGridAreas.CITY_AREAS["london"]     # 7 areas
GeoGridAreas.CITY_AREAS["new york"]   # 7 areas

# Check if city has grid
if GeoGridAreas.has_geo_grid("Delhi"):
    print("Auto-expandable!")
```

## 📊 Response Format

### Single Location Response
```json
{
  "keyword": "restaurants",
  "location": "Delhi",
  "results": [
    {
      "name": "Business Name",
      "rating": 4.5,
      "reviews": 324,
      "website": "https://..."
    }
  ],
  "total_unique_results": 45,
  "cache_stats": {
    "hits": 10,
    "hit_ratio_percent": 67.0
  }
}
```

### Expanded Location Response
```json
{
  "keyword": "restaurants",
  "location": "Delhi",
  "results": [...],
  "expanded_locations": ["Delhi", "Central Delhi", ...],
  "total_unique_results": 87,
  "duplicates_removed": 33,
  "results_by_location": {
    "Delhi": 15,
    "Central Delhi": 12,
    ...
  }
}
```

## ⚠️ Error Handling

```python
try:
    result = engine.search_single_location("restaurants", "Delhi")
except ValueError as e:
    print(f"Bad input: {e}")
except ConnectionError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"API error: {e}")
```

## 🧪 Quick Test

```bash
# 1. Start
python app.py

# 2. Health check
curl http://localhost:5000/health

# 3. Search
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"keyword":"restaurants","location":"Delhi"}'

# 4. Metrics
curl http://localhost:5000/metrics
```

## 🔍 Debugging

```python
from scraper.config import config

# Enable debug mode
config.DEBUG_MODE = True

# Check cache stats
cache_info = engine.cache.cache.get_cache_info()
print(cache_info)

# Check API tracking
from scraper.rate_limiter import get_api_tracker
tracker = get_api_tracker()
print(f"Calls/min: {tracker.get_calls_per_minute()}")
```

## 📈 Performance Tips

1. **Use caching** - Repeat searches are cached for 1 hour
2. **Skip websites** - `fetch_websites=False` is 50% faster
3. **Use expansion** - Get 2-3x more results from one keyword
4. **Batch requests** - Use `/search-multiple` for parallel searches
5. **Tune workers** - Increase for volume, decrease for quota limits

## 🔄 Data Flow Diagrams

### Simple Search
```
User → Check Cache → API Call → Extract Results → 
  Fetch Websites (parallel) → Cache → Return
```

### Expanded Search
```
User → Expand Location (Delhi→9 areas) → 
  Search Each (parallel) → Merge Results → 
    Deduplicate → Cache → Return
```

## 📚 Find More Info

- **Setup**: See README.md
- **Examples**: See USAGE_GUIDE.md
- **Design**: See ARCHITECTURE.md
- **Migration**: See UPGRADE_SUMMARY.md

## 🆘 Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| "API key not configured" | Set `GOOGLE_MAPS_API_KEY` in `.env` |
| Results are slow | Use `fetch_websites=False` |
| Quota errors | Reduce `MAX_WORKERS` to 2 |
| Cache not working | Check `CACHE_ENABLED=true` |
| Too many duplicates | Try `use_expansion=true` |

## 🎯 Next Steps

1. Read README.md for quick start
2. Try basic search in Python or HTTP
3. Review USAGE_GUIDE.md for advanced features
4. Check ARCHITECTURE.md for system design
5. Tune configuration for your needs

---

**Pro Tip:** Start with simple searches, then enable expansion as you scale up! 🚀
