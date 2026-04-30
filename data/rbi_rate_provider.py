"""
RBI Rate Cycle Provider

Reads RBI Monetary Policy Committee (MPC) decisions from a local JSON config
and computes the current rate cycle direction + sector score adjustments.

RBI MPC meets 6 times/year (bi-monthly). Update data/rbi_rate_config.json
after each meeting — the cycle direction changes infrequently.

Cycle classification:
  cutting : last 2 decisions include ≥1 cut AND no recent hike
  hiking  : last 2 decisions include ≥1 hike AND no recent cut
  pausing : mixed or all holds

Sector adjustments (pts, capped ±3):
  Financial Services : ±2.5  — banks/NBFCs most rate-sensitive (NIMs, cost of funds)
  Consumer Cyclical  : ±1.5  — auto/durables loans cheaper/dearer
  Consumer Defensive : ±0.8  — rural credit improves/deteriorates with rate cuts
  All others         : 0     — technology, pharma, metals are rate-agnostic

Amplification: if ≥50 bps cut/hike in last 6 months, adjustments scale by 1.5×.
"""

import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "rbi_rate_config.json"

# Sector adjustments for a 1-notch cycle (25 bps move)
# Keys are Yahoo Finance sector names (matching stock_scorer._SECTOR_CURRENCY_SENSITIVITY)
_BASE_SECTOR_ADJUSTMENTS: Dict[str, float] = {
    "Financial Services": 2.5,   # Banks, NBFCs: NIM expansion on cuts
    "Consumer Cyclical":  1.5,   # Auto, durables: cheaper EMIs
    "Consumer Defensive": 0.8,   # FMCG: rural credit/consumption
    # Technology, Healthcare, Basic Materials, Energy: rate-agnostic → 0
}

_MAX_ADJ_PTS = 3.0   # Cap per stock
_AMPLIFY_THRESHOLD_BPS = 50  # Cumulative bps in 6 months that triggers 1.5× scale


class RBIRateProvider:
    """
    Reads RBI MPC history from rbi_rate_config.json and computes:
      - Current repo rate
      - Rate cycle: 'cutting' | 'hiking' | 'pausing'
      - Per-sector score adjustment (pts)

    The config file is the source of truth — update it after each MPC meeting.
    """

    def __init__(self, config_path: Path = _CONFIG_PATH):
        self._config_path = config_path
        self._data: Optional[Dict] = None

    def _load(self) -> Dict:
        if self._data is None:
            try:
                with open(self._config_path) as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.warning(f"RBI rate config not found/invalid: {e} — returning neutral defaults")
                self._data = {"repo_rate": 6.50, "decision_history": []}
        return self._data

    def get_rate_info(self) -> Dict:
        """
        Returns current rate state:
          {
            'repo_rate': float,
            'cycle': 'cutting' | 'hiking' | 'pausing',
            'cumulative_bps_6m': int,   # net bps change in last 6 months
            'last_action': str,
            'last_updated': str,
          }
        """
        data = self._load()
        history = data.get("decision_history", [])
        repo_rate = data.get("repo_rate", 6.50)
        last_updated = data.get("last_updated", "unknown")

        if not history:
            return {
                "repo_rate": repo_rate,
                "cycle": "pausing",
                "cumulative_bps_6m": 0,
                "last_action": "hold",
                "last_updated": last_updated,
            }

        # Compute cumulative bps in last 6 months
        cutoff = date.today() - timedelta(days=182)
        recent = [
            d for d in history
            if datetime.strptime(d["date"], "%Y-%m-%d").date() >= cutoff
        ]
        cumulative_bps = sum(d["bps"] for d in recent)

        # Classify cycle from last 2 decisions
        last2 = history[:2]
        actions = [d["action"] for d in last2]
        if "cut" in actions and "hike" not in actions:
            cycle = "cutting"
        elif "hike" in actions and "cut" not in actions:
            cycle = "hiking"
        else:
            cycle = "pausing"

        return {
            "repo_rate": repo_rate,
            "cycle": cycle,
            "cumulative_bps_6m": cumulative_bps,
            "last_action": history[0]["action"] if history else "hold",
            "last_updated": last_updated,
        }

    def get_sector_adjustment(self, sector: Optional[str]) -> float:
        """
        Returns score adjustment (pts) for a given sector based on RBI rate cycle.
        Positive = tailwind (cutting cycle), Negative = headwind (hiking cycle).
        Returns 0.0 for pausing or rate-agnostic sectors.
        """
        if not sector:
            return 0.0

        base = _BASE_SECTOR_ADJUSTMENTS.get(sector, 0.0)
        if base == 0.0:
            return 0.0

        rate_info = self.get_rate_info()
        cycle = rate_info["cycle"]

        if cycle == "pausing":
            return 0.0

        direction = 1.0 if cycle == "cutting" else -1.0

        # Amplify if ≥50 bps moved in last 6 months (aggressive cycle)
        cum = abs(rate_info["cumulative_bps_6m"])
        scale = 1.5 if cum >= _AMPLIFY_THRESHOLD_BPS else 1.0

        adj = direction * base * scale
        return round(float(max(-_MAX_ADJ_PTS, min(_MAX_ADJ_PTS, adj))), 2)


# Module-level singleton
_default_provider: Optional[RBIRateProvider] = None


def get_default_provider() -> RBIRateProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = RBIRateProvider()
    return _default_provider


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    p = RBIRateProvider()
    info = p.get_rate_info()
    print(f"\nRBI Rate Cycle Summary")
    print(f"  Repo rate      : {info['repo_rate']}%")
    print(f"  Cycle          : {info['cycle'].upper()}")
    print(f"  Cum. bps (6m)  : {info['cumulative_bps_6m']:+d} bps")
    print(f"  Last action    : {info['last_action']}")
    print(f"  Last updated   : {info['last_updated']}")
    print()
    print("Sector adjustments:")
    for sector in [
        "Financial Services", "Consumer Cyclical", "Consumer Defensive",
        "Technology", "Healthcare", "Basic Materials", "Energy",
    ]:
        adj = p.get_sector_adjustment(sector)
        bar = "+" * int(abs(adj) * 2) if adj > 0 else "-" * int(abs(adj) * 2)
        print(f"  {sector:25s}: {adj:+.2f} pts  {bar}")
