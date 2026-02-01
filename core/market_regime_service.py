"""
Market Regime Detection Service

Analyzes market conditions (NIFTY50) and provides adaptive weights:
- Trend Detection: Bull, Bear, Sideways
- Volatility Detection: High, Normal, Low
- Adaptive Weights: Adjust agent weights based on regime

Strategy:
- Bull + Normal Vol: Balanced (36/27/18/9/10)
- Bull + High Vol: More Momentum (27/36/18/9/10)
- Bear + High Vol: More Quality/Safety (18/18/36/18/10)
- Bear + Normal: Fundamentals + Quality (27/18/27/18/10)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MarketRegimeService:
    """
    Market Regime Detection Service

    Analyzes NIFTY50 index to determine:
    1. Trend: BULL, BEAR, SIDEWAYS
    2. Volatility: HIGH, NORMAL, LOW
    3. Combined Regime: BULL_NORMAL, BEAR_HIGH, etc.

    Provides adaptive weights based on regime with 6-hour caching.
    """

    # Trend thresholds
    TREND_THRESHOLDS = {
        'sma_50_200_diff_bull': 0.02,    # 50-SMA > 200-SMA by 2%
        'sma_50_200_diff_bear': -0.02,   # 50-SMA < 200-SMA by 2%
        'price_sma_50_bull': 0.01,       # Price > 50-SMA by 1%
        'price_sma_50_bear': -0.01,      # Price < 50-SMA by 1%
    }

    # Volatility thresholds (annualized %)
    VOLATILITY_THRESHOLDS = {
        'high': 25,      # >25% = high volatility
        'normal': 15,    # 15-25% = normal
        'low': 15,       # <15% = low volatility
    }

    # Adaptive weight mappings
    ADAPTIVE_WEIGHTS = {
        'BULL_NORMAL': {
            'fundamentals': 0.36,
            'momentum': 0.27,
            'quality': 0.18,
            'sentiment': 0.09,
            'institutional_flow': 0.10
        },
        'BULL_HIGH': {
            'fundamentals': 0.27,
            'momentum': 0.36,      # Increase momentum in volatile bull
            'quality': 0.18,
            'sentiment': 0.09,
            'institutional_flow': 0.10
        },
        'BULL_LOW': {
            'fundamentals': 0.40,  # Increase fundamentals in stable bull
            'momentum': 0.25,
            'quality': 0.15,
            'sentiment': 0.10,
            'institutional_flow': 0.10
        },
        'BEAR_NORMAL': {
            'fundamentals': 0.27,
            'momentum': 0.18,
            'quality': 0.27,      # Increase quality in bear
            'sentiment': 0.18,    # Increase sentiment for reversal signals
            'institutional_flow': 0.10
        },
        'BEAR_HIGH': {
            'fundamentals': 0.18,
            'momentum': 0.18,
            'quality': 0.36,      # Maximum quality in volatile bear (safety)
            'sentiment': 0.18,
            'institutional_flow': 0.10
        },
        'BEAR_LOW': {
            'fundamentals': 0.30,
            'momentum': 0.15,
            'quality': 0.30,      # Quality + fundamentals
            'sentiment': 0.15,
            'institutional_flow': 0.10
        },
        'SIDEWAYS_NORMAL': {
            'fundamentals': 0.36,  # Default weights
            'momentum': 0.27,
            'quality': 0.18,
            'sentiment': 0.09,
            'institutional_flow': 0.10
        },
        'SIDEWAYS_HIGH': {
            'fundamentals': 0.30,
            'momentum': 0.20,
            'quality': 0.30,      # Quality for stability
            'sentiment': 0.10,
            'institutional_flow': 0.10
        },
        'SIDEWAYS_LOW': {
            'fundamentals': 0.36,
            'momentum': 0.27,
            'quality': 0.18,
            'sentiment': 0.09,
            'institutional_flow': 0.10
        }
    }

    def __init__(self, cache_duration_hours: int = 6):
        """
        Initialize Market Regime Service

        Args:
            cache_duration_hours: How long to cache regime (default: 6 hours)
        """
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cached_regime: Optional[Dict] = None
        self.cache_timestamp: Optional[datetime] = None

        logger.info(f"Market Regime Service initialized (cache: {cache_duration_hours}h)")

    def get_current_regime(
        self,
        nifty_data: Optional[pd.DataFrame] = None,
        data_provider = None
    ) -> Dict:
        """
        Get current market regime with caching

        Args:
            nifty_data: Pre-fetched NIFTY50 data (optional)
            data_provider: Data provider to fetch NIFTY if needed

        Returns:
            {
                'regime': str (e.g., "BULL_NORMAL"),
                'trend': str ("BULL", "BEAR", "SIDEWAYS"),
                'volatility': str ("HIGH", "NORMAL", "LOW"),
                'weights': dict,
                'metrics': {
                    'current_price': float,
                    'sma_50': float,
                    'sma_200': float,
                    'volatility_pct': float,
                    ...
                },
                'timestamp': str,
                'cached': bool
            }
        """
        # Check cache
        if self._is_cache_valid():
            logger.info("Using cached market regime")
            return {**self.cached_regime, 'cached': True}

        logger.info("Detecting current market regime...")

        try:
            # Fetch NIFTY data if not provided
            if nifty_data is None or nifty_data.empty:
                if data_provider is None:
                    raise ValueError("Must provide either nifty_data or data_provider")

                logger.info("Fetching NIFTY50 data...")
                nifty_cached = data_provider.get_comprehensive_data('^NSEI')
                nifty_data = nifty_cached.get('historical_data', pd.DataFrame())

                if nifty_data.empty:
                    raise ValueError("No NIFTY50 data available")

            # Detect regime
            trend, trend_metrics = self._detect_trend(nifty_data)
            volatility, vol_metrics = self._detect_volatility(nifty_data)

            # Combine regime
            regime = f"{trend}_{volatility}"

            # Get adaptive weights
            weights = self.ADAPTIVE_WEIGHTS.get(regime, self.ADAPTIVE_WEIGHTS['SIDEWAYS_NORMAL'])

            # Assemble result
            result = {
                'regime': regime,
                'trend': trend,
                'volatility': volatility,
                'weights': weights,
                'metrics': {
                    **trend_metrics,
                    **vol_metrics
                },
                'timestamp': datetime.now().isoformat(),
                'cached': False
            }

            # Cache result
            self.cached_regime = result
            self.cache_timestamp = datetime.now()

            logger.info(f"✅ Market Regime: {regime}")
            logger.info(f"   Trend: {trend}, Volatility: {volatility}")

            return result

        except Exception as e:
            logger.error(f"Failed to detect market regime: {e}", exc_info=True)

            # Return default regime on error
            return {
                'regime': 'SIDEWAYS_NORMAL',
                'trend': 'SIDEWAYS',
                'volatility': 'NORMAL',
                'weights': self.ADAPTIVE_WEIGHTS['SIDEWAYS_NORMAL'],
                'metrics': {},
                'timestamp': datetime.now().isoformat(),
                'cached': False,
                'error': str(e)
            }

    def _detect_trend(self, nifty_data: pd.DataFrame) -> Tuple[str, Dict]:
        """
        Detect market trend

        Rules:
        - BULL: 50-SMA > 200-SMA AND price > 50-SMA
        - BEAR: 50-SMA < 200-SMA AND price < 50-SMA
        - SIDEWAYS: Mixed signals

        Returns:
            (trend_str, metrics_dict)
        """
        try:
            # Get current price
            current_price = float(nifty_data['Close'].iloc[-1])

            # Calculate moving averages
            sma_50 = nifty_data['Close'].rolling(window=50).mean().iloc[-1]
            sma_200 = nifty_data['Close'].rolling(window=200).mean().iloc[-1]

            # Calculate relative positions
            price_vs_sma50 = (current_price - sma_50) / sma_50
            sma50_vs_sma200 = (sma_50 - sma_200) / sma_200

            metrics = {
                'current_price': float(current_price),
                'sma_50': float(sma_50),
                'sma_200': float(sma_200),
                'price_vs_sma50_pct': float(price_vs_sma50 * 100),
                'sma50_vs_sma200_pct': float(sma50_vs_sma200 * 100)
            }

            # Determine trend
            if (sma50_vs_sma200 > self.TREND_THRESHOLDS['sma_50_200_diff_bull'] and
                price_vs_sma50 > self.TREND_THRESHOLDS['price_sma_50_bull']):
                trend = 'BULL'
            elif (sma50_vs_sma200 < self.TREND_THRESHOLDS['sma_50_200_diff_bear'] and
                  price_vs_sma50 < self.TREND_THRESHOLDS['price_sma_50_bear']):
                trend = 'BEAR'
            else:
                trend = 'SIDEWAYS'

            logger.info(f"  Trend: {trend}")
            logger.info(f"    Price vs 50-SMA: {price_vs_sma50*100:+.2f}%")
            logger.info(f"    50-SMA vs 200-SMA: {sma50_vs_sma200*100:+.2f}%")

            return trend, metrics

        except Exception as e:
            logger.error(f"Trend detection failed: {e}")
            return 'SIDEWAYS', {}

    def _detect_volatility(self, nifty_data: pd.DataFrame, window: int = 30) -> Tuple[str, Dict]:
        """
        Detect market volatility

        Uses 30-day rolling volatility (annualized)

        Returns:
            (volatility_str, metrics_dict)
        """
        try:
            # Calculate returns
            returns = nifty_data['Close'].pct_change()

            # Calculate 30-day rolling volatility (annualized)
            volatility = returns.rolling(window=window).std().iloc[-1]
            volatility_pct = float(volatility * np.sqrt(252) * 100)

            # Also calculate recent volatility trend
            vol_series = returns.rolling(window=window).std() * np.sqrt(252) * 100
            vol_trend = 'increasing' if vol_series.iloc[-1] > vol_series.iloc[-10] else 'decreasing'

            metrics = {
                'volatility_pct': volatility_pct,
                'volatility_trend': vol_trend,
                'volatility_window_days': window
            }

            # Classify volatility
            if volatility_pct > self.VOLATILITY_THRESHOLDS['high']:
                vol_class = 'HIGH'
            elif volatility_pct > self.VOLATILITY_THRESHOLDS['normal']:
                vol_class = 'NORMAL'
            else:
                vol_class = 'LOW'

            logger.info(f"  Volatility: {vol_class} ({volatility_pct:.1f}%)")

            return vol_class, metrics

        except Exception as e:
            logger.error(f"Volatility detection failed: {e}")
            return 'NORMAL', {}

    def _is_cache_valid(self) -> bool:
        """Check if cached regime is still valid"""
        if self.cached_regime is None or self.cache_timestamp is None:
            return False

        age = datetime.now() - self.cache_timestamp
        return age < self.cache_duration

    def clear_cache(self):
        """Manually clear cache"""
        self.cached_regime = None
        self.cache_timestamp = None
        logger.info("Market regime cache cleared")

    def get_cache_info(self) -> Dict:
        """Get cache information"""
        if self.cache_timestamp is None:
            return {
                'cached': False,
                'age_seconds': None,
                'expires_in_seconds': None
            }

        age = datetime.now() - self.cache_timestamp
        remaining = self.cache_duration - age

        return {
            'cached': True,
            'cached_regime': self.cached_regime.get('regime') if self.cached_regime else None,
            'age_seconds': age.total_seconds(),
            'expires_in_seconds': max(0, remaining.total_seconds()),
            'cache_valid': self._is_cache_valid()
        }

    def get_all_regimes_weights(self) -> Dict:
        """Get all available regime weight configurations"""
        return self.ADAPTIVE_WEIGHTS.copy()


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize service
    regime_service = MarketRegimeService(cache_duration_hours=6)

    # Create sample NIFTY data (bull market)
    print("\n" + "="*60)
    print("Testing Market Regime Detection")
    print("="*60)

    # Simulate bull market
    dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq='D')
    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(300).cumsum() * 0.01)  # Uptrend

    sample_nifty = pd.DataFrame({
        'Close': prices,
        'High': prices * 1.01,
        'Low': prices * 0.99,
        'Volume': np.random.randint(1000000, 10000000, 300)
    }, index=dates)

    # Detect regime
    regime_info = regime_service.get_current_regime(nifty_data=sample_nifty)

    # Display results
    print(f"\n{'Detected Regime':-^60}")
    print(f"Regime: {regime_info['regime']}")
    print(f"Trend: {regime_info['trend']}")
    print(f"Volatility: {regime_info['volatility']}")

    print(f"\n{'Market Metrics':-^60}")
    for key, value in regime_info['metrics'].items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    print(f"\n{'Adaptive Weights':-^60}")
    for agent, weight in regime_info['weights'].items():
        print(f"  {agent}: {weight:.0%}")

    # Test cache
    print(f"\n{'Cache Test':-^60}")
    regime_info2 = regime_service.get_current_regime(nifty_data=sample_nifty)
    print(f"Second call used cache: {regime_info2['cached']}")

    cache_info = regime_service.get_cache_info()
    print(f"Cache age: {cache_info['age_seconds']:.1f}s")
    print(f"Cache expires in: {cache_info['expires_in_seconds']/3600:.1f}h")

    # Display all regime configurations
    print(f"\n{'All Regime Weight Configurations':-^60}")
    all_weights = regime_service.get_all_regimes_weights()
    for regime_name, weights in all_weights.items():
        print(f"\n{regime_name}:")
        for agent, weight in weights.items():
            print(f"  {agent}: {weight:.0%}")
