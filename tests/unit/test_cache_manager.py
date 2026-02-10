"""
Unit tests for Cache Manager functionality.

Tests LRU cache, TTL expiration, and technical indicator caching.
"""

import pytest
import time
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.cache_manager import LRUCache, CacheManager, TechnicalIndicatorCache, get_cache_manager


class TestLRUCache:
    """Test suite for LRUCache class"""

    def test_basic_set_and_get(self):
        """Test basic cache set and get operations"""
        cache = LRUCache(max_size=10, default_ttl=60)

        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

        cache.set('key2', {'nested': 'dict'})
        assert cache.get('key2') == {'nested': 'dict'}

    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = LRUCache(max_size=10, default_ttl=60)
        assert cache.get('nonexistent') is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = LRUCache(max_size=3, default_ttl=60)

        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)

        # Access 'a' to make it recently used
        cache.get('a')

        # Add 'd' - should evict 'b' (least recently used)
        cache.set('d', 4)

        assert cache.get('a') == 1  # Still present
        assert cache.get('b') is None  # Evicted
        assert cache.get('c') == 3  # Still present
        assert cache.get('d') == 4  # Newly added

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = LRUCache(max_size=10, default_ttl=1)

        cache.set('key', 'value', ttl=1)
        assert cache.get('key') == 'value'

        # Wait for expiration
        time.sleep(1.2)

        assert cache.get('key') is None

    def test_update_existing_key(self):
        """Test updating an existing key"""
        cache = LRUCache(max_size=10, default_ttl=60)

        cache.set('key', 'value1')
        assert cache.get('key') == 'value1'

        cache.set('key', 'value2')
        assert cache.get('key') == 'value2'

    def test_delete_key(self):
        """Test deleting a key"""
        cache = LRUCache(max_size=10, default_ttl=60)

        cache.set('key', 'value')
        assert cache.get('key') == 'value'

        result = cache.delete('key')
        assert result is True
        assert cache.get('key') is None

        # Deleting non-existent key
        result = cache.delete('nonexistent')
        assert result is False

    def test_clear_cache(self):
        """Test clearing the entire cache"""
        cache = LRUCache(max_size=10, default_ttl=60)

        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')

        cache.clear()

        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert cache.get('key3') is None

    def test_cleanup_expired(self):
        """Test cleanup of expired entries"""
        cache = LRUCache(max_size=10, default_ttl=1)

        cache.set('key1', 'value1', ttl=1)
        cache.set('key2', 'value2', ttl=1)
        cache.set('key3', 'value3', ttl=60)  # Won't expire

        time.sleep(1.2)

        removed = cache.cleanup_expired()
        assert removed == 2

        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert cache.get('key3') == 'value3'

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = LRUCache(max_size=5, default_ttl=60)

        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Generate hits and misses
        cache.get('key1')  # Hit
        cache.get('key1')  # Hit
        cache.get('nonexistent')  # Miss

        stats = cache.stats()

        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 66.67
        assert stats['size'] == 2
        assert stats['max_size'] == 5

    def test_thread_safety(self):
        """Test thread-safe operations"""
        cache = LRUCache(max_size=100, default_ttl=60)
        results = []

        def worker(thread_id):
            for i in range(10):
                cache.set(f'key_{thread_id}_{i}', i)
                value = cache.get(f'key_{thread_id}_{i}')
                if value is not None:
                    results.append(value)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Most operations should succeed (allowing for some race conditions)
        assert len(results) >= 80


class TestCacheManager:
    """Test suite for CacheManager class"""

    def test_get_cache(self):
        """Test getting or creating named caches"""
        manager = CacheManager()

        cache1 = manager.get_cache('test1', max_size=10, ttl=60)
        cache2 = manager.get_cache('test2', max_size=20, ttl=120)

        # Same name should return same cache
        cache1_again = manager.get_cache('test1')
        assert cache1 is cache1_again

        # Different names should return different caches
        assert cache1 is not cache2

    def test_clear_specific_cache(self):
        """Test clearing a specific named cache"""
        manager = CacheManager()

        cache1 = manager.get_cache('cache1')
        cache2 = manager.get_cache('cache2')

        cache1.set('key', 'value1')
        cache2.set('key', 'value2')

        result = manager.clear_cache('cache1')
        assert result is True

        assert cache1.get('key') is None
        assert cache2.get('key') == 'value2'

    def test_clear_all_caches(self):
        """Test clearing all caches"""
        manager = CacheManager()

        cache1 = manager.get_cache('cache1')
        cache2 = manager.get_cache('cache2')

        cache1.set('key', 'value1')
        cache2.set('key', 'value2')

        manager.clear_all()

        assert cache1.get('key') is None
        assert cache2.get('key') is None

    def test_cleanup_all_expired(self):
        """Test cleanup of expired entries across all caches"""
        manager = CacheManager()

        cache1 = manager.get_cache('cache1', ttl=1)
        cache2 = manager.get_cache('cache2', ttl=1)

        cache1.set('key1', 'value1', ttl=1)
        cache2.set('key2', 'value2', ttl=1)
        cache2.set('key3', 'value3', ttl=60)

        time.sleep(1.2)

        results = manager.cleanup_all_expired()

        assert 'cache1' in results
        assert 'cache2' in results
        assert results['cache1'] == 1
        assert results['cache2'] == 1

    def test_stats_all_caches(self):
        """Test getting stats for all caches"""
        manager = CacheManager()

        cache1 = manager.get_cache('cache1')
        cache2 = manager.get_cache('cache2')

        cache1.set('key', 'value')
        cache2.set('key', 'value')

        stats = manager.stats()

        assert 'cache1' in stats
        assert 'cache2' in stats
        assert stats['cache1']['size'] == 1
        assert stats['cache2']['size'] == 1


class TestTechnicalIndicatorCache:
    """Test suite for TechnicalIndicatorCache class"""

    def create_sample_price_data(self, num_bars=100):
        """Create sample price data for testing"""
        dates = pd.date_range(end=datetime.now(), periods=num_bars, freq='D')
        data = pd.DataFrame({
            'Close': np.random.uniform(100, 200, num_bars),
            'High': np.random.uniform(100, 200, num_bars),
            'Low': np.random.uniform(100, 200, num_bars),
            'Volume': np.random.uniform(1000000, 5000000, num_bars),
        }, index=dates)
        return data

    def simple_calculator(self, price_data):
        """Simple indicator calculator for testing"""
        return {
            'sma_20': float(price_data['Close'].tail(20).mean()),
            'current_price': float(price_data['Close'].iloc[-1]),
            'bar_count': len(price_data)
        }

    def test_cache_miss_full_calculation(self):
        """Test full calculation on cache miss"""
        indicator_cache = TechnicalIndicatorCache()

        price_data = self.create_sample_price_data(100)
        indicators = indicator_cache.get_indicators(
            symbol='TEST',
            price_data=price_data,
            calculator_func=self.simple_calculator
        )

        assert indicators is not None
        assert 'sma_20' in indicators
        assert 'bar_count' in indicators
        assert indicators['bar_count'] == 100

    def test_incremental_update(self):
        """Test incremental update with few new bars"""
        indicator_cache = TechnicalIndicatorCache(max_incremental_bars=5)

        # Initial calculation
        price_data = self.create_sample_price_data(100)
        indicators1 = indicator_cache.get_indicators(
            symbol='TEST',
            price_data=price_data,
            calculator_func=self.simple_calculator
        )

        # Add 3 new bars (should trigger incremental update)
        new_data = self.create_sample_price_data(103)
        # Ensure last 100 bars match
        new_data.iloc[:100] = price_data.values

        indicators2 = indicator_cache.get_indicators(
            symbol='TEST',
            price_data=new_data,
            calculator_func=self.simple_calculator
        )

        assert indicators2 is not None
        assert indicators2['bar_count'] == 103

    def test_force_recalculation(self):
        """Test forcing full recalculation"""
        indicator_cache = TechnicalIndicatorCache()

        price_data = self.create_sample_price_data(100)

        # Initial calculation
        indicators1 = indicator_cache.get_indicators(
            symbol='TEST',
            price_data=price_data,
            calculator_func=self.simple_calculator
        )

        # Force recalculation
        indicators2 = indicator_cache.get_indicators(
            symbol='TEST',
            price_data=price_data,
            calculator_func=self.simple_calculator,
            force_recalc=True
        )

        assert indicators2 is not None

    def test_invalidate_cache(self):
        """Test cache invalidation"""
        indicator_cache = TechnicalIndicatorCache()

        price_data = self.create_sample_price_data(100)
        indicators = indicator_cache.get_indicators(
            symbol='TEST',
            price_data=price_data,
            calculator_func=self.simple_calculator
        )

        assert indicators is not None

        # Invalidate
        result = indicator_cache.invalidate('TEST')
        assert result is True

        # Should be cache miss now (would need to verify through debug/logging)

    def test_cache_stats(self):
        """Test cache statistics"""
        indicator_cache = TechnicalIndicatorCache()

        price_data = self.create_sample_price_data(100)
        indicator_cache.get_indicators(
            symbol='TEST1',
            price_data=price_data,
            calculator_func=self.simple_calculator
        )

        stats = indicator_cache.stats()
        assert 'size' in stats
        assert stats['size'] >= 1


class TestGlobalCacheManager:
    """Test global cache manager singleton"""

    def test_singleton_instance(self):
        """Test that get_cache_manager returns singleton"""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2

    def test_shared_caches(self):
        """Test that caches are shared across get_cache_manager calls"""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        cache1 = manager1.get_cache('shared')
        cache1.set('key', 'value')

        cache2 = manager2.get_cache('shared')
        assert cache2.get('key') == 'value'
