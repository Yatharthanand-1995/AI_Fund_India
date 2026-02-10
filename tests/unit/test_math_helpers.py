"""
Unit tests for math helper utilities
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from utils.math_helpers import safe_divide, safe_percentage_change


class TestSafeDivide:
    """Test safe_divide function"""

    def test_normal_division(self):
        """Test normal division works correctly"""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(100, 4) == 25.0
        assert safe_divide(-10, 2) == -5.0

    def test_division_by_zero(self):
        """Test division by zero returns default"""
        assert safe_divide(10, 0, default=None) is None
        assert safe_divide(10, 0, default=0.0) == 0.0
        assert safe_divide(100, 0, default=-1) == -1

    def test_division_by_near_zero(self):
        """Test division by very small number returns default"""
        assert safe_divide(10, 1e-11, default=None) is None
        assert safe_divide(10, -1e-11, default=0.0) == 0.0

    def test_nan_numerator(self):
        """Test NaN numerator returns default"""
        assert safe_divide(pd.NA, 5, default=None) is None
        assert safe_divide(float('nan'), 5, default=0.0) == 0.0

    def test_nan_denominator(self):
        """Test NaN denominator returns default"""
        assert safe_divide(10, pd.NA, default=None) is None
        assert safe_divide(10, float('nan'), default=0.0) == 0.0

    def test_infinity_result(self):
        """Test infinity result is handled"""
        # Very large numbers that might overflow
        result = safe_divide(1e308, 1e-308, default=None)
        # Should either return valid number or default
        assert result is None or pd.isfinite(result)

    def test_default_none(self):
        """Test default None behavior"""
        assert safe_divide(10, 0) is None


class TestSafePercentageChange:
    """Test safe_percentage_change function"""

    def test_positive_change(self):
        """Test positive percentage change"""
        result = safe_percentage_change(110, 100)
        assert result == 10.0

    def test_negative_change(self):
        """Test negative percentage change"""
        result = safe_percentage_change(90, 100)
        assert result == -10.0

    def test_zero_change(self):
        """Test zero percentage change"""
        result = safe_percentage_change(100, 100)
        assert result == 0.0

    def test_zero_previous(self):
        """Test zero previous value returns default"""
        assert safe_percentage_change(100, 0, default=0.0) == 0.0
        assert safe_percentage_change(100, 0, default=None) is None

    def test_near_zero_previous(self):
        """Test near-zero previous value returns default"""
        result = safe_percentage_change(100, 1e-11, default=0.0)
        assert result == 0.0

    def test_nan_current(self):
        """Test NaN current value returns default"""
        result = safe_percentage_change(pd.NA, 100, default=0.0)
        assert result == 0.0

    def test_nan_previous(self):
        """Test NaN previous value returns default"""
        result = safe_percentage_change(100, pd.NA, default=0.0)
        assert result == 0.0

    def test_large_change(self):
        """Test large percentage change"""
        result = safe_percentage_change(200, 100)
        assert result == 100.0

    def test_double_increase(self):
        """Test 100% increase"""
        result = safe_percentage_change(200, 100)
        assert result == 100.0

    def test_half_decrease(self):
        """Test 50% decrease"""
        result = safe_percentage_change(50, 100)
        assert result == -50.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
