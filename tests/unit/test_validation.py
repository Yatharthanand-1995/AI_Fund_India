"""
Unit tests for validation utilities
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from utils.validation import (
    is_empty_or_none,
    validate_numeric,
    validate_dataframe,
    safe_get,
    validate_symbol,
    validate_price_data,
    clamp
)


class TestIsEmptyOrNone:
    """Test is_empty_or_none function"""

    def test_none(self):
        assert is_empty_or_none(None) is True

    def test_empty_string(self):
        assert is_empty_or_none("") is True
        assert is_empty_or_none("   ") is True

    def test_empty_list(self):
        assert is_empty_or_none([]) is True

    def test_empty_dict(self):
        assert is_empty_or_none({}) is True

    def test_empty_dataframe(self):
        assert is_empty_or_none(pd.DataFrame()) is True

    def test_non_empty_values(self):
        assert is_empty_or_none("hello") is False
        assert is_empty_or_none([1, 2, 3]) is False
        assert is_empty_or_none({'a': 1}) is False
        assert is_empty_or_none(pd.DataFrame({'A': [1]})) is False


class TestValidateNumeric:
    """Test validate_numeric function"""

    def test_valid_integer(self):
        assert validate_numeric(5) is True
        assert validate_numeric(0) is True
        assert validate_numeric(-10) is True

    def test_valid_float(self):
        assert validate_numeric(5.5) is True
        assert validate_numeric(0.0) is True
        assert validate_numeric(-10.5) is True

    def test_string_number(self):
        assert validate_numeric("5") is True
        assert validate_numeric("5.5") is True

    def test_min_value(self):
        assert validate_numeric(5, min_value=0) is True
        assert validate_numeric(-1, min_value=0) is False

    def test_max_value(self):
        assert validate_numeric(5, max_value=10) is True
        assert validate_numeric(15, max_value=10) is False

    def test_range(self):
        assert validate_numeric(5, min_value=0, max_value=10) is True
        assert validate_numeric(-1, min_value=0, max_value=10) is False
        assert validate_numeric(15, min_value=0, max_value=10) is False

    def test_none_with_allow_none(self):
        assert validate_numeric(None, allow_none=True) is True
        assert validate_numeric(None, allow_none=False) is False

    def test_nan(self):
        assert validate_numeric(float('nan')) is False
        assert validate_numeric(float('nan'), allow_none=True) is True

    def test_infinity(self):
        assert validate_numeric(float('inf')) is False
        assert validate_numeric(float('-inf')) is False


class TestValidateDataFrame:
    """Test validate_dataframe function"""

    def test_valid_dataframe(self):
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        valid, error = validate_dataframe(df, ['A', 'B'], min_rows=2)
        assert valid is True
        assert error is None

    def test_none_dataframe(self):
        valid, error = validate_dataframe(None, ['A'], min_rows=1)
        assert valid is False
        assert 'None' in error

    def test_empty_dataframe(self):
        valid, error = validate_dataframe(pd.DataFrame(), ['A'], min_rows=1)
        assert valid is False
        assert 'empty' in error

    def test_insufficient_rows(self):
        df = pd.DataFrame({'A': [1]})
        valid, error = validate_dataframe(df, ['A'], min_rows=5)
        assert valid is False
        assert 'Insufficient rows' in error

    def test_missing_columns(self):
        df = pd.DataFrame({'A': [1, 2]})
        valid, error = validate_dataframe(df, ['A', 'B', 'C'], min_rows=1)
        assert valid is False
        assert 'Missing columns' in error
        assert 'B' in error
        assert 'C' in error


class TestSafeGet:
    """Test safe_get function"""

    def test_simple_access(self):
        data = {'a': 42}
        assert safe_get(data, 'a') == 42

    def test_nested_access(self):
        data = {'a': {'b': {'c': 42}}}
        assert safe_get(data, 'a', 'b', 'c') == 42

    def test_missing_key(self):
        data = {'a': 1}
        assert safe_get(data, 'b', default=0) == 0

    def test_missing_nested_key(self):
        data = {'a': {'b': 1}}
        assert safe_get(data, 'a', 'x', 'y', default=None) is None

    def test_non_dict_value(self):
        data = {'a': 42}
        assert safe_get(data, 'a', 'b', default=0) == 0


class TestValidateSymbol:
    """Test validate_symbol function"""

    def test_valid_symbol(self):
        valid, error = validate_symbol("TCS")
        assert valid is True
        assert error is None

    def test_empty_symbol(self):
        valid, error = validate_symbol("")
        assert valid is False
        assert 'empty' in error

    def test_none_symbol(self):
        valid, error = validate_symbol(None)
        assert valid is False

    def test_long_symbol(self):
        valid, error = validate_symbol("A" * 25)
        assert valid is False
        assert 'long' in error

    def test_valid_special_chars(self):
        assert validate_symbol("NIFTY-50")[0] is True
        assert validate_symbol("BANK.NS")[0] is True

    def test_invalid_special_chars(self):
        valid, error = validate_symbol("TCS@#$")
        assert valid is False
        assert 'invalid characters' in error


class TestValidatePriceData:
    """Test validate_price_data function"""

    def test_valid_price_data(self):
        df = pd.DataFrame({
            'Open': [100, 102],
            'High': [105, 108],
            'Low': [98, 101],
            'Close': [103, 106],
            'Volume': [1000000, 1100000]
        })
        valid, error = validate_price_data(df)
        assert valid is True
        assert error is None

    def test_missing_columns(self):
        df = pd.DataFrame({
            'Open': [100],
            'Close': [103]
        })
        valid, error = validate_price_data(df)
        assert valid is False
        assert 'Missing columns' in error


class TestClamp:
    """Test clamp function"""

    def test_value_in_range(self):
        assert clamp(5, 0, 10) == 5

    def test_value_below_min(self):
        assert clamp(-5, 0, 10) == 0

    def test_value_above_max(self):
        assert clamp(15, 0, 10) == 10

    def test_value_at_min(self):
        assert clamp(0, 0, 10) == 0

    def test_value_at_max(self):
        assert clamp(10, 0, 10) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
