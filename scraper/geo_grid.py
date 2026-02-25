"""
Geographic grid expansion for multi-area searches.
Expands a single city into multiple sub-areas for broader result coverage.
"""

from typing import List, Optional, Dict, Set
from .config import GeoGridAreas


class GeoGridExpander:
    """
    Manages geographic grid expansion for cities.
    Transforms single location into multiple search areas.
    """
    
    def __init__(self, enable_expansion: bool = True):
        """
        Initialize geo-grid expander.
        
        Args:
            enable_expansion: Whether to enable automatic expansion
        """
        self.enable_expansion = enable_expansion
        self.custom_grids: Dict[str, List[str]] = {}
    
    def add_custom_grid(self, city: str, areas: List[str]):
        """
        Add custom geographic grid for a city.
        
        Args:
            city: City name
            areas: List of areas to search within city
        """
        self.custom_grids[city.lower().strip()] = areas
    
    def expand_location(self, location: str) -> List[str]:
        """
        Expand a location into multiple search areas.
        
        Args:
            location: City or location name
        
        Returns:
            List of locations to search (original + areas if available)
        """
        if not self.enable_expansion:
            return [location]
        
        location_lower = location.lower().strip()
        
        # Check custom grids first
        if location_lower in self.custom_grids:
            return [location] + self.custom_grids[location_lower]
        
        # Check predefined grids
        areas = GeoGridAreas.get_areas(location)
        if areas:
            return [location] + areas
        
        # No grid available, return original location
        return [location]
    
    def get_expanded_locations(self, location: str) -> List[str]:
        """
        Get all expanded locations for a search.
        Alias for expand_location for clarity.
        """
        return self.expand_location(location)
    
    def has_expansion(self, location: str) -> bool:
        """Check if location has predefined expansion."""
        location_lower = location.lower().strip()
        return (
            location_lower in self.custom_grids or
            GeoGridAreas.has_geo_grid(location)
        )
    
    def get_expansion_info(self, location: str) -> Optional[Dict]:
        """
        Get expansion information for a location.
        
        Returns:
            Dict with expansion details or None
        """
        location_lower = location.lower().strip()
        
        # Check custom grid
        if location_lower in self.custom_grids:
            return {
                "type": "custom",
                "primary_location": location,
                "areas": self.custom_grids[location_lower],
                "total_searches": len(self.custom_grids[location_lower]) + 1,
            }
        
        # Check predefined grid
        city_data = GeoGridAreas.CITY_AREAS.get(location_lower)
        if city_data:
            return {
                "type": "predefined",
                "primary_location": location,
                "description": city_data["description"],
                "areas": city_data["areas"],
                "total_searches": len(city_data["areas"]) + 1,
            }
        
        # No expansion
        return None


class SearchLocationManager:
    """
    Manages search locations and coordinates multi-location searches.
    """
    
    def __init__(self, expander: Optional[GeoGridExpander] = None):
        """
        Initialize search location manager.
        
        Args:
            expander: GeoGridExpander instance (creates new if None)
        """
        self.expander = expander or GeoGridExpander()
        self.search_history: List[Dict] = []
    
    def get_search_locations(
        self,
        primary_location: str,
        use_expansion: bool = True
    ) -> List[str]:
        """
        Get all locations to search.
        
        Args:
            primary_location: Initial location
            use_expansion: Whether to apply geo-grid expansion
        
        Returns:
            List of all locations to search
        """
        if use_expansion and self.expander.has_expansion(primary_location):
            return self.expander.expand_location(primary_location)
        
        return [primary_location]
    
    def record_search(
        self,
        keyword: str,
        primary_location: str,
        locations_searched: List[str],
        results_count: int,
        use_expansion: bool = True
    ):
        """
        Record a search in history.
        
        Args:
            keyword: Search keyword
            primary_location: Primary location
            locations_searched: All locations searched
            results_count: Number of results found
            use_expansion: Whether expansion was used
        """
        self.search_history.append({
            "keyword": keyword,
            "primary_location": primary_location,
            "locations_searched": locations_searched,
            "results_count": results_count,
            "used_expansion": use_expansion,
            "areas_expanded": len(locations_searched) - 1,
        })
    
    def get_search_history(self) -> List[Dict]:
        """Get search history."""
        return self.search_history


# Geo-grid expansion utility functions

def suggest_alternate_searches(
    keyword: str,
    location: str,
    max_suggestions: int = 5
) -> Dict[str, List[str]]:
    """
    Suggest alternative search strategies for a location.
    
    Args:
        keyword: Search keyword
        location: Location name
        max_suggestions: Max suggestions to return
    
    Returns:
        Dict with search strategy suggestions
    """
    expander = GeoGridExpander()
    expansion_info = expander.get_expansion_info(location)
    
    suggestions = {
        "keyword": keyword,
        "location": location,
        "strategies": []
    }
    
    if expansion_info:
        suggestions["strategies"].append({
            "name": "Geo-Grid Expansion",
            "description": f"Search across {expansion_info.get('total_searches')} areas",
            "type": expansion_info.get("type"),
            "areas": expansion_info.get("areas")[:max_suggestions],
        })
    
    suggestions["strategies"].append({
        "name": "Single Location",
        "description": "Search only primary location",
        "type": "single",
    })
    
    return suggestions


def estimate_api_calls(
    keyword: str,
    location: str,
    use_expansion: bool = True,
    max_results_per_location: int = 60,
    results_per_page: int = 20
) -> Dict:
    """
    Estimate API calls needed for a search.
    
    Args:
        keyword: Search keyword
        location: Location
        use_expansion: Whether to use expansion
        max_results_per_location: Max results per location
        results_per_page: Results per API page
    
    Returns:
        Dict with API call estimates
    """
    expander = GeoGridExpander()
    
    if use_expansion:
        locations = expander.expand_location(location)
        num_areas = len(locations)
    else:
        locations = [location]
        num_areas = 1
    
    # Calculate pages needed per location
    pages_per_location = (max_results_per_location + results_per_page - 1) // results_per_page
    
    # Calculate place details calls (for website fetching)
    details_calls_per_location = max_results_per_location
    
    return {
        "keyword": keyword,
        "primary_location": location,
        "use_expansion": use_expansion,
        "total_areas": num_areas,
        "text_search_calls": num_areas * pages_per_location,
        "place_details_calls": num_areas * details_calls_per_location,
        "total_api_calls": (
            num_areas * pages_per_location +
            num_areas * details_calls_per_location
        ),
        "details_per_area": details_calls_per_location,
    }
