import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from dotenv import load_dotenv

# 🔥 Load .env for local only
load_dotenv()

# 🔥 Works for both local & Render
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")

# ⚠️ Do NOT crash in production
if not API_KEY:
    print("⚠️ WARNING: Google API key not found. Check environment variables.")

MAX_WORKERS = 2  # Reduced from 5 to prevent excessive concurrent requests
REQUEST_TIMEOUT = 10  # Increased timeout slightly


@lru_cache(maxsize=500)
def get_website(place_id):
    """Get website from Place Details API with caching"""
    if not API_KEY:
        return "N/A"

    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "website",
        "key": API_KEY
    }

    try:
        res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        return res.json().get("result", {}).get("website", "N/A")
    except Exception:
        return "N/A"


def scrape_gmb(keyword, location, limit=60, page_token=None):
    """Deep aggressive scraper - fetches EVERY SINGLE result available"""

    if not API_KEY:
        return {"results": [], "next_page_token": None}

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    results = []
    place_ids = []
    current_page_token = page_token
    page_count = 0
    MAX_PAGES = 15  # 🔥 DEEP SEARCH - Keep searching till no more results!

    while page_count < MAX_PAGES:
        params = {
            "query": f"{keyword} in {location}",
            "key": API_KEY
        }

        # Pagination support
        if current_page_token:
            params["pagetoken"] = current_page_token
            time.sleep(2)  # Google requires delay between pages

        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            data = response.json()
        except Exception:
            break

        # Process results from this page
        page_results = data.get("results", [])
        if not page_results:  # No more results
            break

        for place in page_results:
            place_id = place.get("place_id")
            place_ids.append(place_id)
            results.append({
                "name": place.get("name"),
                "rating": place.get("rating", "N/A"),
                "reviews": place.get("user_ratings_total", "N/A"),
                "website": "",
                "place_id": place_id
            })

        # Check if there are more pages
        current_page_token = data.get("next_page_token")
        if not current_page_token:  # No more pages available
            break
        
        page_count += 1

    # 🔥 Fetch websites in parallel with better error handling
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_website, pid): i for i, pid in enumerate(place_ids)}
        websites = [None] * len(place_ids)  # Pre-fill with None values
        
        # Use as_completed with timeout to handle slow requests
        for future in as_completed(futures, timeout=60):
            try:
                idx = futures[future]
                websites[idx] = future.result()
            except Exception as e:
                idx = futures[future]
                websites[idx] = "N/A"  # Default to N/A on error
                print(f"Error fetching website for index {idx}: {str(e)}")

    for i, result in enumerate(results):
        result["website"] = websites[i] if i < len(websites) and websites[i] else "N/A"
        result.pop("place_id", None)

    return {
        "results": results,
        "next_page_token": current_page_token if page_count < MAX_PAGES else None,
        "total_results_found": len(results)
    }