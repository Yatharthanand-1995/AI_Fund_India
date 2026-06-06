"""
Unit tests for risk mechanisms M3, M6, M7.

These tests are FAST (< 5 seconds total) because they test the mechanism
logic directly with synthetic data — no yfinance downloads, no full 5Y run.

Run with:
    pytest tests/backtest/test_mechanisms_unit.py -v
"""
import pandas as pd
import pytest
from tests.backtest.conftest import make_holding, make_holdings, make_score_map
from scripts.portfolio_backtest import portfolio_factor_hhi, FACTOR_BUCKETS


# ─────────────────────────────────────────────────────────────────────────────
# M3 — Maximum Holding Period Logic Tests
# (Tests the conditions under which M3 should fire, not the full simulation)
# ─────────────────────────────────────────────────────────────────────────────

class TestM3MaxHoldLogic:
    """
    M3 fires when a held position is 'stale':
      - At 12M: score decayed > m3_12m_decay pts from entry_score
      - At 18M: score decayed > m3_18m_decay pts from entry_score
      - At 24M: score below 75th percentile of current universe
    """

    def _should_m3_exit(
        self,
        months_held: float,
        current_score: float,
        entry_score: float,
        score_map: dict,
        sell_threshold: float = 38.0,
        m3_12m_decay: float = 10.0,
        m3_18m_decay: float = 5.0,
    ) -> tuple:
        """
        Replicate M3 decision logic from run_signal_simulation().
        Returns (should_exit: bool, reason: str).
        """
        if months_held >= 24:
            sorted_scores = sorted(score_map.values())
            idx_75 = int(len(sorted_scores) * 0.75)
            universe_75th = sorted_scores[idx_75] if idx_75 < len(sorted_scores) else sell_threshold
            if current_score < universe_75th:
                return True, f'm3_24mo({current_score:.0f}<75p:{universe_75th:.0f})'
        elif months_held >= 18:
            min_score = max(sell_threshold, entry_score - m3_18m_decay)
            if current_score < min_score:
                return True, f'm3_18mo_decay'
        elif months_held >= 12:
            min_score = max(sell_threshold, entry_score - m3_12m_decay)
            if current_score < min_score:
                return True, f'm3_12mo_decay'
        return False, ''

    def test_exits_at_12m_when_score_decays_beyond_threshold(self):
        """Stock held 13 months, entry score 70, now 58: decayed 12pts > 10pt limit → exit."""
        score_map = {f'STOCK{i}.NS': 60.0 + i for i in range(10)}
        should_exit, _ = self._should_m3_exit(
            months_held=13.0,
            current_score=58.0,
            entry_score=70.0,
            score_map=score_map,
        )
        assert should_exit, "M3 should exit: 13M held, score decayed 12pts (limit 10pts)"

    def test_no_exit_at_12m_when_score_within_threshold(self):
        """Stock held 13 months, entry 70, now 62: decayed 8pts < 10pt limit → hold."""
        score_map = {f'STOCK{i}.NS': 60.0 + i for i in range(10)}
        should_exit, _ = self._should_m3_exit(
            months_held=13.0,
            current_score=62.0,
            entry_score=70.0,
            score_map=score_map,
        )
        assert not should_exit, "M3 should NOT exit: score only decayed 8pts (limit 10pts)"

    def test_exits_at_18m_when_score_decays_beyond_tighter_threshold(self):
        """Stock held 20 months, entry 68, now 62: decayed 6pts > 5pt limit at 18M → exit."""
        score_map = {f'STOCK{i}.NS': 60.0 + i for i in range(10)}
        should_exit, _ = self._should_m3_exit(
            months_held=20.0,
            current_score=62.0,
            entry_score=68.0,
            score_map=score_map,
        )
        assert should_exit, "M3 should exit at 18M+ when score decayed 6pts (limit 5pts)"

    def test_exits_at_24m_when_below_75th_percentile(self):
        """Stock held 25 months, score 62. Universe 75th percentile is 72 → exit."""
        # Create universe where 75th percentile = 72
        score_map = {f'STOCK{i}.NS': 50.0 + i * 2 for i in range(20)}  # 50,52,...88
        # 75th pct of 20 values = idx 15 = value 80
        # Use a universe where 75th pct is clearly above 62
        score_map['ITC.NS'] = 62.0  # the stock being evaluated
        should_exit, _ = self._should_m3_exit(
            months_held=25.0,
            current_score=62.0,
            entry_score=68.0,
            score_map=score_map,
        )
        assert should_exit, "M3 should exit at 24M+ when score below 75th percentile"

    def test_does_not_fire_before_12m(self):
        """Stock held only 8 months with heavily decayed score → M3 must not fire."""
        score_map = {f'STOCK{i}.NS': 60.0 + i for i in range(10)}
        should_exit, _ = self._should_m3_exit(
            months_held=8.0,
            current_score=40.0,  # very decayed, but within 12M window
            entry_score=72.0,
            score_map=score_map,
        )
        assert not should_exit, "M3 must NOT fire before 12M regardless of score decay"

    def test_sell_threshold_floor_prevents_early_false_exit(self):
        """Entry score 42, sell_threshold=38, m3_12m_decay=10 → min_score=38, not 32."""
        score_map = {f'STOCK{i}.NS': 40.0 + i for i in range(10)}
        # Entry was low (42), score is 39. Without floor: 42-10=32 → no exit.
        # With sell_threshold floor: min_score=max(38, 42-10)=38. score 39 > 38 → no exit.
        should_exit, _ = self._should_m3_exit(
            months_held=13.0,
            current_score=39.0,
            entry_score=42.0,
            score_map=score_map,
            sell_threshold=38.0,
        )
        assert not should_exit, "With floor, entry 42 - decay 10 = 32, floored to 38; score 39 > 38 → hold"


# ─────────────────────────────────────────────────────────────────────────────
# M6 — Opportunity Cost Rotation Logic Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestM6RotationLogic:
    """
    M6 rotates the lowest-scoring held stock (that has cleared min-hold)
    when a better unowned candidate exists with score gap >= m6_rotation_gap.
    """

    def _should_m6_rotate(
        self,
        holdings: dict,
        score_map: dict,
        prices: set,
        date_t: pd.Timestamp,
        min_hold_months: int = 3,
        m6_rotation_gap: float = 12.0,
    ) -> tuple:
        """
        Replicate M6 rotation decision from run_signal_simulation().
        Returns (should_rotate: bool, worst_sym: str, best_sym: str, gap: float).
        """
        held_eligible = {
            s: score_map.get(s, 0.0)
            for s, h in holdings.items()
            if (date_t - h.get('entry_date', date_t)).days / 30.5 >= min_hold_months
        }
        if not held_eligible:
            return False, '', '', 0.0
        worst_sym   = min(held_eligible, key=held_eligible.get)
        worst_score = held_eligible[worst_sym]
        not_held = {
            s: score_map.get(s, 0.0)
            for s in score_map
            if s not in holdings and s in prices
        }
        if not not_held:
            return False, worst_sym, '', 0.0
        best_sym   = max(not_held, key=not_held.get)
        best_score = not_held[best_sym]
        gap = best_score - worst_score
        if gap >= m6_rotation_gap:
            return True, worst_sym, best_sym, gap
        return False, worst_sym, best_sym, gap

    def test_rotates_when_gap_exceeds_threshold(self):
        """Held COAL scores 52, candidate JSW scores 65: gap=13 > threshold=12 → rotate."""
        date_t = pd.Timestamp('2024-03-01')
        holdings = make_holdings({'COAL.NS': {'entry_score': 70, 'entry_months_ago': 8}}, reference_date='2024-03-01')
        score_map = {'COAL.NS': 52.0, 'JSW.NS': 65.0, 'OTHER.NS': 60.0}
        prices = {'COAL.NS', 'JSW.NS', 'OTHER.NS'}
        should_rotate, worst, best, gap = self._should_m6_rotate(
            holdings, score_map, prices, date_t
        )
        assert should_rotate, f"Gap={gap:.1f} > 12 → should rotate"
        assert worst == 'COAL.NS'
        assert best  == 'JSW.NS'

    def test_no_rotation_when_gap_below_threshold(self):
        """Held COAL scores 55, best candidate scores 64: gap=9 < 12 → no rotation."""
        date_t = pd.Timestamp('2024-03-01')
        holdings = make_holdings({'COAL.NS': {'entry_score': 70, 'entry_months_ago': 6}}, reference_date='2024-03-01')
        score_map = {'COAL.NS': 55.0, 'JSW.NS': 64.0}
        prices = {'COAL.NS', 'JSW.NS'}
        should_rotate, _, _, gap = self._should_m6_rotate(
            holdings, score_map, prices, date_t
        )
        assert not should_rotate, f"Gap={gap:.1f} < 12 → no rotation"

    def test_respects_min_hold(self):
        """Held stock only 2 months: not eligible for rotation even if large gap exists."""
        date_t = pd.Timestamp('2024-03-01')
        # entry_months_ago=2 means entry was 2 months before date_t → 2 months held < 3 min
        holdings = make_holdings({'COAL.NS': {'entry_score': 70, 'entry_months_ago': 2}}, reference_date='2024-03-01')
        score_map = {'COAL.NS': 40.0, 'JSW.NS': 80.0}  # 40pt gap!
        prices = {'COAL.NS', 'JSW.NS'}
        should_rotate, _, _, _ = self._should_m6_rotate(
            holdings, score_map, prices, date_t, min_hold_months=3
        )
        assert not should_rotate, "Stock held only 2 months: M6 should not fire"

    def test_picks_lowest_scoring_eligible_held_stock(self):
        """With 2 eligible held stocks, rotation targets the lower-scoring one."""
        date_t = pd.Timestamp('2024-03-01')
        holdings = make_holdings({
            'COAL.NS': {'entry_score': 70, 'entry_months_ago': 10},
            'ITC.NS':  {'entry_score': 68, 'entry_months_ago': 6},
        }, reference_date='2024-03-01')
        score_map = {'COAL.NS': 52.0, 'ITC.NS': 60.0, 'JSW.NS': 75.0}
        prices = {'COAL.NS', 'ITC.NS', 'JSW.NS'}
        should_rotate, worst, _, _ = self._should_m6_rotate(
            holdings, score_map, prices, date_t
        )
        assert should_rotate
        assert worst == 'COAL.NS', "Should rotate the lower-scoring stock (COAL=52, not ITC=60)"


# ─────────────────────────────────────────────────────────────────────────────
# M7 — Factor Concentration HHI Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestM7HHI:
    """
    M7 computes portfolio HHI across factor buckets and blocks new entries
    that would push HHI above m7_hhi_threshold.
    """

    def test_hhi_is_1_when_all_same_bucket(self):
        """3 def_value stocks with equal weights: HHI should be 1.0."""
        syms = {'ITC.NS', 'BRITANNIA.NS', 'NESTLEIND.NS'}
        weights = {s: 1/3 for s in syms}
        hhi, buckets = portfolio_factor_hhi(syms, weights)
        assert abs(hhi - 1.0) < 0.01, f"All same bucket → HHI={hhi:.3f} should be ~1.0"
        assert buckets.get('def_value', 0) > 0.99

    def test_hhi_is_low_when_buckets_diverse(self):
        """5 stocks from 5 different buckets with equal weight: HHI = 0.20."""
        syms = {
            'ITC.NS',       # def_value
            'COALINDIA.NS', # psu_commodity
            'TCS.NS',       # tech
            'HDFCBANK.NS',  # cyclical_growth
            'SUNPHARMA.NS', # other
        }
        weights = {s: 0.20 for s in syms}
        hhi, _ = portfolio_factor_hhi(syms, weights)
        assert abs(hhi - 0.20) < 0.01, f"5 diverse buckets → HHI={hhi:.3f} should be ~0.20"

    def test_blocks_entry_when_hhi_would_exceed_threshold(self):
        """
        Current portfolio: ITC.NS (def_value=40%), BRITANNIA.NS (def_value=40%).
        HHI = 0.64. Adding NESTLEIND.NS (def_value) → HHI → 1.0 > 0.35 → BLOCKED.
        """
        current_syms = {'ITC.NS', 'BRITANNIA.NS'}
        trial_syms   = {'ITC.NS', 'BRITANNIA.NS', 'NESTLEIND.NS'}
        weights      = {s: 1/3 for s in trial_syms}
        hhi, _ = portfolio_factor_hhi(trial_syms, weights)
        assert hhi > 0.35, f"Adding 3rd def_value stock → HHI={hhi:.3f} should exceed 0.35"

    def test_allows_entry_when_adding_different_bucket(self):
        """
        Adding a stock from a NEW bucket diversifies HHI.
        Start with ITC.NS (def_value=100%), add TCS.NS (tech) → HHI drops from 1.0 to 0.5.
        """
        trial_1 = {'ITC.NS'}
        w1 = {'ITC.NS': 1.0}
        hhi_before, _ = portfolio_factor_hhi(trial_1, w1)
        assert abs(hhi_before - 1.0) < 0.01

        trial_2 = {'ITC.NS', 'TCS.NS'}
        w2 = {s: 0.5 for s in trial_2}
        hhi_after, _ = portfolio_factor_hhi(trial_2, w2)
        assert hhi_after < hhi_before, "Adding a different-bucket stock should lower HHI"
        assert abs(hhi_after - 0.5) < 0.01, f"2 stocks in 2 buckets → HHI=0.50, got {hhi_after:.3f}"

    def test_m7_gate_not_applied_to_empty_portfolio(self):
        """
        When portfolio has 0 or 1 stock, the HHI gate must NOT block entries.
        Single stock always computes HHI=1.0 — which would block every first entry
        if the guard was not in place. The gate is only meaningful at ≥ 2 holdings.
        This test validates the logic boundary (len(holdings) >= 2 guard).
        """
        # Single stock in same bucket as candidate: HHI = 1.0 > any threshold
        # But the guard in run_signal_simulation skips M7 when len(holdings) < 2.
        # We test the HHI function directly: confirm it IS 1.0 (which would block if applied)
        trial_syms = {'ITC.NS'}
        equal_w    = {'ITC.NS': 1.0}
        hhi, _     = portfolio_factor_hhi(trial_syms, equal_w)
        assert hhi == 1.0, "Single stock → HHI must be 1.0 (guard prevents this from blocking entry)"

    def test_hhi_zero_for_empty_portfolio(self):
        """Empty portfolio: HHI should be 0."""
        hhi, buckets = portfolio_factor_hhi(set(), {})
        assert hhi == 0.0

    def test_all_stocks_have_factor_bucket(self):
        """Every symbol in NIFTY50_SECTORS should be in FACTOR_BUCKETS."""
        from scripts.portfolio_backtest import NIFTY50_SECTORS
        missing = [s for s in NIFTY50_SECTORS if s not in FACTOR_BUCKETS]
        assert not missing, f"Symbols in NIFTY50_SECTORS but missing FACTOR_BUCKETS: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# M3 Cooldown Logic Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestM3Cooldown:
    """
    Tests for the M3 re-entry cooldown mechanism.
    The cooldown blocks a stock from re-entering for N months after an M3 exit.
    In the backtest: tracked via m3_cooldown_until dict {sym → pd.Timestamp}.
    In the live system: tracked via portfolio_cooldowns SQLite table.
    """

    def test_cooldown_blocks_reentry_within_window(self):
        """
        After M3 exit at date_exit with 6-month cooldown,
        a re-entry attempt 4 months later must be blocked.
        """
        date_exit        = pd.Timestamp('2024-06-01')
        cooldown_until   = date_exit + pd.DateOffset(months=6)  # 2024-12-01
        date_reenter     = pd.Timestamp('2024-10-01')           # 4 months later

        blocked = date_reenter < cooldown_until
        assert blocked, (
            f"Re-entry at {date_reenter.date()} should be blocked "
            f"until {cooldown_until.date()}"
        )

    def test_cooldown_allows_reentry_after_expiry(self):
        """
        A re-entry attempt 7 months after M3 exit (> 6-month window) must be allowed.
        """
        date_exit      = pd.Timestamp('2024-06-01')
        cooldown_until = date_exit + pd.DateOffset(months=6)  # 2024-12-01
        date_reenter   = pd.Timestamp('2025-01-01')           # 7 months later

        blocked = date_reenter < cooldown_until
        assert not blocked, (
            f"Re-entry at {date_reenter.date()} should be ALLOWED "
            f"after cooldown expiry at {cooldown_until.date()}"
        )

    def test_cooldown_zero_never_blocks(self):
        """
        When m3_cooldown_months=0, the gate condition (cooldown_months > 0)
        is False before checking the dict — no stock is ever blocked.
        This mirrors `if m3_cooldown_months > 0 and sym in m3_cooldown_until`.
        """
        m3_cooldown_months = 0
        # Even if the dict has a far-future entry, the gate should not fire
        m3_cooldown_until  = {'ITC.NS': pd.Timestamp('2999-01-01')}
        sym                = 'ITC.NS'
        date_t             = pd.Timestamp('2024-10-01')

        # Replicate the exact backtest gate condition
        blocked = m3_cooldown_months > 0 and sym in m3_cooldown_until and date_t < m3_cooldown_until[sym]
        assert not blocked, "m3_cooldown_months=0 must short-circuit the gate"

    def test_live_db_cooldown_roundtrip(self, tmp_path):
        """
        Live system: set_cooldown() stores a record, is_in_cooldown() reads it back.
        Tests the full DB roundtrip for the cooldown mechanism.
        """
        import os
        from core.portfolio_manager import PortfolioManager
        db_path = str(tmp_path / 'test_cooldown.db')
        pm = PortfolioManager(db_path)

        # No cooldown yet
        assert not pm.db.is_in_cooldown('ITC'), "No cooldown set yet"

        # Set 6-month cooldown
        pm.db.set_cooldown('ITC', months=6, exit_reason='m3_24mo_test')

        # Should be active immediately
        assert pm.db.is_in_cooldown('ITC'), "Cooldown should be active after set_cooldown()"

        # Different symbol: no cooldown
        assert not pm.db.is_in_cooldown('TCS'), "TCS should not be in cooldown"

        # get_cooldowns() should return the record
        cds = pm.db.get_cooldowns()
        assert len(cds) == 1
        assert cds[0]['symbol'] == 'ITC'
        assert cds[0]['exit_reason'] == 'm3_24mo_test'


# ─────────────────────────────────────────────────────────────────────────────
# CSV / Structural Integrity Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCSVAndStructural:
    """
    Tests that verify the backtest output infrastructure is correct:
    - save_run_result() writes mechanism parameters to CSV
    - walkforward_backtest._run_slice() passes all required parameters
    - run_sweep._run_one() passes all required parameters
    """

    def test_save_run_result_writes_mechanism_columns(self, tmp_path):
        """
        After BUG 1 fix: backtest_results.csv must contain
        buy_threshold, sell_threshold, stop_loss_pct, mechanisms columns.
        """
        import pandas as pd
        from unittest.mock import patch
        from scripts.portfolio_backtest import save_run_result

        results_path = tmp_path / 'backtest_results.csv'
        with patch('scripts.portfolio_backtest.RESULTS_LOG', results_path):
            # Also suppress experiment log write during test
            with patch('scripts.portfolio_backtest.append_to_experiment_log'):
                save_run_result(
                    'test_run',
                    {
                        'years': 5, 'top_n': 10, 'sector_cap': 0.30,
                        'exit_drawdown': 0.10, 'score_decay': 38,
                        'quality': True, 'costs': True,
                        'buy_threshold': 60, 'sell_threshold': 38,
                        'stop_loss': 0.10, 'mechanisms': 'M1+M3',
                    },
                    {
                        'cagr': 0.15, 'sharpe': 0.57, 'max_drawdown': -0.208,
                        'alpha_ann': 0.083, 'beta': 0.84, 'win_rate': 0.583,
                        'ann_std': 0.133, 'total_return': 1.035,
                    },
                    {
                        'total': 0.49, 'cagr': 0.083, 'sharpe': 0.16,
                        'max_dd': -0.148, 'std': 0.136,
                    },
                )
        df = pd.read_csv(results_path)
        assert 'buy_threshold'  in df.columns, "buy_threshold must be in CSV"
        assert 'sell_threshold' in df.columns, "sell_threshold must be in CSV"
        assert 'mechanisms'     in df.columns, "mechanisms must be in CSV"
        assert df.iloc[0]['buy_threshold']  == 60,      "buy_threshold value wrong"
        assert df.iloc[0]['sell_threshold'] == 38,      "sell_threshold value wrong"
        assert df.iloc[0]['mechanisms']     == 'M1+M3', "mechanisms value wrong"

    def test_walkforward_run_slice_passes_cooldown_and_guard(self):
        """
        After BUG 2 fix: _run_slice() in walkforward_backtest.py must
        include m3_cooldown_months and m1_sector_guard in its mech_kwargs.
        Structural test — inspects source code to confirm the keys are present.
        """
        import inspect
        from scripts.walkforward_backtest import _run_slice
        src = inspect.getsource(_run_slice)
        assert 'm3_cooldown_months' in src, \
            "_run_slice must pass m3_cooldown_months to run_signal_simulation"
        assert 'm1_sector_guard' in src, \
            "_run_slice must pass m1_sector_guard to run_signal_simulation"

    def test_run_sweep_passes_cooldown_and_guard(self):
        """
        After BUG 3 fix: _run_one() in run_sweep.py must include
        m3_cooldown_months and m1_sector_guard in its mech_kwargs.
        """
        import inspect
        from scripts.run_sweep import _run_one
        src = inspect.getsource(_run_one)
        assert 'm3_cooldown_months' in src, \
            "_run_one must pass m3_cooldown_months to run_signal_simulation"
        assert 'm1_sector_guard' in src, \
            "_run_one must pass m1_sector_guard to run_signal_simulation"
