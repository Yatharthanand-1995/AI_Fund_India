"""
Portfolio Manager — Signal-driven live portfolio for the AI Hedge Fund.

Architecture (mirrors the backtest signal mode):
  BUY  : composite_score >= buy_threshold  AND  sector/position limits allow
  HOLD : sell_threshold <= score < buy_threshold  AND  no stop-loss breach
  SELL : score < sell_threshold  OR  price dropped > stop_loss_pct from entry

Persists state in SQLite so the portfolio survives server restarts.
All monetary values are in INR. Portfolio is paper-trading only.
"""

import sqlite3
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sector mapping (NIFTY50 — mirrors backtest NIFTY50_SECTORS)
# ---------------------------------------------------------------------------
NIFTY50_SECTORS: Dict[str, str] = {
    'RELIANCE':   'Energy',   'ONGC':      'Energy',   'BPCL':      'Energy',
    'COALINDIA':  'Energy',   'NTPC':      'Energy',   'POWERGRID': 'Energy',
    'TCS':        'IT',       'INFY':      'IT',       'WIPRO':     'IT',
    'HCLTECH':    'IT',       'TECHM':     'IT',       'LTIM':      'IT',
    'HDFCBANK':   'Financials','ICICIBANK': 'Financials','SBIN':     'Financials',
    'AXISBANK':   'Financials','KOTAKBANK': 'Financials','BAJFINANCE':'Financials',
    'BAJAJFINSV': 'Financials','SBILIFE':   'Financials','HDFCLIFE': 'Financials',
    'INDUSINDBK': 'Financials',
    'HINDUNILVR': 'FMCG',     'ITC':       'FMCG',     'NESTLEIND': 'FMCG',
    'BRITANNIA':  'FMCG',     'TATACONSUM':'FMCG',
    'SUNPHARMA':  'Pharma',   'DIVISLAB':  'Pharma',   'CIPLA':     'Pharma',
    'DRREDDY':    'Pharma',   'APOLLOHOSP':'Pharma',
    'TATAMOTORS': 'Auto',     'MARUTI':    'Auto',     'HEROMOTOCO':'Auto',
    'EICHERMOT':  'Auto',     'BAJAJ-AUTO':'Auto',     'M&M':       'Auto',
    'JSWSTEEL':   'Metals',   'TATASTEEL': 'Metals',   'HINDALCO':  'Metals',
    'LT':         'Industrials','ADANIPORTS':'Industrials','ADANIENT':'Industrials',
    'GRASIM':     'Construction','ULTRACEMCO':'Construction',
    'ASIANPAINT': 'Consumer', 'TITAN':     'Consumer',
    'BHARTIARTL': 'Telecom',
}

SECTOR_MAX_OVERRIDES: Dict[str, int] = {
    'IT': 2,  # default (BEAR/SIDEWAYS): worst sector by IC diagnostic
}

# Regime-aware sector caps: relax cyclical caps in confirmed bull, tighten in bear.
# Trend prefix (BULL/BEAR/SIDEWAYS) extracted from regime string e.g. "BULL_NORMAL".
SECTOR_CAPS_BY_REGIME: Dict[str, Dict[str, int]] = {
    'BULL': {
        # Bull market: momentum leaders (IT, Financials) can run — allow more concentration
        'IT': 4, 'Financials': 3, 'Metals': 3, 'Auto': 3,
    },
    'BEAR': {
        # Bear market: reduce cyclical exposure, keep defensives intact
        'IT': 2, 'Financials': 2, 'Metals': 1, 'Auto': 1,
        'Pharma': 3, 'FMCG': 3,   # defensives get more room in bear
    },
    'SIDEWAYS': {
        # Sideways: moderate relaxation from base defaults
        'IT': 3, 'Financials': 3, 'Metals': 2, 'Auto': 2,
    },
}


def _get_sector_overrides(regime: str) -> Dict[str, int]:
    """Return sector hard-cap overrides for the given regime string."""
    trend = regime.split('_')[0].upper() if regime else 'SIDEWAYS'
    return SECTOR_CAPS_BY_REGIME.get(trend, SECTOR_MAX_OVERRIDES)


def _is_fno_expiry_window(date: Optional[datetime] = None) -> bool:
    """
    Returns True if today is within 2 calendar days before the NSE F&O expiry
    (last Thursday of the month), or on the expiry day itself.

    During F&O expiry week, rollover flows and short-covering cause intraday
    volatility spikes that distort entry prices. New BUY entries are suppressed.
    Exits (SELL_STOP, SELL_SCORE) are NOT suppressed — the guard only blocks new entries.
    """
    d = (date or datetime.now(timezone.utc)).date()
    # Find last Thursday of the current month
    import calendar
    last_day = calendar.monthrange(d.year, d.month)[1]
    last_thursday = max(
        datetime(d.year, d.month, day).date()
        for day in range(last_day, last_day - 7, -1)
        if datetime(d.year, d.month, day).weekday() == 3  # Thursday = 3
    )
    # Guard window: expiry day and 2 calendar days before it
    return last_thursday - timedelta(days=2) <= d <= last_thursday


def _clean_symbol(symbol: str) -> str:
    return symbol.replace('.NS', '').replace('.BO', '').upper()


def _get_sector(symbol: str) -> str:
    return NIFTY50_SECTORS.get(_clean_symbol(symbol), 'Other')


def _live_correlation_guard(
    candidate_sym: str,
    held_symbols: List[str],
    price_history_fn,
    max_corr: float = 0.70,
    max_peers: int = 2,
    window: int = 60,
) -> Tuple[bool, str]:
    """
    Return (blocked, reason) for a candidate stock entry.

    Uses a callable price_history_fn(symbol) → pd.Series of daily closes
    to compute 60-day rolling return correlations between the candidate
    and all currently held positions.

    Blocks entry when candidate correlates > max_corr with max_peers or
    more existing holdings — prevents the Jan-2025 style 4-defensive-stock
    simultaneous crash.
    """
    if len(held_symbols) < max_peers:
        return False, ''

    try:
        import pandas as pd

        cand_prices = price_history_fn(candidate_sym)
        if cand_prices is None or len(cand_prices) < window:
            return False, ''
        cand_rets = cand_prices.pct_change().dropna().iloc[-window:]

        high_corr_peers = []
        for held in held_symbols:
            try:
                held_prices = price_history_fn(held)
                if held_prices is None or len(held_prices) < window:
                    continue
                held_rets = held_prices.pct_change().dropna().iloc[-window:]
                common = cand_rets.index.intersection(held_rets.index)
                if len(common) < window // 2:
                    continue
                corr = float(np.corrcoef(
                    cand_rets.loc[common].values,
                    held_rets.loc[common].values
                )[0, 1])
                if corr > max_corr:
                    high_corr_peers.append(f"{held}({corr:.2f})")
            except Exception:
                continue

        if len(high_corr_peers) >= max_peers:
            return True, (f"Correlation guard: {candidate_sym} correlates >{max_corr:.0%} "
                          f"with {', '.join(high_corr_peers)}")
    except Exception:
        pass

    return False, ''


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PortfolioConfig:
    # ── Core thresholds (Config A values) ────────────────────────────────
    buy_threshold: float = 60.0    # was 65 — aligned with BacktestScorer v4 calibration
    sell_threshold: float = 38.0   # was 50 — wider hold zone, reduces churn
    stop_loss_pct: float = 0.10    # 10% hard stop from entry
    max_positions: int = 10
    sector_cap_pct: float = 0.30

    # ── Config A: min-hold and profit protection ──────────────────────────
    min_hold_months: int = 3           # no SELL_SCORE within first 3 months
    profit_trigger_pct: float = 0.20   # profit % to activate trailing stop
    profit_trail_pct: float = 0.12     # trail % from peak once activated

    # ── Config A: M1 — relative rank (RS) exit ───────────────────────────
    # Uses composite_score cross-sectional rank as a live proxy for RS rank.
    # Bottom-35th percentile of scores ≈ bottom-35th percentile of RS.
    rs_exit_enabled: bool = True
    rs_exit_percentile: float = 0.35   # fire when below this fraction of universe
    rs_exit_strikes: int = 3           # consecutive evaluations below threshold

    # ── Config A: M3 — max holding period with progressive score hurdle ───
    m3_maxhold_enabled: bool = True
    m3_12m_decay: float = 8.0    # at 12M: score must not decay more than this from entry
    m3_18m_decay: float = 3.0    # at 18M: tighter decay allowance
    # at 24M: must beat 75th pct of current universe (hardcoded, no config needed)

    # ── M3 re-entry cooldown ──────────────────────────────────────────────
    m3_cooldown_months: int = 6    # block re-entry for this many months after M3 exit

    updated_at: str = ''

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Holding:
    id: int
    symbol: str
    entry_price: float
    entry_score: float
    entry_date: str
    sector: str
    current_price: Optional[float] = None
    current_score: Optional[float] = None
    return_pct: Optional[float] = None
    signal: str = 'HOLD'       # HOLD | SELL_SCORE | SELL_STOP

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ClosedTrade:
    id: int
    symbol: str
    entry_price: float
    entry_score: float
    entry_date: str
    exit_price: float
    exit_date: str
    exit_reason: str
    return_pct: float
    sector: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SignalItem:
    symbol: str
    signal: str          # BUY | HOLD | SELL_SCORE | SELL_STOP | WATCH
    composite_score: float
    current_price: Optional[float]
    entry_price: Optional[float]       # None for BUY signals (not yet held)
    return_pct: Optional[float]
    reason: str
    sector: str
    recommendation: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvaluationResult:
    evaluated_at: str
    n_holdings: int
    signals: List[SignalItem]
    buys: List[SignalItem]
    sells: List[SignalItem]
    holds: List[SignalItem]
    watches: List[SignalItem]          # high-score stocks not yet bought (at capacity)
    portfolio_return_pct: float
    regime: str

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class PortfolioDatabase:
    """SQLite persistence for portfolio holdings and signal history."""

    def __init__(self, db_path: str = "data/portfolio.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_tables(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS portfolio_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    buy_threshold REAL DEFAULT 60.0,
                    sell_threshold REAL DEFAULT 38.0,
                    stop_loss_pct REAL DEFAULT 0.10,
                    max_positions INTEGER DEFAULT 10,
                    sector_cap_pct REAL DEFAULT 0.30,
                    min_hold_months INTEGER DEFAULT 3,
                    profit_trigger_pct REAL DEFAULT 0.20,
                    profit_trail_pct REAL DEFAULT 0.12,
                    rs_exit_enabled INTEGER DEFAULT 1,
                    rs_exit_percentile REAL DEFAULT 0.35,
                    rs_exit_strikes INTEGER DEFAULT 3,
                    m3_maxhold_enabled INTEGER DEFAULT 1,
                    m3_12m_decay REAL DEFAULT 8.0,
                    m3_18m_decay REAL DEFAULT 3.0,
                    m3_cooldown_months INTEGER DEFAULT 6,
                    updated_at TEXT
                );

                INSERT OR IGNORE INTO portfolio_config (id) VALUES (1);

                CREATE TABLE IF NOT EXISTS portfolio_holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    entry_price REAL NOT NULL,
                    entry_score REAL NOT NULL,
                    entry_date TEXT NOT NULL,
                    sector TEXT NOT NULL DEFAULT 'Other',
                    status TEXT NOT NULL DEFAULT 'open',
                    trailing_stop_price REAL,
                    peak_price REAL,
                    rs_strike_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS portfolio_cooldowns (
                    symbol TEXT PRIMARY KEY,
                    cooldown_until TEXT NOT NULL,
                    exit_reason TEXT,
                    exited_at TEXT
                );

                CREATE TABLE IF NOT EXISTS portfolio_closed_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_score REAL NOT NULL,
                    entry_date TEXT NOT NULL,
                    exit_price REAL NOT NULL,
                    exit_date TEXT NOT NULL,
                    exit_reason TEXT NOT NULL,
                    return_pct REAL NOT NULL,
                    sector TEXT NOT NULL DEFAULT 'Other'
                );

                CREATE TABLE IF NOT EXISTS portfolio_signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evaluated_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    composite_score REAL,
                    current_price REAL,
                    entry_price REAL,
                    return_pct REAL,
                    reason TEXT,
                    regime TEXT
                );
            """)
            # ── Migrations: add new columns to existing tables without data loss ──
            holding_cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(portfolio_holdings)"
            ).fetchall()]
            for col, defn in [
                ('trailing_stop_price', 'REAL'),
                ('peak_price',          'REAL'),
                ('rs_strike_count',     'INTEGER DEFAULT 0'),
            ]:
                if col not in holding_cols:
                    conn.execute(f"ALTER TABLE portfolio_holdings ADD COLUMN {col} {defn}")
                    logger.info(f"Migrated portfolio_holdings: added {col}")

            config_cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(portfolio_config)"
            ).fetchall()]
            for col, defn in [
                ('min_hold_months',    'INTEGER DEFAULT 3'),
                ('profit_trigger_pct', 'REAL DEFAULT 0.20'),
                ('profit_trail_pct',   'REAL DEFAULT 0.12'),
                ('rs_exit_enabled',    'INTEGER DEFAULT 1'),
                ('rs_exit_percentile', 'REAL DEFAULT 0.35'),
                ('rs_exit_strikes',    'INTEGER DEFAULT 3'),
                ('m3_maxhold_enabled', 'INTEGER DEFAULT 1'),
                ('m3_12m_decay',       'REAL DEFAULT 8.0'),
                ('m3_18m_decay',       'REAL DEFAULT 3.0'),
                ('m3_cooldown_months', 'INTEGER DEFAULT 6'),
            ]:
                if col not in config_cols:
                    conn.execute(f"ALTER TABLE portfolio_config ADD COLUMN {col} {defn}")
                    logger.info(f"Migrated portfolio_config: added {col}")

    # ── Config ────────────────────────────────────────────────────────────

    def get_config(self) -> PortfolioConfig:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM portfolio_config WHERE id=1").fetchone()
            if row:
                d = dict(row)
                return PortfolioConfig(
                    buy_threshold=d.get('buy_threshold', 60.0),
                    sell_threshold=d.get('sell_threshold', 38.0),
                    stop_loss_pct=d.get('stop_loss_pct', 0.10),
                    max_positions=d.get('max_positions', 10),
                    sector_cap_pct=d.get('sector_cap_pct', 0.30),
                    min_hold_months=d.get('min_hold_months', 3),
                    profit_trigger_pct=d.get('profit_trigger_pct', 0.20),
                    profit_trail_pct=d.get('profit_trail_pct', 0.12),
                    rs_exit_enabled=bool(d.get('rs_exit_enabled', 1)),
                    rs_exit_percentile=d.get('rs_exit_percentile', 0.35),
                    rs_exit_strikes=d.get('rs_exit_strikes', 3),
                    m3_maxhold_enabled=bool(d.get('m3_maxhold_enabled', 1)),
                    m3_12m_decay=d.get('m3_12m_decay', 8.0),
                    m3_18m_decay=d.get('m3_18m_decay', 3.0),
                    m3_cooldown_months=d.get('m3_cooldown_months', 6),
                    updated_at=d.get('updated_at') or '',
                )
            return PortfolioConfig()

    def update_config(self, **kwargs) -> PortfolioConfig:
        allowed = {
            'buy_threshold', 'sell_threshold', 'stop_loss_pct',
            'max_positions', 'sector_cap_pct',
            'min_hold_months', 'profit_trigger_pct', 'profit_trail_pct',
            'rs_exit_enabled', 'rs_exit_percentile', 'rs_exit_strikes',
            'm3_maxhold_enabled', 'm3_12m_decay', 'm3_18m_decay', 'm3_cooldown_months',
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        set_clause = ', '.join(f"{k}=?" for k in updates)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE portfolio_config SET {set_clause} WHERE id=1",
                list(updates.values())
            )
        return self.get_config()

    # ── Holdings ──────────────────────────────────────────────────────────

    def get_open_holdings(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_holdings WHERE status='open' ORDER BY entry_date DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def add_holding(self, symbol: str, entry_price: float,
                    entry_score: float, stop_loss_pct: float = 0.10,
                    initial_stop_price: Optional[float] = None) -> Dict:
        sector = _get_sector(symbol)
        now = datetime.now(timezone.utc).isoformat()
        # Prefer ATR-based stop from scorer (initial_stop_price) over flat-% fallback.
        # ATR stop adapts to each stock's actual volatility; flat % is a last resort.
        if initial_stop_price and initial_stop_price > 0:
            trailing_stop = round(float(initial_stop_price), 2)
        elif entry_price > 0:
            trailing_stop = round(entry_price * (1.0 - stop_loss_pct), 2)
        else:
            trailing_stop = None
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO portfolio_holdings
                   (symbol, entry_price, entry_score, entry_date, sector, status, trailing_stop_price)
                   VALUES (?,?,?,?,?,'open',?)""",
                (symbol, entry_price, entry_score, now, sector, trailing_stop)
            )
        return {'symbol': symbol, 'entry_price': entry_price,
                'entry_score': entry_score, 'entry_date': now, 'sector': sector,
                'trailing_stop_price': trailing_stop}

    def close_holding(self, symbol: str, exit_price: float,
                      exit_reason: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM portfolio_holdings WHERE symbol=? AND status='open'",
                (symbol,)
            ).fetchone()
            if not row:
                return None
            return_pct = (exit_price - row['entry_price']) / row['entry_price'] * 100
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO portfolio_closed_trades
                   (symbol,entry_price,entry_score,entry_date,exit_price,
                    exit_date,exit_reason,return_pct,sector)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (symbol, row['entry_price'], row['entry_score'], row['entry_date'],
                 exit_price, now, exit_reason, return_pct, row['sector'])
            )
            conn.execute(
                "DELETE FROM portfolio_holdings WHERE symbol=? AND status='open'",
                (symbol,)
            )
            return {'symbol': symbol, 'return_pct': return_pct,
                    'exit_reason': exit_reason}

    def get_closed_trades(self, limit: int = 50) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_closed_trades ORDER BY exit_date DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def reset_portfolio(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM portfolio_holdings")
            conn.execute("DELETE FROM portfolio_closed_trades")
            conn.execute("DELETE FROM portfolio_signal_log")

    # ── Signal log ────────────────────────────────────────────────────────

    def log_signals(self, signals: List[SignalItem], regime: str,
                    evaluated_at: str):
        rows = [
            (evaluated_at, s.symbol, s.signal, s.composite_score,
             s.current_price, s.entry_price, s.return_pct, s.reason, regime)
            for s in signals
        ]
        with self._conn() as conn:
            conn.executemany(
                """INSERT INTO portfolio_signal_log
                   (evaluated_at,symbol,signal,composite_score,current_price,
                    entry_price,return_pct,reason,regime)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                rows
            )

    def get_signal_history(self, limit: int = 100) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_signal_log ORDER BY evaluated_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Peak price tracking ───────────────────────────────────────────────

    def update_peak_price(self, symbol: str, new_peak: float) -> None:
        """Ratchet up the peak_price high-watermark for a holding."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE portfolio_holdings SET peak_price=? WHERE symbol=? AND status='open'",
                (round(new_peak, 2), symbol)
            )

    def update_rs_strikes(self, symbol: str, count: int) -> None:
        """Persist the M1 consecutive-strike count for a holding."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE portfolio_holdings SET rs_strike_count=? WHERE symbol=? AND status='open'",
                (count, symbol)
            )

    # ── Re-entry cooldown (M3 exits) ──────────────────────────────────────

    def set_cooldown(self, symbol: str, months: int, exit_reason: str) -> None:
        """Block re-entry for `months` months after an M3-triggered exit."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        until = (now + timedelta(days=30 * months)).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO portfolio_cooldowns
                   (symbol, cooldown_until, exit_reason, exited_at) VALUES (?,?,?,?)""",
                (symbol, until, exit_reason, now.isoformat())
            )

    def is_in_cooldown(self, symbol: str) -> bool:
        """Return True if the symbol is still in M3 re-entry cooldown."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT cooldown_until FROM portfolio_cooldowns WHERE symbol=?",
                (symbol,)
            ).fetchone()
            if not row:
                return False
            return datetime.now(timezone.utc).isoformat() < row['cooldown_until']

    def get_cooldowns(self) -> List[Dict]:
        """Return all active cooldowns."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_cooldowns ORDER BY exited_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Signal evaluation engine
# ---------------------------------------------------------------------------

class PortfolioManager:
    """
    Evaluates buy/hold/sell signals against live agent scores and
    manages the paper portfolio state in SQLite.
    """

    def __init__(self, db_path: str = "data/portfolio.db"):
        self.db = PortfolioDatabase(db_path)
        # Optional: caller can populate this dict {symbol: pd.Series of daily closes}
        # before calling evaluate() to enable the correlation guard.
        self._price_history_cache: Dict = {}

    def set_price_history(self, price_map: Dict) -> None:
        """Supply recent price history for correlation guard in evaluate().
        price_map: {symbol_str: pd.Series of daily closing prices}
        """
        self._price_history_cache = price_map

    # ── Public API ────────────────────────────────────────────────────────

    def get_config(self) -> PortfolioConfig:
        return self.db.get_config()

    def update_config(self, **kwargs) -> PortfolioConfig:
        return self.db.update_config(**kwargs)

    def get_holdings(self) -> List[Dict]:
        return self.db.get_open_holdings()

    def get_closed_trades(self, limit: int = 50) -> List[Dict]:
        return self.db.get_closed_trades(limit)

    def get_signal_history(self, limit: int = 100) -> List[Dict]:
        return self.db.get_signal_history(limit)

    def get_cooldowns(self) -> List[Dict]:
        """Return all M3 re-entry cooldowns (active and expired)."""
        return self.db.get_cooldowns()

    def manual_buy(self, symbol: str, entry_price: float,
                   entry_score: float) -> Dict:
        config = self.db.get_config()
        return self.db.add_holding(symbol, entry_price, entry_score, config.stop_loss_pct)

    def manual_sell(self, symbol: str, exit_price: float,
                    reason: str = 'manual') -> Optional[Dict]:
        return self.db.close_holding(symbol, exit_price, reason)

    def reset(self):
        self.db.reset_portfolio()

    def evaluate(self, stock_scores: List[Dict],
                 regime: str = 'UNKNOWN') -> EvaluationResult:
        """
        Core signal evaluation — Config A aligned (M1+M3_tight).

        stock_scores: list of score_stock() result dicts (from batch or screener).
        Each dict must have: symbol, composite_score, current_price, recommendation.

        Exit priority order (mirrors backtest run_signal_simulation):
          1. Hard stop-loss: price < entry × (1 - stop_loss_pct)
          2. Profit protection: peak ≥ entry×(1+trigger) AND price < peak×(1-trail)
          3. M1 RS exit: bottom-35th-pct composite score for 3 consecutive evaluations
          4. M3 max-hold: score decay beyond threshold at 12M/18M/24M hurdles
          5. Score exit: score < sell_threshold AND held ≥ min_hold_months
          6. HOLD otherwise

        Entry guards (all must pass):
          - score ≥ effective_buy_threshold (regime-boosted)
          - not in M3 re-entry cooldown
          - sector cap allows
          - regime position count allows
          - not F&O expiry window
        """
        config = self.db.get_config()
        now    = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # ── Build score lookup by clean symbol ────────────────────────────
        score_map: Dict[str, Dict] = {}
        for r in stock_scores:
            sym = _clean_symbol(r.get('symbol', ''))
            if sym:
                score_map[sym] = r

        # ── Derive position cap from market regime (200-DMA gate) ─────────
        # regime string format: "BULL_*" | "BEAR_*" | "SIDEWAYS_*" | "UNKNOWN"
        trend = regime.split('_')[0].upper() if regime else 'SIDEWAYS'
        regime_position_cap = {'BEAR': 4, 'SIDEWAYS': 7, 'BULL': 10}.get(trend, config.max_positions)
        effective_max_positions = min(config.max_positions, regime_position_cap)

        # ── Cross-sectional RS percentile (M1 proxy) ─────────────────────
        # The live composite_score already incorporates momentum (27% weight),
        # so the score percentile is a reliable proxy for price RS rank.
        all_scores = sorted(score_map.values(), key=lambda r: r.get('composite_score', 0))
        rs_threshold_score = 0.0
        if all_scores:
            idx = int(len(all_scores) * config.rs_exit_percentile)
            rs_threshold_score = all_scores[min(idx, len(all_scores)-1)].get('composite_score', 0)

        open_holdings = self.db.get_open_holdings()
        held_symbols  = {_clean_symbol(h['symbol']) for h in open_holdings}
        signals: List[SignalItem] = []

        # Regime-aware sector overrides
        regime_overrides = _get_sector_overrides(regime)
        max_per_sector   = max(1, int(effective_max_positions * config.sector_cap_pct))

        # ── Step 1: evaluate current holdings ─────────────────────────────
        for h in open_holdings:
            sym       = _clean_symbol(h['symbol'])
            analysis  = score_map.get(sym)
            score     = float(analysis['composite_score']) if analysis else 0.0
            price     = float((analysis or {}).get('current_price') or h['entry_price'])
            rec       = (analysis or {}).get('recommendation', '')
            ret       = (price - h['entry_price']) / h['entry_price'] * 100

            # months_held — used by min-hold, M3
            try:
                entry_dt   = datetime.fromisoformat(h['entry_date'].replace('Z', '+00:00'))
                months_held = (now - entry_dt).days / 30.5
            except Exception:
                months_held = 0.0

            # ── Update peak_price high-watermark ─────────────────────────
            current_peak = h.get('peak_price') or h['entry_price']
            if price > current_peak:
                current_peak = price
                self.db.update_peak_price(h['symbol'], current_peak)

            # ── Hard stop-loss (Priority 1) ───────────────────────────────
            hard_stop     = h['entry_price'] * (1.0 - config.stop_loss_pct)
            stop_triggered = price < hard_stop

            # ── Profit protection trailing stop (Priority 2) ──────────────
            # Only activates once peak reached entry × (1 + profit_trigger_pct).
            # Then trails: if price pulls back > profit_trail_pct from peak → exit.
            profit_trail_triggered = (
                current_peak >= h['entry_price'] * (1.0 + config.profit_trigger_pct)
                and price < current_peak * (1.0 - config.profit_trail_pct)
            )

            # ── M1 RS exit strike tracking (Priority 3) ───────────────────
            current_strikes = int(h.get('rs_strike_count') or 0)
            if config.rs_exit_enabled and months_held >= config.min_hold_months:
                # A strike is earned when this stock's score is below the
                # rs_exit_percentile threshold of the full scored universe.
                in_bottom = score <= rs_threshold_score
                new_strikes = (current_strikes + 1) if in_bottom else 0
                if new_strikes != current_strikes:
                    self.db.update_rs_strikes(h['symbol'], new_strikes)
                current_strikes = new_strikes

            rs_exit_triggered = (
                config.rs_exit_enabled
                and months_held >= config.min_hold_months
                and current_strikes >= config.rs_exit_strikes
            )

            # ── M3 max-hold score hurdle (Priority 4) ─────────────────────
            m3_exit_triggered = False
            m3_exit_reason    = ''
            if config.m3_maxhold_enabled and months_held >= 12.0:
                universe_scores = sorted(r.get('composite_score', 0) for r in score_map.values())
                if months_held >= 24.0:
                    idx_75 = int(len(universe_scores) * 0.75)
                    pct_75 = universe_scores[idx_75] if idx_75 < len(universe_scores) else config.sell_threshold
                    if score < pct_75:
                        m3_exit_triggered = True
                        m3_exit_reason    = f'm3_24mo({score:.0f}<75p:{pct_75:.0f})'
                elif months_held >= 18.0:
                    hurdle = max(config.sell_threshold, h['entry_score'] - config.m3_18m_decay)
                    if score < hurdle:
                        m3_exit_triggered = True
                        m3_exit_reason    = f'm3_18mo(score:{score:.0f}<{hurdle:.0f})'
                else:  # 12-18M
                    hurdle = max(config.sell_threshold, h['entry_score'] - config.m3_12m_decay)
                    if score < hurdle:
                        m3_exit_triggered = True
                        m3_exit_reason    = f'm3_12mo(score:{score:.0f}<{hurdle:.0f})'

            # ── Score exit with min-hold guard (Priority 5) ───────────────
            score_exit_triggered = (
                score < config.sell_threshold
                and months_held >= config.min_hold_months
            )

            # ── Update trailing_stop_price (ratchet, informational only) ──
            # We keep the DB trailing stop in sync with the hard stop floor,
            # but the ACTUAL exit decision now uses priority-ordered logic above.
            current_trailing = h.get('trailing_stop_price')
            if price > h['entry_price']:
                candidate = round(price * (1.0 - config.stop_loss_pct), 2)
                if current_trailing is None or candidate > current_trailing:
                    with self.db._conn() as conn:
                        conn.execute(
                            "UPDATE portfolio_holdings SET trailing_stop_price=? WHERE symbol=? AND status='open'",
                            (candidate, h['symbol'])
                        )

            # ── Determine exit signal ─────────────────────────────────────
            if stop_triggered:
                signal = 'SELL_STOP'
                reason = f"Hard stop-loss: ₹{price:.2f} < stop ₹{hard_stop:.2f} ({ret:+.1f}%)"
                self.db.close_holding(h['symbol'], price, 'hard_stop_loss')
                held_symbols.discard(sym)

            elif profit_trail_triggered:
                peak_gain = (current_peak / h['entry_price'] - 1) * 100
                pullback  = (1 - price / current_peak) * 100
                signal = 'SELL_STOP'
                reason = (f"Profit trail: peak +{peak_gain:.0f}%, "
                          f"pulled back -{pullback:.0f}% from peak")
                self.db.close_holding(h['symbol'], price, 'profit_trail_stop')
                held_symbols.discard(sym)

            elif rs_exit_triggered:
                signal = 'SELL_SCORE'
                reason = (f"M1 RS exit: score {score:.0f} in bottom-"
                          f"{config.rs_exit_percentile*100:.0f}th pct for "
                          f"{current_strikes} consecutive evaluations")
                self.db.close_holding(h['symbol'], price, 'm1_rs_exit')
                held_symbols.discard(sym)

            elif m3_exit_triggered:
                signal = 'SELL_SCORE'
                reason = f"M3 max-hold: {m3_exit_reason} ({months_held:.0f}mo held)"
                self.db.close_holding(h['symbol'], price, m3_exit_reason)
                # Set re-entry cooldown so this stock can't immediately re-enter
                self.db.set_cooldown(sym, config.m3_cooldown_months, m3_exit_reason)
                held_symbols.discard(sym)

            elif score_exit_triggered:
                signal = 'SELL_SCORE'
                reason = (f"Score {score:.1f} below sell threshold {config.sell_threshold} "
                          f"({months_held:.0f}mo held)")
                self.db.close_holding(h['symbol'], price, 'score_exit')
                held_symbols.discard(sym)

            elif score < config.sell_threshold and months_held < config.min_hold_months:
                # Score weak but still in min-hold window — surface clearly so user knows
                signal = 'HOLD'
                reason = (f"Score {score:.1f} weak but min-hold active "
                          f"({months_held:.1f}/{config.min_hold_months}mo)")

            else:
                signal = 'HOLD'
                peak_note = f', peak ₹{current_peak:.0f}' if current_peak > h['entry_price'] else ''
                reason = (f"Score {score:.1f} in hold zone "
                          f"(stop ₹{hard_stop:.0f}{peak_note})")

            signals.append(SignalItem(
                symbol=h['symbol'], signal=signal, composite_score=score,
                current_price=price, entry_price=h['entry_price'],
                return_pct=ret, reason=reason, sector=h['sector'],
                recommendation=rec,
            ))

        # ── Step 2: identify BUY candidates ───────────────────────────────
        fno_window = _is_fno_expiry_window()
        if fno_window:
            logger.info("F&O expiry window active — new BUY entries suppressed")

        remaining_holdings = self.db.get_open_holdings()
        sec_counts: Dict[str, int] = {}
        for h in remaining_holdings:
            sec_counts[h['sector']] = sec_counts.get(h['sector'], 0) + 1
        n_held = len(remaining_holdings)

        # Regime-aware entry threshold boost (mirrors backtest)
        regime_threshold_boost = {'BEAR': 10.0, 'SIDEWAYS': 3.0, 'BULL': 0.0}.get(trend, 0.0)
        effective_buy_threshold = config.buy_threshold + regime_threshold_boost

        candidates = sorted(
            [(sym, r) for sym, r in score_map.items()
             if sym not in {_clean_symbol(h['symbol']) for h in remaining_holdings}],
            key=lambda x: x[1].get('composite_score', 0),
            reverse=True
        )

        for sym, analysis in candidates:
            score      = analysis.get('composite_score', 0)
            price      = analysis.get('current_price')
            rec        = analysis.get('recommendation', '')
            sec        = _get_sector(sym)
            native_sym = analysis.get('symbol', sym)

            if score < effective_buy_threshold:
                if score >= config.sell_threshold:
                    buy_reason = f"Score {score:.1f} below threshold {effective_buy_threshold:.0f}"
                    if regime_threshold_boost > 0:
                        buy_reason += f" ({trend} regime +{regime_threshold_boost:.0f}pt boost)"
                    signals.append(SignalItem(
                        symbol=native_sym, signal='WATCH', composite_score=score,
                        current_price=price, entry_price=None, return_pct=None,
                        reason=buy_reason, sector=sec, recommendation=rec,
                    ))
                continue

            if n_held >= effective_max_positions:
                signals.append(SignalItem(
                    symbol=native_sym, signal='WATCH', composite_score=score,
                    current_price=price, entry_price=None, return_pct=None,
                    reason=(f"Regime position cap: {n_held}/{effective_max_positions} "
                            f"({trend} regime)"),
                    sector=sec, recommendation=rec,
                ))
                continue

            # M3 re-entry cooldown check
            if self.db.is_in_cooldown(sym):
                signals.append(SignalItem(
                    symbol=native_sym, signal='WATCH', composite_score=score,
                    current_price=price, entry_price=None, return_pct=None,
                    reason=f"M3 re-entry cooldown active ({config.m3_cooldown_months}mo block)",
                    sector=sec, recommendation=rec,
                ))
                continue

            # Sector cap (regime-aware)
            hard_cap    = regime_overrides.get(sec, max_per_sector)
            general_ok  = sec_counts.get(sec, 0) < max_per_sector
            override_ok = sec_counts.get(sec, 0) < hard_cap
            if not (general_ok and override_ok):
                signals.append(SignalItem(
                    symbol=native_sym, signal='WATCH', composite_score=score,
                    current_price=price, entry_price=None, return_pct=None,
                    reason=f"Sector cap: {sec} ({sec_counts.get(sec,0)} held)",
                    sector=sec, recommendation=rec,
                ))
                continue

            if fno_window:
                signals.append(SignalItem(
                    symbol=native_sym, signal='WATCH', composite_score=score,
                    current_price=price, entry_price=None, return_pct=None,
                    reason=f"F&O expiry window: entry deferred (score {score:.1f} qualifies)",
                    sector=sec, recommendation=rec,
                ))
                continue

            # Correlation guard: avoid adding a stock that moves in lockstep
            # with multiple existing holdings (prevents concentrated macro-regime crashes)
            held_list = [_clean_symbol(h['symbol']) for h in remaining_holdings]
            price_history = getattr(self, '_price_history_cache', {})
            if price_history:
                blocked, corr_reason = _live_correlation_guard(
                    sym, held_list,
                    price_history_fn=lambda s: price_history.get(s),
                )
                if blocked:
                    signals.append(SignalItem(
                        symbol=native_sym, signal='WATCH', composite_score=score,
                        current_price=price, entry_price=None, return_pct=None,
                        reason=corr_reason, sector=sec, recommendation=rec,
                    ))
                    continue

            # ── BUY ───────────────────────────────────────────────────────
            entry_price = price or 0.0
            atr_stop    = (analysis.get('trading_levels') or {}).get('stop_loss')
            if entry_price > 0:
                self.db.add_holding(native_sym, entry_price, score,
                                    config.stop_loss_pct, initial_stop_price=atr_stop)
            signals.append(SignalItem(
                symbol=native_sym, signal='BUY', composite_score=score,
                current_price=price, entry_price=None, return_pct=None,
                reason=f"Score {score:.1f} ≥ threshold {effective_buy_threshold:.0f}",
                sector=sec, recommendation=rec,
            ))
            sec_counts[sec] = sec_counts.get(sec, 0) + 1
            n_held += 1

        # ── Log signals & compute P&L ─────────────────────────────────────
        self.db.log_signals(signals, regime, now_iso)

        final_holdings = self.db.get_open_holdings()
        total_ret = 0.0
        for h in final_holdings:
            sym   = _clean_symbol(h['symbol'])
            price = (score_map.get(sym) or {}).get('current_price') or h['entry_price']
            total_ret += (price - h['entry_price']) / h['entry_price'] * 100
        avg_ret = total_ret / len(final_holdings) if final_holdings else 0.0

        buys    = [s for s in signals if s.signal == 'BUY']
        sells   = [s for s in signals if s.signal in ('SELL_SCORE', 'SELL_STOP')]
        holds   = [s for s in signals if s.signal == 'HOLD']
        watches = [s for s in signals if s.signal == 'WATCH']

        return EvaluationResult(
            evaluated_at=now_iso,
            n_holdings=len(final_holdings),
            signals=signals,
            buys=buys, sells=sells, holds=holds, watches=watches,
            portfolio_return_pct=avg_ret,
            regime=regime,
        )

    def get_performance_summary(self, score_map: Optional[Dict[str, Dict]] = None) -> Dict:
        """Return summary P&L for open + closed trades."""
        holdings = self.db.get_open_holdings()
        closed   = self.db.get_closed_trades(limit=500)

        open_returns = []
        for h in holdings:
            sym = _clean_symbol(h['symbol'])
            if score_map:
                price = (score_map.get(sym) or {}).get('current_price') or h['entry_price']
            else:
                price = h['entry_price']
            ret = (price - h['entry_price']) / h['entry_price'] * 100
            open_returns.append(ret)

        closed_returns = [t['return_pct'] for t in closed]

        all_returns = open_returns + closed_returns
        winners = [r for r in all_returns if r > 0]
        losers  = [r for r in all_returns if r <= 0]

        return {
            'n_open':           len(holdings),
            'n_closed':         len(closed),
            'avg_open_return':  sum(open_returns) / len(open_returns) if open_returns else 0,
            'avg_closed_return':sum(closed_returns) / len(closed_returns) if closed_returns else 0,
            'total_trades':     len(all_returns),
            'win_rate':         len(winners) / len(all_returns) if all_returns else 0,
            'avg_win':          sum(winners) / len(winners) if winners else 0,
            'avg_loss':         sum(losers) / len(losers) if losers else 0,
            'best_trade':       max(all_returns) if all_returns else 0,
            'worst_trade':      min(all_returns) if all_returns else 0,
        }
