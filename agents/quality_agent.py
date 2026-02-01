"""
Quality Agent - Business Quality & Stability Analysis (18% weight)

Analyzes:
- Volatility (lower = better quality)
- Price Stability & Consistency
- Long-term Trend (1-year performance)
- Maximum Drawdown
- Sector Quality Indicators

Scoring: 0-100 with confidence level
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class QualityAgent:
    """
    Quality Agent for Indian stock market

    Focuses on business quality and stability rather than growth or momentum.
    High-quality companies typically have:
    - Lower volatility (stable)
    - Positive long-term trends
    - Manageable drawdowns
    - Consistent performance

    Scoring breakdown (0-100):
    - Volatility: 35 points (lower is better)
    - Long-term Trend: 30 points (1-year performance)
    - Drawdown: 25 points (smaller drawdowns = better)
    - Consistency: 10 points

    Base score: 50 (neutral)
    """

    # Quality thresholds
    THRESHOLDS = {
        # Volatility (annualized %)
        'volatility_excellent': 20,  # Very stable
        'volatility_good': 30,
        'volatility_fair': 40,
        'volatility_poor': 50,

        # 1-year return (%)
        'return_excellent': 20,
        'return_good': 10,
        'return_fair': 0,

        # Maximum drawdown (%)
        'drawdown_excellent': -10,  # Small drawdown
        'drawdown_good': -20,
        'drawdown_fair': -30,
        'drawdown_poor': -50,
    }

    def __init__(self, sector_mapping: Optional[Dict] = None):
        """
        Initialize Quality Agent

        Args:
            sector_mapping: Dict mapping symbols to sectors for sector-based adjustments
        """
        self.agent_name = "QualityAgent"
        self.weight = 0.18  # 18% of total score
        self.sector_mapping = sector_mapping or {}

    def analyze(self, symbol: str, price_data: pd.DataFrame, cached_data: Optional[Dict] = None) -> Dict:
        """
        Analyze business quality and stability

        Args:
            symbol: Stock symbol
            price_data: Historical OHLCV DataFrame
            cached_data: Pre-fetched comprehensive data (optional)

        Returns:
            {
                'score': float (0-100),
                'confidence': float (0-1),
                'reasoning': str,
                'metrics': {
                    'volatility': float,
                    '1y_return': float,
                    'max_drawdown': float,
                    'stability_score': float,
                    ...
                },
                'breakdown': {
                    'volatility_score': float,
                    'trend_score': float,
                    'drawdown_score': float,
                    'consistency_score': float
                }
            }
        """
        logger.info(f"Analyzing quality for {symbol}")

        try:
            if price_data.empty:
                raise ValueError("Empty price data")

            # Calculate metrics
            metrics = self._extract_metrics(symbol, price_data, cached_data)

            # Start with neutral base score of 50
            base_score = 50

            # Calculate component scores (can add or subtract from base)
            volatility_adjustment = self._score_volatility(metrics)
            trend_adjustment = self._score_long_term_trend(metrics)
            drawdown_adjustment = self._score_drawdown(metrics)
            consistency_adjustment = self._score_consistency(metrics)

            # Calculate total score
            total_score = base_score + volatility_adjustment + trend_adjustment + \
                         drawdown_adjustment + consistency_adjustment

            # Clamp to 0-100
            total_score = max(0, min(100, total_score))

            # Calculate confidence
            confidence = self._calculate_confidence(price_data, metrics)

            # Generate reasoning
            reasoning = self._generate_reasoning(metrics, {
                'volatility': volatility_adjustment,
                'trend': trend_adjustment,
                'drawdown': drawdown_adjustment,
                'consistency': consistency_adjustment
            })

            return {
                'score': round(total_score, 2),
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'metrics': metrics,
                'breakdown': {
                    'base_score': 50,
                    'volatility_adjustment': round(volatility_adjustment, 2),
                    'trend_adjustment': round(trend_adjustment, 2),
                    'drawdown_adjustment': round(drawdown_adjustment, 2),
                    'consistency_adjustment': round(consistency_adjustment, 2)
                },
                'agent': self.agent_name
            }

        except Exception as e:
            logger.error(f"Quality analysis failed for {symbol}: {e}", exc_info=True)
            return {
                'score': 50.0,  # Neutral score on failure
                'confidence': 0.1,
                'reasoning': f"Analysis failed: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e)
            }

    def _extract_metrics(self, symbol: str, price_data: pd.DataFrame, cached_data: Optional[Dict]) -> Dict:
        """Extract quality-related metrics"""
        metrics = {}

        # Get basic info
        if cached_data:
            info = cached_data.get('info', {})
            metrics['sector'] = info.get('sector', 'Unknown')
            metrics['market_cap'] = info.get('marketCap')

        # Calculate volatility (annualized)
        metrics['volatility'] = self._calculate_volatility(price_data)

        # Calculate returns
        metrics['1y_return'] = self._calculate_return(price_data, days=252)
        metrics['6m_return'] = self._calculate_return(price_data, days=126)

        # Calculate drawdown
        metrics['max_drawdown'] = self._calculate_max_drawdown(price_data)
        metrics['current_drawdown'] = self._calculate_current_drawdown(price_data)

        # Calculate consistency (coefficient of variation of returns)
        metrics['return_consistency'] = self._calculate_return_consistency(price_data)

        # Price range analysis
        metrics['price_range_52w'] = self._calculate_52w_range(price_data)

        logger.debug(f"Extracted {len([v for v in metrics.values() if v is not None])} quality metrics")
        return metrics

    def _calculate_volatility(self, price_data: pd.DataFrame, window: int = 30) -> Optional[float]:
        """Calculate 30-day annualized volatility (%)"""
        try:
            returns = price_data['Close'].pct_change()
            volatility = returns.rolling(window=window).std().iloc[-1]
            return float(volatility * np.sqrt(252) * 100)  # Annualized percentage
        except Exception as e:
            logger.debug(f"Failed to calculate volatility: {e}")
            return None

    def _calculate_return(self, price_data: pd.DataFrame, days: int) -> Optional[float]:
        """Calculate percentage return over specified days"""
        try:
            if len(price_data) < days:
                return None

            current_price = price_data['Close'].iloc[-1]
            past_price = price_data['Close'].iloc[-days]

            if past_price == 0:
                return None

            return ((current_price - past_price) / past_price) * 100

        except Exception as e:
            logger.debug(f"Failed to calculate {days}-day return: {e}")
            return None

    def _calculate_max_drawdown(self, price_data: pd.DataFrame) -> Optional[float]:
        """
        Calculate maximum drawdown (%)

        Maximum peak-to-trough decline over the period
        """
        try:
            prices = price_data['Close']
            cummax = prices.cummax()
            drawdown = (prices - cummax) / cummax * 100
            return float(drawdown.min())

        except Exception as e:
            logger.debug(f"Failed to calculate max drawdown: {e}")
            return None

    def _calculate_current_drawdown(self, price_data: pd.DataFrame) -> Optional[float]:
        """Calculate current drawdown from all-time high"""
        try:
            prices = price_data['Close']
            all_time_high = prices.max()
            current_price = prices.iloc[-1]
            return ((current_price - all_time_high) / all_time_high) * 100

        except Exception as e:
            logger.debug(f"Failed to calculate current drawdown: {e}")
            return None

    def _calculate_return_consistency(self, price_data: pd.DataFrame) -> Optional[float]:
        """
        Calculate consistency of returns (coefficient of variation)

        Lower CV = more consistent returns = better quality
        """
        try:
            monthly_returns = price_data['Close'].resample('M').last().pct_change().dropna()

            if len(monthly_returns) < 6:
                return None

            mean_return = monthly_returns.mean()
            std_return = monthly_returns.std()

            if mean_return == 0:
                return None

            # Coefficient of variation
            cv = abs(std_return / mean_return)
            return float(cv)

        except Exception as e:
            logger.debug(f"Failed to calculate return consistency: {e}")
            return None

    def _calculate_52w_range(self, price_data: pd.DataFrame) -> Optional[float]:
        """Calculate where current price is in 52-week range (0-100%)"""
        try:
            if len(price_data) < 252:
                return None

            recent_data = price_data.tail(252)
            high_52w = recent_data['High'].max()
            low_52w = recent_data['Low'].min()
            current_price = price_data['Close'].iloc[-1]

            if high_52w == low_52w:
                return None

            range_pct = ((current_price - low_52w) / (high_52w - low_52w)) * 100
            return float(range_pct)

        except Exception as e:
            logger.debug(f"Failed to calculate 52w range: {e}")
            return None

    def _score_volatility(self, metrics: Dict) -> float:
        """
        Score volatility (-20 to +20 adjustment)

        Lower volatility = higher quality (positive adjustment)
        Higher volatility = lower quality (negative adjustment)
        """
        volatility = metrics.get('volatility')

        if volatility is None:
            return 0

        if volatility < self.THRESHOLDS['volatility_excellent']:
            return 20  # Very stable - excellent quality
        elif volatility < self.THRESHOLDS['volatility_good']:
            return 12  # Stable - good quality
        elif volatility < self.THRESHOLDS['volatility_fair']:
            return 5   # Moderate volatility
        elif volatility < self.THRESHOLDS['volatility_poor']:
            return -5  # High volatility
        else:
            return -15  # Very high volatility - poor quality

    def _score_long_term_trend(self, metrics: Dict) -> float:
        """
        Score 1-year trend (-15 to +15 adjustment)

        Positive long-term trend indicates quality and resilience
        """
        return_1y = metrics.get('1y_return')

        if return_1y is None:
            return 0

        if return_1y >= self.THRESHOLDS['return_excellent']:
            return 15  # Excellent long-term performance
        elif return_1y >= self.THRESHOLDS['return_good']:
            return 10  # Good performance
        elif return_1y >= self.THRESHOLDS['return_fair']:
            return 5   # Stable
        elif return_1y >= -10:
            return 0   # Slight decline
        elif return_1y >= -20:
            return -10  # Significant decline
        else:
            return -15  # Major decline - poor quality

    def _score_drawdown(self, metrics: Dict) -> float:
        """
        Score maximum drawdown (-15 to +10 adjustment)

        Smaller drawdowns = better quality (ability to preserve capital)
        """
        max_dd = metrics.get('max_drawdown')

        if max_dd is None:
            return 0

        if max_dd >= self.THRESHOLDS['drawdown_excellent']:
            return 10  # Very small drawdown
        elif max_dd >= self.THRESHOLDS['drawdown_good']:
            return 5   # Manageable drawdown
        elif max_dd >= self.THRESHOLDS['drawdown_fair']:
            return 0   # Moderate drawdown
        elif max_dd >= self.THRESHOLDS['drawdown_poor']:
            return -10  # Large drawdown
        else:
            return -15  # Severe drawdown - poor quality

    def _score_consistency(self, metrics: Dict) -> float:
        """
        Score return consistency (-5 to +5 adjustment)

        Lower coefficient of variation = more consistent = better quality
        """
        consistency = metrics.get('return_consistency')

        if consistency is None:
            return 0

        if consistency < 1.0:
            return 5   # Very consistent
        elif consistency < 2.0:
            return 3   # Consistent
        elif consistency < 3.0:
            return 0   # Moderate
        else:
            return -5  # Inconsistent

    def _calculate_confidence(self, price_data: pd.DataFrame, metrics: Dict) -> float:
        """Calculate confidence level (0-1)"""
        confidence = 0.7  # Base confidence

        # Has sufficient data (1+ year)
        if len(price_data) >= 252:
            confidence += 0.15

        # Has key metrics
        key_metrics = ['volatility', '1y_return', 'max_drawdown']
        available = sum(1 for m in key_metrics if metrics.get(m) is not None)
        if available == len(key_metrics):
            confidence += 0.15

        return min(1.0, confidence)

    def _generate_reasoning(self, metrics: Dict, adjustments: Dict) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        # Volatility
        volatility = metrics.get('volatility')
        if volatility is not None:
            if volatility < self.THRESHOLDS['volatility_excellent']:
                reasons.append(f"Low volatility: {volatility:.1f}%")
            elif volatility > self.THRESHOLDS['volatility_poor']:
                reasons.append(f"High volatility: {volatility:.1f}%")

        # Long-term trend
        return_1y = metrics.get('1y_return')
        if return_1y is not None:
            if return_1y >= 20:
                reasons.append(f"Strong 1Y return: {return_1y:+.1f}%")
            elif return_1y < -10:
                reasons.append(f"Weak 1Y return: {return_1y:+.1f}%")

        # Drawdown
        max_dd = metrics.get('max_drawdown')
        if max_dd is not None:
            if max_dd >= -15:
                reasons.append(f"Small drawdown: {max_dd:.1f}%")
            elif max_dd < -40:
                reasons.append(f"Large drawdown: {max_dd:.1f}%")

        if not reasons:
            reasons.append("Quality metrics available")

        return " | ".join(reasons)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = QualityAgent()

    # Create sample data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=400, freq='D')
    np.random.seed(42)
    prices = 100 + np.random.randn(400).cumsum() * 0.5
    sample_data = pd.DataFrame({
        'Close': prices,
        'High': prices * 1.02,
        'Low': prices * 0.98,
        'Volume': np.random.randint(1000000, 10000000, 400)
    }, index=dates)

    result = agent.analyze("TCS", sample_data)

    print(f"\n{'='*60}")
    print(f"Quality Analysis")
    print('='*60)
    print(f"Score: {result['score']}/100")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"\nBreakdown:")
    for key, value in result['breakdown'].items():
        print(f"  {key}: {value}")
