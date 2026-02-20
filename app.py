from flask import Flask, render_template, request, jsonify
from scraper.gmb_scraper import scrape_gmb
from flask_caching import Cache
from functools import wraps
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


if __name__ == "__main__":
    app.run(debug=True)