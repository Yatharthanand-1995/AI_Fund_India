# Logging, Monitoring & Error Tracking

Comprehensive observability system for the AI Hedge Fund application.

## Features

- **Structured Logging** - JSON and colored console formats
- **Log Rotation** - Size-based and time-based rotation
- **Request Logging** - All API requests with timing
- **Performance Monitoring** - Response times, percentiles, slow request alerts
- **Error Tracking** - Automatic error categorization and counting
- **Metrics Collection** - Counters, timings, gauges
- **Real-time Dashboard** - Live system monitoring
- **Log Analysis** - Tools for analyzing historical logs

## Components

### 1. Logging Configuration (`logging_config.py`)

Centralized logging setup with multiple handlers:

```python
from utils.logging_config import setup_logging, get_logger

# Setup logging (call once at startup)
setup_logging(
    level='INFO',
    json_format=False,  # Use JSON for production
    console_output=True
)

# Get logger
logger = get_logger(__name__)

# Use logger
logger.info("Application started")
logger.error("Error occurred", exc_info=True)
```

**Features:**
- Colored console output (development)
- JSON structured logging (production)
- Multiple log files:
  - `logs/app.log` - All logs (rotating, 10 MB)
  - `logs/error.log` - Errors only (rotating, 10 MB)
  - `logs/daily.log` - Daily rotation (30 days)
- Automatic log rotation
- Configurable log levels
- Exception tracking with full traceback

**Log Formatters:**
- `ColoredFormatter` - Colored console output
- `JSONFormatter` - Structured JSON logging

**Performance Logging:**
```python
from utils.logging_config import log_performance

with log_performance(logger, 'analyze_stock', symbol='TCS'):
    result = analyze_stock('TCS')
# Logs: "Completed: analyze_stock (123.45ms)"
```

### 2. API Middleware (`api_middleware.py`)

FastAPI middleware for comprehensive request/response logging:

```python
from utils.api_middleware import (
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    ErrorTrackingMiddleware,
)

# Add to FastAPI app
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold_ms=2000)
app.add_middleware(ErrorTrackingMiddleware)
```

**RequestLoggingMiddleware:**
- Logs all requests with method, path, query params
- Generates unique request ID
- Logs response status and duration
- Adds custom headers: `X-Request-ID`, `X-Response-Time`
- Handles exceptions gracefully

**PerformanceMonitoringMiddleware:**
- Tracks response times
- Alerts on slow requests (configurable threshold)
- Logs performance metrics

**ErrorTrackingMiddleware:**
- Tracks 4xx and 5xx errors
- Counts errors by endpoint
- Categorizes exceptions
- Provides error statistics

### 3. Metrics Collection (`metrics.py`)

Comprehensive metrics tracking:

```python
from utils.metrics import metrics, Timer, track_api_request

# Increment counters
metrics.increment('api.requests')

# Record timings
metrics.record_timing('api.response_time', 123.45)

# Set gauges
metrics.set_gauge('cache.size', 1000)

# Record errors
metrics.record_error('validation_error')

# Get statistics
stats = metrics.get_stats()
summary = metrics.get_summary()
```

**Convenience Functions:**
```python
from utils.metrics import (
    track_api_request,
    track_api_error,
    track_agent_execution,
    track_data_fetch,
    track_cache_access,
    track_llm_generation,
)

# Track API request
track_api_request('/analyze')

# Track agent execution
track_agent_execution('fundamentals', duration_ms=123.45)

# Track cache access
track_cache_access(hit=True)
```

**Timer Context Manager:**
```python
with Timer(metrics, 'operation_name'):
    do_something()
# Automatically records timing
```

**Metrics Types:**
- **Counters** - Monotonically increasing (e.g., request count)
- **Timings** - Duration measurements with percentiles (p50, p95, p99)
- **Gauges** - Point-in-time values (e.g., cache size)
- **Errors** - Error categorization and counting

## API Endpoints

### GET /metrics

Get comprehensive metrics:
```json
{
  "uptime_seconds": 3600,
  "start_time": "2025-01-31T10:00:00",
  "counters": {
    "api.requests": 1234,
    "cache.hits": 890,
    "cache.misses": 344,
    "errors.total": 5
  },
  "timings": {
    "api.response_time": {
      "count": 1234,
      "avg_ms": 156.78,
      "min_ms": 12.34,
      "max_ms": 2345.67,
      "p50_ms": 123.45,
      "p95_ms": 456.78,
      "p99_ms": 890.12
    }
  },
  "gauges": {
    "cache.size": 1000
  },
  "errors": {
    "validation_error": 3,
    "data_fetch_error": 2
  }
}
```

### GET /metrics/summary

Get key performance indicators:
```json
{
  "uptime_seconds": 3600,
  "total_requests": 1234,
  "total_errors": 5,
  "error_rate": 0.41,
  "avg_response_time_ms": 156.78,
  "cache_hit_rate": 72.09
}
```

## Monitoring Tools

### 1. Real-time Dashboard

Live system monitoring with auto-refresh:

```bash
python scripts/monitor_system.py
```

**Displays:**
- System health status
- Key metrics (requests, errors, response times)
- Response time percentiles (p50, p95, p99)
- Request counters
- Error counts
- Agent performance
- Auto-refreshes every 5 seconds

### 2. Log Analyzer

Analyze historical logs:

```bash
# Analyze main log
python scripts/analyze_logs.py

# Analyze specific file
python scripts/analyze_logs.py --file logs/app.log

# Show errors only
python scripts/analyze_logs.py --errors-only

# JSON output
python scripts/analyze_logs.py --json
```

**Analyzes:**
- Log level distribution
- Most active loggers
- Top endpoints
- Most analyzed symbols
- Recent errors
- Slow requests

## Makefile Commands

```bash
# Monitoring
make monitor          # Real-time dashboard
make logs            # Tail application logs
make logs-error      # Tail error logs
make analyze-logs    # Analyze logs

# Metrics
make metrics         # View current metrics
make health          # Check system health
```

## Environment Variables

Configure logging via environment variables:

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Use JSON format (true/false)
LOG_JSON=false

# Log files
LOG_FILE=app.log
ERROR_LOG_FILE=error.log

# Slow request threshold (milliseconds)
SLOW_REQUEST_THRESHOLD=2000
```

## Log Files

All logs are stored in `logs/` directory:

```
logs/
├── app.log           # Main application log (rotating, 10 MB)
├── app.log.1         # Rotated backup
├── app.log.2
├── error.log         # Errors only (rotating, 10 MB)
├── error.log.1
└── daily.log         # Daily rotation (30 days)
```

**Rotation:**
- Size-based: When file exceeds 10 MB
- Time-based: Daily at midnight
- Keeps 5 backups for size-based, 30 days for time-based

## Log Formats

### Console Format (Development)

```
2025-01-31 10:30:00 - api.main - INFO - Request started: POST /analyze
```

### JSON Format (Production)

```json
{
  "timestamp": "2025-01-31T10:30:00.123456",
  "level": "INFO",
  "logger": "api.main",
  "message": "Request started: POST /analyze",
  "module": "main",
  "function": "analyze_stock",
  "line": 123,
  "request_id": "abc-123-def",
  "symbol": "TCS"
}
```

## Best Practices

### 1. Use Structured Logging

Add context to logs:

```python
logger.info(
    "Stock analyzed",
    extra={
        'symbol': 'TCS',
        'score': 85.5,
        'recommendation': 'BUY',
        'duration_ms': 123.45
    }
)
```

### 2. Log at Appropriate Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages (potential issues)
- `ERROR`: Error messages (failures)
- `CRITICAL`: Critical errors (system failures)

### 3. Use Performance Logging

Time critical operations:

```python
with log_performance(logger, 'data_fetch', symbol='TCS'):
    data = fetch_data('TCS')
```

### 4. Track Metrics

Instrument your code:

```python
# Increment counter
metrics.increment('cache.misses')

# Record timing
with Timer(metrics, 'agent.fundamentals.duration'):
    score = fundamentals_agent.analyze(symbol)
```

### 5. Don't Log Sensitive Data

Never log:
- API keys
- Passwords
- Personal information
- Financial data

## Troubleshooting

### High Error Rate

```bash
# Check recent errors
python scripts/analyze_logs.py --errors-only

# Monitor in real-time
python scripts/monitor_system.py
```

### Slow Requests

```bash
# Check slow request logs
grep "Slow request" logs/app.log

# View metrics
curl http://localhost:8010/metrics | jq .timings
```

### Log Files Too Large

Logs rotate automatically, but you can manually:

```bash
# Archive old logs
tar -czf logs-archive-$(date +%Y%m%d).tar.gz logs/*.log.*

# Clear old logs
rm logs/*.log.*
```

## Production Recommendations

1. **Use JSON logging**:
   ```bash
   LOG_JSON=true
   ```

2. **Set appropriate log level**:
   ```bash
   LOG_LEVEL=WARNING
   ```

3. **Monitor metrics**:
   - Set up alerts on error rate
   - Track p95/p99 response times
   - Monitor cache hit rates

4. **External logging service**:
   - Send logs to ELK, Splunk, or CloudWatch
   - Set up dashboards and alerts
   - Enable long-term log retention

5. **Regular analysis**:
   - Run log analyzer daily
   - Review error patterns
   - Identify optimization opportunities

## Integration with Monitoring Services

### Datadog

```python
# Install datadog
pip install datadog

# Configure
import datadog
datadog.initialize(api_key='YOUR_KEY')

# Send metrics
datadog.statsd.increment('api.requests')
```

### Prometheus

```python
# Install prometheus client
pip install prometheus-client

# Expose metrics endpoint
from prometheus_client import Counter, Histogram, generate_latest

requests_counter = Counter('api_requests_total', 'Total requests')
response_time = Histogram('api_response_seconds', 'Response time')
```

## Examples

See the example usage sections in each module:
- `utils/logging_config.py` - Logging examples
- `utils/api_middleware.py` - Middleware examples
- `utils/metrics.py` - Metrics examples

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run `python scripts/analyze_logs.py`
3. Use `python scripts/monitor_system.py` for real-time monitoring
4. Review metrics at `/metrics` endpoint
