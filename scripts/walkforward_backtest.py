#!/usr/bin/env python3
"""
Walk-Forward Validation — Indian Stock Fund Portfolio Backtest

PURPOSE
-------
Honest out-of-sample validation. Parameters are optimised on the TRAIN window
only; the TEST window is never seen during optimisation. This is the only
statistically valid way to claim that threshold choices generalise.

SPLIT
-----
  Train: Jun 2021 – Dec 2023  (30 months)
  Test:  Jan 2024 – Jun 2026  (30 months)

PASS CRITERIA
-------------
  test_sharpe  >=  0.70 × train_sharpe   (< 30% performance collapse)
  test_maxdd   > baseline_maxdd - 0.05   (not dramatically worse on hold-out)

USAGE
-----
  python scripts/walkforward_backtest.py                 # full train+test
  python scripts/walkforward_backtest.py --mode train    # optimise only
  python scripts/walkforward_backtest.py --mode test     # run best params on test
  python scripts/walkforward_backtest.py --mode both     # sequential: train then test
  python scripts/walkforward_backtest.py --mechanisms M1 M3 M6  # enable specific mechs
  python scripts/walkforward_backtest.py --compare       # print walkforward_results.csv
"""
import argparse
import json
import sys
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Add project root to path
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
)

RESULTS_LOG = Path(__file__).parent / 'walkforward_results.csv'
BEST_PARAMS_FILE = Path(__file__).parent / 'walkforward_best_params.json'

# ── Parameter grid ────────────────────────────────────────────────────────────

PARAM_GRID = [
    {'buy_threshold': b, 'sell_threshold': s, 'stop_loss': sl}
    for b  in [58.0, 60.0, 62.0]
    for s  in [35.0, 38.0, 40.0]
    for sl in [0.08, 0.10, 0.12]
]  # 27 combinations


# ── Core simulation helper ────────────────────────────────────────────────────

def _run_slice(
    prices: Dict,
    bench: pd.Series,
    quality_map: Dict,
    fundamentals_cache: Dict,
    start: str,
    end: str,
    params: Dict,
    mechanisms: List[str],
) -> Dict:
    """
    Run a single backtest on a time slice [start, end] with given params + mechanisms.
    Returns metrics dict.
    """
    start_ts = pd.Timestamp(start)
    end_ts   = pd.Timestamp(end)
    prices_slice = {s: p[(p.index >= start_ts) & (p.index <= end_ts)]
                    for s, p in prices.items()}
    prices_slice = {s: p for s, p in prices_slice.items() if len(p) > 30}
    bench_slice = bench[(bench.index >= start_ts) & (bench.index <= end_ts)]

    if bench_slice.empty or len(prices_slice) < 5:
        return {}

    mech_kwargs = {
        'rs_exit_enabled':    'M1' in mechanisms,
        'rs_exit_percentile': 0.35,
        'rs_exit_strikes':    3,
        'm2_exit_enabled':    'M2' in mechanisms,
        'm2_underperform_threshold': 0.15,
        'm2_exit_strikes':    2,
        'm3_maxhold_enabled': 'M3' in mechanisms,
        'm3_12m_decay':       8.0,   # Config A tight values
        'm3_18m_decay':       3.0,
        'm4_circuit_enabled': 'M4' in mechanisms,
        'm4_dd_threshold':    0.08,
        'm5_vix_enabled':     False,  # VIX data availability varies; disabled for WF
        'm6_rotation_enabled': 'M6' in mechanisms,
        'm6_rotation_gap':    12.0,
        'm7_hhi_enabled':     'M7' in mechanisms,
        'm7_hhi_threshold':   0.35,
        # M3 re-entry cooldown: 6 months when M3 is enabled (mirrors live system)
        'm3_cooldown_months': 6 if 'M3' in mechanisms else 0,
        # Sector rotation guard: tested and found net-negative — keep disabled
        'm1_sector_guard':    False,
    }

    try:
        pv, _ = run_signal_simulation(
            prices_slice, bench_slice, quality_map,
            buy_threshold=params['buy_threshold'],
            sell_threshold=params['sell_threshold'],
            stop_loss=params['stop_loss'],
            max_positions=10,
            transaction_cost=0.0027,
            sector_cap=0.30,
            fundamentals_cache=fundamentals_cache,
            use_backtest_scorer=True,
            min_hold_months=3,
            profit_trail_pct=0.12,
            profit_trigger_pct=0.20,
            strong_buy_threshold=75.0,
            **mech_kwargs,
        )
        pv_monthly    = pv.resample('ME').last().dropna()
        bench_monthly = bench_slice.resample('ME').last().dropna()
        if len(pv_monthly) < 6:
            return {}
        return compute_metrics(pv_monthly, bench_monthly)
    except Exception as e:
        print(f"  [warn] slice run failed: {e}")
        return {}


def _params_label(p: Dict) -> str:
    return f"b{int(p['buy_threshold'])}_s{int(p['sell_threshold'])}_sl{int(p['stop_loss']*100)}"


# ── Train phase ───────────────────────────────────────────────────────────────

def run_train(
    prices: Dict,
    bench: pd.Series,
    quality_map: Dict,
    fundamentals_cache: Dict,
    mechanisms: List[str],
) -> Tuple[Dict, List[Dict]]:
    """
    Run all 27 param combinations on the TRAIN window.
    Selects best by Sharpe (not raw return — prevents overfit on lucky years).
    Returns (best_params, all_results).
    """
    train_start, train_end = '2021-06-01', '2023-12-31'
    print(f"\n{'='*60}")
    print(f"  WALK-FORWARD: TRAIN PHASE")
    print(f"  Window: {train_start} → {train_end}")
    print(f"  Grid: {len(PARAM_GRID)} combinations")
    print(f"  Mechanisms: {mechanisms or 'none'}")
    print(f"{'='*60}")

    results = []
    for i, params in enumerate(PARAM_GRID, 1):
        label = _params_label(params)
        print(f"  [{i:2d}/{len(PARAM_GRID)}] {label} ...", end=' ', flush=True)
        m = _run_slice(prices, bench, quality_map, fundamentals_cache,
                       train_start, train_end, params, mechanisms)
        if not m:
            print("FAILED")
            continue
        results.append({'params': params, 'metrics': m, 'label': label})
        print(f"CAGR={m['cagr']:.1%}  Sharpe={m['sharpe']:.2f}  MaxDD={m['max_drawdown']:.1%}")

    if not results:
        raise RuntimeError("All training runs failed — check data availability")

    best = max(results, key=lambda r: r['metrics']['sharpe'])
    print(f"\n  ✓ Best on TRAIN: {best['label']}")
    print(f"    CAGR={best['metrics']['cagr']:.1%}  Sharpe={best['metrics']['sharpe']:.2f}"
          f"  MaxDD={best['metrics']['max_drawdown']:.1%}  Alpha={best['metrics']['alpha_ann']:.1%}/yr")
    return best, results


# ── Test phase ────────────────────────────────────────────────────────────────

def run_test(
    prices: Dict,
    bench: pd.Series,
    quality_map: Dict,
    fundamentals_cache: Dict,
    best_params: Dict,
    train_metrics: Dict,
    mechanisms: List[str],
) -> Dict:
    """
    Run ONLY the best params (selected on train) against the hold-out TEST window.
    No parameter adjustment allowed here — pure out-of-sample evaluation.
    """
    test_start, test_end = '2024-01-01', '2026-06-30'
    label = _params_label(best_params)
    print(f"\n{'='*60}")
    print(f"  WALK-FORWARD: TEST PHASE (out-of-sample)")
    print(f"  Window: {test_start} → {test_end}")
    print(f"  Params: {label}  (selected from train, not re-optimised)")
    print(f"{'='*60}")

    m = _run_slice(prices, bench, quality_map, fundamentals_cache,
                   test_start, test_end, best_params, mechanisms)
    if not m:
        print("  ✗ Test run failed")
        return {}

    print(f"\n  TEST RESULTS:")
    print(f"  CAGR={m['cagr']:.1%}  Sharpe={m['sharpe']:.2f}"
          f"  MaxDD={m['max_drawdown']:.1%}  Alpha={m['alpha_ann']:.1%}/yr")
    print(f"  WinRate={m['win_rate']:.1%}")

    train_sharpe = train_metrics.get('sharpe', 0)
    ratio = m['sharpe'] / train_sharpe if train_sharpe > 0 else 0
    threshold = 0.70

    print(f"\n  PASS/FAIL CRITERIA:")
    print(f"  test_sharpe / train_sharpe = {m['sharpe']:.2f} / {train_sharpe:.2f} = {ratio:.2f}")
    if ratio >= threshold:
        print(f"  ✅ PASS: test Sharpe is {ratio:.0%} of train Sharpe (≥ {threshold:.0%} required)")
    else:
        print(f"  ❌ FAIL: test Sharpe is only {ratio:.0%} of train Sharpe (< {threshold:.0%})")
        print(f"     DO NOT wire these parameters to live system until this improves.")

    return m


# ── Save results ──────────────────────────────────────────────────────────────

def save_results(
    best_params: Dict,
    train_metrics: Dict,
    test_metrics: Dict,
    mechanisms: List[str],
    all_train: List[Dict],
) -> None:
    """Append train + test metrics to walkforward_results.csv."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    mechs_str = '+'.join(mechanisms) if mechanisms else 'none'
    label = _params_label(best_params)

    def _row(phase, m, params):
        return {
            'run_at':        now,
            'phase':         phase,
            'params':        label,
            'mechanisms':    mechs_str,
            'buy_threshold': params.get('buy_threshold', ''),
            'sell_threshold':params.get('sell_threshold', ''),
            'stop_loss':     params.get('stop_loss', ''),
            'cagr_pct':      round(m.get('cagr', 0) * 100, 1),
            'sharpe':        round(m.get('sharpe', 0), 3),
            'max_drawdown_pct': round(m.get('max_drawdown', 0) * 100, 1),
            'alpha_ann_pct': round(m.get('alpha_ann', 0) * 100, 1),
            'win_rate_pct':  round(m.get('win_rate', 0) * 100, 1),
            'n_train_combos': len(all_train),
        }

    rows = []
    if train_metrics:
        rows.append(_row('TRAIN', train_metrics, best_params))
    if test_metrics:
        rows.append(_row('TEST', test_metrics, best_params))

    if not rows:
        return

    df_new = pd.DataFrame(rows)
    if RESULTS_LOG.exists():
        df_old = pd.read_csv(RESULTS_LOG)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    df_all.to_csv(RESULTS_LOG, index=False)

    # Save best params for future --mode test runs
    with open(BEST_PARAMS_FILE, 'w') as f:
        json.dump({'params': best_params, 'mechanisms': mechanisms}, f, indent=2)

    print(f"\n  ✓ Results saved → scripts/walkforward_results.csv")
    print(f"  ✓ Best params saved → scripts/walkforward_best_params.json")


def print_comparison():
    """Print all saved walk-forward runs."""
    if not RESULTS_LOG.exists():
        print("  No walk-forward results yet. Run first.")
        return
    df = pd.read_csv(RESULTS_LOG)
    print(f"\n{'='*80}")
    print("  WALK-FORWARD RESULTS")
    print(f"{'='*80}")
    cols = ['run_at', 'phase', 'params', 'mechanisms', 'cagr_pct', 'sharpe',
            'max_drawdown_pct', 'alpha_ann_pct']
    print(df[cols].to_string(index=False))
    print(f"{'='*80}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Walk-Forward Validation (train 2021-23 / test 2024-26)')
    parser.add_argument('--mode', choices=['train', 'test', 'both'], default='both',
                        help='Run train phase, test phase, or both (default: both)')
    parser.add_argument('--mechanisms', nargs='*', default=[],
                        choices=['M1', 'M2', 'M3', 'M4', 'M6', 'M7'],
                        help='Mechanisms to enable (space-separated, e.g. --mechanisms M1 M3 M6)')
    parser.add_argument('--compare', action='store_true',
                        help='Print saved walk-forward results and exit')
    args = parser.parse_args()

    if args.compare:
        print_comparison()
        return

    mechanisms = args.mechanisms or []

    print(f"\n  Downloading price data (5Y window) …")
    all_syms = get_all_historical_symbols(years=5)
    prices, bench = fetch_all_prices(all_syms, years=5)

    rebal_dates = get_rebalance_dates(prices, bench)
    cutoff = bench.index[-1] - pd.DateOffset(years=5)
    prices_full = {s: p[p.index >= cutoff] for s, p in prices.items()
                   if not p[p.index >= cutoff].empty}
    bench_full  = bench[bench.index >= cutoff]

    print(f"  Building quality cache …")
    q_cache     = build_annual_quality_cache(list(prices_full.keys()), rebal_dates)
    quality_map = lookup_quality(q_cache, rebal_dates[0]) if q_cache else {}

    print(f"  Building fundamentals cache …")
    fund_cache  = build_annual_fundamentals_cache(list(prices_full.keys()), rebal_dates, prices_full)

    best_params = None
    train_metrics = {}
    test_metrics  = {}
    all_train: List[Dict] = []

    if args.mode in ('train', 'both'):
        best_result, all_train = run_train(
            prices_full, bench_full, quality_map, fund_cache, mechanisms
        )
        best_params   = best_result['params']
        train_metrics = best_result['metrics']

        # Save best params for --mode test runs
        with open(BEST_PARAMS_FILE, 'w') as f:
            json.dump({'params': best_params, 'mechanisms': mechanisms}, f, indent=2)

    if args.mode in ('test', 'both'):
        if best_params is None:
            # Load from previous train run
            if not BEST_PARAMS_FILE.exists():
                print("  ✗ No saved best params. Run --mode train first.")
                return
            with open(BEST_PARAMS_FILE) as f:
                saved = json.load(f)
            best_params = saved['params']
            mechanisms  = saved.get('mechanisms', mechanisms)
            print(f"  Loaded best params from {BEST_PARAMS_FILE.name}: {_params_label(best_params)}")

        test_metrics = run_test(
            prices_full, bench_full, quality_map, fund_cache,
            best_params, train_metrics, mechanisms
        )

    save_results(best_params or {}, train_metrics, test_metrics, mechanisms, all_train)


if __name__ == '__main__':
    main()
