"""
Tests for Utility Modules

Tests:
- Metrics collection
- Logging configuration
- Stock universe
- API middleware
"""

import pytest
import logging
import pandas as pd
from pathlib import Path
from utils.metrics import MetricsCollector, Timer
from data.stock_universe import StockUniverse, get_universe


# ============================================================================
# Metrics Tests
# ============================================================================

@pytest.mark.unit
class TestMetricsCollector:
    """Tests for MetricsCollector"""

    def test_initialization(self):
        """Test metrics collector initialization"""
        metrics = MetricsCollector()

        assert metrics.get_counter('test') == 0
        assert len(metrics.counters) == 0

    def test_increment_counter(self):
        """Test incrementing counters"""
        metrics = MetricsCollector()

        metrics.increment('test.counter')
        assert metrics.get_counter('test.counter') == 1

        metrics.increment('test.counter', 5)
        assert metrics.get_counter('test.counter') == 6

    def test_decrement_counter(self):
        """Test decrementing counters"""
        metrics = MetricsCollector()

        metrics.increment('test', 10)
        metrics.decrement('test', 3)
        assert metrics.get_counter('test') == 7

    def test_record_timing(self):
        """Test recording timings"""
        metrics = MetricsCollector()

        metrics.record_timing('test.timing', 100.0)
        metrics.record_timing('test.timing', 200.0)

        timing = metrics.get_timing_stats('test.timing')
        assert timing.count == 2
        assert timing.avg == 150.0
        assert timing.min == 100.0
        assert timing.max == 200.0

    def test_set_gauge(self):
        """Test setting gauges"""
        metrics = MetricsCollector()

        metrics.set_gauge('test.gauge', 42.5)
        assert metrics.get_gauge('test.gauge') == 42.5

    def test_record_error(self):
        """Test recording errors"""
        metrics = MetricsCollector()

        metrics.record_error('validation_error')
        metrics.record_error('validation_error')
        metrics.record_error('network_error')

        assert metrics.errors['validation_error'] == 2
        assert metrics.errors['network_error'] == 1
        assert metrics.get_counter('errors.total') == 3

    def test_get_stats(self):
        """Test getting statistics"""
        metrics = MetricsCollector()

        metrics.increment('requests', 100)
        metrics.record_timing('response_time', 123.45)
        metrics.set_gauge('cache_size', 1000)
        metrics.record_error('test_error')

        stats = metrics.get_stats()

        assert 'uptime_seconds' in stats
        assert 'counters' in stats
        assert 'timings' in stats
        assert 'gauges' in stats
        assert 'errors' in stats

        assert stats['counters']['requests'] == 100
        assert stats['gauges']['cache_size'] == 1000
        assert stats['errors']['test_error'] == 1

    def test_get_summary(self):
        """Test getting summary"""
        metrics = MetricsCollector()

        metrics.increment('api.requests', 100)
        metrics.increment('errors.total', 5)
        metrics.record_timing('api.response_time', 150.0)
        metrics.increment('cache.hits', 80)
        metrics.increment('cache.misses', 20)

        summary = metrics.get_summary()

        assert summary['total_requests'] == 100
        assert summary['total_errors'] == 5
        assert summary['error_rate'] == 5.0
        assert summary['avg_response_time_ms'] == 150.0
        assert summary['cache_hit_rate'] == 80.0

    def test_reset(self):
        """Test resetting metrics"""
        metrics = MetricsCollector()

        metrics.increment('test', 10)
        metrics.reset()

        assert metrics.get_counter('test') == 0
        assert len(metrics.counters) == 0

    def test_timer_context_manager(self):
        """Test Timer context manager"""
        metrics = MetricsCollector()

        with Timer(metrics, 'test.operation'):
            pass  # Do nothing

        timing = metrics.get_timing_stats('test.operation')
        assert timing.count == 1
        assert timing.avg >= 0

    def test_percentiles(self):
        """Test percentile calculations"""
        metrics = MetricsCollector()

        # Record 100 values from 1 to 100
        for i in range(1, 101):
            metrics.record_timing('test', float(i))

        timing = metrics.get_timing_stats('test')

        assert timing.count == 100
        assert 45 <= timing.p50 <= 55  # Median around 50
        assert 90 <= timing.p95 <= 100  # 95th percentile around 95
        assert 95 <= timing.p99 <= 100  # 99th percentile around 99


# ============================================================================
# Stock Universe Tests
# ============================================================================

@pytest.mark.unit
class TestStockUniverse:
    """Tests for StockUniverse"""

    def test_singleton(self):
        """Test singleton pattern"""
        universe1 = get_universe()
        universe2 = get_universe()

        assert universe1 is universe2

    def test_initialization(self):
        """Test universe initialization"""
        universe = StockUniverse()

        assert len(universe.indices) > 0
        assert 'NIFTY_50' in universe.indices

    def test_get_symbols(self):
        """Test getting symbols"""
        universe = StockUniverse()

        symbols = universe.get_symbols('NIFTY_50')

        assert isinstance(symbols, list)
        assert len(symbols) == 48
        assert 'TCS' in symbols

    def test_get_symbols_with_sector_filter(self):
        """Test getting symbols with sector filter"""
        universe = StockUniverse()

        it_stocks = universe.get_symbols('NIFTY_50', sector='Information Technology')

        assert isinstance(it_stocks, list)
        assert len(it_stocks) > 0
        assert 'TCS' in it_stocks

    def test_get_stock_info(self):
        """Test getting stock info"""
        universe = StockUniverse()

        info = universe.get_stock_info('TCS')

        assert info['symbol'] == 'TCS'
        assert info['name'] == 'Tata Consultancy Services'
        assert info['sector'] == 'Information Technology'
        assert 'NIFTY_50' in info['indices']

    def test_get_stock_info_invalid(self):
        """Test getting info for invalid symbol"""
        universe = StockUniverse()

        info = universe.get_stock_info('INVALID')

        assert info == {}

    def test_search_stocks(self):
        """Test searching stocks"""
        universe = StockUniverse()

        results = universe.search_stocks('tata', search_in=['name'])

        assert len(results) > 0
        assert any('Tata' in r['name'] for r in results)

    def test_is_valid_symbol(self):
        """Test symbol validation"""
        universe = StockUniverse()

        assert universe.is_valid_symbol('TCS') is True
        assert universe.is_valid_symbol('INVALID') is False

    def test_validate_symbols(self):
        """Test validating multiple symbols"""
        universe = StockUniverse()

        validation = universe.validate_symbols(['TCS', 'INVALID', 'INFY'])

        assert validation['TCS'] is True
        assert validation['INVALID'] is False
        assert validation['INFY'] is True

    def test_filter_valid_symbols(self):
        """Test filtering to valid symbols"""
        universe = StockUniverse()

        symbols = ['TCS', 'INVALID', 'INFY', 'FAKE']
        valid = universe.filter_valid_symbols(symbols)

        assert 'TCS' in valid
        assert 'INFY' in valid
        assert 'INVALID' not in valid
        assert 'FAKE' not in valid

    def test_get_index_summary(self):
        """Test getting index summary"""
        universe = StockUniverse()

        summary = universe.get_index_summary('NIFTY_50')

        assert summary['name'] == 'NIFTY_50'
        assert summary['total_stocks'] == 48
        assert 'sectors' in summary
        assert 'market_caps' in summary

    def test_get_universe_stats(self):
        """Test getting universe statistics"""
        universe = StockUniverse()

        stats = universe.get_universe_stats()

        assert stats['total_unique_symbols'] > 0
        assert stats['indices_count'] > 0
        assert 'NIFTY_50' in stats['indices']

    def test_to_dataframe(self):
        """Test converting to DataFrame"""
        universe = StockUniverse()

        df = universe.to_dataframe('NIFTY_50')

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 48
        assert 'symbol' in df.columns
        assert 'name' in df.columns
        assert 'sector' in df.columns

    def test_export_to_json(self):
        """Test exporting to JSON"""
        universe = StockUniverse()

        data = universe.export_to_json('NIFTY_50')

        assert data['index'] == 'NIFTY_50'
        assert data['total_stocks'] == 48
        assert len(data['stocks']) == 48

    def test_get_top_stocks_by_weight(self):
        """Test getting top stocks by weight"""
        universe = StockUniverse()

        top_stocks = universe.get_top_stocks_by_weight('NIFTY_50', limit=5)

        assert len(top_stocks) == 5
        # Should be sorted by weight descending
        assert top_stocks[0]['weight'] >= top_stocks[-1]['weight']


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestMetricsIntegration:
    """Integration tests for metrics in real scenarios"""

    def test_metrics_across_multiple_operations(self):
        """Test metrics collection across multiple operations"""
        metrics = MetricsCollector()

        # Simulate API requests
        for i in range(10):
            metrics.increment('api.requests')
            metrics.record_timing('api.response_time', 100.0 + i * 10)

        # Simulate cache operations
        metrics.increment('cache.hits', 7)
        metrics.increment('cache.misses', 3)

        # Simulate errors
        metrics.record_error('network_error')

        stats = metrics.get_stats()
        summary = metrics.get_summary()

        assert summary['total_requests'] == 10
        assert summary['cache_hit_rate'] == 70.0
        assert summary['total_errors'] == 1
        assert stats['timings']['api.response_time']['count'] == 10


@pytest.mark.integration
class TestStockUniverseIntegration:
    """Integration tests for stock universe"""

    def test_universe_consistency_across_indices(self):
        """Test that stocks appear in correct indices"""
        universe = StockUniverse()

        # TCS should be in both NIFTY_50 and NIFTY_IT
        tcs_indices = universe.get_indices_for_symbol('TCS')

        assert 'NIFTY_50' in tcs_indices
        assert 'NIFTY_IT' in tcs_indices

    def test_sector_filtering_consistency(self):
        """Test sector filtering gives consistent results"""
        universe = StockUniverse()

        it_stocks = universe.get_symbols('NIFTY_50', sector='Information Technology')

        # All stocks should have IT sector
        for symbol in it_stocks:
            info = universe.get_stock_info(symbol)
            assert info['sector'] == 'Information Technology'
