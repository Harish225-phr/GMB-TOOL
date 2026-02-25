"""
Enhanced cache management for search results.
Reduces API calls and improves response times.
"""

import json
import hashlib
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import threading

from .models import SearchResult, BusinessLead


class CacheKey:
    """Generates cache keys for searches."""
    
    @staticmethod
    def generate_search_key(keyword: str, location: str) -> str:
        """
        Generate cache key for a search.
        
        Args:
            keyword: Search keyword
            location: Search location
        
        Returns:
            Cache key string
        """
        key_string = f"{keyword.lower().strip()}||{location.lower().strip()}"
        hash_value = hashlib.md5(key_string.encode()).hexdigest()
        return f"search_{hash_value}"
    
    @staticmethod
    def generate_expanded_search_key(
        keyword: str,
        primary_location: str,
        expanded_locations: List[str]
    ) -> str:
        """
        Generate cache key for expanded multi-location search.
        
        Args:
            keyword: Search keyword
            primary_location: Primary location
            expanded_locations: List of all searched locations
        
        Returns:
            Cache key string
        """
        locations_str = "||".join(sorted([l.lower().strip() for l in expanded_locations]))
        key_string = f"{keyword.lower().strip()}||{primary_location.lower().strip()}||{locations_str}"
        hash_value = hashlib.md5(key_string.encode()).hexdigest()
        return f"search_expanded_{hash_value}"


class CacheEntry:
    """Represents a cached entry with metadata."""
    
    def __init__(
        self,
        data: Dict[str, Any],
        ttl_seconds: int = 3600,
        key: Optional[str] = None
    ):
        """
        Initialize cache entry.
        
        Args:
            data: Data to cache
            ttl_seconds: Time to live in seconds
            key: Cache key
        """
        self.data = data
        self.ttl_seconds = ttl_seconds
        self.created_at = datetime.now()
        self.accessed_at = datetime.now()
        self.access_count = 0
        self.key = key
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry
    
    def get_time_remaining(self) -> float:
        """Get time remaining in seconds."""
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        remaining = (expiry - datetime.now()).total_seconds()
        return max(0, remaining)
    
    def touch(self):
        """Update access time and count."""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "data": self.data,
            "ttl": self.ttl_seconds,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "time_remaining": self.get_time_remaining(),
        }


class SearchResultCache:
    """
    Cache for search results with TTL support.
    Thread-safe caching for search operations.
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize search result cache.
        
        Args:
            default_ttl: Default TTL in seconds (1 hour default)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
    
    def get(self, key: str) -> Optional[Dict]:
        """
        Get cached result.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data or None
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self.stats["misses"] += 1
                return None
            
            if entry.is_expired():
                self.stats["evictions"] += 1
                del self._cache[key]
                return None
            
            entry.touch()
            self.stats["hits"] += 1
            return entry.data
    
    def set(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Set cache value.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: TTL in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        entry = CacheEntry(data, ttl, key)
        
        with self._lock:
            self._cache[key] = entry
    
    def delete(self, key: str):
        """Delete cache entry."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache."""
        with self._lock:
            self._cache.clear()
            self.stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def cleanup_expired(self):
        """Remove expired entries."""
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
                self.stats["evictions"] += len(expired_keys)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            total_hits = self.stats["hits"]
            total_misses = self.stats["misses"]
            total = total_hits + total_misses
            hit_ratio = (
                (total_hits / total * 100) if total > 0 else 0
            )
            
            return {
                "hits": total_hits,
                "misses": total_misses,
                "hit_ratio_percent": round(hit_ratio, 2),
                "evictions": self.stats["evictions"],
                "cache_size": len(self._cache),
            }
    
    def get_cache_info(self) -> Dict:
        """Get detailed cache information."""
        with self._lock:
            entries_info = []
            for key, entry in self._cache.items():
                entries_info.append({
                    "key": key,
                    "time_remaining": entry.get_time_remaining(),
                    "access_count": entry.access_count,
                    "size_estimate": len(str(entry.data)),
                })
            
            return {
                "total_entries": len(self._cache),
                "entries": entries_info[:10],  # Limit to 10 for API response
                **self.get_stats(),
            }


class SmartSearchCache:
    """
    Advanced cache that can cache partial results and support pagination.
    """
    
    def __init__(self, base_cache: Optional[SearchResultCache] = None):
        """
        Initialize smart search cache.
        
        Args:
            base_cache: Underlying cache implementation
        """
        self.cache = base_cache or SearchResultCache(
            default_ttl=3600
        )
        self.pagination_cache: Dict[str, List[str]] = {}  # page_tokens by search
        self._lock = threading.Lock()
    
    def get_search_results(
        self,
        keyword: str,
        location: str,
        page_token: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get cached search results, optionally for specific page.
        
        Args:
            keyword: Search keyword
            location: Search location
            page_token: Pagination token (not used for caching currently)
        
        Returns:
            Cached result dict or None
        """
        # First page calls get cached
        if not page_token:
            key = CacheKey.generate_search_key(keyword, location)
            return self.cache.get(key)
        
        return None
    
    def cache_search_results(
        self,
        keyword: str,
        location: str,
        results: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Cache search results.
        
        Args:
            keyword: Search keyword
            location: Search location
            results: Results to cache
            ttl: Custom TTL
        """
        key = CacheKey.generate_search_key(keyword, location)
        self.cache.set(key, results, ttl)
    
    def cache_expanded_search_results(
        self,
        keyword: str,
        primary_location: str,
        expanded_locations: List[str],
        results: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Cache multi-location expanded search results.
        
        Args:
            keyword: Search keyword
            primary_location: Primary location
            expanded_locations: All searched locations
            results: Results to cache
            ttl: Custom TTL
        """
        key = CacheKey.generate_expanded_search_key(
            keyword,
            primary_location,
            expanded_locations
        )
        self.cache.set(key, results, ttl)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self.cache.get_stats()


# Global cache instance
_global_cache: Optional[SearchResultCache] = None


def initialize_global_cache(default_ttl: int = 3600):
    """Initialize global search result cache."""
    global _global_cache
    _global_cache = SearchResultCache(default_ttl)


def get_global_cache() -> SearchResultCache:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        initialize_global_cache()
    return _global_cache
