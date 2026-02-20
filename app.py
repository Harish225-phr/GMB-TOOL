from flask import Flask, render_template, request, jsonify
from scraper.gmb_scraper import scrape_gmb
from flask_caching import Cache
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sys

app = Flask(__name__)

# Cache configuration
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 3600})


def log_error(msg):
    """Log errors to both stdout and stderr"""
    print(f"[ERROR] {msg}", file=sys.stderr)
    print(f"[ERROR] {msg}", file=sys.stdout)


# Global error handler to ensure all responses are valid JSON
@app.errorhandler(Exception)
def handle_error(error):
    """Catch all unhandled exceptions and return proper JSON error"""
    error_msg = str(error)
    log_error(f"Unhandled exception: {error_msg}")
    import traceback
    traceback.print_exc()
    response = jsonify({"error": "Server error. Please try again later.", "details": error_msg})
    response.headers['Content-Type'] = 'application/json'
    return response, 500


# Ensure all JSON responses have proper Content-Type
@app.after_request
def after_request(response):
    """Ensure all responses have proper Content-Type and encoding"""
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Content-Encoding'] = 'utf-8'
    # Ensure response is not empty
    if response.data is None or response.data == b'':
        response.data = json.dumps({"error": "Empty response from server"}).encode('utf-8')
    return response


def get_cache_key(keyword, location):
    """Generate cache key from keyword and location"""
    key_string = f"{keyword.lower()}_{location.lower()}"
    return hashlib.md5(key_string.encode()).hexdigest()


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "App is running"}), 200


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    try:
        # Validate request
        if not request.json:
            return jsonify({"error": "Invalid JSON request"}), 400
            
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
        
        # Fetch fresh data with timeout protection
        try:
            log_error(f"Starting search: {keyword} in {location}")
            response = scrape_gmb(keyword, location, page_token=page_token)
        except Exception as e:
            error_msg = str(e)
            log_error(f"Scraper exception: {error_msg}")
            # Check if it's API key issue
            if "API key" in error_msg or "not configured" in error_msg:
                return jsonify({"error": "API Key not configured. Check Render environment variables."}), 500
            return jsonify({"error": f"Search failed: {error_msg}"}), 500
        
        if response is None:
            return jsonify({"error": "No response from scraper"}), 500
        
        # Cache only first page
        if not page_token:
            cache.set(cache_key, response, timeout=3600)

        result_data = response.get("results", [])
        next_token = response.get("next_page_token")
        
        return jsonify({
            "data": result_data, 
            "next_page_token": next_token, 
            "cached": not page_token and cache.get(cache_key) is not None
        })
    
    except json.JSONDecodeError as e:
        log_error(f"JSON decode error: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        log_error(f"Search error: {str(e)}")
        return jsonify({"error": "Search failed. Please try again."}), 500


@app.route("/search-multiple", methods=["POST"])
def search_multiple():
    """Search across multiple locations for same keyword - PARALLEL"""
    try:
        # Validate request
        if not request.json:
            return jsonify({"error": "Invalid JSON request"}), 400
            
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
                if response is None:
                    return (location, [])
                return (location, response.get("results", []))
            except Exception as e:
                log_error(f"Error searching {location}: {str(e)}")
                return (location, [])

        # Use ThreadPoolExecutor for parallel searches - MAX 2 concurrent to avoid overwhelming server
        with ThreadPoolExecutor(max_workers=2) as executor:  # Reduced from 3 to 2
            futures = [executor.submit(search_location, loc) for loc in location_list]
            
            # Collect results with timeout to prevent hanging
            from concurrent.futures import as_completed
            try:
                for future in as_completed(futures, timeout=120):  # Increased to 120s
                    try:
                        location, results = future.result()
                        all_results[location] = results if results else []
                    except Exception as e:
                        log_error(f"Future result error: {str(e)}")
                        # Still return partial results even if some locations fail
                        continue
            except Exception as e:
                log_error(f"as_completed timeout: {str(e)}")

        response_data = {
            "results": all_results,
            "total_locations": len(location_list),
            "locations_found": len(all_results),
            "keyword": keyword
        }
        
        log_error(f"Multi-search response: {json.dumps(response_data, default=str)[:200]}")  # Log first 200 chars
        return jsonify(response_data)

    except json.JSONDecodeError as e:
        log_error(f"JSON decode error in search-multiple: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        log_error(f"Search-multiple error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Search failed. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=True)