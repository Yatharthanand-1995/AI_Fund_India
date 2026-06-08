#!/usr/bin/env python3
"""
Portfolio Backtest — Multi-Year Simulation (default 5Y)

Simulates a monthly-rebalanced long-only portfolio using the AI scoring system
on NIFTY50 stocks and compares against the NIFTY50 index benchmark.

Methodology:
  • Universe   : NIFTY50 stocks
  • Rebalance  : monthly (last trading day of each month)
  • Selection  : top N stocks by composite score, equal-weighted
  • Scoring    : momentum-based (price-only, fully historically valid)
                 quality refreshed annually using TTM fundamentals at each
                 refresh date (no lookahead bias)
  • Costs      : 0.27% per trade (27 bps: STT + brokerage + GST + stamp duty + exchange charges)
  • Benchmark  : NIFTY50 index (^NSEI)

Metrics reported:
  CAGR, Total Return, Sharpe Ratio, Max Drawdown, Calmar Ratio,
  Win Rate (vs benchmark), Alpha, Beta, year-by-year breakdown,
  monthly returns table, drawdown chart

Usage:
    python scripts/portfolio_backtest.py
    python scripts/portfolio_backtest.py --years 5 --top 10
    python scripts/portfolio_backtest.py --years 3 --top 5 --no-costs
    python scripts/portfolio_backtest.py --signal-mode --buy-threshold 60 --sell-threshold 40 --stop-loss 0.12 --no-quality
"""

import sys
import os
import json
import warnings
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

warnings.filterwarnings('ignore')
logging.disable(logging.CRITICAL)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ─────────────────────────────────────────────────────────────────────────────
# NIFTY 50 universe — point-in-time (survivorship-bias-free)
# ─────────────────────────────────────────────────────────────────────────────
# We no longer use a hardcoded list. Instead, get_universe_at_date() calls
# data.nifty50_historical.get_nifty50_at_date() and adds the .NS suffix.
# For fetching price data we need the UNION of all historical symbols so
# we can build one yfinance batch call covering the full backtest window.

from data.nifty50_historical import get_nifty50_at_date as _get_nifty50_pit

# Symbols that existed historically but map to a DIFFERENT Yahoo Finance ticker.
# Key = plain symbol in historical snapshots, Value = Yahoo Finance ticker (no .NS needed).
# These are corporate actions (mergers, renames) that break the plain symbol → .NS rule.
_SYMBOL_REMAP: Dict[str, str] = {
    'LTI':      'LTI.NS',       # pre-LTIM merger symbol — has price history until Nov 2022
    'INFRATEL': 'INFRATEL.NS',  # Bharti Infratel — delisted after Indus Towers merger Mar 2021
    'HDFC':     'HDFC.NS',      # HDFC Ltd — delisted after merger into HDFCBANK Jul 2023
}

# Last valid trading date for symbols that were subsequently delisted/merged.
# After this date the symbol has no price data; skip it in scoring.
_SYMBOL_LAST_DATE: Dict[str, pd.Timestamp] = {
    'INFRATEL.NS': pd.Timestamp('2021-03-15'),   # merged into Indus Towers
    'HDFC.NS':     pd.Timestamp('2023-07-12'),   # merged into HDFCBANK
    'LTI.NS':      pd.Timestamp('2022-11-25'),   # merged into LTIM
}


def get_universe_at_date(as_of_date: pd.Timestamp) -> List[str]:
    """Return NIFTY50 constituents as of as_of_date as Yahoo Finance .NS tickers."""
    plain = _get_nifty50_pit(as_of_date.to_pydatetime() if hasattr(as_of_date, 'to_pydatetime') else as_of_date)
    tickers = []
    for sym in plain:
        if sym in _SYMBOL_REMAP:
            tickers.append(_SYMBOL_REMAP[sym])
        else:
            tickers.append(f"{sym}.NS")
    return sorted(tickers)


def get_all_historical_symbols(years: int) -> List[str]:
    """
    Return the union of all symbols ever in NIFTY50 over the backtest window.
    Used so a single yfinance batch fetch covers every symbol we might need.
    """
    from datetime import datetime as _dt
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data.nifty50_historical import _SNAPSHOTS

    cutoff = pd.Timestamp.now() - pd.DateOffset(years=years + 1)
    all_syms: set = set()
    for eff_date, sym_set in _SNAPSHOTS:
        if pd.Timestamp(eff_date) >= cutoff:
            for sym in sym_set:
                if sym in _SYMBOL_REMAP:
                    all_syms.add(_SYMBOL_REMAP[sym])
                else:
                    all_syms.add(f"{sym}.NS")
    return sorted(all_syms)


BENCHMARK = '^NSEI'

TRANSACTION_COST = 0.0027  # 27 bps/side: STT 0.1% sell + brokerage + GST + stamp duty + exchange charges
SECTOR_CAP_DEFAULT = 0.30  # max 30% of portfolio in any one sector

# Risk-free rate proxy (Indian liquid fund / overnight rate annualised).
# Applied as monthly return when portfolio is fully in cash.
CASH_ANNUAL_RATE = 0.065   # 6.5% p.a.
CASH_MONTHLY_RATE = (1 + CASH_ANNUAL_RATE) ** (1 / 12) - 1

# Sector labels — covers both current and historical NIFTY50 constituents
NIFTY50_SECTORS: Dict[str, str] = {
    # Current stocks
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
    'TRENT.NS':       'Consumer',
    'BHARTIARTL.NS':  'Telecom',
    'BEL.NS':         'Industrials',
    # Historical stocks (removed from index but present in 2019-2024 windows)
    'HDFC.NS':        'Financials',   # HDFC Ltd — merged into HDFCBANK Jul 2023
    'LTI.NS':         'IT',           # LTI — merged into LTIM Nov 2022
    'VEDL.NS':        'Metals',       # Vedanta
    'UPL.NS':         'Chemicals',    # UPL — removed Sep 2024
    'ZEEL.NS':        'Media',        # Zee Entertainment — removed Nov 2020
    'SHREECEM.NS':    'Construction', # Shree Cement — removed Mar 2021
    'INFRATEL.NS':    'Telecom',      # Bharti Infratel — merged Mar 2021
    'LUPIN.NS':       'Pharma',       # Lupin — removed 2019
    'AMBUJA.NS':      'Construction', # Ambuja Cements — removed 2019
}

# ── Factor buckets for M7 HHI concentration monitoring ───────────────────────
# 5 buckets capture the dominant factor exposures present in NIFTY50.
# A stock can only be in one bucket; 'other' is the catch-all.
# Used by portfolio_factor_hhi() to block new entries when a factor is crowded.
FACTOR_BUCKETS: Dict[str, str] = {
    # Defensive Value: high ROE + low P/E + stable dividend (ITC-style)
    'ITC.NS':         'def_value',
    'BRITANNIA.NS':   'def_value',
    'NESTLEIND.NS':   'def_value',
    'HINDUNILVR.NS':  'def_value',
    'TATACONSUM.NS':  'def_value',
    'ASIANPAINT.NS':  'def_value',
    # PSU / Commodity: state-owned or commodity-driven earnings (incl. large integrated energy)
    'RELIANCE.NS':    'psu_commodity',
    'COALINDIA.NS':   'psu_commodity',
    'NTPC.NS':        'psu_commodity',
    'POWERGRID.NS':   'psu_commodity',
    'ONGC.NS':        'psu_commodity',
    'BPCL.NS':        'psu_commodity',
    'GAIL.NS':        'psu_commodity',
    'BEL.NS':         'psu_commodity',
    'SBIN.NS':        'psu_commodity',
    # Tech / Growth: IT services + high revenue growth
    'TCS.NS':         'tech',
    'INFY.NS':        'tech',
    'HCLTECH.NS':     'tech',
    'WIPRO.NS':       'tech',
    'TECHM.NS':       'tech',
    'LTIM.NS':        'tech',
    'LTI.NS':         'tech',
    # Cyclical Growth: banks, auto, industrials — earnings tied to GDP cycle
    'HDFCBANK.NS':    'cyclical_growth',
    'ICICIBANK.NS':   'cyclical_growth',
    'AXISBANK.NS':    'cyclical_growth',
    'KOTAKBANK.NS':   'cyclical_growth',
    'BAJFINANCE.NS':  'cyclical_growth',
    'BAJAJFINSV.NS':  'cyclical_growth',
    'HDFC.NS':        'cyclical_growth',
    'INDUSINDBK.NS':  'cyclical_growth',
    'TATAMOTORS.NS':  'cyclical_growth',
    'MARUTI.NS':      'cyclical_growth',
    'HEROMOTOCO.NS':  'cyclical_growth',
    'EICHERMOT.NS':   'cyclical_growth',
    'BAJAJ-AUTO.NS':  'cyclical_growth',
    'M&M.NS':         'cyclical_growth',
    'JSWSTEEL.NS':    'cyclical_growth',
    'TATASTEEL.NS':   'cyclical_growth',
    'HINDALCO.NS':    'cyclical_growth',
    'VEDL.NS':        'cyclical_growth',
    'LT.NS':          'cyclical_growth',
    # Other: pharma, telecom, consumer discretionary, specialty
    'SUNPHARMA.NS':   'other',
    'DIVISLAB.NS':    'other',
    'CIPLA.NS':       'other',
    'DRREDDY.NS':     'other',
    'APOLLOHOSP.NS':  'other',
    'LUPIN.NS':       'other',
    'BHARTIARTL.NS':  'other',
    'INFRATEL.NS':    'other',
    'ADANIPORTS.NS':  'other',
    'ADANIENT.NS':    'other',
    'GRASIM.NS':      'other',
    'ULTRACEMCO.NS':  'other',
    'TITAN.NS':       'other',
    'TRENT.NS':       'other',
    'SBILIFE.NS':     'other',
    'HDFCLIFE.NS':    'other',
    'UPL.NS':         'other',
    'ZEEL.NS':        'other',
    'SHREECEM.NS':    'other',
    'AMBUJA.NS':      'other',
}


def portfolio_factor_hhi(holdings_syms: set, score_weights: Dict[str, float]) -> tuple:
    """
    Compute portfolio Herfindahl-Hirschman Index across factor buckets.

    Returns (hhi, bucket_weights_dict).
    HHI = sum of squared bucket weight fractions (0-1 scale).
    HHI = 0.20 means 5 equally-weighted buckets (diverse).
    HHI = 1.00 means all weight in one bucket (fully concentrated).
    """
    from collections import defaultdict
    bucket_w: Dict[str, float] = defaultdict(float)
    total_w = sum(score_weights.get(s, 0.0) for s in holdings_syms)
    if total_w <= 0:
        return 0.0, {}
    for sym in holdings_syms:
        w = score_weights.get(sym, 0.0) / total_w
        bucket = FACTOR_BUCKETS.get(sym, 'other')
        bucket_w[bucket] += w
    hhi = sum(v ** 2 for v in bucket_w.values())
    return hhi, dict(bucket_w)


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
    """
    Fetch price history for all symbols (union of historical NIFTY50 + benchmark).
    Uses years+1 so warmup period is available for the first rebalance date.
    """
    import yfinance as yf

    all_syms = symbols + [BENCHMARK]
    print(f"  Fetching {years+1}Y price history for {len(symbols)} stocks + benchmark …")
    raw = yf.download(all_syms, period=f"{years + 1}y", auto_adjust=True, progress=False)

    prices: Dict[str, pd.Series] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw['Close']
        for sym in symbols:
            if sym in close.columns and not close[sym].dropna().empty:
                prices[sym] = close[sym].dropna()
        bench = close[BENCHMARK].dropna() if BENCHMARK in close.columns else pd.Series(dtype=float)
    else:
        prices[symbols[0]] = raw['Close'].dropna()
        bench = pd.Series(dtype=float)

    # Truncate delisted symbols at their last valid trading date
    for sym, last_date in _SYMBOL_LAST_DATE.items():
        if sym in prices:
            prices[sym] = prices[sym][prices[sym].index <= last_date]
            if prices[sym].empty:
                del prices[sym]

    print(f"  Got {len(prices)}/{len(symbols)} stocks  |  "
          f"benchmark {'OK' if not bench.empty else 'MISSING'}")
    return prices, bench


def get_quality_snapshot(symbols: List[str]) -> Dict[str, float]:
    """
    DEPRECATED: Uses today's fundamentals — causes lookahead bias in backtests.
    Kept for backward compatibility. Use get_point_in_time_quality() instead.
    """
    import warnings
    warnings.warn(
        "get_quality_snapshot() uses current-date fundamentals which causes "
        "lookahead bias in backtests. Use get_point_in_time_quality(symbols, as_of_date) "
        "to get TTM fundamentals at the backtest date.",
        DeprecationWarning, stacklevel=2
    )
    import yfinance as yf
    quality: Dict[str, float] = {}
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            roe = info.get('returnOnEquity')
            dte = info.get('debtToEquity')
            roe_s = 0 if roe is None else min(40, max(0, roe * 100 / 25 * 40))
            dte_s = 18 if dte is None else max(2, 35 - min(33, (dte / 100) * 35))
            quality[sym] = round(roe_s + dte_s, 1)
        except Exception:
            quality[sym] = 25.0
    return quality


def get_point_in_time_quality(
    symbols: List[str],
    as_of_date: pd.Timestamp,
    fallback_score: float = 25.0,
) -> Dict[str, float]:
    """
    Compute point-in-time quality scores using TTM fundamentals
    available as of as_of_date.

    Method:
      - Fetches yfinance quarterly income statement and balance sheet.
      - Selects only quarters whose report date <= as_of_date (no future data).
      - Computes TTM (trailing 12 months) ROE and latest D/E ratio.
      - Returns quality score 0-100, same scale as get_quality_snapshot().

    Why this matters:
      A company's ROE in 2020 can differ dramatically from 2026.
      Using today's ROE for a 2020 backtest creates lookahead bias.

    Args:
        symbols: List of stock symbols (no .NS suffix)
        as_of_date: Point-in-time date for fundamental data
        fallback_score: Score returned when data is unavailable (default 25)

    Returns:
        Dict mapping symbol -> quality score 0-100
    """
    import yfinance as yf

    quality: Dict[str, float] = {}

    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")

            # ── Income statement: get TTM net income ──
            inc = ticker.quarterly_income_stmt
            ttm_net_income = None
            if inc is not None and not inc.empty:
                # Filter columns (quarters) on or before as_of_date
                past_cols = [c for c in inc.columns if pd.Timestamp(c) <= as_of_date]
                if len(past_cols) >= 4:
                    # Sum last 4 quarters for TTM
                    ni_row = None
                    for candidate in ['Net Income', 'Net Income Common Stockholders', 'Net Income From Continuing Operations']:
                        if candidate in inc.index:
                            ni_row = inc.loc[candidate, past_cols[:4]]
                            break
                    if ni_row is not None:
                        ttm_net_income = float(ni_row.sum())

            # ── Balance sheet: get equity and total debt at most recent quarter ──
            bs = ticker.quarterly_balance_sheet
            equity = None
            total_debt = None
            if bs is not None and not bs.empty:
                past_cols_bs = [c for c in bs.columns if pd.Timestamp(c) <= as_of_date]
                if past_cols_bs:
                    latest_col = past_cols_bs[0]  # most recent past quarter
                    # Stockholders equity
                    for eq_key in ['Stockholders Equity', 'Common Stock Equity', 'Total Equity Gross Minority Interest']:
                        if eq_key in bs.index:
                            val = bs.loc[eq_key, latest_col]
                            if pd.notna(val) and val != 0:
                                equity = float(val)
                                break
                    # Total debt
                    for debt_key in ['Total Debt', 'Long Term Debt', 'Total Liabilities Net Minority Interest']:
                        if debt_key in bs.index:
                            val = bs.loc[debt_key, latest_col]
                            if pd.notna(val) and val > 0:
                                total_debt = float(val)
                                break

            # ── Compute ROE ──
            roe = None
            if ttm_net_income is not None and equity and equity > 0:
                roe = ttm_net_income / equity  # as decimal (e.g. 0.25 = 25%)

            # ── Compute D/E ──
            dte = None
            if total_debt is not None and equity and equity > 0:
                dte = (total_debt / equity) * 100  # percent form (matches yfinance convention)

            # ── Score (same scale as original) ──
            # If both metrics are unavailable (no usable historical data),
            # return fallback_score rather than the misleading 0+18=18 default.
            if roe is None and dte is None:
                quality[sym] = fallback_score
            else:
                roe_s = 0 if roe is None else min(40, max(0, roe * 100 / 25 * 40))
                dte_s = 18 if dte is None else max(2, 35 - min(33, (dte / 100) * 35))
                quality[sym] = round(roe_s + dte_s, 1)

        except Exception:
            quality[sym] = fallback_score

    return quality


def build_annual_quality_cache(
    symbols: List[str],
    rebal_dates: List[pd.Timestamp],
    fallback_score: float = 25.0,
) -> Dict[pd.Timestamp, Dict[str, float]]:
    """
    Pre-build a cache of point-in-time quality scores refreshed once per year.

    For a 5-year backtest the scoring model should not use the same fundamental
    snapshot throughout. This helper fetches quarterly financials once per
    calendar year and returns a mapping {annual_date: {sym: score}}.

    During simulation each rebalance date uses the most recent annual snapshot
    on or before it (no lookahead bias). One network round-trip per year —
    a 5-year run issues ~5 batches instead of ~60 individual fetches.
    """
    year_dates: Dict[int, pd.Timestamp] = {}
    for d in sorted(rebal_dates):
        yr = d.year
        if yr not in year_dates:
            year_dates[yr] = d

    cache: Dict[pd.Timestamp, Dict[str, float]] = {}
    for yr, snapshot_date in sorted(year_dates.items()):
        print(f"  Quality snapshot {yr} (as of {snapshot_date.strftime('%Y-%m')}) …")
        plain_syms = [s.replace('.NS', '') for s in symbols]
        scores = get_point_in_time_quality(plain_syms, snapshot_date, fallback_score)
        cache[snapshot_date] = {f"{s}.NS": v for s, v in scores.items()}

    return cache


def lookup_quality(
    cache: Dict[pd.Timestamp, Dict[str, float]],
    as_of_date: pd.Timestamp,
    fallback: float = 25.0,
) -> Dict[str, float]:
    """Return the most recent quality snapshot on or before as_of_date."""
    past = [d for d in cache if d <= as_of_date]
    if not past:
        return {}
    return cache[max(past)]


# ─────────────────────────────────────────────────────────────────────────────
# Fundamentals cache — live-aligned BacktestScorer (P/E rank + EPS growth + ROE/D/E)
# ─────────────────────────────────────────────────────────────────────────────

def get_point_in_time_fundamentals(
    symbols: List[str],
    as_of_date: pd.Timestamp,
    all_prices: Dict[str, pd.Series],
) -> Dict[str, Dict]:
    """
    Fetch point-in-time fundamentals: ROE, D/E, P/E, TTM revenue.

    Data strategy:
      1. Try quarterly_income_stmt / quarterly_balance_sheet filtered to as_of_date.
         This gives true point-in-time data for recent snapshots (last ~6 quarters).
      2. When quarterly data has no columns ≤ as_of_date (too historical for yfinance),
         fall back to ticker.info (current-date). For NIFTY50 blue-chips, fundamental
         cross-sectional rankings (ROE rank, P/E rank) are stable year-over-year.
         This introduces modest lookahead bias but is the only reliable data source
         for 2021-2023 historical snapshots.

    Returns raw metrics per symbol — scoring happens cross-sectionally in the sim loop.
    """
    import yfinance as yf
    results: Dict[str, Dict] = {}

    for sym in symbols:
        try:
            ticker   = yf.Ticker(f"{sym}.NS")
            inc      = ticker.quarterly_income_stmt
            bs       = ticker.quarterly_balance_sheet
            sym_ns   = f"{sym}.NS"

            ttm_net_income: Optional[float] = None
            ttm_revenue:    Optional[float] = None
            equity:         Optional[float] = None
            total_debt:     Optional[float] = None
            roe:            Optional[float] = None
            dte:            Optional[float] = None
            pe:             Optional[float] = None

            # ── Try quarterly data first (reliable for recent snapshots) ──────
            # has_quarterly_income: True only when ≥4 past quarters available (for TTM)
            # has_quarterly_balance: True when any balance sheet column available
            # The info fallback fires when income data is insufficient (< 4 quarters)
            has_quarterly_income  = False
            has_quarterly_balance = False

            if inc is not None and not inc.empty:
                past_cols = [c for c in inc.columns if pd.Timestamp(c) <= as_of_date]
                if len(past_cols) >= 4:
                    has_quarterly_income = True
                    for ni_key in ['Net Income', 'Net Income Common Stockholders',
                                   'Net Income From Continuing Operation Net Minority Interest']:
                        if ni_key in inc.index:
                            ttm_net_income = float(inc.loc[ni_key, past_cols[:4]].sum())
                            break
                    for rev_key in ['Total Revenue', 'Operating Revenue']:
                        if rev_key in inc.index:
                            ttm_revenue = float(inc.loc[rev_key, past_cols[:4]].sum())
                            break

            if bs is not None and not bs.empty:
                past_cols_bs = [c for c in bs.columns if pd.Timestamp(c) <= as_of_date]
                if past_cols_bs:
                    has_quarterly_balance = True
                    col = past_cols_bs[0]
                    for eq_key in ['Stockholders Equity', 'Common Stock Equity',
                                   'Total Equity Gross Minority Interest']:
                        if eq_key in bs.index:
                            v = bs.loc[eq_key, col]
                            if pd.notna(v) and v != 0:
                                equity = float(v)
                                break
                    for dt_key in ['Total Debt', 'Long Term Debt']:
                        if dt_key in bs.index:
                            v = bs.loc[dt_key, col]
                            if pd.notna(v) and v > 0:
                                total_debt = float(v)
                                break

            # Compute ROE and D/E from quarterly data only if both sides are available
            has_quarterly = has_quarterly_income and has_quarterly_balance
            if has_quarterly and ttm_net_income is not None and equity and equity > 0:
                roe = ttm_net_income / equity
            if has_quarterly_balance and total_debt is not None and equity and equity > 0:
                dte = (total_debt / equity) * 100

            # ── P/E from historical price / TTM EPS ──────────────────────────
            # Requires shares outstanding — try income stmt first, then info
            if has_quarterly_income and ttm_net_income is not None:
                shares: Optional[float] = None
                if inc is not None and not inc.empty:
                    past_cols_inc = [c for c in inc.columns if pd.Timestamp(c) <= as_of_date]
                    if past_cols_inc:
                        for sh_key in ['Diluted Average Shares', 'Basic Average Shares']:
                            if sh_key in inc.index:
                                val = inc.loc[sh_key, past_cols_inc[0]]
                                if pd.notna(val) and val > 0:
                                    shares = float(val)
                                    break
                if shares and shares > 0:
                    ttm_eps = ttm_net_income / shares
                    p_ser = all_prices.get(sym_ns)
                    if p_ser is not None and not p_ser.empty:
                        idx = p_ser.index.get_indexer([as_of_date], method='ffill')[0]
                        if idx >= 0:
                            price_at = float(p_ser.iloc[idx])
                            candidate = price_at / ttm_eps
                            if 0 < candidate < 200:
                                pe = candidate

            # ── Fallback to ticker.info when quarterly income data is insufficient ─
            # yfinance quarterly data only covers ~6-8 recent quarters.
            # For snapshots >6 quarters old, has_quarterly_income=False.
            # ticker.info gives current-date metrics — acceptable for cross-sectional
            # ranking of stable large caps (NIFTY50 ROE/P/E rankings shift slowly).
            if not has_quarterly_income:
                info = ticker.info
                roe_info = info.get('returnOnEquity')           # decimal e.g. 0.18
                dte_info = info.get('debtToEquity')             # yfinance: already % e.g. 42.3
                pe_info  = info.get('trailingPE') or info.get('forwardPE')
                rev_growth_info = info.get('revenueGrowth')     # decimal e.g. 0.12

                if roe_info is not None:
                    roe = float(roe_info)
                if dte_info is not None:
                    dte = float(dte_info)
                if pe_info is not None and 0 < pe_info < 200:
                    pe = float(pe_info)
                # Store revenue growth directly (no TTM revenue needed)
                # Also compute FCF yield and pledge from info while we have it
                if rev_growth_info is not None:
                    _fcf_y = None
                    try:
                        _raw_fcf = info.get('freeCashflow')
                        _raw_mc  = info.get('marketCap')
                        if _raw_fcf is not None and _raw_mc and _raw_mc > 0:
                            _fcf_y = float(_raw_fcf) / float(_raw_mc) * 100
                    except Exception:
                        pass
                    _pledge = None
                    try:
                        _rp = info.get('promoterSharesPledgedPercent')
                        if _rp is not None:
                            _pledge = float(_rp) * 100
                    except Exception:
                        pass
                    # Earnings surprise for the info-fallback path
                    _surp_pct, _surp_days = None, None
                    try:
                        ed = ticker.earnings_dates
                        if ed is not None and not ed.empty:
                            ed_utc = ed.copy()
                            if ed_utc.index.tz is not None:
                                ed_utc.index = ed_utc.index.tz_convert('UTC')
                            else:
                                ed_utc.index = ed_utc.index.tz_localize('UTC')
                            as_of_utc = as_of_date.tz_localize('UTC') if as_of_date.tz is None else as_of_date.tz_convert('UTC')
                            past_ed = ed_utc[ed_utc.index <= as_of_utc].dropna(
                                subset=['Reported EPS', 'EPS Estimate']
                            )
                            if not past_ed.empty:
                                latest_ann = past_ed.sort_index(ascending=False).iloc[0]
                                days_since = (as_of_utc - latest_ann.name).days
                                if days_since <= 90:
                                    if ('Surprise(%)' in latest_ann.index
                                            and pd.notna(latest_ann['Surprise(%)'])):
                                        _surp_pct = float(latest_ann['Surprise(%)'])
                                    else:
                                        actual = float(latest_ann['Reported EPS'])
                                        est = float(latest_ann['EPS Estimate'])
                                        if abs(est) > 0.001:
                                            _surp_pct = (actual - est) / abs(est) * 100
                                    _surp_days = days_since
                    except Exception:
                        pass
                    results[sym] = {
                        'ttm_revenue':            None,
                        'roe':                    roe,
                        'dte':                    dte,
                        'pe':                     pe,
                        'rev_growth_direct':      float(rev_growth_info),
                        'fcf_yield':              _fcf_y,
                        'pledge_pct':             _pledge,
                        'earnings_surprise_pct':  _surp_pct,
                        'earnings_surprise_days': _surp_days,
                    }
                    continue

            # ── FCF Yield: Free Cash Flow / Market Cap ───────────────────────
            # yfinance quarterly cashflow exposes 'Free Cash Flow' directly.
            # Falls back to ticker.info['freeCashflow'] for older snapshots.
            fcf_yield: Optional[float] = None
            try:
                cf = ticker.quarterly_cashflow
                ttm_fcf: Optional[float] = None

                if cf is not None and not cf.empty:
                    past_cf = [c for c in cf.columns if pd.Timestamp(c) <= as_of_date]
                    if len(past_cf) >= 4:
                        if 'Free Cash Flow' in cf.index:
                            ttm_fcf = float(cf.loc['Free Cash Flow', past_cf[:4]].sum())
                        else:
                            ttm_ocf, ttm_capex = None, None
                            for ocf_key in ['Operating Cash Flow', 'Cash From Operations']:
                                if ocf_key in cf.index:
                                    ttm_ocf = float(cf.loc[ocf_key, past_cf[:4]].sum())
                                    break
                            for cx_key in ['Capital Expenditure']:
                                if cx_key in cf.index:
                                    ttm_capex = float(cf.loc[cx_key, past_cf[:4]].sum())
                                    break
                            if ttm_ocf is not None:
                                ttm_fcf = ttm_ocf - abs(ttm_capex or 0)

                # Fallback: use ticker.info for snapshots where quarterly CF is unavailable
                if ttm_fcf is None:
                    info_cf = ticker.info
                    raw_fcf = info_cf.get('freeCashflow')
                    if raw_fcf is not None:
                        ttm_fcf = float(raw_fcf)

                if ttm_fcf is not None:
                    # Market cap: price × shares if available, else ticker.info.marketCap
                    mktcap: Optional[float] = None
                    p_ser = all_prices.get(f"{sym}.NS")
                    if p_ser is not None and not p_ser.empty:
                        idx_mc = p_ser.index.get_indexer([as_of_date], method='ffill')[0]
                        if idx_mc >= 0:
                            price_mc = float(p_ser.iloc[idx_mc])
                            sh_mc: Optional[float] = None
                            if inc is not None and not inc.empty:
                                pi = [c for c in inc.columns if pd.Timestamp(c) <= as_of_date]
                                if pi:
                                    for sh_k in ['Diluted Average Shares', 'Basic Average Shares']:
                                        if sh_k in inc.index:
                                            v = inc.loc[sh_k, pi[0]]
                                            if pd.notna(v) and float(v) > 0:
                                                sh_mc = float(v)
                                                break
                            if sh_mc and sh_mc > 0:
                                mktcap = price_mc * sh_mc
                    if mktcap is None:
                        mc_raw = ticker.info.get('marketCap')
                        if mc_raw and mc_raw > 0:
                            mktcap = float(mc_raw)
                    if mktcap and mktcap > 0:
                        fcf_yield = (ttm_fcf / mktcap) * 100
            except Exception:
                pass

            # ── Promoter pledge % (India-specific forced-selling risk) ────────
            pledge_pct: Optional[float] = None
            try:
                raw_pledge = ticker.info.get('promoterSharesPledgedPercent')
                if raw_pledge is not None:
                    pledge_pct = float(raw_pledge) * 100
            except Exception:
                pass

            # ── Earnings surprise — point-in-time EPS beat/miss ─────────────
            # Uses ticker.earnings_dates filtered to announcements on or before
            # as_of_date AND within the prior 90 days. This is truly PIT:
            # we only know about surprises that had already been announced.
            earnings_surprise_pct: Optional[float] = None
            earnings_surprise_days: Optional[int] = None
            try:
                ed = ticker.earnings_dates
                if ed is not None and not ed.empty:
                    # Normalize to UTC for comparison
                    ed_utc = ed.copy()
                    if ed_utc.index.tz is not None:
                        ed_utc.index = ed_utc.index.tz_convert('UTC')
                    else:
                        ed_utc.index = ed_utc.index.tz_localize('UTC')
                    as_of_utc = as_of_date.tz_localize('UTC') if as_of_date.tz is None else as_of_date.tz_convert('UTC')

                    # Past announcements only (genuine PIT)
                    past_ed = ed_utc[ed_utc.index <= as_of_utc].dropna(
                        subset=['Reported EPS', 'EPS Estimate']
                    )
                    if not past_ed.empty:
                        latest_ann = past_ed.sort_index(ascending=False).iloc[0]
                        ann_date = latest_ann.name
                        days_since_ann = (as_of_utc - ann_date).days

                        # Only apply within 90-day drift window
                        if days_since_ann <= 90:
                            if ('Surprise(%)' in latest_ann.index
                                    and pd.notna(latest_ann['Surprise(%)'])):
                                earnings_surprise_pct = float(latest_ann['Surprise(%)'])
                            else:
                                actual = float(latest_ann['Reported EPS'])
                                est    = float(latest_ann['EPS Estimate'])
                                if abs(est) > 0.001:
                                    earnings_surprise_pct = (actual - est) / abs(est) * 100
                            earnings_surprise_days = days_since_ann
            except Exception:
                pass

            results[sym] = {
                'ttm_revenue':           ttm_revenue,
                'roe':                   roe,
                'dte':                   dte,
                'pe':                    pe,
                'fcf_yield':             fcf_yield,
                'pledge_pct':            pledge_pct,
                'earnings_surprise_pct': earnings_surprise_pct,
                'earnings_surprise_days': earnings_surprise_days,
            }
        except Exception:
            results[sym] = {}

    return results


def build_annual_fundamentals_cache(
    symbols: List[str],
    rebal_dates: List[pd.Timestamp],
    all_prices: Dict[str, pd.Series],
) -> Dict[pd.Timestamp, Dict[str, Dict]]:
    """
    Build a point-in-time fundamentals cache refreshed once per calendar year.

    Structure: {snapshot_date: {sym_ns: {pe, eps_growth, roe, dte, quality_raw}}}

    quality_raw = ROE score + D/E score (0-75 scale, same as legacy quality_map)
    eps_growth  = YoY change in TTM EPS (requires 2 consecutive annual snapshots)
    pe          = historical price / TTM EPS at snapshot date

    No lookahead bias: all metrics use only data available on or before snapshot_date.
    """
    year_dates: Dict[int, pd.Timestamp] = {}
    for d in sorted(rebal_dates):
        if d.year not in year_dates:
            year_dates[d.year] = d

    # Fetch raw metrics for each year
    plain_syms = [s.replace('.NS', '') for s in symbols]
    year_raw: Dict[int, Dict[str, Dict]] = {}
    for yr, snap_date in sorted(year_dates.items()):
        print(f"  Fundamentals snapshot {yr} (as of {snap_date.strftime('%Y-%m')}) …")
        year_raw[yr] = get_point_in_time_fundamentals(plain_syms, snap_date, all_prices)

    # Second pass: compute EPS growth (current year vs prior year)
    cache: Dict[pd.Timestamp, Dict[str, Dict]] = {}
    for yr, snap_date in sorted(year_dates.items()):
        enriched: Dict[str, Dict] = {}
        curr_raw = year_raw[yr]
        prev_raw = year_raw.get(yr - 1, {})

        for sym_ns in symbols:
            sym = sym_ns.replace('.NS', '')
            c = curr_raw.get(sym, {})
            p = prev_raw.get(sym, {})

            roe = c.get('roe')
            dte = c.get('dte')
            pe  = c.get('pe')

            # Revenue growth YoY — prefer direct revenueGrowth from info fallback
            # otherwise compute from TTM revenue if both years are available
            rev_growth: Optional[float] = c.get('rev_growth_direct')  # from info fallback
            if rev_growth is None:
                rev_c = c.get('ttm_revenue')
                rev_p = p.get('ttm_revenue')
                if rev_c is not None and rev_p is not None and rev_p > 0:
                    rev_growth = (rev_c - rev_p) / rev_p

            # ROE change YoY — key quality-improvement signal
            roe_prev = p.get('roe')
            roe_growth: Optional[float] = None
            if roe is not None and roe_prev is not None and roe_prev != 0:
                roe_growth = (roe - roe_prev) / abs(roe_prev)

            # Legacy quality_raw score (0-75 scale) for backward compat
            roe_s = 0.0 if roe is None else float(min(40, max(0, roe * 100 / 25 * 40)))
            dte_s = 18.0 if dte is None else float(max(2, 35 - min(33, (dte / 100) * 35)))
            quality_raw = round(roe_s + dte_s, 1)

            enriched[sym_ns] = {
                'pe':                    pe,
                'roe':                   roe,
                'dte':                   dte,
                'rev_growth':            rev_growth,
                'roe_growth':            roe_growth,
                'quality_raw':           quality_raw,
                'fcf_yield':             c.get('fcf_yield'),
                'pledge_pct':            c.get('pledge_pct'),
                'earnings_surprise_pct':  c.get('earnings_surprise_pct'),
                'earnings_surprise_days': c.get('earnings_surprise_days'),
            }

        cache[snap_date] = enriched

    return cache


def lookup_fundamentals(
    cache: Dict[pd.Timestamp, Dict[str, Dict]],
    as_of_date: pd.Timestamp,
) -> Dict[str, Dict]:
    """Return the most recent fundamentals snapshot on or before as_of_date."""
    past = [d for d in cache if d <= as_of_date]
    if not past:
        return {}
    return cache[max(past)]


def _rev_growth_to_score(rev_growth: Optional[float]) -> float:
    """Map YoY revenue growth to 0-100 score. Graduated scale for Indian large-caps."""
    if rev_growth is None:
        return 50.0
    if rev_growth >= 0.25:  return 90.0
    if rev_growth >= 0.15:  return 75.0
    if rev_growth >= 0.07:  return 63.0
    if rev_growth >= 0.01:  return 54.0
    if rev_growth >= -0.05: return 44.0
    if rev_growth >= -0.15: return 30.0
    return 15.0


def _roe_growth_to_score(roe_growth: Optional[float]) -> float:
    """Map YoY ROE change % to 0-100 score. Improvement = rising score quality."""
    if roe_growth is None:
        return 50.0
    if roe_growth >= 0.20:  return 85.0
    if roe_growth >= 0.10:  return 70.0
    if roe_growth >= 0.02:  return 58.0
    if roe_growth >= -0.05: return 46.0
    if roe_growth >= -0.15: return 34.0
    return 20.0


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


def fetch_vix_prices(years: int) -> pd.Series:
    """Pre-fetch India VIX (^INDIAVIX) for M5 position-sizing scalar."""
    import yfinance as yf
    print(f"  Fetching India VIX history …")
    raw = yf.download("^INDIAVIX", period=f"{years + 1}y", auto_adjust=True, progress=False)
    if raw.empty:
        print("  WARNING: India VIX data unavailable — VIX scalar disabled")
        return pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw['Close']
        col = '^INDIAVIX' if '^INDIAVIX' in close.columns else close.columns[0]
        series = close[col].dropna()
    else:
        series = raw['Close'].dropna()
    print(f"  India VIX: {len(series)} trading days fetched")
    return series


def vix_scalar_at(vix_prices: pd.Series, as_of_date: pd.Timestamp) -> float:
    """Return position-count and sizing scalar based on India VIX level.

    VIX < 15:   full deployment (1.00)
    VIX 15-20:  mild caution   (0.85)
    VIX 20-25:  reduce risk    (0.65)
    VIX > 25:   defensive      (0.40)
    """
    if vix_prices.empty:
        return 1.0
    idx = vix_prices.index.get_indexer([as_of_date], method='ffill')[0]
    if idx < 0:
        return 1.0
    vix = float(vix_prices.iloc[idx])
    # Thresholds calibrated for India VIX (structurally 12-20 vs US 12-25)
    if vix < 18:
        return 1.0
    elif vix < 22:
        return 0.85
    elif vix < 26:
        return 0.65
    else:
        return 0.40


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
    """
    NSE Momentum 30 aligned cross-sectional momentum score.

    WHAT CHANGED (and why):
      Old formula: 1M(25%) + 3M(30%) + 6M(30%) + 12M(15%)
      Problem: 1M return has NEGATIVE alpha in Indian markets (short-term reversal).
               The system was in cash for the first 6 months of 2021 because
               1M/3M scores were low even as NIFTY surged +14%.

      New formula: Skip last 1 month entirely. Use 6M and 12M returns
                   normalized by their realized volatility (matches NSE Momentum 30).
                   The stock's absolute return is divided by its vol so a highly
                   volatile stock needs a bigger return to score equally.

    This function returns the single-stock score (0-100) using absolute thresholds.
    For full cross-sectional Z-scoring (relative to universe), use
    cross_sectional_momentum_scores() which should be called at the batch level.

    Even as a single-stock score this is dramatically better: excluding 1M
    removes the noise that kept the system in cash at bull market starts.
    """
    hist = prices.iloc[:as_of_idx + 1]
    n = len(hist)
    SKIP = 21  # skip last 1 month (reversal avoidance)

    def ret_skip(lookback_days: int) -> Optional[float]:
        """Return from (lookback+skip) ago to (skip) ago — avoids last month."""
        total = lookback_days + SKIP
        if n < total + 1:
            return None
        p_end   = hist.iloc[-(SKIP)]               # 1 month ago
        p_start = hist.iloc[-(total)]              # lookback ago
        return (p_end - p_start) / p_start if p_start > 0 else None

    def realized_vol(lookback_days: int) -> Optional[float]:
        """Annualised realized vol over the lookback window (skipping last month)."""
        total = lookback_days + SKIP
        if n < total + 2:
            return None
        period = hist.iloc[-(total):-(SKIP)]
        daily_ret = period.pct_change().dropna()
        if len(daily_ret) < 10:
            return None
        return float(daily_ret.std() * np.sqrt(252))

    # Raw returns (skip last month)
    r6  = ret_skip(126)   # 6M return, skip last 1M
    r12 = ret_skip(252)   # 12M return, skip last 1M

    if r6 is None and r12 is None:
        return None

    # Volatility normalization
    v6  = realized_vol(126) or 0.20   # fallback 20% if insufficient data
    v12 = realized_vol(252) or 0.20

    # Vol-normalized return (Sharpe-ratio-like signal)
    norm6  = (r6  / v6)  if r6  is not None else 0.0
    norm12 = (r12 / v12) if r12 is not None else 0.0

    # Convert to 0-100 score
    # Calibration: norm ≈ +0.5 (e.g. 10% return on 20% vol) → ~70 score
    #              norm ≈ +1.0 (e.g. 20% return on 20% vol) → ~85 score
    #              norm ≈ -0.5                               → ~30 score
    #              norm =  0                                 → 50 (neutral)
    def norm_to_score(x: float) -> float:
        # Sigmoid-style mapping: capped at 5 (norm) → 100
        capped = float(np.clip(x, -3.0, 3.0))
        return float(50 + 18 * capped - 2 * capped ** 3)  # smooth S-curve

    s6  = norm_to_score(norm6)
    s12 = norm_to_score(norm12)

    # Equal-weight 6M and 12M (mirrors NSE Momentum 30)
    combined = 0.5 * s6 + 0.5 * s12
    return float(np.clip(combined, 0.0, 100.0))


def cross_sectional_momentum_scores(
    all_prices: Dict[str, pd.Series],
    as_of_date: pd.Timestamp,
    pit_universe: set,
) -> Dict[str, float]:
    """
    Cross-sectional Z-score momentum for the entire universe at a point in time.
    More accurate than single-stock absolute scoring — eliminates market-wide bias.

    Returns: {symbol: cross_sectional_score 0-100} for all scorable symbols.
    """
    SKIP = 21
    raw: Dict[str, Tuple[Optional[float], Optional[float]]] = {}

    for sym in pit_universe:
        series = all_prices.get(sym)
        if series is None or series.empty:
            continue
        idx = series.index.get_indexer([as_of_date], method='ffill')[0]
        if idx < 0:
            continue
        hist = series.iloc[:idx + 1]
        n = len(hist)

        def ret_skip(lb):
            total = lb + SKIP
            if n < total + 1: return None
            p1 = hist.iloc[-SKIP]; p0 = hist.iloc[-total]
            return (p1 - p0) / p0 if p0 > 0 else None

        def vol_norm(lb):
            total = lb + SKIP
            if n < total + 2: return None
            d = hist.iloc[-total:-SKIP].pct_change().dropna()
            return float(d.std() * np.sqrt(252)) if len(d) >= 10 else None

        r6 = ret_skip(126); v6 = vol_norm(126) or 0.20
        r12 = ret_skip(252); v12 = vol_norm(252) or 0.20

        norm6  = (r6  / v6)  if r6  is not None else None
        norm12 = (r12 / v12) if r12 is not None else None
        raw[sym] = (norm6, norm12)

    # Cross-sectional Z-score each dimension
    vals6  = [v for v, _ in raw.values() if v is not None]
    vals12 = [v for _, v in raw.values() if v is not None]
    m6, s6   = (np.mean(vals6),  np.std(vals6))  if vals6  else (0, 1)
    m12, s12 = (np.mean(vals12), np.std(vals12)) if vals12 else (0, 1)

    result: Dict[str, float] = {}
    for sym, (n6, n12) in raw.items():
        z6  = ((n6  - m6)  / s6)  if n6  is not None and s6  > 0 else 0.0
        z12 = ((n12 - m12) / s12) if n12 is not None and s12 > 0 else 0.0
        combined_z = 0.5 * z6 + 0.5 * z12
        # Map z-score to 0-100: z=+2 → ~98th percentile
        from scipy.stats import norm as _norm
        percentile = float(_norm.cdf(combined_z)) * 100
        result[sym] = float(np.clip(percentile, 0, 100))

    return result


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


STRONG_BUY_THRESHOLD = 75.0   # score ≥ 75 → larger initial allocation + 1.3× weight


def vol_adjusted_weights(
    holdings: Dict[str, Dict],
    prices: Dict[str, pd.Series],
    score_map: Dict[str, float],
    as_of_date: pd.Timestamp,
    strong_buy_threshold: float = STRONG_BUY_THRESHOLD,
    vol_window: int = 60,
    cap: float = 0.20,
) -> Dict[str, float]:
    """
    Score-over-vol weights: weight_i ∝ score_i / annualised_vol_i.

    Lower-volatility stocks get proportionally more weight for the same score —
    NESTLEIND (18% vol) and HINDALCO (35% vol) with equal scores no longer get
    equal weight. STRONG_BUY positions get a 1.3× conviction multiplier.

    Caps at 20% per position; redistributes surplus to uncapped positions.
    Falls back to equal weight if vol data is unavailable.
    """
    vols: Dict[str, float] = {}
    for sym in holdings:
        p = prices.get(sym)
        if p is None or p.empty:
            vols[sym] = 0.20
            continue
        idx = p.index.get_indexer([as_of_date], method='ffill')[0]
        if idx < vol_window:
            vols[sym] = 0.20
            continue
        daily_ret = p.iloc[max(0, idx - vol_window): idx + 1].pct_change().dropna()
        ann_vol = float(daily_ret.std() * np.sqrt(252)) if len(daily_ret) >= 10 else 0.20
        vols[sym] = max(0.05, ann_vol)  # floor at 5% to avoid division blow-up

    raw: Dict[str, float] = {}
    for sym, h in holdings.items():
        score = max(1.0, score_map.get(sym, h.get('entry_score', 50.0)))
        tier_mult = 1.3 if h.get('entry_tier') == 'STRONG_BUY' else 1.0
        raw[sym] = (score / vols[sym]) * tier_mult

    total = sum(raw.values())
    if total <= 0:
        n = len(holdings)
        return {sym: 1.0 / n for sym in holdings}

    normalized = {sym: v / total for sym, v in raw.items()}

    capped: Dict[str, float] = {}
    surplus = 0.0
    for sym, w in normalized.items():
        if w > cap:
            surplus += w - cap
            capped[sym] = cap
        else:
            capped[sym] = w

    uncapped = [s for s, w in capped.items() if w < cap]
    if uncapped and surplus > 0:
        add_each = surplus / len(uncapped)
        for sym in uncapped:
            capped[sym] = min(cap, capped[sym] + add_each)

    return capped


def nifty_200dma_regime(nifty_prices: pd.Series, as_of_idx: int) -> Dict:
    """
    NIFTY 200-DMA regime filter — the most evidence-backed rule in Indian systematic investing.

    Returns a dict with max_positions and max_equity_pct:
      BULL     (price > 200-DMA AND > 50-DMA): full deployment allowed
      SIDEWAYS (price > 200-DMA, < 50-DMA):   moderate caution
      BEAR     (price < 200-DMA):              defensive mode

    Research: Capitalmind, NSE factor index whitepapers, and our own backtest
    analysis show that being fully invested when NIFTY is below its 200-DMA
    is the #1 source of avoidable alpha loss. This single filter would have
    avoided most of the 2022 bear market losses and the Feb 2026 crash.
    """
    hist = nifty_prices.iloc[:as_of_idx + 1]
    defaults = {'regime': 'SIDEWAYS', 'max_positions': 7, 'max_equity': 0.75}

    if len(hist) < 200:
        return defaults

    price  = float(hist.iloc[-1])
    sma200 = float(hist.iloc[-200:].mean())
    sma50  = float(hist.iloc[-50:].mean())  if len(hist) >= 50 else sma200

    if price < sma200 * 0.98:          # clearly below 200-DMA
        return {'regime': 'BEAR',     'max_positions': 4, 'max_equity': 0.50}
    elif price < sma50:                 # below 50-DMA but above 200-DMA
        return {'regime': 'SIDEWAYS', 'max_positions': 7, 'max_equity': 0.75}
    else:                              # healthy bull — above both SMAs
        return {'regime': 'BULL',     'max_positions': 10, 'max_equity': 0.90}


def event_risk_scalar(as_of_date: pd.Timestamp) -> float:
    """
    Reduce equity exposure during high-risk calendar events.

    Budget Day (Feb 1) is the single most binary event in the Indian calendar.
    Feb 2026: NIFTY dropped on STT hike. Being fully invested into budget week
    with 7 concentrated positions turned a -5% market move into -13.1%.

    Returns a scalar (0.60–1.0) to multiply against target position sizes.
    """
    m, d = as_of_date.month, as_of_date.day

    # Budget window: Jan 26 – Feb 5 (include pre-budget positioning)
    if (m == 1 and d >= 26) or (m == 2 and d <= 5):
        return 0.65   # reduce to 65% of normal position sizes

    # RBI MPC typically meets in Feb, Apr, Jun, Aug, Oct, Dec
    # Use a calendar-based approximation: first week of even months
    rbi_months = {2, 4, 6, 8, 10, 12}
    if m in rbi_months and 5 <= d <= 12:  # MPC week (announced ~10th)
        return 0.85

    return 1.0  # normal


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
# Correlation Guard
# ─────────────────────────────────────────────────────────────────────────────

def portfolio_correlation_guard(
    candidate: str,
    holdings: Dict[str, Any],
    prices: Dict[str, pd.Series],
    as_of_date: pd.Timestamp,
    window: int = 60,
    max_corr: float = 0.70,
    max_correlated_peers: int = 2,
) -> bool:
    """
    Return True (block entry) when the candidate stock has correlation > max_corr
    with more than max_correlated_peers stocks already held.

    Motivation: Jan-2025 -10% month happened because SUNPHARMA, TCS, ITC, BEL
    all fell together — 4 defensives with hidden pairwise correlation. A rolling
    60-day window captures the regime-specific correlation that sector labels miss
    (e.g. PSU stocks all move together during government budget uncertainty even
    if they are in different sectors).

    Parameters
    ----------
    candidate        : symbol to evaluate for entry
    holdings         : current held stocks dict
    prices           : all price series (keyed by sym.NS or plain sym)
    as_of_date       : evaluation date
    window           : rolling daily return window (default 60 trading days)
    max_corr         : pairwise correlation threshold (default 0.70)
    max_correlated_peers : block if candidate correlates > max_corr with this
                           many current holdings (default 2)
    """
    if len(holdings) < 2:
        return False  # need at least 2 existing holdings to form a meaningful check

    def _ret_series(sym: str) -> Optional[pd.Series]:
        # Try sym.NS first then bare sym
        for key in (f"{sym}.NS", sym):
            p = prices.get(key)
            if p is not None and not p.empty:
                idx = p.index.get_indexer([as_of_date], method='ffill')[0]
                if idx >= window:
                    rets = p.iloc[idx - window: idx + 1].pct_change().dropna()
                    if len(rets) >= window // 2:
                        return rets
        return None

    cand_rets = _ret_series(candidate)
    if cand_rets is None:
        return False  # no data → don't block

    high_corr_count = 0
    for held_sym in holdings:
        held_rets = _ret_series(held_sym)
        if held_rets is None:
            continue
        # Align on common dates
        common = cand_rets.index.intersection(held_rets.index)
        if len(common) < window // 2:
            continue
        corr = float(np.corrcoef(cand_rets.loc[common], held_rets.loc[common])[0, 1])
        if corr > max_corr:
            high_corr_count += 1
            if high_corr_count >= max_correlated_peers:
                return True  # block

    return False


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
    quality_cache: Optional[Dict] = None,
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

        # Point-in-time universe: only score stocks valid in NIFTY50 on date_t
        pit_universe = set(get_universe_at_date(date_t))

        # Use annual quality snapshot if cache provided, else fall back to static map
        active_quality = lookup_quality(quality_cache, date_t) if quality_cache else quality_map

        score_map: Dict[str, float] = {}
        scored: List[Tuple[str, float]] = []
        inr_s = inr_prices if inr_prices is not None else pd.Series(dtype=float)
        rbi_h = rbi_history or []
        for sym, price_series in prices.items():
            if sym not in pit_universe:
                continue  # not in NIFTY50 at this date — skip (survivorship bias fix)
            idx = price_series.index.get_indexer([date_t], method='ffill')[0]
            if idx < 63:
                continue
            m_adj = macro_adj_for_stock(sym, date_t, inr_s, rbi_h)
            score = composite_score_at(
                sym, price_series, idx, active_quality, mom_w, qual_w, m_adj,
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
        if not new_holdings:
            # All-cash month: earn liquid fund rate instead of 0%
            port_ret = CASH_MONTHLY_RATE
        else:
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
    sell_threshold: float = 40.0,
    stop_loss: float = 0.10,
    max_positions: int = 10,
    transaction_cost: float = 0.001,
    sector_cap: float = 0.30,
    inr_prices: Optional[pd.Series] = None,
    rbi_history: Optional[List[Dict]] = None,
    quality_cache: Optional[Dict] = None,
    fundamentals_cache: Optional[Dict] = None,
    use_200dma_filter: bool = True,
    use_event_calendar: bool = True,
    use_cross_sectional: bool = True,
    use_backtest_scorer: bool = True,
    min_hold_months: int = 3,
    profit_trail_pct: float = 0.12,
    profit_trigger_pct: float = 0.20,
    strong_buy_threshold: float = STRONG_BUY_THRESHOLD,
    rs_exit_enabled: bool = False,
    rs_exit_percentile: float = 0.30,
    rs_exit_strikes: int = 3,
    m2_exit_enabled: bool = False,
    m2_underperform_threshold: float = 0.15,
    m2_exit_strikes: int = 2,
    m4_circuit_enabled: bool = False,
    m4_dd_threshold: float = 0.08,
    m5_vix_enabled: bool = False,
    vix_prices: Optional[pd.Series] = None,
    # M3: maximum holding period with progressive score hurdle
    m3_maxhold_enabled: bool = False,
    m3_12m_decay: float = 10.0,   # pts below entry_score allowed at 12M
    m3_18m_decay: float = 5.0,    # pts below entry_score allowed at 18M
    # M6: opportunity cost active rotation
    m6_rotation_enabled: bool = False,
    m6_rotation_gap: float = 12.0,  # min score gap to trigger rotation
    # M7: factor concentration HHI gate
    m7_hhi_enabled: bool = False,
    m7_hhi_threshold: float = 0.35,  # HHI > this blocks new entry in crowded bucket
    # M3 re-entry cooldown: block re-entry for N months after an M3 exit
    m3_cooldown_months: int = 0,      # 0 = disabled; 6 = aligned with live system
    # M1 sector rotation guard: pause strike accumulation when a stock's entire
    # sector is beating NIFTY on 3M basis — avoids exiting sector-trough dips
    m1_sector_guard: bool = False,
    # Correlation guard: block entry when candidate correlates > corr_max_threshold
    # with more than corr_max_peers existing holdings (60-day rolling window)
    corr_guard_enabled: bool = True,
    corr_max_threshold: float = 0.70,
    corr_max_peers: int = 2,
    # Earnings surprise: disable the ±8pt PIT adjustment in BacktestScorer
    use_earnings_surprise_disabled: bool = False,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Signal-driven portfolio simulation v4 — fully live-system aligned.

    Scoring (BacktestScorer when use_backtest_scorer=True):
      composite = 0.36×fundamentals + 0.27×momentum + 0.18×quality + 9.5 + macro + rs_adj
      (mirrors StockScorer live weights: funds 36%, momentum 27%, quality 18%,
       sentiment 9% → 50 neutral, inst_flow 10% → 50 neutral)

    Exit logic (ordered by priority):
      1. Hard stop-loss: down > stop_loss% from entry → instant exit
      2. Profit protection: up > profit_trigger% at peak, then drops > profit_trail% → exit
         (locks in gains — avoids "turned winner into loser" scenario)
      3. Score thesis broken: score < sell_threshold AND held ≥ min_hold_months → exit
         (min_hold prevents false exits in volatile months during new positions)
      3.5 M3 max hold: score must clear progressive hurdle at 12M / 18M / 24M (optional)
      4. Budget/event trim: reduce positions before budget day / big event windows
      M6 rotation (optional): replace lowest-scoring held stock if better candidate exists
      M7 HHI gate (optional): blocks new entries that would crowd a factor bucket

    Entry logic:
      STRONG BUY (score ≥ strong_buy_threshold): 1.3× weight, labeled STRONG_BUY
      BUY         (score ≥ buy_threshold):         standard weight, labeled BUY
      Regime boost raises threshold in BEAR (+10), SIDEWAYS (+3)
      Event scalar raises threshold further during budget (+8) / RBI (+4) windows

    Position sizing:
      score / annualised_vol weights (lower vol = more weight for same score)
      Cap 20% per position; STRONG_BUY tier gets 1.3× multiplier

    Cash earns 6.5% p.a. (Indian liquid fund proxy).
    """
    rebal_dates = get_rebalance_dates(prices, bench)
    if len(rebal_dates) < 2:
        raise ValueError("Not enough rebalance dates")

    bench_at = {d: bench.get(d) for d in rebal_dates}
    portfolio_values: List[Tuple[pd.Timestamp, float]] = [(rebal_dates[0], 100.0)]
    holdings: Dict[str, Dict] = {}  # sym → {entry_price, entry_score, entry_date, peak_price, entry_tier, event_entry}
    pv = 100.0
    trade_log: List[Dict] = []
    # M1: consecutive months each held stock has been in the bottom rs_exit_percentile
    rs_strike_count: Dict[str, int] = {}
    # M2: consecutive months each held stock has underperformed NIFTY 12M return by > threshold
    m2_strike_count: Dict[str, int] = {}
    m2_latest_lag: Dict[str, float] = {}  # most recent underperformance value for exit message
    # M3 re-entry cooldown: {sym → earliest date it may re-enter after an M3 exit}
    m3_cooldown_until: Dict[str, pd.Timestamp] = {}
    # M4: monthly drawdown circuit breaker state
    m4_in_circuit: bool = False          # True when circuit is active
    m4_circuit_pv: float = 100.0         # portfolio value when circuit was triggered
    last_period_ret: float = 0.0         # return of the just-completed period
    _vix_prices: pd.Series = vix_prices if vix_prices is not None else pd.Series(dtype=float)

    for i in range(len(rebal_dates) - 1):
        date_t  = rebal_dates[i]
        date_t1 = rebal_dates[i + 1]

        bench_idx = bench.index.get_indexer([date_t], method='ffill')[0]
        regime, mom_w, qual_w = detect_regime_at(bench, bench_idx) if bench_idx >= 0 else ('SIDEWAYS', 0.55, 0.45)

        # ── NIFTY 200-DMA regime filter ─────────────────────────────────────
        dma_info = nifty_200dma_regime(bench, bench_idx) if use_200dma_filter and bench_idx >= 0 else {
            'regime': regime, 'max_positions': max_positions, 'max_equity': 1.0
        }
        effective_max_positions = min(max_positions, dma_info['max_positions'])
        dma_regime = dma_info['regime']

        # ── M5: India VIX scalar — preventive position count reduction ───────
        # Reduces effective_max_positions before the market moves (forward-looking
        # signal, fires 2-3 weeks before 200-DMA breaks in typical crash sequences).
        if m5_vix_enabled:
            vix_s = vix_scalar_at(_vix_prices, date_t)
            effective_max_positions = max(2, round(effective_max_positions * vix_s))
        else:
            vix_s = 1.0

        # ── M4: Monthly drawdown circuit breaker — reactive risk control ─────
        # If the PREVIOUS period lost > m4_dd_threshold → activate circuit:
        # hard-cap positions to 2 and skip all new entries this period.
        # Circuit clears once portfolio recovers above the trigger level.
        if m4_circuit_enabled:
            if last_period_ret < -m4_dd_threshold and not m4_in_circuit:
                m4_in_circuit = True
                m4_circuit_pv  = pv
            if m4_in_circuit and pv >= m4_circuit_pv * (1 - m4_dd_threshold * 0.5):
                m4_in_circuit = False
            if m4_in_circuit:
                effective_max_positions = min(effective_max_positions, 2)

        # ── Event calendar risk scalar ──────────────────────────────────────
        ev_scalar = event_risk_scalar(date_t) if use_event_calendar else 1.0

        # ── Point-in-time universe & data snapshots ─────────────────────────
        pit_universe = set(get_universe_at_date(date_t))

        # Resolve which data snapshot to use:
        # BacktestScorer path: fundamentals_cache has PE, EPS growth, ROE, D/E
        # Legacy path: quality_cache / quality_map
        if use_backtest_scorer and fundamentals_cache:
            fund_snap = lookup_fundamentals(fundamentals_cache, date_t)
            # Derive quality_snap (0-75 scale) from fundamentals cache for regime weights
            active_quality: Dict[str, float] = {
                sym: v.get('quality_raw', 25.0) for sym, v in fund_snap.items()
            }
        else:
            fund_snap = {}
            active_quality = lookup_quality(quality_cache, date_t) if quality_cache else quality_map

        # ── Cross-sectional momentum (NSE Momentum 30 aligned) ──────────────
        cs_scores: Dict[str, float] = {}
        if use_cross_sectional:
            cs_scores = cross_sectional_momentum_scores(prices, date_t, pit_universe)

        # ── Cross-sectional fundamental ranks within PIT universe ────────────
        # ROE rank: higher ROE → better score (quality premium)
        # P/E rank: lower P/E → better score (value premium, when data available)
        roe_ranks: Dict[str, float] = {}
        pe_ranks:  Dict[str, float] = {}
        if use_backtest_scorer and fund_snap:
            roe_vals: List[Tuple[str, float]] = []
            pe_vals:  List[Tuple[str, float]] = []
            for sym in pit_universe:
                fund = fund_snap.get(sym, {})
                roe = fund.get('roe')
                pe  = fund.get('pe')
                if roe is not None:
                    roe_vals.append((sym, roe))
                if pe is not None and 0 < pe < 200:
                    pe_vals.append((sym, pe))

            # ROE rank: descending (higher ROE = better)
            roe_sorted = sorted(roe_vals, key=lambda x: x[1], reverse=True)
            n_roe = len(roe_sorted)
            for rank_i, (sym, _) in enumerate(roe_sorted):
                roe_ranks[sym] = (n_roe - rank_i) / max(n_roe, 1) * 100

            # P/E rank: ascending (lower P/E = better, value premium)
            pe_sorted = sorted(pe_vals, key=lambda x: x[1])
            n_pe = len(pe_sorted)
            for rank_i, (sym, _) in enumerate(pe_sorted):
                pe_ranks[sym] = (n_pe - rank_i) / max(n_pe, 1) * 100

        # ── Build score map for all stocks ───────────────────────────────────
        score_map: Dict[str, float] = {}
        inr_s = inr_prices if inr_prices is not None else pd.Series(dtype=float)
        rbi_h = rbi_history or []

        for sym, price_series in prices.items():
            if sym not in pit_universe:
                continue
            idx = price_series.index.get_indexer([date_t], method='ffill')[0]
            if idx < 63:
                continue

            # Momentum component (cross-sectional Z-score preferred)
            if use_cross_sectional and sym in cs_scores:
                mom_raw = cs_scores[sym]
            else:
                mom_raw = momentum_score_at(price_series, idx) or 50.0

            # RS acceleration
            rs_adj = 0.0
            if bench_idx >= 0:
                rs_adj = rs_acceleration_score_at(price_series, bench, idx, bench_idx)

            m_adj = macro_adj_for_stock(sym, date_t, inr_s, rbi_h)

            if use_backtest_scorer and fund_snap:
                # ── BacktestScorer: live-aligned weights 0.36F + 0.27M + 0.18Q + 9.5 ──
                fund = fund_snap.get(sym, {})

                # Fundamentals score (0-100)
                # ROE rank (cross-sectional within PIT universe): 40% — quality premium
                # Revenue growth YoY:                             35% — business health
                # ROE quality improvement (YoY change):          25% — improving vs declining
                roe_rank_score = roe_ranks.get(sym, 50.0)
                rev_score      = _rev_growth_to_score(fund.get('rev_growth'))
                roe_delta_score = _roe_growth_to_score(fund.get('roe_growth'))

                # If P/E data is available, blend 15% value premium
                if sym in pe_ranks:
                    fund_score = float(np.clip(
                        0.35 * roe_rank_score
                        + 0.30 * rev_score
                        + 0.20 * roe_delta_score
                        + 0.15 * pe_ranks[sym],
                        0.0, 100.0
                    ))
                else:
                    fund_score = float(np.clip(
                        0.40 * roe_rank_score
                        + 0.35 * rev_score
                        + 0.25 * roe_delta_score,
                        0.0, 100.0
                    ))

                # Quality score normalized 0-100 (ROE + D/E component, max ~75 raw)
                qual_raw   = active_quality.get(sym, 25.0)
                qual_score = float(min(100.0, qual_raw / 75.0 * 100.0))

                # Earnings surprise adjustment (±8 pts, 90-day decay)
                # PIT-safe: only uses surprise announcements on or before as_of_date.
                # Mirrors live SentimentAgent._score_earnings_surprise() logic.
                # Applied at 0.09 weight (sentiment agent proxy) scaled to ±8 pts.
                surp_pct  = fund.get('earnings_surprise_pct')
                surp_days = fund.get('earnings_surprise_days')
                earnings_adj = 0.0
                if (not use_earnings_surprise_disabled
                        and surp_pct is not None
                        and surp_days is not None
                        and surp_days <= 90):
                    decay = max(0.0, 1.0 - surp_days / 90.0)
                    if surp_pct >= 10:
                        base = 8.0
                    elif surp_pct >= 5:
                        base = 5.0
                    elif surp_pct >= 2:
                        base = 2.5
                    elif surp_pct >= -1:
                        base = 0.0
                    elif surp_pct >= -5:
                        base = -4.0
                    else:
                        base = -8.0
                    earnings_adj = round(base * decay, 2)

                composite = float(np.clip(
                    0.36 * fund_score
                    + 0.27 * mom_raw
                    + 0.18 * qual_score
                    + 9.5           # 0.09×50 (sentiment neutral) + 0.10×50 (inst_flow neutral)
                    + m_adj
                    + rs_adj
                    + earnings_adj,
                    0.0, 100.0
                ))
            else:
                # ── Legacy formula: regime-weighted momentum + quality ──────
                qual_raw = active_quality.get(sym, 25.0)
                composite = float(np.clip(
                    mom_w * mom_raw + qual_w * qual_raw + m_adj + rs_adj,
                    0.0, 100.0
                ))

            score_map[sym] = composite

        # ── M1: Relative rank degradation — update strike counts ────────────
        # Compute 6M trailing return rank (percentile) for all PIT universe stocks.
        # Held stocks below rs_exit_percentile accumulate a strike; above resets to 0.
        # Three consecutive strikes → RS degradation exit (catches value/momentum traps).
        #
        # Sector rotation guard (m1_sector_guard=True):
        # If the held stock's SECTOR has positive 3M RS vs NIFTY, pause strike
        # accumulation for stocks in that sector. A stock ranking low because its
        # whole sector was in a cyclical trough (e.g., IT in 2024) should not be
        # exited — it's waiting for a sector re-rating, not deteriorating individually.
        if rs_exit_enabled:
            rs_6m_returns: List[Tuple[str, float]] = []
            # Also collect 3M returns for sector RS guard
            rs_3m_by_sym: Dict[str, float] = {}
            for sym in pit_universe:
                p_ser = prices.get(sym)
                if p_ser is None:
                    continue
                idx_now = p_ser.index.get_indexer([date_t], method='ffill')[0]
                idx_6m  = idx_now - 126  # ~6 months of trading days
                idx_3m  = idx_now - 63   # ~3 months
                if idx_now < 0 or idx_6m < 0:
                    continue
                p_now = float(p_ser.iloc[idx_now])
                p_6m  = float(p_ser.iloc[idx_6m])
                if p_6m > 0:
                    rs_6m_returns.append((sym, (p_now - p_6m) / p_6m))
                if idx_3m >= 0:
                    p_3m = float(p_ser.iloc[idx_3m])
                    if p_3m > 0:
                        rs_3m_by_sym[sym] = (p_now - p_3m) / p_3m

            rs_6m_returns.sort(key=lambda x: x[1])
            n_rs = len(rs_6m_returns)
            rs_pct_rank: Dict[str, float] = {
                sym: rank / max(n_rs - 1, 1)
                for rank, (sym, _) in enumerate(rs_6m_returns)
            }

            # Compute sector 3M RS vs NIFTY (for sector rotation guard)
            sector_recovering: Dict[str, bool] = {}
            if m1_sector_guard:
                bench_idx_now = bench.index.get_indexer([date_t], method='ffill')[0]
                bench_idx_3m  = bench_idx_now - 63
                nifty_3m = 0.0
                if bench_idx_now >= 0 and bench_idx_3m >= 0:
                    b_now = float(bench.iloc[bench_idx_now])
                    b_3m  = float(bench.iloc[bench_idx_3m])
                    nifty_3m = (b_now - b_3m) / b_3m if b_3m > 0 else 0.0

                # Average 3M return per sector across all universe stocks
                sector_returns: Dict[str, List[float]] = {}
                for sym in pit_universe:
                    sec = NIFTY50_SECTORS.get(sym, 'Other')
                    r3m = rs_3m_by_sym.get(sym)
                    if r3m is not None:
                        sector_returns.setdefault(sec, []).append(r3m)
                for sec, rets in sector_returns.items():
                    avg_3m = sum(rets) / len(rets) if rets else 0.0
                    # Sector is "recovering" if its avg 3M return beats NIFTY 3M
                    sector_recovering[sec] = avg_3m > nifty_3m

            for sym in list(holdings.keys()):
                rank = rs_pct_rank.get(sym)
                if rank is None:
                    continue
                if rank < rs_exit_percentile:
                    # Sector guard: pause strike if the stock's sector is recovering
                    if m1_sector_guard:
                        sec = NIFTY50_SECTORS.get(sym, 'Other')
                        if sector_recovering.get(sec, False):
                            # Sector is outperforming NIFTY — this stock's low rank
                            # may be temporary sector rotation, not permanent decay.
                            # Don't accumulate a strike this month.
                            rs_strike_count[sym] = max(0, rs_strike_count.get(sym, 0) - 1)
                            continue
                    rs_strike_count[sym] = rs_strike_count.get(sym, 0) + 1
                else:
                    rs_strike_count[sym] = 0

        # ── M2: 12M price momentum override — update strike counts ──────────
        # Compare each held stock's 12M trailing return vs NIFTY 12M return.
        # Stocks lagging NIFTY by > m2_underperform_threshold for m2_exit_strikes
        # consecutive months exit as momentum_trap (catches ITC-style value traps).
        nifty_12m_ret: Optional[float] = None
        if m2_exit_enabled:
            idx_bench_now = bench.index.get_indexer([date_t], method='ffill')[0]
            idx_bench_12m = idx_bench_now - 252  # ~12 months of trading days
            if idx_bench_now >= 0 and idx_bench_12m >= 0:
                b_now = float(bench.iloc[idx_bench_now])
                b_12m = float(bench.iloc[idx_bench_12m])
                if b_12m > 0:
                    nifty_12m_ret = (b_now - b_12m) / b_12m

            for sym in list(holdings.keys()):
                p_ser = prices.get(sym)
                if p_ser is None or nifty_12m_ret is None:
                    continue
                idx_now = p_ser.index.get_indexer([date_t], method='ffill')[0]
                idx_12m = idx_now - 252
                if idx_now < 0 or idx_12m < 0:
                    continue
                p_now = float(p_ser.iloc[idx_now])
                p_12m = float(p_ser.iloc[idx_12m])
                if p_12m <= 0:
                    continue
                stock_12m_ret = (p_now - p_12m) / p_12m
                underperform = nifty_12m_ret - stock_12m_ret
                m2_latest_lag[sym] = underperform
                if underperform > m2_underperform_threshold:
                    m2_strike_count[sym] = m2_strike_count.get(sym, 0) + 1
                else:
                    m2_strike_count[sym] = 0

        # ── Update peak_price high watermark for all holdings ────────────────
        for sym, h in holdings.items():
            p_ser = prices.get(sym)
            if p_ser is not None:
                pidx = p_ser.index.get_indexer([date_t], method='ffill')[0]
                if pidx >= 0:
                    curr_p = float(p_ser.iloc[pidx])
                    if curr_p > h.get('peak_price', h['entry_price']):
                        h['peak_price'] = curr_p

        exits: List[str] = []
        exit_reasons: Dict[str, str] = {}

        # ── Step 1a: Budget/event trim — reduce exposure before big events ────
        # Trim lowest-scored positions so portfolio fits within ev_scalar × current size.
        # Only fires when ev_scalar < 0.75 (budget window) and we have >2 positions.
        if use_event_calendar and ev_scalar < 0.75 and len(holdings) > 2:
            held_scored = sorted(
                [(s, score_map.get(s, h.get('entry_score', 0))) for s, h in holdings.items()],
                key=lambda x: x[1]
            )
            target_size = max(2, round(len(holdings) * ev_scalar))
            trim_count  = len(holdings) - target_size
            for sym, _ in held_scored[:trim_count]:
                if sym not in exits:
                    exits.append(sym)
                    exit_reasons[sym] = 'event_trim'

        # ── Step 1a-M4: Circuit breaker trim — reduce existing holdings ────────
        # Fires when the PREVIOUS period return was below -m4_dd_threshold.
        # Actively exits bottom-scored positions until holdings ≤ circuit cap (2),
        # freeing capital to cash. Without this, "cap new entries" alone doesn't
        # reduce existing exposure and misses the bad month entirely.
        if m4_circuit_enabled and m4_in_circuit and len(holdings) > 2:
            circuit_cap = 2
            held_not_exiting = [(s, score_map.get(s, h.get('entry_score', 0)))
                                 for s, h in holdings.items() if s not in exits]
            held_not_exiting.sort(key=lambda x: x[1])
            trim_count = len(held_not_exiting) - circuit_cap
            for sym, _ in held_not_exiting[:max(0, trim_count)]:
                exits.append(sym)
                exit_reasons[sym] = f'circuit_trim(dd>{m4_dd_threshold*100:.0f}%)'

        # ── Step 1b: Hard exits — stop-loss, profit-protect, thesis-broken ───
        for sym, h in list(holdings.items()):
            if sym in exits:  # already marked for event_trim
                continue
            p_series = prices.get(sym)
            if p_series is None:
                exits.append(sym); exit_reasons[sym] = 'no_data'; continue
            idx_t = p_series.index.get_indexer([date_t], method='ffill')[0]
            if idx_t < 0:
                exits.append(sym); exit_reasons[sym] = 'no_data'; continue

            current_price   = float(p_series.iloc[idx_t])
            entry_price     = h['entry_price']
            peak_price      = h.get('peak_price', entry_price)
            ret_from_entry  = (current_price - entry_price) / entry_price
            ret_from_peak   = (current_price - peak_price)  / peak_price  if peak_price > 0 else 0.0
            current_score   = score_map.get(sym, 0.0)
            months_held     = (date_t - h.get('entry_date', date_t)).days / 30.5

            # Priority 1: Hard stop-loss (always fires, no grace period)
            if ret_from_entry < -stop_loss:
                exits.append(sym)
                exit_reasons[sym] = f'stop_loss({ret_from_entry*100:.1f}%)'

            # Priority 2: Profit protection — trailing stop on winners
            # Activates only once the position has gained > profit_trigger_pct at its peak.
            # Then protects if it pulls back > profit_trail_pct from that peak.
            # Rationale: "let winners run, but don't turn a +25% winner into a -5% loser."
            elif (peak_price >= entry_price * (1 + profit_trigger_pct)
                  and ret_from_peak < -profit_trail_pct):
                exits.append(sym)
                peak_gain = (peak_price / entry_price - 1) * 100
                pullback  = abs(ret_from_peak) * 100
                exit_reasons[sym] = f'profit_protect(pk+{peak_gain:.0f}%,pb-{pullback:.0f}%)'

            # Priority 2.5: M1 — Relative rank degradation exit
            # Fires when RS rank has been below rs_exit_percentile for rs_exit_strikes
            # consecutive months. Catches value traps and dead momentum stocks where
            # the composite score still looks marginal but price action says otherwise.
            elif rs_exit_enabled and rs_strike_count.get(sym, 0) >= rs_exit_strikes:
                exits.append(sym)
                pct_rank = rs_pct_rank.get(sym, 0.0) * 100
                exit_reasons[sym] = f'rs_degradation(rank{pct_rank:.0f}th,{rs_strike_count[sym]}mo)'

            # Priority 2.7: M2 — 12M momentum trap exit
            # Fires when stock has underperformed NIFTY by > threshold for consecutive
            # months. Complements M1 (rank-based) with an absolute benchmark test —
            # catches ITC-style stocks that look cheap but bleed alpha for 2+ years.
            elif m2_exit_enabled and m2_strike_count.get(sym, 0) >= m2_exit_strikes:
                exits.append(sym)
                lag = m2_latest_lag.get(sym, 0.0)
                exit_reasons[sym] = f'momentum_trap(lag{lag*100:.0f}%,{m2_strike_count[sym]}mo)'

            # Priority 2.9: M3 — Maximum holding period with progressive score hurdle
            # After 12M a position must still "earn" its place vs its own entry conviction.
            # At 24M it must beat the 75th percentile of the universe — still-excellent
            # stocks will pass; sideways value traps (ITC) will fail and be exited.
            # Fires only if no higher-priority exit has already been triggered.
            elif m3_maxhold_enabled:
                m3_fired = False
                if months_held >= 24:
                    sorted_scores = sorted(score_map.values())
                    idx_75 = int(len(sorted_scores) * 0.75)
                    universe_75th = sorted_scores[idx_75] if idx_75 < len(sorted_scores) else sell_threshold
                    if current_score < universe_75th:
                        exits.append(sym)
                        exit_reasons[sym] = f'm3_24mo({current_score:.0f}<75p:{universe_75th:.0f})'
                        m3_fired = True
                elif months_held >= 18:
                    min_score_18m = max(sell_threshold, h['entry_score'] - m3_18m_decay)
                    if current_score < min_score_18m:
                        exits.append(sym)
                        exit_reasons[sym] = f'm3_18mo_decay({current_score:.0f}<{min_score_18m:.0f})'
                        m3_fired = True
                elif months_held >= 12:
                    min_score_12m = max(sell_threshold, h['entry_score'] - m3_12m_decay)
                    if current_score < min_score_12m:
                        exits.append(sym)
                        exit_reasons[sym] = f'm3_12mo_decay({current_score:.0f}<{min_score_12m:.0f})'
                        m3_fired = True
                # Below 12 months: M3 does not apply (min-hold window)
                # Set re-entry cooldown so the exited stock can't immediately re-enter
                if m3_fired and m3_cooldown_months > 0:
                    m3_cooldown_until[sym] = date_t + pd.DateOffset(months=m3_cooldown_months)

            # Priority 3: Score thesis broken — requires min_hold to prevent false exits
            elif current_score < sell_threshold:
                if months_held >= min_hold_months:
                    exits.append(sym)
                    exit_reasons[sym] = f'score_exit({current_score:.0f})'
                # else: give position time to recover; don't exit within min_hold window

        for sym in exits:
            holdings.pop(sym, None)
            rs_strike_count.pop(sym, None)
            m2_strike_count.pop(sym, None)
            m2_latest_lag.pop(sym, None)
            # Note: m3_cooldown_until is NOT cleared here — it persists intentionally
            # so the stock stays locked out for cooldown_months after an M3 exit.

        # ── Step 2.5: M6 — Opportunity cost active rotation ──────────────────
        # If the best unowned candidate scores > m6_rotation_gap pts above the
        # lowest-scoring held stock that has cleared min-hold, rotate the pair.
        # Mirrors NSE Momentum 30: bottom-ranked held stock is always evicted when
        # a better-ranked candidate exists. One rotation per rebalance period.
        if m6_rotation_enabled and len(holdings) > 0:
            held_eligible = {
                s: score_map.get(s, 0.0)
                for s, h in holdings.items()
                if (date_t - h.get('entry_date', date_t)).days / 30.5 >= min_hold_months
            }
            if held_eligible:
                worst_sym   = min(held_eligible, key=held_eligible.get)
                worst_score = held_eligible[worst_sym]
                not_held_candidates = {
                    s: score_map.get(s, 0.0)
                    for s in score_map
                    if s not in holdings and s in prices
                }
                if not_held_candidates:
                    best_sym   = max(not_held_candidates, key=not_held_candidates.get)
                    best_score = not_held_candidates[best_sym]
                    gap = best_score - worst_score
                    if gap >= m6_rotation_gap:
                        exits.append(worst_sym)
                        exit_reasons[worst_sym] = (
                            f'm6_rotation(gap:{gap:.0f},in:{best_sym.replace(".NS","")}'
                            f',score:{worst_score:.0f}→{best_score:.0f})'
                        )
                        holdings.pop(worst_sym, None)

        # ── Step 2: Effective entry gate (regime + event calendar) ───────────
        # BEAR regime raises buy bar by 10pts; SIDEWAYS +3pts
        # Budget window adds 8pts; RBI MPC week adds 4pts
        regime_threshold_boost = {'BEAR': 10.0, 'SIDEWAYS': 3.0, 'BULL': 0.0}.get(dma_regime, 0.0)
        event_threshold_boost  = 0.0 if ev_scalar >= 0.85 else (8.0 if ev_scalar < 0.70 else 4.0)
        effective_buy_threshold = buy_threshold + regime_threshold_boost + event_threshold_boost

        # ── Step 3: ENTRY — buy new high-conviction stocks ──────────────────
        candidates = sorted(
            [(s, sc) for s, sc in score_map.items()
             if sc >= effective_buy_threshold and s not in holdings],
            key=lambda x: x[1], reverse=True
        )
        sec_counts: Dict[str, int] = {}
        for sym in holdings:
            sec = NIFTY50_SECTORS.get(sym, 'Other')
            sec_counts[sec] = sec_counts.get(sec, 0) + 1

        max_per_sec  = max(1, int(effective_max_positions * sector_cap))
        override_max = SECTOR_MAX_OVERRIDES

        for sym, score in candidates:
            if len(holdings) >= effective_max_positions:
                break
            sec = NIFTY50_SECTORS.get(sym, 'Other')
            general_ok  = sec_counts.get(sec, 0) < max_per_sec
            override_ok = sec_counts.get(sec, 0) < override_max.get(sec, max_per_sec)
            if not (general_ok and override_ok):
                continue
            # M3 re-entry cooldown gate
            # If this stock was M3-exited, block re-entry until cooldown expires.
            if m3_cooldown_months > 0 and sym in m3_cooldown_until:
                if date_t < m3_cooldown_until[sym]:
                    continue  # still in cooldown window — skip
            # M7: factor concentration HHI gate
            # Simulate adding this stock and check if it pushes HHI over threshold.
            # Uses equal weights as a proxy (vol-weights not yet computed at entry).
            # Guard: skip HHI check when portfolio has < 2 stocks — a single stock
            # always produces HHI = 1.0 (100% in one bucket), which would block
            # every entry into an empty portfolio.
            if m7_hhi_enabled and len(holdings) >= 2:
                trial_syms = set(holdings.keys()) | {sym}
                equal_w = {s: 1.0 / len(trial_syms) for s in trial_syms}
                trial_hhi, _ = portfolio_factor_hhi(trial_syms, equal_w)
                if trial_hhi > m7_hhi_threshold:
                    continue  # skip — would over-concentrate a factor bucket
            # Correlation guard: skip entry if candidate correlates > threshold
            # with too many existing holdings (detects hidden cross-sector clusters
            # like PSU/defensives that fall together during macro selloffs)
            if corr_guard_enabled and portfolio_correlation_guard(
                sym, holdings, prices, date_t,
                max_corr=corr_max_threshold,
                max_correlated_peers=corr_max_peers,
            ):
                continue  # too correlated with existing portfolio
            p_series = prices[sym]
            idx_t = p_series.index.get_indexer([date_t], method='ffill')[0]
            if idx_t < 0:
                continue
            entry_p = float(p_series.iloc[idx_t])
            tier = 'STRONG_BUY' if score >= strong_buy_threshold else 'BUY'
            holdings[sym] = {
                'entry_price': entry_p,
                'entry_score': score,
                'entry_date':  date_t,
                'peak_price':  entry_p,
                'entry_tier':  tier,
                'event_entry': ev_scalar < 1.0,
            }
            sec_counts[sec] = sec_counts.get(sec, 0) + 1

        # ── Step 4: Cash month ───────────────────────────────────────────────
        if not holdings:
            pv = pv * (1 + CASH_MONTHLY_RATE)
            last_period_ret = CASH_MONTHLY_RATE
            portfolio_values.append((date_t1, round(pv, 4)))
            trade_log.append({
                'date': date_t.strftime('%Y-%m'), 'regime': dma_regime,
                'top_stocks': '(cash)', 'exits': '', 'n_positions': 0,
                'port_ret_pct': round(CASH_MONTHLY_RATE * 100, 3),
                'bench_ret_pct': None, 'alpha_pct': round(CASH_MONTHLY_RATE * 100, 3),
                'pv': round(pv, 2), 'turnover_pct': 0.0,
                'max_pos_cap': effective_max_positions, 'ev_scalar': ev_scalar,
            })
            continue

        # ── Step 5: Vol-adjusted weights (score/σ, STRONG_BUY 1.3×) ────────
        weights = vol_adjusted_weights(
            holdings, prices, score_map, date_t,
            strong_buy_threshold=strong_buy_threshold,
        )

        # ── Step 6: Compute period return ────────────────────────────────────
        old_syms    = set(list(holdings.keys()) + exits)
        new_syms    = set(holdings.keys())
        exited_syms = set(exits)
        entered_syms = {s for s in new_syms
                        if s not in (old_syms - exited_syms) and exit_reasons.get(s) is None}
        turnover = (len(exited_syms) + len(entered_syms)) / max(len(old_syms | new_syms), 1)
        cost     = turnover * transaction_cost

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
        last_period_ret = port_ret  # M4 reads this at start of next iteration
        portfolio_values.append((date_t1, round(pv, 4)))

        b0 = bench_at.get(date_t) or (bench.iloc[bench_idx] if bench_idx >= 0 else None)
        b_idx_t1 = bench.index.get_indexer([date_t1], method='ffill')[0]
        b1 = bench.iloc[b_idx_t1] if b_idx_t1 >= 0 else None
        bench_ret = (b1 - b0) / b0 if (b0 and b1 and b0 > 0) else None

        # Count tiers for log
        n_strong = sum(1 for h in holdings.values() if h.get('entry_tier') == 'STRONG_BUY')

        trade_log.append({
            'date':          date_t.strftime('%Y-%m'),
            'regime':        dma_regime,
            'top_stocks':    ', '.join(s.replace('.NS', '') for s in holdings),
            'exits':         ', '.join(f"{s.replace('.NS','')}({r})"
                                       for s, r in exit_reasons.items()),
            'n_positions':   len(holdings),
            'n_strong_buy':  n_strong,
            'port_ret_pct':  round(port_ret * 100, 2),
            'bench_ret_pct': round(bench_ret * 100, 2) if bench_ret else None,
            'alpha_pct':     round((port_ret - (bench_ret or 0)) * 100, 2),
            'pv':            round(pv, 2),
            'turnover_pct':  round(turnover * 100, 1),
            'max_pos_cap':   effective_max_positions,
            'ev_scalar':     ev_scalar,
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
    """
    Compute benchmark metrics using monthly returns — consistent with compute_metrics()
    which also operates on monthly portfolio values.
    """
    # Resample to month-end prices first, then compute returns
    bench_m = bench.resample('ME').last().dropna()
    n_months = len(bench_m) - 1
    n_years  = n_months / 12 if n_months > 0 else 1
    total    = (bench_m.iloc[-1] / bench_m.iloc[0]) - 1
    cagr     = (1 + total) ** (1 / n_years) - 1 if n_years > 0 else 0
    mret     = bench_m.pct_change().dropna()
    std      = mret.std() * np.sqrt(12)
    rf_m     = (1 + risk_free) ** (1/12) - 1
    sharpe   = ((mret - rf_m).mean() / mret.std() * np.sqrt(12)) if mret.std() > 0 else 0
    rolling  = bench_m.cummax()
    dd       = ((bench_m - rolling) / rolling).min()
    return {'total': total, 'cagr': cagr, 'sharpe': sharpe, 'max_dd': dd, 'std': std}


# ─────────────────────────────────────────────────────────────────────────────
# Printing
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(m: Dict, bm: Dict, pv: pd.Series, bench: pd.Series, log: pd.DataFrame, top_n: int, years: int = 5):
    sep = "=" * 64
    print(f"\n{sep}")
    print(f"  PORTFOLIO BACKTEST RESULTS — Top-{top_n} NIFTY50 Strategy ({years}Y)")
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

    row(f'Total Return ({years}Y)',  m['total_return'], bm['total'])
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

    # Monthly returns table (all months)
    show_months = len(log)
    print(f"\n  ─── Monthly Returns (Strategy vs NIFTY50, all {show_months} months) ───")
    print(f"  {'Month':<10} {'Strategy':>9} {'NIFTY50':>9} {'Alpha':>8}  Holdings")
    print(f"  {'-'*10} {'-'*9} {'-'*9} {'-'*8}  {'-'*30}")
    recent = log
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

_EXPERIMENT_LOG = Path(__file__).parent.parent / 'docs' / 'EXPERIMENT_LOG.md'

# v4 baseline metrics used to compute deltas in the experiment log.
_BASELINE = {'cagr': 0.129, 'sharpe': 0.42, 'max_drawdown': -0.272, 'alpha_ann': 0.055}


def append_to_experiment_log(name: str, params_str: str, m: Dict, hypothesis: str = '') -> None:
    """Append one structured entry to docs/EXPERIMENT_LOG.md after every backtest run."""
    delta_cagr   = m['cagr']        - _BASELINE['cagr']
    delta_maxdd  = m['max_drawdown'] - _BASELINE['max_drawdown']
    delta_sharpe = m['sharpe']       - _BASELINE['sharpe']
    delta_alpha  = m['alpha_ann']    - _BASELINE['alpha_ann']

    if delta_sharpe > 0.02 and delta_maxdd >= -0.02:
        verdict = '✅ IMPROVED'
    elif delta_sharpe > 0:
        verdict = '⚠️  MIXED'
    else:
        verdict = '❌ WORSE'

    entry = (
        f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — {name}\n"
        f"**Params:** {params_str}  \n"
        f"**CAGR:** {m['cagr']:.1%} ({delta_cagr:+.1%} vs v4 baseline)  \n"
        f"**Sharpe:** {m['sharpe']:.2f} ({delta_sharpe:+.2f})  \n"
        f"**MaxDD:** {m['max_drawdown']:.1%} ({delta_maxdd:+.1%})  \n"
        f"**Alpha/yr:** {m['alpha_ann']:.1%} ({delta_alpha:+.1%})  \n"
        f"**WinRate:** {m['win_rate']:.1%}  \n"
        f"**Hypothesis:** {hypothesis or '—'}  \n"
        f"**Verdict:** {verdict}\n"
        f"\n---\n"
    )
    try:
        if not _EXPERIMENT_LOG.exists():
            _EXPERIMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
            _EXPERIMENT_LOG.write_text(
                "# Experiment Log — Indian Stock Fund Backtest\n"
                "Auto-appended by scripts/portfolio_backtest.py after every run.\n"
                "v4 baseline: CAGR 12.9% | Sharpe 0.42 | MaxDD -27.2% | Alpha +5.5%/yr\n\n"
                "---\n"
            )
        with open(_EXPERIMENT_LOG, 'a') as f:
            f.write(entry)
        print(f"  ✓ Experiment log updated → docs/EXPERIMENT_LOG.md")
    except Exception as e:
        print(f"  ⚠ Could not write experiment log: {e}")


def save_run_result(name: str, config: Dict, m: Dict, bm: Dict, hypothesis: str = '') -> None:
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
        # Signal-mode parameters (empty for calendar-mode runs)
        'buy_threshold':     config.get('buy_threshold', ''),
        'sell_threshold':    config.get('sell_threshold', ''),
        'stop_loss_pct':     config.get('stop_loss', ''),
        'mechanisms':        config.get('mechanisms', ''),
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
    # Build params summary for experiment log
    params_str = (
        f"buy={config.get('buy_threshold', '?')} sell={config.get('sell_threshold', '?')} "
        f"sl={config.get('stop_loss', '?')} years={config.get('years', '?')} "
        f"mechanisms={config.get('mechanisms', '—')}"
    )
    append_to_experiment_log(name, params_str, m, hypothesis=hypothesis)


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
    parser = argparse.ArgumentParser(description='Multi-Year Portfolio Backtest on NIFTY50 (default 5Y)')
    parser.add_argument('--years',    type=int,   default=5,     help='Backtest window in years (default: 5)')
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
    parser.add_argument('--buy-threshold',   type=float, default=60.0,
                        help='Signal mode: minimum score to initiate a position (default: 60 for v4 scorer, 65 for legacy)')
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
    # v4 signal-mode options
    parser.add_argument('--min-hold',       type=int,   default=3,
                        help='Min months before a score-exit fires (default 3; stop-loss always instant)')
    parser.add_argument('--profit-trail',   type=float, default=0.12,
                        help='Trailing stop %% from peak price once in profit (default 0.12 = 12%%)')
    parser.add_argument('--profit-trigger', type=float, default=0.20,
                        help='Profit %% from entry required to activate trailing stop (default 0.20 = 20%%)')
    parser.add_argument('--strong-buy',     type=float, default=75.0,
                        help='Score threshold for STRONG_BUY tier → 1.3× weight (default 75)')
    parser.add_argument('--legacy-scorer',  action='store_true',
                        help='Use legacy 60/40 momentum+quality formula instead of BacktestScorer')
    # M1: Relative rank degradation exit
    parser.add_argument('--rs-exit',         action='store_true',
                        help='M1: exit when RS rank below --rs-percentile for --rs-strikes months')
    parser.add_argument('--rs-percentile',   type=float, default=0.30,
                        help='M1: RS rank percentile threshold (default 0.30 = bottom 30%%)')
    parser.add_argument('--rs-strikes',      type=int,   default=3,
                        help='M1: consecutive months below RS threshold before exit (default 3)')
    parser.add_argument('--m1-sector-guard', action='store_true',
                        help='M1: pause strike count when stock sector is beating NIFTY 3M (prevents IT-rally misses)')
    # M2: 12M momentum trap exit
    parser.add_argument('--m2-exit',         action='store_true',
                        help='M2: exit when stock underperforms NIFTY 12M by > --m2-threshold for --m2-strikes months')
    parser.add_argument('--m2-threshold',    type=float, default=0.15,
                        help='M2: underperformance vs NIFTY 12M to trigger a strike (default 0.15 = 15%%)')
    parser.add_argument('--m2-strikes',      type=int,   default=2,
                        help='M2: consecutive months of underperformance before exit (default 2)')
    # M4: monthly portfolio drawdown circuit breaker
    parser.add_argument('--m4-circuit',      action='store_true',
                        help='M4: activate circuit breaker when monthly portfolio loss > --m4-threshold')
    parser.add_argument('--m4-threshold',    type=float, default=0.08,
                        help='M4: monthly loss threshold to trigger circuit (default 0.08 = 8%%)')
    # M5: India VIX position-sizing scalar
    parser.add_argument('--m5-vix',          action='store_true',
                        help='M5: scale max positions by India VIX level (preventive, forward-looking)')
    # M3: maximum holding period with progressive score hurdle
    parser.add_argument('--m3-maxhold',      action='store_true',
                        help='M3: require held stocks to clear rising score bar at 12M/18M/24M')
    parser.add_argument('--m3-12m-decay',    type=float, default=10.0,
                        help='M3: max score decay (pts below entry_score) allowed at 12M (default 10)')
    parser.add_argument('--m3-18m-decay',    type=float, default=5.0,
                        help='M3: max score decay allowed at 18M (default 5)')
    parser.add_argument('--m3-cooldown',     type=int,   default=0,
                        help='M3: months to block re-entry after an M3 exit (default 0=off; live system uses 6)')
    # M6: opportunity cost active rotation
    parser.add_argument('--m6-rotation',     action='store_true',
                        help='M6: replace lowest-scoring held stock when better candidate exists')
    parser.add_argument('--m6-gap',          type=float, default=12.0,
                        help='M6: minimum score gap (pts) to trigger rotation (default 12)')
    # M7: factor concentration HHI gate
    parser.add_argument('--m7-hhi',          action='store_true',
                        help='M7: block new entries that push portfolio factor HHI above threshold')
    parser.add_argument('--m7-threshold',    type=float, default=0.35,
                        help='M7: HHI threshold above which a factor bucket is considered crowded (default 0.35)')
    # Earnings surprise signal
    parser.add_argument('--no-earnings-surprise', action='store_true',
                        help='Disable earnings surprise adjustment in BacktestScorer '
                             '(enabled by default; ±8 pts, 90-day decay from announcement)')
    # Correlation guard
    parser.add_argument('--no-corr-guard',   action='store_true',
                        help='Disable correlation guard (enabled by default; blocks entry when '
                             'candidate correlates >0.70 with 2+ held stocks on 60d window)')
    parser.add_argument('--corr-threshold',  type=float, default=0.70,
                        help='Correlation guard: max pairwise correlation allowed (default 0.70)')
    parser.add_argument('--corr-peers',      type=int,   default=2,
                        help='Correlation guard: max number of held stocks candidate may exceed '
                             'threshold with before being blocked (default 2)')
    # Experiment logging
    parser.add_argument('--hypothesis',      type=str,   default='',
                        help='Free-text hypothesis for this run — appended to EXPERIMENT_LOG.md')
    args = parser.parse_args()

    if args.compare:
        print_comparison_table()
        return

    cost = 0.0 if args.no_costs else TRANSACTION_COST

    # Auto-generate run name if not provided
    macro_suffix = '_nomacro' if args.no_macro else '_macro'
    if args.signal_mode:
        scorer_tag = 'legacyScorer_' if args.legacy_scorer else 'v4scorer_'
        run_name = args.name or (
            f"signal_{scorer_tag}"
            f"buy{int(args.buy_threshold)}_sell{int(args.sell_threshold)}_"
            f"sl{int(args.stop_loss*100)}_"
            f"mh{args.min_hold}_pt{int(args.profit_trigger*100)}_"
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
    print(f"  Universe: NIFTY50 (point-in-time, survivorship-bias-free)  |  Window: {args.years}Y")
    if args.signal_mode:
        scorer_str = 'LEGACY 60/40' if args.legacy_scorer else 'BacktestScorer v4 (0.36F+0.27M+0.18Q)'
        print(f"  Mode: SIGNAL-DRIVEN  |  Scorer: {scorer_str}")
        print(f"  Buy≥{args.buy_threshold:.0f}  Sell<{args.sell_threshold:.0f}  Stop={args.stop_loss*100:.0f}%  "
              f"StrongBuy≥{args.strong_buy:.0f}  MinHold={args.min_hold}mo")
        print(f"  ProfitProtect: trigger={args.profit_trigger*100:.0f}%, trail={args.profit_trail*100:.0f}% from peak")
        if args.rs_exit:
            guard_str = "  +SectorGuard" if args.m1_sector_guard else ""
            print(f"  M1 RS-Exit: ON  (bottom {args.rs_percentile*100:.0f}th pct for {args.rs_strikes} months → exit{guard_str})")
        if args.m2_exit:
            print(f"  M2 Momentum-Trap: ON  (underperforms NIFTY by >{args.m2_threshold*100:.0f}% for {args.m2_strikes} months → exit)")
        if args.m4_circuit:
            print(f"  M4 Circuit: ON  (monthly loss >{args.m4_threshold*100:.0f}% → cap to 2 positions next period)")
        if args.m5_vix:
            print(f"  M5 VIX Scalar: ON  (VIX<15→1.0, 15-20→0.85, 20-25→0.65, >25→0.40)")
        if args.m3_maxhold:
            cooldown_str = f", cooldown={args.m3_cooldown}mo" if args.m3_cooldown > 0 else ""
            print(f"  M3 MaxHold: ON  (12M: decay≤{args.m3_12m_decay:.0f}pts, 18M: ≤{args.m3_18m_decay:.0f}pts, 24M: beat 75th pct{cooldown_str})")
        if args.m6_rotation:
            print(f"  M6 Rotation: ON  (gap≥{args.m6_gap:.0f}pts → rotate worst held for best candidate)")
        if args.m7_hhi:
            print(f"  M7 HHI Gate: ON  (HHI threshold={args.m7_threshold:.2f} — blocks factor-crowding entries)")
        if args.hypothesis:
            print(f"  Hypothesis: {args.hypothesis}")
    else:
        print(f"  Mode: Calendar  |  Top-{args.top} stocks")
    sector_cap_str = f"{int(args.sector_cap * 100)}% cap" if args.sector_cap > 0 else "no cap"
    cost_str = 'none' if cost == 0 else f'{cost*100:.2f}% per trade ({cost*10000:.0f} bps)'
    macro_str = 'OFF (--no-macro)' if args.no_macro else 'ON (USD/INR + RBI cycle)'
    print(f"  Costs: {cost_str}  |  Sector: {sector_cap_str}")
    print(f"  Macro overlays: {macro_str}")
    print("="*64)

    # Fetch prices — use UNION of all historical NIFTY50 symbols so point-in-time
    # universe lookups at any rebalance date have data available.
    all_hist_syms = get_all_historical_symbols(args.years)
    print(f"  Historical universe: {len(all_hist_syms)} unique symbols across {args.years}Y window")
    prices, bench = fetch_all_prices(all_hist_syms, years=args.years)

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

    vix_prices: pd.Series = fetch_vix_prices(args.years) if args.m5_vix else pd.Series(dtype=float)

    if bench.empty:
        print("  WARNING: NIFTY50 benchmark data unavailable — relative metrics will be skipped")

    # Trim to backtest window (drop warmup year) — do this BEFORE quality fetch
    # so we know the start date for point-in-time fundamentals
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=args.years)
    prices_bt = {sym: s[s.index >= cutoff] for sym, s in prices.items() if not s[s.index >= cutoff].empty}
    bench_bt  = bench[bench.index >= cutoff] if not bench.empty else bench

    print(f"\n  Backtest window: {cutoff.strftime('%Y-%m')} → {pd.Timestamp.now().strftime('%Y-%m')}")
    print(f"  Stocks with data in window: {len(prices_bt)}")

    # Fundamentals / quality cache — annual refresh (no lookahead bias)
    # Signal mode v4: full BacktestScorer with P/E rank + EPS growth + ROE + D/E
    # Signal mode legacy / calendar mode: quality only (ROE + D/E)
    # --no-quality: skip all fundamental fetching (momentum-only, fast)
    quality_map: Dict[str, float] = {}
    quality_cache: Optional[Dict] = None
    fundamentals_cache: Optional[Dict] = None

    _rebal_dates_preview = get_rebalance_dates(prices_bt, bench_bt)

    if args.no_quality:
        quality_map = {sym: 25.0 for sym in prices_bt}
        print("  Fundamentals: disabled (momentum-only mode)")
    elif args.signal_mode and not args.legacy_scorer:
        # BacktestScorer v4: build full fundamentals cache (P/E, EPS growth, ROE, D/E)
        print(f"\n  Building annual fundamentals cache (BacktestScorer v4, {args.years}Y × ~1 fetch/year) …")
        print("  Fetching: P/E, TTM EPS, earnings growth YoY, ROE, D/E — no lookahead bias")
        # Pass full prices (warmup window) so P/E can be computed at historical prices
        fundamentals_cache = build_annual_fundamentals_cache(
            list(prices_bt.keys()), _rebal_dates_preview, prices  # full prices for P/E lookup
        )
        # Derive quality_map fallback from first snapshot for calendar mode compat
        first_snap = lookup_fundamentals(fundamentals_cache, _rebal_dates_preview[0])
        quality_map = {sym: v.get('quality_raw', 25.0) for sym, v in first_snap.items()}
        valid_count = sum(1 for v in quality_map.values() if v != 25.0)
        print(f"  Fundamentals ready: {len(fundamentals_cache)} annual snapshots, "
              f"{valid_count}/{len(quality_map)} stocks with real data in earliest snapshot")
    else:
        # Legacy path: quality cache only (ROE + D/E)
        print(f"\n  Building annual quality cache ({args.years}Y × ~1 fetch/year) …")
        print("  TTM fundamentals from quarterly financials — no lookahead bias")
        quality_cache = build_annual_quality_cache(
            list(prices_bt.keys()), _rebal_dates_preview
        )
        quality_map = lookup_quality(quality_cache, _rebal_dates_preview[0]) if quality_cache else {}
        valid_count = sum(1 for v in quality_map.values() if v != 25.0)
        print(f"  Quality ready: {len(quality_cache)} annual snapshots, "
              f"{valid_count}/{len(quality_map)} stocks with real data in earliest snapshot")

    # Run simulation
    if args.signal_mode:
        print(f"\n  Running signal-driven simulation (v4) …")
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
            quality_cache=quality_cache,
            fundamentals_cache=fundamentals_cache,
            use_backtest_scorer=not args.legacy_scorer,
            min_hold_months=args.min_hold,
            profit_trail_pct=args.profit_trail,
            profit_trigger_pct=args.profit_trigger,
            strong_buy_threshold=args.strong_buy,
            rs_exit_enabled=args.rs_exit,
            rs_exit_percentile=args.rs_percentile,
            rs_exit_strikes=args.rs_strikes,
            m2_exit_enabled=args.m2_exit,
            m2_underperform_threshold=args.m2_threshold,
            m2_exit_strikes=args.m2_strikes,
            m4_circuit_enabled=args.m4_circuit,
            m4_dd_threshold=args.m4_threshold,
            m5_vix_enabled=args.m5_vix,
            vix_prices=vix_prices,
            m3_maxhold_enabled=args.m3_maxhold,
            m3_12m_decay=args.m3_12m_decay,
            m3_18m_decay=args.m3_18m_decay,
            m3_cooldown_months=args.m3_cooldown,
            m1_sector_guard=args.m1_sector_guard,
            m6_rotation_enabled=args.m6_rotation,
            m6_rotation_gap=args.m6_gap,
            m7_hhi_enabled=args.m7_hhi,
            m7_hhi_threshold=args.m7_threshold,
            corr_guard_enabled=not args.no_corr_guard,
            corr_max_threshold=args.corr_threshold,
            corr_max_peers=args.corr_peers,
            use_earnings_surprise_disabled=args.no_earnings_surprise,
        )
    else:
        print(f"\n  Running monthly simulation (top-{args.top}) …")
        pv, trade_log = run_simulation(
            prices_bt, bench_bt, quality_map, args.top, cost,
            args.sector_cap, args.exit_drawdown, args.score_decay,
            inr_prices=inr_prices,
            rbi_history=rbi_history,
            quality_cache=quality_cache,
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
    print_summary(m, bm, pv_monthly, bench_bt, trade_log, args.top, years=args.years)

    if not args.no_quality:
        print("\n" + "="*64)
        if args.signal_mode and not args.legacy_scorer:
            print("  NOTE: BacktestScorer v4 active — formula aligned with live StockScorer")
            print("  Weights: 0.36×Fundamentals + 0.27×Momentum + 0.18×Quality + 9.5")
            print("  Fundamentals: P/E rank (cross-sectional) + EPS growth YoY + ROE")
        else:
            print("  NOTE: Quality refreshed annually using TTM fundamentals")
            print("  (quarterly financials from yfinance — no lookahead bias).")
        print("  Run with --no-quality for a fully price-based backtest.")
        print("="*64 + "\n")

    # Build mechanism tag for experiment log
    mechs = []
    if args.signal_mode:
        if getattr(args, 'rs_exit', False):      mechs.append('M1')
        if getattr(args, 'm2_exit', False):      mechs.append('M2')
        if getattr(args, 'm3_maxhold', False):   mechs.append('M3')
        if getattr(args, 'm4_circuit', False):   mechs.append('M4')
        if getattr(args, 'm5_vix', False):       mechs.append('M5')
        if getattr(args, 'm6_rotation', False):  mechs.append('M6')
        if getattr(args, 'm7_hhi', False):       mechs.append('M7')

    # Save run to results log
    save_run_result(run_name, {
        'years':          args.years,
        'top_n':          args.top,
        'sector_cap':     args.sector_cap,
        'exit_drawdown':  args.exit_drawdown if not args.signal_mode else args.stop_loss,
        'score_decay':    args.score_decay if not args.signal_mode else args.sell_threshold,
        'quality':        not args.no_quality,
        'costs':          not args.no_costs,
        'buy_threshold':  args.buy_threshold if args.signal_mode else None,
        'sell_threshold': args.sell_threshold if args.signal_mode else None,
        'stop_loss':      args.stop_loss if args.signal_mode else None,
        'mechanisms':     '+'.join(mechs) if mechs else 'none',
    }, m, bm, hypothesis=getattr(args, 'hypothesis', ''))

    print(f"  Run --compare to see all saved runs side-by-side.\n")


if __name__ == '__main__':
    main()
