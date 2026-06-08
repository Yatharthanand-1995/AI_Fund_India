#!/usr/bin/env python3
"""
Parameter Sweep — 27-Combination Grid Search

Systematically runs all combinations of buy_threshold × sell_threshold × stop_loss
against the full 5Y backtest. Results auto-append to backtest_results.csv.

GRID
----
  buy_threshold:   58, 60, 62
  sell_threshold:  35, 38, 40
  stop_loss:       8%, 10%, 12%
  Total: 3 × 3 × 3 = 27 combinations

USAGE
-----
  python scripts/run_sweep.py                       # default 27-combo sweep, signal mode
  python scripts/run_sweep.py --mechanisms M1 M3    # enable specific mechanisms for all combos
  python scripts/run_sweep.py --years 3             # 3Y sweep (faster)
  python scripts/run_sweep.py --top-n 5             # show top-N results at end
  python scripts/run_sweep.py --dry-run             # print grid, don't run

OUTPUT
------
  - All 27 results appended to scripts/backtest_results.csv
  - Ranked comparison table printed at end (by Sharpe, then MaxDD)
  - Best config highlighted
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.portfolio_backtest import (
    fetch_all_prices,
    get_all_historical_symbols,
    build_annual_quality_cache,
    build_annual_fundamentals_cache,
    lookup_quality,
    get_rebalance_dates,
    run_signal_simulation,
    bench_metrics,
    compute_metrics,
    save_run_result,
    append_to_experiment_log,
    RESULTS_LOG,
)

# ── Parameter grid ────────────────────────────────────────────────────────────

PARAM_GRID = [
    {'buy_threshold': b, 'sell_threshold': s, 'stop_loss': sl}
    for b  in [58.0, 60.0, 62.0]
    for s  in [35.0, 38.0, 40.0]
    for sl in [0.08, 0.10, 0.12]
]


def _run_one(
    prices_bt: Dict,
    bench_bt: pd.Series,
    quality_map: Dict,
    fund_cache: Dict,
    params: Dict,
    mechanisms: List[str],
    years: int,
) -> Dict:
    """Run a single param combination and return metrics."""
    mech_kwargs = {
        'rs_exit_enabled':     'M1' in mechanisms,
        'rs_exit_percentile':  0.35,
        'rs_exit_strikes':     3,
        'm2_exit_enabled':     'M2' in mechanisms,
        'm2_underperform_threshold': 0.15,
        'm2_exit_strikes':     2,
        'm3_maxhold_enabled':  'M3' in mechanisms,
        'm3_12m_decay':        8.0,   # Config A tight values
        'm3_18m_decay':        3.0,
        'm4_circuit_enabled':  'M4' in mechanisms,
        'm4_dd_threshold':     0.08,
        'm5_vix_enabled':      False,
        'm6_rotation_enabled': 'M6' in mechanisms,
        'm6_rotation_gap':     12.0,
        'm7_hhi_enabled':      'M7' in mechanisms,
        'm7_hhi_threshold':    0.35,
        # M3 re-entry cooldown: 6 months when M3 is enabled (mirrors live system)
        'm3_cooldown_months':  6 if 'M3' in mechanisms else 0,
        # Sector rotation guard: tested and found net-negative — keep disabled
        'm1_sector_guard':     False,
    }
    pv, _ = run_signal_simulation(
        prices_bt, bench_bt, quality_map,
        buy_threshold=params['buy_threshold'],
        sell_threshold=params['sell_threshold'],
        stop_loss=params['stop_loss'],
        max_positions=10,
        transaction_cost=0.0027,
        sector_cap=0.30,
        fundamentals_cache=fund_cache,
        use_backtest_scorer=True,
        min_hold_months=3,
        profit_trail_pct=0.12,
        profit_trigger_pct=0.20,
        strong_buy_threshold=75.0,
        **mech_kwargs,
    )
    pv_monthly    = pv.resample('ME').last().dropna()
    bench_monthly = bench_bt.resample('ME').last().dropna()
    return compute_metrics(pv_monthly, bench_monthly)


def _label(params: Dict, mechanisms: List[str]) -> str:
    mechs = '+'.join(mechanisms) if mechanisms else 'noM'
    return (
        f"sweep_{mechs}_"
        f"b{int(params['buy_threshold'])}_"
        f"s{int(params['sell_threshold'])}_"
        f"sl{int(params['stop_loss']*100)}"
    )


def print_ranked_table(results: List[Dict], top_n: int = 10) -> None:
    """Print ranked results table sorted by Sharpe desc, then MaxDD desc."""
    if not results:
        return
    df = pd.DataFrame(results)
    df = df.sort_values(['sharpe', 'max_drawdown'], ascending=[False, False])
    print(f"\n{'='*80}")
    print(f"  SWEEP RESULTS — TOP {min(top_n, len(df))} by Sharpe")
    print(f"{'='*80}")
    hdr = f"  {'Label':42s}  {'CAGR':>6}  {'Sharpe':>7}  {'MaxDD':>7}  {'Alpha':>7}  {'Win':>5}"
    print(hdr)
    print('  ' + '-' * 76)
    for i, (_, row) in enumerate(df.head(top_n).iterrows()):
        marker = ' ◀ BEST' if i == 0 else ''
        print(
            f"  {row['label']:42s}  "
            f"{row['cagr']*100:5.1f}%  "
            f"{row['sharpe']:7.2f}  "
            f"{row['max_drawdown']*100:6.1f}%  "
            f"{row['alpha_ann']*100:6.1f}%  "
            f"{row['win_rate']*100:4.0f}%"
            f"{marker}"
        )
    print(f"{'='*80}")
    best = df.iloc[0]
    print(f"\n  ✓ Best config: {best['label']}")
    print(f"    CAGR {best['cagr']:.1%}  |  Sharpe {best['sharpe']:.2f}  |  MaxDD {best['max_drawdown']:.1%}  |  Alpha {best['alpha_ann']:.1%}/yr")
    print(f"\n  Run this config with full options:")
    params = best['params']
    mechs_flags = ''.join(f' --{m.lower()}-exit' if m in ('M1','M2') else
                          f' --m{m[1]}-maxhold' if m == 'M3' else
                          f' --m{m[1]}-circuit' if m == 'M4' else
                          f' --m{m[1]}-rotation' if m == 'M6' else
                          f' --m{m[1]}-hhi' if m == 'M7' else ''
                          for m in best.get('mechanisms', []))
    print(
        f"  python scripts/portfolio_backtest.py --signal-mode --years 5 \\\n"
        f"    --buy-threshold {params['buy_threshold']:.0f} "
        f"--sell-threshold {params['sell_threshold']:.0f} "
        f"--stop-loss {params['stop_loss']:.2f}{mechs_flags}"
    )


def main():
    parser = argparse.ArgumentParser(description='27-combo parameter grid search')
    parser.add_argument('--years',      type=int,   default=5,   help='Backtest window (default 5)')
    parser.add_argument('--mechanisms', nargs='*', default=[],
                        choices=['M1', 'M2', 'M3', 'M4', 'M6', 'M7'],
                        help='Mechanisms to enable for all combos (e.g. --mechanisms M1 M3)')
    parser.add_argument('--top-n',      type=int,   default=10,  help='Show top-N results (default 10)')
    parser.add_argument('--dry-run',    action='store_true',     help='Print grid and exit without running')
    args = parser.parse_args()

    mechanisms = args.mechanisms or []

    if args.dry_run:
        print(f"\n  Sweep grid ({len(PARAM_GRID)} combinations):")
        for p in PARAM_GRID:
            print(f"    {_label(p, mechanisms)}")
        return

    print(f"\n{'='*60}")
    print(f"  PARAMETER SWEEP — {len(PARAM_GRID)} combinations × {args.years}Y")
    print(f"  Mechanisms: {mechanisms or 'none'}")
    print(f"  {'='*56}")
    print(f"  Fetching price data …")

    all_syms = get_all_historical_symbols(years=args.years)
    prices, bench = fetch_all_prices(all_syms, years=args.years)

    cutoff = bench.index[-1] - pd.DateOffset(years=args.years)
    prices_bt = {s: p[p.index >= cutoff] for s, p in prices.items()
                 if not p[p.index >= cutoff].empty}
    bench_bt  = bench[bench.index >= cutoff]
    bm = bench_metrics(bench_bt)

    rebal_dates = get_rebalance_dates(prices_bt, bench_bt)
    print(f"  Building caches …")
    q_cache     = build_annual_quality_cache(list(prices_bt.keys()), rebal_dates)
    quality_map = lookup_quality(q_cache, rebal_dates[0]) if q_cache else {}
    fund_cache  = build_annual_fundamentals_cache(list(prices_bt.keys()), rebal_dates, prices_bt)

    results = []
    failed  = 0

    for i, params in enumerate(PARAM_GRID, 1):
        label = _label(params, mechanisms)
        print(f"  [{i:2d}/{len(PARAM_GRID)}] {label} ...", end=' ', flush=True)
        try:
            m = _run_one(prices_bt, bench_bt, quality_map, fund_cache, params, mechanisms, args.years)
            results.append({**m, 'label': label, 'params': params, 'mechanisms': mechanisms})
            save_run_result(label, {
                'years': args.years, 'top_n': 10, 'sector_cap': 0.30,
                'exit_drawdown': params['stop_loss'], 'score_decay': params['sell_threshold'],
                'quality': True, 'costs': True,
                'buy_threshold': params['buy_threshold'],
                'sell_threshold': params['sell_threshold'],
                'stop_loss': params['stop_loss'],
                'mechanisms': '+'.join(mechanisms) if mechanisms else 'none',
            }, m, bm, hypothesis=f"Grid sweep combo {i}/{len(PARAM_GRID)}")
            print(f"CAGR={m['cagr']:.1%}  Sharpe={m['sharpe']:.2f}  MaxDD={m['max_drawdown']:.1%}")
        except Exception as e:
            print(f"FAILED ({e})")
            failed += 1

    print(f"\n  Completed {len(results)}/{len(PARAM_GRID)} combos ({failed} failed)")
    print_ranked_table(results, top_n=args.top_n)
    print(f"\n  Full results in scripts/backtest_results.csv")
    print(f"  Compare: python scripts/portfolio_backtest.py --compare\n")


if __name__ == '__main__':
    main()
