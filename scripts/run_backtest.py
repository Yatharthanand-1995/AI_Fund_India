#!/usr/bin/env python3
"""
Quick Backtest Runner - Easy CLI for running backtests

Usage:
    python scripts/run_backtest.py --symbols TCS INFY RELIANCE --months 12
    python scripts/run_backtest.py --nifty50 --months 24 --frequency monthly
    python scripts/run_backtest.py --help
"""

import argparse
import logging
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtester import Backtester
from data.nifty_constituents import NIFTY_50


def main():
    parser = argparse.ArgumentParser(description='Run backtest on Indian stocks')

    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Stock symbols to backtest (e.g., TCS INFY RELIANCE)'
    )

    parser.add_argument(
        '--nifty50',
        action='store_true',
        help='Backtest all NIFTY 50 stocks'
    )

    parser.add_argument(
        '--months',
        type=int,
        default=12,
        help='Number of months to backtest (default: 12)'
    )

    parser.add_argument(
        '--frequency',
        choices=['daily', 'weekly', 'monthly', 'quarterly'],
        default='monthly',
        help='Rebalancing frequency (default: monthly)'
    )

    parser.add_argument(
        '--parallel',
        action='store_true',
        default=True,
        help='Run backtest in parallel (default: True)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file for detailed results (CSV format)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Determine symbols
    if args.nifty50:
        symbols = list(NIFTY_50.keys())
        print(f"\n📊 Backtesting ALL NIFTY 50 stocks ({len(symbols)} stocks)")
    elif args.symbols:
        symbols = args.symbols
        print(f"\n📊 Backtesting {len(symbols)} stocks: {', '.join(symbols)}")
    else:
        print("❌ Error: Must specify either --symbols or --nifty50")
        parser.print_help()
        return 1

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.months * 30)

    print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"🔄 Frequency: {args.frequency}")
    print(f"⚡ Parallel: {args.parallel}")
    print()

    # Initialize backtester
    backtester = Backtester()

    # Run backtest
    try:
        print("⏳ Running backtest... This may take several minutes.\n")

        results = backtester.run_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency=args.frequency,
            parallel=args.parallel
        )

        if not results:
            print("\n⚠️  No results generated. Check if data is available for the specified period.")
            return 1

        # Generate summary
        summary = backtester.generate_summary(results)

        # Print summary
        backtester.print_summary(summary)

        # Save detailed results if requested
        if args.output:
            import pandas as pd

            # Convert results to DataFrame
            data = []
            for r in results:
                data.append({
                    'symbol': r.symbol,
                    'date': r.date,
                    'recommendation': r.recommendation,
                    'score': r.composite_score,
                    'confidence': r.confidence,
                    'entry_price': r.entry_price,
                    'return_1m': r.forward_return_1m,
                    'return_3m': r.forward_return_3m,
                    'return_6m': r.forward_return_6m,
                    'alpha_1m': r.alpha_1m,
                    'alpha_3m': r.alpha_3m,
                    'alpha_6m': r.alpha_6m,
                    'regime': r.market_regime
                })

            df = pd.DataFrame(data)
            df.to_csv(args.output, index=False)
            print(f"\n💾 Detailed results saved to: {args.output}")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Backtest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Backtest failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
