"""
NSE Data Provider using NSEpy
Primary data source for Indian stocks
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
import time

try:
    from nsepy import get_history
    NSEPY_AVAILABLE = True
except ImportError:
    NSEPY_AVAILABLE = False
    logging.warning("NSEpy not available. Install with: pip install nsepy")

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logging.warning("TA-Lib not available. Technical indicators will be limited.")

from data.base_provider import BaseDataProvider
from core.exceptions import DataFetchException, DataValidationException
from utils.math_helpers import safe_divide, safe_percentage_change
from core.cache_manager import TechnicalIndicatorCache, get_cache_manager

logger = logging.getLogger(__name__)


class NSEProvider(BaseDataProvider):
    """
    Data provider for NSE stocks using NSEpy

    Features:
    - Fetches data directly from NSE
    - No API key required
    - 20-minute caching
    - 40+ technical indicators (if TA-Lib available)
    - Rate limiting (500ms between requests)
    """

    def __init__(self, cache_duration: int = 1200, rate_limit_delay: float = 0.5):
        """
        Initialize NSE provider

        Args:
            cache_duration: Cache TTL in seconds (default: 1200 = 20 min)
            rate_limit_delay: Delay between requests in seconds (default: 0.5)
        """
        super().__init__(cache_duration)
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0

        # Initialize technical indicator cache for incremental updates
        self.indicator_cache = TechnicalIndicatorCache(
            cache_manager=get_cache_manager(),
            max_incremental_bars=5
        )

        if not NSEPY_AVAILABLE:
            raise ImportError("NSEpy is required. Install with: pip install nsepy")

    def _rate_limit(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def get_stock_data(self, symbol: str) -> Dict:
        """Fetch basic stock info from NSE"""
        # NSEpy doesn't provide real-time quote API
        # We'll get latest data from historical endpoint
        try:
            self._rate_limit()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)

            df = get_history(symbol=symbol, start=start_date, end=end_date, index=False)

            # Validate data availability
            if df is None or df.empty:
                logger.warning(f"No data found for {symbol}")
                raise DataValidationException(f"No NSE data available for {symbol}")

            # Bounds checking before index access
            if len(df) < 1:
                logger.warning(f"Insufficient data for {symbol}")
                raise DataValidationException(f"Insufficient NSE data for {symbol}")

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            # Validate required values
            try:
                current_price = float(latest['Close'])
                if pd.isna(current_price) or current_price <= 0:
                    raise DataValidationException(f"Invalid price for {symbol}")
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Price validation error for {symbol}: {e}", exc_info=True)
                raise DataValidationException(f"Invalid NSE data format for {symbol}") from e

            # Safe percentage calculation
            price_change_pct = safe_percentage_change(
                float(latest['Close']),
                float(prev['Close']),
                default=0.0
            )

            return {
                'symbol': symbol,
                'current_price': current_price,
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'volume': int(latest['Volume']),
                'price_change': float(latest['Close'] - prev['Close']),
                'price_change_percent': price_change_pct,
                'date': latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)
            }

        except (DataFetchException, DataValidationException):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to fetch stock data for {symbol}: {e}", exc_info=True)
            raise DataFetchException(f"NSE data fetch failed for {symbol}") from e

    def get_historical_data(
        self,
        symbol: str,
        period: str = "2y",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data from NSE"""
        try:
            self._rate_limit()

            # Calculate dates
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                # Parse period string
                period_map = {
                    '1mo': 30, '3mo': 90, '6mo': 180,
                    '1y': 365, '2y': 730, '5y': 1825
                }
                days = period_map.get(period, 730)
                start_date = end_date - timedelta(days=days)

            logger.info(f"Fetching historical data for {symbol} from {start_date.date()} to {end_date.date()}")

            # Detect if symbol is an index
            is_index = symbol.startswith('^') or 'NIFTY' in symbol.upper() or 'SENSEX' in symbol.upper() or 'CNX' in symbol.upper()

            # NSEpy doesn't use ^ prefix for symbols
            clean_symbol = symbol.replace('^', '')

            logger.info(f"Fetching {'index' if is_index else 'stock'} data for {clean_symbol}")

            # Fetch from NSEpy
            df = get_history(
                symbol=clean_symbol,
                start=start_date,
                end=end_date,
                index=is_index  # Use correct parameter based on symbol type
            )

            if df is None or df.empty:
                logger.warning(f"No historical data found for {symbol}")
                raise DataValidationException(f"No historical NSE data for {symbol}")

            # Standardize column names
            df = df.rename(columns={
                'Date': 'Date',
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })

            # Ensure numeric types
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Remove rows with NaN values
            df = df.dropna()

            logger.info(f"Fetched {len(df)} days of data for {symbol}")
            return df

        except (DataFetchException, DataValidationException):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}", exc_info=True)
            raise DataFetchException(f"NSE historical data fetch failed for {symbol}") from e

    def get_technical_indicators(
        self,
        historical_data: pd.DataFrame,
        symbol: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Calculate 40+ technical indicators using TA-Lib with optional caching.

        Args:
            historical_data: Historical OHLCV DataFrame
            symbol: Stock symbol (optional, enables caching if provided)
            use_cache: Whether to use incremental caching (default: True)

        Returns:
            Dictionary of technical indicators
        """
        if historical_data.empty or len(historical_data) < 14:
            logger.warning("Insufficient data for technical indicators")
            return {}

        if not TALIB_AVAILABLE:
            logger.warning("TA-Lib not available, returning limited indicators")
            return self._get_basic_indicators(historical_data)

        # Use cache if symbol provided and caching enabled
        if symbol and use_cache:
            return self.indicator_cache.get_indicators(
                symbol=symbol,
                price_data=historical_data,
                calculator_func=lambda data: self._calculate_indicators(data)
            )

        # Direct calculation without cache
        return self._calculate_indicators(historical_data)

    def _calculate_indicators(self, historical_data: pd.DataFrame) -> Dict:
        """
        Internal method to calculate all technical indicators.

        Args:
            historical_data: Historical OHLCV DataFrame

        Returns:
            Dictionary of technical indicators
        """
        try:
            # Convert to numpy arrays
            close = historical_data['Close'].values.astype(np.float64)
            high = historical_data['High'].values.astype(np.float64)
            low = historical_data['Low'].values.astype(np.float64)
            volume = historical_data['Volume'].values.astype(np.float64)

            indicators = {}

            # Momentum Indicators
            indicators['rsi'] = talib.RSI(close, timeperiod=14)
            indicators['stoch_k'], indicators['stoch_d'] = talib.STOCH(high, low, close)
            indicators['williams_r'] = talib.WILLR(high, low, close, timeperiod=14)
            indicators['cci'] = talib.CCI(high, low, close, timeperiod=14)
            indicators['roc'] = talib.ROC(close, timeperiod=10)
            indicators['momentum'] = talib.MOM(close, timeperiod=10)

            # Trend Indicators
            indicators['sma_20'] = talib.SMA(close, timeperiod=20)
            indicators['sma_50'] = talib.SMA(close, timeperiod=50)
            indicators['sma_200'] = talib.SMA(close, timeperiod=200)
            indicators['ema_12'] = talib.EMA(close, timeperiod=12)
            indicators['ema_26'] = talib.EMA(close, timeperiod=26)
            indicators['dema'] = talib.DEMA(close, timeperiod=30)
            indicators['tema'] = talib.TEMA(close, timeperiod=30)

            # MACD
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'] = \
                talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

            # Bollinger Bands
            indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = \
                talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)

            # ADX
            indicators['adx'] = talib.ADX(high, low, close, timeperiod=14)

            # Volatility Indicators
            indicators['atr'] = talib.ATR(high, low, close, timeperiod=14)
            indicators['natr'] = talib.NATR(high, low, close, timeperiod=14)

            # Volume Indicators (Critical for Institutional Flow Agent)
            indicators['obv'] = talib.OBV(close, volume)
            indicators['ad'] = talib.AD(high, low, close, volume)
            indicators['mfi'] = talib.MFI(high, low, close, volume, timeperiod=14)
            indicators['adosc'] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)

            # Calculate VWAP (not in TA-Lib)
            indicators['vwap'] = self._calculate_vwap(high, low, close, volume)

            # Volume Z-score
            indicators['volume_zscore'] = self._calculate_volume_zscore(volume)

            # Extract latest values for scalar indicators
            result = {}
            for key, value in indicators.items():
                if isinstance(value, np.ndarray):
                    if key in ['obv', 'ad']:  # Keep full arrays for trend analysis
                        result[key] = value
                    else:
                        result[key] = float(value[-1]) if not np.isnan(value[-1]) else None
                else:
                    result[key] = value

            logger.info(f"Calculated {len(result)} technical indicators")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate technical indicators: {e}")
            return {}

    def _calculate_vwap(self, high, low, close, volume, window: int = 50) -> np.ndarray:
        """Calculate Volume Weighted Average Price using rolling window"""
        try:
            # Convert to pandas Series for rolling operations
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            close_series = pd.Series(close)
            volume_series = pd.Series(volume)

            # Calculate typical price
            typical_price = (high_series + low_series + close_series) / 3

            # Use rolling window instead of cumsum to prevent overflow
            tp_volume = typical_price * volume_series
            vwap = tp_volume.rolling(window=window).sum() / volume_series.rolling(window=window).sum()

            # Fill initial NaN values with typical price
            vwap = vwap.fillna(typical_price)

            return vwap.values
        except Exception as e:
            logger.error(f"Failed to calculate VWAP: {e}")
            return np.array([])

    def _calculate_volume_zscore(self, volume, window: int = 20) -> np.ndarray:
        """Calculate volume Z-score for spike detection"""
        try:
            volume_series = pd.Series(volume)
            rolling_mean = volume_series.rolling(window=window).mean()
            rolling_std = volume_series.rolling(window=window).std()
            zscore = (volume_series - rolling_mean) / rolling_std
            return zscore.fillna(0).values
        except Exception as e:
            logger.error(f"Failed to calculate volume Z-score: {e}")
            return np.zeros_like(volume)

    def _get_basic_indicators(self, historical_data: pd.DataFrame) -> Dict:
        """Calculate basic indicators without TA-Lib"""
        try:
            close = historical_data['Close']

            # Simple Moving Averages
            sma_20 = close.rolling(window=20).mean().iloc[-1]
            sma_50 = close.rolling(window=50).mean().iloc[-1]

            # Basic RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return {
                'sma_20': float(sma_20) if not pd.isna(sma_20) else None,
                'sma_50': float(sma_50) if not pd.isna(sma_50) else None,
                'rsi': float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
            }
        except Exception as e:
            logger.error(f"Failed to calculate basic indicators: {e}")
            return {}

    def get_comprehensive_data(self, symbol: str) -> Dict:
        """Get all data with caching"""
        # Check cache first
        cached = self._get_cached_data(symbol)
        if cached:
            return cached

        logger.info(f"Fetching comprehensive data for {symbol} from NSE")

        try:
            # Get historical data (2 years)
            historical_data = self.get_historical_data(symbol, period="2y")

            if historical_data.empty:
                logger.warning(f"No historical data for {symbol}")
                return self._create_empty_data(symbol, "No historical data available")

            # Get latest stock data
            stock_data = self.get_stock_data(symbol)

            # Calculate technical indicators with caching
            technical_data = self.get_technical_indicators(historical_data, symbol=symbol, use_cache=True)

            # Compute 52-week high/low from historical data
            week_52_high = None
            week_52_low = None
            if not historical_data.empty:
                last_year = historical_data.iloc[-252:] if len(historical_data) >= 252 else historical_data
                week_52_high = float(last_year['High'].max())
                week_52_low = float(last_year['Low'].min())

            # Assemble comprehensive data
            comprehensive_data = {
                'symbol': symbol,
                'current_price': stock_data.get('current_price'),
                'price_change_percent': stock_data.get('price_change_percent'),
                'market_cap': None,  # NSEpy doesn't provide market cap
                'sector': None,  # NSEpy doesn't provide sector
                'week_52_high': week_52_high,
                'week_52_low': week_52_low,
                'historical_data': historical_data,
                'technical_data': technical_data,
                'info': stock_data,
                'financials': pd.DataFrame(),  # NSEpy doesn't provide financials
                'quarterly_financials': pd.DataFrame(),
                'data_completeness': {
                    'has_historical': not historical_data.empty,
                    'has_financials': False,
                    'has_quarterly': False,
                    'has_info': bool(stock_data),
                    'has_technical': bool(technical_data)
                },
                'timestamp': datetime.now().isoformat(),
                'provider': self.provider_name
            }

            # Cache the result
            self._cache_data(symbol, comprehensive_data)

            return comprehensive_data

        except Exception as e:
            logger.error(f"Failed to get comprehensive data for {symbol}: {e}")
            return self._create_empty_data(symbol, str(e))


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    provider = NSEProvider()

    # Test with TCS
    data = provider.get_comprehensive_data("TCS")

    print(f"\n{'='*60}")
    print(f"Symbol: {data['symbol']}")
    print(f"Current Price: ₹{data['current_price']:.2f}" if data['current_price'] else "N/A")
    print(f"Change: {data['price_change_percent']:.2f}%" if data['price_change_percent'] else "N/A")
    print(f"Historical Data Points: {len(data['historical_data'])}")
    print(f"Technical Indicators: {len(data['technical_data'])}")
    print(f"Data Completeness: {data['data_completeness']}")

    if data['technical_data']:
        print(f"\nSample Indicators:")
        print(f"  RSI: {data['technical_data'].get('rsi', 'N/A')}")
        print(f"  SMA 20: {data['technical_data'].get('sma_20', 'N/A')}")
        print(f"  MACD: {data['technical_data'].get('macd', 'N/A')}")
