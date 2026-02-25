"""
Low-level Google Places API wrapper.
Handles HTTP requests with error handling, retries, and rate limiting.
"""

import requests
import time
from typing import Dict, Any, Optional, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import config
from .rate_limiter import get_rate_limiter, get_api_tracker


class GooglePlacesAPIClient:
    """
    Wrapper for Google Places API endpoints.
    Provides methods for text search and place details with built-in error handling.
    """
    
    # API endpoints
    TEXT_SEARCH_ENDPOINT = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    PLACE_DETAILS_ENDPOINT = "https://maps.googleapis.com/maps/api/place/details/json"
    
    # Status codes
    STATUS_OK = "OK"
    STATUS_ZERO_RESULTS = "ZERO_RESULTS"
    STATUS_OVER_QUERY_LIMIT = "OVER_QUERY_LIMIT"
    STATUS_REQUEST_DENIED = "REQUEST_DENIED"
    STATUS_INVALID_REQUEST = "INVALID_REQUEST"
    STATUS_UNKNOWN_ERROR = "UNKNOWN_ERROR"
    STATUS_NOT_FOUND = "NOT_FOUND"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            api_key: Google Maps API key (uses config default if None)
        """
        self.api_key = api_key or config.GOOGLE_API_KEY
        
        if not self.api_key:
            raise ValueError("Google Maps API key not configured")
        
        # Create session with retry strategy
        self.session = self._create_session()
    
    @staticmethod
    def _create_session() -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy for network errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def text_search(
        self,
        query: str,
        page_token: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Perform text search using Google Places Text Search API.
        
        Args:
            query: Search query (keyword + location)
            page_token: Token for pagination
            region: Region bias code (ISO 3166-1)
        
        Returns:
            Tuple of (response_dict, status_code)
            
        Raises:
            ValueError: If API key is invalid
            Exception: For critical errors
        """
        # Apply rate limiting
        get_rate_limiter().wait_if_needed()
        
        params = {
            "query": query,
            "key": self.api_key,
        }
        
        if page_token:
            params["pagetoken"] = page_token
        
        if region:
            params["region"] = region
        
        try:
            response = self.session.get(
                self.TEXT_SEARCH_ENDPOINT,
                params=params,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            # Record successful call
            get_api_tracker().record_call()
            
            data = response.json()
            return data, response.status_code
            
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"API request timed out after {config.REQUEST_TIMEOUT}s for query: {query}"
            )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Connection error: {str(e)}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                raise ValueError(
                    "Forbidden: Check your API key and ensure Places API is enabled"
                )
            raise Exception(f"HTTP {response.status_code}: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error in text_search: {str(e)}")
    
    def get_place_details(
        self,
        place_id: str,
        fields: Optional[list] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get detailed information about a place.
        
        Args:
            place_id: Google Place ID
            fields: Specific fields to fetch (more efficient)
        
        Returns:
            Tuple of (response_dict, status_code)
        """
        # Apply rate limiting
        get_rate_limiter().wait_if_needed()
        
        if fields is None:
            fields = ["website", "name", "rating", "user_ratings_total"]
        
        params = {
            "place_id": place_id,
            "fields": ",".join(fields),
            "key": self.api_key,
        }
        
        try:
            response = self.session.get(
                self.PLACE_DETAILS_ENDPOINT,
                params=params,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            get_api_tracker().record_call()
            
            data = response.json()
            return data, response.status_code
            
        except Exception as e:
            raise Exception(f"Error fetching place details: {str(e)}")
    
    @staticmethod
    def is_success_status(status: str) -> bool:
        """Check if API response status is successful."""
        return status in (
            GooglePlacesAPIClient.STATUS_OK,
            GooglePlacesAPIClient.STATUS_ZERO_RESULTS,
        )
    
    @staticmethod
    def is_quota_error(status: str) -> bool:
        """Check if error is related to quota."""
        return status == GooglePlacesAPIClient.STATUS_OVER_QUERY_LIMIT
    
    def close(self):
        """Close session."""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class CachedGooglePlacesAPIClient(GooglePlacesAPIClient):
    """
    Google Places API client with built-in result caching.
    Reduces API calls for repeated searches.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize cached API client."""
        super().__init__(api_key)
        self._search_cache: Dict[str, Dict[str, Any]] = {}
        self._details_cache: Dict[str, Dict[str, Any]] = {}
    
    def text_search(
        self,
        query: str,
        page_token: Optional[str] = None,
        region: Optional[str] = None,
        use_cache: bool = True,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Text search with optional caching.
        
        Args:
            query: Search query
            page_token: Pagination token
            region: Region bias
            use_cache: Whether to use cache for this search
        
        Returns:
            Tuple of (response_dict, status_code)
        """
        # Generate cache key (only cache first page)
        cache_key = f"{query}|{region}" if not page_token and use_cache else None
        
        if cache_key and cache_key in self._search_cache:
            return self._search_cache[cache_key], 200
        
        # Fetch from API
        result, status = super().text_search(query, page_token, region)
        
        # Cache first page results
        if cache_key:
            self._search_cache[cache_key] = result
        
        return result, status
    
    def get_place_details(
        self,
        place_id: str,
        fields: Optional[list] = None,
        use_cache: bool = True,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get place details with optional caching.
        
        Args:
            place_id: Place ID
            fields: Fields to fetch
            use_cache: Whether to use cache
        
        Returns:
            Tuple of (response_dict, status_code)
        """
        if use_cache and place_id in self._details_cache:
            return self._details_cache[place_id], 200
        
        result, status = super().get_place_details(place_id, fields)
        
        if use_cache:
            self._details_cache[place_id] = result
        
        return result, status
    
    def clear_caches(self):
        """Clear all caches."""
        self._search_cache.clear()
        self._details_cache.clear()
