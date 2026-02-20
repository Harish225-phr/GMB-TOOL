import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from dotenv import load_dotenv

# 🔥 Load .env for local only
load_dotenv()

# 🔥 Works for both local & Render
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")

# ⚠️ Do NOT crash in production
if not API_KEY:
    print("⚠️ WARNING: Google API key not found. Check environment variables.")

MAX_WORKERS = 5
REQUEST_TIMEOUT = 8


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


def scrape_gmb(keyword, location, limit=20, page_token=None):
    """Fast scraper with pagination support"""

    if not API_KEY:
        return {"results": [], "next_page_token": None}

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{keyword} in {location}",
        "key": API_KEY
    }

    # Pagination support
    if page_token:
        params["pagetoken"] = page_token
        time.sleep(1)  # Google requires delay

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        data = response.json()
    except Exception:
        return {"results": [], "next_page_token": None}

    results = []
    place_ids = []

    for place in data.get("results", [])[:limit]:
        place_id = place.get("place_id")

        place_ids.append(place_id)
        results.append({
            "name": place.get("name"),
            "rating": place.get("rating", "N/A"),
            "reviews": place.get("user_ratings_total", "N/A"),
            "website": "",
            "place_id": place_id
        })

    # 🔥 Fetch websites in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        websites = list(executor.map(get_website, place_ids))

    for i, result in enumerate(results):
        result["website"] = websites[i] if i < len(websites) else "N/A"
        result.pop("place_id", None)

    return {
        "results": results,
        "next_page_token": data.get("next_page_token")
    }