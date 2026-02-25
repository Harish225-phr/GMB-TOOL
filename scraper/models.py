"""
Data models and type definitions for lead scraping.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class BusinessLead:
    """
    Represents a single business lead from Google Places API.
    """
    name: str
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    website: Optional[str] = None
    place_id: Optional[str] = None
    location: Optional[str] = None  # Search location this result came from
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "rating": self.rating if self.rating else "N/A",
            "reviews": self.reviews_count if self.reviews_count else "N/A",
            "website": self.website if self.website else "N/A",
        }
    
    def get_dedup_key(self) -> str:
        """Generate unique key for deduplication (name + website)."""
        website_part = (self.website or "").lower().strip()
        name_part = self.name.lower().strip()
        return f"{name_part}|||{website_part}"


@dataclass
class SearchResult:
    """
    Represents complete search results for a keyword-location pair.
    """
    keyword: str
    location: str
    results: List[BusinessLead] = field(default_factory=list)
    next_page_token: Optional[str] = None
    total_results_found: int = 0
    total_pages_fetched: int = 0
    search_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "keyword": self.keyword,
            "location": self.location,
            "results": [r.to_dict() for r in self.results],
            "next_page_token": self.next_page_token,
            "total_results": len(self.results),
            "total_pages_fetched": self.total_pages_fetched,
        }


@dataclass
class AggregatedSearchResult:
    """
    Represents aggregated results from multiple locations (geo-grid expansion).
    """
    keyword: str
    primary_location: str
    results: List[BusinessLead] = field(default_factory=list)  # Deduplicated results
    results_by_location: Dict[str, int] = field(default_factory=dict)  # Count per location
    total_unique_results: int = 0
    total_results_before_dedup: int = 0
    dedup_count: int = 0  # Number of duplicates removed
    search_timestamp: datetime = field(default_factory=datetime.now)
    expanded_locations: List[str] = field(default_factory=list)  # All locations searched
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "keyword": self.keyword,
            "location": self.primary_location,
            "results": [r.to_dict() for r in self.results],
            "total_unique_results": self.total_unique_results,
            "duplicates_removed": self.dedup_count,
            "results_by_location": self.results_by_location,
            "expanded_locations": self.expanded_locations,
        }


@dataclass
class ApiCallMetrics:
    """Track API call metrics for monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_results_fetched: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_time_seconds: float = 0.0
