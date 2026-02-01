"""
Stock Scorer - Orchestrates all 5 AI agents and calculates composite score

This is the main orchestration layer that:
1. Initializes all 5 agents
2. Fetches comprehensive data (once)
3. Runs all agents with shared data
4. Applies weights (static or adaptive)
5. Calculates composite score
6. Determines recommendation (STRONG BUY, BUY, HOLD, SELL)
7. Returns comprehensive analysis
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
import pandas as pd

from agents.fundamentals_agent import FundamentalsAgent
from agents.momentum_agent import MomentumAgent
from agents.quality_agent import QualityAgent
from agents.sentiment_agent import SentimentAgent
from agents.institutional_flow_agent import InstitutionalFlowAgent
from data.hybrid_provider import HybridDataProvider
from core.market_regime_service import MarketRegimeService

logger = logging.getLogger(__name__)


class StockScorer:
    """
    Stock Scorer - Orchestrates all 5 agents to score stocks

    Manages:
    - Agent initialization
    - Data fetching and sharing
    - Score aggregation
    - Recommendation determination

    Default weights:
    - Fundamentals: 36%
    - Momentum: 27%
    - Quality: 18%
    - Sentiment: 9%
    - Institutional Flow: 10%
    """

    # Static weights (default)
    STATIC_WEIGHTS = {
        'fundamentals': 0.36,
        'momentum': 0.27,
        'quality': 0.18,
        'sentiment': 0.09,
        'institutional_flow': 0.10
    }

    # Recommendation thresholds
    # More conservative thresholds to avoid too many buy signals
    RECOMMENDATION_THRESHOLDS = {
        'STRONG BUY': 80,  # Top tier stocks (>= 80)
        'BUY': 68,         # Strong stocks (68-79)
        'WEAK BUY': 58,    # Above average (58-67)
        'HOLD_HIGH': 57,   # Neutral zone (45-57)
        'HOLD_LOW': 45,    # Neutral zone (45-57)
        'WEAK SELL': 35,   # Below average (35-44)
        'SELL': 0          # Avoid (< 35)
    }

    def __init__(
        self,
        data_provider: Optional[HybridDataProvider] = None,
        use_adaptive_weights: bool = False,
        sector_mapping: Optional[Dict] = None
    ):
        """
        Initialize Stock Scorer

        Args:
            data_provider: Data provider instance (creates new if None)
            use_adaptive_weights: Use adaptive weights based on market regime
            sector_mapping: Mapping of symbols to sectors
        """
        logger.info("Initializing Stock Scorer with 5 agents")

        # Initialize data provider
        self.data_provider = data_provider or HybridDataProvider()

        # Initialize all 5 agents
        self.fundamentals_agent = FundamentalsAgent()
        self.momentum_agent = MomentumAgent()
        self.quality_agent = QualityAgent(sector_mapping=sector_mapping)
        self.sentiment_agent = SentimentAgent()
        self.institutional_flow_agent = InstitutionalFlowAgent()

        # Configuration
        self.use_adaptive_weights = use_adaptive_weights
        self.sector_mapping = sector_mapping or {}

        # Initialize market regime service for adaptive weights
        self.market_regime_service = MarketRegimeService() if use_adaptive_weights else None

        # Current weights (will be set to static or adaptive)
        self.current_weights = self.STATIC_WEIGHTS.copy()

        # Stats tracking
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_score': 0.0,
            'recommendations': {
                'STRONG BUY': 0,
                'BUY': 0,
                'WEAK BUY': 0,
                'HOLD': 0,
                'WEAK SELL': 0,
                'SELL': 0
            }
        }

        logger.info(f"Stock Scorer initialized (adaptive_weights: {use_adaptive_weights})")

    def score_stock(self, symbol: str, nifty_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Score a single stock using all 5 agents

        Args:
            symbol: Stock symbol (e.g., "TCS")
            nifty_data: NIFTY50 data for relative strength (optional, will fetch if None)

        Returns:
            {
                'symbol': str,
                'composite_score': float (0-100),
                'composite_confidence': float (0-1),
                'recommendation': str,
                'agent_scores': {
                    'fundamentals': {...},
                    'momentum': {...},
                    'quality': {...},
                    'sentiment': {...},
                    'institutional_flow': {...}
                },
                'weights_used': dict,
                'timestamp': str,
                'analysis_time_seconds': float
            }
        """
        self.stats['total_analyses'] += 1
        start_time = datetime.now()

        logger.info(f"{'='*60}")
        logger.info(f"Scoring stock: {symbol}")
        logger.info(f"{'='*60}")

        try:
            # Step 1: Get current weights (adaptive or static)
            weights = self._get_current_weights()
            logger.info(f"Using weights: {weights}")

            # Step 2: Fetch comprehensive data (once for all agents)
            logger.info(f"Fetching comprehensive data for {symbol}...")
            cached_data = self.data_provider.get_comprehensive_data(symbol)

            if cached_data.get('error'):
                raise ValueError(f"Data fetch failed: {cached_data.get('error')}")

            price_data = cached_data.get('historical_data')
            if price_data is None or price_data.empty:
                raise ValueError("No historical price data available")

            # Step 3: Fetch NIFTY50 data if needed and not provided
            if nifty_data is None or nifty_data.empty:
                logger.info("Fetching NIFTY50 data for relative strength...")
                try:
                    nifty_cached = self.data_provider.get_comprehensive_data('^NSEI')
                    nifty_data = nifty_cached.get('historical_data', pd.DataFrame())
                except Exception as e:
                    logger.warning(f"Could not fetch NIFTY data: {e}")
                    nifty_data = pd.DataFrame()

            # Step 4: Run all 5 agents
            logger.info("Running all 5 agents...")

            # Fundamentals Agent
            logger.info("  → Running Fundamentals Agent (36%)")
            fundamentals_result = self.fundamentals_agent.analyze(symbol, cached_data)

            # Momentum Agent
            logger.info("  → Running Momentum Agent (27%)")
            momentum_result = self.momentum_agent.analyze(
                symbol, price_data, nifty_data, cached_data
            )

            # Quality Agent
            logger.info("  → Running Quality Agent (18%)")
            quality_result = self.quality_agent.analyze(symbol, price_data, cached_data)

            # Sentiment Agent
            logger.info("  → Running Sentiment Agent (9%)")
            sentiment_result = self.sentiment_agent.analyze(symbol, cached_data)

            # Institutional Flow Agent
            logger.info("  → Running Institutional Flow Agent (10%)")
            flow_result = self.institutional_flow_agent.analyze(symbol, price_data, cached_data)

            # Step 5: Calculate composite score
            logger.info("Calculating composite score...")
            composite_score, composite_confidence = self._calculate_composite_score(
                fundamentals_result,
                momentum_result,
                quality_result,
                sentiment_result,
                flow_result,
                weights
            )

            # Step 6: Determine recommendation
            recommendation = self._get_recommendation(composite_score, composite_confidence)

            # Step 7: Calculate analysis time
            analysis_time = (datetime.now() - start_time).total_seconds()

            # Step 8: Assemble complete result
            result = {
                'symbol': symbol,
                'composite_score': round(composite_score, 2),
                'composite_confidence': round(composite_confidence, 2),
                'recommendation': recommendation,
                'agent_scores': {
                    'fundamentals': fundamentals_result,
                    'momentum': momentum_result,
                    'quality': quality_result,
                    'sentiment': sentiment_result,
                    'institutional_flow': flow_result
                },
                'weights_used': weights,
                'current_price': cached_data.get('current_price'),
                'price_change_percent': cached_data.get('price_change_percent'),
                'market_cap': cached_data.get('market_cap'),
                'sector': cached_data.get('sector'),
                'company_name': cached_data.get('company_name'),
                'timestamp': datetime.now().isoformat(),
                'analysis_time_seconds': round(analysis_time, 2),
                'data_provider': cached_data.get('provider')
            }

            # Update stats
            self.stats['successful_analyses'] += 1
            self.stats['recommendations'][recommendation] += 1
            self._update_average_score(composite_score)

            logger.info(f"✅ Analysis complete: {recommendation} ({composite_score:.1f}/100)")
            logger.info(f"   Analysis time: {analysis_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Failed to score {symbol}: {e}", exc_info=True)
            self.stats['failed_analyses'] += 1

            return {
                'symbol': symbol,
                'composite_score': 50.0,
                'composite_confidence': 0.0,
                'recommendation': 'ERROR',
                'error': str(e),
                'agent_scores': {},
                'weights_used': weights if 'weights' in locals() else self.STATIC_WEIGHTS,
                'timestamp': datetime.now().isoformat(),
                'analysis_time_seconds': (datetime.now() - start_time).total_seconds()
            }

    def score_stocks_batch(self, symbols: List[str]) -> List[Dict]:
        """
        Score multiple stocks in batch

        Args:
            symbols: List of stock symbols

        Returns:
            List of analysis results, sorted by composite score (descending)
        """
        logger.info(f"Batch scoring {len(symbols)} stocks...")
        results = []

        # Fetch NIFTY data once for all stocks
        try:
            nifty_cached = self.data_provider.get_comprehensive_data('^NSEI')
            nifty_data = nifty_cached.get('historical_data', pd.DataFrame())
        except Exception as e:
            logger.warning(f"Could not fetch NIFTY data: {e}")
            nifty_data = pd.DataFrame()

        # Score each stock
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\nProgress: {i}/{len(symbols)} - {symbol}")
            try:
                result = self.score_stock(symbol, nifty_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to score {symbol}: {e}")
                results.append({
                    'symbol': symbol,
                    'composite_score': 0.0,
                    'error': str(e)
                })

        # Sort by composite score (descending)
        results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

        logger.info(f"\n✅ Batch analysis complete: {len(results)} stocks scored")
        return results

    def _calculate_composite_score(
        self,
        fundamentals_result: Dict,
        momentum_result: Dict,
        quality_result: Dict,
        sentiment_result: Dict,
        flow_result: Dict,
        weights: Dict
    ) -> tuple[float, float]:
        """
        Calculate weighted composite score and confidence

        Returns:
            (composite_score, composite_confidence)
        """
        # Extract scores
        fund_score = fundamentals_result.get('score', 50.0)
        mom_score = momentum_result.get('score', 50.0)
        qual_score = quality_result.get('score', 50.0)
        sent_score = sentiment_result.get('score', 50.0)
        flow_score = flow_result.get('score', 50.0)

        # Extract confidence levels
        fund_conf = fundamentals_result.get('confidence', 0.5)
        mom_conf = momentum_result.get('confidence', 0.5)
        qual_conf = quality_result.get('confidence', 0.5)
        sent_conf = sentiment_result.get('confidence', 0.5)
        flow_conf = flow_result.get('confidence', 0.5)

        # Calculate weighted composite score
        composite_score = (
            weights['fundamentals'] * fund_score +
            weights['momentum'] * mom_score +
            weights['quality'] * qual_score +
            weights['sentiment'] * sent_score +
            weights['institutional_flow'] * flow_score
        )

        # Calculate weighted composite confidence
        composite_confidence = (
            weights['fundamentals'] * fund_conf +
            weights['momentum'] * mom_conf +
            weights['quality'] * qual_conf +
            weights['sentiment'] * sent_conf +
            weights['institutional_flow'] * flow_conf
        )

        logger.info(f"  Composite Score: {composite_score:.2f}/100")
        logger.info(f"  Composite Confidence: {composite_confidence:.2%}")

        return composite_score, composite_confidence

    def _get_recommendation(self, score: float, confidence: float) -> str:
        """
        Determine recommendation based on score and confidence

        Args:
            score: Composite score (0-100)
            confidence: Composite confidence (0-1)

        Returns:
            Recommendation string
        """
        # Adjust thresholds based on confidence
        # Lower confidence = more conservative recommendations
        confidence_factor = max(0.5, confidence)  # Minimum 0.5

        if score >= self.RECOMMENDATION_THRESHOLDS['STRONG BUY'] * confidence_factor:
            return 'STRONG BUY'
        elif score >= self.RECOMMENDATION_THRESHOLDS['BUY'] * confidence_factor:
            return 'BUY'
        elif score >= self.RECOMMENDATION_THRESHOLDS['WEAK BUY']:
            return 'WEAK BUY'
        elif score >= self.RECOMMENDATION_THRESHOLDS['HOLD_LOW']:
            return 'HOLD'
        elif score >= self.RECOMMENDATION_THRESHOLDS['WEAK SELL']:
            return 'WEAK SELL'
        else:
            return 'SELL'

    def _get_current_weights(self) -> Dict:
        """
        Get current weights (static or adaptive)

        Returns:
            Dict of agent weights
        """
        if self.use_adaptive_weights and self.market_regime_service:
            try:
                # Get current market regime
                regime_info = self.market_regime_service.get_current_regime(
                    data_provider=self.data_provider
                )
                weights = regime_info['weights']
                logger.info(f"Using adaptive weights for regime: {regime_info['regime']}")
                return weights
            except Exception as e:
                logger.warning(f"Failed to get adaptive weights, using static: {e}")
                return self.STATIC_WEIGHTS.copy()
        else:
            return self.STATIC_WEIGHTS.copy()

    def set_weights(self, weights: Dict):
        """
        Manually set custom weights

        Args:
            weights: Dict with keys matching agent names
        """
        # Validate weights sum to 1.0
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.current_weights = weights
        logger.info(f"Custom weights set: {weights}")

    def _update_average_score(self, new_score: float):
        """Update running average score"""
        current_avg = self.stats['average_score']
        successful = self.stats['successful_analyses']

        if successful == 1:
            self.stats['average_score'] = new_score
        else:
            # Running average
            self.stats['average_score'] = (
                (current_avg * (successful - 1) + new_score) / successful
            )

    def get_stats(self) -> Dict:
        """Get scorer statistics"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_analyses'] / self.stats['total_analyses'] * 100
                if self.stats['total_analyses'] > 0 else 0
            )
        }

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_score': 0.0,
            'recommendations': {k: 0 for k in self.stats['recommendations'].keys()}
        }
        logger.info("Statistics reset")

    def get_market_regime(self) -> Dict:
        """
        Get current market regime information

        Returns:
            Dict with regime, trend, volatility, and adaptive weights
        """
        if self.market_regime_service:
            return self.market_regime_service.get_current_regime(
                data_provider=self.data_provider
            )
        else:
            return {
                'regime': 'STATIC',
                'trend': 'N/A',
                'volatility': 'N/A',
                'weights': self.STATIC_WEIGHTS,
                'message': 'Adaptive weights not enabled'
            }


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize scorer
    scorer = StockScorer()

    # Test with a single stock
    print("\n" + "="*60)
    print("Testing Stock Scorer with TCS")
    print("="*60)

    result = scorer.score_stock("TCS")

    # Display results
    print(f"\n{'='*60}")
    print(f"Analysis Results for {result['symbol']}")
    print('='*60)
    print(f"Composite Score: {result['composite_score']}/100")
    print(f"Confidence: {result['composite_confidence']:.0%}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Analysis Time: {result['analysis_time_seconds']}s")

    print(f"\n{'Agent Scores':-^60}")
    for agent_name, agent_result in result['agent_scores'].items():
        score = agent_result.get('score', 'N/A')
        conf = agent_result.get('confidence', 0)
        reasoning = agent_result.get('reasoning', 'N/A')
        print(f"\n{agent_name.upper()}: {score}/100 (conf: {conf:.0%})")
        print(f"  {reasoning}")

    print(f"\n{'Weights Used':-^60}")
    for agent, weight in result['weights_used'].items():
        print(f"  {agent}: {weight:.0%}")

    # Test batch scoring
    print("\n\n" + "="*60)
    print("Testing Batch Scoring")
    print("="*60)

    test_symbols = ["TCS", "INFY", "RELIANCE"]
    batch_results = scorer.score_stocks_batch(test_symbols)

    print(f"\n{'Top Stocks':-^60}")
    for i, res in enumerate(batch_results[:5], 1):
        print(f"{i}. {res['symbol']}: {res['composite_score']:.1f}/100 - {res.get('recommendation', 'N/A')}")

    # Print stats
    print(f"\n{'Scorer Statistics':-^60}")
    stats = scorer.get_stats()
    print(f"Total Analyses: {stats['total_analyses']}")
    print(f"Success Rate: {stats['success_rate']:.1f}%")
    print(f"Average Score: {stats['average_score']:.1f}")
    print(f"\nRecommendation Distribution:")
    for rec, count in stats['recommendations'].items():
        if count > 0:
            print(f"  {rec}: {count}")
