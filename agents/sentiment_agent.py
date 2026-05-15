"""
Sentiment Agent - Market Sentiment & Analyst Outlook (9% weight)

Analyzes:
- Analyst Recommendations (from yfinance)
- Target Price vs Current Price (upside potential)
- Number of Analysts (coverage indicates institutional interest)
- News Sentiment (Yahoo Finance RSS — free, no API key required)

Scoring: 0-100 with confidence level
"""

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

from utils.metric_extraction import MetricExtractor
from core.exceptions import DataValidationException, InsufficientDataException, CalculationException
from data.news_sentiment_provider import get_news_sentiment, score_to_adjustment

logger = logging.getLogger(__name__)


class SentimentAgent:
    """
    Sentiment Agent for Indian stock market

    Focuses on analyst sentiment and target prices.
    Indian stocks often have limited analyst coverage compared to US stocks.

    Scoring breakdown (0-100):
    - Analyst Recommendation: 55 points
    - Target Price Upside: 33 points
    - Analyst Coverage: 12 points
    Total: 100 points

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

    def __init__(self, enable_news_sentiment: bool = True):
        """
        Initialize Sentiment Agent

        Args:
            enable_news_sentiment: Enable Yahoo RSS news sentiment (default: True, free)
        """
        self.agent_name = "SentimentAgent"
        self.weight = 0.09  # 9% of total score
        self.enable_news_sentiment = enable_news_sentiment

    def analyze(self, symbol: str, cached_data: Optional[Dict] = None, market_regime: Optional[str] = None) -> Dict:
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
                logger.info(f"No analyst data for {symbol} — excluding from composite")
                return {
                    'score': None,
                    'confidence': 0.0,
                    'status': 'no_data',
                    'reasoning': 'No analyst data available for Indian stock',
                    'metrics': {},
                    'breakdown': {},
                    'agent': self.agent_name
                }

            # Extract metrics (handles None fields gracefully)
            metrics = self._extract_metrics(symbol, info)

            # Thin coverage guard: < 3 analysts means recommendation_mean is unreliable
            # (one analyst's view shouldn't anchor the composite score).
            # Return score=None so the composite re-normalizes weights rather than being
            # pulled toward a statistically noisy signal. Same pattern as QualityAgent.
            num_analysts = metrics.get('number_of_analyst_opinions') or 0
            if num_analysts < 3 and metrics.get('recommendation_mean') is not None:
                logger.info(
                    f"Thin analyst coverage for {symbol} ({num_analysts} analysts) — "
                    f"excluding recommendation from composite"
                )
                return {
                    'score': None,
                    'confidence': 0.0,
                    'status': 'no_data',
                    'reasoning': f'Thin analyst coverage ({num_analysts} analysts, min 3 required)',
                    'metrics': metrics,
                    'breakdown': {},
                    'agent': self.agent_name
                }

            # Calculate component scores (AQR/FactSet standard breakdown):
            #   Revision diffusion (level + momentum): 50 pts  — replaces flat rating level
            #   Target price upside:                   30 pts
            #   Analyst coverage:                      20 pts
            diffusion_score = self._score_revision_diffusion(metrics)
            target_price_score = self._score_target_price(metrics)
            coverage_score = self._score_analyst_coverage(metrics)

            # News sentiment adjustment (Yahoo RSS — free, no API key)
            news_adjustment = 0.0
            news_data: Dict = {}
            if self.enable_news_sentiment:
                try:
                    news_data = get_news_sentiment(symbol)
                    news_adjustment = score_to_adjustment(
                        news_data.get('sentiment_score', 0.0),
                        max_adjustment=8.0
                    )
                    metrics['news_sentiment_score'] = news_data.get('sentiment_score')
                    metrics['news_headline_count'] = news_data.get('headline_count', 0)
                    metrics['news_bullish_count'] = news_data.get('bullish_count', 0)
                    metrics['news_bearish_count'] = news_data.get('bearish_count', 0)
                    logger.debug(
                        f"News sentiment for {symbol}: {news_data.get('sentiment_score', 0):+.2f} "
                        f"→ adjustment {news_adjustment:+.1f}"
                    )
                except Exception as _news_err:
                    logger.debug(f"News sentiment unavailable for {symbol}: {_news_err}")

            # Analyst revision momentum (±10 pts) — most predictive India signal.
            # Fetches yfinance rating change history (last 60 days), nets upgrades vs downgrades.
            # Only fires when ≥2 rating changes exist to avoid single-firm noise.
            revision_data = self._fetch_analyst_revisions(symbol)
            revision_adj = self._score_analyst_revisions(revision_data)
            metrics['analyst_upgrades_30d'] = revision_data.get('upgrades_30d', 0)
            metrics['analyst_downgrades_30d'] = revision_data.get('downgrades_30d', 0)
            metrics['analyst_net_revisions_30d'] = revision_data.get('net_revisions_30d', 0)
            if revision_adj != 0.0:
                logger.debug(
                    f"Analyst revisions for {symbol}: "
                    f"+{revision_data['upgrades_30d']}u/-{revision_data['downgrades_30d']}d "
                    f"→ {revision_adj:+.1f} pts"
                )

            # Calculate total score (clamped to 0–100)
            total_score = max(0.0, min(100.0,
                diffusion_score + target_price_score + coverage_score + news_adjustment + revision_adj
            ))

            # Calculate confidence
            confidence = self._calculate_confidence(metrics)

            # Generate reasoning
            reasoning = self._generate_reasoning(metrics, {
                'diffusion': diffusion_score,
                'target_price': target_price_score,
                'coverage': coverage_score,
                'news': news_adjustment,
                'revisions': revision_adj,
            })

            return {
                'score': round(total_score, 2),
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'metrics': metrics,
                'breakdown': {
                    'diffusion_score': round(diffusion_score, 2),
                    'target_price_score': round(target_price_score, 2),
                    'coverage_score': round(coverage_score, 2),
                    'news_adjustment': round(news_adjustment, 2),
                    'revision_adjustment': round(revision_adj, 2),
                },
                'status': 'success',
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
                'status': 'error',
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
                'status': 'error',
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
                'status': 'error',
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
                'status': 'error',
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
        Score analyst recommendations (0-55 points)

        Lower recommendation mean = more bullish
        """
        rec_mean = metrics.get('recommendation_mean')

        if rec_mean is None:
            return 0

        if rec_mean < self.RECOMMENDATION_THRESHOLDS['strong_buy']:
            return 55  # Strong Buy consensus
        elif rec_mean < self.RECOMMENDATION_THRESHOLDS['buy']:
            return 44  # Buy consensus
        elif rec_mean < self.RECOMMENDATION_THRESHOLDS['hold']:
            return 28  # Hold consensus
        elif rec_mean < self.RECOMMENDATION_THRESHOLDS['sell']:
            return 11  # Sell leaning
        else:
            return 0   # Sell consensus

    def _score_revision_diffusion(self, metrics: Dict) -> float:
        """
        Analyst revision diffusion score (0–50 pts).
        AQR/FactSet primary sentiment signal: (upgrades − downgrades) / total + rate of change.
        Uses recommendationTrend periods [0M, -1M] from yfinance.

        Falls back to flat rating level when trend data is absent.
        """
        trend_data = metrics.get('recommendation_trend')
        if trend_data and len(trend_data) >= 2:
            def bull_minus_bear(period: Dict) -> float:
                bulls = period.get('strongBuy', 0) + period.get('buy', 0)
                bears = period.get('sell', 0) + period.get('strongSell', 0)
                total = bulls + bears + period.get('hold', 0)
                if total == 0:
                    return 0.0
                return (bulls - bears) / total   # -1 to +1

            current = trend_data[0]    # 0M (latest)
            prior = trend_data[1]      # -1M
            current_diffusion = bull_minus_bear(current)
            prior_diffusion = bull_minus_bear(prior)
            diffusion_change = current_diffusion - prior_diffusion

            # Level (50%) + momentum (50%) → 0–50 pts total
            level_score = (current_diffusion + 1) / 2 * 25       # -1..+1 → 0..25
            momentum_score = max(0.0, min(25.0, (diffusion_change + 0.5) * 25))
            return level_score + momentum_score

        # No trend data — fall back to flat recommendation mean (legacy signal)
        rec_mean = metrics.get('recommendation_mean')
        if rec_mean is None:
            return 0
        if rec_mean < self.RECOMMENDATION_THRESHOLDS['strong_buy']:
            return 50
        if rec_mean < self.RECOMMENDATION_THRESHOLDS['buy']:
            return 40
        if rec_mean < self.RECOMMENDATION_THRESHOLDS['hold']:
            return 25
        if rec_mean < self.RECOMMENDATION_THRESHOLDS['sell']:
            return 10
        return 0

    def _score_target_price(self, metrics: Dict) -> float:
        """Score target price upside (0–30 pts). Higher upside = more bullish."""
        upside = metrics.get('upside_percent')

        if upside is None:
            return 0

        if upside >= self.UPSIDE_THRESHOLDS['high']:
            return 30
        elif upside >= self.UPSIDE_THRESHOLDS['medium']:
            return 23
        elif upside >= self.UPSIDE_THRESHOLDS['low']:
            return 18
        elif upside > 0:
            return 15
        elif upside > -10:
            return 9
        else:
            return 0

    def _score_analyst_coverage(self, metrics: Dict) -> float:
        """Score analyst coverage (0–20 pts). More coverage = stronger signal quality."""
        num_analysts = metrics.get('number_of_analyst_opinions')

        if num_analysts is None:
            return 0

        # Calibrated for Indian market (lower analyst coverage than US)
        if num_analysts >= 20:
            return 20
        elif num_analysts >= 10:
            return 16
        elif num_analysts >= 5:
            return 11
        elif num_analysts >= 3:
            return 7
        elif num_analysts >= 1:
            return 4
        else:
            return 0

    def _fetch_analyst_revisions(self, symbol: str) -> Dict:
        """
        Fetch analyst rating change history from yfinance (last 60 days).
        Counts upgrades vs downgrades to compute net revision momentum.

        This is the highest-alpha signal in Indian equities per published research:
        net upgrades in the 30-day window before results predict 3M outperformance
        with ~60% hit rate (NSE Indices study 2019-2023).

        Returns:
          {
            'net_revisions_30d': int,   # upgrades - downgrades (positive = bullish)
            'upgrades_30d': int,
            'downgrades_30d': int,
            'revision_score': float,    # -1.0 to +1.0
          }
        """
        try:
            import yfinance as yf
            from datetime import date, timedelta
            ticker_sym = symbol if symbol.endswith('.NS') else f"{symbol}.NS"
            t = yf.Ticker(ticker_sym)
            recs = t.recommendations
            if recs is None or recs.empty:
                return {'net_revisions_30d': 0, 'upgrades_30d': 0, 'downgrades_30d': 0, 'revision_score': 0.0}

            # Filter to last 60 days
            cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=60)
            if recs.index.tz is None:
                recs.index = recs.index.tz_localize('UTC')
            recent = recs[recs.index >= cutoff]
            if recent.empty:
                return {'net_revisions_30d': 0, 'upgrades_30d': 0, 'downgrades_30d': 0, 'revision_score': 0.0}

            # Map grades to numeric scale (higher = more bullish)
            _GRADE_MAP = {
                'Strong Buy': 5, 'Buy': 4, 'Outperform': 4, 'Overweight': 4,
                'Hold': 3, 'Neutral': 3, 'Market Perform': 3, 'Equal-Weight': 3,
                'Underperform': 2, 'Underweight': 2,
                'Sell': 1, 'Strong Sell': 1,
            }

            upgrades = downgrades = 0
            for _, row in recent.iterrows():
                to_g = _GRADE_MAP.get(str(row.get('To Grade', '')).strip(), 0)
                from_g = _GRADE_MAP.get(str(row.get('From Grade', '')).strip(), 0)
                if to_g == 0 or from_g == 0:
                    continue
                if to_g > from_g:
                    upgrades += 1
                elif to_g < from_g:
                    downgrades += 1

            net = upgrades - downgrades
            total = upgrades + downgrades
            revision_score = (net / total) if total > 0 else 0.0

            return {
                'net_revisions_30d': net,
                'upgrades_30d': upgrades,
                'downgrades_30d': downgrades,
                'revision_score': round(revision_score, 3),
            }
        except Exception as e:
            logger.debug(f"Analyst revision fetch failed for {symbol}: {e}")
            return {'net_revisions_30d': 0, 'upgrades_30d': 0, 'downgrades_30d': 0, 'revision_score': 0.0}

    def _score_analyst_revisions(self, revision_data: Dict) -> float:
        """
        Convert analyst revision momentum into a score adjustment (±10 pts).
        Positive = net upgrades (bullish drift signal), negative = net downgrades.
        Only fires when there are ≥2 rating changes (avoids single-firm noise).
        """
        net = revision_data.get('net_revisions_30d', 0)
        total = revision_data.get('upgrades_30d', 0) + revision_data.get('downgrades_30d', 0)
        if total < 2:
            return 0.0   # Not enough signal
        score = revision_data.get('revision_score', 0.0)  # -1 to +1
        return round(float(np.clip(score * 10.0, -10.0, 10.0)), 2)

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
        num_analysts = metrics.get('number_of_analyst_opinions') or 0
        if num_analysts >= 5:
            confidence += 0.2
        elif num_analysts >= 3:
            confidence += 0.1
        elif num_analysts >= 1:
            confidence += 0.05

        return min(1.0, confidence)

    def _generate_reasoning(self, metrics: Dict, breakdown: Dict) -> str:
        reasons = []

        # Revision diffusion
        diffusion_score = breakdown.get('diffusion', 0)
        trend_data = metrics.get('recommendation_trend')
        if trend_data and len(trend_data) >= 2:
            reasons.append(f"Revision diffusion {diffusion_score:.0f}/50 pts")
        else:
            rec_mean = metrics.get('recommendation_mean')
            if rec_mean is not None:
                label = (
                    "Strong Buy" if rec_mean < 2.0 else
                    "Buy" if rec_mean < 2.5 else
                    "Hold" if rec_mean < 3.5 else "Sell"
                )
                reasons.append(f"{label} consensus ({rec_mean:.1f})")

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

        # News sentiment
        news_score = metrics.get('news_sentiment_score')
        headline_count = metrics.get('news_headline_count', 0)
        if news_score is not None and headline_count > 0:
            bull = metrics.get('news_bullish_count', 0)
            bear = metrics.get('news_bearish_count', 0)
            if news_score >= 0.2:
                reasons.append(f"Positive news flow ({bull}B/{bear}Be of {headline_count})")
            elif news_score <= -0.2:
                reasons.append(f"Negative news flow ({bull}B/{bear}Be of {headline_count})")
            else:
                reasons.append(f"Neutral news ({headline_count} headlines)")

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
                'recommendation_score': 28.0,
                'target_price_score': 17.0,
                'coverage_score': 5.0
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
