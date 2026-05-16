"""
Market Breadth Provider

Computes the percentage of NIFTY50 stocks trading above their 200-day SMA.

This is a third regime confirmation signal used alongside:
  1. NIFTY price vs SMA (index-level)
  2. India VIX / realized vol
  3. FII net flows
  4. NIFTY Put/Call Ratio

Breadth adds what the index level misses: a few large-cap heavyweights (Reliance,
HDFC Bank) can keep NIFTY near all-time highs even when most stocks are declining.
Breadth cuts through that illusion.

Interpretation:
  >70% above 200-SMA  → broad bull, high conviction
  50–70%              → mixed, transitioning
  30–50%              → broad weakness despite index
  <30%                → broad bear, strong confirmation

Cached for 4 hours (intraday changes are noise; daily close is what matters).
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# NIFTY50 constituents — updated semi-annually; kept in sync with data/nifty_constituents.py
_NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK",
    "INFY", "SBIN", "HINDUNILVR", "ITC", "LT",
    "KOTAKBANK", "BAJFINANCE", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "HCLTECH",
    "NESTLEIND", "POWERGRID", "NTPC", "TECHM", "BAJAJFINSV",
    "ONGC", "JSWSTEEL", "TATAMOTORS", "HINDALCO", "COALINDIA",
    "ADANIPORTS", "DIVISLAB", "DRREDDY", "CIPLA", "BPCL",
    "EICHERMOT", "GRASIM", "HEROMOTOCO", "INDUSINDBK", "M&M",
    "TATASTEEL", "BRITANNIA", "APOLLOHOSP", "BAJAJ-AUTO", "TATACONSUM",
    "SBILIFE", "HDFCLIFE", "ADANIENT", "LTF", "LTIM",
]

_CACHE_TTL = 4 * 3600   # 4 hours — breadth is a daily metric


class MarketBreadthProvider:
    """
    Computes NIFTY50 market breadth: % of constituents above 200-day SMA.
    Uses yfinance for price data. Runs in ~10 seconds with a single batch call.
    """

    def __init__(self, symbols: Optional[List[str]] = None, timeout: int = 30):
        self._symbols = symbols or _NIFTY50_SYMBOLS
        self._timeout = timeout
        self._cache: Optional[Dict] = None
        self._cache_ts: float = 0.0

    def get_breadth(self) -> Dict:
        """
        Compute NIFTY50 breadth.

        Returns:
          {
            'breadth_pct': float,       # % stocks above 200-SMA (0–100)
            'above_200sma': int,        # count above
            'below_200sma': int,        # count below
            'total_checked': int,
            'signal': str,              # 'broad_bull' | 'mixed' | 'broad_weak' | 'broad_bear'
            'regime_modifier': float,   # confidence modifier for regime blending
            'source': str,
          }
        """
        now = time.monotonic()
        if self._cache and (now - self._cache_ts) < _CACHE_TTL:
            return {**self._cache, 'source': 'cache'}

        try:
            above, below, total = self._compute_breadth()
            if total == 0:
                return self._neutral_defaults()

            breadth_pct = round(above / total * 100, 1)
            signal, modifier = self._classify_breadth(breadth_pct)

            result = {
                'breadth_pct': breadth_pct,
                'above_200sma': above,
                'below_200sma': below,
                'total_checked': total,
                'signal': signal,
                'regime_modifier': modifier,
                'source': 'yfinance',
            }
            self._cache = result
            self._cache_ts = now
            logger.info(
                f"Market breadth: {breadth_pct:.0f}% above 200-SMA "
                f"({above}/{total} stocks, {signal})"
            )
            return result

        except Exception as e:
            logger.warning(f"Market breadth computation failed: {e}")
            return self._neutral_defaults()

    def _compute_breadth(self) -> Tuple[int, int, int]:
        """Fetch 250 days of price for all NIFTY50 stocks and count above/below 200-SMA."""
        import yfinance as yf

        # Batch download — single HTTP call for all symbols
        tickers = [f"{s}.NS" for s in self._symbols]
        data = yf.download(
            tickers,
            period="260d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        # yfinance returns MultiIndex columns: (field, ticker) when multiple tickers
        if isinstance(data.columns, pd.MultiIndex):
            closes = data['Close']
        else:
            closes = data[['Close']]

        above = below = 0
        for col in closes.columns:
            series = closes[col].dropna()
            if len(series) < 200:
                continue
            sma200 = series.rolling(200).mean().iloc[-1]
            current = series.iloc[-1]
            if current > sma200:
                above += 1
            else:
                below += 1

        return above, below, above + below

    @staticmethod
    def _classify_breadth(breadth_pct: float) -> Tuple[str, float]:
        """
        Returns (signal, regime_confidence_modifier).

        High breadth in a BULL regime → confirms trend, boost confidence.
        Low breadth even when index is at highs → warns of narrow market, reduce confidence.

        Note: the modifier is applied ONLY when it reinforces or contradicts the
        SMA-based trend. The MarketRegimeService handles direction-awareness.
        """
        if breadth_pct >= 70:
            return 'broad_bull', +0.12
        elif breadth_pct >= 50:
            return 'mixed', +0.03
        elif breadth_pct >= 30:
            return 'broad_weak', -0.08
        else:
            return 'broad_bear', -0.15

    @staticmethod
    def _neutral_defaults() -> Dict:
        return {
            'breadth_pct': 50.0,
            'above_200sma': 0,
            'below_200sma': 0,
            'total_checked': 0,
            'signal': 'unknown',
            'regime_modifier': 0.0,
            'source': 'default',
        }


_default_provider: Optional[MarketBreadthProvider] = None


def get_default_provider() -> MarketBreadthProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = MarketBreadthProvider()
    return _default_provider


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = MarketBreadthProvider()
    result = p.get_breadth()
    print(f"NIFTY50 Breadth: {result['breadth_pct']:.0f}% above 200-SMA")
    print(f"Signal: {result['signal']} | Modifier: {result['regime_modifier']:+.2f}")
    print(f"Above: {result['above_200sma']} | Below: {result['below_200sma']} | Total: {result['total_checked']}")
