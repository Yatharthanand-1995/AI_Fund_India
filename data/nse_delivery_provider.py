"""
NSE Delivery & Deals Provider — Free, no API key required

Fetches from NSE India's public API (same pattern as fii_dii_provider.py):

1. Delivery Volume % — fraction of traded volume taken as delivery
   High delivery % on an up-day = genuine accumulation (not intraday speculation)

2. Block Deals — large institutional trades (> ₹10 Cr) reported to NSE
3. Bulk Deals — trades > 0.5% of equity shares reported to NSE

Both are strong signals for the InstitutionalFlowAgent.
Requires no authentication — NSE publishes this data publicly.
"""

import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── NSE API endpoints ─────────────────────────────────────────────────────────
_NSE_BASE = "https://www.nseindia.com"
_EQUITY_TRADE_URL = _NSE_BASE + "/api/quote-equity?symbol={symbol}&section=trade_info"
_BULK_DEALS_URL = _NSE_BASE + "/api/bulk-deals"
_BLOCK_DEALS_URL = _NSE_BASE + "/api/block-deals"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

# Cache TTLs
_DELIVERY_TTL = 900    # 15 min — refreshes intraday
_DEALS_TTL = 3600      # 60 min — bulk/block deals are end-of-day data


class NSEDeliveryProvider:
    """
    Provides delivery volume % and block/bulk deal signals for Indian stocks.

    Delivery Volume %:
        = (Delivery Quantity / Total Traded Quantity) × 100
        > 60% on an up-day → genuine buying, not just intraday speculation
        < 25% on a down-day → panic selling / stop-loss trigger (less structural)

    Block/Bulk Deals:
        Identifies if institutions have been buyers or sellers in recent deals.
        Each deal is checked against the queried symbol.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self._delivery_cache: Dict[str, Dict] = {}
        self._deals_cache: Optional[Dict] = None
        self._deals_cache_ts: float = 0.0

    # ── Session management ────────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        """Return a session with NSE cookies (required to avoid 401/403)."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(_HEADERS)
            try:
                self._session.get(_NSE_BASE, timeout=self.timeout)
            except Exception:
                pass  # proceed without cookies — may still work
        return self._session

    # ── Delivery volume ───────────────────────────────────────────────────────

    def get_delivery_data(self, symbol: str) -> Dict:
        """
        Fetch delivery volume % for a symbol.

        Returns:
            {
                'delivery_pct':     float | None   # 0–100
                'traded_quantity':  int   | None
                'delivery_quantity':int   | None
                'last_price':       float | None
                'change_pct':       float | None   # day % change
                'source':           str             # 'nse_live' or 'unavailable'
            }
        """
        now = time.monotonic()
        cached = self._delivery_cache.get(symbol)
        if cached and (now - cached.get("_ts", 0)) < _DELIVERY_TTL:
            return {k: v for k, v in cached.items() if k != "_ts"}

        session = self._get_session()
        url = _EQUITY_TRADE_URL.format(symbol=symbol)
        try:
            resp = session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            # Delivery data lives in securityWiseDP
            sdp = data.get("securityWiseDP", {})
            traded_qty = sdp.get("quantityTraded")
            delivery_qty = sdp.get("deliveryQuantity")
            # deliveryToTradedQuantity is already a percentage (e.g. 44.74)
            delivery_pct_raw = sdp.get("deliveryToTradedQuantity")

            delivery_pct: Optional[float] = None
            delivery_quantity: Optional[int] = None

            if delivery_pct_raw is not None:
                try:
                    delivery_pct = float(delivery_pct_raw)
                except (TypeError, ValueError):
                    pass

            if delivery_qty is not None:
                try:
                    delivery_quantity = int(delivery_qty)
                except (TypeError, ValueError):
                    pass

            # Price change comes from the marketDeptOrderBook.tradeInfo sub-key
            trade_info = data.get("marketDeptOrderBook", {}).get("tradeInfo", {})
            last_price = trade_info.get("totalTradedValue") or None  # fallback
            change_pct: Optional[float] = None
            # pChange not in trade_info section — we'll use delivery date as proxy
            # and leave change_pct as None (scoring will be direction-neutral)

            result = {
                "delivery_pct": round(delivery_pct, 2) if delivery_pct is not None else None,
                "traded_quantity": int(traded_qty) if traded_qty else None,
                "delivery_quantity": delivery_quantity,
                "last_price": None,
                "change_pct": change_pct,
                "source": "nse_live",
                "_ts": now,
            }
            self._delivery_cache[symbol] = result
            logger.info(
                f"Delivery data for {symbol}: {delivery_pct:.1f}% delivery"
                if delivery_pct is not None else f"Delivery data for {symbol}: delivery_pct=None"
            )
            return {k: v for k, v in result.items() if k != "_ts"}

        except Exception as e:
            logger.debug(f"Delivery fetch failed for {symbol}: {e}")
            return self._delivery_defaults()

    # ── Block / Bulk deals ────────────────────────────────────────────────────

    def get_deals_for_symbol(self, symbol: str) -> Dict:
        """
        Check if a symbol has appeared in recent block or bulk deals.

        Returns:
            {
                'bulk_buy_count':   int   # number of bulk BUY entries today
                'bulk_sell_count':  int   # number of bulk SELL entries today
                'block_buy_count':  int   # block BUY entries today
                'block_sell_count': int   # block SELL entries today
                'net_deal_signal':  float # positive = net buying, negative = net selling
                'source':           str
            }
        """
        deals = self._fetch_all_deals()
        symbol_upper = symbol.upper()

        bulk_buy = bulk_sell = block_buy = block_sell = 0

        for deal in deals.get("bulk", []):
            if deal.get("symbol", "").upper() == symbol_upper:
                qty = deal.get("quantity", 0) or 0
                trade_type = str(deal.get("buySell", "")).upper()
                if "B" in trade_type:
                    bulk_buy += 1
                elif "S" in trade_type:
                    bulk_sell += 1

        for deal in deals.get("block", []):
            if deal.get("symbol", "").upper() == symbol_upper:
                trade_type = str(deal.get("buySell", "")).upper()
                if "B" in trade_type:
                    block_buy += 1
                elif "S" in trade_type:
                    block_sell += 1

        total_buy = bulk_buy + block_buy
        total_sell = bulk_sell + block_sell
        net = total_buy - total_sell

        return {
            "bulk_buy_count": bulk_buy,
            "bulk_sell_count": bulk_sell,
            "block_buy_count": block_buy,
            "block_sell_count": block_sell,
            "net_deal_signal": float(net),
            "source": deals.get("source", "unavailable"),
        }

    def _fetch_all_deals(self) -> Dict:
        """Fetch bulk and block deals with caching."""
        now = time.monotonic()
        if self._deals_cache is not None and (now - self._deals_cache_ts) < _DEALS_TTL:
            return self._deals_cache

        session = self._get_session()
        result: Dict = {"bulk": [], "block": [], "source": "unavailable"}

        try:
            resp = session.get(_BULK_DEALS_URL, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()
            result["bulk"] = raw if isinstance(raw, list) else raw.get("data", [])
            result["source"] = "nse_live"
        except Exception as e:
            logger.debug(f"Bulk deals fetch failed: {e}")

        try:
            resp = session.get(_BLOCK_DEALS_URL, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()
            result["block"] = raw if isinstance(raw, list) else raw.get("data", [])
            result["source"] = "nse_live"
        except Exception as e:
            logger.debug(f"Block deals fetch failed: {e}")

        self._deals_cache = result
        self._deals_cache_ts = now
        return result

    # ── Scoring ───────────────────────────────────────────────────────────────

    def score_delivery(self, symbol: str, delivery_data: Optional[Dict] = None) -> float:
        """
        Convert delivery % into a score adjustment for InstitutionalFlowAgent.
        Returns float in [-6, +6].

        Logic:
        - High delivery (>65%) = genuine accumulation / holding → bullish
        - Medium delivery (40-65%) = normal, slight positive signal
        - Low delivery (<25%) = pure intraday speculation → bearish signal
          (people are not taking delivery, suggesting weak conviction)

        Direction (up/down day) is used as a multiplier when available.
        """
        if delivery_data is None:
            delivery_data = self.get_delivery_data(symbol)

        delivery_pct = delivery_data.get("delivery_pct")
        change_pct = delivery_data.get("change_pct")

        if delivery_pct is None:
            return 0.0

        # Base score from delivery % alone
        if delivery_pct >= 70:
            base = 6.0
        elif delivery_pct >= 60:
            base = 4.0
        elif delivery_pct >= 50:
            base = 2.0
        elif delivery_pct >= 40:
            base = 1.0
        elif delivery_pct >= 30:
            base = 0.0
        elif delivery_pct >= 20:
            base = -2.0
        else:
            base = -4.0   # <20% — very low conviction

        # If we know the day direction, amplify or flip accordingly
        if change_pct is not None:
            if change_pct > 0 and base > 0:
                base = min(6.0, base * 1.3)   # high delivery + up day → amplify
            elif change_pct < 0 and base > 0:
                base = -base * 0.8            # high delivery + down day → genuine selling

        return round(base, 2)

    def score_deals(self, symbol: str, deals_data: Optional[Dict] = None) -> float:
        """
        Convert block/bulk deal data into a score adjustment.
        Returns float in [-5, +5].
        """
        if deals_data is None:
            deals_data = self.get_deals_for_symbol(symbol)

        net = deals_data.get("net_deal_signal", 0.0)
        if net >= 3:
            return 5.0
        elif net == 2:
            return 4.0
        elif net == 1:
            return 2.0
        elif net == 0:
            return 0.0
        elif net == -1:
            return -2.0
        elif net == -2:
            return -4.0
        else:
            return -5.0

    # ── Defaults ──────────────────────────────────────────────────────────────

    @staticmethod
    def _delivery_defaults() -> Dict:
        return {
            "delivery_pct": None,
            "traded_quantity": None,
            "delivery_quantity": None,
            "last_price": None,
            "change_pct": None,
            "source": "unavailable",
        }

    def clear_cache(self) -> None:
        self._delivery_cache.clear()
        self._deals_cache = None
        self._deals_cache_ts = 0.0


# ── Module-level singleton ────────────────────────────────────────────────────
_default_provider: Optional[NSEDeliveryProvider] = None


def get_default_provider() -> NSEDeliveryProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = NSEDeliveryProvider()
    return _default_provider


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    provider = NSEDeliveryProvider()
    for sym in ["TCS", "RELIANCE", "HDFCBANK"]:
        d = provider.get_delivery_data(sym)
        deals = provider.get_deals_for_symbol(sym)
        print(
            f"{sym:12} delivery={d['delivery_pct']}%  "
            f"change={d['change_pct']}%  "
            f"deals net={deals['net_deal_signal']}"
        )
        print(f"  delivery_score={provider.score_delivery(sym, d):+.1f}  "
              f"deals_score={provider.score_deals(sym, deals):+.1f}")
