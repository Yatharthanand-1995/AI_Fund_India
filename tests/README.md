# Test Suite

Comprehensive test suite for the AI Hedge Fund system with 100+ tests.

## Overview

- **Unit Tests** - Test individual components in isolation
- **Integration Tests** - Test component interactions
- **API Tests** - Test FastAPI endpoints
- **Agent Tests** - Test all 5 AI agents
- **Utility Tests** - Test metrics, logging, stock universe

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_agents.py           # Tests for all 5 AI agents (50+ tests)
├── test_api.py              # Tests for API endpoints (40+ tests)
├── test_utils.py            # Tests for utilities (30+ tests)
└── README.md                # This file
```

## Running Tests

### All Tests

```bash
# Run all tests
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Using make
make test
make test-cov
```

### By Type

```bash
# Unit tests only
pytest tests/ -m unit
make test-unit

# Integration tests only
pytest tests/ -m integration
make test-integration

# API tests only
pytest tests/ -m api

# Agent tests only
pytest tests/ -m agents
```

### By Speed

```bash
# Fast tests only (skip slow tests)
pytest tests/ -m "not slow"
make test-fast

# Slow tests only
pytest tests/ -m slow
```

### Specific Test Files

```bash
# Test agents only
pytest tests/test_agents.py

# Test API only
pytest tests/test_api.py -v

# Test specific class
pytest tests/test_agents.py::TestFundamentalsAgent

# Test specific method
pytest tests/test_agents.py::TestFundamentalsAgent::test_analyze_with_valid_data
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.agents` - Agent tests
- `@pytest.mark.data` - Data provider tests
- `@pytest.mark.slow` - Slow-running tests (>1 second)

## Fixtures

### Sample Data Fixtures

- `sample_historical_data` - 252 days of OHLCV data
- `sample_nifty_data` - NIFTY 50 index data
- `sample_stock_info` - Complete stock info dict
- `sample_financials` - Financial statements
- `sample_comprehensive_data` - Full data package

### Mock Components

- `mock_data_provider` - Mock data provider
- `mock_stock_scorer` - Mock stock scorer
- `mock_narrative_engine` - Mock narrative engine

### API Testing

- `api_client` - FastAPI TestClient

### Utilities

- `valid_symbols` - List of valid test symbols
- `invalid_symbols` - List of invalid symbols
- `temp_log_dir` - Temporary log directory
- `sample_agent_result` - Standard agent result format

## Test Coverage

### Agents (test_agents.py)

**Fundamentals Agent:**
- ✓ Initialization
- ✓ Analyze with valid data
- ✓ Analyze without data
- ✓ Score breakdown components
- ✓ Excellent fundamentals scenario
- ✓ Poor fundamentals scenario

**Momentum Agent:**
- ✓ Initialization
- ✓ Analyze with price data
- ✓ Analyze without data
- ✓ RSI calculation
- ✓ Strong uptrend scenario

**Quality Agent:**
- ✓ Initialization
- ✓ Analyze with price data
- ✓ Low volatility stock
- ✓ High volatility stock

**Sentiment Agent:**
- ✓ Initialization
- ✓ Analyze with analyst data
- ✓ Strong buy recommendation
- ✓ Sell recommendation

**Institutional Flow Agent:**
- ✓ Initialization
- ✓ Analyze with price/volume data
- ✓ High volume accumulation pattern

**Cross-Agent Tests:**
- ✓ All agents return required fields
- ✓ All agents score in valid range (0-100)
- ✓ All agents handle missing data gracefully

### API (test_api.py)

**POST /analyze:**
- ✓ Analyze valid symbol
- ✓ Invalid request handling
- ✓ Analysis with narrative generation

**POST /analyze/batch:**
- ✓ Batch analyze multiple symbols
- ✓ Exceeds limit validation
- ✓ Empty list validation

**GET /portfolio/top-picks:**
- ✓ Default parameters
- ✓ Custom limit
- ✓ Invalid limit validation

**GET /market/regime:**
- ✓ Get market regime
- ✓ Verify trend values
- ✓ Verify volatility values
- ✓ Verify weights present

**GET /health:**
- ✓ Health check returns status
- ✓ All components present
- ✓ Version info present

**GET /stocks/universe:**
- ✓ Universe data structure
- ✓ NIFTY 50 included

**GET /metrics:**
- ✓ Full metrics structure
- ✓ Counters, timings, gauges present

**GET /metrics/summary:**
- ✓ KPIs present
- ✓ Error rate calculation
- ✓ Cache hit rate calculation

**General:**
- ✓ Root endpoint
- ✓ CORS headers
- ✓ Request validation
- ✓ Custom response headers

### Utilities (test_utils.py)

**Metrics Collector:**
- ✓ Initialization
- ✓ Increment/decrement counters
- ✓ Record timings
- ✓ Set gauges
- ✓ Record errors
- ✓ Get statistics
- ✓ Get summary
- ✓ Reset functionality
- ✓ Timer context manager
- ✓ Percentile calculations (p50, p95, p99)

**Stock Universe:**
- ✓ Singleton pattern
- ✓ Initialization
- ✓ Get symbols
- ✓ Sector filtering
- ✓ Market cap filtering
- ✓ Get stock info
- ✓ Search stocks
- ✓ Symbol validation
- ✓ Filter valid symbols
- ✓ Index summary
- ✓ Universe statistics
- ✓ DataFrame export
- ✓ JSON export
- ✓ Top stocks by weight

## Writing New Tests

### Test Template

```python
import pytest

@pytest.mark.unit
class TestMyComponent:
    """Tests for MyComponent"""

    def test_initialization(self):
        """Test component initialization"""
        component = MyComponent()
        assert component is not None

    def test_main_functionality(self, sample_data):
        """Test main functionality"""
        component = MyComponent()
        result = component.process(sample_data)

        assert result is not None
        assert 'key_field' in result
```

### Using Fixtures

```python
def test_with_fixtures(sample_historical_data, sample_stock_info):
    """Test using multiple fixtures"""
    # Fixtures are automatically provided
    assert len(sample_historical_data) == 252
    assert sample_stock_info['symbol'] == 'TCS'
```

### Mocking

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    """Test with mocking"""
    with patch('module.function') as mock_func:
        mock_func.return_value = {'result': 'success'}

        result = my_function()
        assert result['result'] == 'success'
```

### Parameterized Tests

```python
@pytest.mark.parametrize('input,expected', [
    (80, 'STRONG BUY'),
    (65, 'BUY'),
    (50, 'HOLD'),
    (35, 'SELL'),
])
def test_recommendation(input, expected):
    """Test recommendation generation"""
    assert get_recommendation(input) == expected
```

## Coverage Reports

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=. --cov-report=html

# Open in browser
open htmlcov/index.html
```

### Coverage Goals

- Overall: >80%
- Agents: >90%
- API: >85%
- Utilities: >80%

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Use Fixtures**: Reuse common test data and setups
3. **Mock External Dependencies**: Don't call real APIs in tests
4. **Test Edge Cases**: Test both success and failure scenarios
5. **Clear Test Names**: Use descriptive test method names
6. **Fast Tests**: Keep unit tests fast (<1s each)
7. **Mark Slow Tests**: Use `@pytest.mark.slow` for long tests
8. **Test Coverage**: Aim for >80% coverage
9. **Document Tests**: Add docstrings explaining what's being tested
10. **Refactor Tests**: Keep test code clean and maintainable

## Troubleshooting

### Tests Fail Randomly

- Check for timing issues (use `time.sleep` if needed)
- Check for shared state between tests
- Use `pytest -x` to stop at first failure

### Import Errors

- Ensure PYTHONPATH includes project root
- Check that `__init__.py` files exist
- Run from project root directory

### Fixture Not Found

- Check fixture is defined in `conftest.py`
- Check fixture scope (function/class/module/session)
- Check fixture is imported if in separate file

### Mock Not Working

- Verify correct import path in patch
- Check mock is applied before function call
- Use `assert_called_with()` to debug calls

## Performance

### Test Execution Times

- Unit tests: <1 second each
- Integration tests: 1-5 seconds
- API tests: 1-3 seconds
- Full suite: <30 seconds

### Optimization Tips

- Use `pytest-xdist` for parallel execution:
  ```bash
  pip install pytest-xdist
  pytest tests/ -n auto
  ```

- Skip slow tests during development:
  ```bash
  pytest tests/ -m "not slow"
  ```

- Run only failed tests:
  ```bash
  pytest tests/ --lf  # last failed
  pytest tests/ --ff  # failed first
  ```

## Makefile Commands

```bash
make test              # Run all tests
make test-fast         # Fast tests only
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-cov          # With coverage report
make test-api          # API tests only
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage.py](https://coverage.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
