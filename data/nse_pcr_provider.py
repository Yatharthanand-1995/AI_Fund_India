"""
NSE Put/Call Ratio Provider

Fetches NIFTY options chain from NSE public API and computes the Put/Call Ratio (PCR).

PCR = Total Put OI / Total Call OI

Interpretation:
  PCR > 1.3  → excess put buying = fear/oversold = contrarian bullish signal
  PCR < 0.7  → excess call buying = greed = contrarian bearish (crowded longs)
  PCR 0.7–1.3 → neutral positioning

PCR diverges from India VIX during expiry weeks and options positioning squeezes
— capturing both provides a more complete picture of market sentiment extremes.

NSE publishes this data publicly at no cost.
"""

import logging
import time
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_NSE_OPTION_CHAIN_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_CACHE_TTL = 900   # 15 minutes — PCR shifts intraday during session


class NSEPCRProvider:
    """
    Computes NIFTY Put/Call Ratio from NSE option chain.

    Used as a regime sentiment overlay — extreme PCR readings flag
    positioning extremes that SMA/VIX alone miss (especially during expiry).
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self._cache: Optional[Dict] = None
        self._cache_ts: float = 0.0

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(_HEADERS)
            try:
                self._session.get("https://www.nseindia.com", timeout=self.timeout)
            except Exception:
                pass
        return self._session

    def get_pcr(self) -> Dict:
        """
        Fetch NIFTY PCR from NSE option chain.

        Returns:
          {
            'pcr': float,           # put OI / call OI
            'total_put_oi': int,
            'total_call_oi': int,
            'signal': str,          # 'fear' | 'neutral' | 'greed'
            'regime_modifier': float,  # confidence modifier for regime blending
            'source': str,
          }
        """
        now = time.monotonic()
        if self._cache and (now - self._cache_ts) < _CACHE_TTL:
            return {**self._cache, 'source': 'cache'}

        try:
            session = self._get_session()
            resp = session.get(_NSE_OPTION_CHAIN_URL, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            records = data.get('records', {}).get('data', [])
            total_put_oi = total_call_oi = 0

            for record in records:
                pe = record.get('PE', {})
                ce = record.get('CE', {})
                if pe:
                    total_put_oi += pe.get('openInterest', 0) or 0
                if ce:
                    total_call_oi += ce.get('openInterest', 0) or 0

            if total_call_oi == 0:
                return self._neutral_defaults()

            pcr = round(total_put_oi / total_call_oi, 3)
            signal, modifier = self._classify_pcr(pcr)

            result = {
                'pcr': pcr,
                'total_put_oi': total_put_oi,
                'total_call_oi': total_call_oi,
                'signal': signal,
                'regime_modifier': modifier,
                'source': 'nse_live',
            }
            self._cache = result
            self._cache_ts = now
            logger.info(f"NIFTY PCR: {pcr:.2f} ({signal}, modifier={modifier:+.2f})")
            return result

        except Exception as e:
            logger.debug(f"NSE PCR fetch failed: {e}")
            return self._neutral_defaults()

    @staticmethod
    def _classify_pcr(pcr: float):
        """
        Returns (signal, regime_confidence_modifier).

        modifier > 0 → confirms existing bullish bias (fear = potential reversal up)
        modifier < 0 → flags complacency/greed risk

        Thresholds match institutional practice (NSE/BlackRock standard):
          PCR > 1.5  extreme fear → strong reversal signal (+0.15 confidence if BULL)
          PCR > 1.3  elevated fear → mild bullish signal (+0.08)
          PCR 0.7–1.3 neutral → no adjustment
          PCR < 0.7  greed → mild bearish signal (-0.08)
          PCR < 0.5  extreme greed → strong bearish signal (-0.15)
        """
        if pcr > 1.5:
            return 'extreme_fear', +0.15
        elif pcr > 1.3:
            return 'fear', +0.08
        elif pcr < 0.5:
            return 'extreme_greed', -0.15
        elif pcr < 0.7:
            return 'greed', -0.08
        else:
            return 'neutral', 0.0

    @staticmethod
    def _neutral_defaults() -> Dict:
        return {
            'pcr': 1.0,
            'total_put_oi': 0,
            'total_call_oi': 0,
            'signal': 'neutral',
            'regime_modifier': 0.0,
            'source': 'default',
        }


_default_provider: Optional[NSEPCRProvider] = None


def get_default_provider() -> NSEPCRProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = NSEPCRProvider()
    return _default_provider


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = NSEPCRProvider()
    result = p.get_pcr()
    print(f"NIFTY PCR: {result['pcr']:.2f}")
    print(f"Signal: {result['signal']}")
    print(f"Regime modifier: {result['regime_modifier']:+.2f}")
    print(f"Put OI: {result['total_put_oi']:,} | Call OI: {result['total_call_oi']:,}")
