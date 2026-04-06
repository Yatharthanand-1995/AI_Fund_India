"""
News Sentiment Provider — Yahoo Finance RSS (Free, no API key required)

Fetches stock news headlines from Yahoo Finance RSS feeds and scores them
using a keyword dictionary. No LLM, no API key, no external dependencies
beyond Python stdlib + requests (already in requirements).

Scoring output: float in [-1.0, +1.0]
  +1.0 = strongly bullish headlines
  -1.0 = strongly bearish headlines
   0.0 = neutral / no data

Used by SentimentAgent to add a news-based adjustment (±8 points).
"""

import logging
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

# ── Keyword dictionaries ──────────────────────────────────────────────────────
# Weighted: strong signals get 2, mild signals get 1

BULLISH_KEYWORDS: Dict[str, int] = {
    # Strong positive signals
    "record profit": 2, "record revenue": 2, "record high": 2,
    "beat estimate": 2, "beat expectation": 2, "strong results": 2,
    "upgrade": 2, "outperform": 2, "buy rating": 2,
    "major order": 2, "large order": 2, "mega deal": 2,
    "capacity expansion": 2, "strong demand": 2,
    # Mild positive
    "profit": 1, "gain": 1, "rise": 1, "rally": 1, "surge": 1,
    "soar": 1, "jump": 1, "growth": 1, "positive": 1, "strong": 1,
    "win": 1, "award": 1, "deal": 1, "order": 1, "acquisition": 1,
    "expansion": 1, "launch": 1, "partnership": 1, "dividend": 1,
    "buyback": 1, "share buyback": 1, "new high": 1, "upside": 1,
    "recover": 1, "rebound": 1, "improve": 1, "beat": 1,
    "margin expansion": 1, "market share": 1,
}

BEARISH_KEYWORDS: Dict[str, int] = {
    # Strong negative signals
    "miss estimate": 2, "miss expectation": 2, "profit warning": 2,
    "earnings miss": 2, "revenue miss": 2, "guidance cut": 2,
    "fraud": 2, "scam": 2, "sebi probe": 2, "investigation": 2,
    "default": 2, "debt restructure": 2, "insolvency": 2,
    "downgrade": 2, "sell rating": 2, "underperform": 2,
    "plant shutdown": 2, "mass layoff": 2,
    # Mild negative
    "loss": 1, "fall": 1, "drop": 1, "decline": 1, "plunge": 1,
    "crash": 1, "slump": 1, "weak": 1, "concern": 1, "risk": 1,
    "penalty": 1, "fine": 1, "probe": 1, "recall": 1, "delay": 1,
    "slowdown": 1, "cut": 1, "reduce": 1, "miss": 1, "shortfall": 1,
    "headwind": 1, "pressure": 1, "challenge": 1, "below estimate": 1,
    "margin pressure": 1, "write-off": 1, "writedown": 1,
}

# RSS feed URL template — works for NSE symbols with .NS suffix
_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}.NS&region=IN&lang=en-US"

# Cache: symbol → {score, headlines, fetched_at}
_cache: Dict[str, Dict] = {}
_CACHE_TTL = 1800  # 30 minutes


def _fetch_rss(symbol: str, timeout: int = 8) -> List[str]:
    """Fetch headlines from Yahoo Finance RSS. Returns list of title strings."""
    url = _RSS_URL.format(symbol=symbol)
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        titles = []
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                titles.append(title_el.text.strip().lower())
        return titles
    except Exception as e:
        logger.debug(f"News RSS fetch failed for {symbol}: {e}")
        return []


def _score_headlines(headlines: List[str]) -> float:
    """
    Score a list of headlines using keyword dictionaries.
    Returns float in [-1.0, +1.0].
    """
    if not headlines:
        return 0.0

    total_bullish = 0
    total_bearish = 0

    for headline in headlines:
        for phrase, weight in BULLISH_KEYWORDS.items():
            if phrase in headline:
                total_bullish += weight
        for phrase, weight in BEARISH_KEYWORDS.items():
            if phrase in headline:
                total_bearish += weight

    net = total_bullish - total_bearish
    # Normalise: each headline can contribute roughly 1-2 points,
    # so scale by number of headlines to keep it in [-1, +1]
    max_possible = len(headlines) * 3  # rough ceiling
    if max_possible == 0:
        return 0.0

    raw = net / max_possible
    return max(-1.0, min(1.0, raw))


def get_news_sentiment(symbol: str, max_headlines: int = 20) -> Dict:
    """
    Fetch and score news headlines for a stock symbol.

    Returns:
        {
            'sentiment_score': float  # -1.0 to +1.0
            'headline_count': int
            'bullish_count': int      # headlines with bullish signals
            'bearish_count': int      # headlines with bearish signals
            'headlines': List[str]    # raw headlines (lowercase)
            'source': str             # 'yahoo_rss' or 'cache' or 'unavailable'
        }
    """
    now = time.monotonic()
    cached = _cache.get(symbol)
    if cached and (now - cached["fetched_at"]) < _CACHE_TTL:
        logger.debug(f"News sentiment cache hit for {symbol}")
        result = dict(cached)
        result["source"] = "cache"
        return result

    headlines = _fetch_rss(symbol, timeout=8)[:max_headlines]

    if not headlines:
        result = _unavailable_defaults()
        result["source"] = "unavailable"
        _cache[symbol] = {**result, "fetched_at": now}
        return result

    # Count bullish/bearish headlines
    bullish_count = 0
    bearish_count = 0
    for h in headlines:
        b = sum(w for p, w in BULLISH_KEYWORDS.items() if p in h)
        be = sum(w for p, w in BEARISH_KEYWORDS.items() if p in h)
        if b > be:
            bullish_count += 1
        elif be > b:
            bearish_count += 1

    score = _score_headlines(headlines)

    result = {
        "sentiment_score": round(score, 3),
        "headline_count": len(headlines),
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "headlines": headlines,
        "source": "yahoo_rss",
        "fetched_at": now,
    }
    _cache[symbol] = result
    logger.info(
        f"News sentiment for {symbol}: score={score:+.2f} "
        f"({bullish_count} bullish, {bearish_count} bearish, {len(headlines)} headlines)"
    )
    return result


def score_to_adjustment(sentiment_score: float, max_adjustment: float = 8.0) -> float:
    """
    Convert sentiment score [-1, +1] to a scoring adjustment [-max, +max].
    Used by SentimentAgent to nudge the total score.
    """
    return round(sentiment_score * max_adjustment, 2)


def _unavailable_defaults() -> Dict:
    return {
        "sentiment_score": 0.0,
        "headline_count": 0,
        "bullish_count": 0,
        "bearish_count": 0,
        "headlines": [],
    }


# ── Module-level convenience ──────────────────────────────────────────────────

def clear_cache() -> None:
    """Clear the in-memory news cache (e.g. after data collection)."""
    _cache.clear()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for sym in ["TCS", "RELIANCE", "INFY", "HDFCBANK"]:
        data = get_news_sentiment(sym)
        print(
            f"{sym:12} score={data['sentiment_score']:+.2f}  "
            f"headlines={data['headline_count']}  "
            f"bull={data['bullish_count']} bear={data['bearish_count']}  "
            f"source={data['source']}"
        )
        if data["headlines"]:
            print(f"  Latest: {data['headlines'][0][:80]}")
