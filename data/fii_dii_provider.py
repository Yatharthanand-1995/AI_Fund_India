"""
FII/DII Flow Provider

Fetches Foreign Institutional Investor (FII) and Domestic Institutional Investor (DII)
net buy/sell data from NSE India's public API.

FII/DII flow is a critical signal for Indian equity markets:
- FII buying: Strong bullish signal (foreign inflows lift all boats)
- DII buying: Counter-cyclical (often buys when FII sells)
- FII selling + DII selling: Severe bearish signal
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# NSE public endpoint for FII/DII data
NSE_FII_DII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
NSE_BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/fii-dii-activity",
}

# Cache duration in seconds (60 minutes — data is published daily)
CACHE_TTL = 3600


class FIIDIIProvider:
    """
    Provides FII/DII net flow data from NSE India.

    Returns rolling 30-day net buy/sell figures for FII and DII.
    Gracefully returns safe neutral defaults on network failure.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._cache: Optional[Dict] = None
        self._cache_ts: float = 0.0
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """Create or reuse an HTTP session with NSE cookies."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(NSE_BASE_HEADERS)
            # NSE requires an initial visit to set cookies
            try:
                self._session.get(
                    "https://www.nseindia.com",
                    timeout=self.timeout
                )
            except Exception:
                pass  # Continue without cookies — may still work
        return self._session

    def _fetch_raw(self) -> List[Dict]:
        """Fetch raw FII/DII records from NSE API."""
        session = self._get_session()
        response = session.get(NSE_FII_DII_URL, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return []

    def _parse_records(self, records: List[Dict]) -> Dict:
        """
        Parse raw NSE records into aggregated FII/DII net flow.

        Returns dict with:
        - fii_net_30d: FII net buy (+ = buying, - = selling) in crores
        - dii_net_30d: DII net buy (+ = buying, - = selling) in crores
        - fii_recent_trend: 'buying' | 'selling' | 'neutral'
        - dii_recent_trend: 'buying' | 'selling' | 'neutral'
        - days_available: number of records parsed
        - last_updated: ISO timestamp of most recent record
        """
        fii_net_total = 0.0
        dii_net_total = 0.0
        fii_recent = []
        dii_recent = []
        last_date = None

        cutoff = datetime.now() - timedelta(days=30)

        for rec in records:
            try:
                # NSE uses 'date' key with format DD-Mon-YYYY
                date_str = rec.get("date", "")
                try:
                    rec_date = datetime.strptime(date_str, "%d-%b-%Y")
                except ValueError:
                    continue

                if rec_date < cutoff:
                    continue

                fii_net = float(rec.get("fiinf", rec.get("fiiNet", 0)) or 0)
                dii_net = float(rec.get("diinf", rec.get("diiNet", 0)) or 0)

                fii_net_total += fii_net
                dii_net_total += dii_net
                fii_recent.append(fii_net)
                dii_recent.append(dii_net)

                if last_date is None or rec_date > last_date:
                    last_date = rec_date

            except (ValueError, TypeError, KeyError):
                continue

        def _trend(values: List[float]) -> str:
            if not values:
                return "neutral"
            # Use last 5 days for trend
            recent = values[-5:]
            net = sum(recent)
            if net > 500:
                return "buying"
            if net < -500:
                return "selling"
            return "neutral"

        return {
            "fii_net_30d": round(fii_net_total, 2),
            "dii_net_30d": round(dii_net_total, 2),
            "fii_recent_trend": _trend(fii_recent),
            "dii_recent_trend": _trend(dii_recent),
            "days_available": len(fii_recent),
            "last_updated": last_date.isoformat() if last_date else None,
        }

    def get_flow_data(self) -> Dict:
        """
        Get aggregated FII/DII net flow for the past 30 days.

        Returns cached data if available and fresh, otherwise fetches from NSE.
        Returns safe neutral defaults if network is unavailable.
        """
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_ts) < CACHE_TTL:
            logger.debug("FII/DII: returning cached data")
            return self._cache

        try:
            records = self._fetch_raw()
            result = self._parse_records(records)
            result["source"] = "nse_live"
            self._cache = result
            self._cache_ts = now
            logger.info(
                f"FII/DII fetched: FII {result['fii_net_30d']:+.0f}Cr, "
                f"DII {result['dii_net_30d']:+.0f}Cr ({result['days_available']} days)"
            )
            return result
        except Exception as e:
            logger.warning(f"FII/DII fetch failed ({type(e).__name__}): {e} — using neutral defaults")
            return self._neutral_defaults()

    @staticmethod
    def _neutral_defaults() -> Dict:
        """Return safe neutral defaults when data is unavailable."""
        return {
            "fii_net_30d": 0.0,
            "dii_net_30d": 0.0,
            "fii_recent_trend": "neutral",
            "dii_recent_trend": "neutral",
            "days_available": 0,
            "last_updated": None,
            "source": "default",
        }

    def score_flow(self, flow_data: Optional[Dict] = None) -> float:
        """
        Convert FII/DII flow data into a score adjustment (-15 to +15).

        Positive = institutional accumulation (bullish)
        Negative = institutional distribution (bearish)
        """
        if flow_data is None:
            flow_data = self.get_flow_data()

        if flow_data.get("source") == "default" or flow_data.get("days_available", 0) == 0:
            return 0.0  # No data — neutral

        fii_net = flow_data.get("fii_net_30d", 0.0)
        dii_net = flow_data.get("dii_net_30d", 0.0)
        fii_trend = flow_data.get("fii_recent_trend", "neutral")
        dii_trend = flow_data.get("dii_recent_trend", "neutral")

        score = 0.0

        # FII net flow (primary signal, ±10 points)
        if fii_net > 10000:
            score += 10
        elif fii_net > 5000:
            score += 7
        elif fii_net > 2000:
            score += 4
        elif fii_net > 0:
            score += 2
        elif fii_net < -10000:
            score -= 10
        elif fii_net < -5000:
            score -= 7
        elif fii_net < -2000:
            score -= 4
        elif fii_net < 0:
            score -= 2

        # DII net flow (secondary signal, ±5 points)
        if dii_net > 5000:
            score += 5
        elif dii_net > 2000:
            score += 3
        elif dii_net > 0:
            score += 1
        elif dii_net < -5000:
            score -= 5
        elif dii_net < -2000:
            score -= 3
        elif dii_net < 0:
            score -= 1

        # Both selling = amplify negative signal
        if fii_trend == "selling" and dii_trend == "selling":
            score -= 2
        # Both buying = amplify positive signal
        elif fii_trend == "buying" and dii_trend == "buying":
            score += 2

        return max(-15.0, min(15.0, score))


# Module-level singleton for reuse across agents
_default_provider: Optional[FIIDIIProvider] = None


def get_default_provider() -> FIIDIIProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = FIIDIIProvider()
    return _default_provider
