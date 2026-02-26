"""
Batch processing module for multi-location searches.
Enables frontend-controlled batch processing to prevent timeouts on free tier.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 2  # Process 2-3 locations per batch
    max_retries: int = 3
    timeout_per_batch: int = 45  # 45 seconds per batch to stay safe
    enable_streaming: bool = True
    

@dataclass
class BatchMetadata:
    """Metadata for a batch processing session."""
    session_id: str
    keyword: str
    locations: List[str]
    use_expansion: bool
    fetch_websites: bool
    batch_size: int
    
    total_batches: int = field(init=False)
    total_locations: int = field(init=False)
    current_batch_index: int = 0
    completed_locations: List[str] = field(default_factory=list)
    failed_locations: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        self.total_locations = len(self.locations)
        self.total_batches = (self.total_locations + self.batch_size - 1) // self.batch_size
    
    def get_current_batch(self) -> List[str]:
        """Get locations for current batch."""
        start_idx = self.current_batch_index * self.batch_size
        end_idx = start_idx + self.batch_size
        return self.locations[start_idx:end_idx]
    
    def has_next_batch(self) -> bool:
        """Check if there's a next batch."""
        return self.current_batch_index < self.total_batches - 1
    
    def advance_batch(self) -> bool:
        """Move to next batch."""
        if self.has_next_batch():
            self.current_batch_index += 1
            return True
        return False
    
    def mark_location_completed(self, location: str):
        """Mark location as completed."""
        if location not in self.completed_locations:
            self.completed_locations.append(location)
    
    def mark_location_failed(self, location: str):
        """Mark location as failed."""
        if location not in self.failed_locations:
            self.failed_locations.append(location)
    
    def get_progress(self) -> Dict:
        """Get progress metrics."""
        elapsed = time.time() - self.start_time
        total_processed = len(self.completed_locations) + len(self.failed_locations)
        
        return {
            "session_id": self.session_id,
            "current_batch": self.current_batch_index + 1,
            "total_batches": self.total_batches,
            "locations_completed": len(self.completed_locations),
            "locations_failed": len(self.failed_locations),
            "total_locations": self.total_locations,
            "percent_complete": round((total_processed / self.total_locations * 100), 1),
            "elapsed_seconds": elapsed,
            "estimated_total_seconds": round(elapsed / max(total_processed, 1) * self.total_locations, 1),
            "has_next_batch": self.has_next_batch(),
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "keyword": self.keyword,
            "locations": self.locations,
            "use_expansion": self.use_expansion,
            "fetch_websites": self.fetch_websites,
            "batch_size": self.batch_size,
            "total_batches": self.total_batches,
            "total_locations": self.total_locations,
            "current_batch_index": self.current_batch_index,
            "completed_locations": self.completed_locations,
            "failed_locations": self.failed_locations,
        }


class BatchProcessor:
    """Manages batch processing of multi-location searches."""
    
    def __init__(self, batch_config: Optional[BatchConfig] = None):
        """Initialize batch processor."""
        self.config = batch_config or BatchConfig()
        self.sessions: Dict[str, BatchMetadata] = {}
    
    def create_session(
        self,
        session_id: str,
        keyword: str,
        locations: List[str],
        use_expansion: bool = False,
        fetch_websites: bool = True,
        batch_size: Optional[int] = None,
    ) -> BatchMetadata:
        """Create a new batch processing session."""
        batch_size = batch_size or self.config.batch_size
        
        metadata = BatchMetadata(
            session_id=session_id,
            keyword=keyword,
            locations=locations,
            use_expansion=use_expansion,
            fetch_websites=fetch_websites,
            batch_size=batch_size,
        )
        
        self.sessions[session_id] = metadata
        
        logger.info(
            f"Batch session created: {session_id} "
            f"({len(locations)} locations, {metadata.total_batches} batches)"
        )
        
        return metadata
    
    def get_session(self, session_id: str) -> Optional[BatchMetadata]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def get_current_batch(self, session_id: str) -> Optional[List[str]]:
        """Get locations for current batch."""
        metadata = self.get_session(session_id)
        if metadata:
            return metadata.get_current_batch()
        return None
    
    def advance_batch(self, session_id: str) -> bool:
        """Advance to next batch."""
        metadata = self.get_session(session_id)
        if metadata:
            return metadata.advance_batch()
        return False
    
    def mark_location_completed(self, session_id: str, location: str):
        """Mark location as completed."""
        metadata = self.get_session(session_id)
        if metadata:
            metadata.mark_location_completed(location)
    
    def mark_location_failed(self, session_id: str, location: str):
        """Mark location as failed."""
        metadata = self.get_session(session_id)
        if metadata:
            metadata.mark_location_failed(location)
    
    def get_progress(self, session_id: str) -> Optional[Dict]:
        """Get session progress."""
        metadata = self.get_session(session_id)
        if metadata:
            return metadata.get_progress()
        return None
    
    def cleanup_session(self, session_id: str):
        """Clean up completed session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Batch session cleaned up: {session_id}")
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get complete session summary."""
        metadata = self.get_session(session_id)
        if metadata:
            return {
                "metadata": metadata.to_dict(),
                "progress": metadata.get_progress(),
            }
        return None


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get or create global batch processor."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor


def initialize_batch_processor(config: Optional[BatchConfig] = None):
    """Initialize global batch processor."""
    global _batch_processor
    _batch_processor = BatchProcessor(config)
