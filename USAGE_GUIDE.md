# GMD Tool - Usage Guide

## Quick Start

### 1. Installation

```bash
# Clone or navigate to project
cd GMD-Tool

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create .env file in project root
GOOGLE_MAPS_API_KEY=your_api_key_here
MAX_WORKERS=3
DEBUG_MODE=false
CACHE_ENABLED=true
```

### 2. Run the Application

```bash
# Development mode
python app.py

# With Gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# The app will be available at http://localhost:5000
```

## Frontend Usage

Access the web interface at `http://localhost:5000`

### Basic Search
1. Enter search keyword (e.g., "restaurants")
2. Enter location (e.g., "Delhi")
3. Check "Use Expansion" for geographic grid search
4. Check "Fetch Websites" to get business URLs
5. Click "Search"

### Multiple Locations
1. Use comma-separated locations: "Delhi, Mumbai, Bangalore"
2. Click "Search Multiple" button

### Result Interpretation
- **Name**: Business name
- **Rating**: Google rating (0-5)
- **Reviews**: Number of reviews
- **Website**: Business website URL (if available)

## API Usage

### Python Integration

#### Basic Setup
```python
from scraper import LeadScraperEngine

# Initialize
engine = LeadScraperEngine(
    enable_caching=True,
    enable_geo_expansion=True,
    fetch_websites_by_default=True
)
```

#### Single Location Search
```python
result = engine.search_single_location(
    keyword="restaurants",
    location="Delhi",
    fetch_websites=True,
    max_results=60
)

# Access results
for lead in result.results:
    print(f"{lead.name}")
    print(f"  Rating: {lead.rating}")
    print(f"  Website: {lead.website}")
    print(f"  Reviews: {lead.reviews_count}")
```

#### Geo-Grid Expansion Search
```python
result = engine.search_with_expansion(
    keyword="restaurants",
    location="Delhi",  # Auto-expands to 9 areas
    fetch_websites=True
)

# View aggregated results
print(f"Total unique results: {result.total_unique_results}")
print(f"Duplicates removed: {result.dedup_count}")
print(f"Results by location:")
for location, count in result.results_by_location.items():
    print(f"  {location}: {count}")
```

#### Quick Search (Convenience Function)
```python
from scraper import search_leads

results_dict = search_leads(
    keyword="coffee shops",
    location="New York",
    use_expansion=True,
    fetch_websites=True
)

# Results are in dictionary format
for lead_dict in results_dict["results"]:
    print(lead_dict)
```

### HTTP API

#### Search Endpoint (POST /search)

**Request:**
```json
{
  "keyword": "plumbers",
  "location": "Austin",
  "use_expansion": false,
  "fetch_websites": true,
  "max_results": 60
}
```

**cURL:**
```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "plumbers",
    "location": "Austin",
    "use_expansion": false,
    "fetch_websites": true
  }'
```

**Response:**
```json
{
  "keyword": "plumbers",
  "location": "Austin",
  "results": [
    {
      "name": "ABC Plumbing",
      "rating": 4.8,
      "reviews": 245,
      "website": "https://abcplumbing.com"
    },
    ...
  ],
  "total_unique_results": 32,
  "cache_stats": {
    "hits": 10,
    "misses": 5,
    "hit_ratio_percent": 66.67
  }
}
```

#### Multi-Location Search (POST /search-multiple)

**Request:**
```json
{
  "keyword": "dental clinics",
  "locations": "Manhattan, Brooklyn, Queens",
  "use_expansion": false,
  "fetch_websites": true
}
```

**cURL:**
```bash
curl -X POST http://localhost:5000/search-multiple \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "dental clinics",
    "locations": "Manhattan, Brooklyn, Queens",
    "fetch_websites": true
  }'
```

**Response:**
```json
{
  "keyword": "dental clinics",
  "locations_requested": 3,
  "locations_completed": 3,
  "results": {
    "Manhattan": {
      "results": [...],
      "total_unique_results": 28
    },
    "Brooklyn": {
      "results": [...],
      "total_unique_results": 35
    },
    "Queens": {
      "results": [...],
      "total_unique_results": 22
    }
  }
}
```

### JavaScript/Fetch Integration

```javascript
// Single search with expansion
async function searchLeads(keyword, location) {
  const response = await fetch('http://localhost:5000/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      keyword: keyword,
      location: location,
      use_expansion: true,
      fetch_websites: true
    })
  });
  
  const data = await response.json();
  return data;
}

// Usage
const results = await searchLeads('restaurants', 'Delhi');
console.log(results);
```

## Advanced Usage

### Custom Geo-Grids

```python
from scraper import GeoGridExpander

expander = GeoGridExpander(enable_expansion=True)

# Add custom grid for a city
expander.add_custom_grid(
    "San Francisco",
    [
        "Downtown San Francisco",
        "Mission District",
        "Castro District",
        "Richmond District",
        "Sunset District"
    ]
)

# Now searches in San Francisco will expand to these 5 areas
from scraper import SearchLocationManager
manager = SearchLocationManager(expander)
locations = manager.get_search_locations("San Francisco", use_expansion=True)
# Returns: ["San Francisco", "Downtown San Francisco", "Mission District", ...]
```

### Performance Tuning

```python
from scraper.config import config

# Increase parallelism for faster searches (more API calls)
config.MAX_WORKERS = 5
config.MAX_CONCURRENT_API_CALLS = 8

# Reduce for slower API quotas
config.MAX_WORKERS = 2
config.MAX_CONCURRENT_API_CALLS = 3

# Adjust rate limiting (seconds between API calls)
config.MIN_DELAY_BETWEEN_REQUESTS = 0.1  # 100ms = 10 calls/sec

# Increase results per search
config.MAX_RESULTS_PER_LOCATION = 100
config.MAX_PAGES_PER_SEARCH = 5  # Max 100 results

# Modify cache TTL
config.CACHE_SEARCH_TTL = 7200  # 2 hours
```

### Deduplication Strategy

```python
from scraper import ResultDeduplicator
from scraper.models import BusinessLead

# Create deduplicator
dedup = ResultDeduplicator(similarity_threshold=0.9)

# Group leads by location
leads_by_location = {
    "Delhi": [lead1, lead2, ...],
    "Noida": [lead3, lead4, ...],
}

# Deduplicate
unique_leads, stats = dedup.deduplicate(leads_by_location, prefer_rating=True)

print(f"Total input: {stats['total_input']}")
print(f"Total output: {stats['total_output']}")
print(f"Duplicates removed: {stats['duplicates_removed']}")
```

### Manual Website Fetching

```python
from scraper import WebsiteExtractor
from scraper.api_client import GooglePlacesAPIClient

# Initialize
client = GooglePlacesAPIClient()
extractor = WebsiteExtractor(client)

# Fetch single website
website = extractor.extract_website(place_id="ChIJ...")

# Batch fetch multiple
place_ids = ["ChIJ...", "ChIJ...", ...]
websites_dict = extractor.extract_websites_batch(place_ids)

# Check cache stats
cache_info = extractor.get_cache_info()
print(f"Cached websites: {cache_info['websites_cached']}")
```

### Cache Management

```python
from scraper import SearchResultCache, CacheKey

# Create cache
cache = SearchResultCache(default_ttl=3600)

# Generate cache key
key = CacheKey.generate_search_key("restaurants", "Delhi")

# Set value
cache.set(key, {
    "results": [...],
    "total": 45
})

# Get value
result = cache.get(key)

# Get statistics
stats = cache.get_stats()
print(f"Hit ratio: {stats['hit_ratio_percent']}%")

# Cleanup expired
cache.cleanup_expired()

# Clear all
cache.clear()
```

### Rate Limiting Control

```python
from scraper.rate_limiter import initialize_rate_limiting, get_rate_limiter

# Initialize with custom settings
initialize_rate_limiting(
    calls_per_second=5,  # 5 API calls per second
    max_concurrent=3      # 3 concurrent requests
)

# Access rate limiter
limiter = get_rate_limiter()

# Wait before making API call
limiter.wait_if_needed()
# ... make API call ...
```

## Common Scenarios

### Scenario 1: Fast Search (No Website Fetching)

```python
engine = LeadScraperEngine(fetch_websites_by_default=False)

result = engine.search_single_location(
    keyword="dentists",
    location="Los Angeles",
    fetch_websites=False  # Skip website fetching
)
# Result: ~1-2 seconds instead of 3-5
```

### Scenario 2: Deep Research (All Results, All Pages)

```python
from scraper.config import config

# Increase limits
config.MAX_PAGES_PER_SEARCH = 5
config.MAX_RESULTS_PER_LOCATION = 100

result = engine.search_with_expansion(
    keyword="law firms",
    location="London"
)
# Result: Comprehensive data from all areas
```

### Scenario 3: Real-Time Dashboard

```python
# Lightweight frequent searches with caching
results = engine.search_single_location(
    keyword="coffee shops",
    location="Seattle",
    fetch_websites=False
)

# Repeat calls will hit cache
results2 = engine.search_single_location(
    keyword="coffee shops",
    location="Seattle"
)
# Result: <100ms from cache
```

### Scenario 4: CSV Export

```python
import csv

result = engine.search_with_expansion(
    keyword="restaurants",
    location="Delhi"
)

# Export to CSV
with open('results.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'rating', 'reviews', 'website'])
    writer.writeheader()
    for lead in result.results:
        writer.writerow(lead.to_dict())
```

### Scenario 5: Scheduled Batch Processing

```python
import time
from datetime import datetime

keywords = ["restaurants", "cafes", "bars"]
locations = ["Delhi", "Mumbai", "Bangalore"]

for keyword in keywords:
    for location in locations:
        print(f"Processing {keyword} in {location}...")
        result = engine.search_with_expansion(
            keyword=keyword,
            location=location
        )
        
        # Save results
        with open(f"results_{keyword}_{location}_{datetime.now().timestamp()}.json", 'w') as f:
            import json
            json.dump(result.to_dict(), f, indent=2)
        
        # Delay between searches
        time.sleep(2)
```

## Troubleshooting

### Issue: "Google API key not configured"
**Solution:**
```bash
# Check environment variable
echo $GOOGLE_MAPS_API_KEY

# Set it properly
export GOOGLE_MAPS_API_KEY=your_key
```

### Issue: Slow searches
**Solutions:**
1. Enable geo-grid cache: `use_expansion=False` for first search
2. Skip website fetching: `fetch_websites=False`
3. Reduce max results: `max_results=20`
4. Increase workers: `config.MAX_WORKERS = 5`

### Issue: API quota exceeded
**Solutions:**
1. Reduce concurrency: `config.MAX_CONCURRENT_API_CALLS = 2`
2. Increase delay: `config.MIN_DELAY_BETWEEN_REQUESTS = 1.0`
3. Clear cache and retry
4. Check API quota in Google Cloud Console

### Issue: Too many duplicates
**Check:**
1. Increase search locations for better coverage
2. Verify deduplication is enabled
3. Review deduplication stats: `result.dedup_count`

## Performance Tips

1. **Cache Results**: Reuse searches when possible (1-hour default TTL)
2. **Disable Websites for Speed**: Fast mode is 50% faster
3. **Batch Searches**: Use `/search-multiple` for many locations
4. **Monitor Metrics**: `engine.get_metrics()` shows performance data
5. **Tune Workers**: Balance speed vs. API quota consumption

## Monitoring & Analytics

```python
# Get detailed metrics
metrics = engine.get_metrics()

print(f"Total API Calls: {metrics['total_api_calls']}")
print(f"Cache Hits: {metrics['cache_hits']}")
print(f"Duplicates Removed: {metrics['duplicates_removed']}")

cache_stats = metrics['cache_stats']
print(f"Cache Hit Ratio: {cache_stats['hit_ratio_percent']}%")
```

## API Response Codes

- **200**: Success
- **400**: Bad request (missing keyword/location)
- **500**: Server error (API key, timeout, etc.)

## Getting Help

For issues or improvements:
1. Check logs: `echo $DEBUG_MODE` and `logger` output
2. Review configuration: `GET /config`
3. Check health: `GET /health`
4. Monitor metrics: `GET /metrics`
