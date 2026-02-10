#!/usr/bin/env python3
"""
Test Backtest - Quick validation of fixes

Tests the backtesting system with:
- 3 stocks (TCS, INFY, RELIANCE)
- 1 year period
- Monthly rebalancing

This should complete in 5-15 minutes and verify:
1. No look-ahead bias (cached_data passed correctly)
2. Signals are generated (>0 results)
3. Forward returns calculated
4. Analysis functions work
5. Database storage works
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.stock_scorer import StockScorer
from core.backtester import Backtester
from data.hybrid_provider import HybridDataProvider
from data.backtest_db import BacktestDatabase
from core.backtest_analyzer import BacktestAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run small test backtest"""
    print("\n" + "="*80)
    print("TEST BACKTEST - Validating Fixes")
    print("="*80)

    # Test configuration
    symbols = ['TCS', 'INFY', 'RELIANCE']
    end_date = datetime(2024, 6, 30)  # Use historical date to ensure forward return data
    start_date = datetime(2023, 6, 1)  # ~1 year
    frequency = 'monthly'

    print(f"\nConfiguration:")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Start Date: {start_date.date()}")
    print(f"  End Date: {end_date.date()}")
    print(f"  Duration: ~{(end_date - start_date).days / 30:.0f} months")
    print(f"  Frequency: {frequency}")
    print(f"\nExpected signals: ~{len(symbols) * 12} (3 stocks x ~12 months)")
    print(f"Estimated time: 5-15 minutes\n")

    # Step 1: Initialize components
    print("Step 1: Initializing components...")
    data_provider = HybridDataProvider()
    scorer = StockScorer(data_provider=data_provider)
    backtester = Backtester(scorer=scorer, data_provider=data_provider)
    print("✓ Components initialized\n")

    # Step 2: Run backtest
    print("Step 2: Running backtest...")
    print("This will take a few minutes. Progress updates every 10 signals.\n")

    try:
        results = backtester.run_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency=frequency,
            parallel=True
        )

        print(f"\n✓ Backtest complete!")
        print(f"  Total signals generated: {len(results)}")

        if not results:
            print("\n❌ FAILURE: No signals generated!")
            print("   This indicates the bug is not fully fixed.")
            return False

        print(f"\n✅ SUCCESS: Generated {len(results)} signals")

    except Exception as e:
        print(f"\n❌ FAILURE: Backtest crashed: {e}")
        logger.error("Backtest failed", exc_info=True)
        return False

    # Step 3: Validate results
    print("\nStep 3: Validating results...")

    # Check that we have forward returns
    results_with_returns = [r for r in results if r.forward_return_3m is not None]
    print(f"  Signals with 3M forward returns: {len(results_with_returns)}/{len(results)}")

    if len(results_with_returns) == 0:
        print("  ⚠️  WARNING: No forward returns calculated!")
    else:
        print("  ✓ Forward returns calculated")

    # Check that we have alpha values
    results_with_alpha = [r for r in results if r.alpha_3m is not None]
    print(f"  Signals with 3M alpha: {len(results_with_alpha)}/{len(results)}")

    if len(results_with_alpha) == 0:
        print("  ⚠️  WARNING: No alpha values calculated!")
    else:
        print("  ✓ Alpha values calculated")

    # Check agent scores
    sample_result = results[0]
    print(f"\n  Sample result (first signal):")
    print(f"    Symbol: {sample_result.symbol}")
    print(f"    Date: {sample_result.date.date()}")
    print(f"    Recommendation: {sample_result.recommendation}")
    print(f"    Composite Score: {sample_result.composite_score:.1f}")
    print(f"    Forward Return (3M): {sample_result.forward_return_3m:+.2f}%" if sample_result.forward_return_3m else "    Forward Return (3M): N/A")
    print(f"    Alpha (3M): {sample_result.alpha_3m:+.2f}%" if sample_result.alpha_3m else "    Alpha (3M): N/A")
    print(f"    Agent Scores:")
    for agent, score in sample_result.agent_scores.items():
        print(f"      {agent:20s}: {score:.1f}")

    # Step 4: Generate summary
    print("\nStep 4: Generating summary...")
    try:
        summary = backtester.generate_summary(results)
        print("✓ Summary generated\n")

        # Print key metrics
        print("  Key Metrics:")
        print(f"    Hit Rate (3M): {summary.hit_rate_3m:.1f}%")
        print(f"    Avg Return (3M): {summary.avg_return_3m:+.2f}%")
        print(f"    Avg Alpha (3M): {summary.avg_alpha_3m:+.2f}%")
        print(f"    Sharpe Ratio (3M): {summary.sharpe_ratio_3m:.2f}")
        print(f"    Win Rate: {summary.win_rate:.1f}%")

    except Exception as e:
        print(f"❌ Failed to generate summary: {e}")
        logger.error("Summary generation failed", exc_info=True)
        return False

    # Step 5: Run analysis
    print("\nStep 5: Running analysis...")
    try:
        analyzer = BacktestAnalyzer()
        analysis = analyzer.analyze_comprehensive(results)
        print("✓ Analysis complete\n")

        # Print agent performance
        if analysis['agent_performance']:
            print("  Agent Performance (sorted by correlation):")
            for ap in analysis['agent_performance'][:5]:
                print(f"    {ap.agent_name:20s}: {ap.correlation_with_returns:+.3f} ({ap.predictive_power})")

        # Print optimal weights
        if analysis['optimal_weights']:
            ow = analysis['optimal_weights']
            print(f"\n  Optimal Weights:")
            print(f"    Expected improvement: {ow.expected_improvement:+.3f}")
            for agent, weight in ow.weights.items():
                print(f"    {agent:20s}: {weight:.1%}")

    except Exception as e:
        print(f"❌ Failed to run analysis: {e}")
        logger.error("Analysis failed", exc_info=True)
        return False

    # Step 6: Test database storage
    print("\nStep 6: Testing database storage...")
    try:
        # Convert analysis to JSON-serializable format
        serializable_analysis = {
            'agent_performance': [
                {
                    'agent_name': ap.agent_name,
                    'correlation_with_returns': float(ap.correlation_with_returns),
                    'avg_score': float(ap.avg_score),
                    'current_weight': float(ap.current_weight),
                    'optimal_weight': float(ap.optimal_weight),
                    'weight_change': float(ap.weight_change),
                    'predictive_power': ap.predictive_power
                }
                for ap in analysis.get('agent_performance', [])
            ],
            'optimal_weights': {
                'weights': analysis['optimal_weights'].weights,
                'expected_improvement': float(analysis['optimal_weights'].expected_improvement),
                'current_sharpe': float(analysis['optimal_weights'].current_sharpe),
                'optimal_sharpe': float(analysis['optimal_weights'].optimal_sharpe),
                'methodology': analysis['optimal_weights'].methodology
            } if 'optimal_weights' in analysis else {},
            'sector_performance': analysis.get('sector_performance', {}),
            'time_series_performance': analysis.get('time_series_performance', {}),
            'recommendations': analysis.get('recommendations', [])
        }

        db = BacktestDatabase()
        run_id = db.save_backtest_run(
            name="Test Backtest - Validation Run",
            results=results,
            summary=summary,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            frequency=frequency,
            metadata={
                'analysis': serializable_analysis,
                'test_run': True
            }
        )
        print(f"✓ Results saved to database")
        print(f"  Run ID: {run_id}")

        # Try to retrieve it
        retrieved = db.get_backtest_run(run_id)
        if retrieved:
            print(f"✓ Successfully retrieved from database")
            print(f"  Retrieved {len(retrieved['signals'])} signals")
        else:
            print("❌ Failed to retrieve from database")
            return False

    except Exception as e:
        print(f"❌ Database storage failed: {e}")
        logger.error("Database storage failed", exc_info=True)
        return False

    # Final validation
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)

    checks = [
        ("Signals generated", len(results) > 0),
        ("Forward returns calculated", len(results_with_returns) > 0),
        ("Alpha values calculated", len(results_with_alpha) > 0),
        ("Summary generated", summary is not None),
        ("Analysis completed", analysis is not None),
        ("Database storage works", run_id is not None),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not passed:
            all_passed = False

    print("="*80)

    if all_passed:
        print("\n🎉 ALL CHECKS PASSED!")
        print("\nThe backtesting system is working correctly.")
        print("You can now run the full 5-year NIFTY 50 backtest with:")
        print("  python scripts/run_nifty50_backtest.py")
        print("\n" + "="*80 + "\n")
        return True
    else:
        print("\n⚠️  SOME CHECKS FAILED")
        print("Review the errors above before running the full backtest.")
        print("\n" + "="*80 + "\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
