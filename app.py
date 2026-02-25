"""
Flask application using refactored lead scraper engine.
Production-grade API for lead generation with geo-grid expansion, caching, and deduplication.
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from scraper.lead_scraper import LeadScraperEngine
from scraper.config import config
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import json
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO if not config.DEBUG_MODE else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={
    r"/search": {"origins": "*"},
    r"/search-multiple": {"origins": "*"},
    r"/health": {"origins": "*"},
    r"/metrics": {"origins": "*"},
    r"/config": {"origins": "*"},
    r"/cache/clear": {"origins": "*"}
})

# Initialize lead scraper engine (global instance) with error handling
scraper_engine = None

def initialize_scraper():
    """Initialize scraper engine safely."""
    global scraper_engine
    
    # Check if API key is configured
    if not config.GOOGLE_API_KEY:
        logger.warning("⚠️ WARNING: Google API key not configured. Check environment variables.")
        api_key_status = "NOT_CONFIGURED"
    else:
        api_key_status = "CONFIGURED"
        logger.info(f"✅ API Key configured (first 10 chars: {config.GOOGLE_API_KEY[:10]}...)")
    
    try:
        scraper_engine = LeadScraperEngine(
            api_key=config.GOOGLE_API_KEY if config.GOOGLE_API_KEY else None,
            enable_caching=config.CACHE_ENABLED,
            enable_geo_expansion=True,
            fetch_websites_by_default=config.FETCH_WEBSITES_BY_DEFAULT,
        )
        logger.info("✅ Lead Scraper Engine initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize scraper engine: {str(e)}")
        return False

# Try to initialize on startup
try:
    if initialize_scraper():
        logger.info("🚀 Application started successfully")
    else:
        logger.warning("⚠️ Application started but scraper engine has issues")
except Exception as e:
    logger.error(f"Critical error during initialization: {str(e)}")
    scraper_engine = None


def log_error(msg):
    """Log errors to both stdout and stderr"""
    logger.error(msg)
    print(f"[ERROR] {msg}", file=sys.stderr)


# Global error handler to ensure all responses are valid JSON
@app.errorhandler(Exception)
def handle_error(error):
    """Catch all unhandled exceptions and return proper JSON error"""
    error_msg = str(error)
    log_error(f"Unhandled exception: {error_msg}")
    import traceback
    traceback.print_exc()
    
    response = jsonify({
        "error": "Server error. Please try again later.",
        "details": error_msg if config.DEBUG_MODE else None
    })
    response.headers['Content-Type'] = 'application/json'
    return response, 500


# Ensure JSON responses have proper Content-Type
@app.after_request
def after_request(response):
    """Ensure JSON responses have proper Content-Type - skip HTML pages"""
    if response.content_type and 'text/html' in response.content_type:
        return response
    
    if response.is_json:
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    api_key_configured = bool(config.GOOGLE_API_KEY)
    scraper_ready = scraper_engine is not None
    
    return jsonify({
        "status": "ok",
        "message": "App is running",
        "version": "2.0",
        "api_key_configured": api_key_configured,
        "scraper_ready": scraper_ready,
        "features": {
            "geo_expansion": True,
            "caching": config.CACHE_ENABLED,
            "website_fetching": config.FETCH_WEBSITES_BY_DEFAULT,
            "parallel_requests": True,
        },
        "warning": "Google API key not configured" if not api_key_configured else None
    }), 200


@app.route("/")
def home():
    """Serve frontend."""
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    """
    Search for leads in a single location or with geo-grid expansion.
    
    Request JSON:
    {
        "keyword": "restaurants",
        "location": "Delhi",
        "use_expansion": true,  # Enable geo-grid expansion
        "fetch_websites": true,  # Fetch business websites
        "max_results": 60
    }
    """
    try:
        # Check if scraper is initialized
        if scraper_engine is None:
            return jsonify({
                "error": "Search service not available",
                "details": "Google API Key not configured. Set GOOGLE_MAPS_API_KEY environment variable."
            }), 503
        
        # Check if API key is configured
        if not config.GOOGLE_API_KEY:
            return jsonify({
                "error": "API Key not configured",
                "details": "Set GOOGLE_MAPS_API_KEY environment variable to use search functionality"
            }), 503
        
        # Validate request
        if not request.json:
            return jsonify({"error": "Invalid JSON request"}), 400
        
        keyword = request.json.get("keyword", "").strip()
        location = request.json.get("location", "").strip()
        use_expansion = request.json.get("use_expansion", True)
        fetch_websites = request.json.get("fetch_websites")
        max_results = request.json.get("max_results")
        
        if not keyword or not location:
            return jsonify({"error": "Keyword and location are required"}), 400
        
        logger.info(
            f"Search request: '{keyword}' in '{location}' "
            f"(expansion={use_expansion})"
        )
        
        # Execute search
        if use_expansion:
            result = scraper_engine.search_with_expansion(
                keyword=keyword,
                location=location,
                fetch_websites=fetch_websites,
                max_results_per_location=max_results
            )
        else:
            result = scraper_engine.search_single_location(
                keyword=keyword,
                location=location,
                fetch_websites=fetch_websites,
                max_results=max_results
            )
        
        response_data = result.to_dict()
        response_data["cache_stats"] = scraper_engine.get_metrics().get("cache_stats")
        
        return jsonify(response_data), 200
    
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log_error(f"Search error: {str(e)}")
        return jsonify({
            "error": "Search failed. Please try again.",
            "details": str(e) if config.DEBUG_MODE else None
        }), 500


@app.route("/search-multiple", methods=["POST"])
def search_multiple():
    """
    Search across multiple locations in parallel.
    
    Request JSON:
    {
        "keyword": "restaurants",
        "locations": "Delhi, Mumbai, Bangalore",
        "use_expansion": false,
        "fetch_websites": true
    }
    """
    try:
        # Check if scraper is initialized
        if scraper_engine is None:
            return jsonify({
                "error": "Search service not available",
                "details": "Google API Key not configured. Set GOOGLE_MAPS_API_KEY environment variable."
            }), 503
        
        # Check if API key is configured
        if not config.GOOGLE_API_KEY:
            return jsonify({
                "error": "API Key not configured",
                "details": "Set GOOGLE_MAPS_API_KEY environment variable to use search functionality"
            }), 503
        
        if not request.json:
            return jsonify({"error": "Invalid JSON request"}), 400
        
        keyword = request.json.get("keyword", "").strip()
        locations_str = request.json.get("locations", "").strip()
        use_expansion = request.json.get("use_expansion", False)
        fetch_websites = request.json.get("fetch_websites", True)
        
        if not keyword or not locations_str:
            return jsonify({"error": "Keyword and locations are required"}), 400
        
        # Parse locations
        location_list = [
            loc.strip() for loc in locations_str.split(",") if loc.strip()
        ]
        
        if not location_list:
            return jsonify({"error": "At least one location is required"}), 400
        
        logger.info(
            f"Multi-location search: '{keyword}' in {len(location_list)} locations"
        )
        
        # Search each location in parallel
        all_results = {}
        
        def search_location(location):
            try:
                if use_expansion:
                    result = scraper_engine.search_with_expansion(
                        keyword, location, fetch_websites
                    )
                else:
                    result = scraper_engine.search_single_location(
                        keyword, location, fetch_websites
                    )
                return (location, result.to_dict())
            except Exception as e:
                logger.error(f"Error searching {location}: {str(e)}")
                return (location, {"error": str(e), "results": []})
        
        # Execute parallel searches
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            futures = [
                executor.submit(search_location, loc) for loc in location_list
            ]
            
            try:
                for future in as_completed(futures, timeout=300):
                    try:
                        location, result_data = future.result()
                        all_results[location] = result_data
                    except Exception as e:
                        log_error(f"Future error: {str(e)}")
                        continue
            except Exception as e:
                log_error(f"Parallel search timeout: {str(e)}")
        
        response_data = {
            "keyword": keyword,
            "locations_requested": len(location_list),
            "locations_completed": len(all_results),
            "results": all_results,
            "metrics": scraper_engine.get_metrics(),
        }
        
        return jsonify(response_data), 200
    
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        log_error(f"Search-multiple error: {str(e)}")
        return jsonify({
            "error": "Search failed. Please try again.",
            "details": str(e) if config.DEBUG_MODE else None
        }), 500


@app.route("/metrics", methods=["GET"])
def metrics():
    """Get system metrics and performance stats."""
    # Check if scraper is initialized
    if scraper_engine is None:
        return jsonify({
            "error": "Metrics unavailable",
            "details": "Scraper engine not initialized. Check GOOGLE_MAPS_API_KEY."
        }), 503
    
    return jsonify(scraper_engine.get_metrics()), 200


@app.route("/cache/clear", methods=["POST"])
def clear_cache():
    """Clear all caches (admin endpoint)."""
    try:
        # Check if scraper is initialized
        if scraper_engine is None:
            return jsonify({
                "error": "Cache clear failed",
                "details": "Scraper engine not initialized. Check GOOGLE_MAPS_API_KEY."
            }), 503
        
        scraper_engine.clear_caches()
        return jsonify({"message": "Caches cleared successfully"}), 200
    except Exception as e:
        log_error(f"Error clearing cache: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/config", methods=["GET"])
def get_config():
    """Get current configuration."""
    return jsonify({
        "max_workers": config.MAX_WORKERS,
        "max_concurrent_api_calls": config.MAX_CONCURRENT_API_CALLS,
        "max_pages_per_search": config.MAX_PAGES_PER_SEARCH,
        "max_results_per_location": config.MAX_RESULTS_PER_LOCATION,
        "request_timeout": config.REQUEST_TIMEOUT,
        "cache_enabled": config.CACHE_ENABLED,
        "fetch_websites_by_default": config.FETCH_WEBSITES_BY_DEFAULT,
    }), 200


if __name__ == "__main__":
    app.run(debug=config.DEBUG_MODE)