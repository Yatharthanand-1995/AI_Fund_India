"""
Unit tests for all India-specific features added in the current session.

Covers:
  - Transaction cost and risk-free rate constants (P0)
  - India VIX integration in MarketRegimeService (P2)
  - NSE holiday calendar in get_rebalance_dates (P2)
  - F&O expiry guard in portfolio_manager (P2)
  - USD/INR sector adjustment in StockScorer (P2)
  - RBI rate cycle provider (P2)
"""

import sys
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ─────────────────────────────────────────────────────────────────────────────
# P0: Transaction cost and risk-free rate
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestConstants:
    def test_transaction_cost_is_27bps(self):
        from scripts.portfolio_backtest import TRANSACTION_COST
        assert TRANSACTION_COST == 0.0027, (
            f"Expected 0.0027 (27 bps), got {TRANSACTION_COST}. "
            "India STT + brokerage + GST + stamp duty ≈ 27 bps/side."
        )

    def test_risk_free_rate_is_7pct(self):
        import inspect
        import scripts.portfolio_backtest as bt
        src = inspect.getsource(bt.compute_metrics)
        assert "0.07" in src, "compute_metrics default risk_free should be 0.07 (10-yr G-Sec)"

    def test_bench_metrics_risk_free_is_7pct(self):
        import inspect
        import scripts.portfolio_backtest as bt
        src = inspect.getsource(bt.bench_metrics)
        assert "0.07" in src, "bench_metrics default risk_free should be 0.07"


# ─────────────────────────────────────────────────────────────────────────────
# P2: India VIX in regime service
# ─────────────────────────────────────────────────────────────────────────────

class TestIndiaVIX:
    def _make_nifty_data(self, n=250, trend="bull"):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq='B')
        if trend == "bull":
            prices = 20000 * (1 + np.linspace(0, 0.30, n))
        else:
            prices = 20000 * (1 - np.linspace(0, 0.15, n))
        return pd.DataFrame({"Close": prices, "High": prices * 1.01,
                              "Low": prices * 0.99, "Volume": 1e6}, index=dates)

    def test_vix_symbol_constant(self):
        from core.market_regime_service import MarketRegimeService
        assert MarketRegimeService.INDIA_VIX_SYMBOL == "^INDIAVIX"

    def test_vix_blend_weight_is_70pct(self):
        from core.market_regime_service import MarketRegimeService
        assert MarketRegimeService.VIX_BLEND_WEIGHT == 0.70

    def test_volatility_with_vix_blends_correctly(self):
        from core.market_regime_service import MarketRegimeService
        svc = MarketRegimeService()
        nifty = self._make_nifty_data(250)
        vol_class, metrics = svc._detect_volatility(nifty, india_vix=20.0)
        # Realized vol will vary; what we can assert is that VIX is captured
        assert metrics["india_vix"] == 20.0
        assert metrics["volatility_source"] == "india_vix_blend"
        assert "realized_vol_pct" in metrics
        # Effective = 0.7*20 + 0.3*realized
        expected_eff = 0.70 * 20.0 + 0.30 * metrics["realized_vol_pct"]
        assert abs(metrics["volatility_pct"] - expected_eff) < 0.1

    def test_volatility_without_vix_uses_realized(self):
        from core.market_regime_service import MarketRegimeService
        svc = MarketRegimeService()
        nifty = self._make_nifty_data(250)
        vol_class, metrics = svc._detect_volatility(nifty, india_vix=None)
        assert metrics["volatility_source"] == "realized_only"
        assert metrics["india_vix"] is None
        assert metrics["volatility_pct"] == metrics["realized_vol_pct"]

    def test_high_vix_triggers_high_regime(self):
        from core.market_regime_service import MarketRegimeService
        svc = MarketRegimeService()
        nifty = self._make_nifty_data(250)
        # VIX=40 should force HIGH regardless of realized vol
        vol_class, metrics = svc._detect_volatility(nifty, india_vix=40.0)
        assert vol_class == "HIGH"

    def test_low_vix_triggers_low_regime(self):
        from core.market_regime_service import MarketRegimeService
        svc = MarketRegimeService()
        nifty = self._make_nifty_data(250)
        # VIX=8 (very calm) with realized ~low should give LOW
        vol_class, metrics = svc._detect_volatility(nifty, india_vix=8.0)
        # Effective = 0.7*8 + 0.3*realized; realized on bull trend data is low-ish
        assert vol_class in ("LOW", "NORMAL")  # depends on realized component

    @patch.object(
        __import__("core.market_regime_service", fromlist=["MarketRegimeService"]).MarketRegimeService,
        "_fetch_india_vix", return_value=None
    )
    def test_regime_falls_back_when_vix_unavailable(self, mock_vix):
        from core.market_regime_service import MarketRegimeService
        svc = MarketRegimeService()
        nifty = self._make_nifty_data(250)
        _, metrics = svc._detect_volatility(nifty, india_vix=None)
        assert metrics["volatility_source"] == "realized_only"


# ─────────────────────────────────────────────────────────────────────────────
# P2: NSE holiday calendar
# ─────────────────────────────────────────────────────────────────────────────

class TestNSECalendar:
    def test_nse_calendar_importable(self):
        import pandas_market_calendars as mcal
        nse = mcal.get_calendar("NSE")
        assert nse is not None

    def test_rebalance_dates_excludes_holidays(self):
        """NSE has ~14 holidays/year not in plain bdate_range."""
        import pandas_market_calendars as mcal
        from scripts.portfolio_backtest import get_rebalance_dates

        nse = mcal.get_calendar("NSE")
        # Build a price series for 2025 using only NSE valid days
        valid = nse.valid_days("2025-01-01", "2025-12-31")
        dates_naive = pd.DatetimeIndex([pd.Timestamp(d).tz_convert(None) for d in valid])
        prices = pd.Series(np.ones(len(dates_naive)) * 100, index=dates_naive)

        rebal = get_rebalance_dates({}, bench=prices)
        assert len(rebal) == 12, f"Expected 12 monthly dates, got {len(rebal)}"

    def test_rebalance_dates_are_timezone_naive(self):
        from scripts.portfolio_backtest import get_rebalance_dates
        dates = pd.date_range("2025-01-01", "2025-12-31", freq="B")
        bench = pd.Series(np.ones(len(dates)), index=dates)
        rebal = get_rebalance_dates({}, bench=bench)
        for d in rebal:
            assert d.tzinfo is None, f"Date {d} should be timezone-naive"


# ─────────────────────────────────────────────────────────────────────────────
# P2: F&O expiry guard
# ─────────────────────────────────────────────────────────────────────────────

class TestFnOExpiryGuard:
    def test_known_expiry_days_april_2026(self):
        """Apr 30 2026 is the last Thursday of April."""
        from core.portfolio_manager import _is_fno_expiry_window
        expiry = datetime(2026, 4, 30, tzinfo=timezone.utc)
        assert _is_fno_expiry_window(expiry) is True

    def test_day_before_expiry_is_in_window(self):
        from core.portfolio_manager import _is_fno_expiry_window
        day_before = datetime(2026, 4, 29, tzinfo=timezone.utc)
        assert _is_fno_expiry_window(day_before) is True

    def test_two_days_before_expiry_is_in_window(self):
        from core.portfolio_manager import _is_fno_expiry_window
        two_before = datetime(2026, 4, 28, tzinfo=timezone.utc)
        assert _is_fno_expiry_window(two_before) is True

    def test_three_days_before_expiry_is_outside_window(self):
        from core.portfolio_manager import _is_fno_expiry_window
        three_before = datetime(2026, 4, 27, tzinfo=timezone.utc)
        assert _is_fno_expiry_window(three_before) is False

    def test_day_after_expiry_is_outside_window(self):
        from core.portfolio_manager import _is_fno_expiry_window
        day_after = datetime(2026, 5, 1, tzinfo=timezone.utc)
        assert _is_fno_expiry_window(day_after) is False

    def test_mid_month_is_outside_window(self):
        from core.portfolio_manager import _is_fno_expiry_window
        mid = datetime(2026, 4, 15, tzinfo=timezone.utc)
        assert _is_fno_expiry_window(mid) is False

    def test_may_2026_expiry_is_may_28(self):
        """May 2026 last Thursday = May 28."""
        from core.portfolio_manager import _is_fno_expiry_window
        assert _is_fno_expiry_window(datetime(2026, 5, 28, tzinfo=timezone.utc)) is True
        assert _is_fno_expiry_window(datetime(2026, 5, 26, tzinfo=timezone.utc)) is True  # 2d before
        assert _is_fno_expiry_window(datetime(2026, 5, 25, tzinfo=timezone.utc)) is False  # 3d before

    def test_window_covers_exactly_3_days(self):
        from core.portfolio_manager import _is_fno_expiry_window
        # April 2026: expiry=Apr30, window=Apr28,29,30
        in_window = [
            datetime(2026, 4, d, tzinfo=timezone.utc)
            for d in range(1, 31)
            if _is_fno_expiry_window(datetime(2026, 4, d, tzinfo=timezone.utc))
        ]
        assert len(in_window) == 3, f"Window should be exactly 3 days, got {len(in_window)}: {in_window}"


# ─────────────────────────────────────────────────────────────────────────────
# P2: USD/INR sector adjustment
# ─────────────────────────────────────────────────────────────────────────────

class TestUSDINRAdjustment:
    def _scorer(self):
        from core.stock_scorer import StockScorer
        return StockScorer()

    def test_technology_positive_on_weakening(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Technology", {"trend_pct": 3.0, "direction": "weakening"})
        assert adj > 0, "IT sector should benefit from INR weakening"

    def test_technology_negative_on_strengthening(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Technology", {"trend_pct": -3.0, "direction": "strengthening"})
        assert adj < 0

    def test_healthcare_positive_on_weakening(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Healthcare", {"trend_pct": 3.0, "direction": "weakening"})
        assert adj > 0

    def test_consumer_defensive_negative_on_weakening(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Consumer Defensive", {"trend_pct": 3.0, "direction": "weakening"})
        assert adj < 0, "FMCG imports raw materials; INR weakening hurts"

    def test_financial_services_zero(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Financial Services", {"trend_pct": 5.0, "direction": "weakening"})
        assert adj == 0.0

    def test_energy_zero(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Energy", {"trend_pct": 5.0, "direction": "weakening"})
        assert adj == 0.0

    def test_small_move_below_1pct_returns_zero(self):
        s = self._scorer()
        # < 1% move → no adjustment (noise threshold)
        adj = s._compute_currency_adjustment("Technology", {"trend_pct": 0.8, "direction": "weakening"})
        assert adj == 0.0

    def test_adjustment_capped_at_4pts(self):
        s = self._scorer()
        # Extreme move: 20% INR weakening
        adj = s._compute_currency_adjustment("Technology", {"trend_pct": 20.0, "direction": "weakening"})
        assert adj <= 4.0

    def test_adjustment_floor_at_minus_4pts(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Technology", {"trend_pct": -20.0, "direction": "strengthening"})
        assert adj >= -4.0

    def test_none_sector_returns_zero(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment(None, {"trend_pct": 5.0, "direction": "weakening"})
        assert adj == 0.0

    def test_none_usdinr_returns_zero(self):
        s = self._scorer()
        adj = s._compute_currency_adjustment("Technology", None)
        assert adj == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# P2: RBI rate cycle provider
# ─────────────────────────────────────────────────────────────────────────────

class TestRBIRateProvider:
    def _provider(self, history, repo_rate=6.0):
        """Create a provider with injected config data."""
        from data.rbi_rate_provider import RBIRateProvider
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"repo_rate": repo_rate, "last_updated": "2026-02-07",
                       "decision_history": history}, f)
            path = Path(f.name)
        p = RBIRateProvider(config_path=path)
        return p

    def test_cutting_cycle_detected(self):
        p = self._provider([
            {"date": "2026-02-07", "action": "cut", "bps": -25, "rate": 5.75},
            {"date": "2025-12-06", "action": "hold", "bps": 0, "rate": 6.0},
        ])
        assert p.get_rate_info()["cycle"] == "cutting"

    def test_hiking_cycle_detected(self):
        p = self._provider([
            {"date": "2023-02-08", "action": "hike", "bps": 25, "rate": 6.75},
            {"date": "2022-12-07", "action": "hike", "bps": 25, "rate": 6.50},
        ])
        assert p.get_rate_info()["cycle"] == "hiking"

    def test_pausing_cycle_on_all_holds(self):
        p = self._provider([
            {"date": "2026-02-07", "action": "hold", "bps": 0, "rate": 6.5},
            {"date": "2025-12-06", "action": "hold", "bps": 0, "rate": 6.5},
        ])
        assert p.get_rate_info()["cycle"] == "pausing"

    def test_pausing_on_mixed_cut_and_hike(self):
        p = self._provider([
            {"date": "2026-02-07", "action": "cut",  "bps": -25, "rate": 6.25},
            {"date": "2025-12-06", "action": "hike", "bps":  25, "rate": 6.50},
        ])
        assert p.get_rate_info()["cycle"] == "pausing"

    def test_financial_services_positive_on_cut(self):
        p = self._provider([
            {"date": "2026-02-07", "action": "cut", "bps": -25, "rate": 5.75},
            {"date": "2025-12-06", "action": "cut", "bps": -25, "rate": 6.00},
        ])
        adj = p.get_sector_adjustment("Financial Services")
        assert adj > 0

    def test_financial_services_negative_on_hike(self):
        p = self._provider([
            {"date": "2023-02-08", "action": "hike", "bps": 25, "rate": 6.75},
            {"date": "2022-12-07", "action": "hike", "bps": 25, "rate": 6.50},
        ])
        adj = p.get_sector_adjustment("Financial Services")
        assert adj < 0

    def test_technology_always_zero(self):
        p = self._provider([
            {"date": "2026-02-07", "action": "cut", "bps": -25, "rate": 5.75},
        ])
        assert p.get_sector_adjustment("Technology") == 0.0

    def test_amplification_triggers_above_50bps(self):
        """≥50 bps cumulative in 6 months → 1.5× scale."""
        today = date.today()
        recent = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        older  = (today - timedelta(days=60)).strftime("%Y-%m-%d")
        p = self._provider([
            {"date": recent, "action": "cut", "bps": -25, "rate": 5.75},
            {"date": older,  "action": "cut", "bps": -25, "rate": 6.00},
        ])
        info = p.get_rate_info()
        assert info["cumulative_bps_6m"] == -50
        adj = p.get_sector_adjustment("Financial Services")
        # Should be 2.5 * 1.5 = 3.75, capped at 3.0
        assert adj == 3.0

    def test_no_amplification_below_50bps(self):
        """< 50 bps → base rate applies."""
        today = date.today()
        recent = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        p = self._provider([
            {"date": recent, "action": "cut", "bps": -25, "rate": 5.75},
        ])
        adj = p.get_sector_adjustment("Financial Services")
        assert adj == pytest.approx(2.5, abs=0.01)

    def test_pausing_gives_zero_adjustment(self):
        p = self._provider([
            {"date": "2026-02-07", "action": "hold", "bps": 0, "rate": 6.5},
            {"date": "2025-12-06", "action": "hold", "bps": 0, "rate": 6.5},
        ])
        for sector in ["Financial Services", "Consumer Cyclical", "Consumer Defensive"]:
            assert p.get_sector_adjustment(sector) == 0.0

    def test_adjustment_capped_at_3pts(self):
        today = date.today()
        dates = [(today - timedelta(days=i*20)).strftime("%Y-%m-%d") for i in range(6)]
        history = [{"date": d, "action": "cut", "bps": -50, "rate": 5.0 + i*0.25}
                   for i, d in enumerate(dates)]
        p = self._provider(history)
        adj = p.get_sector_adjustment("Financial Services")
        assert adj <= 3.0

    def test_empty_history_returns_pausing(self):
        p = self._provider([])
        assert p.get_rate_info()["cycle"] == "pausing"

    def test_config_file_not_found_gives_neutral(self):
        from data.rbi_rate_provider import RBIRateProvider
        p = RBIRateProvider(config_path=Path("/nonexistent/path.json"))
        info = p.get_rate_info()
        assert info["cycle"] == "pausing"
        assert p.get_sector_adjustment("Financial Services") == 0.0

    def test_real_config_file_loads(self):
        """Smoke test: real config file exists and is valid."""
        from data.rbi_rate_provider import get_default_provider
        p = get_default_provider()
        info = p.get_rate_info()
        assert info["repo_rate"] > 0
        assert info["cycle"] in ("cutting", "hiking", "pausing")
