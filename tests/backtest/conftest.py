"""
Shared test helpers for backtest mechanism tests.

These helpers create synthetic, deterministic price series and holdings
dicts that match the exact format used by run_signal_simulation() — so
each mechanism can be tested without downloading real data or running a
full 5-year simulation.
"""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ── Price series factory ──────────────────────────────────────────────────────

def make_daily_prices(
    n_months: int,
    pattern: str = 'flat',
    start_price: float = 100.0,
    start_date: str = '2021-06-01',
) -> pd.Series:
    """
    Build a daily price series for a single stock.

    Patterns:
      'flat'    — price stays near start_price (±1% noise)
      'rising'  — steady uptrend, ~+15% over n_months
      'falling' — steady downtrend, ~-15% over n_months
      'trap'    — rises +15% then stays flat (quality trap)
      'crash'   — rises +20% then drops sharply -25%
    """
    rng = np.random.default_rng(seed=42)
    n_days = n_months * 21
    dates = pd.bdate_range(start=start_date, periods=n_days)

    if pattern == 'flat':
        noise = rng.normal(0, 0.005, n_days)
        prices = start_price * np.exp(np.cumsum(noise))
    elif pattern == 'rising':
        drift = 0.15 / n_days
        noise = rng.normal(0, 0.007, n_days)
        prices = start_price * np.exp(np.cumsum(drift + noise))
    elif pattern == 'falling':
        drift = -0.15 / n_days
        noise = rng.normal(0, 0.007, n_days)
        prices = start_price * np.exp(np.cumsum(drift + noise))
    elif pattern == 'trap':
        # Rise 15% over first half, then flat
        half = n_days // 2
        drift_up = 0.15 / half
        noise = rng.normal(0, 0.005, n_days)
        log_returns = np.where(
            np.arange(n_days) < half,
            drift_up + noise,
            noise * 0.3,  # low-noise flat phase
        )
        prices = start_price * np.exp(np.cumsum(log_returns))
    elif pattern == 'crash':
        # Rise +20% over first 2/3, drop -25% in last 1/3
        up = int(n_days * 2 / 3)
        dn = n_days - up
        noise = rng.normal(0, 0.006, n_days)
        log_returns = np.where(
            np.arange(n_days) < up,
            0.20 / up + noise,
            -0.25 / dn + noise,
        )
        prices = start_price * np.exp(np.cumsum(log_returns))
    else:
        raise ValueError(f"Unknown pattern: {pattern}")

    return pd.Series(prices.round(2), index=dates, name='Close')


def make_synthetic_prices(
    n_months: int,
    stock_patterns: Dict[str, str],
    start_date: str = '2021-06-01',
) -> Dict[str, pd.Series]:
    """
    Build a price dict for multiple stocks.

    Example:
        make_synthetic_prices(30, {'STOCK_A.NS': 'flat', 'STOCK_B.NS': 'rising'})
    """
    return {
        sym: make_daily_prices(n_months, pattern, start_date=start_date)
        for sym, pattern in stock_patterns.items()
    }


def make_bench(n_months: int, start_date: str = '2021-06-01') -> pd.Series:
    """Build a synthetic NIFTY benchmark series (mild uptrend)."""
    return make_daily_prices(n_months, 'rising', start_price=15000.0, start_date=start_date)


# ── Holdings dict factory ─────────────────────────────────────────────────────

def make_holding(
    entry_price: float = 100.0,
    entry_score: float = 68.0,
    entry_months_ago: int = 3,
    peak_price: Optional[float] = None,
    entry_tier: str = 'BUY',
    reference_date: str = '2024-03-01',
) -> Dict:
    """
    Create a single holding dict matching run_signal_simulation() holdings format.

    entry_months_ago is relative to reference_date (the current simulation date).
    So entry_months_ago=6 means the stock was bought 6 months before reference_date.
    """
    ref = pd.Timestamp(reference_date)
    entry_date = ref - pd.DateOffset(months=entry_months_ago)
    return {
        'entry_price': entry_price,
        'entry_score': entry_score,
        'entry_date':  entry_date,
        'peak_price':  peak_price or entry_price,
        'entry_tier':  entry_tier,
        'event_entry': False,
    }


def make_holdings(specs: Dict[str, Dict], reference_date: str = '2024-03-01') -> Dict[str, Dict]:
    """
    Build a holdings dict for multiple stocks.

    specs: {sym: {entry_price, entry_score, entry_months_ago, peak_price}}
    reference_date: the current simulation date (entry_months_ago is relative to this)

    Example:
        make_holdings({
            'ITC.NS':  {'entry_score': 65, 'entry_months_ago': 26},
            'COAL.NS': {'entry_score': 70, 'entry_months_ago': 3},
        }, reference_date='2024-03-01')
    """
    return {
        sym: make_holding(**{**spec, 'reference_date': reference_date})
        for sym, spec in specs.items()
    }


# ── Score map factory ─────────────────────────────────────────────────────────

def make_score_map(scores: Dict[str, float]) -> Dict[str, float]:
    """Thin wrapper — returns scores dict as-is (for readability in tests)."""
    return dict(scores)


# ── Pytest fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def small_price_set():
    """5-stock synthetic price set, 30 months, mixed patterns."""
    return make_synthetic_prices(30, {
        'ALPHA.NS':   'rising',
        'BETA.NS':    'flat',
        'GAMMA.NS':   'trap',
        'DELTA.NS':   'falling',
        'EPSILON.NS': 'rising',
    })


@pytest.fixture
def bench_30m():
    """30-month synthetic NIFTY benchmark."""
    return make_bench(30)
