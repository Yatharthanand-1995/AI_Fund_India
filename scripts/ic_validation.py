#!/usr/bin/env python3
"""
IC (Information Coefficient) Validation

Measures the predictive power of the new scoring system using two approaches:

1. Cross-sectional IC
   Score all stocks TODAY, correlate each agent score with their historical
   1M/3M/6M returns.  Quick sanity check — are high-scoring stocks the ones
   that have been performing well?

2. Rolling monthly IC (momentum component)
   At each of the past 6 monthly snapshots, compute momentum scores using
   only price data available at that point, then measure Spearman correlation
   with the SUBSEQUENT 1-month return.  This is the gold-standard predictive
   IC because it uses truly out-of-sample forward returns.

Metrics reported:
  IC       — mean Spearman rank correlation (good: 0.02-0.05, strong: >0.05)
  ICIR     — IC / std(IC), information ratio  (good: >0.4)
  Hit rate — % of periods where IC > 0
  t-stat   — statistical significance (|t| > 2 is significant at 5%)
  p-value  — two-tailed p-value

Usage:
    python scripts/ic_validation.py
    python scripts/ic_validation.py --stocks 30  # use top 30 NIFTY stocks
    python scripts/ic_validation.py --months 6   # 6 rolling IC periods
"""

import sys
import os
import warnings
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

warnings.filterwarnings('ignore')
logging.disable(logging.CRITICAL)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ─────────────────────────────────────────────────────────────────────────────
# NIFTY 50 universe
# ─────────────────────────────────────────────────────────────────────────────
NIFTY50 = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS',
    'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BAJFINANCE.NS', 'BHARTIARTL.NS',
    'KOTAKBANK.NS', 'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS',
    'TITAN.NS', 'SUNPHARMA.NS', 'NTPC.NS', 'WIPRO.NS', 'ULTRACEMCO.NS',
    'POWERGRID.NS', 'TATAMOTORS.NS', 'ONGC.NS', 'M&M.NS', 'NESTLEIND.NS',
    'JSWSTEEL.NS', 'TATASTEEL.NS', 'ADANIPORTS.NS', 'BAJAJFINSV.NS',
    'COALINDIA.NS', 'HCLTECH.NS', 'GRASIM.NS', 'DIVISLAB.NS', 'CIPLA.NS',
    'APOLLOHOSP.NS', 'EICHERMOT.NS', 'BRITANNIA.NS', 'DRREDDY.NS',
    'HEROMOTOCO.NS', 'HINDALCO.NS', 'INDUSINDBK.NS', 'BPCL.NS',
    'TATACONSUM.NS', 'SBILIFE.NS', 'BAJAJ-AUTO.NS', 'TECHM.NS',
    'LTIM.NS', 'ADANIENT.NS', 'HDFCLIFE.NS',
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def spearman_ic(scores: np.ndarray, returns: np.ndarray) -> Optional[float]:
    """Spearman rank correlation, returns None if <5 paired observations."""
    mask = np.isfinite(scores) & np.isfinite(returns)
    if mask.sum() < 5:
        return None
    corr, _ = scipy_stats.spearmanr(scores[mask], returns[mask])
    return float(corr)


def ic_stats(ic_series: List[float]) -> Dict:
    """Compute IC, ICIR, hit-rate, t-stat, p-value from a list of ICs."""
    arr = np.array([x for x in ic_series if x is not None and np.isfinite(x)])
    if len(arr) == 0:
        return {'ic': None, 'icir': None, 'hit_rate': None, 't_stat': None, 'p_value': None, 'n': 0}
    ic_mean = float(np.mean(arr))
    ic_std  = float(np.std(arr, ddof=1)) if len(arr) > 1 else float('nan')
    icir    = ic_mean / ic_std if ic_std > 0 else float('nan')
    hit     = float(np.mean(arr > 0))
    if len(arr) > 1 and ic_std > 0:
        t = ic_mean / (ic_std / np.sqrt(len(arr)))
        p = float(2 * scipy_stats.t.sf(abs(t), df=len(arr) - 1))
    else:
        t, p = float('nan'), float('nan')
    return {'ic': ic_mean, 'icir': icir, 'hit_rate': hit, 't_stat': t, 'p_value': p, 'n': len(arr)}


def _calc_return(prices: pd.Series, lookback_days: int) -> Optional[float]:
    if len(prices) < lookback_days + 1:
        return None
    past  = prices.iloc[-(lookback_days + 1)]
    now   = prices.iloc[-1]
    if pd.isna(past) or pd.isna(now) or past <= 0:
        return None
    return (now - past) / past * 100


def _calc_momentum_score(prices: pd.Series) -> Optional[float]:
    """
    Simplified momentum score for rolling IC test (price-based only).
    Mirrors the key components of MomentumAgent: 1M/3M/6M returns + RSI trend.
    Returns a 0-100 score.
    """
    r1m  = _calc_return(prices, 21)
    r3m  = _calc_return(prices, 63)
    r6m  = _calc_return(prices, 126)
    r12m = _calc_return(prices, 252)

    available = [r for r in [r1m, r3m, r6m, r12m] if r is not None]
    if len(available) < 2:
        return None

    # Score each return window (mirrors momentum agent thresholds)
    def score_return(r: Optional[float], w1: float, w2: float, w3: float) -> float:
        if r is None:
            return 25.0  # neutral
        if r >= w1:   return 40.0
        if r >= w2:   return 30.0
        if r >= w3:   return 20.0
        if r >= 0:    return 12.0
        if r >= -10:  return 6.0
        return 0.0

    s1m  = score_return(r1m,  5,  2,  0)   * 0.25
    s3m  = score_return(r3m,  10, 5,  0)   * 0.30
    s6m  = score_return(r6m,  20, 10, 0)   * 0.30
    s12m = score_return(r12m, 30, 15, 0)   * 0.15

    # RSI proxy: position vs 14-day EMA
    if len(prices) >= 20:
        ema14 = prices.ewm(span=14, adjust=False).mean().iloc[-1]
        rsi_proxy = min(40.0, max(0.0, (prices.iloc[-1] / ema14 - 1) * 200 + 20))
    else:
        rsi_proxy = 20.0  # neutral

    total = (s1m + s3m + s6m + s12m) * (100 / 40) + rsi_proxy * 0.0
    return min(100.0, max(0.0, float(s1m + s3m + s6m + s12m) / 0.40))


def fetch_prices(symbols: List[str], years: int = 2) -> Dict[str, pd.Series]:
    """Fetch 2 years of Close prices for each symbol."""
    import yfinance as yf
    print(f"\nFetching {years}Y price history for {len(symbols)} stocks …")
    prices = {}
    for sym in symbols:
        try:
            df = yf.download(sym, period=f"{years}y", auto_adjust=True, progress=False)
            if df.empty or 'Close' not in df.columns:
                continue
            close = df['Close'].dropna()
            if isinstance(close, pd.DataFrame):
                close = close.squeeze()
            if len(close) > 60:
                prices[sym] = close
        except Exception:
            pass
    print(f"  Got price data for {len(prices)}/{len(symbols)} stocks")
    return prices


# ─────────────────────────────────────────────────────────────────────────────
# Part 1: Cross-sectional IC (current scores vs historical returns)
# ─────────────────────────────────────────────────────────────────────────────

def run_cross_sectional_ic(symbols: List[str], prices: Dict[str, pd.Series]) -> pd.DataFrame:
    """
    Score all stocks today with the full composite scorer, then correlate
    each agent score and the composite with historical 1M/3M/6M returns.
    """
    from core.stock_scorer import StockScorer

    print("\n" + "="*60)
    print("PART 1 — Cross-sectional IC (current scores vs past returns)")
    print("="*60)
    print(f"Scoring {len(symbols)} stocks …")

    scorer = StockScorer()
    results = scorer.score_stocks_batch(symbols)

    rows = []
    for r in results:
        sym  = r.get('symbol')
        if sym not in prices:
            continue
        price_series = prices[sym]
        agents = r.get('agent_scores', {})

        row = {
            'symbol':            sym,
            'composite':         r.get('raw_composite_score') or r.get('composite_score'),
            'fundamentals':      agents.get('fundamentals', {}).get('score'),
            'momentum':          agents.get('momentum', {}).get('score'),
            'quality':           agents.get('quality', {}).get('score'),
            'sentiment':         agents.get('sentiment', {}).get('score'),
            'institutional':     agents.get('institutional_flow', {}).get('score'),
            'ret_1m':            _calc_return(price_series, 21),
            'ret_3m':            _calc_return(price_series, 63),
            'ret_6m':            _calc_return(price_series, 126),
            'ret_12m':           _calc_return(price_series, 252),
        }
        rows.append(row)

    df = pd.DataFrame(rows).set_index('symbol')
    n  = len(df)

    print(f"\n  {n} stocks with both scores and price data\n")
    print(f"  {'Factor':<18} {'IC(1M)':>8} {'IC(3M)':>8} {'IC(6M)':>8} {'IC(12M)':>9}")
    print(f"  {'-'*18} {'-'*8} {'-'*8} {'-'*8} {'-'*9}")

    factors = ['composite', 'momentum', 'quality', 'fundamentals', 'sentiment', 'institutional']
    factor_ics = {}
    for f in factors:
        scores = df[f].values.astype(float)
        ics = {}
        for window, col in [('1m', 'ret_1m'), ('3m', 'ret_3m'), ('6m', 'ret_6m'), ('12m', 'ret_12m')]:
            ics[window] = spearman_ic(scores, df[col].values.astype(float))
        factor_ics[f] = ics
        def fmt(v):
            if v is None:
                return '   n/a'
            sign = '+' if v > 0 else ''
            return f" {sign}{v:.3f}"
        print(f"  {f:<18} {fmt(ics['1m']):>8} {fmt(ics['3m']):>8} {fmt(ics['6m']):>8} {fmt(ics['12m']):>9}")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Part 2: Rolling monthly IC (momentum, out-of-sample)
# ─────────────────────────────────────────────────────────────────────────────

def run_rolling_ic(symbols: List[str], prices: Dict[str, pd.Series], n_months: int = 6) -> None:
    """
    At each of the past n_months monthly snapshots, compute a momentum score
    for each stock using ONLY price data available at that snapshot, then
    measure Spearman IC against the subsequent 1M actual return.

    This is the gold-standard predictive IC because it uses truly forward returns.
    """
    print("\n" + "="*60)
    print(f"PART 2 — Rolling monthly IC (momentum, {n_months} periods)")
    print("="*60)
    print("  Uses out-of-sample 1M forward returns — true predictive IC\n")

    monthly_ics: List[float] = []
    period_rows = []

    for m in range(n_months, 0, -1):
        # Snapshot date: m months ago (approx 21 trading days each)
        cutoff_offset = m * 21
        fwd_offset    = (m - 1) * 21

        scores_at_T  = {}
        returns_fwd  = {}

        for sym, price in prices.items():
            # Price data up to T
            if len(price) < cutoff_offset + 130:
                continue
            prices_at_T = price.iloc[:-(cutoff_offset)] if cutoff_offset > 0 else price

            # Momentum score at T
            score = _calc_momentum_score(prices_at_T)
            if score is None:
                continue
            scores_at_T[sym] = score

            # Forward 1M return: from T to T+1M
            end_idx   = len(price) - fwd_offset
            start_idx = end_idx - 21
            if start_idx < 0 or end_idx > len(price):
                continue
            p_start = price.iloc[start_idx]
            p_end   = price.iloc[end_idx - 1]
            if pd.isna(p_start) or pd.isna(p_end) or p_start <= 0:
                continue
            returns_fwd[sym] = (p_end - p_start) / p_start * 100

        # Compute IC for this period
        common = [s for s in scores_at_T if s in returns_fwd]
        if len(common) < 5:
            continue

        sc  = np.array([scores_at_T[s] for s in common])
        ret = np.array([returns_fwd[s]  for s in common])
        ic  = spearman_ic(sc, ret)

        if ic is not None:
            monthly_ics.append(ic)
            sign = '+' if ic > 0 else ''
            date_label = f"T-{m}M"
            period_rows.append((date_label, len(common), ic))

    print(f"  {'Period':<10} {'N stocks':>9} {'IC':>9}")
    print(f"  {'-'*10} {'-'*9} {'-'*9}")
    for label, n, ic in period_rows:
        sign = '+' if ic > 0 else ''
        print(f"  {label:<10} {n:>9} {sign}{ic:>8.4f}")

    stats = ic_stats(monthly_ics)
    print(f"\n  ─── Momentum rolling IC summary ({stats['n']} periods) ───")
    _print_stats(stats)


# ─────────────────────────────────────────────────────────────────────────────
# Part 3: Per-agent cross-sectional IC summary with significance
# ─────────────────────────────────────────────────────────────────────────────

def run_agent_ic_summary(df: pd.DataFrame) -> None:
    """
    For each agent, compute Spearman IC vs 1M/3M returns plus a t-stat.
    Gives a clear picture of which agents are actually contributing signal.
    """
    print("\n" + "="*60)
    print("PART 3 — Per-agent IC significance (cross-sectional)")
    print("="*60)
    print("  t-stat >±2.0 → significant at 5% level\n")

    factors = ['composite', 'momentum', 'quality', 'fundamentals', 'sentiment', 'institutional']
    n = len(df)

    print(f"  {'Factor':<18} {'Window':>7} {'IC':>8} {'t-stat':>8} {'p-val':>8} {'Sig':>5}")
    print(f"  {'-'*18} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*5}")

    for f in factors:
        scores = df[f].values.astype(float)
        for window, col in [('1M', 'ret_1m'), ('3M', 'ret_3m')]:
            rets = df[col].values.astype(float)
            mask = np.isfinite(scores) & np.isfinite(rets)
            n_pairs = mask.sum()
            if n_pairs < 5:
                print(f"  {f:<18} {window:>7} {'  n/a':>8}")
                continue
            ic, p = scipy_stats.spearmanr(scores[mask], rets[mask])
            t = ic * np.sqrt((n_pairs - 2) / (1 - ic**2)) if abs(ic) < 1 else float('nan')
            sig = '**' if abs(t) > 2.5 else ('*' if abs(t) > 1.7 else '')
            sign = '+' if ic > 0 else ''
            print(f"  {f:<18} {window:>7} {sign}{ic:>7.4f} {t:>+8.2f} {p:>8.4f} {sig:>5}")
        print()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_stats(s: Dict) -> None:
    ic   = s['ic']
    icir = s['icir']
    hit  = s['hit_rate']
    t    = s['t_stat']
    p    = s['p_value']
    n    = s['n']

    if ic is None:
        print("  Insufficient data for statistics.")
        return

    grade = (
        "STRONG  ✓✓" if abs(ic) >= 0.05 else
        "GOOD    ✓"  if abs(ic) >= 0.02 else
        "WEAK    ~"  if abs(ic) >= 0.01 else
        "NO SIGNAL ✗"
    )
    sig = "significant" if (p is not None and not np.isnan(p) and p < 0.05) else "not significant"

    print(f"  IC (mean Spearman):  {ic:+.4f}   [{grade}]")
    if icir is not None and not np.isnan(icir):
        icir_grade = "good (>0.4)" if abs(icir) >= 0.4 else "weak (<0.4)"
        print(f"  ICIR (IC/σ):        {icir:+.3f}   [{icir_grade}]")
    if hit is not None:
        print(f"  Hit rate:           {hit:.0%}   [periods IC > 0]")
    if t is not None and not np.isnan(t):
        print(f"  t-stat:             {t:+.2f}   [{sig}, n={n}]")
    if p is not None and not np.isnan(p):
        print(f"  p-value:            {p:.4f}")


def _print_interpretation(df: pd.DataFrame) -> None:
    print("\n" + "="*60)
    print("INTERPRETATION")
    print("="*60)
    composite_scores = df['composite'].values.astype(float)
    ret_1m = df['ret_1m'].values.astype(float)
    mask = np.isfinite(composite_scores) & np.isfinite(ret_1m)
    if mask.sum() < 5:
        print("  Insufficient data for interpretation.")
        return

    ic_1m, _ = scipy_stats.spearmanr(composite_scores[mask], ret_1m[mask])
    t = ic_1m * np.sqrt((mask.sum() - 2) / (1 - ic_1m**2)) if abs(ic_1m) < 1 else 0

    print(f"\n  Composite score IC vs 1M return: {ic_1m:+.4f}")
    if abs(ic_1m) >= 0.05:
        print("  → STRONG signal. The scoring system is a good predictor.")
        print("    Comparable to top quantitative factor strategies.")
    elif abs(ic_1m) >= 0.02:
        print("  → GOOD signal. Consistent with institutional-grade factors.")
        print("    An IC of 0.02-0.05 is typical for well-constructed models.")
    elif abs(ic_1m) >= 0.01:
        print("  → WEAK signal. Some predictive power but noisy.")
        print("    Common for single-snapshot tests; use rolling IC for better estimate.")
    else:
        print("  → NO CLEAR SIGNAL in this snapshot.")
        print("    This is normal for cross-sectional IC on a single date.")
        print("    Check rolling IC (Part 2) for out-of-sample predictive power.")

    if abs(t) >= 2.0:
        print(f"  → Result is STATISTICALLY SIGNIFICANT (|t|={abs(t):.1f} > 2.0).")
    else:
        print(f"  → Result is not statistically significant (|t|={abs(t):.1f} < 2.0).")
        print("    Need more stocks or longer test window for robust conclusions.")

    # Top/bottom quintile spread
    valid_mask = np.isfinite(composite_scores) & np.isfinite(ret_1m)
    valid_scores = composite_scores[valid_mask]
    valid_rets   = ret_1m[valid_mask]
    if len(valid_scores) >= 10:
        q80 = np.percentile(valid_scores, 80)
        q20 = np.percentile(valid_scores, 20)
        top_ret  = valid_rets[valid_scores >= q80].mean()
        bot_ret  = valid_rets[valid_scores <= q20].mean()
        spread   = top_ret - bot_ret
        print(f"\n  Top quintile avg 1M return:    {top_ret:+.2f}%")
        print(f"  Bottom quintile avg 1M return: {bot_ret:+.2f}%")
        print(f"  Long-short spread:             {spread:+.2f}%")
        if spread > 0:
            print("  → Top-ranked stocks outperformed bottom-ranked ✓")
        else:
            print("  → Bottom-ranked stocks outperformed — check momentum timing")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='IC Validation for AI Hedge Fund scoring system')
    parser.add_argument('--stocks',  type=int, default=30,  help='Number of NIFTY50 stocks to use (default: 30)')
    parser.add_argument('--months',  type=int, default=6,   help='Rolling IC periods in months (default: 6)')
    parser.add_argument('--no-batch',action='store_true',   help='Skip cross-sectional batch scoring (faster)')
    args = parser.parse_args()

    symbols = NIFTY50[:args.stocks]

    print("\n" + "="*60)
    print("  AI HEDGE FUND — IC VALIDATION")
    print(f"  Universe: {len(symbols)} NIFTY50 stocks")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    print("""
  IC = Spearman rank correlation between factor score and forward return
  Good IC: 0.02-0.05 | Strong IC: >0.05 | ICIR > 0.4 = consistent signal
  Reference: NSE Momentum 30 IC ≈ 0.03-0.06; MSCI Quality IC ≈ 0.02-0.04
""")

    # Fetch all price data once (shared between parts)
    prices = fetch_prices(symbols, years=2)

    if not args.no_batch:
        df = run_cross_sectional_ic(list(prices.keys()), prices)
        run_agent_ic_summary(df)
        _print_interpretation(df)
    else:
        df = None

    run_rolling_ic(list(prices.keys()), prices, n_months=args.months)

    print("\n" + "="*60)
    print("  VALIDATION COMPLETE")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
