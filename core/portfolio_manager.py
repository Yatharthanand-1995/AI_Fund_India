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


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PortfolioConfig:
    buy_threshold: float = 65.0
    sell_threshold: float = 50.0
    stop_loss_pct: float = 0.10
    max_positions: int = 10
    sector_cap_pct: float = 0.30
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
                    buy_threshold REAL DEFAULT 65.0,
                    sell_threshold REAL DEFAULT 50.0,
                    stop_loss_pct REAL DEFAULT 0.10,
                    max_positions INTEGER DEFAULT 10,
                    sector_cap_pct REAL DEFAULT 0.30,
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
                    trailing_stop_price REAL
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
            # Migration: add trailing_stop_price if it doesn't exist yet
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(portfolio_holdings)"
            ).fetchall()]
            if 'trailing_stop_price' not in cols:
                conn.execute(
                    "ALTER TABLE portfolio_holdings ADD COLUMN trailing_stop_price REAL"
                )
                logger.info("Migrated portfolio_holdings: added trailing_stop_price column")

    # ── Config ────────────────────────────────────────────────────────────

    def get_config(self) -> PortfolioConfig:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM portfolio_config WHERE id=1").fetchone()
            if row:
                return PortfolioConfig(
                    buy_threshold=row['buy_threshold'],
                    sell_threshold=row['sell_threshold'],
                    stop_loss_pct=row['stop_loss_pct'],
                    max_positions=row['max_positions'],
                    sector_cap_pct=row['sector_cap_pct'],
                    updated_at=row['updated_at'] or '',
                )
            return PortfolioConfig()

    def update_config(self, **kwargs) -> PortfolioConfig:
        allowed = {'buy_threshold', 'sell_threshold', 'stop_loss_pct',
                   'max_positions', 'sector_cap_pct'}
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
        Core signal evaluation.

        stock_scores: list of score_stock() result dicts (from batch or screener).
        Each dict must have: symbol, composite_score, current_price, recommendation.

        Returns EvaluationResult with buy/hold/sell signals and applies
        exits and entries to the DB automatically.
        """
        config = self.db.get_config()
        now = datetime.now(timezone.utc).isoformat()

        # Build lookup by clean symbol
        score_map: Dict[str, Dict] = {}
        for r in stock_scores:
            sym = _clean_symbol(r.get('symbol', ''))
            if sym:
                score_map[sym] = r

        open_holdings = self.db.get_open_holdings()
        held_symbols = {_clean_symbol(h['symbol']) for h in open_holdings}

        signals: List[SignalItem] = []
        max_per_sector = max(1, int(config.max_positions * config.sector_cap_pct))

        # Regime-aware sector overrides (relax in bull, tighten cyclicals in bear)
        regime_overrides = _get_sector_overrides(regime)

        # ── Step 1: evaluate current holdings → HOLD / SELL ───────────────
        for h in open_holdings:
            sym = _clean_symbol(h['symbol'])
            analysis = score_map.get(sym)
            score = analysis['composite_score'] if analysis else 0.0
            price = (analysis or {}).get('current_price') or h['entry_price']
            rec   = (analysis or {}).get('recommendation', '')
            ret   = (price - h['entry_price']) / h['entry_price'] * 100

            # Update trailing stop: ratchet up when price moves in our favour
            current_trailing = h.get('trailing_stop_price')
            new_trailing = current_trailing
            if price > h['entry_price'] and price > 0:
                candidate = round(price * (1.0 - config.stop_loss_pct), 2)
                if current_trailing is None or candidate > current_trailing:
                    new_trailing = candidate
                    with self.db._conn() as conn:
                        conn.execute(
                            "UPDATE portfolio_holdings SET trailing_stop_price=? WHERE symbol=? AND status='open'",
                            (new_trailing, h['symbol'])
                        )

            # Determine effective stop level (trailing or fixed, whichever is higher)
            effective_stop = new_trailing if new_trailing is not None else (h['entry_price'] * (1.0 - config.stop_loss_pct))
            trailing_triggered = price < effective_stop

            if trailing_triggered:
                stop_type = 'trailing' if (new_trailing is not None and new_trailing > h['entry_price'] * (1.0 - config.stop_loss_pct)) else 'fixed'
                signal = 'SELL_STOP'
                reason = f"{stop_type.title()} stop-loss: ₹{price:.2f} < stop ₹{effective_stop:.2f} ({ret:+.1f}% from entry)"
                self.db.close_holding(h['symbol'], price, f'{stop_type}_stop_loss')
                held_symbols.discard(sym)
            elif score < config.sell_threshold:
                signal = 'SELL_SCORE'
                reason = f"Score {score:.1f} below sell threshold {config.sell_threshold}"
                self.db.close_holding(h['symbol'], price, 'score_exit')
                held_symbols.discard(sym)
            else:
                signal = 'HOLD'
                reason = f"Score {score:.1f} in hold zone (stop: ₹{effective_stop:.2f})"

            signals.append(SignalItem(
                symbol=h['symbol'], signal=signal, composite_score=score,
                current_price=price, entry_price=h['entry_price'],
                return_pct=ret, reason=reason, sector=h['sector'],
                recommendation=rec,
            ))

        # ── Step 2: identify BUY candidates ───────────────────────────────
        # F&O expiry guard: suppress new entries in the 2 days before/on last Thursday
        fno_window = _is_fno_expiry_window()
        if fno_window:
            logger.info("F&O expiry window active — new BUY entries suppressed (exits still allowed)")

        # Sector counts from remaining holdings (after exits)
        remaining_holdings = self.db.get_open_holdings()
        sec_counts: Dict[str, int] = {}
        for h in remaining_holdings:
            sec_counts[h['sector']] = sec_counts.get(h['sector'], 0) + 1
        n_held = len(remaining_holdings)

        # Sort all universe stocks by score descending
        candidates = sorted(
            [(sym, r) for sym, r in score_map.items()
             if sym not in {_clean_symbol(h['symbol']) for h in remaining_holdings}],
            key=lambda x: x[1].get('composite_score', 0),
            reverse=True
        )

        for sym, analysis in candidates:
            score = analysis.get('composite_score', 0)
            price = analysis.get('current_price')
            rec   = analysis.get('recommendation', '')
            sec   = _get_sector(sym)
            native_sym = analysis.get('symbol', sym)

            if score < config.buy_threshold:
                # Below buy threshold — surface as WATCH if score is respectable
                if score >= config.sell_threshold:
                    signals.append(SignalItem(
                        symbol=native_sym, signal='WATCH', composite_score=score,
                        current_price=price, entry_price=None, return_pct=None,
                        reason=f"Score {score:.1f} below buy threshold {config.buy_threshold}",
                        sector=sec, recommendation=rec,
                    ))
                continue

            if n_held >= config.max_positions:
                # At capacity — surface as WATCH
                signals.append(SignalItem(
                    symbol=native_sym, signal='WATCH', composite_score=score,
                    current_price=price, entry_price=None, return_pct=None,
                    reason=f"At capacity ({config.max_positions} positions)",
                    sector=sec, recommendation=rec,
                ))
                continue

            # Sector cap check (regime-aware overrides applied)
            hard_cap = regime_overrides.get(sec, max_per_sector)
            general_ok  = sec_counts.get(sec, 0) < max_per_sector
            override_ok = sec_counts.get(sec, 0) < hard_cap
            if not (general_ok and override_ok):
                signals.append(SignalItem(
                    symbol=native_sym, signal='WATCH', composite_score=score,
                    current_price=price, entry_price=None, return_pct=None,
                    reason=f"Sector cap reached: {sec} ({sec_counts.get(sec,0)} held)",
                    sector=sec, recommendation=rec,
                ))
                continue

            # F&O expiry window — defer to WATCH, do not execute entry
            if fno_window:
                signals.append(SignalItem(
                    symbol=native_sym, signal='WATCH', composite_score=score,
                    current_price=price, entry_price=None, return_pct=None,
                    reason=f"F&O expiry window: entry deferred (score {score:.1f} qualifies)",
                    sector=sec, recommendation=rec,
                ))
                continue

            # BUY — use ATR-based stop from scorer's trading_levels when available
            entry_price = price or 0.0
            atr_stop = (analysis.get('trading_levels') or {}).get('stop_loss')
            if entry_price > 0:
                self.db.add_holding(
                    native_sym, entry_price, score,
                    config.stop_loss_pct,
                    initial_stop_price=atr_stop,
                )
            signals.append(SignalItem(
                symbol=native_sym, signal='BUY', composite_score=score,
                current_price=price, entry_price=None, return_pct=None,
                reason=f"Score {score:.1f} ≥ buy threshold {config.buy_threshold}",
                sector=sec, recommendation=rec,
            ))
            sec_counts[sec] = sec_counts.get(sec, 0) + 1
            n_held += 1

        # ── Log signals ───────────────────────────────────────────────────
        self.db.log_signals(signals, regime, now)

        # ── Compute portfolio P&L ─────────────────────────────────────────
        final_holdings = self.db.get_open_holdings()
        total_ret = 0.0
        for h in final_holdings:
            sym = _clean_symbol(h['symbol'])
            price = (score_map.get(sym) or {}).get('current_price') or h['entry_price']
            total_ret += (price - h['entry_price']) / h['entry_price'] * 100
        avg_ret = total_ret / len(final_holdings) if final_holdings else 0.0

        # Partition signals for the response
        buys   = [s for s in signals if s.signal == 'BUY']
        sells  = [s for s in signals if s.signal in ('SELL_SCORE', 'SELL_STOP')]
        holds  = [s for s in signals if s.signal == 'HOLD']
        watches = [s for s in signals if s.signal == 'WATCH']

        return EvaluationResult(
            evaluated_at=now,
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
