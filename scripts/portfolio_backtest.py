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
  • Costs      : 0.27% per trade (27 bps: STT + brokerage + GST + stamp duty + exchange charges)
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
import json
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

TRANSACTION_COST = 0.0027  # 27 bps/side: STT 0.1% sell + brokerage + GST + stamp duty + exchange charges
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

# ── Macro overlay: USD/INR sector sensitivity (backtest sector names) ─────────
# Positive = benefits from INR depreciation (USD earner), negative = hurt by it
_BT_SECTOR_CURRENCY_SENS: Dict[str, float] = {
    'IT':     +1.0,   # large USD revenue exporters
    'Pharma': +0.5,   # significant USD export revenues
    'Metals': +0.4,   # commodity prices in USD, export-oriented
    'FMCG':   -0.3,   # import input costs rise with weak INR
    'Auto':   -0.2,   # commodity/input cost pressure
}

# ── Macro overlay: RBI rate cycle base adjustments (backtest sector names) ────
_BT_SECTOR_RBI_BASE: Dict[str, float] = {
    'Financials': 2.5,  # banks/NBFCs: NIM expansion on cuts
    'Auto':       1.5,  # EMIs cheaper on rate cuts
    'Consumer':   1.5,  # discretionary spending improves
    'FMCG':       0.8,  # rural credit/consumption
}
_RBI_MAX_ADJ_PTS = 3.0
_RBI_AMPLIFY_BPS = 50   # ≥50 bps in 6 months → 1.5× scale


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
# Macro overlay helpers (USD/INR + RBI rate cycle)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_usdinr_prices(years: int) -> pd.Series:
    """Pre-fetch USD/INR (INR=X) historical prices for macro overlay."""
    import yfinance as yf
    print(f"  Fetching USD/INR history …")
    raw = yf.download("INR=X", period=f"{years + 1}y", auto_adjust=True, progress=False)
    if raw.empty:
        print("  WARNING: USD/INR data unavailable — currency overlay disabled")
        return pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw['Close']
        col = 'INR=X' if 'INR=X' in close.columns else close.columns[0]
        series = close[col].dropna()
    else:
        series = raw['Close'].dropna()
    print(f"  USD/INR: {len(series)} trading days fetched")
    return series


def load_rbi_history() -> List[Dict]:
    """Load MPC decision history from rbi_rate_config.json."""
    config_path = project_root / 'data' / 'rbi_rate_config.json'
    try:
        with open(config_path) as f:
            data = json.load(f)
        return data.get('decision_history', [])
    except Exception:
        return []


def usdinr_adj_at(inr_prices: pd.Series, as_of_date: pd.Timestamp, sector: str) -> float:
    """Point-in-time USD/INR sector adjustment using price data up to as_of_date."""
    sensitivity = _BT_SECTOR_CURRENCY_SENS.get(sector, 0.0)
    if sensitivity == 0.0 or inr_prices.empty:
        return 0.0
    idx = inr_prices.index.get_indexer([as_of_date], method='ffill')[0]
    if idx < 20:
        return 0.0
    hist = inr_prices.iloc[:idx + 1]
    p_now = hist.iloc[-1]
    p_20d = hist.iloc[-20]
    if p_20d <= 0:
        return 0.0
    trend_pct = (p_now / p_20d - 1) * 100
    if abs(trend_pct) < 1.0:   # noise threshold
        return 0.0
    raw_adj = sensitivity * trend_pct * 0.6   # scale: 5% IT move → +3 pts
    return round(float(np.clip(raw_adj, -4.0, 4.0)), 2)


def rbi_adj_at(rbi_history: List[Dict], as_of_date: pd.Timestamp, sector: str) -> float:
    """
    Point-in-time RBI sector adjustment: only uses decisions on or before as_of_date.
    Returns 0 for pausing cycle or rate-agnostic sectors.
    """
    base = _BT_SECTOR_RBI_BASE.get(sector, 0.0)
    if base == 0.0 or not rbi_history:
        return 0.0
    as_of = as_of_date.date() if hasattr(as_of_date, 'date') else as_of_date
    past = [d for d in rbi_history
            if datetime.strptime(d['date'], '%Y-%m-%d').date() <= as_of]
    if len(past) < 2:
        return 0.0
    last2 = past[:2]  # history is newest-first
    actions = [d['action'] for d in last2]
    if 'cut' in actions and 'hike' not in actions:
        cycle = 'cutting'
    elif 'hike' in actions and 'cut' not in actions:
        cycle = 'hiking'
    else:
        return 0.0  # pausing
    cutoff = as_of - timedelta(days=182)
    recent = [d for d in past
              if datetime.strptime(d['date'], '%Y-%m-%d').date() >= cutoff]
    cum_bps = sum(d['bps'] for d in recent)
    direction = 1.0 if cycle == 'cutting' else -1.0
    scale = 1.5 if abs(cum_bps) >= _RBI_AMPLIFY_BPS else 1.0
    adj = direction * base * scale
    return round(float(np.clip(adj, -_RBI_MAX_ADJ_PTS, _RBI_MAX_ADJ_PTS)), 2)


def macro_adj_for_stock(
    sym: str,
    as_of_date: pd.Timestamp,
    inr_prices: pd.Series,
    rbi_history: List[Dict],
) -> float:
    """Combined USD/INR + RBI adjustment for a symbol at a point in time."""
    sector = NIFTY50_SECTORS.get(sym, 'Other')
    return usdinr_adj_at(inr_prices, as_of_date, sector) + rbi_adj_at(rbi_history, as_of_date, sector)


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


def rs_acceleration_score_at(
    prices: pd.Series,
    bench_prices: pd.Series,
    as_of_idx: int,
    bench_as_of_idx: int,
) -> float:
    """
    RS Acceleration = (3m RS vs NIFTY) - (6m RS vs NIFTY).
    Positive  → momentum building (early stage, good entry)
    Negative  → momentum fading  (extended run, mean-reversion risk)

    Returns an adjustment in range [-10, +10] pts to add to composite score.
    Threshold: only penalise when fading strongly (< -10pp) and only reward
    when building clearly (> +5pp). Noise below those levels → 0.
    """
    hist  = prices.iloc[:as_of_idx + 1]
    bench = bench_prices.iloc[:bench_as_of_idx + 1]

    if len(hist) < 127 or len(bench) < 127:
        return 0.0

    def pct(series, days):
        if len(series) < days + 1: return None
        p0 = series.iloc[-(days + 1)]
        return (series.iloc[-1] - p0) / p0 if p0 > 0 else None

    r3s = pct(hist,  63);  r6s = pct(hist,  126)
    r3b = pct(bench, 63);  r6b = pct(bench, 126)

    if any(v is None for v in [r3s, r6s, r3b, r6b]):
        return 0.0

    rs3 = (r3s - r3b) * 100   # stock 3m excess return vs NIFTY
    rs6 = (r6s - r6b) * 100   # stock 6m excess return vs NIFTY
    accel = rs3 - rs6          # positive = building, negative = fading

    if accel > 5:
        # Momentum building: +2 to +10 pts proportional to strength
        return float(np.clip(accel * 0.5, 2.0, 10.0))
    elif accel < -10:
        # Momentum fading strongly: -2 to -10 pts
        return float(np.clip(accel * 0.4, -10.0, -2.0))
    return 0.0


def composite_score_at(
    sym: str,
    prices: pd.Series,
    as_of_idx: int,
    quality_map: Dict[str, float],
    regime_momentum_weight: float = 0.60,
    regime_quality_weight: float = 0.40,
    macro_adj: float = 0.0,
    bench_prices: Optional[pd.Series] = None,
    bench_as_of_idx: int = -1,
) -> Optional[float]:
    """
    Composite = regime_momentum_weight * momentum + regime_quality_weight * quality_proxy
               + rs_acceleration_adj (early vs extended momentum)
               + macro_adj (USD/INR + RBI sector adjustments).
    """
    mom = momentum_score_at(prices, as_of_idx)
    if mom is None:
        return None
    qual = quality_map.get(sym, 25.0)
    base = regime_momentum_weight * mom + regime_quality_weight * qual

    # RS Acceleration: reward building momentum, penalise extended/fading runs
    rs_adj = 0.0
    if bench_prices is not None and bench_as_of_idx >= 0:
        rs_adj = rs_acceleration_score_at(prices, bench_prices, as_of_idx, bench_as_of_idx)

    return float(np.clip(base + rs_adj + macro_adj, 0.0, 100.0))


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


def market_stress_scalar_at(nifty_prices: pd.Series, as_of_idx: int) -> float:
    """
    Portfolio circuit breaker: detects acute market stress using 20-day NIFTY return.

    Returns a position-size scalar:
      1.0  — normal (no stress)
      0.6  — moderate stress: NIFTY down 5–8% over 20 days  → reduce new entries 40%
      0.4  — severe stress:   NIFTY down >8% over 20 days   → reduce new entries 60%

    Applied only to NEW entries in that month; existing holdings are not force-sold
    (avoids locking in losses at the worst moment). The circuit breaker resets
    automatically once the 20-day return recovers above -5%.
    """
    hist = nifty_prices.iloc[:as_of_idx + 1]
    if len(hist) < 21:
        return 1.0
    ret_20d = (hist.iloc[-1] / hist.iloc[-21] - 1)
    if ret_20d < -0.08:
        return 0.4   # severe: global selloff / crash event
    if ret_20d < -0.05:
        return 0.6   # moderate: correcting market
    return 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio construction
# ─────────────────────────────────────────────────────────────────────────────

def get_rebalance_dates(prices: Dict[str, pd.Series], bench: pd.Series) -> List[pd.Timestamp]:
    """
    Last NSE trading day of each calendar month within the price history.
    Uses pandas_market_calendars NSE calendar to exclude Indian market holidays
    (Diwali, Holi, Republic Day, etc.) — ~14 holidays/year that plain bdate_range misses.
    Falls back to last available price date per month if calendar fetch fails.
    """
    all_dates = bench.index if not bench.empty else list(prices.values())[0].index
    actual_dates = set(pd.Timestamp(d).date() for d in all_dates)

    try:
        import pandas_market_calendars as mcal
        nse = mcal.get_calendar('NSE')
        start = all_dates[0]
        end = all_dates[-1]
        valid = nse.valid_days(start_date=start, end_date=end)
        # Filter to dates that actually exist in price data (data gaps possible)
        # Strip UTC timezone to match naive price index
        valid_actual = [
            pd.Timestamp(d).tz_convert(None) for d in valid
            if pd.Timestamp(d).date() in actual_dates
        ]
        df = pd.DataFrame({'date': valid_actual})
    except Exception:
        # Fallback: use price dates as-is
        df = pd.DataFrame({'date': pd.DatetimeIndex(all_dates)})

    df['ym'] = df['date'].dt.to_period('M')
    last_days = df.groupby('ym')['date'].max().tolist()
    return sorted(last_days)


# ─────────────────────────────────────────────────────────────────────────────
# Main simulation
# ─────────────────────────────────────────────────────────────────────────────

# Hard cap: max 2 stocks per sector in any portfolio to prevent correlated crashes.
# Analysis: Feb-2026 -13.5% loss came from 3 correlated Metals + 2 Auto stocks falling together.
# Extending the IT-only cap to all sectors reduces sector concentration risk globally.
SECTOR_MAX_OVERRIDES: Dict[str, int] = {
    'IT':          2,
    'Metals':      2,
    'Auto':        2,
    'Energy':      2,
    'Financials':  2,
    'FMCG':        2,
    'Pharma':      2,
    'Industrials': 2,
    'Construction':2,
    'Consumer':    2,
    'Telecom':     1,  # only 1 stock (BHARTIARTL) in index
}


def apply_sector_cap(
    scored: List[Tuple[str, float]],
    top_n: int,
    sector_cap: float,
    forced_exits: Optional[set] = None,
) -> List[Tuple[str, float]]:
    """
    Select top_n stocks from a score-sorted list, with:
    - forced_exits: symbols that must be excluded (drawdown / score-decay exits)
    - general sector_cap: max fraction in any one sector
    - SECTOR_MAX_OVERRIDES: per-sector hard caps
    """
    forced_exits = forced_exits or set()
    max_general = max(1, int(top_n * sector_cap)) if sector_cap > 0 else top_n
    sector_counts: Dict[str, int] = {}
    selected: List[Tuple[str, float]] = []

    for sym, score in scored:
        if len(selected) >= top_n:
            break
        if sym in forced_exits:
            continue
        sector = NIFTY50_SECTORS.get(sym, 'Other')
        general_ok = sector_counts.get(sector, 0) < max_general
        override_max = SECTOR_MAX_OVERRIDES.get(sector, max_general)
        override_ok = sector_counts.get(sector, 0) < override_max
        if general_ok and override_ok:
            selected.append((sym, score))
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

    # Fill remaining slots respecting SECTOR_MAX_OVERRIDES (hard caps) but relaxing
    # the general fractional cap so small universes can still fill top_n.
    if len(selected) < top_n:
        picked = {s for s, _ in selected}
        for sym, score in scored:
            if len(selected) >= top_n:
                break
            if sym not in picked and sym not in forced_exits:
                sector = NIFTY50_SECTORS.get(sym, 'Other')
                override_max = SECTOR_MAX_OVERRIDES.get(sector, top_n)
                if sector_counts.get(sector, 0) < override_max:
                    selected.append((sym, score))
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
    return selected


def run_simulation(
    prices: Dict[str, pd.Series],
    bench: pd.Series,
    quality_map: Dict[str, float],
    top_n: int,
    transaction_cost: float,
    sector_cap: float = 0.0,
    exit_drawdown: float = 0.0,
    score_decay: float = 0.0,
    inr_prices: Optional[pd.Series] = None,
    rbi_history: Optional[List[Dict]] = None,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Returns (portfolio_value_series, trade_log_df).

    exit_drawdown: force-exit any holding that has fallen > X% from its entry price
                   (e.g. 0.08 = exit if down 8% from when we first bought it).
    score_decay:   force-exit any holding whose score has dropped > N points since entry
                   (e.g. 20.0 = exit if score fell 20+ pts — momentum structurally reversed).
    """
    rebal_dates = get_rebalance_dates(prices, bench)
    if len(rebal_dates) < 2:
        raise ValueError("Not enough rebalance dates")

    bench_at = {d: bench.get(d) for d in rebal_dates}

    portfolio_values: List[Tuple[pd.Timestamp, float]] = [(rebal_dates[0], 100.0)]
    holdings: Dict[str, float] = {}   # sym → weight
    entry_prices: Dict[str, float] = {}  # sym → price when first added
    entry_scores: Dict[str, float] = {}  # sym → score when first added
    pv = 100.0

    trade_log: List[Dict] = []

    for i in range(len(rebal_dates) - 1):
        date_t  = rebal_dates[i]
        date_t1 = rebal_dates[i + 1]

        # ── Score all stocks at date_t ──────────────────────────────────────
        bench_idx = bench.index.get_indexer([date_t], method='ffill')[0]
        regime, mom_w, qual_w = detect_regime_at(bench, bench_idx) if bench_idx >= 0 else ('SIDEWAYS', 0.55, 0.45)

        score_map: Dict[str, float] = {}
        scored: List[Tuple[str, float]] = []
        inr_s = inr_prices if inr_prices is not None else pd.Series(dtype=float)
        rbi_h = rbi_history or []
        for sym, price_series in prices.items():
            idx = price_series.index.get_indexer([date_t], method='ffill')[0]
            if idx < 63:
                continue
            m_adj = macro_adj_for_stock(sym, date_t, inr_s, rbi_h)
            score = composite_score_at(
                sym, price_series, idx, quality_map, mom_w, qual_w, m_adj,
                bench_prices=bench, bench_as_of_idx=bench_idx,
            )
            if score is not None:
                scored.append((sym, score))
                score_map[sym] = score

        if len(scored) < top_n:
            portfolio_values.append((date_t1, pv))
            continue

        scored.sort(key=lambda x: x[1], reverse=True)

        # ── Identify forced exits from current holdings ─────────────────────
        forced_exits: set = set()
        for sym in list(holdings.keys()):
            p_series = prices.get(sym)
            if p_series is None:
                continue
            idx_t = p_series.index.get_indexer([date_t], method='ffill')[0]
            if idx_t < 0:
                continue
            current_price = p_series.iloc[idx_t]

            # 1. Drawdown-from-entry exit
            if exit_drawdown > 0 and sym in entry_prices:
                ep = entry_prices[sym]
                if ep > 0 and (current_price - ep) / ep < -exit_drawdown:
                    forced_exits.add(sym)
                    continue

            # 2. Score-decay exit
            if score_decay > 0 and sym in entry_scores:
                current_score = score_map.get(sym, 0.0)
                if entry_scores[sym] - current_score > score_decay:
                    forced_exits.add(sym)

        # ── Select new holdings ─────────────────────────────────────────────
        selected = apply_sector_cap(scored, top_n, sector_cap, forced_exits)
        new_holdings = {sym: 1.0 / top_n for sym, _ in selected}

        # ── Update entry tracking ───────────────────────────────────────────
        for sym, _ in selected:
            if sym not in holdings:  # new entry
                p_series = prices[sym]
                idx_t = p_series.index.get_indexer([date_t], method='ffill')[0]
                if idx_t >= 0:
                    entry_prices[sym] = p_series.iloc[idx_t]
                entry_scores[sym] = score_map.get(sym, 50.0)
        # Remove exited stocks from tracking
        for sym in list(entry_prices.keys()):
            if sym not in new_holdings:
                entry_prices.pop(sym, None)
                entry_scores.pop(sym, None)

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
            'date':          date_t.strftime('%Y-%m'),
            'regime':        regime,
            'top_stocks':    ', '.join(s.replace('.NS', '') for s, _ in selected),
            'forced_exits':  ', '.join(s.replace('.NS', '') for s in forced_exits) if forced_exits else '',
            'port_ret_pct':  round(port_ret * 100, 2),
            'bench_ret_pct': round(bench_ret * 100, 2) if bench_ret else None,
            'alpha_pct':     round((port_ret - (bench_ret or 0)) * 100, 2),
            'pv':            round(pv, 2),
            'turnover_pct':  round(turnover * 100, 1),
        })

        holdings = new_holdings

    pv_series = pd.Series(
        {d: v for d, v in portfolio_values},
        name='portfolio'
    )
    return pv_series, pd.DataFrame(trade_log)


# ─────────────────────────────────────────────────────────────────────────────
# Signal-driven simulation (institutional buy/hold/sell logic)
# ─────────────────────────────────────────────────────────────────────────────

def run_signal_simulation(
    prices: Dict[str, pd.Series],
    bench: pd.Series,
    quality_map: Dict[str, float],
    buy_threshold: float = 65.0,
    sell_threshold: float = 50.0,
    stop_loss: float = 0.10,
    max_positions: int = 10,
    transaction_cost: float = 0.001,
    sector_cap: float = 0.30,
    inr_prices: Optional[pd.Series] = None,
    rbi_history: Optional[List[Dict]] = None,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Signal-driven portfolio simulation — institutional approach.

    Rules evaluated at each monthly review date:
      EXIT first (in order):
        1. Hard stop-loss: position down > stop_loss % from entry → forced exit
        2. Thesis broken: score < sell_threshold → exit regardless of price
      HOLD:
        3. sell_threshold ≤ score AND position in portfolio → keep it (thesis intact)
      ENTRY:
        4. score ≥ buy_threshold AND sector allows AND < max_positions → buy
      ADD to winner:
        5. score improved vs entry_score AND position profitable → increase weight
           (implemented as: weight = score_proportion of portfolio)

    Position sizing: score-proportional weights, capped at 20% per stock.
    Cash earns 0% (conservative — avoids look-ahead on risk-free rate).
    """
    rebal_dates = get_rebalance_dates(prices, bench)
    if len(rebal_dates) < 2:
        raise ValueError("Not enough rebalance dates")

    bench_at = {d: bench.get(d) for d in rebal_dates}

    portfolio_values: List[Tuple[pd.Timestamp, float]] = [(rebal_dates[0], 100.0)]
    # Holdings: sym → (entry_price, entry_score, current_weight)
    holdings: Dict[str, Dict] = {}
    pv = 100.0
    trade_log: List[Dict] = []

    for i in range(len(rebal_dates) - 1):
        date_t  = rebal_dates[i]
        date_t1 = rebal_dates[i + 1]

        bench_idx = bench.index.get_indexer([date_t], method='ffill')[0]
        regime, mom_w, qual_w = detect_regime_at(bench, bench_idx) if bench_idx >= 0 else ('SIDEWAYS', 0.55, 0.45)

        # ── Score all stocks ────────────────────────────────────────────────
        score_map: Dict[str, float] = {}
        inr_s = inr_prices if inr_prices is not None else pd.Series(dtype=float)
        rbi_h = rbi_history or []
        for sym, price_series in prices.items():
            idx = price_series.index.get_indexer([date_t], method='ffill')[0]
            if idx < 63:
                continue
            m_adj = macro_adj_for_stock(sym, date_t, inr_s, rbi_h)
            s = composite_score_at(
                sym, price_series, idx, quality_map, mom_w, qual_w, m_adj,
                bench_prices=bench, bench_as_of_idx=bench_idx,
            )
            if s is not None:
                score_map[sym] = s

        exits: List[str] = []
        exit_reasons: Dict[str, str] = {}

        # ── Step 1: EXIT — stop-loss and thesis-broken ──────────────────────
        for sym, h in list(holdings.items()):
            p_series = prices.get(sym)
            if p_series is None:
                exits.append(sym); exit_reasons[sym] = 'no_data'; continue
            idx_t = p_series.index.get_indexer([date_t], method='ffill')[0]
            if idx_t < 0:
                exits.append(sym); exit_reasons[sym] = 'no_data'; continue

            current_price = p_series.iloc[idx_t]
            ret_from_entry = (current_price - h['entry_price']) / h['entry_price']
            current_score  = score_map.get(sym, 0.0)

            if ret_from_entry < -stop_loss:
                exits.append(sym); exit_reasons[sym] = f'stop_loss({ret_from_entry*100:.1f}%)'
            elif current_score < sell_threshold:
                exits.append(sym); exit_reasons[sym] = f'score_exit({current_score:.0f})'

        for sym in exits:
            del holdings[sym]

        # ── Step 2: Circuit breaker — scale down new entries under market stress ──
        stress_scalar = market_stress_scalar_at(bench, bench_idx) if bench_idx >= 0 else 1.0
        # Under stress: raise the effective buy threshold so only highest-conviction
        # entries survive (rather than reducing size, we tighten entry gate)
        effective_buy_threshold = buy_threshold if stress_scalar == 1.0 else buy_threshold + (1 - stress_scalar) * 20

        # ── Step 3: ENTRY — buy new high-conviction stocks ──────────────────
        # Sort by score desc; respect sector cap + SECTOR_MAX_OVERRIDES (all sectors capped at 2)
        candidates = sorted(
            [(s, sc) for s, sc in score_map.items() if sc >= effective_buy_threshold and s not in holdings],
            key=lambda x: x[1], reverse=True
        )
        # Rebuild sector count from current holdings
        sec_counts: Dict[str, int] = {}
        for sym in holdings:
            sec = NIFTY50_SECTORS.get(sym, 'Other')
            sec_counts[sec] = sec_counts.get(sec, 0) + 1

        max_per_sec = max(1, int(max_positions * sector_cap))
        override_max = SECTOR_MAX_OVERRIDES

        for sym, score in candidates:
            if len(holdings) >= max_positions:
                break
            sec = NIFTY50_SECTORS.get(sym, 'Other')
            general_ok  = sec_counts.get(sec, 0) < max_per_sec
            override_ok = sec_counts.get(sec, 0) < override_max.get(sec, max_per_sec)
            if not (general_ok and override_ok):
                continue
            p_series = prices[sym]
            idx_t = p_series.index.get_indexer([date_t], method='ffill')[0]
            if idx_t < 0:
                continue
            entry_p = p_series.iloc[idx_t]
            holdings[sym] = {
                'entry_price': entry_p,
                'entry_score': score,
                'stress_entry': stress_scalar < 1.0,  # flag for pyramiding logic
            }
            sec_counts[sec] = sec_counts.get(sec, 0) + 1

        # ── Step 3: Compute score-proportional weights ──────────────────────
        if not holdings:
            # All cash month
            portfolio_values.append((date_t1, pv))
            trade_log.append({
                'date': date_t.strftime('%Y-%m'), 'regime': regime,
                'top_stocks': '(cash)', 'exits': '', 'n_positions': 0,
                'port_ret_pct': 0.0, 'bench_ret_pct': None, 'alpha_pct': 0.0,
                'pv': round(pv, 2), 'turnover_pct': 0.0,
            })
            continue

        # ── Score-proportional weights, capped at 20% per position ────────
        # Note: pyramiding (entry sizing) is tracked in portfolio_manager.py
        # for live trading. The monthly backtest bar is too coarse for intra-month
        # add-ons; we use score-proportional sizing here instead.
        scores_held = {sym: score_map.get(sym, h['entry_score'])
                       for sym, h in holdings.items()}
        total_score = sum(scores_held.values())
        raw_weights = {sym: sc / total_score for sym, sc in scores_held.items()}
        cap = 0.20
        capped: Dict[str, float] = {}
        surplus = 0.0
        for sym, w in raw_weights.items():
            if w > cap:
                surplus += w - cap; capped[sym] = cap
            else:
                capped[sym] = w
        uncapped = [s for s, w in capped.items() if w < cap]
        if uncapped and surplus > 0:
            add_each = surplus / len(uncapped)
            for sym in uncapped:
                capped[sym] = min(cap, capped[sym] + add_each)
        weights = capped

        # ── Step 4: Compute return for this period ──────────────────────────
        # Turnover vs last period
        old_syms = set(h for h in (list(holdings.keys()) + exits))
        new_syms  = set(holdings.keys())
        exited_syms = set(exits)
        entered_syms = {s for s in new_syms if exit_reasons.get(s) is None and s not in (old_syms - exited_syms)}
        turnover = (len(exited_syms) + len(entered_syms)) / max(len(old_syms | new_syms), 1)
        cost = turnover * transaction_cost

        port_ret = 0.0
        for sym, w in weights.items():
            p_series = prices[sym]
            idx_t  = p_series.index.get_indexer([date_t],  method='ffill')[0]
            idx_t1 = p_series.index.get_indexer([date_t1], method='ffill')[0]
            if idx_t < 0 or idx_t1 < 0 or idx_t1 <= idx_t:
                continue
            p0 = p_series.iloc[idx_t]; p1 = p_series.iloc[idx_t1]
            if p0 > 0:
                port_ret += w * (p1 - p0) / p0

        port_ret -= cost
        pv = pv * (1 + port_ret)
        portfolio_values.append((date_t1, round(pv, 4)))

        b0 = bench_at.get(date_t) or (bench.iloc[bench_idx] if bench_idx >= 0 else None)
        b_idx_t1 = bench.index.get_indexer([date_t1], method='ffill')[0]
        b1 = bench.iloc[b_idx_t1] if b_idx_t1 >= 0 else None
        bench_ret = (b1 - b0) / b0 if (b0 and b1 and b0 > 0) else None

        trade_log.append({
            'date':          date_t.strftime('%Y-%m'),
            'regime':        regime,
            'top_stocks':    ', '.join(s.replace('.NS', '') for s in holdings),
            'exits':         ', '.join(f"{s.replace('.NS','')}({r})"
                                       for s, r in exit_reasons.items()),
            'n_positions':   len(holdings),
            'port_ret_pct':  round(port_ret * 100, 2),
            'bench_ret_pct': round(bench_ret * 100, 2) if bench_ret else None,
            'alpha_pct':     round((port_ret - (bench_ret or 0)) * 100, 2),
            'pv':            round(pv, 2),
            'turnover_pct':  round(turnover * 100, 1),
        })

    pv_series = pd.Series({d: v for d, v in portfolio_values}, name='portfolio')
    return pv_series, pd.DataFrame(trade_log)


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(pv: pd.Series, bench: pd.Series, risk_free: float = 0.07) -> Dict:
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


def bench_metrics(bench: pd.Series, risk_free: float = 0.07) -> Dict:
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
        'sector_cap_pct':    int(config['sector_cap'] * 100),
        'exit_drawdown_pct': int(config.get('exit_drawdown', 0) * 100),
        'score_decay':       config.get('score_decay', 0),
        'quality':           'yes' if config['quality'] else 'no',
        'costs':             'yes' if config['costs'] else 'no',
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
    parser.add_argument('--sector-cap',      type=float, default=SECTOR_CAP_DEFAULT,
                        help=f'Max sector weight 0-1 (default: {SECTOR_CAP_DEFAULT}, 0=off)')
    parser.add_argument('--exit-drawdown',   type=float, default=0.0,
                        help='Force-exit a holding if it falls X%% from entry price (e.g. 0.08). Default: off')
    parser.add_argument('--score-decay',     type=float, default=0.0,
                        help='Force-exit a holding if its score drops >N pts from entry (e.g. 20). Default: off')
    parser.add_argument('--signal-mode',     action='store_true',
                        help='Institutional signal mode: buy on score≥buy-threshold, hold until score<sell-threshold or stop-loss')
    parser.add_argument('--buy-threshold',   type=float, default=65.0,
                        help='Signal mode: minimum score to initiate a position (default: 65)')
    parser.add_argument('--sell-threshold',  type=float, default=50.0,
                        help='Signal mode: exit when score drops below this (default: 50)')
    parser.add_argument('--stop-loss',       type=float, default=0.10,
                        help='Signal mode: hard stop-loss %% from entry price (default: 0.10 = 10%%)')
    parser.add_argument('--name',        type=str,   default='',
                        help='Label for this run (saved to results log)')
    parser.add_argument('--compare',     action='store_true',
                        help='Print comparison table of all saved runs and exit')
    parser.add_argument('--no-macro',    action='store_true',
                        help='Disable USD/INR + RBI macro overlays (for A/B comparison)')
    args = parser.parse_args()

    if args.compare:
        print_comparison_table()
        return

    cost = 0.0 if args.no_costs else TRANSACTION_COST

    # Auto-generate run name if not provided
    macro_suffix = '_nomacro' if args.no_macro else '_macro'
    if args.signal_mode:
        run_name = args.name or (
            f"signal_buy{int(args.buy_threshold)}_sell{int(args.sell_threshold)}_"
            f"sl{int(args.stop_loss*100)}_"
            f"{'noQ_' if args.no_quality else ''}"
            f"{args.years}y{macro_suffix}"
        )
    else:
        run_name = args.name or (
            f"top{args.top}_"
            f"{'noQ_' if args.no_quality else ''}"
            f"sc{int(args.sector_cap*100)}_"
            f"{'dd'+str(int(args.exit_drawdown*100))+'_' if args.exit_drawdown else ''}"
            f"{'sd'+str(int(args.score_decay))+'_' if args.score_decay else ''}"
            f"{args.years}y{macro_suffix}"
        )

    print("\n" + "="*64)
    print("  AI HEDGE FUND — PORTFOLIO BACKTEST")
    print(f"  Run: {run_name}")
    print(f"  Universe: NIFTY50  |  Window: {args.years}Y")
    if args.signal_mode:
        print(f"  Mode: SIGNAL-DRIVEN  |  Buy≥{args.buy_threshold:.0f}  Sell<{args.sell_threshold:.0f}  Stop={args.stop_loss*100:.0f}%")
    else:
        print(f"  Mode: Calendar  |  Top-{args.top} stocks")
    sector_cap_str = f"{int(args.sector_cap * 100)}% cap" if args.sector_cap > 0 else "no cap"
    cost_str = 'none' if cost == 0 else f'{cost*100:.2f}% per trade ({cost*10000:.0f} bps)'
    macro_str = 'OFF (--no-macro)' if args.no_macro else 'ON (USD/INR + RBI cycle)'
    print(f"  Costs: {cost_str}  |  Sector: {sector_cap_str}")
    print(f"  Macro overlays: {macro_str}")
    print("="*64)

    # Fetch prices
    prices, bench = fetch_all_prices(NIFTY50, years=args.years + 1)  # +1Y buffer for warmup

    # Macro overlay data (USD/INR + RBI)
    if args.no_macro:
        inr_prices: pd.Series = pd.Series(dtype=float)
        rbi_history: List[Dict] = []
        print("  Macro overlays: DISABLED (--no-macro)")
    else:
        inr_prices = fetch_usdinr_prices(args.years)
        rbi_history = load_rbi_history()
        rbi_msg = f"{len(rbi_history)} MPC decisions loaded" if rbi_history else "no RBI data"
        print(f"  RBI rate cycle: {rbi_msg}")

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
    if args.signal_mode:
        print(f"\n  Running signal-driven simulation …")
        pv, trade_log = run_signal_simulation(
            prices_bt, bench_bt, quality_map,
            buy_threshold=args.buy_threshold,
            sell_threshold=args.sell_threshold,
            stop_loss=args.stop_loss,
            max_positions=args.top,
            transaction_cost=cost,
            sector_cap=args.sector_cap,
            inr_prices=inr_prices,
            rbi_history=rbi_history,
        )
    else:
        print(f"\n  Running monthly simulation (top-{args.top}) …")
        pv, trade_log = run_simulation(
            prices_bt, bench_bt, quality_map, args.top, cost,
            args.sector_cap, args.exit_drawdown, args.score_decay,
            inr_prices=inr_prices,
            rbi_history=rbi_history,
        )

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
        'years':          args.years,
        'top_n':          args.top,
        'sector_cap':     args.sector_cap,
        'exit_drawdown':  args.exit_drawdown if not args.signal_mode else args.stop_loss,
        'score_decay':    args.score_decay if not args.signal_mode else args.sell_threshold,
        'quality':        not args.no_quality,
        'costs':          not args.no_costs,
    }, m, bm)

    print(f"  Run --compare to see all saved runs side-by-side.\n")


if __name__ == '__main__':
    main()
