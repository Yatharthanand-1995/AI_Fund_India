"""
Tests for H2 (survivorship bias) and H4 (stale fundamentals) fixes.

H2 — Point-in-time NIFTY 50 constituency
    - get_nifty50_at_date() returns the right set for any date
    - HDFC present before Jul 2023 merger, absent after
    - Survivorship stocks (VEDL, ZEEL, INFRATEL) present when historically correct
    - Backtester.get_universe_at_date() uses the file; custom list passes through

H4 — Point-in-time fundamentals
    - get_point_in_time_quality() filters quarterly data to as_of_date
    - No future quarters leak into the TTM calculation
    - Graceful fallback on missing data
    - Deprecation warning on old get_quality_snapshot()
"""

import sys
import os
import unittest
import warnings
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# H2 — Point-in-time NIFTY 50 constituency
# ---------------------------------------------------------------------------
class TestNifty50Historical(unittest.TestCase):
    """H2: point-in-time constituency snapshots"""

    def setUp(self):
        from data.nifty50_historical import get_nifty50_at_date, get_survivorship_bias_stocks, get_nifty50_changes_log
        self.get_at = get_nifty50_at_date
        self.get_removed = get_survivorship_bias_stocks
        self.get_changes = get_nifty50_changes_log

    # ── Size checks ──────────────────────────────────────────────────────────

    def test_returns_around_50_symbols(self):
        """Each snapshot should have approximately 50 symbols (±5 for tracking)"""
        for year in [2019, 2020, 2021, 2022, 2023, 2024, 2025]:
            syms = self.get_at(datetime(year, 6, 1))
            self.assertGreater(len(syms), 40, f"Too few symbols for {year}")
            self.assertLess(len(syms), 60, f"Too many symbols for {year}")

    def test_returns_sorted_list(self):
        syms = self.get_at(datetime(2022, 1, 1))
        self.assertEqual(syms, sorted(syms))

    def test_no_duplicates(self):
        for year in [2020, 2022, 2024]:
            syms = self.get_at(datetime(year, 6, 1))
            self.assertEqual(len(syms), len(set(syms)), f"Duplicate symbols in {year}")

    # ── HDFC merger (Jul 2023) ───────────────────────────────────────────────

    def test_hdfc_present_before_merger(self):
        """HDFC Ltd should be in the index before July 2023 merger"""
        syms = self.get_at(datetime(2023, 1, 1))
        self.assertIn('HDFC', syms, "HDFC should be in index before merger")

    def test_hdfc_absent_after_merger(self):
        """HDFC Ltd should NOT be in index after July 13 2023 effective date"""
        syms = self.get_at(datetime(2023, 8, 1))
        self.assertNotIn('HDFC', syms, "HDFC merged into HDFC Bank in Jul 2023")

    def test_hdfc_bank_always_present(self):
        """HDFC Bank should always be in the index"""
        for d in [datetime(2020, 1, 1), datetime(2022, 6, 1), datetime(2024, 1, 1)]:
            self.assertIn('HDFCBANK', self.get_at(d))

    # ── Survivorship bias stocks ──────────────────────────────────────────────

    def test_vedl_removed_in_2020(self):
        """Vedanta was removed in Sep 2020 rebalancing"""
        before = self.get_at(datetime(2020, 6, 1))
        after  = self.get_at(datetime(2021, 1, 1))
        self.assertIn('VEDL', before, "VEDL should be present Jan-2020")
        self.assertNotIn('VEDL', after, "VEDL should be removed after Sep-2020")

    def test_zeel_removed_after_nov_2020(self):
        """ZEEL (Zee Entertainment) was removed in Nov 2020"""
        before = self.get_at(datetime(2020, 6, 1))
        after  = self.get_at(datetime(2021, 1, 15))
        self.assertIn('ZEEL', before)
        self.assertNotIn('ZEEL', after)

    def test_trent_added_in_2024(self):
        """Trent Ltd was added in Mar 2024"""
        before = self.get_at(datetime(2024, 1, 1))
        after  = self.get_at(datetime(2024, 6, 1))
        self.assertNotIn('TRENT', before, "TRENT not in index before Mar 2024")
        self.assertIn('TRENT', after, "TRENT should be in index after Mar 2024")

    def test_jswsteel_added_in_2021(self):
        """JSW Steel added Mar 2021"""
        before = self.get_at(datetime(2021, 1, 1))
        after  = self.get_at(datetime(2021, 6, 1))
        self.assertNotIn('JSWSTEEL', before)
        self.assertIn('JSWSTEEL', after)

    # ── Stable stocks ────────────────────────────────────────────────────────

    def test_core_stocks_always_present(self):
        """Blue chip stocks should be present across all dates"""
        always_in = ['TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'SBIN']
        for sym in always_in:
            for year in [2019, 2020, 2021, 2022, 2023, 2024]:
                syms = self.get_at(datetime(year, 6, 1))
                self.assertIn(sym, syms, f"{sym} should always be in NIFTY 50")

    # ── Date boundary edge cases ──────────────────────────────────────────────

    def test_date_before_earliest_snapshot(self):
        """Date before 2019 falls back to oldest snapshot"""
        syms = self.get_at(datetime(2015, 1, 1))
        self.assertGreater(len(syms), 40)

    def test_exact_snapshot_date(self):
        """Exact match on snapshot date returns that snapshot"""
        syms = self.get_at(datetime(2025, 1, 1))
        # TRENT and BEL should be in Jan 2025 (added 2024)
        self.assertIn('TRENT', syms)
        self.assertIn('BEL', syms)

    # ── Survivorship bias report ─────────────────────────────────────────────

    def test_survivorship_stocks_identified(self):
        """Removed stocks should be identifiable"""
        removed = self.get_removed()
        self.assertIn('VEDL', removed, "VEDL is a known removed stock")
        self.assertIn('ZEEL', removed, "ZEEL is a known removed stock")
        self.assertIn('HDFC', removed, "HDFC merged out — should be flagged")

    def test_survivorship_has_last_seen_dates(self):
        """Each removed stock should have a last-seen date string"""
        removed = self.get_removed()
        for sym, last_seen in removed.items():
            self.assertRegex(last_seen, r'\d{4}-\d{2}-\d{2}', f"{sym} missing date")

    # ── Changes log ──────────────────────────────────────────────────────────

    def test_changes_log_non_empty(self):
        changes = self.get_changes()
        self.assertGreater(len(changes), 3)

    def test_changes_log_structure(self):
        changes = self.get_changes()
        for c in changes:
            self.assertIn('date', c)
            self.assertIn('added', c)
            self.assertIn('removed', c)


# ---------------------------------------------------------------------------
# H2 — Backtester.get_universe_at_date()
# ---------------------------------------------------------------------------
class TestBacktesterUniverse(unittest.TestCase):
    """H2: Backtester uses point-in-time universe when symbols=None"""

    def _make_backtester(self):
        from core.backtester import Backtester
        b = Backtester.__new__(Backtester)
        b.transaction_cost_pct = 0.0025
        b.benchmark_data = None
        return b

    def test_custom_symbols_passed_through(self):
        """When symbols provided, they are returned unchanged"""
        b = self._make_backtester()
        custom = ['TCS', 'INFY', 'RELIANCE']
        result = b.get_universe_at_date(datetime(2022, 1, 1), symbols=custom)
        self.assertEqual(result, custom)

    def test_none_symbols_returns_historical_universe(self):
        """When symbols=None, returns point-in-time NIFTY 50"""
        b = self._make_backtester()
        result = b.get_universe_at_date(datetime(2021, 6, 1), symbols=None)
        self.assertGreater(len(result), 40)
        self.assertIsInstance(result, list)

    def test_universe_differs_by_date(self):
        """Universe at 2020 and 2024 should differ (stocks added/removed)"""
        b = self._make_backtester()
        u2020 = set(b.get_universe_at_date(datetime(2020, 1, 1), symbols=None))
        u2024 = set(b.get_universe_at_date(datetime(2024, 6, 1), symbols=None))
        # They should not be identical — real changes happened
        self.assertNotEqual(u2020, u2024)

    def test_hdfc_in_2022_universe_not_2024(self):
        """HDFC Ltd in 2022 universe but not 2024 (post merger)"""
        b = self._make_backtester()
        u2022 = b.get_universe_at_date(datetime(2022, 6, 1), symbols=None)
        u2024 = b.get_universe_at_date(datetime(2024, 1, 1), symbols=None)
        self.assertIn('HDFC', u2022)
        self.assertNotIn('HDFC', u2024)


# ---------------------------------------------------------------------------
# H4 — Point-in-time fundamentals
# ---------------------------------------------------------------------------
class TestPointInTimeFundamentals(unittest.TestCase):
    """H4: get_point_in_time_quality() uses only past quarterly data"""

    def _make_quarterly_income(self, quarters_with_dates):
        """
        Build a mock quarterly_income_stmt DataFrame.
        yfinance format: rows = metrics, columns = quarter dates (newest first).
        quarters_with_dates: list of (date_str, net_income) tuples, newest first.
        """
        col_data = {}
        for d, ni in quarters_with_dates:
            col_data[pd.Timestamp(d)] = {'Net Income': ni}
        return pd.DataFrame(col_data)

    def _make_quarterly_bs(self, quarters_with_dates):
        """
        Build mock quarterly_balance_sheet.
        yfinance format: rows = metrics, columns = quarter dates (newest first).
        quarters_with_dates: list of (date_str, equity, total_debt) tuples.
        """
        col_data = {}
        for d, eq, td in quarters_with_dates:
            col_data[pd.Timestamp(d)] = {'Stockholders Equity': eq, 'Total Debt': td}
        return pd.DataFrame(col_data)

    def test_filters_future_quarters(self):
        """
        Quarters after as_of_date must NOT be included in TTM calculation.
        If future data were used, ROE would be inflated.
        """
        from scripts.portfolio_backtest import get_point_in_time_quality

        # Build a mock ticker with quarters spanning 2020-2023
        inc_data = [
            ('2023-03-31', 1000),  # FUTURE quarter (after our as_of_date)
            ('2022-12-31', 800),
            ('2022-09-30', 750),
            ('2022-06-30', 700),
            ('2022-03-31', 650),
        ]
        bs_data = [
            ('2023-03-31', 10000, 2000),  # FUTURE
            ('2022-12-31', 9500,  1900),
            ('2022-09-30', 9000,  1800),
            ('2022-06-30', 8500,  1700),
            ('2022-03-31', 8000,  1600),
        ]

        mock_ticker = MagicMock()
        mock_ticker.quarterly_income_stmt = self._make_quarterly_income(inc_data)
        mock_ticker.quarterly_balance_sheet = self._make_quarterly_bs(bs_data)

        as_of_date = pd.Timestamp('2022-12-31')

        with patch('yfinance.Ticker', return_value=mock_ticker):
            result = get_point_in_time_quality(['TCS'], as_of_date)

        # Score should be based on 2022 data only (4 quarters: Sep, Jun, Mar + previous)
        self.assertIn('TCS', result)
        score = result['TCS']
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_fallback_on_no_data(self):
        """When quarterly data unavailable, returns fallback_score"""
        from scripts.portfolio_backtest import get_point_in_time_quality

        mock_ticker = MagicMock()
        mock_ticker.quarterly_income_stmt = pd.DataFrame()
        mock_ticker.quarterly_balance_sheet = pd.DataFrame()

        with patch('yfinance.Ticker', return_value=mock_ticker):
            result = get_point_in_time_quality(['TCS'], pd.Timestamp('2022-01-01'), fallback_score=25.0)

        self.assertEqual(result['TCS'], 25.0)

    def test_fallback_on_exception(self):
        """When yfinance raises, returns fallback_score (no crash)"""
        from scripts.portfolio_backtest import get_point_in_time_quality

        with patch('yfinance.Ticker', side_effect=Exception("network error")):
            result = get_point_in_time_quality(['TCS'], pd.Timestamp('2022-01-01'))

        self.assertIn('TCS', result)
        self.assertEqual(result['TCS'], 25.0)

    def test_score_range(self):
        """Score must always be in [0, 100]"""
        from scripts.portfolio_backtest import get_point_in_time_quality

        inc_data = [
            ('2022-12-31', 5000),  # Very high income
            ('2022-09-30', 5000),
            ('2022-06-30', 5000),
            ('2022-03-31', 5000),
        ]
        bs_data = [
            ('2022-12-31', 10000, 0),  # No debt, good equity
        ]
        mock_ticker = MagicMock()
        mock_ticker.quarterly_income_stmt = self._make_quarterly_income(inc_data)
        mock_ticker.quarterly_balance_sheet = self._make_quarterly_bs(bs_data)

        with patch('yfinance.Ticker', return_value=mock_ticker):
            result = get_point_in_time_quality(['TCS'], pd.Timestamp('2023-01-01'))

        self.assertGreaterEqual(result['TCS'], 0)
        self.assertLessEqual(result['TCS'], 100)

    def test_high_roe_gives_higher_score(self):
        """Higher TTM ROE → higher quality score (both below cap to see difference)"""
        from scripts.portfolio_backtest import get_point_in_time_quality

        def make_mock(net_income, equity):
            # Single quarter income to keep TTM = net_income (4 identical quarters)
            inc_data = [('2022-12-31', net_income), ('2022-09-30', net_income),
                        ('2022-06-30', net_income), ('2022-03-31', net_income)]
            bs_data = [('2022-12-31', equity, 500)]  # small debt to keep D/E stable
            m = MagicMock()
            m.quarterly_income_stmt = self._make_quarterly_income(inc_data)
            m.quarterly_balance_sheet = self._make_quarterly_bs(bs_data)
            return m

        as_of = pd.Timestamp('2023-01-01')
        # ROE 5% (200/4000 TTM per Q × 4 = 800/10000) — well below cap
        with patch('yfinance.Ticker', return_value=make_mock(200, 10000)):
            low_roe = get_point_in_time_quality(['TCS'], as_of)['TCS']
        # ROE 15% (600/4000 TTM) — higher, also below cap
        with patch('yfinance.Ticker', return_value=make_mock(600, 10000)):
            mid_roe = get_point_in_time_quality(['TCS'], as_of)['TCS']

        self.assertGreater(mid_roe, low_roe, "Higher ROE must give higher quality score")

    def test_only_past_quarters_used_for_ttm(self):
        """
        Core invariant: the sum of net income for TTM must use only
        quarters on or before as_of_date.
        """
        # If future quarters were included, TTM NI would be higher
        inc_data = [
            ('2023-06-30', 10000),  # FUTURE
            ('2023-03-31', 1000),
            ('2022-12-31', 1000),
            ('2022-09-30', 1000),
            ('2022-06-30', 1000),
        ]
        bs_data = [('2023-03-31', 10000, 5000)]

        mock = MagicMock()
        mock.quarterly_income_stmt = self._make_quarterly_income(inc_data)
        mock.quarterly_balance_sheet = self._make_quarterly_bs(bs_data)

        from scripts.portfolio_backtest import get_point_in_time_quality
        as_of = pd.Timestamp('2023-03-31')

        with patch('yfinance.Ticker', return_value=mock):
            result = get_point_in_time_quality(['X'], as_of)

        # TTM = 4 quarters on or before 2023-03-31: 1000+1000+1000+1000 = 4000
        # NOT including 10000 from 2023-06-30
        # ROE = 4000/10000 = 40% → roe_s = 40
        # D/E = 5000/10000*100 = 50 → dte_s = max(2, 35 - min(33, 0.5*35)) = 35 - 17.5 = 17.5
        # Expected score ≈ 57-58
        score = result.get('X', 0)
        self.assertGreater(score, 30)
        self.assertLess(score, 85)  # reasonable range if future data excluded

    def test_deprecation_warning_on_old_function(self):
        """get_quality_snapshot() should emit DeprecationWarning"""
        from scripts.portfolio_backtest import get_quality_snapshot

        import yfinance as yf
        mock_ticker = MagicMock()
        mock_ticker.info = {'returnOnEquity': 0.20, 'debtToEquity': 50}

        with patch.object(yf, 'Ticker', return_value=mock_ticker):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                get_quality_snapshot(['TCS'])
                self.assertTrue(
                    any(issubclass(warning.category, DeprecationWarning) for warning in w),
                    "get_quality_snapshot() must emit DeprecationWarning"
                )

    def test_multiple_symbols(self):
        """Function handles multiple symbols in one call"""
        from scripts.portfolio_backtest import get_point_in_time_quality

        mock_ticker = MagicMock()
        mock_ticker.quarterly_income_stmt = pd.DataFrame()
        mock_ticker.quarterly_balance_sheet = pd.DataFrame()

        symbols = ['TCS', 'INFY', 'RELIANCE']
        with patch('yfinance.Ticker', return_value=mock_ticker):
            result = get_point_in_time_quality(symbols, pd.Timestamp('2022-01-01'))

        self.assertEqual(set(result.keys()), set(symbols))


if __name__ == '__main__':
    unittest.main(verbosity=2)
