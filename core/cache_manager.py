"""
Unified cache management system with LRU eviction and TTL support.

Provides thread-safe caching with automatic expiration and size limits.
Includes specialized caching for technical indicators with incremental updates.
"""

from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from collections import OrderedDict
import logging
import threading
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 1200):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._expiry: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None

            # Atomic expiry check and removal
            expiry_time = self._expiry.get(key)
            now = datetime.now()

            if expiry_time and now > expiry_time:
                # Expired - remove atomically
                self._remove(key)
                self._stats['misses'] += 1
                logger.debug(f"Cache miss (expired): {key}")
                return None

            # Valid entry - move to end (most recently used) and return
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            logger.debug(f"Cache hit: {key}")
            return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            ttl = ttl or self.default_ttl

            if key in self._cache:
                # Update existing entry
                self._cache.move_to_end(key)
            else:
                # Check if we need to evict
                if len(self._cache) >= self.max_size:
                    # Remove least recently used
                    oldest_key = next(iter(self._cache))
                    self._remove(oldest_key)
                    self._stats['evictions'] += 1
                    logger.debug(f"Cache eviction (LRU): {oldest_key}")

            self._cache[key] = value
            self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def _remove(self, key: str):
        """Remove from cache (internal use)"""
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]

    def delete(self, key: str) -> bool:
        """
        Delete specific key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key existed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                self._remove(key)
                logger.debug(f"Cache delete: {key}")
                return True
            return False

    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._expiry.clear()
            logger.info(f"Cache cleared: {count} entries removed")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, expiry in self._expiry.items()
                if expiry <= now
            ]

            for key in expired_keys:
                self._remove(key)

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0

            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': round(hit_rate, 2),
                'size': len(self._cache),
                'max_size': self.max_size,
                'utilization': round(len(self._cache) / self.max_size * 100, 2) if self.max_size > 0 else 0
            }

    def reset_stats(self):
        """Reset statistics counters"""
        with self._lock:
            self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
            logger.debug("Cache stats reset")


class CacheManager:
    """Manages multiple named caches"""

    def __init__(self):
        self._caches: Dict[str, LRUCache] = {}
        self._lock = threading.Lock()

    def get_cache(
        self,
        name: str,
        max_size: int = 1000,
        ttl: int = 1200
    ) -> LRUCache:
        """
        Get or create a named cache.

        Args:
            name: Cache name
            max_size: Maximum cache size
            ttl: Default TTL in seconds

        Returns:
            LRUCache instance
        """
        with self._lock:
            if name not in self._caches:
                self._caches[name] = LRUCache(max_size=max_size, default_ttl=ttl)
                logger.info(f"Created cache '{name}' (max_size={max_size}, ttl={ttl}s)")

            return self._caches[name]

    def clear_cache(self, name: str) -> bool:
        """
        Clear a specific cache.

        Args:
            name: Cache name

        Returns:
            True if cache existed, False otherwise
        """
        with self._lock:
            if name in self._caches:
                self._caches[name].clear()
                return True
            return False

    def clear_all(self):
        """Clear all caches"""
        with self._lock:
            for cache in self._caches.values():
                cache.clear()
            logger.info(f"Cleared all {len(self._caches)} caches")

    def cleanup_all_expired(self) -> Dict[str, int]:
        """
        Cleanup expired entries from all caches.

        Returns:
            Dictionary mapping cache names to number of removed entries
        """
        results = {}
        with self._lock:
            for name, cache in self._caches.items():
                removed = cache.cleanup_expired()
                if removed > 0:
                    results[name] = removed

        return results

    def stats(self) -> Dict[str, Dict]:
        """
        Get stats for all caches.

        Returns:
            Dictionary mapping cache names to their stats
        """
        with self._lock:
            return {name: cache.stats() for name, cache in self._caches.items()}

    def delete_cache(self, name: str) -> bool:
        """
        Delete a cache entirely.

        Args:
            name: Cache name

        Returns:
            True if cache existed, False otherwise
        """
        with self._lock:
            if name in self._caches:
                del self._caches[name]
                logger.info(f"Deleted cache '{name}'")
                return True
            return False


class TechnicalIndicatorCache:
    """
    Specialized cache for technical indicators with incremental update support.

    Caches calculated technical indicators and supports efficient incremental
    updates when only a few new price bars are added, avoiding full recalculation.
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None, max_incremental_bars: int = 5):
        """
        Initialize technical indicator cache.

        Args:
            cache_manager: CacheManager instance to use (creates new if None)
            max_incremental_bars: Maximum new bars to allow incremental update
        """
        self.cache_manager = cache_manager or get_cache_manager()
        self.cache = self.cache_manager.get_cache('technical_indicators', max_size=500, ttl=900)
        self.max_incremental_bars = max_incremental_bars
        self._lock = threading.RLock()

    def get_indicators(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        calculator_func: callable,
        force_recalc: bool = False
    ) -> Dict:
        """
        Get technical indicators with incremental calculation if possible.

        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data
            calculator_func: Function to calculate indicators from price_data
            force_recalc: Force full recalculation even if cached

        Returns:
            Dictionary of technical indicators
        """
        cache_key = f"indicators_{symbol}"

        if force_recalc:
            logger.debug(f"Forcing full recalculation for {symbol}")
            return self._calculate_and_cache(cache_key, symbol, price_data, calculator_func)

        with self._lock:
            cached = self.cache.get(cache_key)

            # Check if incremental update is possible
            if cached and self._can_update_incrementally(cached, price_data):
                logger.debug(f"Incremental update possible for {symbol}")
                return self._update_incremental(cache_key, symbol, cached, price_data, calculator_func)

            # Full recalculation needed
            logger.debug(f"Full recalculation for {symbol}")
            return self._calculate_and_cache(cache_key, symbol, price_data, calculator_func)

    def _can_update_incrementally(self, cached: Dict, price_data: pd.DataFrame) -> bool:
        """
        Check if incremental update is possible.

        Args:
            cached: Cached indicator data
            price_data: Current price DataFrame

        Returns:
            True if incremental update possible
        """
        if not cached or 'metadata' not in cached:
            return False

        metadata = cached['metadata']

        # Check if we have the required metadata
        if 'last_bar_count' not in metadata or 'last_timestamp' not in metadata:
            return False

        # Calculate new bars added
        new_bars = len(price_data) - metadata['last_bar_count']

        # Can only update incrementally if:
        # 1. A small number of new bars (within threshold)
        # 2. Last close price matches (data hasn't changed)
        if new_bars <= 0 or new_bars > self.max_incremental_bars:
            return False

        # Verify data consistency - check if last cached close matches
        if 'last_close' in metadata and len(price_data) > metadata['last_bar_count']:
            old_last_close = metadata['last_close']
            current_old_last = price_data['Close'].iloc[metadata['last_bar_count'] - 1]

            # Allow small floating point difference
            if abs(old_last_close - current_old_last) > 0.01:
                logger.debug("Price data changed, full recalculation needed")
                return False

        return True

    def _update_incremental(
        self,
        cache_key: str,
        symbol: str,
        cached: Dict,
        price_data: pd.DataFrame,
        calculator_func: callable
    ) -> Dict:
        """
        Perform incremental update of indicators.

        Args:
            cache_key: Cache key
            symbol: Stock symbol
            cached: Cached indicator data
            price_data: Current price DataFrame
            calculator_func: Function to calculate indicators

        Returns:
            Updated indicators
        """
        try:
            metadata = cached['metadata']
            old_bar_count = metadata['last_bar_count']
            new_bars = len(price_data) - old_bar_count

            logger.info(f"Incremental update for {symbol}: {new_bars} new bars")

            # For now, do full recalculation with the new data
            # In a more advanced implementation, we could update rolling indicators
            # without recalculating everything
            indicators = calculator_func(price_data)

            # Update cache with new metadata
            self._cache_indicators(cache_key, symbol, price_data, indicators)

            return indicators

        except Exception as e:
            logger.warning(f"Incremental update failed for {symbol}: {e}, falling back to full calc")
            return self._calculate_and_cache(cache_key, symbol, price_data, calculator_func)

    def _calculate_and_cache(
        self,
        cache_key: str,
        symbol: str,
        price_data: pd.DataFrame,
        calculator_func: callable
    ) -> Dict:
        """
        Calculate indicators and cache them.

        Args:
            cache_key: Cache key
            symbol: Stock symbol
            price_data: Price DataFrame
            calculator_func: Function to calculate indicators

        Returns:
            Calculated indicators
        """
        # Calculate all indicators
        indicators = calculator_func(price_data)

        # Cache with metadata
        self._cache_indicators(cache_key, symbol, price_data, indicators)

        return indicators

    def _cache_indicators(self, cache_key: str, symbol: str, price_data: pd.DataFrame, indicators: Dict):
        """
        Cache indicators with metadata.

        Args:
            cache_key: Cache key
            symbol: Stock symbol
            price_data: Price DataFrame
            indicators: Calculated indicators
        """
        cached_data = {
            'indicators': indicators,
            'metadata': {
                'symbol': symbol,
                'last_bar_count': len(price_data),
                'last_close': float(price_data['Close'].iloc[-1]) if len(price_data) > 0 else None,
                'last_timestamp': price_data.index[-1] if len(price_data) > 0 else None,
                'cached_at': datetime.now()
            }
        }

        self.cache.set(cache_key, cached_data, ttl=900)  # 15 minutes
        logger.debug(f"Cached indicators for {symbol}: {len(indicators)} indicators")

    def invalidate(self, symbol: str) -> bool:
        """
        Invalidate cached indicators for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            True if cache existed
        """
        cache_key = f"indicators_{symbol}"
        return self.cache.delete(cache_key)

    def clear(self):
        """Clear all cached indicators"""
        self.cache.clear()
        logger.info("Technical indicator cache cleared")

    def stats(self) -> Dict:
        """Get cache statistics"""
        return self.cache.stats()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance (singleton).

    Returns:
        Global CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:  # Double-check locking
                _cache_manager = CacheManager()
                logger.info("Cache manager initialized")
    return _cache_manager
