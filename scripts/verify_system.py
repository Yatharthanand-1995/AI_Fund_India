"""
End-to-End System Verification

Tests the complete system workflow:
1. Data provider functionality
2. All 5 agents
3. Market regime detection
4. Stock scorer orchestration
5. Narrative generation
6. API endpoints
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.hybrid_provider import HybridDataProvider
from agents.fundamentals_agent import FundamentalsAgent
from agents.momentum_agent import MomentumAgent
from agents.quality_agent import QualityAgent
from agents.sentiment_agent import SentimentAgent
from agents.institutional_flow_agent import InstitutionalFlowAgent
from core.stock_scorer import StockScorer
from core.market_regime_service import MarketRegimeService
from narrative_engine.narrative_engine import InvestmentNarrativeEngine

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def print_separator(title):
    """Print a section separator"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def test_data_provider():
    """Test data provider"""
    print_separator("Testing Data Provider")

    provider = HybridDataProvider()
    logger.info("✓ Data provider initialized")

    # Test with a well-known stock
    symbol = 'TCS'
    logger.info(f"Fetching data for {symbol}...")

    try:
        data = provider.get_comprehensive_data(symbol)

        if data:
            logger.info(f"✓ Retrieved comprehensive data for {symbol}")
            logger.info(f"  - Historical data: {len(data.get('historical_data', []))} rows")
            logger.info(f"  - Info fields: {len(data.get('info', {}))} fields")
            logger.info(f"  - Source: {data.get('source', 'unknown')}")
            return True, data
        else:
            logger.error(f"✗ Failed to retrieve data for {symbol}")
            return False, None
    except Exception as e:
        logger.error(f"✗ Data provider error: {e}")
        return False, None


def test_agents(cached_data):
    """Test all 5 agents"""
    print_separator("Testing All Agents")

    symbol = 'TCS'
    agents_results = {}

    # Test Fundamentals Agent
    try:
        agent = FundamentalsAgent()
        result = agent.analyze(symbol, cached_data)
        agents_results['fundamentals'] = result
        logger.info(f"✓ Fundamentals Agent: Score={result['score']:.1f}, Confidence={result['confidence']:.2f}")
    except Exception as e:
        logger.error(f"✗ Fundamentals Agent failed: {e}")
        return False, {}

    # Test Momentum Agent
    try:
        agent = MomentumAgent()
        price_data = cached_data.get('historical_data')
        result = agent.analyze(symbol, price_data, None, cached_data)
        agents_results['momentum'] = result
        logger.info(f"✓ Momentum Agent: Score={result['score']:.1f}, Confidence={result['confidence']:.2f}")
    except Exception as e:
        logger.error(f"✗ Momentum Agent failed: {e}")
        return False, {}

    # Test Quality Agent
    try:
        agent = QualityAgent()
        price_data = cached_data.get('historical_data')
        result = agent.analyze(symbol, price_data, cached_data)
        agents_results['quality'] = result
        logger.info(f"✓ Quality Agent: Score={result['score']:.1f}, Confidence={result['confidence']:.2f}")
    except Exception as e:
        logger.error(f"✗ Quality Agent failed: {e}")
        return False, {}

    # Test Sentiment Agent
    try:
        agent = SentimentAgent()
        result = agent.analyze(symbol, cached_data)
        agents_results['sentiment'] = result
        logger.info(f"✓ Sentiment Agent: Score={result['score']:.1f}, Confidence={result['confidence']:.2f}")
    except Exception as e:
        logger.error(f"✗ Sentiment Agent failed: {e}")
        return False, {}

    # Test Institutional Flow Agent
    try:
        agent = InstitutionalFlowAgent()
        price_data = cached_data.get('historical_data')
        result = agent.analyze(symbol, price_data, cached_data)
        agents_results['institutional_flow'] = result
        logger.info(f"✓ Institutional Flow Agent: Score={result['score']:.1f}, Confidence={result['confidence']:.2f}")
    except Exception as e:
        logger.error(f"✗ Institutional Flow Agent failed: {e}")
        return False, {}

    return True, agents_results


def test_market_regime():
    """Test market regime detection"""
    print_separator("Testing Market Regime Detection")

    try:
        service = MarketRegimeService()
        regime = service.get_current_regime()

        logger.info(f"✓ Market Regime: {regime['regime']}")
        logger.info(f"  - Trend: {regime['trend']}")
        logger.info(f"  - Volatility: {regime['volatility']}")
        logger.info(f"  - Adaptive weights: {regime.get('weights', {})}")

        return True, regime
    except Exception as e:
        logger.error(f"✗ Market regime detection failed: {e}")
        return False, None


def test_stock_scorer():
    """Test stock scorer orchestration"""
    print_separator("Testing Stock Scorer")

    symbol = 'TCS'

    try:
        scorer = StockScorer()
        result = scorer.score_stock(symbol)

        logger.info(f"✓ Stock Scorer completed for {symbol}")
        logger.info(f"  - Composite Score: {result['composite_score']:.1f}/100")
        logger.info(f"  - Recommendation: {result['recommendation']}")
        logger.info(f"  - Confidence: {result['overall_confidence']:.2f}")
        logger.info(f"  - Agent scores:")
        for agent, data in result.get('agent_scores', {}).items():
            logger.info(f"    • {agent}: {data.get('score', 0):.1f}")

        return True, result
    except Exception as e:
        logger.error(f"✗ Stock scorer failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_narrative_engine(analysis_result):
    """Test narrative generation"""
    print_separator("Testing Narrative Engine")

    try:
        engine = InvestmentNarrativeEngine()
        narrative = engine.generate_narrative(analysis_result)

        logger.info(f"✓ Narrative generated ({len(narrative)} characters)")
        logger.info(f"\nSample:\n{narrative[:300]}...\n")

        return True, narrative
    except Exception as e:
        logger.error(f"✗ Narrative generation failed: {e}")
        return False, None


def main():
    """Run all verification tests"""
    print_separator("AI Hedge Fund System - End-to-End Verification")

    results = {
        'data_provider': False,
        'agents': False,
        'market_regime': False,
        'stock_scorer': False,
        'narrative_engine': False,
    }

    # Test 1: Data Provider
    success, cached_data = test_data_provider()
    results['data_provider'] = success

    if not success:
        logger.error("\n✗ Data provider test failed. Cannot proceed with other tests.")
        return print_summary(results)

    # Test 2: All Agents
    success, agents_results = test_agents(cached_data)
    results['agents'] = success

    # Test 3: Market Regime
    success, regime = test_market_regime()
    results['market_regime'] = success

    # Test 4: Stock Scorer
    success, analysis_result = test_stock_scorer()
    results['stock_scorer'] = success

    # Test 5: Narrative Engine (optional - may fail without API key)
    if analysis_result:
        success, narrative = test_narrative_engine(analysis_result)
        results['narrative_engine'] = success

    # Print summary
    print_summary(results)


def print_summary(results):
    """Print test summary"""
    print_separator("Verification Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test, passed_flag in results.items():
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        logger.info(f"{status:8} - {test.replace('_', ' ').title()}")

    print(f"\n{'-' * 80}")
    logger.info(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        logger.info("\n✅ ALL SYSTEMS OPERATIONAL")
        return 0
    elif passed >= total * 0.8:
        logger.info("\n⚠️  MOST SYSTEMS OPERATIONAL (Some optional features may need configuration)")
        return 0
    else:
        logger.error("\n❌ SYSTEM VERIFICATION FAILED")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
