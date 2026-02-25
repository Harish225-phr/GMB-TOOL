"""
Result deduplication using business name and website matching.
Merges results from multiple locations and identifies duplicates.
"""

from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
from .models import BusinessLead


class ResultDeduplicator:
    """
    Handles deduplication of business leads across multiple locations.
    Uses name + website as primary dedup key.
    """
    
    def __init__(self, similarity_threshold: float = 0.9):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Threshold for fuzzy matching (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.dedup_stats = {
            "total_input": 0,
            "total_output": 0,
            "duplicates_removed": 0,
            "by_location": defaultdict(int)
        }
    
    def deduplicate(
        self,
        leads_by_location: Dict[str, List[BusinessLead]],
        prefer_rating: bool = True
    ) -> Tuple[List[BusinessLead], Dict]:
        """
        Deduplicate leads across multiple locations.
        
        Args:
            leads_by_location: Dict mapping location to list of leads
            prefer_rating: Keep result with higher rating in duplicates
        
        Returns:
            Tuple of (unique_leads, stats)
        """
        self.dedup_stats = {
            "total_input": 0,
            "total_output": 0,
            "duplicates_removed": 0,
            "by_location": defaultdict(int)
        }
        
        # Track seen businesses by dedup key
        seen_keys: Dict[str, BusinessLead] = {}
        unique_leads: List[BusinessLead] = []
        
        # Count input leads
        for location, leads in leads_by_location.items():
            self.dedup_stats["total_input"] += len(leads)
            self.dedup_stats["by_location"][location] = len(leads)
        
        # Process each location's leads
        for location, leads in leads_by_location.items():
            for lead in leads:
                dedup_key = lead.get_dedup_key()
                
                if dedup_key in seen_keys:
                    # Duplicate found
                    self.dedup_stats["duplicates_removed"] += 1
                    
                    # Keep lead with higher rating if prefer_rating enabled
                    if prefer_rating:
                        existing_lead = seen_keys[dedup_key]
                        existing_rating = self._get_numeric_rating(
                            existing_lead.rating
                        )
                        new_rating = self._get_numeric_rating(lead.rating)
                        
                        if new_rating > existing_rating:
                            # Replace with better rated lead
                            old_index = self._find_lead_index(
                                unique_leads, existing_lead
                            )
                            if old_index >= 0:
                                unique_leads[old_index] = lead
                            seen_keys[dedup_key] = lead
                else:
                    # New unique lead
                    seen_keys[dedup_key] = lead
                    unique_leads.append(lead)
        
        self.dedup_stats["total_output"] = len(unique_leads)
        
        return unique_leads, self.dedup_stats
    
    def deduplicate_simple(
        self,
        all_leads: List[BusinessLead],
        keep_best: bool = True
    ) -> List[BusinessLead]:
        """
        Simple deduplication of a flat list.
        
        Args:
            all_leads: List of leads to deduplicate
            keep_best: Keep lead with highest rating among duplicates
        
        Returns:
            Deduplicated lead list
        """
        seen_keys: Dict[str, BusinessLead] = {}
        
        for lead in all_leads:
            dedup_key = lead.get_dedup_key()
            
            if dedup_key in seen_keys:
                if keep_best:
                    existing = seen_keys[dedup_key]
                    existing_rating = self._get_numeric_rating(existing.rating)
                    new_rating = self._get_numeric_rating(lead.rating)
                    
                    if new_rating > existing_rating:
                        seen_keys[dedup_key] = lead
            else:
                seen_keys[dedup_key] = lead
        
        return list(seen_keys.values())
    
    @staticmethod
    def _get_numeric_rating(rating) -> float:
        """Convert rating to float for comparison."""
        if rating is None or rating == "N/A":
            return 0.0
        try:
            return float(rating)
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def _find_lead_index(leads: List[BusinessLead], target: BusinessLead) -> int:
        """Find index of lead in list."""
        for i, lead in enumerate(leads):
            if (lead.name == target.name and 
                lead.website == target.website and
                lead.place_id == target.place_id):
                return i
        return -1
    
    def get_stats(self) -> Dict:
        """Get deduplication statistics."""
        return self.dedup_stats


class PrecisionMatcher:
    """
    Advanced matching using multiple fields for deduplication.
    More sophisticated than simple key matching.
    """
    
    @staticmethod
    def normalize_string(text: Optional[str]) -> str:
        """Normalize string for comparison."""
        if not text:
            return ""
        return text.lower().strip()
    
    @staticmethod
    def extract_domain(url: Optional[str]) -> Optional[str]:
        """Extract domain from URL for better matching."""
        if not url or url == "N/A":
            return None
        
        try:
            # Remove https/http
            url = url.replace("https://", "").replace("http://", "").strip()
            # Extract primary domain (remove www., subdomains, etc.)
            parts = url.split("/")[0].split(".")
            if len(parts) >= 2:
                return ".".join(parts[-2:])
            return url.split("/")[0]
        except Exception:
            return None
    
    @classmethod
    def calculate_match_score(
        cls,
        lead1: BusinessLead,
        lead2: BusinessLead
    ) -> float:
        """
        Calculate match score between two leads (0-1).
        
        Args:
            lead1: First lead
            lead2: Second lead
        
        Returns:
            Match score from 0 (no match) to 1 (exact match)
        """
        score = 0.0
        
        # Name matching (primary key)
        name1 = cls.normalize_string(lead1.name)
        name2 = cls.normalize_string(lead2.name)
        if name1 == name2:
            score += 0.6
        elif cls._similar_names(name1, name2):
            score += 0.3
        
        # Website/domain matching
        domain1 = cls.extract_domain(lead1.website)
        domain2 = cls.extract_domain(lead2.website)
        
        if domain1 and domain2:
            if domain1 == domain2:
                score += 0.4
        
        return min(1.0, score)
    
    @staticmethod
    def _similar_names(name1: str, name2: str) -> bool:
        """Check if names are similar (substring match)."""
        if not name1 or not name2:
            return False
        
        # If one is substring of other
        if name1 in name2 or name2 in name1:
            return True
        
        # Levenshtein distance could be used here for fuzzy matching
        # For now, simple substring match
        return False


class DuplicateDetector:
    """
    Detects duplicates with detailed analysis.
    """
    
    def __init__(self):
        self.duplicate_groups: List[List[BusinessLead]] = []
    
    def find_duplicate_groups(
        self,
        leads: List[BusinessLead],
        match_threshold: float = 0.8
    ) -> List[List[BusinessLead]]:
        """
        Find groups of duplicate leads.
        
        Args:
            leads: List of leads to analyze
            match_threshold: Threshold for considering as duplicate
        
        Returns:
            List of duplicate groups
        """
        self.duplicate_groups = []
        processed = set()
        
        for i, lead1 in enumerate(leads):
            if i in processed:
                continue
            
            group = [lead1]
            processed.add(i)
            
            for j, lead2 in enumerate(leads[i+1:], start=i+1):
                if j in processed:
                    continue
                
                score = PrecisionMatcher.calculate_match_score(lead1, lead2)
                
                if score >= match_threshold:
                    group.append(lead2)
                    processed.add(j)
            
            if len(group) > 1:
                self.duplicate_groups.append(group)
        
        return self.duplicate_groups
    
    def merge_duplicate_group(
        self,
        group: List[BusinessLead],
        strategy: str = "best_rating"
    ) -> BusinessLead:
        """
        Merge a group of duplicate leads into one.
        
        Args:
            group: List of duplicate leads
            strategy: Merging strategy (best_rating, most_complete, etc.)
        
        Returns:
            Merged lead
        """
        if not group:
            return None
        
        if strategy == "best_rating":
            return max(
                group,
                key=lambda l: ResultDeduplicator._get_numeric_rating(l.rating)
            )
        
        elif strategy == "most_complete":
            # Return lead with most fields filled
            return max(
                group,
                key=lambda l: sum([
                    1 for v in [l.name, l.website, l.rating, l.reviews_count]
                    if v is not None and v != "N/A"
                ])
            )
        
        # Default: return first
        return group[0]
    
    def get_duplicate_report(self) -> Dict:
        """Generate report on duplicates found."""
        total_leads = sum(len(group) for group in self.duplicate_groups)
        
        return {
            "total_duplicate_groups": len(self.duplicate_groups),
            "total_duplicate_leads": total_leads,
            "potential_saved_results": total_leads - len(self.duplicate_groups),
        }
