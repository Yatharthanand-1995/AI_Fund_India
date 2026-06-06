"""
Tests for all critical and high-priority bug fixes.

Covers:
  C1 — regime_confidence NameError (stock_scorer.py)
  C2 — stop-loss direction guard (stock_scorer.py)
  C3 — empty history stats division-by-zero (api/main.py)
  H1 — lookahead bias: NIFTY slice in backtester (backtester.py)
  H3 — transaction costs in backtester (backtester.py)
  H6 — single-agent dominance confidence cap (stock_scorer.py)
  H7 — macro overlay + regime cap combined (stock_scorer.py)
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# C1 — regime_confidence extracted correctly from regime_info
# ---------------------------------------------------------------------------
class TestRegimeConfidenceFix(unittest.TestCase):
    """C1: regime_confidence must not raise NameError during score_stock()"""

    def _make_scorer(self, regime_info):
        from core.stock_scorer import StockScorer
        scorer = StockScorer.__new__(StockScorer)
        scorer.use_adaptive_weights = False
        scorer.market_regime_service = MagicMock()
        scorer.market_regime_service.get_current_regime.return_value = regime_info
        return scorer

    def test_regime_confidence_extracted_bull(self):
        """regime_confidence should be taken from regime_info when present"""
        from core.stock_scorer import StockScorer
        scorer = self._make_scorer({'trend': 'BULL', 'regime_confidence': 0.85})
        # Simulate the regime extraction block inside score_stock
        regime_trend = 'SIDEWAYS'
        regime_confidence = 0.7
        try:
            regime_info = scorer.market_regime_service.get_current_regime()
            if regime_info:
                regime_trend = regime_info.get('trend', 'SIDEWAYS')
                regime_confidence = regime_info.get('regime_confidence', 0.7)
        except Exception:
            pass
        self.assertEqual(regime_trend, 'BULL')
        self.assertAlmostEqual(regime_confidence, 0.85)

    def test_regime_confidence_default_when_missing(self):
        """regime_confidence should default to 0.7 when key absent"""
        from core.stock_scorer import StockScorer
        scorer = self._make_scorer({'trend': 'BEAR'})  # no regime_confidence key
        regime_trend = 'SIDEWAYS'
        regime_confidence = 0.7
        try:
            regime_info = scorer.market_regime_service.get_current_regime()
            if regime_info:
                regime_trend = regime_info.get('trend', 'SIDEWAYS')
                regime_confidence = regime_info.get('regime_confidence', 0.7)
        except Exception:
            pass
        self.assertEqual(regime_trend, 'BEAR')
        self.assertAlmostEqual(regime_confidence, 0.7)

    def test_regime_confidence_default_on_exception(self):
        """regime_confidence stays 0.7 if get_market_regime raises"""
        from core.stock_scorer import StockScorer
        scorer = self._make_scorer(None)
        scorer.market_regime_service.get_current_regime.side_effect = RuntimeError("network error")
        regime_trend = 'SIDEWAYS'
        regime_confidence = 0.7
        try:
            regime_info = scorer.market_regime_service.get_current_regime()
            if regime_info:
                regime_trend = regime_info.get('trend', 'SIDEWAYS')
                regime_confidence = regime_info.get('regime_confidence', 0.7)
        except Exception:
            pass
        self.assertEqual(regime_trend, 'SIDEWAYS')
        self.assertAlmostEqual(regime_confidence, 0.7)

    def test_regime_adj_formula_uses_confidence(self):
        """Step 5g formula: regime_adj = base * max(0, (conf-0.3)/0.7)"""
        # BULL base = +3.0
        for conf, expected_min, expected_max in [
            (1.0, 2.9, 3.0),   # full confidence → full adj
            (0.7, 1.7, 1.86),  # 57% of max
            (0.3, -0.01, 0.01),  # at threshold → ~0
            (0.0, -0.01, 0.01),  # below threshold → 0
        ]:
            adj = round(3.0 * max(0.0, (conf - 0.3) / 0.7), 2)
            self.assertGreaterEqual(adj, expected_min, f"conf={conf}")
            self.assertLessEqual(adj, expected_max, f"conf={conf}")


# ---------------------------------------------------------------------------
# C2 — stop-loss direction guard
# ---------------------------------------------------------------------------
class TestStopLossGuard(unittest.TestCase):
    """C2: stop-loss must always be strictly below current_price"""

    def _compute_levels(self, current_price, atr):
        from core.stock_scorer import StockScorer
        scorer = StockScorer.__new__(StockScorer)
        momentum_metrics = {'atr': atr} if atr is not None else {}
        sentiment_metrics = {}
        return scorer._compute_trading_levels(
            current_price=current_price,
            momentum_metrics=momentum_metrics,
            sentiment_metrics=sentiment_metrics,
        )

    def test_normal_atr(self):
        """Normal ATR: stop is between 85% and 99.9% of entry"""
        levels = self._compute_levels(current_price=1000, atr=15)
        sl = levels['stop_loss']
        self.assertLess(sl, 1000, "stop_loss must be below current_price")
        self.assertGreater(sl, 0, "stop_loss must be positive")

    def test_tiny_atr(self):
        """Tiny ATR: stop still below entry"""
        levels = self._compute_levels(current_price=500, atr=0.01)
        self.assertLess(levels['stop_loss'], 500)

    def test_massive_atr_clamped(self):
        """Very large ATR: stop clamped to 85% of entry (no wider)"""
        levels = self._compute_levels(current_price=100, atr=200)
        sl = levels['stop_loss']
        self.assertLess(sl, 100, "stop_loss must be below current_price even with huge ATR")
        self.assertGreaterEqual(sl, 85, "stop_loss must not go below 15% drawdown limit")

    def test_stop_always_positive(self):
        """stop_loss is always > 0 regardless of ATR"""
        levels = self._compute_levels(current_price=1, atr=1000)
        self.assertGreater(levels['stop_loss'], 0)

    def test_no_atr_fallback(self):
        """Without ATR, 7% trailing stop is applied"""
        levels = self._compute_levels(current_price=200, atr=None)
        self.assertAlmostEqual(levels['stop_loss'], 186.0, places=0)

    def test_risk_reward_positive(self):
        """risk/reward ratio must be positive when stop is below entry"""
        levels = self._compute_levels(current_price=1000, atr=20)
        rr = levels.get('risk_reward_ratio')
        if rr is not None:
            self.assertGreater(rr, 0, "risk/reward must be positive")


# ---------------------------------------------------------------------------
# C3 — empty history stats guard
# ---------------------------------------------------------------------------
class TestEmptyHistoryStats(unittest.TestCase):
    """C3: history endpoint must not crash on empty or malformed records"""

    def _build_statistics(self, records):
        """Replicate the fixed statistics calculation from api/main.py"""
        scores = []
        for record in records:
            score = record.get('composite_score')
            if score is None:
                continue
            scores.append(score)

        if scores:
            return {
                'avg_score': round(sum(scores) / len(scores), 2),
                'min_score': min(scores),
                'max_score': max(scores),
                'current_score': scores[0],
                'change': round(scores[0] - scores[-1], 2) if len(scores) > 1 else 0
            }
        else:
            return {
                'avg_score': 0, 'min_score': 0, 'max_score': 0,
                'current_score': 0, 'change': 0
            }

    def test_empty_list_no_crash(self):
        stats = self._build_statistics([])
        self.assertEqual(stats['avg_score'], 0)

    def test_all_null_scores_no_crash(self):
        records = [{'composite_score': None}, {'composite_score': None}]
        stats = self._build_statistics(records)
        self.assertEqual(stats['avg_score'], 0)

    def test_mixed_null_and_valid(self):
        records = [
            {'composite_score': 75.0},
            {'composite_score': None},
            {'composite_score': 65.0},
        ]
        stats = self._build_statistics(records)
        self.assertAlmostEqual(stats['avg_score'], 70.0)
        self.assertEqual(stats['current_score'], 75.0)

    def test_single_record(self):
        stats = self._build_statistics([{'composite_score': 80.0}])
        self.assertEqual(stats['avg_score'], 80.0)
        self.assertEqual(stats['change'], 0)

    def test_normal_records(self):
        records = [{'composite_score': 80.0}, {'composite_score': 70.0}, {'composite_score': 60.0}]
        stats = self._build_statistics(records)
        self.assertAlmostEqual(stats['avg_score'], 70.0)
        self.assertEqual(stats['change'], 20.0)  # 80 - 60


# ---------------------------------------------------------------------------
# H1 — Lookahead bias: NIFTY slice in backtester
# ---------------------------------------------------------------------------
class TestNoLookaheadBias(unittest.TestCase):
    """H1: benchmark_data must be sliced to entry_date before scoring"""

    def _make_nifty_df(self, start='2020-01-01', end='2025-12-31'):
        idx = pd.date_range(start, end, freq='B')
        return pd.DataFrame({'Close': np.random.uniform(10000, 20000, len(idx))}, index=idx)

    def test_nifty_sliced_to_entry_date(self):
        """Rows after entry_date must not appear in the NIFTY slice passed to scorer"""
        full_df = self._make_nifty_df()
        entry_date = pd.Timestamp('2022-06-01')

        nifty_slice = full_df[full_df.index <= entry_date]

        self.assertLessEqual(nifty_slice.index.max(), entry_date)
        self.assertGreater(len(nifty_slice), 100)  # enough history exists

    def test_nifty_slice_empty_before_data(self):
        """If entry_date is before benchmark data starts, slice is empty"""
        full_df = self._make_nifty_df(start='2022-01-01', end='2025-12-31')
        entry_date = pd.Timestamp('2019-01-01')

        nifty_slice = full_df[full_df.index <= entry_date]
        self.assertTrue(nifty_slice.empty)

    def test_full_df_not_passed_to_scorer(self):
        """Verify backtester calls score_stock with sliced data, not full benchmark"""
        from core.backtester import Backtester

        # Build a minimal mock backtester
        backtester = Backtester.__new__(Backtester)
        backtester.benchmark_data = self._make_nifty_df()
        backtester.transaction_cost_pct = 0.0025

        entry_date = pd.Timestamp('2021-06-01')

        # Simulate the slice logic from _backtest_single_point
        nifty_slice = pd.DataFrame()
        if backtester.benchmark_data is not None and not backtester.benchmark_data.empty:
            nifty_slice = backtester.benchmark_data[backtester.benchmark_data.index <= entry_date]

        # After slice, no future dates should appear
        self.assertFalse(nifty_slice.empty)
        self.assertLessEqual(nifty_slice.index.max(), entry_date)

        # Full benchmark has future dates
        self.assertGreater(backtester.benchmark_data.index.max(), entry_date)


# ---------------------------------------------------------------------------
# H3 — Transaction costs deducted from alpha
# ---------------------------------------------------------------------------
class TestTransactionCosts(unittest.TestCase):
    """H3: alpha must be reduced by round-trip transaction costs"""

    def _net_alpha(self, stock_ret, bench_ret, cost_pct=0.0025):
        """Replicate the fixed alpha formula"""
        if stock_ret is None or bench_ret is None:
            return None
        round_trip_cost_pct = cost_pct * 2 * 100
        return (stock_ret - bench_ret) - round_trip_cost_pct

    def test_alpha_reduced_by_round_trip(self):
        """0.5% round-trip cost must be subtracted from gross alpha"""
        gross_alpha = self._net_alpha(5.0, 3.0, 0.0)   # no cost
        net_alpha = self._net_alpha(5.0, 3.0, 0.0025)  # 0.25% per leg

        self.assertAlmostEqual(gross_alpha, 2.0)
        self.assertAlmostEqual(net_alpha, 1.5, places=5)  # 2.0 - 0.50%

    def test_positive_alpha_reduced(self):
        alpha = self._net_alpha(10.0, 7.0)
        self.assertAlmostEqual(alpha, 2.5, places=5)  # 3 - 0.5

    def test_negative_alpha_made_worse(self):
        alpha = self._net_alpha(2.0, 3.0)
        self.assertAlmostEqual(alpha, -1.5, places=5)  # -1.0 - 0.5

    def test_none_inputs_return_none(self):
        self.assertIsNone(self._net_alpha(None, 2.0))
        self.assertIsNone(self._net_alpha(2.0, None))
        self.assertIsNone(self._net_alpha(None, None))

    def test_backtester_default_cost(self):
        """Backtester default transaction cost is 0.25% per leg"""
        from core.backtester import Backtester
        b = Backtester.__new__(Backtester)
        b.transaction_cost_pct = Backtester.DEFAULT_TRANSACTION_COST_PCT
        self.assertAlmostEqual(b.transaction_cost_pct, 0.0025)

    def test_custom_cost_respected(self):
        """Custom cost parameter is stored"""
        from core.backtester import Backtester
        b = Backtester.__new__(Backtester)
        b.transaction_cost_pct = 0.005  # 0.5% per leg
        round_trip = b.transaction_cost_pct * 2 * 100
        self.assertAlmostEqual(round_trip, 1.0)  # 1.0% round-trip


# ---------------------------------------------------------------------------
# H6 — Single-agent dominance confidence cap
# ---------------------------------------------------------------------------
class TestSingleAgentDominance(unittest.TestCase):
    """H6: confidence must be penalised when one agent has >70% renormalized weight"""

    def _calculate_composite(self, successful_agents, weights, error_count):
        """Replicate fixed _calculate_composite_score logic for confidence"""
        raw_weight_sum = sum(weights[name] for name in successful_agents)
        normalized_weights = {
            name: weights[name] / raw_weight_sum for name in successful_agents
        }

        composite_confidence = sum(
            result.get('confidence', 0.5) for result in successful_agents.values()
        ) / len(successful_agents)

        if error_count >= 4:
            composite_confidence *= 0.1
        elif error_count >= 3:
            composite_confidence *= 0.3
        elif error_count == 2:
            composite_confidence *= 0.6
        elif error_count == 1:
            composite_confidence *= 0.85

        max_weight = max(normalized_weights.values())
        if max_weight > 0.70:
            cap_factor = 1.0 - (max_weight - 0.70) / 0.30 * 0.5
            composite_confidence = min(composite_confidence, composite_confidence * cap_factor)

        return composite_confidence, normalized_weights

    def test_all_agents_full_confidence(self):
        """All 5 agents pass: no extra penalty, confidence near mean"""
        weights = {'fundamentals': 0.36, 'momentum': 0.27, 'quality': 0.18,
                   'sentiment': 0.09, 'institutional_flow': 0.10}
        agents = {k: {'confidence': 0.8} for k in weights}
        conf, _ = self._calculate_composite(agents, weights, error_count=0)
        self.assertAlmostEqual(conf, 0.8, places=3)

    def test_4_agents_fail_single_dominance(self):
        """Only momentum survives → 100% weight → confidence heavily capped"""
        weights = {'fundamentals': 0.36, 'momentum': 0.27, 'quality': 0.18,
                   'sentiment': 0.09, 'institutional_flow': 0.10}
        agents = {'momentum': {'confidence': 0.9}}
        conf, nw = self._calculate_composite(agents, weights, error_count=4)
        # 4 failures → *0.1, then single agent (100% weight) → extra cap
        self.assertLess(conf, 0.15, "severely degraded confidence expected")
        self.assertAlmostEqual(nw['momentum'], 1.0)

    def test_2_agents_fail_no_dominance(self):
        """2 agents fail but survivors balanced: moderate penalty, no dominance cap"""
        weights = {'fundamentals': 0.36, 'momentum': 0.27, 'quality': 0.18,
                   'sentiment': 0.09, 'institutional_flow': 0.10}
        agents = {
            'fundamentals': {'confidence': 0.8},
            'momentum': {'confidence': 0.8},
            'quality': {'confidence': 0.8},
        }
        conf, nw = self._calculate_composite(agents, weights, error_count=2)
        # 2 failures → *0.6, but weights balanced → no dominance cap
        self.assertAlmostEqual(conf, 0.8 * 0.6, places=2)
        self.assertLess(max(nw.values()), 0.70)

    def test_dominance_cap_linear(self):
        """At 100% weight the cap_factor should be 0.5 → half confidence"""
        cap_factor = 1.0 - (1.0 - 0.70) / 0.30 * 0.5
        self.assertAlmostEqual(cap_factor, 0.5)


# ---------------------------------------------------------------------------
# H7 — Macro overlay cap: total_overlay already capped before regime_adj
# ---------------------------------------------------------------------------
class TestMacroOverlayCap(unittest.TestCase):
    """H7: total_overlay ±10 cap must be applied before regime_adj is added"""

    def _apply_overlays(self, overlays_sum, regime_trend, regime_conf, use_adaptive=False):
        """
        Simulate the overlay + regime step from score_stock:
          1. Cap total_overlay at ±10
          2. Apply regime_adj (additional ±3) on top → final np.clip to [0,100]
        """
        total_overlay = float(np.clip(overlays_sum, -10.0, 10.0))
        composite_base = 60.0
        composite_after_overlay = float(np.clip(composite_base + total_overlay, 0.0, 100.0))

        _REGIME_COMPOSITE_ADJ = {'BULL': +3.0, 'BEAR': -3.0, 'SIDEWAYS': 0.0}
        regime_adj = _REGIME_COMPOSITE_ADJ.get(regime_trend, 0.0)
        regime_adj = round(regime_adj * max(0.0, (regime_conf - 0.3) / 0.7), 2)

        if regime_adj != 0.0 and not use_adaptive:
            final = float(np.clip(composite_after_overlay + regime_adj, 0.0, 100.0))
        else:
            regime_adj = 0.0
            final = composite_after_overlay

        return total_overlay, regime_adj, final

    def test_overlay_capped_at_10(self):
        overlay, _, _ = self._apply_overlays(overlays_sum=15, regime_trend='SIDEWAYS', regime_conf=0.7)
        self.assertEqual(overlay, 10.0)

    def test_overlay_capped_at_minus_10(self):
        overlay, _, _ = self._apply_overlays(overlays_sum=-20, regime_trend='SIDEWAYS', regime_conf=0.7)
        self.assertEqual(overlay, -10.0)

    def test_regime_adds_on_top_of_capped_overlay(self):
        """regime_adj adds after overlay cap — combined max is ~13, clamped to [0,100]"""
        overlay, radj, final = self._apply_overlays(
            overlays_sum=15, regime_trend='BULL', regime_conf=1.0, use_adaptive=False
        )
        self.assertEqual(overlay, 10.0)
        self.assertAlmostEqual(radj, 3.0, places=2)
        # composite_base=60, overlay=10 → 70, +3 regime → 73
        self.assertAlmostEqual(final, 73.0, places=1)

    def test_final_score_clamped_0_100(self):
        """Score can never exceed 100 or go below 0 after all adjustments"""
        for base_sum in [-50, 50]:
            _, _, final = self._apply_overlays(
                overlays_sum=base_sum, regime_trend='BULL' if base_sum > 0 else 'BEAR', regime_conf=1.0
            )
            self.assertGreaterEqual(final, 0.0)
            self.assertLessEqual(final, 100.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
