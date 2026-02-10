#!/usr/bin/env python3
"""
Run 5-Year NIFTY 50 Backtest

This script orchestrates a comprehensive 5-year backtest on NIFTY 50 stocks:
1. Fetches NIFTY 50 symbols
2. Runs backtest with monthly rebalancing
3. Generates summary metrics
4. Performs deep analysis
5. Stores results in database
6. Outputs detailed report

Usage:
    python scripts/run_nifty50_backtest.py
    python scripts/run_nifty50_backtest.py --years 3 --symbols 10
    python scripts/run_nifty50_backtest.py --start-date 2020-01-01 --end-date 2025-01-01
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
        logging.FileHandler('backtest_run.log')
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run comprehensive backtest on NIFTY 50 stocks'
    )

    parser.add_argument(
        '--years',
        type=int,
        default=5,
        help='Number of years to backtest (default: 5)'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date in YYYY-MM-DD format (overrides --years)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date in YYYY-MM-DD format (default: today)'
    )

    parser.add_argument(
        '--symbols',
        type=int,
        help='Number of symbols to test (default: all NIFTY 50)'
    )

    parser.add_argument(
        '--frequency',
        type=str,
        default='monthly',
        choices=['daily', 'weekly', 'monthly', 'quarterly'],
        help='Rebalance frequency (default: monthly)'
    )

    parser.add_argument(
        '--parallel',
        action='store_true',
        default=True,
        help='Run in parallel mode (default: True)'
    )

    parser.add_argument(
        '--name',
        type=str,
        help='Custom name for the backtest run'
    )

    return parser.parse_args()


def run_comprehensive_backtest(args):
    """
    Run the complete backtest workflow

    Args:
        args: Parsed command line arguments

    Returns:
        run_id: UUID of the saved backtest run
    """
    logger.info("="*80)
    logger.info("COMPREHENSIVE NIFTY 50 BACKTEST")
    logger.info("="*80)

    # Step 1: Get NIFTY 50 symbols
    logger.info("\nStep 1: Fetching NIFTY 50 symbols...")
    universe = get_universe()
    symbols = universe.get_symbols('NIFTY_50')

    if args.symbols:
        symbols = symbols[:args.symbols]
        logger.info(f"Limited to {args.symbols} symbols for testing")

    logger.info(f"Symbols to backtest: {len(symbols)}")
    logger.info(f"Symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")

    # Step 2: Determine date range
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
    logger.info(f"Duration: {(end_date - start_date).days} days (~{(end_date - start_date).days / 365:.1f} years)")

    # Step 3: Initialize components
    logger.info("\nStep 3: Initializing components...")
    data_provider = HybridDataProvider()
    scorer = StockScorer(data_provider=data_provider)
    backtester = Backtester(scorer=scorer, data_provider=data_provider)

    logger.info("✓ Data Provider initialized")
    logger.info("✓ Stock Scorer initialized (5 agents)")
    logger.info("✓ Backtester initialized")

    # Step 4: Run backtest
    logger.info("\nStep 4: Running backtest...")
    logger.info(f"Rebalance Frequency: {args.frequency}")
    logger.info(f"Parallel Execution: {args.parallel}")
    logger.info("\nThis may take 2-6 hours depending on data availability...")
    logger.info("Progress updates will be shown every 10 signals.\n")

    try:
        results = backtester.run_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency=args.frequency,
            parallel=args.parallel
        )

        logger.info(f"\n✓ Backtest complete: {len(results)} signals generated")

        if not results:
            logger.error("No backtest results generated!")
            logger.error("This likely means:")
            logger.error("  1. Data provider issues (check API keys)")
            logger.error("  2. Date range too recent (no forward return data)")
            logger.error("  3. Symbols not available")
            return None

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return None

    # Step 5: Generate summary
    logger.info("\nStep 5: Generating summary metrics...")
    try:
        summary = backtester.generate_summary(results)
        logger.info("✓ Summary generated")

        # Print summary to console
        backtester.print_summary(summary)

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}", exc_info=True)
        return None

    # Step 6: Analyze results
    logger.info("\nStep 6: Performing deep analysis...")
    try:
        analyzer = BacktestAnalyzer()
        analysis = analyzer.analyze_comprehensive(results)

        logger.info("✓ Agent performance analyzed")
        logger.info("✓ Optimal weights calculated")
        logger.info("✓ Recommendations generated")

        # Print key insights
        print("\n" + "="*80)
        print("KEY INSIGHTS")
        print("="*80)

        print("\n📊 AGENT PERFORMANCE:")
        for ap in analysis['agent_performance'][:5]:
            print(f"  {ap.agent_name:20s}: Correlation {ap.correlation_with_returns:+.3f} ({ap.predictive_power})")

        print("\n⚖️  OPTIMAL WEIGHTS:")
        ow = analysis['optimal_weights']
        print(f"  Expected Sharpe Improvement: {ow.expected_improvement:+.3f}")
        for agent, weight in ow.weights.items():
            print(f"  {agent:20s}: {weight:.1%}")

        print("\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(analysis['recommendations'][:5], 1):
            print(f"  {i}. {rec}")

        if len(analysis['recommendations']) > 5:
            print(f"  ... and {len(analysis['recommendations']) - 5} more")

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        analysis = {}

    # Step 7: Store in database
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

        # Generate name if not provided
        name = args.name or f"NIFTY 50 {args.years}-Year Backtest"

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
                'args': vars(args),
                'completed_at': datetime.now().isoformat()
            }
        )

        logger.info(f"✓ Results saved to database")
        logger.info(f"Run ID: {run_id}")

    except Exception as e:
        logger.error(f"Failed to save to database: {e}", exc_info=True)
        run_id = None

    # Step 8: Generate report file
    logger.info("\nStep 8: Generating report file...")
    try:
        report_path = project_root / 'backtest_results' / f'backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("NIFTY 50 BACKTEST RESULTS\n")
            f.write("="*80 + "\n\n")

            f.write(f"Run ID: {run_id}\n")
            f.write(f"Name: {name}\n")
            f.write(f"Date Range: {start_date.date()} to {end_date.date()}\n")
            f.write(f"Symbols: {len(symbols)}\n")
            f.write(f"Frequency: {args.frequency}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            f.write("="*80 + "\n")
            f.write("PERFORMANCE SUMMARY\n")
            f.write("="*80 + "\n\n")

            f.write(f"Total Signals: {summary.total_signals}\n")
            f.write(f"BUY Signals: {summary.total_buys}\n")
            f.write(f"SELL Signals: {summary.total_sells}\n\n")

            f.write("Hit Rates (% Positive Alpha):\n")
            f.write(f"  1 Month:  {summary.hit_rate_1m:.1f}%\n")
            f.write(f"  3 Months: {summary.hit_rate_3m:.1f}%\n")
            f.write(f"  6 Months: {summary.hit_rate_6m:.1f}%\n\n")

            f.write("Average Returns:\n")
            f.write(f"  1 Month:  {summary.avg_return_1m:+.2f}%\n")
            f.write(f"  3 Months: {summary.avg_return_3m:+.2f}%\n")
            f.write(f"  6 Months: {summary.avg_return_6m:+.2f}%\n\n")

            f.write("Alpha (Excess Return vs NIFTY 50):\n")
            f.write(f"  1 Month:  {summary.avg_alpha_1m:+.2f}%\n")
            f.write(f"  3 Months: {summary.avg_alpha_3m:+.2f}%\n")
            f.write(f"  6 Months: {summary.avg_alpha_6m:+.2f}%\n\n")

            f.write("Risk Metrics:\n")
            f.write(f"  Sharpe Ratio (3M): {summary.sharpe_ratio_3m:.2f}\n")
            f.write(f"  Max Drawdown: {summary.max_drawdown:.2f}%\n")
            f.write(f"  Win Rate: {summary.win_rate:.1f}%\n")
            f.write(f"  Win/Loss Ratio: {summary.win_loss_ratio:.2f}x\n\n")

            if analysis:
                f.write("="*80 + "\n")
                f.write("RECOMMENDATIONS\n")
                f.write("="*80 + "\n\n")

                for i, rec in enumerate(analysis['recommendations'], 1):
                    f.write(f"{i}. {rec}\n")

        logger.info(f"✓ Report saved to: {report_path}")

    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)

    # Final summary
    print("\n" + "="*80)
    print("BACKTEST COMPLETE!")
    print("="*80)
    print(f"\n✓ Run ID: {run_id}")
    print(f"✓ Total Signals: {len(results)}")
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
    print("NIFTY 50 COMPREHENSIVE BACKTEST")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Years: {args.years}")
    print(f"  Frequency: {args.frequency}")
    print(f"  Parallel: {args.parallel}")
    if args.symbols:
        print(f"  Symbols: {args.symbols} (limited for testing)")
    else:
        print(f"  Symbols: All NIFTY 50")
    print("\n" + "="*80 + "\n")

    # Confirm with user
    response = input("Start backtest? This may take 2-6 hours. [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("Backtest cancelled.")
        return

    # Run backtest
    start_time = datetime.now()
    run_id = run_comprehensive_backtest(args)

    if run_id:
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n✓ Total execution time: {duration/60:.1f} minutes")
        logger.info(f"✓ Backtest successful! Run ID: {run_id}")
    else:
        logger.error("\n✗ Backtest failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
