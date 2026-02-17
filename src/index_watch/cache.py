"""Simple in-memory cache with TTL for market data."""

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CachedData(Generic[T]):
    """Cached data with timestamp and TTL."""

    data: T
    fetched_at: datetime
    ttl_seconds: int

    def is_expired(self) -> bool:
        """Check if cached data has expired."""
        age = datetime.now(timezone.utc) - self.fetched_at
        return age.total_seconds() > self.ttl_seconds


class DataCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self):
        self._cache: dict[str, CachedData] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[Any, datetime] | None:
        """
        Get cached data if not expired.

        Returns:
            tuple of (data, fetched_at) if valid cache exists, None otherwise
        """
        with self._lock:
            cached = self._cache.get(key)
            if cached and not cached.is_expired():
                return cached.data, cached.fetched_at
            # Remove expired entry
            if cached:
                del self._cache[key]
            return None

    def set(self, key: str, data: Any, ttl_seconds: int) -> None:
        """Store data with TTL in cache."""
        with self._lock:
            self._cache[key] = CachedData(
                data=data, fetched_at=datetime.now(timezone.utc), ttl_seconds=ttl_seconds
            )

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()

    def keys(self) -> list[str]:
        """Get all cache keys (for debugging)."""
        with self._lock:
            return list(self._cache.keys())


# Global cache instance
_global_cache = DataCache()


def get_cache() -> DataCache:
    """Get the global cache instance."""
    return _global_cache
