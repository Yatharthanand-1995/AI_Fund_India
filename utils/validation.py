"""
Validation utility functions for data integrity checks.

Provides helper functions for validating inputs, data frames, and safe data access.
"""

import math
from typing import Any, Optional, List, Dict
import pandas as pd


def is_empty_or_none(value: Any) -> bool:
    """
    Check if value is None or empty.

    Args:
        value: Value to check

    Returns:
        True if value is None or empty, False otherwise

    Examples:
        >>> is_empty_or_none(None)
        True
        >>> is_empty_or_none("")
        True
        >>> is_empty_or_none([])
        True
        >>> is_empty_or_none("hello")
        False
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
        return True
    if isinstance(value, pd.DataFrame) and value.empty:
        return True
    return False


def validate_numeric(
    value: Any,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    allow_none: bool = False
) -> bool:
    """
    Validate that value is numeric and within range.

    Args:
        value: Value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        allow_none: Whether None is a valid value

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_numeric(5, min_value=0, max_value=10)
        True
        >>> validate_numeric(-1, min_value=0)
        False
        >>> validate_numeric(None, allow_none=True)
        True
    """
    if value is None:
        return allow_none

    try:
        num = float(value)

        # Check for NaN
        if pd.isna(num):
            return allow_none

        # Check for infinity
        if not math.isfinite(num):
            return False

        # Check range
        if min_value is not None and num < min_value:
            return False
        if max_value is not None and num > max_value:
            return False

        return True

    except (ValueError, TypeError):
        return False


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: List[str],
    min_rows: int = 1
) -> tuple[bool, Optional[str]]:
    """
    Validate DataFrame structure and content.

    Args:
        df: DataFrame to validate
        required_columns: List of column names that must exist
        min_rows: Minimum number of rows required

    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if validation passes

    Examples:
        >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        >>> validate_dataframe(df, ['A', 'B'], min_rows=2)
        (True, None)
        >>> validate_dataframe(df, ['C'])
        (False, "Missing columns: ['C']")
    """
    if df is None:
        return False, "DataFrame is None"

    if df.empty:
        return False, "DataFrame is empty"

    if len(df) < min_rows:
        return False, f"Insufficient rows: {len(df)} < {min_rows} required"

    # Check for required columns
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return False, f"Missing columns: {missing_cols}"

    return True, None


def safe_get(data: Dict[str, Any], *keys, default: Any = None) -> Any:
    """
    Safely get value from nested dictionary.

    Args:
        data: Dictionary to access
        *keys: Sequence of keys for nested access
        default: Default value if key path doesn't exist

    Returns:
        Value at the key path or default if not found

    Examples:
        >>> data = {'a': {'b': {'c': 42}}}
        >>> safe_get(data, 'a', 'b', 'c')
        42
        >>> safe_get(data, 'a', 'x', 'y', default=0)
        0
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result


def validate_symbol(symbol: str) -> tuple[bool, Optional[str]]:
    """
    Validate stock symbol format.

    Args:
        symbol: Stock symbol to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_symbol("TCS")
        (True, None)
        >>> validate_symbol("")
        (False, "Symbol cannot be empty")
    """
    if not symbol or not isinstance(symbol, str):
        return False, "Symbol cannot be empty"

    symbol = symbol.strip()

    if len(symbol) < 1:
        return False, "Symbol cannot be empty"

    if len(symbol) > 20:
        return False, "Symbol is too long (max 20 characters)"

    # Check for valid characters (alphanumeric, dot, hyphen)
    if not all(c.isalnum() or c in '.-_' for c in symbol):
        return False, "Symbol contains invalid characters"

    return True, None


def validate_price_data(
    df: pd.DataFrame,
    min_rows: int = 1
) -> tuple[bool, Optional[str]]:
    """
    Validate price data DataFrame has required structure.

    Args:
        df: Price data DataFrame
        min_rows: Minimum rows required

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> df = pd.DataFrame({
        ...     'Open': [100],
        ...     'High': [110],
        ...     'Low': [95],
        ...     'Close': [105],
        ...     'Volume': [1000000]
        ... })
        >>> validate_price_data(df)
        (True, None)
    """
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    return validate_dataframe(df, required_columns, min_rows)


def validate_price_dataframe_schema(df: pd.DataFrame, symbol: str = "UNKNOWN") -> None:
    """
    Validate that DataFrame has required OHLCV columns and proper data types.

    Args:
        df: DataFrame to validate
        symbol: Stock symbol for error messages

    Raises:
        DataValidationException: If schema is invalid
    """
    from core.exceptions import DataValidationException

    if df is None or df.empty:
        raise DataValidationException(f"{symbol}: DataFrame is None or empty")

    # Check required columns
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_columns if col not in df.columns]

    if missing_cols:
        raise DataValidationException(
            f"{symbol}: Missing required columns: {missing_cols}. "
            f"Available columns: {list(df.columns)}"
        )

    # Validate data types are numeric
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise DataValidationException(
                f"{symbol}: Column '{col}' must be numeric, got {df[col].dtype}"
            )

    # Check for all-NaN columns
    for col in required_columns:
        if df[col].isna().all():
            raise DataValidationException(
                f"{symbol}: Column '{col}' contains all NaN values"
            )


def get_nifty_data(data_provider, min_rows: int = 20) -> pd.DataFrame:
    """
    Get NIFTY50 data with fallback across multiple symbol formats.

    Args:
        data_provider: Data provider instance
        min_rows: Minimum rows required for valid data

    Returns:
        DataFrame with NIFTY historical data

    Raises:
        DataValidationException: If NIFTY data unavailable from any source
    """
    import logging
    logger = logging.getLogger(__name__)

    # Try multiple symbol formats (different providers use different formats)
    nifty_symbols = [
        '^NSEI',           # NSE NIFTY 50 (primary)
        '^BSESN',          # BSE SENSEX (fallback if NIFTY unavailable)
        'NIFTYBEES.NS',    # NIFTY ETF (alternative)
        '^CNX500',         # CNX 500 Index (broader market)
    ]

    errors = []

    for symbol in nifty_symbols:
        try:
            logger.info(f"Attempting to fetch index data with symbol: {symbol}")
            result = data_provider.get_comprehensive_data(symbol)
            nifty_data = result.get('historical_data', pd.DataFrame())

            if not nifty_data.empty and len(nifty_data) >= min_rows:
                logger.info(f"✓ Successfully fetched index data using {symbol} ({len(nifty_data)} rows)")
                return nifty_data
            else:
                msg = f"Insufficient data for {symbol}: {len(nifty_data)} rows (need {min_rows})"
                logger.warning(msg)
                errors.append(msg)
        except Exception as e:
            msg = f"Failed to fetch with {symbol}: {str(e)}"
            logger.warning(msg)
            errors.append(msg)
            continue

    # All symbols failed
    from core.exceptions import DataValidationException
    error_summary = "\n".join([f"  - {e}" for e in errors])
    logger.error(f"Unable to fetch NIFTY/index data from any source:\n{error_summary}")
    raise DataValidationException(
        "Unable to fetch NIFTY50 data from any source. Tried: " + ", ".join(nifty_symbols)
    )


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp value to be within range [min_value, max_value].

    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value

    Returns:
        Clamped value

    Examples:
        >>> clamp(5, 0, 10)
        5
        >>> clamp(-5, 0, 10)
        0
        >>> clamp(15, 0, 10)
        10
    """
    return max(min_value, min(max_value, value))
