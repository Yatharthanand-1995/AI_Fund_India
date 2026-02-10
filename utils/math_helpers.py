"""
Math utility functions for safe financial calculations.

Provides helper functions that handle edge cases like division by zero,
NaN values, and floating-point precision issues.
"""

import pandas as pd
from typing import Optional


def safe_divide(
    numerator: float,
    denominator: float,
    default: Optional[float] = None
) -> Optional[float]:
    """
    Safely divide two numbers with validation.

    Args:
        numerator: The numerator value
        denominator: The denominator value
        default: Value to return if division cannot be performed

    Returns:
        Result of division or default value if invalid

    Examples:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0, default=0.0)
        0.0
        >>> safe_divide(10, 0)
        None
    """
    # Check for NaN values
    if pd.isna(numerator) or pd.isna(denominator):
        return default

    # Check for zero or near-zero denominator
    if denominator == 0 or abs(denominator) < 1e-10:
        return default

    try:
        result = float(numerator / denominator)

        # Check for infinity or NaN result
        import math
        if pd.isna(result) or not math.isfinite(result):
            return default

        return result
    except (ValueError, OverflowError, ZeroDivisionError):
        return default


def safe_percentage_change(
    current: float,
    previous: float,
    default: Optional[float] = 0.0
) -> Optional[float]:
    """
    Safely calculate percentage change between two values.

    Args:
        current: Current value
        previous: Previous value
        default: Value to return if calculation cannot be performed

    Returns:
        Percentage change or default value

    Examples:
        >>> safe_percentage_change(110, 100)
        10.0
        >>> safe_percentage_change(100, 0)
        0.0
    """
    if pd.isna(current) or pd.isna(previous):
        return default

    if previous == 0 or abs(previous) < 1e-10:
        return default

    try:
        change = ((current - previous) / previous) * 100

        if pd.isna(change) or not pd.isfinite(change):
            return default

        return float(change)
    except (ValueError, OverflowError, ZeroDivisionError):
        return default
