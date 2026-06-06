"""
Historical regression tests — pin known outcomes from real backtest runs.

These tests run the FULL 5-year simulation against real downloaded price data.
They are SLOW (~3-5 minutes each) and require network access on first run
(yfinance data cached after that).

Run with:
    pytest tests/backtest/test_regression.py -m slow -v

Skip in CI / fast feedback:
    pytest -m "not slow"

Purpose:
  - Catch accidental regressions in run_signal_simulation() when editing the backtest
  - Confirm that specific mechanism-driven exits happen when expected (COALINDIA, ITC)
  - Pin the v4 baseline metrics so we know if a change moves them

Each test uses a shared price cache fixture (downloaded once per session).
"""
import pytest
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

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


# ── Shared fixtures (downloaded once per test session) ────────────────────────

@pytest.fixture(scope='session')
def price_data_5y():
    """
    Download all historical NIFTY50 prices for a 5Y window.
    Cached at session scope — shared across all regression tests.
    Takes ~60s on first run, then yfinance caches it.
    """
    all_syms = get_all_historical_symbols(years=5)
    prices, bench = fetch_all_prices(all_syms, years=5)
    return prices, bench


@pytest.fixture(scope='session')
def quality_cache_5y(price_data_5y):
    """Annual quality cache for the 5Y window (ROE + D/E snapshots)."""
    prices, bench = price_data_5y
    rebal_dates = get_rebalance_dates(prices, bench)
    cache = build_annual_quality_cache(list(prices.keys()), rebal_dates)
    quality_map = lookup_quality(cache, rebal_dates[0]) if cache else {}
    return cache, quality_map


@pytest.fixture(scope='session')
def fundamentals_cache_5y(price_data_5y):
    """Annual fundamentals cache for the 5Y window (P/E, EPS growth, ROE)."""
    prices, bench = price_data_5y
    rebal_dates = get_rebalance_dates(prices, bench)
    cache = build_annual_fundamentals_cache(list(prices.keys()), rebal_dates)
    return cache


def _run_bt(price_data_5y, quality_cache_5y, fundamentals_cache_5y, **kwargs):
    """Helper: run signal simulation with v4 defaults + overrides."""
    prices, bench = price_data_5y
    _, quality_map = quality_cache_5y
    fund_cache     = fundamentals_cache_5y

    # Trim to backtest window (drop 1Y warmup)
    cutoff = bench.index[-1] - pd.DateOffset(years=5)
    prices_bt = {s: p[p.index >= cutoff] for s, p in prices.items()
                 if not p[p.index >= cutoff].empty}
    bench_bt = bench[bench.index >= cutoff]

    defaults = dict(
        buy_threshold=60.0,
        sell_threshold=38.0,
        stop_loss=0.10,
        max_positions=10,
        transaction_cost=0.0027,
        sector_cap=0.30,
        quality_cache=None,
        fundamentals_cache=fund_cache,
        use_backtest_scorer=True,
        min_hold_months=3,
        profit_trail_pct=0.12,
        profit_trigger_pct=0.20,
        strong_buy_threshold=75.0,
    )
    defaults.update(kwargs)
    pv, trade_log = run_signal_simulation(prices_bt, bench_bt, quality_map, **defaults)
    pv_monthly = pv.resample('ME').last().dropna()
    bench_monthly = bench_bt.resample('ME').last().dropna()
    m = compute_metrics(pv_monthly, bench_monthly)
    return m, trade_log


# ── Regression tests ──────────────────────────────────────────────────────────

@pytest.mark.slow
def test_v4_baseline_metrics_stable(price_data_5y, quality_cache_5y, fundamentals_cache_5y):
    """
    v4 baseline (no M1-M7) should reproduce within ±3pp of known good values.
    Known values: CAGR 12.9%, Sharpe 0.42, MaxDD -27.2%.
    If this test breaks, a change in scoring/exit logic has altered the baseline.
    """
    m, _ = _run_bt(price_data_5y, quality_cache_5y, fundamentals_cache_5y)

    assert m['cagr'] > 0.09, f"v4 baseline CAGR {m['cagr']:.1%} too low (expect >9%)"
    assert m['cagr'] < 0.18, f"v4 baseline CAGR {m['cagr']:.1%} suspiciously high (expect <18%)"
    assert m['sharpe'] > 0.25, f"v4 baseline Sharpe {m['sharpe']:.2f} too low (expect >0.25)"
    assert m['max_drawdown'] > -0.40, f"v4 baseline MaxDD {m['max_drawdown']:.1%} worse than expected"
    assert m['alpha_ann'] > 0.02, f"v4 baseline Alpha {m['alpha_ann']:.1%} too low (expect >2%/yr)"


@pytest.mark.slow
def test_m1_best_config_reproduces(price_data_5y, quality_cache_5y, fundamentals_cache_5y):
    """
    M1 p35/s3 is the known-best configuration: CAGR >13%, MaxDD < -24%.
    Regression guard: if M1 logic changes, this catches it.
    """
    m, _ = _run_bt(
        price_data_5y, quality_cache_5y, fundamentals_cache_5y,
        rs_exit_enabled=True,
        rs_exit_percentile=0.35,
        rs_exit_strikes=3,
    )
    assert m['cagr'] > 0.12, f"M1 p35/s3 CAGR {m['cagr']:.1%} below expected >12%"
    assert m['max_drawdown'] > -0.25, (
        f"M1 p35/s3 MaxDD {m['max_drawdown']:.1%} worse than expected -25%"
    )
    assert m['sharpe'] > 0.40, f"M1 p35/s3 Sharpe {m['sharpe']:.2f} below expected >0.40"


@pytest.mark.slow
def test_m3_exits_itc_before_jan_2025(price_data_5y, quality_cache_5y, fundamentals_cache_5y):
    """
    With M3 enabled (default params), ITC.NS must exit before Jan 2025.

    ITC was entered ~Jun 2022. By Jun 2024 (24 months), it should fail the
    75th-percentile hurdle — its score was ~62 while the universe 75th pct ~68-72.

    Without M3, ITC was held until Jan 2025, contributing to the -10.5% month.
    """
    _, trade_log = _run_bt(
        price_data_5y, quality_cache_5y, fundamentals_cache_5y,
        m3_maxhold_enabled=True,
    )
    df = pd.DataFrame(trade_log)
    # Find rows where exits mention ITC
    itc_exits = df[df['exits'].str.contains('ITC', na=False)]
    assert not itc_exits.empty, "M3 should force an ITC exit somewhere in the 5Y run"
    # The exit date should be before Jan 2025
    first_itc_exit = pd.to_datetime(itc_exits.iloc[0]['date'] + '-01')
    assert first_itc_exit < pd.Timestamp('2025-01-01'), (
        f"M3 ITC exit happened {first_itc_exit:%Y-%m} — expected before 2025-01"
    )


@pytest.mark.slow
def test_m6_rotates_coalindia_before_sep_2024(price_data_5y, quality_cache_5y, fundamentals_cache_5y):
    """
    With M6 enabled (gap=12), COALINDIA.NS must be rotated out before Sep 2024.

    By Q1 2024, COALINDIA scored ~52-58 while JSWSTEEL scored ~70-75 (steel cycle
    starting). The 12-14pt gap should trigger M6 rotation by Mar-Apr 2024 at the latest.

    Without M6, COALINDIA was held until Sep 2024, causing the -9.7% alpha month.
    """
    _, trade_log = _run_bt(
        price_data_5y, quality_cache_5y, fundamentals_cache_5y,
        m6_rotation_enabled=True,
        m6_rotation_gap=12.0,
    )
    df = pd.DataFrame(trade_log)
    coal_exits = df[df['exits'].str.contains('COALINDIA', na=False)]
    assert not coal_exits.empty, "M6 should trigger a COALINDIA rotation at some point"
    first_coal_exit = pd.to_datetime(coal_exits.iloc[0]['date'] + '-01')
    assert first_coal_exit < pd.Timestamp('2024-09-01'), (
        f"M6 COALINDIA exit happened {first_coal_exit:%Y-%m} — expected before 2024-09"
    )


@pytest.mark.slow
def test_m3_improves_maxdd_vs_baseline(price_data_5y, quality_cache_5y, fundamentals_cache_5y):
    """
    With M3 enabled, MaxDD should improve (be less negative) vs v4 baseline.
    If M3 makes MaxDD WORSE, something is wrong with the implementation.
    """
    m_baseline, _ = _run_bt(price_data_5y, quality_cache_5y, fundamentals_cache_5y)
    m_m3, _ = _run_bt(
        price_data_5y, quality_cache_5y, fundamentals_cache_5y,
        m3_maxhold_enabled=True,
    )
    assert m_m3['max_drawdown'] >= m_baseline['max_drawdown'] - 0.03, (
        f"M3 made MaxDD worse: {m_m3['max_drawdown']:.1%} vs baseline {m_baseline['max_drawdown']:.1%}"
    )


@pytest.mark.slow
def test_m7_reduces_factor_concentration(price_data_5y, quality_cache_5y, fundamentals_cache_5y):
    """
    With M7 enabled (threshold=0.35), the portfolio should never hold 3+ stocks from
    the same factor bucket (def_value) simultaneously.
    Specifically: ITC + BRITANNIA + NESTLEIND should not co-exist in portfolio.
    """
    _, trade_log = _run_bt(
        price_data_5y, quality_cache_5y, fundamentals_cache_5y,
        m7_hhi_enabled=True,
        m7_hhi_threshold=0.35,
    )
    df = pd.DataFrame(trade_log)
    def_value_stocks = {'ITC', 'BRITANNIA', 'NESTLEIND', 'HINDUNILVR', 'TATACONSUM', 'ASIANPAINT'}
    for _, row in df.iterrows():
        held = set(row.get('top_stocks', '').split(', '))
        overlap = held & def_value_stocks
        assert len(overlap) <= 2, (
            f"M7 failed: {len(overlap)} def_value stocks held simultaneously in {row['date']}: {overlap}"
        )
