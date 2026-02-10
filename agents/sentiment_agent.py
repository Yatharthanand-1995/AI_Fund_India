"""
Sentiment Agent - Market Sentiment & Analyst Outlook (9% weight)

Analyzes:
- Analyst Recommendations (from yfinance)
- Target Price vs Current Price (upside potential)
- Number of Analysts (coverage indicates institutional interest)
- Optional: News Sentiment (LLM-powered, if enabled)

Scoring: 0-100 with confidence level
"""

import logging
from typing import Dict, Optional

from utils.metric_extraction import MetricExtractor
from core.exceptions import DataValidationException, InsufficientDataException, CalculationException

logger = logging.getLogger(__name__)


class SentimentAgent:
    """
    Sentiment Agent for Indian stock market

    Focuses on analyst sentiment and target prices.
    Indian stocks often have limited analyst coverage compared to US stocks.

    Scoring breakdown (0-100):
    - Analyst Recommendation: 50 points
    - Target Price Upside: 30 points
    - Analyst Coverage: 10 points
    - News Sentiment (optional): 10 points

    Base score: 50 (neutral)
    """

    # Analyst recommendation mapping (1-5 scale from yfinance)
    # 1.0 = Strong Buy, 2.0 = Buy, 3.0 = Hold, 4.0 = Sell, 5.0 = Strong Sell
    RECOMMENDATION_THRESHOLDS = {
        'strong_buy': 1.5,
        'buy': 2.5,
        'hold': 3.5,
        'sell': 4.5,
    }

    # Target price upside thresholds (%)
    UPSIDE_THRESHOLDS = {
        'high': 20,
        'medium': 10,
        'low': 5,
    }

    def __init__(self, enable_news_sentiment: bool = False):
        """
        Initialize Sentiment Agent

        Args:
            enable_news_sentiment: Enable LLM-powered news sentiment (default: False)
        """
        self.agent_name = "SentimentAgent"
        self.weight = 0.09  # 9% of total score
        self.enable_news_sentiment = enable_news_sentiment

    def analyze(self, symbol: str, cached_data: Optional[Dict] = None) -> Dict:
        """
        Analyze market sentiment and analyst outlook

        Args:
            symbol: Stock symbol
            cached_data: Pre-fetched comprehensive data (contains info)

        Returns:
            {
                'score': float (0-100),
                'confidence': float (0-1),
                'reasoning': str,
                'metrics': {
                    'recommendation_mean': float,
                    'target_price': float,
                    'current_price': float,
                    'upside_percent': float,
                    'analyst_count': int,
                    ...
                },
                'breakdown': {
                    'recommendation_score': float,
                    'target_price_score': float,
                    'coverage_score': float
                }
            }
        """
        logger.info(f"Analyzing sentiment for {symbol}")

        try:
            # Extract info
            info = cached_data.get('info', {}) if cached_data else {}

            # Check for actual sentiment keys rather than just empty info.
            # NSE provider info dict has price fields but no analyst data, so
            # we proceed with _extract_metrics which handles None gracefully.
            SENTIMENT_KEYS = [
                'recommendationMean', 'recommendationKey',
                'targetMeanPrice', 'numberOfAnalystOpinions'
            ]
            has_sentiment_data = any(info.get(k) is not None for k in SENTIMENT_KEYS)
            if not has_sentiment_data:
                logger.info(f"No analyst/sentiment data available for {symbol} - using neutral defaults")

            # Extract metrics (handles None fields gracefully)
            metrics = self._extract_metrics(symbol, info)

            # Calculate component scores
            recommendation_score = self._score_recommendation(metrics)
            target_price_score = self._score_target_price(metrics)
            coverage_score = self._score_analyst_coverage(metrics)

            # Calculate total score
            total_score = recommendation_score + target_price_score + coverage_score

            # Calculate confidence
            confidence = self._calculate_confidence(metrics)

            # Generate reasoning
            reasoning = self._generate_reasoning(metrics, {
                'recommendation': recommendation_score,
                'target_price': target_price_score,
                'coverage': coverage_score
            })

            return {
                'score': round(total_score, 2),
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'metrics': metrics,
                'breakdown': {
                    'recommendation_score': round(recommendation_score, 2),
                    'target_price_score': round(target_price_score, 2),
                    'coverage_score': round(coverage_score, 2)
                },
                'agent': self.agent_name
            }

        except DataValidationException as e:
            logger.warning(f"Data validation failed for {symbol}: {e}")
            return {
                'score': 50.0,
                'confidence': 0.1,
                'reasoning': f"Data validation failed: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e),
                'error_category': 'validation'
            }

        except InsufficientDataException as e:
            logger.info(f"Insufficient data for {symbol}: {e}")
            return {
                'score': 50.0,
                'confidence': 0.2,
                'reasoning': f"Insufficient data: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e),
                'error_category': 'insufficient_data'
            }

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Data format error for {symbol}: {e}")
            return {
                'score': 50.0,
                'confidence': 0.15,
                'reasoning': f"Data format error: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e),
                'error_category': 'data_format'
            }

        except Exception as e:
            logger.error(f"Unexpected error analyzing {symbol}: {e}", exc_info=True)
            return {
                'score': 50.0,
                'confidence': 0.1,
                'reasoning': f"Analysis failed: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e),
                'error_category': 'unknown'
            }

    def _extract_metrics(self, symbol: str, info: Dict) -> Dict:
        """Extract sentiment-related metrics"""
        metrics = {}

        # Analyst recommendation (1-5 scale)
        metrics['recommendation_mean'] = info.get('recommendationMean')
        metrics['recommendation_key'] = info.get('recommendationKey')

        # Target price
        metrics['target_mean_price'] = info.get('targetMeanPrice')
        metrics['target_high_price'] = info.get('targetHighPrice')
        metrics['target_low_price'] = info.get('targetLowPrice')
        metrics['current_price'] = info.get('currentPrice') or info.get('regularMarketPrice')

        # Calculate upside
        if metrics['target_mean_price'] and metrics['current_price']:
            metrics['upside_percent'] = (
                (metrics['target_mean_price'] - metrics['current_price']) /
                metrics['current_price'] * 100
            )
        else:
            metrics['upside_percent'] = None

        # Analyst coverage
        metrics['number_of_analyst_opinions'] = info.get('numberOfAnalystOpinions')

        # Additional sentiment indicators
        metrics['recommendation_trend'] = info.get('recommendationTrend')  # Not always available

        logger.debug(f"Extracted {len([v for v in metrics.values() if v is not None])} sentiment metrics")
        return metrics

    def _score_recommendation(self, metrics: Dict) -> float:
        """
        Score analyst recommendations (0-50 points)

        Lower recommendation mean = more bullish
        """
        rec_mean = metrics.get('recommendation_mean')

        if rec_mean is None:
            return 25  # Neutral if no data

        if rec_mean < self.RECOMMENDATION_THRESHOLDS['strong_buy']:
            return 50  # Strong Buy consensus
        elif rec_mean < self.RECOMMENDATION_THRESHOLDS['buy']:
            return 40  # Buy consensus
        elif rec_mean < self.RECOMMENDATION_THRESHOLDS['hold']:
            return 25  # Hold consensus
        elif rec_mean < self.RECOMMENDATION_THRESHOLDS['sell']:
            return 10  # Sell leaning
        else:
            return 0   # Sell consensus

    def _score_target_price(self, metrics: Dict) -> float:
        """
        Score target price upside (0-30 points)

        Higher upside = more bullish
        """
        upside = metrics.get('upside_percent')

        if upside is None:
            return 15  # Neutral if no data

        if upside >= self.UPSIDE_THRESHOLDS['high']:
            return 30  # High upside potential
        elif upside >= self.UPSIDE_THRESHOLDS['medium']:
            return 23  # Medium upside
        elif upside >= self.UPSIDE_THRESHOLDS['low']:
            return 18  # Low upside
        elif upside > 0:
            return 15  # Slight upside
        elif upside > -10:
            return 10  # Slight downside
        else:
            return 0   # Significant downside

    def _score_analyst_coverage(self, metrics: Dict) -> float:
        """
        Score analyst coverage (0-10 points)

        More coverage = more institutional interest = better
        Note: Indian stocks typically have less coverage than US stocks
        """
        num_analysts = metrics.get('number_of_analyst_opinions')

        if num_analysts is None:
            return 3  # Low score if no data

        # Adjusted for Indian market (lower coverage)
        if num_analysts >= 20:
            return 10  # Excellent coverage
        elif num_analysts >= 10:
            return 8   # Good coverage
        elif num_analysts >= 5:
            return 6   # Moderate coverage
        elif num_analysts >= 3:
            return 4   # Limited coverage
        elif num_analysts >= 1:
            return 2   # Very limited
        else:
            return 0   # No coverage

    def _calculate_confidence(self, metrics: Dict) -> float:
        """
        Calculate confidence level (0-1)

        Factors:
        - Has recommendation: +0.3
        - Has target price: +0.3
        - Has multiple analysts: +0.2
        - Recent data: +0.2 (if recommendation_trend available)
        """
        confidence = 0.3  # Base confidence

        # Has recommendation
        if metrics.get('recommendation_mean') is not None:
            confidence += 0.3

        # Has target price
        if metrics.get('target_mean_price') is not None:
            confidence += 0.2

        # Has analyst coverage
        num_analysts = metrics.get('number_of_analyst_opinions', 0)
        if num_analysts >= 5:
            confidence += 0.2
        elif num_analysts >= 3:
            confidence += 0.1
        elif num_analysts >= 1:
            confidence += 0.05

        return min(1.0, confidence)

    def _generate_reasoning(self, metrics: Dict, breakdown: Dict) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        # Recommendation
        rec_mean = metrics.get('recommendation_mean')
        if rec_mean is not None:
            if rec_mean < 2.0:
                reasons.append(f"Strong Buy consensus ({rec_mean:.1f})")
            elif rec_mean < 2.5:
                reasons.append(f"Buy consensus ({rec_mean:.1f})")
            elif rec_mean < 3.5:
                reasons.append(f"Hold consensus ({rec_mean:.1f})")
            else:
                reasons.append(f"Sell leaning ({rec_mean:.1f})")

        # Target price upside
        upside = metrics.get('upside_percent')
        if upside is not None:
            if upside >= 20:
                reasons.append(f"High upside: {upside:+.1f}%")
            elif upside >= 10:
                reasons.append(f"Medium upside: {upside:+.1f}%")
            elif upside < -10:
                reasons.append(f"Downside risk: {upside:+.1f}%")

        # Analyst coverage
        num_analysts = metrics.get('number_of_analyst_opinions')
        if num_analysts is not None:
            if num_analysts >= 10:
                reasons.append(f"{num_analysts} analysts covering")
            elif num_analysts < 3:
                reasons.append(f"Limited coverage ({num_analysts} analysts)")

        if not reasons:
            reasons.append("Limited analyst data")

        return " | ".join(reasons)

    def _neutral_result(self, reason: str) -> Dict:
        """Return neutral result when data is unavailable"""
        return {
            'score': 50.0,
            'confidence': 0.2,
            'reasoning': reason,
            'metrics': {},
            'breakdown': {
                'recommendation_score': 25.0,
                'target_price_score': 15.0,
                'coverage_score': 3.0
            },
            'agent': self.agent_name
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = SentimentAgent()

    # Sample data
    sample_info = {
        'recommendationMean': 2.1,  # Buy consensus
        'targetMeanPrice': 3500,
        'currentPrice': 3200,
        'numberOfAnalystOpinions': 15
    }

    sample_cached = {'info': sample_info}

    result = agent.analyze("TCS", sample_cached)

    print(f"\n{'='*60}")
    print(f"Sentiment Analysis")
    print('='*60)
    print(f"Score: {result['score']}/100")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"\nBreakdown:")
    for key, value in result['breakdown'].items():
        print(f"  {key}: {value}")
    print(f"\nMetrics:")
    for key, value in result['metrics'].items():
        if value is not None:
            print(f"  {key}: {value}")
