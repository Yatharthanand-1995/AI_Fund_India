"""
Institutional Flow Agent - Smart Money Tracking (10% weight)

Analyzes:
- OBV (On-Balance Volume) trend - Accumulation/Distribution
- MFI (Money Flow Index) - Buying/Selling pressure
- CMF (Chaikin Money Flow) - Volume-weighted accumulation
- Volume Spikes - Unusual institutional activity
- VWAP - Price vs Volume Weighted Average Price
- Optional: FII/DII flow data (if available for Indian stocks)

Scoring: 0-100 with confidence level
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class InstitutionalFlowAgent:
    """
    Institutional Flow Agent for Indian stock market

    Tracks "smart money" (institutional investors) through volume-based indicators.
    Institutional buying often precedes price movements.

    Scoring breakdown (0-100):
    - OBV Trend: 30 points (accumulation/distribution)
    - MFI: 25 points (money flow strength)
    - CMF: 20 points (Chaikin Money Flow)
    - Volume Spikes: 15 points (unusual activity)
    - VWAP: 10 points (price positioning)

    Base score: 50 (neutral)
    """

    # Thresholds for indicators
    THRESHOLDS = {
        # OBV trend (slope)
        'obv_strong_accumulation': 0.15,
        'obv_accumulation': 0.05,
        'obv_distribution': -0.05,
        'obv_strong_distribution': -0.15,

        # MFI levels
        'mfi_strong_buying': 60,
        'mfi_buying': 50,
        'mfi_selling': 40,
        'mfi_strong_selling': 30,
        'mfi_overbought': 80,

        # CMF levels
        'cmf_strong_accumulation': 0.15,
        'cmf_accumulation': 0.05,
        'cmf_distribution': -0.05,
        'cmf_strong_distribution': -0.15,

        # Volume Z-score
        'volume_spike': 2.0,
        'volume_high': 1.5,
    }

    def __init__(self):
        """Initialize Institutional Flow Agent"""
        self.agent_name = "InstitutionalFlowAgent"
        self.weight = 0.10  # 10% of total score

    def analyze(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        cached_data: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze institutional money flow

        Args:
            symbol: Stock symbol
            price_data: Historical OHLCV DataFrame
            cached_data: Pre-fetched comprehensive data (contains technical indicators)

        Returns:
            {
                'score': float (0-100),
                'confidence': float (0-1),
                'reasoning': str,
                'metrics': {
                    'obv_trend': float,
                    'mfi': float,
                    'cmf': float,
                    'volume_zscore': float,
                    'vwap_position': str,
                    ...
                },
                'breakdown': {
                    'obv_score': float,
                    'mfi_score': float,
                    'cmf_score': float,
                    'volume_spike_score': float,
                    'vwap_score': float
                }
            }
        """
        logger.info(f"Analyzing institutional flow for {symbol}")

        try:
            if price_data.empty:
                raise ValueError("Empty price data")

            # Extract technical indicators
            technical_data = cached_data.get('technical_data', {}) if cached_data else {}

            # Extract metrics
            metrics = self._extract_metrics(price_data, technical_data)

            # Calculate component scores (adjustments to base 50)
            obv_adjustment = self._score_obv_trend(metrics)
            mfi_adjustment = self._score_mfi(metrics)
            cmf_adjustment = self._score_cmf(metrics)
            volume_spike_adjustment = self._score_volume_spikes(metrics)
            vwap_adjustment = self._score_vwap(metrics)

            # Calculate total score
            total_score = 50 + obv_adjustment + mfi_adjustment + cmf_adjustment + \
                         volume_spike_adjustment + vwap_adjustment

            # Clamp to 0-100
            total_score = max(0, min(100, total_score))

            # Calculate confidence
            confidence = self._calculate_confidence(technical_data, metrics)

            # Generate reasoning
            reasoning = self._generate_reasoning(metrics, {
                'obv': obv_adjustment,
                'mfi': mfi_adjustment,
                'cmf': cmf_adjustment,
                'volume_spike': volume_spike_adjustment,
                'vwap': vwap_adjustment
            })

            return {
                'score': round(total_score, 2),
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'metrics': metrics,
                'breakdown': {
                    'base_score': 50,
                    'obv_adjustment': round(obv_adjustment, 2),
                    'mfi_adjustment': round(mfi_adjustment, 2),
                    'cmf_adjustment': round(cmf_adjustment, 2),
                    'volume_spike_adjustment': round(volume_spike_adjustment, 2),
                    'vwap_adjustment': round(vwap_adjustment, 2)
                },
                'agent': self.agent_name
            }

        except Exception as e:
            logger.error(f"Institutional flow analysis failed for {symbol}: {e}", exc_info=True)
            return {
                'score': 50.0,  # Neutral score on failure
                'confidence': 0.1,
                'reasoning': f"Analysis failed: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e)
            }

    def _extract_metrics(self, price_data: pd.DataFrame, technical_data: Dict) -> Dict:
        """Extract institutional flow metrics"""
        metrics = {}

        # Get technical indicators from cached data
        obv_array = technical_data.get('obv')
        mfi_array = technical_data.get('mfi')
        cmf_array = technical_data.get('adosc')  # Chaikin Money Flow
        vwap_array = technical_data.get('vwap')

        # OBV trend (last 20 days)
        if obv_array is not None and len(obv_array) >= 20:
            metrics['obv_trend'] = self._calculate_trend(obv_array[-20:])
            metrics['obv_current'] = float(obv_array[-1]) if len(obv_array) > 0 else None
        else:
            metrics['obv_trend'] = None
            metrics['obv_current'] = None

        # MFI (current value)
        if mfi_array is not None:
            if isinstance(mfi_array, np.ndarray) and len(mfi_array) > 0:
                metrics['mfi'] = float(mfi_array[-1]) if not np.isnan(mfi_array[-1]) else None
            else:
                metrics['mfi'] = float(mfi_array) if not np.isnan(mfi_array) else None
        else:
            metrics['mfi'] = None

        # CMF (current value)
        if cmf_array is not None:
            if isinstance(cmf_array, np.ndarray) and len(cmf_array) > 0:
                metrics['cmf'] = float(cmf_array[-1]) if not np.isnan(cmf_array[-1]) else None
            else:
                metrics['cmf'] = float(cmf_array) if not np.isnan(cmf_array) else None
        else:
            metrics['cmf'] = None

        # Volume Z-score (recent spikes)
        metrics['volume_zscore'] = self._calculate_volume_zscore_latest(price_data)

        # VWAP position
        current_price = float(price_data['Close'].iloc[-1])
        if vwap_array is not None and len(vwap_array) > 0:
            vwap_latest = float(vwap_array[-1])
            metrics['vwap'] = vwap_latest
            metrics['price_vs_vwap'] = ((current_price - vwap_latest) / vwap_latest) * 100
            metrics['vwap_position'] = 'above' if current_price > vwap_latest else 'below'
        else:
            metrics['vwap'] = None
            metrics['price_vs_vwap'] = None
            metrics['vwap_position'] = None

        # Average volume trend
        if len(price_data) >= 20:
            recent_avg_volume = price_data['Volume'].tail(5).mean()
            past_avg_volume = price_data['Volume'].tail(20).iloc[:15].mean()
            if past_avg_volume > 0:
                metrics['volume_trend'] = ((recent_avg_volume - past_avg_volume) / past_avg_volume) * 100
            else:
                metrics['volume_trend'] = None
        else:
            metrics['volume_trend'] = None

        logger.debug(f"Extracted {len([v for v in metrics.values() if v is not None])} flow metrics")
        return metrics

    def _calculate_trend(self, data_array: np.ndarray) -> Optional[float]:
        """
        Calculate trend using linear regression slope

        Positive slope = accumulation/uptrend
        Negative slope = distribution/downtrend
        """
        try:
            if len(data_array) < 5:
                return None

            # Normalize and calculate slope
            x = np.arange(len(data_array))
            y = data_array
            slope = np.polyfit(x, y, 1)[0]

            # Normalize by mean to get percentage trend
            mean_val = np.mean(y)
            if mean_val == 0:
                return None

            normalized_slope = slope / mean_val
            return float(normalized_slope)

        except Exception as e:
            logger.debug(f"Failed to calculate trend: {e}")
            return None

    def _calculate_volume_zscore_latest(self, price_data: pd.DataFrame, window: int = 20) -> Optional[float]:
        """Calculate latest volume Z-score"""
        try:
            if len(price_data) < window:
                return None

            volumes = price_data['Volume'].tail(window + 1)
            latest_volume = volumes.iloc[-1]
            historical_volumes = volumes.iloc[:-1]

            mean = historical_volumes.mean()
            std = historical_volumes.std()

            if std == 0:
                return None

            zscore = (latest_volume - mean) / std
            return float(zscore)

        except Exception as e:
            logger.debug(f"Failed to calculate volume Z-score: {e}")
            return None

    def _score_obv_trend(self, metrics: Dict) -> float:
        """
        Score OBV trend (-15 to +15 adjustment)

        Positive trend = accumulation (bullish)
        Negative trend = distribution (bearish)
        """
        obv_trend = metrics.get('obv_trend')

        if obv_trend is None:
            return 0

        if obv_trend >= self.THRESHOLDS['obv_strong_accumulation']:
            return 15  # Strong accumulation
        elif obv_trend >= self.THRESHOLDS['obv_accumulation']:
            return 10  # Accumulation
        elif obv_trend > self.THRESHOLDS['obv_distribution']:
            return 0   # Neutral
        elif obv_trend > self.THRESHOLDS['obv_strong_distribution']:
            return -10  # Distribution
        else:
            return -15  # Strong distribution

    def _score_mfi(self, metrics: Dict) -> float:
        """
        Score Money Flow Index (-12 to +13 adjustment)

        Higher MFI = more buying pressure
        """
        mfi = metrics.get('mfi')

        if mfi is None:
            return 0

        if mfi >= self.THRESHOLDS['mfi_overbought']:
            return 8   # Overbought (still bullish but cautious)
        elif mfi >= self.THRESHOLDS['mfi_strong_buying']:
            return 13  # Strong buying pressure
        elif mfi >= self.THRESHOLDS['mfi_buying']:
            return 7   # Buying pressure
        elif mfi >= self.THRESHOLDS['mfi_selling']:
            return 0   # Neutral
        elif mfi >= self.THRESHOLDS['mfi_strong_selling']:
            return -7  # Selling pressure
        else:
            return -12  # Strong selling pressure

    def _score_cmf(self, metrics: Dict) -> float:
        """
        Score Chaikin Money Flow (-10 to +10 adjustment)

        Positive CMF = accumulation
        Negative CMF = distribution
        """
        cmf = metrics.get('cmf')

        if cmf is None:
            return 0

        if cmf >= self.THRESHOLDS['cmf_strong_accumulation']:
            return 10  # Strong accumulation
        elif cmf >= self.THRESHOLDS['cmf_accumulation']:
            return 6   # Accumulation
        elif cmf > self.THRESHOLDS['cmf_distribution']:
            return 0   # Neutral
        elif cmf > self.THRESHOLDS['cmf_strong_distribution']:
            return -6  # Distribution
        else:
            return -10  # Strong distribution

    def _score_volume_spikes(self, metrics: Dict) -> float:
        """
        Score volume spikes (-5 to +8 adjustment)

        High volume spikes can indicate institutional activity
        """
        volume_zscore = metrics.get('volume_zscore')

        if volume_zscore is None:
            return 0

        if volume_zscore >= self.THRESHOLDS['volume_spike']:
            return 8   # Significant volume spike
        elif volume_zscore >= self.THRESHOLDS['volume_high']:
            return 5   # High volume
        elif volume_zscore >= 1.0:
            return 3   # Above average volume
        elif volume_zscore >= -1.0:
            return 0   # Normal volume
        else:
            return -2  # Low volume

    def _score_vwap(self, metrics: Dict) -> float:
        """
        Score VWAP positioning (-5 to +5 adjustment)

        Price above VWAP = bullish (institutions buying above average)
        Price below VWAP = bearish
        """
        vwap_position = metrics.get('vwap_position')
        price_vs_vwap = metrics.get('price_vs_vwap')

        if vwap_position is None or price_vs_vwap is None:
            return 0

        if vwap_position == 'above':
            if price_vs_vwap >= 2:
                return 5   # Well above VWAP
            elif price_vs_vwap >= 0.5:
                return 3   # Above VWAP
            else:
                return 1   # Slightly above
        else:  # below
            if price_vs_vwap <= -2:
                return -5  # Well below VWAP
            elif price_vs_vwap <= -0.5:
                return -3  # Below VWAP
            else:
                return -1  # Slightly below

    def _calculate_confidence(self, technical_data: Dict, metrics: Dict) -> float:
        """Calculate confidence level (0-1)"""
        confidence = 0.7  # Base confidence

        # Has key volume indicators
        key_indicators = ['obv', 'mfi', 'adosc', 'vwap']
        available = sum(1 for ind in key_indicators if technical_data.get(ind) is not None)

        if available >= 4:
            confidence += 0.2
        elif available >= 3:
            confidence += 0.15
        elif available >= 2:
            confidence += 0.1

        # Has trend data
        if metrics.get('obv_trend') is not None:
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_reasoning(self, metrics: Dict, adjustments: Dict) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        # OBV trend
        obv_trend = metrics.get('obv_trend')
        if obv_trend is not None:
            if obv_trend >= 0.15:
                reasons.append("Strong accumulation (OBV)")
            elif obv_trend >= 0.05:
                reasons.append("Accumulation (OBV)")
            elif obv_trend <= -0.15:
                reasons.append("Strong distribution (OBV)")
            elif obv_trend <= -0.05:
                reasons.append("Distribution (OBV)")

        # MFI
        mfi = metrics.get('mfi')
        if mfi is not None:
            if mfi >= 60:
                reasons.append(f"Strong buying (MFI: {mfi:.1f})")
            elif mfi <= 40:
                reasons.append(f"Weak buying (MFI: {mfi:.1f})")

        # CMF
        cmf = metrics.get('cmf')
        if cmf is not None:
            if cmf >= 0.15:
                reasons.append(f"High CMF: {cmf:.2f}")
            elif cmf <= -0.15:
                reasons.append(f"Low CMF: {cmf:.2f}")

        # Volume spike
        vol_z = metrics.get('volume_zscore')
        if vol_z is not None and vol_z >= 2.0:
            reasons.append(f"Volume spike (Z: {vol_z:.1f})")

        # VWAP
        vwap_pos = metrics.get('vwap_position')
        price_vs_vwap = metrics.get('price_vs_vwap')
        if vwap_pos and price_vs_vwap is not None:
            if vwap_pos == 'above' and price_vs_vwap >= 1:
                reasons.append(f"Above VWAP (+{price_vs_vwap:.1f}%)")
            elif vwap_pos == 'below' and price_vs_vwap <= -1:
                reasons.append(f"Below VWAP ({price_vs_vwap:.1f}%)")

        if not reasons:
            reasons.append("Neutral institutional flow")

        return " | ".join(reasons)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = InstitutionalFlowAgent()

    # Create sample data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
    sample_data = pd.DataFrame({
        'Close': 100 + np.random.randn(100).cumsum(),
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    # Sample technical data
    sample_technical = {
        'obv': np.random.randn(100).cumsum() * 1e6,
        'mfi': np.array([65.5]),
        'adosc': np.array([0.12]),
        'vwap': 100 + np.random.randn(100).cumsum() * 0.3
    }

    sample_cached = {'technical_data': sample_technical}

    result = agent.analyze("TCS", sample_data, sample_cached)

    print(f"\n{'='*60}")
    print(f"Institutional Flow Analysis")
    print('='*60)
    print(f"Score: {result['score']}/100")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"\nBreakdown:")
    for key, value in result['breakdown'].items():
        print(f"  {key}: {value}")
