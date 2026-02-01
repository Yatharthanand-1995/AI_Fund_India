"""
Metrics Collection and Monitoring

Tracks:
- Request counts and response times
- Agent execution times
- Data provider performance
- Cache hit rates
- Error rates
- System health

Usage:
    from utils.metrics import metrics

    metrics.increment('api.requests')
    metrics.record_timing('api.response_time', 123.45)
    stats = metrics.get_stats()
"""

import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class TimingStats:
    """Statistics for timing measurements"""
    count: int = 0
    total: float = 0.0
    min: float = float('inf')
    max: float = 0.0
    recent: deque = field(default_factory=lambda: deque(maxlen=100))

    def record(self, value: float):
        """Record a timing value"""
        self.count += 1
        self.total += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.recent.append(value)

    @property
    def avg(self) -> float:
        """Calculate average"""
        return self.total / self.count if self.count > 0 else 0.0

    @property
    def p50(self) -> float:
        """Calculate 50th percentile (median)"""
        if not self.recent:
            return 0.0
        sorted_recent = sorted(self.recent)
        return sorted_recent[len(sorted_recent) // 2]

    @property
    def p95(self) -> float:
        """Calculate 95th percentile"""
        if not self.recent:
            return 0.0
        sorted_recent = sorted(self.recent)
        idx = int(len(sorted_recent) * 0.95)
        return sorted_recent[min(idx, len(sorted_recent) - 1)]

    @property
    def p99(self) -> float:
        """Calculate 99th percentile"""
        if not self.recent:
            return 0.0
        sorted_recent = sorted(self.recent)
        idx = int(len(sorted_recent) * 0.99)
        return sorted_recent[min(idx, len(sorted_recent) - 1)]


class MetricsCollector:
    """
    Centralized metrics collection
    """

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.timings: Dict[str, TimingStats] = defaultdict(TimingStats)
        self.gauges: Dict[str, float] = {}
        self.errors: Dict[str, int] = defaultdict(int)
        self.lock = Lock()
        self.start_time = datetime.now()

    def increment(self, metric: str, value: int = 1):
        """
        Increment a counter

        Args:
            metric: Metric name (e.g., 'api.requests')
            value: Increment value (default: 1)
        """
        with self.lock:
            self.counters[metric] += value

    def decrement(self, metric: str, value: int = 1):
        """
        Decrement a counter

        Args:
            metric: Metric name
            value: Decrement value (default: 1)
        """
        with self.lock:
            self.counters[metric] -= value

    def record_timing(self, metric: str, value: float):
        """
        Record a timing value (in milliseconds)

        Args:
            metric: Metric name (e.g., 'api.response_time')
            value: Time in milliseconds
        """
        with self.lock:
            self.timings[metric].record(value)

    def set_gauge(self, metric: str, value: float):
        """
        Set a gauge value

        Args:
            metric: Metric name (e.g., 'cache.size')
            value: Gauge value
        """
        with self.lock:
            self.gauges[metric] = value

    def record_error(self, error_type: str):
        """
        Record an error

        Args:
            error_type: Type of error
        """
        with self.lock:
            self.errors[error_type] += 1
            self.counters['errors.total'] += 1

    def get_counter(self, metric: str) -> int:
        """Get counter value"""
        with self.lock:
            return self.counters.get(metric, 0)

    def get_timing_stats(self, metric: str) -> Optional[TimingStats]:
        """Get timing statistics"""
        with self.lock:
            return self.timings.get(metric)

    def get_gauge(self, metric: str) -> Optional[float]:
        """Get gauge value"""
        with self.lock:
            return self.gauges.get(metric)

    def get_stats(self) -> Dict:
        """
        Get all statistics

        Returns:
            Dictionary with all metrics
        """
        with self.lock:
            uptime = (datetime.now() - self.start_time).total_seconds()

            stats = {
                'uptime_seconds': uptime,
                'start_time': self.start_time.isoformat(),
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'errors': dict(self.errors),
                'timings': {}
            }

            # Format timing stats
            for metric, timing in self.timings.items():
                stats['timings'][metric] = {
                    'count': timing.count,
                    'avg_ms': round(timing.avg, 2),
                    'min_ms': round(timing.min, 2) if timing.count > 0 else None,
                    'max_ms': round(timing.max, 2),
                    'p50_ms': round(timing.p50, 2),
                    'p95_ms': round(timing.p95, 2),
                    'p99_ms': round(timing.p99, 2),
                }

            return stats

    def get_summary(self) -> Dict:
        """
        Get summary statistics

        Returns:
            Dictionary with key metrics
        """
        stats = self.get_stats()

        return {
            'uptime_seconds': stats['uptime_seconds'],
            'total_requests': self.get_counter('api.requests'),
            'total_errors': self.get_counter('errors.total'),
            'error_rate': self._calculate_error_rate(),
            'avg_response_time_ms': self._get_avg_response_time(),
            'cache_hit_rate': self._calculate_cache_hit_rate(),
        }

    def _calculate_error_rate(self) -> float:
        """Calculate error rate"""
        total = self.get_counter('api.requests')
        errors = self.get_counter('errors.total')
        return (errors / total * 100) if total > 0 else 0.0

    def _get_avg_response_time(self) -> float:
        """Get average response time"""
        timing = self.get_timing_stats('api.response_time')
        return round(timing.avg, 2) if timing else 0.0

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        hits = self.get_counter('cache.hits')
        misses = self.get_counter('cache.misses')
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.counters.clear()
            self.timings.clear()
            self.gauges.clear()
            self.errors.clear()
            self.start_time = datetime.now()

        logger.info("Metrics reset")


class Timer:
    """
    Context manager for timing operations

    Usage:
        with Timer(metrics, 'operation_name'):
            do_something()
    """

    def __init__(self, metrics: MetricsCollector, metric: str):
        self.metrics = metrics
        self.metric = metric
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.metrics.record_timing(self.metric, duration_ms)

        if exc_type:
            self.metrics.record_error(f"{self.metric}.error")

        return False


# Global metrics instance
metrics = MetricsCollector()


# Convenience functions

def track_api_request(endpoint: str):
    """Track an API request"""
    metrics.increment('api.requests')
    metrics.increment(f'api.requests.{endpoint}')


def track_api_error(endpoint: str, error_type: str):
    """Track an API error"""
    metrics.record_error(error_type)
    metrics.increment(f'api.errors.{endpoint}')


def track_agent_execution(agent_name: str, duration_ms: float):
    """Track agent execution time"""
    metrics.record_timing(f'agent.{agent_name}.duration', duration_ms)
    metrics.increment(f'agent.{agent_name}.executions')


def track_data_fetch(provider: str, duration_ms: float, success: bool):
    """Track data provider performance"""
    metrics.record_timing(f'data.{provider}.duration', duration_ms)

    if success:
        metrics.increment(f'data.{provider}.success')
    else:
        metrics.increment(f'data.{provider}.failure')
        metrics.record_error(f'data.{provider}.error')


def track_cache_access(hit: bool):
    """Track cache hit/miss"""
    if hit:
        metrics.increment('cache.hits')
    else:
        metrics.increment('cache.misses')


def track_llm_generation(provider: str, duration_ms: float, tokens: Optional[int] = None):
    """Track LLM narrative generation"""
    metrics.record_timing(f'llm.{provider}.duration', duration_ms)
    metrics.increment(f'llm.{provider}.calls')

    if tokens:
        metrics.increment(f'llm.{provider}.tokens', tokens)


# Example usage
if __name__ == "__main__":
    from utils.logging_config import setup_logging

    setup_logging()

    print("="*60)
    print("Metrics Collection Test")
    print("="*60)

    # Simulate some metrics
    for i in range(10):
        metrics.increment('api.requests')

        with Timer(metrics, 'api.response_time'):
            time.sleep(0.01)

        if i % 5 == 0:
            metrics.record_error('validation_error')

    track_cache_access(hit=True)
    track_cache_access(hit=True)
    track_cache_access(hit=False)

    track_agent_execution('fundamentals', 123.45)
    track_data_fetch('nse', 234.56, success=True)
    track_llm_generation('gemini', 567.89, tokens=150)

    # Get statistics
    print("\nFull Stats:")
    print("="*60)
    import json
    print(json.dumps(metrics.get_stats(), indent=2))

    print("\nSummary:")
    print("="*60)
    print(json.dumps(metrics.get_summary(), indent=2))

    print("\nMetrics test completed!")
