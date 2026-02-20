from flask import Flask, render_template, request, jsonify
from scraper.gmb_scraper import scrape_gmb
from flask_caching import Cache
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

app = Flask(__name__)

# Cache configuration
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 3600})


def get_cache_key(keyword, location):
    """Generate cache key from keyword and location"""
    key_string = f"{keyword.lower()}_{location.lower()}"
    return hashlib.md5(key_string.encode()).hexdigest()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    try:
        keyword = request.json.get("keyword", "").strip()
        location = request.json.get("location", "").strip()
        page_token = request.json.get("page_token")  # For pagination

        if not keyword or not location:
            return jsonify({"error": "Keyword and location are required"}), 400

        # Cache key for this search
        cache_key = get_cache_key(keyword, location)
        
        # For first page - check full cache
        if not page_token:
            cached_data = cache.get(cache_key)
            if cached_data:
                return jsonify({"data": cached_data["results"], "next_page_token": cached_data.get("next_page_token"), "cached": True})
        
        # Fetch fresh data
        response = scrape_gmb(keyword, location, page_token=page_token)
        
        # Cache only first page
        if not page_token:
            cache.set(cache_key, response, timeout=3600)

        return jsonify({"data": response["results"], "next_page_token": response.get("next_page_token"), "cached": not page_token and cache.get(cache_key) is not None})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/search-multiple", methods=["POST"])
def search_multiple():
    """Search across multiple locations for same keyword - PARALLEL"""
    try:
        keyword = request.json.get("keyword", "").strip()
        locations = request.json.get("locations", "").strip()

        if not keyword or not locations:
            return jsonify({"error": "Keyword and locations are required"}), 400

        # Parse locations - split by comma
        location_list = [loc.strip() for loc in locations.split(",") if loc.strip()]
        
        if not location_list:
            return jsonify({"error": "At least one location is required"}), 400

        all_results = {}

        # Parallel search for all locations
        def search_location(location):
            try:
                response = scrape_gmb(keyword, location)
                return (location, response["results"])
            except Exception as e:
                return (location, [])

        # Use ThreadPoolExecutor for parallel searches
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(search_location, loc) for loc in location_list]
            for future in futures:
                location, results = future.result()
                all_results[location] = results

        return jsonify({
            "results": all_results,
            "total_locations": len(location_list),
            "keyword": keyword
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)