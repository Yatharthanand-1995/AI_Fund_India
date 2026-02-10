#!/usr/bin/env python3
"""
Run 5-Year NIFTY 50 Backtest with Adjusted Weights

This version adjusts agent weights for backtest mode where fundamental data is unavailable.
Uses only price-based agents (Momentum, Quality, Institutional Flow) with higher weights.
"""

import sys
import os
import logging
import argparse
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
from data.stock_universe import get_universe

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backtest_run_fixed.log')
    ]
)
logger = logging.getLogger(__name__)


# BACKTEST-OPTIMIZED WEIGHTS
# Reduce weights for agents that don't work well with price-only data
BACKTEST_WEIGHTS = {
    'fundamentals': 0.10,      # Reduced from 0.36 (returns neutral 50 in backtest)
    'momentum': 0.45,          # Increased from 0.27 (primary price-based signal)
    'quality': 0.25,           # Increased from 0.18 (price-based volatility/returns)
    'sentiment': 0.05,         # Reduced from 0.09 (returns neutral 50 in backtest)
    'institutional_flow': 0.15 # Increased from 0.10 (price/volume based)
}

# ADJUSTED THRESHOLDS for backtest mode
# With fundamentals=50, we need lower thresholds to generate BUY signals
BACKTEST_THRESHOLDS = {
    'STRONG BUY': 70,  # Down from 80
    'BUY': 60,         # Down from 68
    'WEAK BUY': 52,    # Down from 58
    'HOLD_HIGH': 48,
    'HOLD_LOW': 42,
    'WEAK SELL': 32,
    'SELL': 0
}


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run comprehensive backtest on NIFTY 50 stocks with optimized settings'
    )

    parser.add_argument('--years', type=int, default=5, help='Number of years to backtest')
    parser.add_argument('--start-date', type=str, help='Start date YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, help='End date YYYY-MM-DD')
    parser.add_argument('--symbols', type=int, help='Number of symbols (default: all)')
    parser.add_argument('--frequency', type=str, default='monthly', choices=['daily', 'weekly', 'monthly', 'quarterly'])
    parser.add_argument('--name', type=str, help='Custom backtest name')

    return parser.parse_args()


def run_backtest_fixed(args):
    """Run backtest with optimized settings"""
    logger.info("="*80)
    logger.info("NIFTY 50 BACKTEST - OPTIMIZED FOR PRICE-ONLY DATA")
    logger.info("="*80)

    # Get symbols
    logger.info("\nStep 1: Fetching NIFTY 50 symbols...")
    universe = get_universe()
    symbols = universe.get_symbols('NIFTY_50')

    if args.symbols:
        symbols = symbols[:args.symbols]
        logger.info(f"Limited to {args.symbols} symbols for testing")

    logger.info(f"Symbols to backtest: {len(symbols)}")

    # Determine date range
    logger.info("\nStep 2: Setting up date range...")
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()

    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        start_date = end_date - timedelta(days=args.years * 365)

    logger.info(f"Start Date: {start_date.date()}")
    logger.info(f"End Date: {end_date.date()}")

    # Initialize components with custom weights
    logger.info("\nStep 3: Initializing components with backtest-optimized weights...")
    data_provider = HybridDataProvider()
    scorer = StockScorer(data_provider=data_provider)

    # Set backtest-optimized weights
    scorer.set_weights(BACKTEST_WEIGHTS)
    logger.info(f"Backtest weights: {BACKTEST_WEIGHTS}")

    # Override recommendation thresholds
    scorer.RECOMMENDATION_THRESHOLDS = BACKTEST_THRESHOLDS
    logger.info(f"Adjusted thresholds: BUY≥{BACKTEST_THRESHOLDS['BUY']}, SELL<{BACKTEST_THRESHOLDS['WEAK SELL']}")

    backtester = Backtester(scorer=scorer, data_provider=data_provider)

    # Run backtest
    logger.info("\nStep 4: Running backtest...")
    logger.info("This may take 2-6 hours depending on data availability...")

    try:
        results = backtester.run_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency=args.frequency,
            parallel=True
        )

        logger.info(f"\n✓ Backtest complete: {len(results)} signals generated")

        if not results:
            logger.error("No backtest results generated!")
            return None

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return None

    # Generate summary
    logger.info("\nStep 5: Generating summary metrics...")
    try:
        summary = backtester.generate_summary(results)
        logger.info("✓ Summary generated")
        backtester.print_summary(summary)
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}", exc_info=True)
        return None

    # Analyze results
    logger.info("\nStep 6: Performing deep analysis...")
    try:
        analyzer = BacktestAnalyzer()
        analysis = analyzer.analyze_comprehensive(results, current_weights=BACKTEST_WEIGHTS)

        logger.info("✓ Analysis complete")

        # Print key insights
        print("\n" + "="*80)
        print("KEY INSIGHTS")
        print("="*80)

        if analysis['agent_performance']:
            print("\n📊 AGENT PERFORMANCE:")
            for ap in analysis['agent_performance'][:5]:
                print(f"  {ap.agent_name:20s}: Correlation {ap.correlation_with_returns:+.3f} ({ap.predictive_power})")

        if 'optimal_weights' in analysis:
            print("\n⚖️  OPTIMAL WEIGHTS:")
            ow = analysis['optimal_weights']
            print(f"  Expected Sharpe Improvement: {ow.expected_improvement:+.3f}")
            for agent, weight in ow.weights.items():
                current = BACKTEST_WEIGHTS[agent]
                change = weight - current
                print(f"  {agent:20s}: {weight:.1%} (current: {current:.1%}, change: {change:+.1%})")

        if analysis['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(analysis['recommendations'][:5], 1):
                print(f"  {i}. {rec}")

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        analysis = {}

    # Store in database
    logger.info("\nStep 7: Storing results in database...")
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
        name = args.name or f"NIFTY 50 {args.years}-Year Backtest (Optimized)"

        run_id = db.save_backtest_run(
            name=name,
            results=results,
            summary=summary,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            frequency=args.frequency,
            metadata={
                'analysis': serializable_analysis,
                'weights': BACKTEST_WEIGHTS,
                'thresholds': BACKTEST_THRESHOLDS,
                'args': vars(args),
                'completed_at': datetime.now().isoformat(),
                'version': 'optimized_v2'
            }
        )

        logger.info(f"✓ Results saved to database")
        logger.info(f"Run ID: {run_id}")

    except Exception as e:
        logger.error(f"Failed to save to database: {e}", exc_info=True)
        run_id = None

    # Generate report
    logger.info("\nStep 8: Generating report file...")
    try:
        report_path = project_root / 'backtest_results' / f'backtest_optimized_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("NIFTY 50 BACKTEST RESULTS (OPTIMIZED FOR PRICE-ONLY DATA)\n")
            f.write("="*80 + "\n\n")

            f.write(f"Run ID: {run_id}\n")
            f.write(f"Name: {name}\n")
            f.write(f"Date Range: {start_date.date()} to {end_date.date()}\n")
            f.write(f"Symbols: {len(symbols)}\n")
            f.write(f"Frequency: {args.frequency}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            f.write("BACKTEST-OPTIMIZED CONFIGURATION:\n")
            f.write(f"  Weights: {BACKTEST_WEIGHTS}\n")
            f.write(f"  Thresholds: BUY≥{BACKTEST_THRESHOLDS['BUY']}, SELL<{BACKTEST_THRESHOLDS['WEAK SELL']}\n\n")

            f.write("PERFORMANCE SUMMARY:\n")
            f.write(f"  Total Signals: {summary.total_signals}\n")
            f.write(f"  BUY Signals: {summary.total_buys}\n")
            f.write(f"  SELL Signals: {summary.total_sells}\n")
            f.write(f"  Hit Rate (3M): {summary.hit_rate_3m:.1f}%\n")
            f.write(f"  Avg Alpha (3M): {summary.avg_alpha_3m:+.2f}%\n")
            f.write(f"  Sharpe Ratio (3M): {summary.sharpe_ratio_3m:.2f}\n")

        logger.info(f"✓ Report saved to: {report_path}")

    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)

    # Final summary
    print("\n" + "="*80)
    print("BACKTEST COMPLETE!")
    print("="*80)
    print(f"\n✓ Run ID: {run_id}")
    print(f"✓ Total Signals: {len(results)}")
    print(f"✓ BUY Signals: {summary.total_buys}")
    print(f"✓ SELL Signals: {summary.total_sells}")
    print(f"✓ Hit Rate (3M): {summary.hit_rate_3m:.1f}%")
    print(f"✓ Avg Alpha (3M): {summary.avg_alpha_3m:+.2f}%")
    print(f"✓ Sharpe Ratio (3M): {summary.sharpe_ratio_3m:.2f}")
    print(f"\n✓ Results saved to database")
    print(f"✓ View in UI at: http://localhost:3000/backtest")
    print(f"✓ Report file: {report_path}")
    print("\n" + "="*80 + "\n")

    return run_id


def main():
    """Main entry point"""
    args = parse_args()

    print("\n" + "="*80)
    print("NIFTY 50 BACKTEST - OPTIMIZED FOR PRICE-ONLY DATA")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Years: {args.years}")
    print(f"  Frequency: {args.frequency}")
    print(f"  Weights: Optimized for backtest (Momentum: 45%, Quality: 25%)")
    print(f"  Thresholds: Adjusted (BUY≥60, SELL<32)")
    if args.symbols:
        print(f"  Symbols: {args.symbols} (limited for testing)")
    print("\n" + "="*80 + "\n")

    # Confirm with user
    response = input("Start optimized backtest? This may take 2-6 hours. [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("Backtest cancelled.")
        return

    # Run backtest
    start_time = datetime.now()
    run_id = run_backtest_fixed(args)

    if run_id:
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n✓ Total execution time: {duration/60:.1f} minutes")
        logger.info(f"✓ Backtest successful! Run ID: {run_id}")
    else:
        logger.error("\n✗ Backtest failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
