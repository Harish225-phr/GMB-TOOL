import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable (secure!)
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    raise ValueError("❌ GOOGLE_MAPS_API_KEY not found in .env file!")

MAX_WORKERS = 5
REQUEST_TIMEOUT = 8


@lru_cache(maxsize=500)
def get_website(place_id):
    """Get website from Place Details API with caching"""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "website",
        "key": API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        return res.json().get("result", {}).get("website", "N/A")
    except Exception as e:
        return "N/A"


def scrape_gmb(keyword, location, limit=20, page_token=None):
    """Fast scraper with pagination support - returns 20 results per page"""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{keyword} in {location}",
        "key": API_KEY
    }
    
    # Add pagination token if provided
    if page_token:
        params["pagetoken"] = page_token
        time.sleep(0.5)  # API requires delay for pagination
    
    results = []
    place_ids = []
    
    # Fetch one page (returns up to 20 results)
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    data = response.json()
    
    for place in data.get("results", []):
        place_ids.append(place.get("place_id"))
        results.append({
            "name": place.get("name"),
            "rating": place.get("rating", "N/A"),
            "reviews": place.get("user_ratings_total", "N/A"),
            "website": "",
            "place_id": place.get("place_id")
        })
    
    # Fetch websites concurrently
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        websites = list(executor.map(get_website, place_ids))
    
    for i, result in enumerate(results):
        result["website"] = websites[i] if i < len(websites) else "N/A"
        del result["place_id"]
    
    # Return results and next page token for pagination
    return {
        "results": results,
        "next_page_token": data.get("next_page_token")  # None if no more pages
    }