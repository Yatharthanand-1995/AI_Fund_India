"""
Hybrid Data Provider - Orchestrates NSEpy + Yahoo Finance with automatic failover
Primary provider with intelligent fallback and circuit breaker protection
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime
import logging

from data.base_provider import BaseDataProvider
from data.nse_provider import NSEProvider
from data.yahoo_provider import YahooFinanceProvider
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class HybridDataProvider(BaseDataProvider):
    """
    Hybrid data provider with automatic failover

    Strategy:
    1. Try NSEpy first (free, direct from NSE)
    2. Fall back to Yahoo Finance if NSEpy fails
    3. Use circuit breaker to avoid repeated failures
    4. Merge data from both sources for best coverage

    Features:
    - Automatic failover
    - Circuit breaker protection
    - Data merging (financials from yfinance, technical from both)
    - 20-minute caching
    - Graceful degradation
    """

    def __init__(
        self,
        cache_duration: int = 1200,
        enable_yfinance_fallback: bool = True,
        prefer_provider: str = "nse"  # "nse" or "yahoo"
    ):
        """
        Initialize hybrid provider

        Args:
            cache_duration: Cache TTL in seconds (default: 1200 = 20 min)
            enable_yfinance_fallback: Enable Yahoo Finance as fallback (default: True)
            prefer_provider: Preferred provider - "nse" or "yahoo" (default: "nse")
        """
        super().__init__(cache_duration)

        self.enable_yfinance_fallback = enable_yfinance_fallback
        self.prefer_provider = prefer_provider

        # Initialize providers
        try:
            self.nse_provider = NSEProvider(cache_duration=cache_duration)
            self.nse_available = True
            logger.info("NSE provider initialized successfully")
        except Exception as e:
            self.nse_available = False
            logger.warning(f"NSE provider not available: {e}")

        try:
            self.yahoo_provider = YahooFinanceProvider(cache_duration=cache_duration)
            self.yahoo_available = True
            logger.info("Yahoo Finance provider initialized successfully")
        except Exception as e:
            self.yahoo_available = False
            logger.warning(f"Yahoo Finance provider not available: {e}")

        # Circuit breakers for each provider
        self.nse_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            name="NSEpy"
        )
        self.yahoo_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            name="YahooFinance"
        )

        # Track usage stats
        self.stats = {
            'nse_success': 0,
            'nse_failure': 0,
            'yahoo_success': 0,
            'yahoo_failure': 0,
            'fallback_used': 0,
            'total_requests': 0
        }

    def get_stock_data(self, symbol: str) -> Dict:
        """Fetch basic stock data with fallback"""
        return self._fetch_with_fallback(
            symbol,
            lambda provider: provider.get_stock_data(symbol)
        )

    def get_historical_data(
        self,
        symbol: str,
        period: str = "2y",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch historical data with fallback"""
        return self._fetch_with_fallback(
            symbol,
            lambda provider: provider.get_historical_data(symbol, period, start_date, end_date)
        )

    def get_technical_indicators(self, historical_data: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        if self.nse_available:
            return self.nse_provider.get_technical_indicators(historical_data)
        elif self.yahoo_available:
            return self.yahoo_provider.get_technical_indicators(historical_data)
        return {}

    def get_comprehensive_data(self, symbol: str) -> Dict:
        """
        Get comprehensive data with intelligent fallback and data merging

        Strategy:
        1. Check cache first
        2. Try preferred provider (NSE by default)
        3. Fall back to secondary provider if primary fails
        4. Merge data from both sources if available
        """
        # Check cache first
        cached = self._get_cached_data(symbol)
        if cached:
            return cached

        self.stats['total_requests'] += 1

        logger.info(f"Fetching comprehensive data for {symbol} (hybrid mode)")

        # Determine provider order
        if self.prefer_provider == "yahoo":
            primary_provider = "yahoo"
            secondary_provider = "nse"
        else:
            primary_provider = "nse"
            secondary_provider = "yahoo"

        # Try primary provider
        data = self._try_provider(symbol, primary_provider)

        # Fall back to secondary if needed
        if self._is_empty_data(data) and self.enable_yfinance_fallback:
            logger.info(f"Primary provider ({primary_provider}) failed, trying fallback ({secondary_provider})")
            self.stats['fallback_used'] += 1
            data = self._try_provider(symbol, secondary_provider)

        # If we have partial data, try to enrich from other provider
        if not self._is_empty_data(data):
            data = self._enrich_data(symbol, data)

        # Cache result
        if not self._is_empty_data(data):
            self._cache_data(symbol, data)

        return data

    def _try_provider(self, symbol: str, provider_name: str) -> Dict:
        """Try fetching data from a specific provider with circuit breaker"""
        if provider_name == "nse" and self.nse_available:
            try:
                data = self.nse_circuit_breaker.call(
                    self.nse_provider.get_comprehensive_data,
                    symbol
                )
                self.stats['nse_success'] += 1
                logger.info(f"Successfully fetched data from NSE for {symbol}")
                return data
            except CircuitBreakerError as e:
                logger.warning(f"NSE circuit breaker is open: {e}")
                self.stats['nse_failure'] += 1
                return self._create_empty_data(symbol, str(e))
            except Exception as e:
                logger.error(f"NSE provider failed for {symbol}: {e}")
                self.stats['nse_failure'] += 1
                return self._create_empty_data(symbol, str(e))

        elif provider_name == "yahoo" and self.yahoo_available:
            try:
                data = self.yahoo_circuit_breaker.call(
                    self.yahoo_provider.get_comprehensive_data,
                    symbol
                )
                self.stats['yahoo_success'] += 1
                logger.info(f"Successfully fetched data from Yahoo Finance for {symbol}")
                return data
            except CircuitBreakerError as e:
                logger.warning(f"Yahoo Finance circuit breaker is open: {e}")
                self.stats['yahoo_failure'] += 1
                return self._create_empty_data(symbol, str(e))
            except Exception as e:
                logger.error(f"Yahoo Finance provider failed for {symbol}: {e}")
                self.stats['yahoo_failure'] += 1
                return self._create_empty_data(symbol, str(e))

        return self._create_empty_data(symbol, f"Provider '{provider_name}' not available")

    def _fetch_with_fallback(self, symbol: str, fetch_func):
        """Generic fetch with fallback logic"""
        # Try NSE first
        if self.nse_available:
            try:
                result = self.nse_circuit_breaker.call(fetch_func, self.nse_provider)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"NSE fetch failed: {e}")

        # Fall back to Yahoo
        if self.yahoo_available and self.enable_yfinance_fallback:
            try:
                result = self.yahoo_circuit_breaker.call(fetch_func, self.yahoo_provider)
                return result
            except Exception as e:
                logger.warning(f"Yahoo Finance fetch failed: {e}")

        return {} if isinstance(fetch_func(self.nse_provider), dict) else pd.DataFrame()

    def _is_empty_data(self, data: Dict) -> bool:
        """Check if data is empty/invalid"""
        if not data:
            return True
        if 'error' in data:
            return True
        if data.get('historical_data') is None or (
            isinstance(data.get('historical_data'), pd.DataFrame) and
            data.get('historical_data').empty
        ):
            return True
        return False

    def _enrich_data(self, symbol: str, data: Dict) -> Dict:
        """
        Enrich data by filling gaps from other provider

        For example:
        - NSE provides good historical data but no financials
        - Yahoo provides financials and analyst ratings
        - Merge both for complete picture
        """
        # If data came from NSE and missing financials, try to get from Yahoo
        if data.get('provider') == 'NSEProvider' and self.yahoo_available:
            if not data['data_completeness'].get('has_financials'):
                try:
                    logger.info(f"Enriching NSE data with Yahoo Finance financials for {symbol}")
                    yahoo_data = self.yahoo_provider.get_comprehensive_data(symbol)

                    if not self._is_empty_data(yahoo_data):
                        data['financials'] = yahoo_data.get('financials', pd.DataFrame())
                        data['quarterly_financials'] = yahoo_data.get('quarterly_financials', pd.DataFrame())
                        data['info'].update(yahoo_data.get('info', {}))
                        data['data_completeness']['has_financials'] = not yahoo_data.get('financials', pd.DataFrame()).empty
                        data['data_completeness']['has_quarterly'] = not yahoo_data.get('quarterly_financials', pd.DataFrame()).empty
                        data['provider'] = 'HybridProvider (NSE + Yahoo)'
                        logger.info(f"Successfully enriched data from Yahoo Finance")

                except Exception as e:
                    logger.warning(f"Failed to enrich data from Yahoo Finance: {e}")

        return data

    def get_provider_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            **self.stats,
            'nse_circuit_breaker': self.nse_circuit_breaker.get_state(),
            'yahoo_circuit_breaker': self.yahoo_circuit_breaker.get_state(),
            'cache_stats': self.get_cache_stats()
        }

    def reset_circuit_breakers(self):
        """Manually reset all circuit breakers"""
        self.nse_circuit_breaker.reset()
        self.yahoo_circuit_breaker.reset()
        logger.info("All circuit breakers have been reset")

    def get_health_status(self) -> Dict:
        """Get health status of all providers"""
        return {
            'hybrid_provider': 'healthy',
            'nse_provider': {
                'available': self.nse_available,
                'circuit_breaker_state': self.nse_circuit_breaker.state.value,
                'success_rate': self._calculate_success_rate('nse')
            },
            'yahoo_provider': {
                'available': self.yahoo_available,
                'circuit_breaker_state': self.yahoo_circuit_breaker.state.value,
                'success_rate': self._calculate_success_rate('yahoo')
            },
            'stats': self.stats
        }

    def _calculate_success_rate(self, provider: str) -> float:
        """Calculate success rate for a provider"""
        success = self.stats.get(f'{provider}_success', 0)
        failure = self.stats.get(f'{provider}_failure', 0)
        total = success + failure
        return (success / total * 100) if total > 0 else 0.0


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize hybrid provider
    provider = HybridDataProvider(
        enable_yfinance_fallback=True,
        prefer_provider="nse"
    )

    # Test with multiple stocks
    test_symbols = ["TCS", "INFY", "RELIANCE"]

    for symbol in test_symbols:
        print(f"\n{'='*60}")
        print(f"Analyzing: {symbol}")
        print('='*60)

        data = provider.get_comprehensive_data(symbol)

        print(f"Symbol: {data['symbol']}")
        print(f"Provider: {data.get('provider', 'Unknown')}")
        print(f"Current Price: ₹{data['current_price']:.2f}" if data.get('current_price') else "N/A")
        print(f"Change: {data['price_change_percent']:.2f}%" if data.get('price_change_percent') else "N/A")
        print(f"Market Cap: ₹{data['market_cap']/1e7:.2f} Cr" if data.get('market_cap') else "N/A")
        print(f"Sector: {data.get('sector', 'N/A')}")
        print(f"\nData Completeness:")
        for key, value in data['data_completeness'].items():
            print(f"  {key}: {value}")
        print(f"\nTechnical Indicators: {len(data.get('technical_data', {}))}")

    # Print provider stats
    print(f"\n{'='*60}")
    print("Provider Statistics")
    print('='*60)
    stats = provider.get_provider_stats()
    print(f"Total Requests: {stats['total_requests']}")
    print(f"NSE Success: {stats['nse_success']}")
    print(f"NSE Failures: {stats['nse_failure']}")
    print(f"Yahoo Success: {stats['yahoo_success']}")
    print(f"Yahoo Failures: {stats['yahoo_failure']}")
    print(f"Fallback Used: {stats['fallback_used']}")

    # Health status
    print(f"\n{'='*60}")
    print("Health Status")
    print('='*60)
    health = provider.get_health_status()
    print(f"NSE Available: {health['nse_provider']['available']}")
    print(f"NSE Circuit Breaker: {health['nse_provider']['circuit_breaker_state']}")
    print(f"NSE Success Rate: {health['nse_provider']['success_rate']:.1f}%")
    print(f"Yahoo Available: {health['yahoo_provider']['available']}")
    print(f"Yahoo Circuit Breaker: {health['yahoo_provider']['circuit_breaker_state']}")
    print(f"Yahoo Success Rate: {health['yahoo_provider']['success_rate']:.1f}%")
