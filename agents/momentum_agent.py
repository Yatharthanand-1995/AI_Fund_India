"""
Momentum Agent - Technical Analysis & Price Trends (27% weight)

Analyzes:
- RSI (Relative Strength Index)
- Moving Averages (SMA 20/50/200, EMA 12/26)
- MACD (Moving Average Convergence Divergence)
- Price Returns (1M, 3M, 6M, 1Y)
- Relative Strength vs NIFTY50
- Trend Direction

Scoring: 0-100 with confidence level
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MomentumAgent:
    """
    Momentum Agent for Indian stock market

    Scoring breakdown (0-100):
    - RSI: 25 points
    - Trend (MA crossovers): 35 points
    - Returns: 30 points
    - Relative Strength vs NIFTY: 10 points

    Confidence factors:
    - Base: 0.8 (technical data is usually reliable)
    - +0.1 if has long-term data (>200 days)
    - +0.1 if has NIFTY benchmark data
    """

    # Technical indicator thresholds
    THRESHOLDS = {
        # RSI levels
        'rsi_oversold': 30,
        'rsi_neutral_low': 40,
        'rsi_neutral_high': 60,
        'rsi_overbought': 70,
        'rsi_strong_buy': 50,

        # Return thresholds (%)
        'return_excellent': 15,
        'return_good': 10,
        'return_fair': 5,
        'return_poor': 0,

        # MACD
        'macd_strong_bullish': 0.5,
        'macd_bullish': 0,
    }

    def __init__(self):
        """Initialize Momentum Agent"""
        self.agent_name = "MomentumAgent"
        self.weight = 0.27  # 27% of total score

    def analyze(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        nifty_data: Optional[pd.DataFrame] = None,
        cached_data: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze momentum and technical indicators

        Args:
            symbol: Stock symbol (e.g., "TCS")
            price_data: Historical OHLCV DataFrame
            nifty_data: NIFTY50 historical data for relative strength (optional)
            cached_data: Pre-fetched comprehensive data (contains technical indicators)

        Returns:
            {
                'score': float (0-100),
                'confidence': float (0-1),
                'reasoning': str,
                'metrics': {
                    'rsi': float,
                    '1m_return': float,
                    '3m_return': float,
                    '6m_return': float,
                    'trend': str,
                    'relative_strength': float,
                    ...
                },
                'breakdown': {
                    'rsi_score': float,
                    'trend_score': float,
                    'returns_score': float,
                    'relative_strength_score': float
                }
            }
        """
        logger.info(f"Analyzing momentum for {symbol}")

        try:
            if price_data.empty:
                raise ValueError("Empty price data")

            # Extract technical indicators from cached data
            technical_data = cached_data.get('technical_data', {}) if cached_data else {}

            # Calculate metrics
            metrics = self._extract_metrics(price_data, nifty_data, technical_data)

            # Calculate component scores
            rsi_score = self._score_rsi(metrics)
            trend_score = self._score_trend(metrics)
            returns_score = self._score_returns(metrics)
            relative_strength_score = self._score_relative_strength(metrics)

            # Calculate total score
            total_score = (
                rsi_score +
                trend_score +
                returns_score +
                relative_strength_score
            )

            # Calculate confidence
            confidence = self._calculate_confidence(price_data, nifty_data, technical_data)

            # Generate reasoning
            reasoning = self._generate_reasoning(metrics, {
                'rsi': rsi_score,
                'trend': trend_score,
                'returns': returns_score,
                'relative_strength': relative_strength_score
            })

            return {
                'score': round(total_score, 2),
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'metrics': metrics,
                'breakdown': {
                    'rsi_score': round(rsi_score, 2),
                    'trend_score': round(trend_score, 2),
                    'returns_score': round(returns_score, 2),
                    'relative_strength_score': round(relative_strength_score, 2)
                },
                'agent': self.agent_name
            }

        except Exception as e:
            logger.error(f"Momentum analysis failed for {symbol}: {e}", exc_info=True)
            return {
                'score': 50.0,  # Neutral score on failure
                'confidence': 0.1,
                'reasoning': f"Analysis failed: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e)
            }

    def _extract_metrics(
        self,
        price_data: pd.DataFrame,
        nifty_data: Optional[pd.DataFrame],
        technical_data: Dict
    ) -> Dict:
        """Extract all momentum-related metrics"""
        metrics = {}

        # Get current and historical prices
        current_price = float(price_data['Close'].iloc[-1])
        metrics['current_price'] = current_price

        # Calculate returns
        metrics['1m_return'] = self._calculate_return(price_data, days=20)  # ~1 month
        metrics['3m_return'] = self._calculate_return(price_data, days=60)  # ~3 months
        metrics['6m_return'] = self._calculate_return(price_data, days=120)  # ~6 months
        metrics['1y_return'] = self._calculate_return(price_data, days=252)  # ~1 year

        # Extract technical indicators from cached data
        metrics['rsi'] = technical_data.get('rsi')
        metrics['macd'] = technical_data.get('macd')
        metrics['macd_signal'] = technical_data.get('macd_signal')
        metrics['macd_histogram'] = technical_data.get('macd_histogram')

        # Moving averages
        metrics['sma_20'] = technical_data.get('sma_20')
        metrics['sma_50'] = technical_data.get('sma_50')
        metrics['sma_200'] = technical_data.get('sma_200')
        metrics['ema_12'] = technical_data.get('ema_12')
        metrics['ema_26'] = technical_data.get('ema_26')

        # Determine trend
        metrics['trend'] = self._determine_trend(
            current_price,
            metrics.get('sma_20'),
            metrics.get('sma_50'),
            metrics.get('sma_200')
        )

        # Price position relative to MAs
        if metrics['sma_20']:
            metrics['price_vs_sma20'] = ((current_price - metrics['sma_20']) / metrics['sma_20']) * 100
        if metrics['sma_50']:
            metrics['price_vs_sma50'] = ((current_price - metrics['sma_50']) / metrics['sma_50']) * 100

        # Relative strength vs NIFTY
        if nifty_data is not None and not nifty_data.empty:
            metrics['relative_strength'] = self._calculate_relative_strength(
                price_data,
                nifty_data
            )
            metrics['nifty_3m_return'] = self._calculate_return(nifty_data, days=60)
        else:
            metrics['relative_strength'] = None
            metrics['nifty_3m_return'] = None

        # Volatility (for context)
        metrics['volatility'] = self._calculate_volatility(price_data)

        logger.debug(f"Extracted {len([v for v in metrics.values() if v is not None])} momentum metrics")
        return metrics

    def _calculate_return(self, price_data: pd.DataFrame, days: int) -> Optional[float]:
        """Calculate percentage return over specified days"""
        try:
            if len(price_data) < days:
                logger.debug(f"Insufficient data for {days}-day return")
                return None

            current_price = price_data['Close'].iloc[-1]
            past_price = price_data['Close'].iloc[-days]

            if past_price == 0:
                return None

            return ((current_price - past_price) / past_price) * 100

        except Exception as e:
            logger.debug(f"Failed to calculate {days}-day return: {e}")
            return None

    def _calculate_relative_strength(
        self,
        stock_data: pd.DataFrame,
        nifty_data: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate relative strength vs NIFTY50

        Returns percentage outperformance/underperformance
        """
        try:
            # Use 3-month period
            stock_return = self._calculate_return(stock_data, days=60)
            nifty_return = self._calculate_return(nifty_data, days=60)

            if stock_return is None or nifty_return is None:
                return None

            return stock_return - nifty_return

        except Exception as e:
            logger.debug(f"Failed to calculate relative strength: {e}")
            return None

    def _calculate_volatility(self, price_data: pd.DataFrame, window: int = 30) -> Optional[float]:
        """Calculate 30-day volatility (annualized)"""
        try:
            returns = price_data['Close'].pct_change()
            volatility = returns.rolling(window=window).std().iloc[-1]
            return float(volatility * np.sqrt(252) * 100)  # Annualized percentage
        except Exception as e:
            logger.debug(f"Failed to calculate volatility: {e}")
            return None

    def _determine_trend(
        self,
        price: float,
        sma_20: Optional[float],
        sma_50: Optional[float],
        sma_200: Optional[float]
    ) -> str:
        """
        Determine overall trend direction

        Returns: 'strong_uptrend', 'uptrend', 'sideways', 'downtrend', 'strong_downtrend'
        """
        if not sma_20 or not sma_50:
            return 'unknown'

        # Strong uptrend: Price > SMA20 > SMA50 > SMA200
        if price > sma_20 > sma_50:
            if sma_200 and sma_50 > sma_200:
                return 'strong_uptrend'
            return 'uptrend'

        # Strong downtrend: Price < SMA20 < SMA50 < SMA200
        if price < sma_20 < sma_50:
            if sma_200 and sma_50 < sma_200:
                return 'strong_downtrend'
            return 'downtrend'

        # Sideways: Mixed signals
        return 'sideways'

    def _score_rsi(self, metrics: Dict) -> float:
        """
        Score RSI (25 points max)

        RSI Interpretation:
        - 50-70: Bullish but not overbought (best) - 25 pts
        - 40-50: Neutral to slightly bullish - 18 pts
        - 30-40: Oversold (potential bounce) - 15 pts
        - 70-80: Overbought (still okay) - 12 pts
        - >80: Very overbought (caution) - 8 pts
        - <30: Very oversold (risky) - 10 pts
        """
        rsi = metrics.get('rsi')
        if rsi is None:
            return 12.5  # Neutral score if no data

        if 50 <= rsi < 70:
            return 25  # Sweet spot - bullish momentum
        elif 40 <= rsi < 50:
            return 18  # Neutral to slightly bullish
        elif 70 <= rsi < 80:
            return 15  # Overbought but acceptable
        elif 30 <= rsi < 40:
            return 15  # Oversold - potential buying opportunity
        elif rsi >= 80:
            return 8   # Very overbought - caution
        elif rsi < 30:
            return 10  # Very oversold - risky
        else:
            return 12.5

    def _score_trend(self, metrics: Dict) -> float:
        """
        Score trend based on MA crossovers and price position (35 points max)

        Components:
        - Trend direction: 20 points
        - Price vs SMA20: 10 points
        - MACD: 5 points
        """
        score = 0.0

        # Trend direction scoring (20 points)
        trend = metrics.get('trend', 'unknown')
        if trend == 'strong_uptrend':
            score += 20
        elif trend == 'uptrend':
            score += 16
        elif trend == 'sideways':
            score += 10
        elif trend == 'downtrend':
            score += 5
        elif trend == 'strong_downtrend':
            score += 0

        # Price vs SMA20 (10 points)
        price_vs_sma20 = metrics.get('price_vs_sma20')
        if price_vs_sma20 is not None:
            if price_vs_sma20 > 5:
                score += 10  # Well above SMA20
            elif price_vs_sma20 > 0:
                score += 7   # Above SMA20
            elif price_vs_sma20 > -5:
                score += 4   # Slightly below SMA20
            else:
                score += 0   # Well below SMA20

        # MACD (5 points)
        macd = metrics.get('macd')
        macd_signal = metrics.get('macd_signal')
        if macd is not None and macd_signal is not None:
            if macd > macd_signal and macd > 0:
                score += 5  # Bullish crossover above zero
            elif macd > macd_signal:
                score += 3  # Bullish crossover
            elif macd < 0 and macd_signal < 0:
                score += 1  # Both negative

        return min(35, score)

    def _score_returns(self, metrics: Dict) -> float:
        """
        Score historical returns (30 points max)

        Weighted by timeframe:
        - 3-month return: 50% (15 points)
        - 6-month return: 30% (9 points)
        - 1-month return: 20% (6 points)
        """
        score = 0.0

        # 3-month return (15 points) - Most important
        ret_3m = metrics.get('3m_return')
        if ret_3m is not None:
            if ret_3m >= self.THRESHOLDS['return_excellent']:
                score += 15
            elif ret_3m >= self.THRESHOLDS['return_good']:
                score += 12
            elif ret_3m >= self.THRESHOLDS['return_fair']:
                score += 9
            elif ret_3m > 0:
                score += 6
            elif ret_3m > -5:
                score += 3
            else:
                score += 0  # Significant loss

        # 6-month return (9 points)
        ret_6m = metrics.get('6m_return')
        if ret_6m is not None:
            if ret_6m >= 20:
                score += 9
            elif ret_6m >= 15:
                score += 7
            elif ret_6m >= 10:
                score += 5
            elif ret_6m > 0:
                score += 3

        # 1-month return (6 points) - Recent momentum
        ret_1m = metrics.get('1m_return')
        if ret_1m is not None:
            if ret_1m >= 10:
                score += 6
            elif ret_1m >= 5:
                score += 5
            elif ret_1m > 0:
                score += 3
            elif ret_1m > -5:
                score += 1

        return min(30, score)

    def _score_relative_strength(self, metrics: Dict) -> float:
        """
        Score relative strength vs NIFTY50 (10 points max)

        Outperformance vs market index is a strong signal
        """
        rel_strength = metrics.get('relative_strength')

        if rel_strength is None:
            return 5  # Neutral if no data

        if rel_strength > 15:
            return 10  # Strong outperformance
        elif rel_strength > 10:
            return 8
        elif rel_strength > 5:
            return 7
        elif rel_strength > 0:
            return 6   # Slight outperformance
        elif rel_strength > -5:
            return 4   # Slight underperformance
        elif rel_strength > -10:
            return 2
        else:
            return 0   # Strong underperformance

    def _calculate_confidence(
        self,
        price_data: pd.DataFrame,
        nifty_data: Optional[pd.DataFrame],
        technical_data: Dict
    ) -> float:
        """
        Calculate confidence level (0-1)

        Technical data is generally reliable, so base confidence is high
        """
        confidence = 0.8  # Base confidence

        # Has long-term data (>200 days)
        if len(price_data) >= 200:
            confidence += 0.1

        # Has NIFTY benchmark for relative strength
        if nifty_data is not None and not nifty_data.empty:
            confidence += 0.05

        # Has key technical indicators
        key_indicators = ['rsi', 'sma_20', 'sma_50', 'macd']
        available = sum(1 for ind in key_indicators if technical_data.get(ind) is not None)
        if available == len(key_indicators):
            confidence += 0.05

        return min(1.0, confidence)

    def _generate_reasoning(self, metrics: Dict, breakdown: Dict) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        # RSI
        rsi = metrics.get('rsi')
        if rsi is not None:
            if 50 <= rsi < 70:
                reasons.append(f"Strong RSI: {rsi:.1f}")
            elif rsi >= 70:
                reasons.append(f"Overbought RSI: {rsi:.1f}")
            elif rsi <= 30:
                reasons.append(f"Oversold RSI: {rsi:.1f}")

        # Trend
        trend = metrics.get('trend')
        if trend == 'strong_uptrend':
            reasons.append("Strong uptrend")
        elif trend == 'uptrend':
            reasons.append("Uptrend")
        elif trend == 'downtrend' or trend == 'strong_downtrend':
            reasons.append(f"Downtrend")

        # 3-month return
        ret_3m = metrics.get('3m_return')
        if ret_3m is not None:
            if ret_3m >= 15:
                reasons.append(f"Excellent 3M return: {ret_3m:+.1f}%")
            elif ret_3m >= 10:
                reasons.append(f"Strong 3M return: {ret_3m:+.1f}%")
            elif ret_3m < -5:
                reasons.append(f"Weak 3M return: {ret_3m:+.1f}%")

        # Relative strength
        rel_str = metrics.get('relative_strength')
        if rel_str is not None:
            if rel_str > 10:
                reasons.append(f"Outperforming NIFTY: +{rel_str:.1f}%")
            elif rel_str < -10:
                reasons.append(f"Underperforming NIFTY: {rel_str:.1f}%")

        if not reasons:
            reasons.append("Limited momentum data")

        return " | ".join(reasons)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = MomentumAgent()

    # Create sample price data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq='D')
    sample_prices = pd.DataFrame({
        'Close': np.random.randn(300).cumsum() + 100,
        'Open': np.random.randn(300).cumsum() + 100,
        'High': np.random.randn(300).cumsum() + 102,
        'Low': np.random.randn(300).cumsum() + 98,
        'Volume': np.random.randint(1000000, 10000000, 300)
    }, index=dates)

    # Sample technical data
    sample_technical = {
        'rsi': 58.5,
        'sma_20': 98.5,
        'sma_50': 96.2,
        'sma_200': 94.0,
        'macd': 1.2,
        'macd_signal': 0.8
    }

    sample_cached = {'technical_data': sample_technical}

    result = agent.analyze("TCS", sample_prices, None, sample_cached)

    print(f"\n{'='*60}")
    print(f"Momentum Analysis for TCS")
    print('='*60)
    print(f"Score: {result['score']}/100")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"\nBreakdown:")
    for key, value in result['breakdown'].items():
        print(f"  {key}: {value}")
    print(f"\nKey Metrics:")
    for key, value in result['metrics'].items():
        if value is not None and isinstance(value, (int, float)):
            print(f"  {key}: {value:.2f}")
        elif isinstance(value, str):
            print(f"  {key}: {value}")
