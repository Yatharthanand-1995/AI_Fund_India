"""
Base Data Provider - Abstract class for all data providers
Defines the interface that all data providers must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseDataProvider(ABC):
    """
    Abstract base class for stock data providers

    All providers must implement:
    - get_stock_data(): Fetch basic stock info
    - get_historical_data(): Fetch OHLCV data
    - get_technical_indicators(): Calculate indicators
    - get_comprehensive_data(): All-in-one method
    """

    def __init__(self, cache_duration: int = 1200):
        """
        Initialize base provider

        Args:
            cache_duration: Cache TTL in seconds (default: 1200 = 20 minutes)
        """
        self.cache_duration = cache_duration
        self.cache: Dict = {}
        self.cache_expiry: Dict = {}
        self.provider_name = self.__class__.__name__

    @abstractmethod
    def get_stock_data(self, symbol: str) -> Dict:
        """
        Fetch basic stock information

        Args:
            symbol: Stock symbol (e.g., "TCS" for NSE)

        Returns:
            Dict with basic stock info:
            {
                'symbol': str,
                'current_price': float,
                'price_change_percent': float,
                'market_cap': int,
                'sector': str,
                'company_name': str,
                ...
            }
        """
        pass

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        period: str = "2y",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data

        Args:
            symbol: Stock symbol
            period: Time period (e.g., "1mo", "3mo", "1y", "2y", "5y")
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        pass

    @abstractmethod
    def get_technical_indicators(self, historical_data: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators using TA-Lib

        Args:
            historical_data: DataFrame with OHLCV data

        Returns:
            Dict with technical indicators:
            {
                'rsi': float,
                'macd': float,
                'sma_20': float,
                'obv': np.array,
                ...
            }
        """
        pass

    @abstractmethod
    def get_comprehensive_data(self, symbol: str) -> Dict:
        """
        Get all data in one call (with caching)

        This is the main method used by agents.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with all data:
            {
                'symbol': str,
                'current_price': float,
                'historical_data': pd.DataFrame,
                'technical_data': dict,
                'info': dict,
                'financials': pd.DataFrame (if available),
                'data_completeness': {
                    'has_historical': bool,
                    'has_financials': bool,
                    'has_info': bool
                },
                'timestamp': str,
                'provider': str
            }
        """
        pass

    def _is_cached_data_fresh(self, symbol: str) -> bool:
        """
        Check if cached data is still fresh

        Args:
            symbol: Stock symbol

        Returns:
            True if cache is fresh, False otherwise
        """
        if symbol not in self.cache or symbol not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[symbol]

    def _cache_data(self, symbol: str, data: Dict):
        """
        Cache data with expiry

        Args:
            symbol: Stock symbol
            data: Data to cache
        """
        from datetime import timedelta
        self.cache[symbol] = data
        self.cache_expiry[symbol] = datetime.now() + timedelta(seconds=self.cache_duration)
        logger.debug(f"Cached data for {symbol} (TTL: {self.cache_duration}s)")

    def _get_cached_data(self, symbol: str) -> Optional[Dict]:
        """
        Get cached data if fresh

        Args:
            symbol: Stock symbol

        Returns:
            Cached data or None
        """
        if self._is_cached_data_fresh(symbol):
            logger.debug(f"Cache HIT for {symbol} (provider: {self.provider_name})")
            return self.cache[symbol]
        logger.debug(f"Cache MISS for {symbol} (provider: {self.provider_name})")
        return None

    def clear_cache(self, symbol: Optional[str] = None):
        """
        Clear cache for a symbol or all symbols

        Args:
            symbol: Stock symbol to clear, or None to clear all
        """
        if symbol:
            self.cache.pop(symbol, None)
            self.cache_expiry.pop(symbol, None)
            logger.info(f"Cleared cache for {symbol}")
        else:
            self.cache.clear()
            self.cache_expiry.clear()
            logger.info("Cleared all cache")

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        return {
            "provider": self.provider_name,
            "cached_symbols": len(self.cache),
            "cache_size_mb": sum(
                len(str(v)) for v in self.cache.values()
            ) / (1024 * 1024),
            "symbols": list(self.cache.keys())
        }

    def _create_empty_data(self, symbol: str, error: str = "No data available") -> Dict:
        """
        Create empty data structure when data fetch fails

        Args:
            symbol: Stock symbol
            error: Error message

        Returns:
            Dict with empty data
        """
        return {
            'symbol': symbol,
            'current_price': None,
            'price_change_percent': None,
            'market_cap': None,
            'sector': None,
            'historical_data': pd.DataFrame(),
            'technical_data': {},
            'info': {},
            'financials': pd.DataFrame(),
            'data_completeness': {
                'has_historical': False,
                'has_financials': False,
                'has_info': False
            },
            'timestamp': datetime.now().isoformat(),
            'provider': self.provider_name,
            'error': error
        }
