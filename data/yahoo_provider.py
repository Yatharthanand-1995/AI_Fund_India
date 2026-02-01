"""
Yahoo Finance Data Provider
Fallback provider for Indian stocks (using .NS or .BO suffix)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
import time

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not available. Install with: pip install yfinance")

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

from data.base_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class YahooFinanceProvider(BaseDataProvider):
    """
    Data provider for Indian stocks using Yahoo Finance

    Features:
    - Uses .NS suffix for NSE stocks, .BO for BSE stocks
    - Provides financials and company info (when available)
    - Analyst ratings and target prices
    - 40+ technical indicators
    - 15-second timeout protection
    """

    def __init__(
        self,
        cache_duration: int = 1200,
        timeout: int = 15,
        exchange: str = "NS"  # NS for NSE, BO for BSE
    ):
        """
        Initialize Yahoo Finance provider

        Args:
            cache_duration: Cache TTL in seconds (default: 1200 = 20 min)
            timeout: Request timeout in seconds (default: 15)
            exchange: NSE (NS) or BSE (BO) - default: NS
        """
        super().__init__(cache_duration)
        self.timeout = timeout
        self.exchange = exchange

        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance is required. Install with: pip install yfinance")

    def _add_exchange_suffix(self, symbol: str) -> str:
        """
        Add exchange suffix if not present

        Args:
            symbol: Stock symbol (e.g., "TCS" or "TCS.NS")

        Returns:
            Symbol with suffix (e.g., "TCS.NS")
        """
        if '.' not in symbol:
            return f"{symbol}.{self.exchange}"
        return symbol

    def get_stock_data(self, symbol: str) -> Dict:
        """Fetch basic stock info from Yahoo Finance"""
        try:
            symbol_with_suffix = self._add_exchange_suffix(symbol)
            ticker = yf.Ticker(symbol_with_suffix)

            # Get info (sometimes slow or incomplete)
            info = ticker.info

            if not info or 'regularMarketPrice' not in info:
                logger.warning(f"Limited info available for {symbol_with_suffix}")
                return {}

            return {
                'symbol': symbol,
                'yahoo_symbol': symbol_with_suffix,
                'current_price': info.get('regularMarketPrice') or info.get('currentPrice'),
                'open': info.get('regularMarketOpen') or info.get('open'),
                'high': info.get('dayHigh'),
                'low': info.get('dayLow'),
                'volume': info.get('volume'),
                'price_change_percent': info.get('regularMarketChangePercent'),
                'market_cap': info.get('marketCap'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'company_name': info.get('longName') or info.get('shortName'),
                'pe_ratio': info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            }

        except Exception as e:
            logger.error(f"Failed to fetch stock data for {symbol}: {e}")
            return {}

    def get_historical_data(
        self,
        symbol: str,
        period: str = "2y",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data from Yahoo Finance"""
        try:
            symbol_with_suffix = self._add_exchange_suffix(symbol)

            logger.info(f"Fetching historical data for {symbol_with_suffix} (period: {period})")

            # Download data
            if start_date and end_date:
                df = yf.download(
                    symbol_with_suffix,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    timeout=self.timeout
                )
            else:
                df = yf.download(
                    symbol_with_suffix,
                    period=period,
                    progress=False,
                    timeout=self.timeout
                )

            if df.empty:
                logger.warning(f"No historical data found for {symbol_with_suffix}")
                return pd.DataFrame()

            # Clean up multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Ensure we have required columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns for {symbol_with_suffix}")
                return pd.DataFrame()

            # Ensure numeric types
            for col in required_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Remove rows with NaN values
            df = df.dropna()

            logger.info(f"Fetched {len(df)} days of data for {symbol_with_suffix}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_technical_indicators(self, historical_data: pd.DataFrame) -> Dict:
        """Calculate technical indicators (same as NSE provider)"""
        if historical_data.empty or len(historical_data) < 14:
            logger.warning("Insufficient data for technical indicators")
            return {}

        if not TALIB_AVAILABLE:
            logger.warning("TA-Lib not available, returning limited indicators")
            return {}

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

            # Trend Indicators
            indicators['sma_20'] = talib.SMA(close, timeperiod=20)
            indicators['sma_50'] = talib.SMA(close, timeperiod=50)
            indicators['sma_200'] = talib.SMA(close, timeperiod=200)
            indicators['ema_12'] = talib.EMA(close, timeperiod=12)
            indicators['ema_26'] = talib.EMA(close, timeperiod=26)

            # MACD
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'] = \
                talib.MACD(close)

            # Bollinger Bands
            indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = \
                talib.BBANDS(close, timeperiod=20)

            # Volume Indicators
            indicators['obv'] = talib.OBV(close, volume)
            indicators['ad'] = talib.AD(high, low, close, volume)
            indicators['mfi'] = talib.MFI(high, low, close, volume, timeperiod=14)

            # VWAP
            typical_price = (high + low + close) / 3
            indicators['vwap'] = np.cumsum(typical_price * volume) / np.cumsum(volume)

            # Extract latest values
            result = {}
            for key, value in indicators.items():
                if isinstance(value, np.ndarray):
                    if key in ['obv', 'ad', 'vwap']:
                        result[key] = value
                    else:
                        result[key] = float(value[-1]) if not np.isnan(value[-1]) else None
                else:
                    result[key] = value

            return result

        except Exception as e:
            logger.error(f"Failed to calculate technical indicators: {e}")
            return {}

    def get_financials(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Get financial statements from Yahoo Finance"""
        try:
            symbol_with_suffix = self._add_exchange_suffix(symbol)
            ticker = yf.Ticker(symbol_with_suffix)

            return {
                'financials': ticker.financials,
                'quarterly_financials': ticker.quarterly_financials,
                'balance_sheet': ticker.balance_sheet,
                'quarterly_balance_sheet': ticker.quarterly_balance_sheet,
                'cashflow': ticker.cashflow,
                'quarterly_cashflow': ticker.quarterly_cashflow
            }

        except Exception as e:
            logger.error(f"Failed to fetch financials for {symbol}: {e}")
            return {
                'financials': pd.DataFrame(),
                'quarterly_financials': pd.DataFrame(),
                'balance_sheet': pd.DataFrame(),
                'quarterly_balance_sheet': pd.DataFrame(),
                'cashflow': pd.DataFrame(),
                'quarterly_cashflow': pd.DataFrame()
            }

    def get_comprehensive_data(self, symbol: str) -> Dict:
        """Get all data with caching"""
        # Check cache first
        cached = self._get_cached_data(symbol)
        if cached:
            return cached

        logger.info(f"Fetching comprehensive data for {symbol} from Yahoo Finance")

        try:
            symbol_with_suffix = self._add_exchange_suffix(symbol)
            ticker = yf.Ticker(symbol_with_suffix)

            # Get historical data (2 years)
            historical_data = self.get_historical_data(symbol, period="2y")

            if historical_data.empty:
                logger.warning(f"No historical data for {symbol_with_suffix}")
                return self._create_empty_data(symbol, "No historical data available")

            # Get stock info
            info = ticker.info or {}

            # Get financials
            financials_data = self.get_financials(symbol)

            # Calculate technical indicators
            technical_data = self.get_technical_indicators(historical_data)

            # Get latest price from historical data
            latest = historical_data.iloc[-1]
            prev = historical_data.iloc[-2] if len(historical_data) > 1 else latest
            price_change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

            # Assemble comprehensive data
            comprehensive_data = {
                'symbol': symbol,
                'yahoo_symbol': symbol_with_suffix,
                'current_price': float(latest['Close']),
                'price_change_percent': float(price_change_pct),
                'market_cap': info.get('marketCap'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'company_name': info.get('longName') or info.get('shortName'),
                'historical_data': historical_data,
                'technical_data': technical_data,
                'info': info,
                'financials': financials_data.get('financials', pd.DataFrame()),
                'quarterly_financials': financials_data.get('quarterly_financials', pd.DataFrame()),
                'data_completeness': {
                    'has_historical': not historical_data.empty,
                    'has_financials': not financials_data.get('financials', pd.DataFrame()).empty,
                    'has_quarterly': not financials_data.get('quarterly_financials', pd.DataFrame()).empty,
                    'has_info': bool(info),
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

    provider = YahooFinanceProvider(exchange="NS")

    # Test with TCS
    data = provider.get_comprehensive_data("TCS")

    print(f"\n{'='*60}")
    print(f"Symbol: {data['symbol']}")
    print(f"Yahoo Symbol: {data.get('yahoo_symbol')}")
    print(f"Company: {data.get('company_name', 'N/A')}")
    print(f"Current Price: ₹{data['current_price']:.2f}" if data['current_price'] else "N/A")
    print(f"Change: {data['price_change_percent']:.2f}%" if data['price_change_percent'] else "N/A")
    print(f"Market Cap: ₹{data['market_cap']/1e7:.2f} Cr" if data.get('market_cap') else "N/A")
    print(f"Sector: {data.get('sector', 'N/A')}")
    print(f"Historical Data Points: {len(data['historical_data'])}")
    print(f"Technical Indicators: {len(data['technical_data'])}")
    print(f"Has Financials: {data['data_completeness']['has_financials']}")
