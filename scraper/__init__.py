"""
Lead Scraper Package
Production-grade Google Maps lead generation engine with geo-grid expansion, caching, and deduplication.
"""

from .lead_scraper import LeadScraperEngine, search_leads
from .config import config, AppConfig, GeoGridAreas
from .models import BusinessLead, SearchResult, AggregatedSearchResult
from .api_client import GooglePlacesAPIClient, CachedGooglePlacesAPIClient
from .geo_grid import GeoGridExpander, SearchLocationManager
from .deduplicator import ResultDeduplicator, PrecisionMatcher
from .website_extractor import WebsiteExtractor, OptionalWebsiteFetcher
from .cache_manager import SearchResultCache, SmartSearchCache
from .rate_limiter import (
    RateLimiter,
    ConcurrencyController,
    AdaptiveRateLimiter,
    initialize_rate_limiting
)

__version__ = "2.0.0"
__all__ = [
    "LeadScraperEngine",
    "search_leads",
    "config",
    "AppConfig",
    "BusinessLead",
    "SearchResult",
    "AggregatedSearchResult",
    "GooglePlacesAPIClient",
    "CachedGooglePlacesAPIClient",
    "GeoGridExpander",
    "ResultDeduplicator",
    "WebsiteExtractor",
    "SearchResultCache",
]
