"""
Shared Metric Extraction Utilities

Common utilities for safely extracting and converting metrics from data sources.
Used by all agent classes to ensure consistent behavior and eliminate code duplication.
"""

from typing import Optional, Dict, Any
import pandas as pd
import logging
from utils.math_helpers import safe_divide, safe_percentage_change

logger = logging.getLogger(__name__)


class MetricExtractor:
    """Shared metric extraction utilities for all agents"""

    @staticmethod
    def get_safe_value(
        data: Dict,
        key: str,
        multiply: float = 1.0,
        divide: float = 1.0,
        default: Optional[float] = None,
        max_value: float = 1e10
    ) -> Optional[float]:
        """
        Safely extract and convert metric with validation

        Args:
            data: Dictionary containing the metrics
            key: Key to extract from the dictionary
            multiply: Multiplier to apply to the value (default: 1.0)
            divide: Divisor to apply to the value (default: 1.0)
            default: Default value to return if extraction fails (default: None)
            max_value: Maximum allowed absolute value (default: 1e10)

        Returns:
            Extracted and converted value or default

        Examples:
            >>> data = {'revenue': '1000000', 'pe_ratio': 15.5}
            >>> MetricExtractor.get_safe_value(data, 'revenue', divide=1_000_000)
            1.0
            >>> MetricExtractor.get_safe_value(data, 'pe_ratio')
            15.5
            >>> MetricExtractor.get_safe_value(data, 'missing_key', default=0.0)
            0.0
        """
        try:
            value = data.get(key)

            # Handle missing or invalid values
            if value is None or value == 'N/A' or value == '':
                return default

            # Convert to float
            value = float(value)

            # Apply transformations
            if multiply != 1.0:
                value *= multiply

            if divide != 1.0:
                value /= divide

            # Validate against max_value to catch unrealistic data
            if abs(value) > max_value:
                logger.warning(f"Value for key '{key}' exceeds max_value: {value} > {max_value}")
                return None

            return value

        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to extract value for key '{key}': {e}")
            return default

    @staticmethod
    def safe_divide(
        numerator: float,
        denominator: float,
        default: Optional[float] = None
    ) -> Optional[float]:
        """
        Safe division with zero-check (delegates to utils.math_helpers.safe_divide)

        Args:
            numerator: The numerator value
            denominator: The denominator value
            default: Value to return if division is unsafe (default: None)

        Returns:
            Result of division or default value

        Examples:
            >>> MetricExtractor.safe_divide(100, 20)
            5.0
            >>> MetricExtractor.safe_divide(100, 0)
            None
            >>> MetricExtractor.safe_divide(100, 0, default=0.0)
            0.0
        """
        return safe_divide(numerator, denominator, default)

    @staticmethod
    def get_safe_percentage(
        data: Dict,
        key: str,
        default: Optional[float] = None,
        max_value: float = 100.0
    ) -> Optional[float]:
        """
        Safely extract a percentage value and ensure it's in valid range

        Args:
            data: Dictionary containing the metrics
            key: Key to extract from the dictionary
            default: Default value to return if extraction fails (default: None)
            max_value: Maximum allowed percentage value (default: 100.0)

        Returns:
            Extracted percentage value or default

        Examples:
            >>> data = {'growth_rate': '25.5%', 'margin': 15.2}
            >>> MetricExtractor.get_safe_percentage(data, 'growth_rate')
            25.5
            >>> MetricExtractor.get_safe_percentage(data, 'margin')
            15.2
        """
        try:
            value = data.get(key)

            if value is None or value == 'N/A' or value == '':
                return default

            # Handle percentage strings (e.g., "25.5%")
            if isinstance(value, str):
                value = value.rstrip('%')

            value = float(value)

            # Validate range
            if abs(value) > max_value:
                logger.warning(f"Percentage value for key '{key}' exceeds max_value: {value} > {max_value}")
                return None

            return value

        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to extract percentage for key '{key}': {e}")
            return default

    @staticmethod
    def calculate_percentage_change(
        current: float,
        previous: float,
        default: Optional[float] = None
    ) -> Optional[float]:
        """
        Calculate percentage change between two values (delegates to utils.math_helpers.safe_percentage_change)

        Args:
            current: Current value
            previous: Previous value
            default: Default value to return if calculation fails (default: None)

        Returns:
            Percentage change or default value

        Examples:
            >>> MetricExtractor.calculate_percentage_change(120, 100)
            20.0
            >>> MetricExtractor.calculate_percentage_change(80, 100)
            -20.0
            >>> MetricExtractor.calculate_percentage_change(100, 0)
            None
        """
        return safe_percentage_change(current, previous, default)
