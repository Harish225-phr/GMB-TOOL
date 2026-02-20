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


# Global error handler to ensure all responses are valid JSON
@app.errorhandler(Exception)
def handle_error(error):
    """Catch all unhandled exceptions and return proper JSON error"""
    print(f"Unhandled error: {str(error)}")
    import traceback
    traceback.print_exc()
    return jsonify({"error": "Server error. Please try again later."}), 500


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

        # Parallel search for all locations - REDUCED workers to avoid timeouts
        def search_location(location):
            try:
                response = scrape_gmb(keyword, location)
                return (location, response.get("results", []))
            except Exception as e:
                print(f"Error searching {location}: {str(e)}")
                return (location, [])

        # Use ThreadPoolExecutor for parallel searches - MAX 3 concurrent to avoid overwhelming server
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(search_location, loc) for loc in location_list]
            
            # Collect results with timeout to prevent hanging
            from concurrent.futures import as_completed
            for future in as_completed(futures, timeout=60):  # 60 second timeout per location
                try:
                    location, results = future.result()
                    all_results[location] = results
                except Exception as e:
                    print(f"Future result error: {str(e)}")
                    # Still return partial results even if some locations fail
                    continue

        return jsonify({
            "results": all_results,
            "total_locations": len(location_list),
            "locations_found": len(all_results),
            "keyword": keyword
        })

    except Exception as e:
        print(f"Search-multiple error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)