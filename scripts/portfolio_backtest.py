#!/usr/bin/env python3
"""
Portfolio Backtest — 3-Year Simulation

Simulates a monthly-rebalanced long-only portfolio using the AI scoring system
on NIFTY50 stocks and compares against the NIFTY50 index benchmark.

Methodology:
  • Universe   : NIFTY50 stocks
  • Rebalance  : monthly (last trading day of each month)
  • Selection  : top N stocks by composite score, equal-weighted
  • Scoring    : momentum-based (price-only, fully historically valid)
                 quality uses current yfinance fundamentals as constant proxy
                 (acceptable approximation for large-cap NIFTY stocks over 3Y)
  • Costs      : 0.1% per trade (brokerage + STT + slippage estimate)
  • Benchmark  : NIFTY50 index (^NSEI)

Metrics reported:
  CAGR, Total Return, Sharpe Ratio, Max Drawdown, Calmar Ratio,
  Win Rate (vs benchmark), Alpha, Beta, year-by-year breakdown,
  monthly returns table, drawdown chart

Usage:
    python scripts/portfolio_backtest.py
    python scripts/portfolio_backtest.py --years 3 --top 10
    python scripts/portfolio_backtest.py --years 2 --top 5 --no-costs
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
BENCHMARK = '^NSEI'

TRANSACTION_COST = 0.001   # 0.1% per trade (round-trip = 0.2%)
SECTOR_CAP_DEFAULT = 0.30  # max 30% of portfolio in any one sector

# Sector labels for NIFTY50 (used for concentration cap)
NIFTY50_SECTORS: Dict[str, str] = {
    'RELIANCE.NS':    'Energy',
    'ONGC.NS':        'Energy',
    'BPCL.NS':        'Energy',
    'COALINDIA.NS':   'Energy',
    'NTPC.NS':        'Energy',
    'POWERGRID.NS':   'Energy',
    'TCS.NS':         'IT',
    'INFY.NS':        'IT',
    'WIPRO.NS':       'IT',
    'HCLTECH.NS':     'IT',
    'TECHM.NS':       'IT',
    'LTIM.NS':        'IT',
    'HDFCBANK.NS':    'Financials',
    'ICICIBANK.NS':   'Financials',
    'SBIN.NS':        'Financials',
    'AXISBANK.NS':    'Financials',
    'KOTAKBANK.NS':   'Financials',
    'BAJFINANCE.NS':  'Financials',
    'BAJAJFINSV.NS':  'Financials',
    'SBILIFE.NS':     'Financials',
    'HDFCLIFE.NS':    'Financials',
    'INDUSINDBK.NS':  'Financials',
    'HINDUNILVR.NS':  'FMCG',
    'ITC.NS':         'FMCG',
    'NESTLEIND.NS':   'FMCG',
    'BRITANNIA.NS':   'FMCG',
    'TATACONSUM.NS':  'FMCG',
    'SUNPHARMA.NS':   'Pharma',
    'DIVISLAB.NS':    'Pharma',
    'CIPLA.NS':       'Pharma',
    'DRREDDY.NS':     'Pharma',
    'APOLLOHOSP.NS':  'Pharma',
    'TATAMOTORS.NS':  'Auto',
    'MARUTI.NS':      'Auto',
    'HEROMOTOCO.NS':  'Auto',
    'EICHERMOT.NS':   'Auto',
    'BAJAJ-AUTO.NS':  'Auto',
    'M&M.NS':         'Auto',
    'JSWSTEEL.NS':    'Metals',
    'TATASTEEL.NS':   'Metals',
    'HINDALCO.NS':    'Metals',
    'LT.NS':          'Industrials',
    'ADANIPORTS.NS':  'Industrials',
    'ADANIENT.NS':    'Industrials',
    'GRASIM.NS':      'Construction',
    'ULTRACEMCO.NS':  'Construction',
    'ASIANPAINT.NS':  'Consumer',
    'TITAN.NS':       'Consumer',
    'BHARTIARTL.NS':  'Telecom',
}


# ─────────────────────────────────────────────────────────────────────────────
# Data fetching
# ─────────────────────────────────────────────────────────────────────────────

def fetch_all_prices(symbols: List[str], years: int) -> Tuple[Dict[str, pd.Series], pd.Series]:
    """Returns dict of Close series per symbol + benchmark series."""
    import yfinance as yf

    all_syms = symbols + [BENCHMARK]
    print(f"  Fetching {years}Y price history for {len(symbols)} stocks + benchmark …")
    raw = yf.download(all_syms, period=f"{years}y", auto_adjust=True, progress=False)

    prices: Dict[str, pd.Series] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw['Close']
        for sym in symbols:
            if sym in close.columns and not close[sym].dropna().empty:
                prices[sym] = close[sym].dropna()
        bench = close[BENCHMARK].dropna() if BENCHMARK in close.columns else pd.Series(dtype=float)
    else:
        # Single-ticker fallback
        prices[symbols[0]] = raw['Close'].dropna()
        bench = pd.Series(dtype=float)

    print(f"  Got {len(prices)}/{len(symbols)} stocks  |  "
          f"benchmark {'OK' if not bench.empty else 'MISSING'}")
    return prices, bench


def get_quality_snapshot(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch current ROE and D/E from yfinance as a constant proxy for quality.
    For large-cap NIFTY50 stocks, fundamentals are relatively stable over 3Y.
    """
    import yfinance as yf
    quality: Dict[str, float] = {}
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            roe = info.get('returnOnEquity')
            dte = info.get('debtToEquity')
            # Simplified quality score 0-100
            roe_s = 0 if roe is None else min(40, max(0, roe * 100 / 25 * 40))
            dte_s = 18 if dte is None else max(2, 35 - min(33, (dte / 100) * 35))
            quality[sym] = round(roe_s + dte_s, 1)
        except Exception:
            quality[sym] = 25.0   # neutral
    return quality


# ─────────────────────────────────────────────────────────────────────────────
# Scoring at a historical date
# ─────────────────────────────────────────────────────────────────────────────

def momentum_score_at(prices: pd.Series, as_of_idx: int) -> Optional[float]:
    """Compute momentum score using only price data up to and including as_of_idx."""
    hist = prices.iloc[:as_of_idx + 1]
    n = len(hist)

    def ret(days: int) -> Optional[float]:
        if n < days + 1: return None
        p0, p1 = hist.iloc[-(days + 1)], hist.iloc[-1]
        return (p1 - p0) / p0 if p0 > 0 else None

    r1, r3, r6, r12 = ret(21), ret(63), ret(126), ret(252)

    def score_r(r: Optional[float], t1: float, t2: float, t3: float) -> float:
        if r is None: return 0.25
        if r >= t1: return 1.0
        if r >= t2: return 0.75
        if r >= t3: return 0.5
        if r >= 0:  return 0.25
        if r >= -0.10: return 0.10
        return 0.0

    components = [
        score_r(r1,  0.05, 0.02,  0.0) * 0.25,
        score_r(r3,  0.10, 0.05,  0.0) * 0.30,
        score_r(r6,  0.20, 0.10,  0.0) * 0.30,
        score_r(r12, 0.30, 0.15,  0.0) * 0.15,
    ]
    return sum(components) * 100


def composite_score_at(
    sym: str,
    prices: pd.Series,
    as_of_idx: int,
    quality_map: Dict[str, float],
    regime_momentum_weight: float = 0.60,
    regime_quality_weight: float = 0.40,
) -> Optional[float]:
    """
    Composite = regime_momentum_weight * momentum + regime_quality_weight * quality_proxy.
    Weights shift by regime (same logic as adaptive weights, simplified for backtest).
    """
    mom = momentum_score_at(prices, as_of_idx)
    if mom is None:
        return None
    qual = quality_map.get(sym, 25.0)
    return regime_momentum_weight * mom + regime_quality_weight * qual


def detect_regime_at(nifty_prices: pd.Series, as_of_idx: int) -> Tuple[str, float, float]:
    """
    Returns (regime_str, momentum_weight, quality_weight) at as_of_idx.
    Regime determined by SMA50 vs SMA200 on NIFTY index.
    """
    hist = nifty_prices.iloc[:as_of_idx + 1]
    if len(hist) < 200:
        return 'SIDEWAYS', 0.55, 0.45

    sma50  = hist.iloc[-50:].mean()
    sma200 = hist.iloc[-200:].mean()
    price  = hist.iloc[-1]
    gap_pct = (sma50 - sma200) / sma200  # positive = bull

    # Confidence-blended weights (mirrors market_regime_service logic)
    confidence = min(1.0, abs(gap_pct) / 0.05)
    confidence = max(0.3, confidence)   # floor

    if gap_pct > 0.02 and price > sma50 * 1.01:
        # Bull: momentum-dominant
        base_mom = 0.65; base_qual = 0.35
        regime = 'BULL'
    elif gap_pct < -0.02 and price < sma50 * 0.99:
        # Bear: quality-dominant
        base_mom = 0.35; base_qual = 0.65
        regime = 'BEAR'
    else:
        base_mom = 0.55; base_qual = 0.45
        regime = 'SIDEWAYS'

    # Blend toward neutral (0.55/0.45) for low-confidence signals
    neutral_mom, neutral_qual = 0.55, 0.45
    mom_w  = confidence * base_mom  + (1 - confidence) * neutral_mom
    qual_w = confidence * base_qual + (1 - confidence) * neutral_qual
    return regime, round(mom_w, 3), round(qual_w, 3)


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio construction
# ─────────────────────────────────────────────────────────────────────────────

def get_rebalance_dates(prices: Dict[str, pd.Series], bench: pd.Series) -> List[pd.Timestamp]:
    """Last trading day of each calendar month within common price history."""
    all_dates = bench.index if not bench.empty else list(prices.values())[0].index
    df = pd.DataFrame({'date': all_dates})
    df['ym'] = df['date'].dt.to_period('M')
    last_days = df.groupby('ym')['date'].max().tolist()
    return sorted(last_days)


# ─────────────────────────────────────────────────────────────────────────────
# Main simulation
# ─────────────────────────────────────────────────────────────────────────────

def apply_sector_cap(
    scored: List[Tuple[str, float]],
    top_n: int,
    sector_cap: float,
) -> List[Tuple[str, float]]:
    """
    Select top_n stocks from a score-sorted list, capping sector exposure.
    sector_cap = max fraction of portfolio in any one sector (e.g. 0.30 → 3/10).
    """
    max_per_sector = max(1, int(top_n * sector_cap))
    sector_counts: Dict[str, int] = {}
    selected: List[Tuple[str, float]] = []
    for sym, score in scored:
        if len(selected) >= top_n:
            break
        sector = NIFTY50_SECTORS.get(sym, 'Other')
        if sector_counts.get(sector, 0) < max_per_sector:
            selected.append((sym, score))
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
    # If capping leaves us short, fill remaining slots uncapped
    if len(selected) < top_n:
        picked = {s for s, _ in selected}
        for sym, score in scored:
            if len(selected) >= top_n:
                break
            if sym not in picked:
                selected.append((sym, score))
    return selected


def run_simulation(
    prices: Dict[str, pd.Series],
    bench: pd.Series,
    quality_map: Dict[str, float],
    top_n: int,
    transaction_cost: float,
    sector_cap: float = 0.0,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Returns (portfolio_value_series, trade_log_df).
    portfolio_value_series is indexed by rebalance date, starting at 100.
    """
    rebal_dates = get_rebalance_dates(prices, bench)
    if len(rebal_dates) < 2:
        raise ValueError("Not enough rebalance dates")

    bench_at = {d: bench.get(d) for d in rebal_dates}

    portfolio_values: List[Tuple[pd.Timestamp, float]] = [(rebal_dates[0], 100.0)]
    holdings: Dict[str, float] = {}   # sym → weight
    pv = 100.0

    trade_log: List[Dict] = []

    for i in range(len(rebal_dates) - 1):
        date_t  = rebal_dates[i]
        date_t1 = rebal_dates[i + 1]

        # ── Score all stocks at date_t ──────────────────────────────────────
        # Find benchmark index position for regime detection
        bench_idx = bench.index.get_indexer([date_t], method='ffill')[0]
        regime, mom_w, qual_w = detect_regime_at(bench, bench_idx) if bench_idx >= 0 else ('SIDEWAYS', 0.55, 0.45)

        scored: List[Tuple[str, float]] = []
        for sym, price_series in prices.items():
            idx = price_series.index.get_indexer([date_t], method='ffill')[0]
            if idx < 63:   # need at least 3M of data
                continue
            score = composite_score_at(sym, price_series, idx, quality_map, mom_w, qual_w)
            if score is not None:
                scored.append((sym, score))

        if len(scored) < top_n:
            # Not enough stocks — carry forward
            portfolio_values.append((date_t1, pv))
            continue

        scored.sort(key=lambda x: x[1], reverse=True)
        if sector_cap > 0:
            selected = apply_sector_cap(scored, top_n, sector_cap)
        else:
            selected = scored[:top_n]
        new_holdings = {sym: 1.0 / top_n for sym, _ in selected}

        # ── Transaction costs on turnover ──────────────────────────────────
        old_syms = set(holdings.keys())
        new_syms = set(new_holdings.keys())
        turnover = len(old_syms.symmetric_difference(new_syms)) / max(len(old_syms | new_syms), 1)
        cost = turnover * transaction_cost

        # ── Compute portfolio return from t to t+1 ─────────────────────────
        port_ret = 0.0
        for sym, w in new_holdings.items():
            p_series = prices[sym]
            idx_t  = p_series.index.get_indexer([date_t],  method='ffill')[0]
            idx_t1 = p_series.index.get_indexer([date_t1], method='ffill')[0]
            if idx_t < 0 or idx_t1 < 0 or idx_t1 <= idx_t:
                continue
            p0 = p_series.iloc[idx_t]
            p1 = p_series.iloc[idx_t1]
            if p0 > 0:
                port_ret += w * (p1 - p0) / p0

        port_ret -= cost
        pv = pv * (1 + port_ret)
        portfolio_values.append((date_t1, round(pv, 4)))

        # Benchmark return this period
        b0 = bench_at.get(date_t) or bench.iloc[bench_idx] if bench_idx >= 0 else None
        b_idx_t1 = bench.index.get_indexer([date_t1], method='ffill')[0]
        b1 = bench.iloc[b_idx_t1] if b_idx_t1 >= 0 else None
        bench_ret = (b1 - b0) / b0 if (b0 and b1 and b0 > 0) else None

        trade_log.append({
            'date':         date_t.strftime('%Y-%m'),
            'regime':       regime,
            'top_stocks':   ', '.join(s.replace('.NS', '') for s, _ in selected),
            'port_ret_pct': round(port_ret * 100, 2),
            'bench_ret_pct': round(bench_ret * 100, 2) if bench_ret else None,
            'alpha_pct':    round((port_ret - (bench_ret or 0)) * 100, 2),
            'pv':           round(pv, 2),
            'turnover_pct': round(turnover * 100, 1),
        })

        holdings = new_holdings

    pv_series = pd.Series(
        {d: v for d, v in portfolio_values},
        name='portfolio'
    )
    return pv_series, pd.DataFrame(trade_log)


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(pv: pd.Series, bench: pd.Series, risk_free: float = 0.065) -> Dict:
    """Compute CAGR, Sharpe, Max Drawdown, Calmar, Alpha, Beta, Win Rate."""
    returns = pv.pct_change().dropna()
    n_months = len(returns)
    n_years  = n_months / 12

    total_ret = (pv.iloc[-1] / pv.iloc[0]) - 1
    cagr = (1 + total_ret) ** (1 / n_years) - 1 if n_years > 0 else 0

    ann_std = returns.std() * np.sqrt(12)
    monthly_rf = (1 + risk_free) ** (1/12) - 1
    excess = returns - monthly_rf
    sharpe = (excess.mean() / returns.std() * np.sqrt(12)) if returns.std() > 0 else 0

    rolling_max = pv.cummax()
    drawdown = (pv - rolling_max) / rolling_max
    max_dd = drawdown.min()
    calmar = cagr / abs(max_dd) if max_dd != 0 else float('nan')

    # Align benchmark returns
    bench_ret = bench.pct_change().dropna()
    common_idx = returns.index.intersection(bench_ret.index)
    if len(common_idx) >= 6:
        pr = returns.loc[common_idx].values
        br = bench_ret.loc[common_idx].values
        beta, alpha_monthly, _, _, _ = scipy_stats.linregress(br, pr)
        alpha_ann = (1 + alpha_monthly) ** 12 - 1
        bench_total = (bench.iloc[-1] / bench.iloc[0]) - 1
        bench_cagr  = (1 + bench_total) ** (1 / n_years) - 1 if n_years > 0 else 0
        win_rate = np.mean(pr > br)
    else:
        beta, alpha_ann, bench_total, bench_cagr, win_rate = 0, 0, 0, 0, 0.5

    return {
        'total_return':  total_ret,
        'cagr':          cagr,
        'ann_std':       ann_std,
        'sharpe':        sharpe,
        'max_drawdown':  max_dd,
        'calmar':        calmar,
        'alpha_ann':     alpha_ann,
        'beta':          beta,
        'win_rate':      win_rate,
        'n_months':      n_months,
        'bench_total':   bench_total,
        'bench_cagr':    bench_cagr,
    }


def bench_metrics(bench: pd.Series, risk_free: float = 0.065) -> Dict:
    n_years = len(bench) / 252
    total   = (bench.iloc[-1] / bench.iloc[0]) - 1
    cagr    = (1 + total) ** (1 / n_years) - 1 if n_years > 0 else 0
    ret     = bench.pct_change().dropna()
    mret    = ret.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    std     = mret.std() * np.sqrt(12)
    rf_m    = (1 + risk_free) ** (1/12) - 1
    sharpe  = ((mret - rf_m).mean() / mret.std() * np.sqrt(12)) if mret.std() > 0 else 0
    rolling = bench.cummax()
    dd      = ((bench - rolling) / rolling).min()
    return {'total': total, 'cagr': cagr, 'sharpe': sharpe, 'max_dd': dd, 'std': std}


# ─────────────────────────────────────────────────────────────────────────────
# Printing
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(m: Dict, bm: Dict, pv: pd.Series, bench: pd.Series, log: pd.DataFrame, top_n: int):
    sep = "=" * 64
    print(f"\n{sep}")
    print(f"  PORTFOLIO BACKTEST RESULTS — Top-{top_n} NIFTY50 Strategy")
    print(sep)

    print(f"\n  {'Metric':<28} {'Strategy':>12} {'NIFTY50':>12} {'Edge':>10}")
    print(f"  {'-'*28} {'-'*12} {'-'*12} {'-'*10}")

    def row(label, s_val, b_val, fmt='.1%', higher_better=True):
        edge = s_val - b_val
        sign = '+' if edge >= 0 else ''
        arrow = '✓' if (edge > 0 and higher_better) or (edge < 0 and not higher_better) else '✗'
        s_str = format(s_val, fmt)
        b_str = format(b_val, fmt)
        e_str = format(edge, fmt)
        print(f"  {label:<28} {s_str:>12} {b_str:>12} {sign}{e_str}{arrow:>5}")

    row('Total Return (3Y)',     m['total_return'], bm['total'])
    row('CAGR',                  m['cagr'],         bm['cagr'])
    row('Sharpe Ratio',          m['sharpe'],       bm['sharpe'], fmt='.2f')
    row('Max Drawdown',          m['max_drawdown'], bm['max_dd'], higher_better=False)
    row('Annualised Volatility', m['ann_std'],      bm['std'],   higher_better=False)
    print(f"  {'Calmar Ratio':<28} {m['calmar']:>12.2f}")
    print(f"  {'Alpha (annualised)':<28} {m['alpha_ann']:>+12.1%}")
    print(f"  {'Beta vs NIFTY50':<28} {m['beta']:>12.2f}")
    print(f"  {'Monthly Win Rate vs NIFTY':<28} {m['win_rate']:>12.1%}")
    print(f"  {'Backtest months':<28} {m['n_months']:>12}")

    # Year-by-year breakdown
    print(f"\n  ─── Year-by-Year Performance ───")
    print(f"  {'Year':<8} {'Strategy':>10} {'NIFTY50':>10} {'Alpha':>9}")
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*9}")
    pv_m  = pv.resample('YE').last()
    ben_m = bench.resample('YE').last()
    for yr in pv_m.index:
        yr_label = str(yr.year)
        prev_yr  = yr - pd.DateOffset(years=1)
        pv_prev  = pv.asof(prev_yr)
        bn_prev  = bench.asof(prev_yr)
        pv_now   = pv_m.get(yr)
        bn_now   = ben_m.get(yr)
        if pv_prev and pv_now and bn_prev and bn_now and pv_prev > 0 and bn_prev > 0:
            sr = (pv_now - pv_prev) / pv_prev
            br = (bn_now - bn_prev) / bn_prev
            sign = '+' if sr > 0 else ''
            print(f"  {yr_label:<8} {sign}{sr:>9.1%} {br:>+9.1%} {(sr-br):>+8.1%}")

    # Monthly returns table (last 24 months)
    print(f"\n  ─── Monthly Returns (Strategy vs NIFTY50, last 24 months) ───")
    print(f"  {'Month':<10} {'Strategy':>9} {'NIFTY50':>9} {'Alpha':>8}  Holdings")
    print(f"  {'-'*10} {'-'*9} {'-'*9} {'-'*8}  {'-'*30}")
    recent = log.tail(24)
    for _, row_d in recent.iterrows():
        pr = row_d['port_ret_pct']
        br = row_d['bench_ret_pct']
        al = row_d['alpha_pct']
        ps = '+' if pr >= 0 else ''
        bs = '+' if (br or 0) >= 0 else ''
        als = '+' if al >= 0 else ''
        stocks = row_d['top_stocks'][:40]
        br_str = f"{bs}{br:.1f}%" if br is not None else '  n/a'
        print(f"  {row_d['date']:<10} {ps}{pr:>7.1f}% {br_str:>9} {als}{al:>6.1f}%  {stocks}")

    # Simple drawdown summary
    pv_monthly = pv.resample('ME').last()
    rolling_max = pv_monthly.cummax()
    dd_series   = (pv_monthly - rolling_max) / rolling_max * 100
    print(f"\n  ─── Drawdown Summary ───")
    print(f"  Max drawdown     : {dd_series.min():.1f}%  ({dd_series.idxmin().strftime('%Y-%m')})")
    print(f"  Current drawdown : {dd_series.iloc[-1]:.1f}%")
    in_dd = dd_series[dd_series < -5]
    print(f"  Months >5% below peak : {len(in_dd)} / {len(dd_series)}")


# ─────────────────────────────────────────────────────────────────────────────
# Results log — append every run to a CSV for side-by-side comparison
# ─────────────────────────────────────────────────────────────────────────────

RESULTS_LOG = Path(__file__).parent / 'backtest_results.csv'

def save_run_result(name: str, config: Dict, m: Dict, bm: Dict) -> None:
    """Append this run's key metrics to backtest_results.csv."""
    row = {
        'run_at':        datetime.now().strftime('%Y-%m-%d %H:%M'),
        'name':          name,
        'years':         config['years'],
        'top_n':         config['top_n'],
        'sector_cap_pct': int(config['sector_cap'] * 100),
        'quality':       'yes' if config['quality'] else 'no',
        'costs':         'yes' if config['costs'] else 'no',
        # Strategy
        'total_return_pct':   round(m['total_return'] * 100, 1),
        'cagr_pct':           round(m['cagr'] * 100, 1),
        'sharpe':             round(m['sharpe'], 2),
        'max_drawdown_pct':   round(m['max_drawdown'] * 100, 1),
        'alpha_ann_pct':      round(m['alpha_ann'] * 100, 1),
        'beta':               round(m['beta'], 2),
        'win_rate_pct':       round(m['win_rate'] * 100, 1),
        'ann_vol_pct':        round(m['ann_std'] * 100, 1),
        # Benchmark
        'nifty_return_pct':   round(bm['total'] * 100, 1),
        'nifty_cagr_pct':     round(bm['cagr'] * 100, 1),
        'nifty_sharpe':       round(bm['sharpe'], 2),
        'nifty_maxdd_pct':    round(bm['max_dd'] * 100, 1),
    }
    df_new = pd.DataFrame([row])
    if RESULTS_LOG.exists():
        df_old = pd.read_csv(RESULTS_LOG)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    df_all.to_csv(RESULTS_LOG, index=False)
    print(f"\n  ✓ Results saved → scripts/backtest_results.csv  (row #{len(df_all)})")


def print_comparison_table() -> None:
    """Print all saved runs side-by-side from backtest_results.csv."""
    if not RESULTS_LOG.exists():
        print("  No results saved yet. Run a backtest first.")
        return
    df = pd.read_csv(RESULTS_LOG)
    print(f"\n{'='*90}")
    print("  BACKTEST COMPARISON TABLE")
    print(f"{'='*90}")
    cols = ['name', 'years', 'top_n', 'sector_cap_pct', 'quality',
            'total_return_pct', 'cagr_pct', 'sharpe', 'max_drawdown_pct',
            'alpha_ann_pct', 'win_rate_pct', 'nifty_return_pct', 'nifty_cagr_pct']
    headers = ['Name', 'Yrs', 'TopN', 'SecCap%', 'Qual',
               'Return%', 'CAGR%', 'Sharpe', 'MaxDD%',
               'Alpha%', 'WinRate%', 'NIFTY%', 'NIFTY CAGR%']
    widths = [22, 4, 4, 7, 4, 8, 6, 6, 7, 7, 8, 7, 10]
    header_row = '  ' + '  '.join(f"{h:>{w}}" for h, w in zip(headers, widths))
    print(header_row)
    print('  ' + '-' * (sum(widths) + 2 * len(widths)))
    for _, row in df.iterrows():
        vals = [str(row.get(c, ''))[:w] for c, w in zip(cols, widths)]
        print('  ' + '  '.join(f"{v:>{w}}" for v, w in zip(vals, widths)))
    print(f"{'='*90}\n")
    print(f"  Full data: scripts/backtest_results.csv")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='3-Year Portfolio Backtest on NIFTY50')
    parser.add_argument('--years',    type=int,   default=3,     help='Backtest window in years (default: 3)')
    parser.add_argument('--top',      type=int,   default=10,    help='Stocks to hold per month (default: 10)')
    parser.add_argument('--no-costs',    action='store_true',                  help='Disable transaction costs')
    parser.add_argument('--no-quality',  action='store_true',                  help='Momentum-only scoring (skip quality fetch)')
    parser.add_argument('--sector-cap',  type=float, default=SECTOR_CAP_DEFAULT,
                        help=f'Max sector weight 0-1 (default: {SECTOR_CAP_DEFAULT}, 0=off)')
    parser.add_argument('--name',        type=str,   default='',
                        help='Label for this run (saved to results log)')
    parser.add_argument('--compare',     action='store_true',
                        help='Print comparison table of all saved runs and exit')
    args = parser.parse_args()

    if args.compare:
        print_comparison_table()
        return

    cost = 0.0 if args.no_costs else TRANSACTION_COST

    # Auto-generate run name if not provided
    run_name = args.name or (
        f"top{args.top}_"
        f"{'noQ_' if args.no_quality else ''}"
        f"sc{int(args.sector_cap*100)}_"
        f"{args.years}y"
    )

    print("\n" + "="*64)
    print("  AI HEDGE FUND — PORTFOLIO BACKTEST")
    print(f"  Run: {run_name}")
    print(f"  Universe: NIFTY50  |  Window: {args.years}Y  |  Top-{args.top} stocks")
    sector_cap_str = f"{int(args.sector_cap * 100)}% cap" if args.sector_cap > 0 else "no cap"
    print(f"  Rebalance: Monthly  |  Costs: {'none' if cost == 0 else '0.1% per trade'}  |  Sector: {sector_cap_str}")
    print("="*64)

    # Fetch prices
    prices, bench = fetch_all_prices(NIFTY50, years=args.years + 1)  # +1Y buffer for warmup

    if bench.empty:
        print("  WARNING: NIFTY50 benchmark data unavailable — relative metrics will be skipped")

    # Quality snapshot (current ROE/D-E as constant proxy)
    if args.no_quality:
        quality_map = {sym: 25.0 for sym in prices}
        print("  Quality: disabled (momentum-only mode)")
    else:
        print("\n  Fetching quality snapshot (ROE, D/E) …")
        quality_map = get_quality_snapshot(list(prices.keys()))
        print(f"  Got quality data for {sum(1 for v in quality_map.values() if v != 25.0)} stocks")

    # Trim to backtest window (drop warmup year)
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=args.years)
    prices_bt = {sym: s[s.index >= cutoff] for sym, s in prices.items() if not s[s.index >= cutoff].empty}
    bench_bt  = bench[bench.index >= cutoff] if not bench.empty else bench

    print(f"\n  Backtest window: {cutoff.strftime('%Y-%m')} → {pd.Timestamp.now().strftime('%Y-%m')}")
    print(f"  Stocks with data in window: {len(prices_bt)}")

    # Run simulation
    print(f"\n  Running monthly simulation (top-{args.top}) …")
    pv, trade_log = run_simulation(prices_bt, bench_bt, quality_map, args.top, cost, args.sector_cap)

    # Compute metrics
    bm = bench_metrics(bench_bt) if not bench_bt.empty else {
        'total': 0, 'cagr': 0, 'sharpe': 0, 'max_dd': 0, 'std': 0
    }

    # Align PV index with monthly for metrics
    pv_monthly = pv.resample('ME').last().dropna()
    bench_monthly = bench_bt.resample('ME').last().dropna() if not bench_bt.empty else pd.Series(dtype=float)
    m = compute_metrics(pv_monthly, bench_monthly)

    # Print results
    print_summary(m, bm, pv_monthly, bench_bt, trade_log, args.top)

    if not args.no_quality:
        print("\n" + "="*64)
        print("  NOTE: Quality scores use current fundamentals as a constant")
        print("  proxy. For large-cap NIFTY50 stocks this is a reasonable")
        print("  approximation but may slightly overstate quality signal.")
        print("  Run with --no-quality for a fully price-based backtest.")
        print("="*64 + "\n")

    # Save run to results log
    save_run_result(run_name, {
        'years':      args.years,
        'top_n':      args.top,
        'sector_cap': args.sector_cap,
        'quality':    not args.no_quality,
        'costs':      not args.no_costs,
    }, m, bm)

    print(f"  Run --compare to see all saved runs side-by-side.\n")


if __name__ == '__main__':
    main()
