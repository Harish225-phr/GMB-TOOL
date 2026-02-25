"""
Rate limiting and concurrency control for Google Places API.
Prevents hitting API quotas and quota resets.
"""

import time
import threading
from threading import Lock, Semaphore
from collections import deque
from typing import Optional
from datetime import datetime, timedelta


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rate.
    Allows configurable requests per second with burst capacity.
    """
    
    def __init__(self, calls_per_second: float = 5, max_burst: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Target number of requests per second
            max_burst: Maximum burst capacity (defaults to calls_per_second)
        """
        self.calls_per_second = calls_per_second
        self.max_burst = max_burst or int(calls_per_second)
        self.tokens = float(self.max_burst)
        self.last_update_time = time.time()
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Wait until a token is available."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update_time
            
            # Add new tokens based on elapsed time
            self.tokens = min(
                self.max_burst,
                self.tokens + (elapsed * self.calls_per_second)
            )
            self.last_update_time = now
            
            # If no tokens available, calculate wait time
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.calls_per_second
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ConcurrencyController:
    """
    Manages concurrent API calls using semaphore.
    Prevents exceeding maximum concurrent requests.
    """
    
    def __init__(self, max_concurrent: int = 5):
        """
        Initialize concurrency controller.
        
        Args:
            max_concurrent: Maximum number of concurrent requests
        """
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        self.active_count = 0
        self.lock = Lock()
    
    def __enter__(self):
        """Context manager entry - acquire semaphore."""
        self.semaphore.acquire()
        with self.lock:
            self.active_count += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - release semaphore."""
        with self.lock:
            self.active_count -= 1
        self.semaphore.release()
    
    def get_active_count(self) -> int:
        """Get current number of active requests."""
        with self.lock:
            return self.active_count


class APICallTracker:
    """
    Tracks API calls to prevent quota exhaustion.
    Monitors calls per minute and helps identify quota issues.
    """
    
    def __init__(self, window_size_minutes: int = 60):
        """
        Initialize API call tracker.
        
        Args:
            window_size_minutes: Time window for tracking (default 60 minutes)
        """
        self.window_size = timedelta(minutes=window_size_minutes)
        self.calls = deque()  # Store timestamps of API calls
        self.lock = Lock()
    
    def record_call(self):
        """Record an API call."""
        with self.lock:
            now = datetime.now()
            self.calls.append(now)
            # Remove old calls outside the window
            self._cleanup_old_calls(now)
    
    def record_error(self, error_type: str):
        """Record an API error."""
        pass  # Can be extended to track specific errors
    
    def get_call_count(self) -> int:
        """Get number of calls in current window."""
        with self.lock:
            now = datetime.now()
            self._cleanup_old_calls(now)
            return len(self.calls)
    
    def get_calls_per_minute(self) -> float:
        """Get average calls per minute."""
        call_count = self.get_call_count()
        return (call_count / self.window_size.total_seconds()) * 60 if call_count else 0
    
    def _cleanup_old_calls(self, now: datetime):
        """Remove calls older than window size."""
        cutoff = now - self.window_size
        while self.calls and self.calls[0] < cutoff:
            self.calls.popleft()


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on API responses.
    Slows down if quota warnings are detected.
    """
    
    def __init__(self, initial_calls_per_second: float = 5):
        """Initialize adaptive rate limiter."""
        self.base_rate = initial_calls_per_second
        self.current_rate = initial_calls_per_second
        self.lock = Lock()
        self.rate_limiter = RateLimiter(initial_calls_per_second)
        self.backoff_multiplier = 0.5
        self.recovery_multiplier = 1.1
        self.min_rate = 0.1  # Minimum 1 request per 10 seconds
    
    def wait_if_needed(self):
        """Wait based on current adaptive rate."""
        with self.lock:
            self.rate_limiter = RateLimiter(self.current_rate)
        self.rate_limiter.wait_if_needed()
    
    def handle_quota_warning(self):
        """Reduce rate when quota warning received."""
        with self.lock:
            old_rate = self.current_rate
            self.current_rate = max(
                self.min_rate,
                self.current_rate * self.backoff_multiplier
            )
            print(f"[RATE_LIMIT] Quota warning: reduced rate {old_rate} -> {self.current_rate}")
    
    def handle_success(self):
        """Gradually increase rate on successful calls."""
        with self.lock:
            if self.current_rate < self.base_rate:
                self.current_rate = min(
                    self.base_rate,
                    self.current_rate * self.recovery_multiplier
                )
    
    def reset(self):
        """Reset to base rate."""
        with self.lock:
            self.current_rate = self.base_rate


# Global instances
_rate_limiter = None
_concurrency_controller = None
_api_tracker = None


def initialize_rate_limiting(calls_per_second: float = 5, max_concurrent: int = 3):
    """Initialize global rate limiting and concurrency control."""
    global _rate_limiter, _concurrency_controller, _api_tracker
    
    _rate_limiter = RateLimiter(calls_per_second)
    _concurrency_controller = ConcurrencyController(max_concurrent)
    _api_tracker = APICallTracker(window_size_minutes=60)


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        initialize_rate_limiting()
    return _rate_limiter


def get_concurrency_controller() -> ConcurrencyController:
    """Get global concurrency controller instance."""
    global _concurrency_controller
    if _concurrency_controller is None:
        initialize_rate_limiting()
    return _concurrency_controller


def get_api_tracker() -> APICallTracker:
    """Get global API call tracker instance."""
    global _api_tracker
    if _api_tracker is None:
        initialize_rate_limiting()
    return _api_tracker
