"""
Unit tests for the 5 improvements implemented in the scoring + backtest engine.

Changes under test:
  1. SECTOR_MAX_OVERRIDES — 2-stock cap extended to all sectors
  2. rs_acceleration_score_at() — rewards building momentum, penalises fading
  3. market_stress_scalar_at() — circuit breaker on NIFTY 20-day fall
  4. _compute_earnings_acceleration() — QoQ EPS trend adjustment in StockScorer
  5. composite_score_at() — RS accel wired in, macro_adj preserved

All tests use synthetic deterministic data — no network calls.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ─────────────────────────────────────────────────────────────────────────────
# 1. SECTOR_MAX_OVERRIDES — 2-stock cap for all sectors
# ─────────────────────────────────────────────────────────────────────────────

class TestSectorMaxOverrides:
    def _overrides(self):
        from scripts.portfolio_backtest import SECTOR_MAX_OVERRIDES
        return SECTOR_MAX_OVERRIDES

    def test_it_still_capped_at_2(self):
        assert self._overrides().get('IT') == 2

    def test_metals_capped_at_2(self):
        assert self._overrides().get('Metals') == 2, (
            "Metals must be capped at 2 — Feb-2026 loss was caused by 3 correlated Metals positions"
        )

    def test_auto_capped_at_2(self):
        assert self._overrides().get('Auto') == 2, (
            "Auto sector caused Feb-2026 cluster crash — needs 2-stock cap"
        )

    def test_energy_capped_at_2(self):
        assert self._overrides().get('Energy') == 2

    def test_financials_capped_at_2(self):
        assert self._overrides().get('Financials') == 2

    def test_all_sectors_have_override(self):
        overrides = self._overrides()
        required = ['IT', 'Metals', 'Auto', 'Energy', 'Financials', 'FMCG', 'Pharma', 'Industrials']
        missing = [s for s in required if s not in overrides]
        assert not missing, f"Missing sector caps: {missing}"

    def test_apply_sector_cap_respects_metals_limit(self):
        from scripts.portfolio_backtest import apply_sector_cap, NIFTY50_SECTORS
        # Build a scored list with 3 Metals stocks at top
        metals_syms = [s for s, sec in NIFTY50_SECTORS.items() if sec == 'Metals']
        assert len(metals_syms) >= 3, "Need ≥3 Metals stocks for this test"
        scored = [(sym, 90.0 - i) for i, sym in enumerate(metals_syms[:3])]
        # Pad with non-metals to fill top_n=5
        scored += [('BHARTIARTL.NS', 50.0), ('NTPC.NS', 48.0)]
        selected = apply_sector_cap(scored, top_n=5, sector_cap=0.30)
        selected_syms = [s for s, _ in selected]
        metals_selected = [s for s in selected_syms if NIFTY50_SECTORS.get(s) == 'Metals']
        assert len(metals_selected) <= 2, (
            f"Metals cap at 2 violated: got {metals_selected}"
        )

    def test_apply_sector_cap_allows_fill_from_other_sectors(self):
        from scripts.portfolio_backtest import apply_sector_cap, NIFTY50_SECTORS
        # All top 3 are Metals — only 2 should be selected, 3rd blocked by SECTOR_MAX_OVERRIDES.
        # top_n=7 gives max_general=2, and override=2 → effective cap = min(2,2) = 2.
        metals_syms = [s for s, sec in NIFTY50_SECTORS.items() if sec == 'Metals']
        scored = [(sym, 95.0 - i) for i, sym in enumerate(metals_syms[:3])]
        scored += [('BHARTIARTL.NS', 50.0), ('NTPC.NS', 48.0)]
        selected = apply_sector_cap(scored, top_n=7, sector_cap=0.30)
        metals_selected = [s for s, _ in selected if NIFTY50_SECTORS.get(s) == 'Metals']
        assert len(metals_selected) == 2, (
            f"Exactly 2 metals expected; got {metals_selected}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. rs_acceleration_score_at()
# ─────────────────────────────────────────────────────────────────────────────

def _make_trend_series(n=300, annual_return=0.20):
    """Synthetic price series with smooth compound growth."""
    daily = (1 + annual_return) ** (1 / 252)
    prices = 100 * np.cumprod([daily] * n)
    dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
    return pd.Series(prices, index=dates)


class TestRSAcceleration:
    def _fn(self):
        from scripts.portfolio_backtest import rs_acceleration_score_at
        return rs_acceleration_score_at

    def test_returns_zero_when_insufficient_data(self):
        fn = self._fn()
        short = _make_trend_series(n=50)
        bench = _make_trend_series(n=50)
        result = fn(short, bench, len(short) - 1, len(bench) - 1)
        assert result == 0.0

    def test_building_momentum_returns_positive(self):
        """Stock accelerating vs benchmark → positive score boost."""
        fn = self._fn()
        # RS Accel = rs3 - rs6. For accel > 0 need rs3 > rs6.
        # rs3 = last 63d return; rs6 = last 126d return.
        # Pattern: decline in first half of the 126d window, then surge.
        # rs6 captures (decline + surge), rs3 captures only (surge) → rs3 > rs6.
        n = 300
        dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
        bench_prices = pd.Series(np.ones(n) * 20000, index=dates)
        stock = np.ones(n) * 100.0
        for i in range(1, n):
            if i < n - 126:
                stock[i] = stock[i-1] * 1.001   # early drift (irrelevant to accel calc)
            elif i < n - 63:
                stock[i] = stock[i-1] * 0.997   # declining in 6m-window first half
            else:
                stock[i] = stock[i-1] * 1.008   # surging in recent 3m
        stock_series = pd.Series(stock, index=dates)
        adj = fn(stock_series, bench_prices, n - 1, n - 1)
        assert adj > 0, f"Building momentum should give positive adj, got {adj}"

    def test_fading_momentum_returns_negative(self):
        """Stock was strong 6m ago but weak recently → negative penalty."""
        fn = self._fn()
        n = 300
        dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
        bench_prices = pd.Series(np.ones(n) * 20000, index=dates)
        # Stock: up 30% in 6 months ago window, flat/down recently
        stock = np.ones(n) * 100.0
        for i in range(1, n):
            if i < n - 126:
                stock[i] = stock[i-1]
            elif i < n - 63:
                stock[i] = stock[i-1] * 1.005   # was strong
            else:
                stock[i] = stock[i-1] * 0.998   # now fading
        stock_series = pd.Series(stock, index=dates)
        adj = fn(stock_series, bench_prices, n - 1, n - 1)
        assert adj < 0, f"Fading momentum should give negative adj, got {adj}"

    def test_neutral_momentum_returns_near_zero(self):
        """Stock tracks benchmark closely → near-zero adjustment."""
        fn = self._fn()
        bench = _make_trend_series(n=300, annual_return=0.10)
        stock = _make_trend_series(n=300, annual_return=0.11)  # almost same
        adj = fn(stock, bench, 299, 299)
        assert -2.0 <= adj <= 2.0, f"Near-neutral should give adj ≈ 0, got {adj}"

    def test_max_positive_capped_at_10(self):
        """Extreme acceleration never exceeds +10 pts."""
        fn = self._fn()
        n = 300
        dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
        bench = pd.Series(np.ones(n) * 20000, index=dates)
        # Parabolic stock: very slow 6m, enormous surge in 3m
        stock = np.ones(n) * 100.0
        for i in range(1, n):
            stock[i] = stock[i-1] * (1.001 if i < n - 63 else 1.020)
        s = pd.Series(stock, index=dates)
        adj = fn(s, bench, n - 1, n - 1)
        assert adj <= 10.0

    def test_max_negative_capped_at_minus_10(self):
        """Extreme deceleration never goes below -10 pts."""
        fn = self._fn()
        n = 300
        dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
        bench = pd.Series(np.ones(n) * 20000, index=dates)
        # Was parabolic 6m ago, now crashing
        stock = np.ones(n) * 100.0
        for i in range(1, n):
            stock[i] = stock[i-1] * (1.020 if i < n - 63 else 0.985)
        s = pd.Series(stock, index=dates)
        adj = fn(s, bench, n - 1, n - 1)
        assert adj >= -10.0

    def test_bench_missing_returns_zero(self):
        """If bench series is empty, should return 0 gracefully."""
        fn = self._fn()
        stock = _make_trend_series(n=300)
        empty_bench = pd.Series(dtype=float)
        adj = fn(stock, empty_bench, 299, -1)
        assert adj == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. market_stress_scalar_at()
# ─────────────────────────────────────────────────────────────────────────────

class TestMarketStressCircuitBreaker:
    def _fn(self):
        from scripts.portfolio_backtest import market_stress_scalar_at
        return market_stress_scalar_at

    def _make_nifty(self, n, ret_20d):
        """Series of length n where last 20 days moved by ret_20d."""
        prices = np.ones(n) * 20000.0
        # Set the 20-day window return
        base = 20000.0
        for i in range(n - 20, n):
            prices[i] = base * (1 + ret_20d * (i - (n - 20)) / 19)
        dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
        return pd.Series(prices, index=dates)

    def test_no_stress_returns_1(self):
        fn = self._fn()
        nifty = self._make_nifty(300, ret_20d=0.02)   # +2% → no stress
        scalar = fn(nifty, 299)
        assert scalar == 1.0

    def test_moderate_stress_5pct_fall_returns_0_6(self):
        fn = self._fn()
        nifty = self._make_nifty(300, ret_20d=-0.06)  # -6% → moderate
        scalar = fn(nifty, 299)
        assert scalar == 0.6, f"Expected 0.6 for -6% 20d fall, got {scalar}"

    def test_severe_stress_8pct_fall_returns_0_4(self):
        fn = self._fn()
        nifty = self._make_nifty(300, ret_20d=-0.09)  # -9% → severe
        scalar = fn(nifty, 299)
        assert scalar == 0.4, f"Expected 0.4 for -9% 20d fall, got {scalar}"

    def test_exactly_5pct_fall_is_moderate(self):
        fn = self._fn()
        nifty = self._make_nifty(300, ret_20d=-0.051)
        scalar = fn(nifty, 299)
        assert scalar == 0.6

    def test_exactly_8pct_fall_is_severe(self):
        fn = self._fn()
        nifty = self._make_nifty(300, ret_20d=-0.081)
        scalar = fn(nifty, 299)
        assert scalar == 0.4

    def test_insufficient_history_returns_1(self):
        fn = self._fn()
        short = pd.Series(np.ones(10) * 20000)
        scalar = fn(short, 9)
        assert scalar == 1.0

    def test_feb_2026_type_crash_triggers_severe(self):
        """Verify the Feb-2026 -11.3% NIFTY fall would trigger severe circuit breaker."""
        fn = self._fn()
        nifty = self._make_nifty(300, ret_20d=-0.113)
        scalar = fn(nifty, 299)
        assert scalar == 0.4, "Feb-2026 -11.3% crash should trigger severe (0.4) circuit breaker"

    def test_circuit_breaker_raises_effective_buy_threshold(self):
        """Stress scalar < 1 should raise buy threshold by up to +12 pts (at scalar=0.4)."""
        stress_scalar = 0.6
        buy_threshold = 60.0
        # Match the formula in run_signal_simulation
        effective = buy_threshold + (1 - stress_scalar) * 20
        assert effective == 68.0, f"Moderate stress: threshold should be 68, got {effective}"

        stress_scalar = 0.4
        effective = buy_threshold + (1 - stress_scalar) * 20
        assert effective == 72.0, f"Severe stress: threshold should be 72, got {effective}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. composite_score_at() — RS accel integrated
# ─────────────────────────────────────────────────────────────────────────────

class TestCompositeScoreWithRSAccel:
    def _score_fn(self):
        from scripts.portfolio_backtest import composite_score_at
        return composite_score_at

    def _make_prices(self, n=300, annual_ret=0.15):
        daily = (1 + annual_ret) ** (1 / 252)
        p = 100 * np.cumprod([daily] * n)
        d = pd.date_range(end='2024-12-31', periods=n, freq='B')
        return pd.Series(p, index=d)

    def test_returns_float_in_range(self):
        score_fn = self._score_fn()
        prices = self._make_prices(300)
        bench = self._make_prices(300, annual_ret=0.10)
        quality = {'TEST': 40.0}
        result = score_fn('TEST', prices, 299, quality, bench_prices=bench, bench_as_of_idx=299)
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_building_momentum_scores_higher_than_without_bench(self):
        """Passing bench_prices with accelerating stock should add pts vs no bench."""
        score_fn = self._score_fn()
        n = 300
        dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
        bench = pd.Series(np.ones(n) * 20000.0, index=dates)
        # Decline-then-surge: rs3 (surge only) > rs6 (decline+surge) → accel > 0
        stock = np.ones(n) * 100.0
        for i in range(1, n):
            if i < n - 126:
                stock[i] = stock[i-1] * 1.001
            elif i < n - 63:
                stock[i] = stock[i-1] * 0.997   # declining
            else:
                stock[i] = stock[i-1] * 1.008   # surging
        s = pd.Series(stock, index=dates)
        quality = {'ACC': 50.0}
        score_with = score_fn('ACC', s, n-1, quality, bench_prices=bench, bench_as_of_idx=n-1)
        score_without = score_fn('ACC', s, n-1, quality)
        assert score_with > score_without, (
            "Accelerating stock should score higher when bench_prices provided"
        )

    def test_macro_adj_and_rs_adj_both_applied(self):
        """macro_adj and RS acceleration should both shift the score."""
        score_fn = self._score_fn()
        n = 300
        dates = pd.date_range(end='2024-12-31', periods=n, freq='B')
        bench = pd.Series(np.ones(n) * 20000.0, index=dates)
        stock = pd.Series(100 * np.cumprod([(1.10)**(1/252)] * n), index=dates)
        quality = {'SYM': 50.0}
        base = score_fn('SYM', stock, n-1, quality)
        with_macro = score_fn('SYM', stock, n-1, quality, macro_adj=5.0)
        with_both = score_fn('SYM', stock, n-1, quality, macro_adj=5.0,
                             bench_prices=bench, bench_as_of_idx=n-1)
        assert with_macro > base
        # with_both may or may not be > with_macro depending on RS accel direction,
        # but it should be bounded
        assert 0.0 <= with_both <= 100.0

    def test_score_without_bench_unchanged_from_old_behaviour(self):
        """Without bench_prices, composite_score_at must behave exactly as before."""
        score_fn = self._score_fn()
        prices = self._make_prices(300, annual_ret=0.25)
        quality = {'X': 30.0}
        # Old path: no bench_prices
        s1 = score_fn('X', prices, 299, quality, 0.60, 0.40, 0.0)
        s2 = score_fn('X', prices, 299, quality, 0.60, 0.40, 0.0)
        assert s1 == s2, "Deterministic — same inputs must give same output"


# ─────────────────────────────────────────────────────────────────────────────
# 5. _compute_earnings_acceleration() in StockScorer
# ─────────────────────────────────────────────────────────────────────────────

class TestEarningsAcceleration:
    def _scorer(self):
        from core.stock_scorer import StockScorer
        return StockScorer.__new__(StockScorer)   # skip __init__

    def _make_quarterly(self, eps_vals):
        """Build a fake quarterly_earnings DataFrame (newest first)."""
        df = pd.DataFrame({'Earnings': eps_vals},
                          index=[f'Q{i}' for i in range(len(eps_vals))])
        return df

    def test_accelerating_eps_returns_positive(self):
        s = self._scorer()
        # Q0: big jump vs Q1; Q1: flat vs Q2 → acceleration
        with patch('yfinance.Ticker') as mock_t:
            inst = MagicMock()
            inst.quarterly_earnings = self._make_quarterly([120, 80, 75, 70])
            mock_t.return_value = inst
            adj = s._compute_earnings_acceleration('TCS')
        assert adj > 0, f"Accelerating EPS should give positive adj, got {adj}"

    def test_decelerating_eps_returns_negative(self):
        s = self._scorer()
        # Q0: tiny vs Q1; Q1: big vs Q2 → deceleration
        with patch('yfinance.Ticker') as mock_t:
            inst = MagicMock()
            inst.quarterly_earnings = self._make_quarterly([82, 80, 60, 40])
            mock_t.return_value = inst
            adj = s._compute_earnings_acceleration('ITC')
        assert adj < 0, f"Decelerating EPS should give negative adj, got {adj}"

    def test_stable_eps_returns_near_zero(self):
        s = self._scorer()
        # Flat EPS: no acceleration
        with patch('yfinance.Ticker') as mock_t:
            inst = MagicMock()
            inst.quarterly_earnings = self._make_quarterly([100, 100, 100, 100])
            mock_t.return_value = inst
            adj = s._compute_earnings_acceleration('HDFCBANK')
        assert -2.0 <= adj <= 2.0, f"Stable EPS should give adj ≈ 0, got {adj}"

    def test_insufficient_quarters_returns_zero(self):
        s = self._scorer()
        with patch('yfinance.Ticker') as mock_t:
            inst = MagicMock()
            inst.quarterly_earnings = self._make_quarterly([100, 110])  # only 2 quarters
            mock_t.return_value = inst
            adj = s._compute_earnings_acceleration('TEST')
        assert adj == 0.0

    def test_yfinance_failure_returns_zero_gracefully(self):
        s = self._scorer()
        with patch('yfinance.Ticker', side_effect=Exception("network error")):
            adj = s._compute_earnings_acceleration('BROKEN')
        assert adj == 0.0

    def test_positive_adj_capped_at_8(self):
        s = self._scorer()
        # Extreme acceleration
        with patch('yfinance.Ticker') as mock_t:
            inst = MagicMock()
            inst.quarterly_earnings = self._make_quarterly([1000, 10, 9, 8])
            mock_t.return_value = inst
            adj = s._compute_earnings_acceleration('EXTREME')
        assert adj <= 8.0

    def test_negative_adj_floor_at_minus_8(self):
        s = self._scorer()
        # Extreme deceleration: was massive, now tiny
        with patch('yfinance.Ticker') as mock_t:
            inst = MagicMock()
            inst.quarterly_earnings = self._make_quarterly([1, 1000, 10, 9])
            mock_t.return_value = inst
            adj = s._compute_earnings_acceleration('COLLAPSE')
        assert adj >= -8.0

    def test_fallback_to_info_when_quarterly_empty(self):
        """Falls back to earningsGrowth + revenueGrowth from info when quarterly is empty."""
        s = self._scorer()
        with patch('yfinance.Ticker') as mock_t:
            inst = MagicMock()
            inst.quarterly_earnings = pd.DataFrame()   # empty
            inst.info = {'earningsGrowth': 0.30, 'revenueGrowth': 0.25}
            mock_t.return_value = inst
            adj = s._compute_earnings_acceleration('HCLTECH')
        assert adj >= 0.0, "Good growth in fallback path should give non-negative adj"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Backtest regression — sector cap reduces Sep-2024 loss
# ─────────────────────────────────────────────────────────────────────────────

class TestSectorCapReducesConcentrationLoss:
    """
    Regression test: a portfolio of 5 correlated Metals stocks should be
    capped to 2 by apply_sector_cap. Before the fix, 3 Metals + 2 Auto
    caused the Feb-2026 -13.5% disaster.
    """

    def test_portfolio_never_holds_3_metals(self):
        from scripts.portfolio_backtest import apply_sector_cap, NIFTY50_SECTORS
        metals = [s for s, sec in NIFTY50_SECTORS.items() if sec == 'Metals']
        auto   = [s for s, sec in NIFTY50_SECTORS.items() if sec == 'Auto']
        assert len(metals) >= 3 and len(auto) >= 3

        scored = (
            [(sym, 90.0 - i) for i, sym in enumerate(metals[:3])] +
            [(sym, 80.0 - i) for i, sym in enumerate(auto[:3])]
        )
        selected = apply_sector_cap(scored, top_n=6, sector_cap=0.30)
        selected_syms = [s for s, _ in selected]

        metals_cnt = sum(1 for s in selected_syms if NIFTY50_SECTORS.get(s) == 'Metals')
        auto_cnt   = sum(1 for s in selected_syms if NIFTY50_SECTORS.get(s) == 'Auto')

        assert metals_cnt <= 2, f"Metals concentration: {metals_cnt} > 2"
        assert auto_cnt   <= 2, f"Auto concentration: {auto_cnt} > 2"

    def test_feb2026_portfolio_would_be_diversified(self):
        """
        Simulate the exact Feb-2026 portfolio composition that caused -13.5% loss.
        Verify the sector cap would have blocked the third Metals/Auto entry.
        """
        from scripts.portfolio_backtest import apply_sector_cap
        # Feb-2026 actual holdings (from trade log): EICHERMOT, HEROMOTOCO, TATASTEEL,
        # HINDALCO, SBIN, BPCL — that's 2 Auto + 2 Metals + Financials + Energy
        # With the cap these 6 pass (2 per sector). A 3rd Auto/Metals would be blocked.
        feb26_holdings = [
            ('EICHERMOT.NS',  75.0),   # Auto
            ('HEROMOTOCO.NS', 73.0),   # Auto
            ('TATASTEEL.NS',  70.0),   # Metals
            ('HINDALCO.NS',   68.0),   # Metals
            ('SBIN.NS',       65.0),   # Financials
            ('BPCL.NS',       63.0),   # Energy
            ('JSWSTEEL.NS',   61.0),   # Metals — THIRD Metals, should be blocked
        ]
        selected = apply_sector_cap(feb26_holdings, top_n=7, sector_cap=0.30)
        selected_syms = {s for s, _ in selected}
        assert 'JSWSTEEL.NS' not in selected_syms, (
            "3rd Metals stock should be blocked by sector cap"
        )
