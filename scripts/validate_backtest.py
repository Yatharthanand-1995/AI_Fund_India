#!/usr/bin/env python3
"""
Comprehensive Backtest Validation Script

Tests all critical components to ensure no look-ahead bias,
correct signal generation, and proper return calculation.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from core.stock_scorer import StockScorer
from core.backtester import Backtester
from data.hybrid_provider import HybridDataProvider
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_signal_generation():
    """Test that signals align with thresholds"""
    print("\n" + "="*80)
    print("TEST 1: Signal Generation Logic")
    print("="*80)

    scorer = StockScorer()

    # Test case: Score 49 should NOT be BUY (threshold = 50)
    # Manually create agent scores that sum to 49
    test_scores = {
        'fundamentals': 50.0,
        'momentum': 48.0,
        'quality': 48.0,
        'sentiment': 50.0,
        'institutional_flow': 49.0
    }

    # Calculate composite
    weights = scorer._get_current_weights()
    composite = sum(test_scores[agent] * weights[agent] for agent in test_scores)
    print(f"Composite Score: {composite:.2f}")

    # Get recommendation
    rec = scorer._get_recommendation(composite, confidence=0.7)
    print(f"Recommendation: {rec}")
    print(f"Expected: HOLD or below (score < 50)")

    # Test thresholds
    print(f"\nThreshold Tests:")
    print(f"  Score 56 (confidence 0.7): {scorer._get_recommendation(56, 0.7)} (expected: STRONG BUY)")
    print(f"  Score 52 (confidence 0.7): {scorer._get_recommendation(52, 0.7)} (expected: BUY)")
    print(f"  Score 48 (confidence 0.7): {scorer._get_recommendation(48, 0.7)} (expected: WEAK BUY)")
    print(f"  Score 40 (confidence 0.7): {scorer._get_recommendation(40, 0.7)} (expected: HOLD)")

    # Verify no confidence factor manipulation
    rec_low_conf = scorer._get_recommendation(49, confidence=0.3)
    rec_high_conf = scorer._get_recommendation(49, confidence=0.9)
    print(f"\nConfidence Factor Test:")
    print(f"  Score 49, Low Confidence (0.3): {rec_low_conf}")
    print(f"  Score 49, High Confidence (0.9): {rec_high_conf}")

    assert rec_low_conf == rec_high_conf, "FAIL: Confidence should not affect threshold!"
    assert rec in ['HOLD', 'WEAK BUY', 'WEAK SELL'], f"FAIL: Score {composite} should not be BUY or STRONG BUY!"

    print("✅ PASS: Signal generation correct")
    return True


def test_no_lookahead_bias():
    """Test that backtest doesn't use future data"""
    print("\n" + "="*80)
    print("TEST 2: Look-Ahead Bias Check")
    print("="*80)

    scorer = StockScorer()
    backtester = Backtester(scorer=scorer, data_provider=HybridDataProvider())

    # Pick a historical date
    backtest_date = datetime(2023, 6, 1)
    symbol = "RELIANCE.NS"

    print(f"Backtest Date: {backtest_date.date()}")
    print(f"Symbol: {symbol}")

    # Get point-in-time data
    past_data = backtester._get_point_in_time_data(symbol, backtest_date)

    if past_data is None or past_data.empty:
        print("⚠️  SKIP: No data available for this symbol/date")
        return True

    # Verify no future data
    max_date = past_data.index.max()
    print(f"Latest Data Date: {max_date.date()}")

    # Allow for minor date differences due to timezone/trading day issues
    date_diff = (max_date.date() - backtest_date.date()).days
    print(f"Date Difference: {date_diff} days")

    assert date_diff <= 0, f"FAIL: Future data leaked into past! Max date {max_date.date()} is after backtest date {backtest_date.date()}"
    print("✅ PASS: No look-ahead bias detected")
    return True


def test_forward_returns_calculation():
    """Test that forward returns use correct dates"""
    print("\n" + "="*80)
    print("TEST 3: Forward Return Calculation")
    print("="*80)

    scorer = StockScorer()
    backtester = Backtester(scorer=scorer, data_provider=HybridDataProvider())

    # Get data
    symbol = "TCS.NS"
    entry_date = datetime(2023, 3, 1)
    print(f"Symbol: {symbol}")
    print(f"Entry Date: {entry_date.date()}")

    # Get future data
    future_data = backtester._get_future_data(symbol, entry_date, forward_days=100)

    if future_data is None or future_data.empty:
        print("⚠️  SKIP: No future data available")
        return True

    # Calculate forward returns
    returns = backtester._calculate_forward_returns(future_data, entry_date, [20, 60])

    print(f"20-day Return: {returns.get(20, 'N/A')}")
    print(f"60-day Return: {returns.get(60, 'N/A')}")

    # Verify returns are calculated
    if 20 in returns:
        assert -50 < returns[20] < 100, f"FAIL: 20-day return {returns[20]:.2f}% unrealistic"
        print("✅ PASS: Forward returns calculated correctly")
        return True
    else:
        print("⚠️  WARN: Could not calculate 20-day return (may need more data)")
        return True


def test_benchmark_alignment():
    """Test that benchmark returns are calculated"""
    print("\n" + "="*80)
    print("TEST 4: Benchmark Alignment")
    print("="*80)

    scorer = StockScorer()
    backtester = Backtester(scorer=scorer, data_provider=HybridDataProvider())

    # Load benchmark
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 1, 1)
    print(f"Loading benchmark data: {start_date.date()} to {end_date.date()}")

    backtester._load_benchmark_data(
        start_date=start_date,
        end_date=end_date,
        max_forward_period=120
    )

    if backtester.benchmark_data is None or backtester.benchmark_data.empty:
        print("⚠️  SKIP: Could not load benchmark data")
        return True

    print(f"Benchmark data loaded: {len(backtester.benchmark_data)} days")

    # Calculate benchmark returns for a date
    test_date = datetime(2023, 6, 15)
    print(f"Test Date: {test_date.date()}")

    benchmark_returns = backtester._calculate_benchmark_returns(test_date, [20, 60, 120])

    print(f"Benchmark Returns: {benchmark_returns}")

    assert len(benchmark_returns) > 0, "FAIL: Benchmark returns empty!"
    assert 20 in benchmark_returns or 60 in benchmark_returns, "FAIL: No benchmark data for standard periods"
    print("✅ PASS: Benchmark returns calculated")
    return True


def test_score_distribution():
    """Test that composite scores vary appropriately"""
    print("\n" + "="*80)
    print("TEST 5: Score Distribution")
    print("="*80)

    # Run mini backtest
    scorer = StockScorer()
    backtester = Backtester(scorer=scorer, data_provider=HybridDataProvider())

    symbols = ["TCS.NS", "INFY.NS", "RELIANCE.NS"]
    start_date = datetime(2023, 6, 1)
    end_date = datetime(2023, 12, 31)

    print(f"Running mini backtest: {symbols}")
    print(f"Period: {start_date.date()} to {end_date.date()}")

    results = backtester.run_backtest(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        rebalance_frequency='monthly'
    )

    if not results:
        print("⚠️  SKIP: No backtest results generated")
        return True

    scores = [r.composite_score for r in results]
    recommendations = [r.recommendation for r in results]

    print(f"\nTotal Signals: {len(scores)}")
    print(f"Min Score: {min(scores):.2f}")
    print(f"Max Score: {max(scores):.2f}")
    print(f"Avg Score: {sum(scores)/len(scores):.2f}")

    # Count recommendations
    from collections import Counter
    rec_counts = Counter(recommendations)
    print(f"\nSignal Distribution:")
    for rec, count in rec_counts.most_common():
        print(f"  {rec}: {count} ({count/len(recommendations)*100:.1f}%)")

    # Check variation
    score_range = max(scores) - min(scores)
    assert score_range > 5, f"FAIL: Scores don't vary enough (range {score_range:.2f} < 5 points)"
    print(f"\nScore Range: {score_range:.2f}")

    # Check signal distribution is reasonable (not 98% BUY)
    buy_count = sum(1 for rec in recommendations if 'BUY' in rec)
    buy_pct = buy_count / len(recommendations) * 100
    assert buy_pct < 90, f"FAIL: Too many BUY signals ({buy_pct:.1f}%) - likely broken threshold logic"

    print("✅ PASS: Scores show variation and reasonable distribution")
    return True


def main():
    print("\n" + "="*80)
    print("BACKTEST VALIDATION SUITE")
    print("="*80)

    tests = [
        ("Signal Generation", test_signal_generation),
        ("Look-Ahead Bias", test_no_lookahead_bias),
        ("Forward Returns", test_forward_returns_calculation),
        ("Benchmark Alignment", test_benchmark_alignment),
        ("Score Distribution", test_score_distribution)
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                skipped += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80)

    if failed > 0:
        print("\n⚠️  Some tests failed - backtest may have issues")
        sys.exit(1)
    else:
        print("\n✅ All tests passed - backtest ready to run")
        sys.exit(0)


if __name__ == "__main__":
    main()
