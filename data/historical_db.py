"""
Historical Database Manager for AI Hedge Fund System

Manages SQLite database for tracking:
- Stock analysis history
- Market regime changes
- User watchlists
- User search behavior

Tables:
1. stock_analyses - Historical stock scores and recommendations
2. market_regimes - Market regime timeline
3. watchlist - User watchlists
4. user_searches - User behavior tracking
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path

from core.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class HistoricalDatabase:
    """Manages historical data storage in SQLite"""

    def __init__(self, db_path: str = "data/analysis_history.db"):
        """
        Initialize database connection and create tables if needed

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._create_tables()
        self._create_indexes()
        logger.info(f"Historical database initialized at {db_path}")

    @contextmanager
    def _get_connection(self):
        """
        Context manager with proper transaction support and error handling

        Provides ACID compliance with automatic commit/rollback
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)

            # Enable Write-Ahead Logging for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")

            # Faster with WAL mode
            conn.execute("PRAGMA synchronous=NORMAL")

            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")

            # Enable column access by name
            conn.row_factory = sqlite3.Row

            yield conn

            # Commit on success
            conn.commit()
            logger.debug("Database transaction committed")

        except sqlite3.IntegrityError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database integrity error: {e}", exc_info=True)
            raise DatabaseException(f"Data integrity violation: {e}") from e

        except sqlite3.OperationalError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operational error: {e}", exc_info=True)
            raise DatabaseException(f"Database operation failed: {e}") from e

        except sqlite3.DatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise DatabaseException(f"Database error: {e}") from e

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected database error: {e}", exc_info=True)
            raise DatabaseException(f"Unexpected database error: {e}") from e

        finally:
            if conn:
                conn.close()

    def _create_tables(self):
        """Create database tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Stock analyses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    composite_score REAL NOT NULL,
                    recommendation TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    agent_scores_json TEXT NOT NULL,
                    weights_json TEXT NOT NULL,
                    market_regime_json TEXT,
                    price REAL,
                    sector TEXT,
                    narrative TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Market regimes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_regimes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    regime TEXT NOT NULL,
                    trend TEXT NOT NULL,
                    volatility TEXT NOT NULL,
                    weights_json TEXT NOT NULL,
                    metrics_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Watchlist table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    symbol TEXT NOT NULL,
                    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    UNIQUE(user_id, symbol)
                )
            """)

            # User searches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'manual',
                    user_id TEXT DEFAULT 'default'
                )
            """)

            logger.info("Database tables created successfully")

    def _create_indexes(self):
        """Create database indexes for performance"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Indexes for stock_analyses
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_analyses_symbol
                ON stock_analyses(symbol)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_analyses_timestamp
                ON stock_analyses(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_analyses_composite_score
                ON stock_analyses(composite_score DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_analyses_symbol_timestamp
                ON stock_analyses(symbol, timestamp DESC)
            """)

            # Indexes for market_regimes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_regimes_timestamp
                ON market_regimes(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_regimes_regime
                ON market_regimes(regime)
            """)

            # Indexes for watchlist
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlist_user_id
                ON watchlist(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlist_symbol
                ON watchlist(symbol)
            """)

            # Indexes for user_searches
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_searches_timestamp
                ON user_searches(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_searches_symbol
                ON user_searches(symbol)
            """)

            logger.info("Database indexes created successfully")

    # ========================================================================
    # Stock Analysis CRUD Operations
    # ========================================================================

    def save_stock_analysis(
        self,
        symbol: str,
        composite_score: float,
        recommendation: str,
        confidence: float,
        agent_scores: Dict[str, float],
        weights: Dict[str, float],
        market_regime: Optional[Dict[str, Any]] = None,
        price: Optional[float] = None,
        sector: Optional[str] = None,
        narrative: Optional[str] = None
    ) -> int:
        """
        Save stock analysis to database

        Args:
            symbol: Stock symbol
            composite_score: Overall composite score
            recommendation: Investment recommendation
            confidence: Confidence level (0-1)
            agent_scores: Dictionary of agent scores
            weights: Dictionary of agent weights
            market_regime: Market regime data (optional)
            price: Current stock price (optional)
            sector: Stock sector (optional)
            narrative: Investment narrative (optional)

        Returns:
            ID of inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO stock_analyses (
                    symbol, composite_score, recommendation, confidence,
                    agent_scores_json, weights_json, market_regime_json,
                    price, sector, narrative
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol.upper(),
                composite_score,
                recommendation,
                confidence,
                json.dumps(agent_scores),
                json.dumps(weights),
                json.dumps(market_regime) if market_regime else None,
                price,
                sector,
                narrative
            ))
            return cursor.lastrowid

    def get_stock_history(
        self,
        symbol: str,
        days: int = 30,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical analysis for a stock

        Args:
            symbol: Stock symbol
            days: Number of days to look back
            limit: Maximum number of records to return

        Returns:
            List of historical analyses
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)

            query = """
                SELECT * FROM stock_analyses
                WHERE symbol = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, (symbol.upper(), cutoff_date))
            rows = cursor.fetchall()

            return [self._parse_stock_analysis_row(row) for row in rows]

    def get_latest_stock_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get most recent analysis for a stock

        Args:
            symbol: Stock symbol

        Returns:
            Latest analysis or None
        """
        history = self.get_stock_history(symbol, days=365, limit=1)
        return history[0] if history else None

    def get_top_performers(
        self,
        days: int = 7,
        limit: int = 20,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top performing stocks by composite score

        Args:
            days: Number of days to look back
            limit: Maximum number of stocks to return
            min_score: Minimum composite score filter

        Returns:
            List of top performing stocks
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)

            # Get latest analysis for each symbol in the time window
            query = """
                WITH LatestAnalyses AS (
                    SELECT symbol, MAX(timestamp) as max_timestamp
                    FROM stock_analyses
                    WHERE timestamp >= ?
                    GROUP BY symbol
                )
                SELECT sa.* FROM stock_analyses sa
                INNER JOIN LatestAnalyses la
                    ON sa.symbol = la.symbol AND sa.timestamp = la.max_timestamp
            """

            if min_score:
                query += f" WHERE sa.composite_score >= {min_score}"

            query += " ORDER BY sa.composite_score DESC"
            query += f" LIMIT {limit}"

            cursor.execute(query, (cutoff_date,))
            rows = cursor.fetchall()

            return [self._parse_stock_analysis_row(row) for row in rows]

    def get_score_trend(
        self,
        symbol: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate score trend for a stock

        Args:
            symbol: Stock symbol
            days: Number of days to analyze

        Returns:
            Trend statistics (avg, min, max, direction)
        """
        history = self.get_stock_history(symbol, days=days)

        if not history or len(history) < 2:
            return {
                'trend': 'INSUFFICIENT_DATA',
                'avg_score': None,
                'min_score': None,
                'max_score': None,
                'change': None
            }

        scores = [h['composite_score'] for h in history]
        recent_score = history[0]['composite_score']
        older_score = history[-1]['composite_score']

        change = recent_score - older_score

        if change > 5:
            trend = 'IMPROVING'
        elif change < -5:
            trend = 'DECLINING'
        else:
            trend = 'STABLE'

        return {
            'trend': trend,
            'avg_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'change': change,
            'data_points': len(history)
        }

    def _parse_stock_analysis_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Parse database row into dictionary"""
        return {
            'id': row['id'],
            'symbol': row['symbol'],
            'timestamp': row['timestamp'],
            'composite_score': row['composite_score'],
            'recommendation': row['recommendation'],
            'confidence': row['confidence'],
            'agent_scores': json.loads(row['agent_scores_json']),
            'weights': json.loads(row['weights_json']),
            'market_regime': json.loads(row['market_regime_json']) if row['market_regime_json'] else None,
            'price': row['price'],
            'sector': row['sector'],
            'narrative': row['narrative'],
            'created_at': row['created_at']
        }

    # ========================================================================
    # Market Regime CRUD Operations
    # ========================================================================

    def save_market_regime(
        self,
        regime: str,
        trend: str,
        volatility: str,
        weights: Dict[str, float],
        metrics: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save market regime to database

        Args:
            regime: Market regime (BULL, BEAR, SIDEWAYS)
            trend: Trend direction
            volatility: Volatility level
            weights: Agent weights for this regime
            metrics: Additional metrics

        Returns:
            ID of inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_regimes (
                    regime, trend, volatility, weights_json, metrics_json
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                regime,
                trend,
                volatility,
                json.dumps(weights),
                json.dumps(metrics) if metrics else None
            ))
            return cursor.lastrowid

    def get_regime_history(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get market regime history

        Args:
            days: Number of days to look back

        Returns:
            List of market regime records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)

            cursor.execute("""
                SELECT * FROM market_regimes
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (cutoff_date,))

            rows = cursor.fetchall()

            return [{
                'id': row['id'],
                'timestamp': row['timestamp'],
                'regime': row['regime'],
                'trend': row['trend'],
                'volatility': row['volatility'],
                'weights': json.loads(row['weights_json']),
                'metrics': json.loads(row['metrics_json']) if row['metrics_json'] else None,
                'created_at': row['created_at']
            } for row in rows]

    def get_current_regime(self) -> Optional[Dict[str, Any]]:
        """Get most recent market regime"""
        history = self.get_regime_history(days=7)
        return history[0] if history else None

    # ========================================================================
    # Watchlist CRUD Operations
    # ========================================================================

    def add_to_watchlist(
        self,
        symbol: str,
        notes: Optional[str] = None,
        user_id: str = 'default'
    ) -> bool:
        """
        Add stock to watchlist

        Args:
            symbol: Stock symbol
            notes: Optional notes
            user_id: User identifier

        Returns:
            True if added, False if already exists
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO watchlist (user_id, symbol, notes)
                    VALUES (?, ?, ?)
                """, (user_id, symbol.upper(), notes))
                return True
        except (sqlite3.IntegrityError, DatabaseException):
            logger.warning(f"Stock {symbol} already in watchlist for user {user_id}")
            return False

    def remove_from_watchlist(
        self,
        symbol: str,
        user_id: str = 'default'
    ) -> bool:
        """
        Remove stock from watchlist

        Args:
            symbol: Stock symbol
            user_id: User identifier

        Returns:
            True if removed, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM watchlist
                WHERE user_id = ? AND symbol = ?
            """, (user_id, symbol.upper()))
            return cursor.rowcount > 0

    def get_watchlist(self, user_id: str = 'default') -> List[Dict[str, Any]]:
        """
        Get user's watchlist

        Args:
            user_id: User identifier

        Returns:
            List of watchlist stocks
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watchlist
                WHERE user_id = ?
                ORDER BY added_at DESC
            """, (user_id,))

            rows = cursor.fetchall()

            return [{
                'id': row['id'],
                'symbol': row['symbol'],
                'added_at': row['added_at'],
                'notes': row['notes']
            } for row in rows]

    def is_in_watchlist(
        self,
        symbol: str,
        user_id: str = 'default'
    ) -> bool:
        """Check if stock is in watchlist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM watchlist
                WHERE user_id = ? AND symbol = ?
            """, (user_id, symbol.upper()))
            return cursor.fetchone()[0] > 0

    # ========================================================================
    # User Search Tracking
    # ========================================================================

    def track_search(
        self,
        symbol: str,
        source: str = 'manual',
        user_id: str = 'default'
    ):
        """Track user search behavior"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_searches (symbol, source, user_id)
                VALUES (?, ?, ?)
            """, (symbol.upper(), source, user_id))

    def get_recent_searches(
        self,
        user_id: str = 'default',
        limit: int = 10
    ) -> List[str]:
        """Get recent search symbols"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT symbol FROM user_searches
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            return [row['symbol'] for row in cursor.fetchall()]

    # ========================================================================
    # Data Maintenance
    # ========================================================================

    def cleanup_old_data(self, retention_days: int = 365):
        """
        Remove data older than retention period

        Args:
            retention_days: Days to retain data
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clean stock analyses
            cursor.execute("""
                DELETE FROM stock_analyses
                WHERE timestamp < ?
            """, (cutoff_date,))
            analyses_deleted = cursor.rowcount

            # Clean market regimes
            cursor.execute("""
                DELETE FROM market_regimes
                WHERE timestamp < ?
            """, (cutoff_date,))
            regimes_deleted = cursor.rowcount

            # Clean user searches (keep only 90 days)
            search_cutoff = datetime.now() - timedelta(days=90)
            cursor.execute("""
                DELETE FROM user_searches
                WHERE timestamp < ?
            """, (search_cutoff,))
            searches_deleted = cursor.rowcount

            logger.info(
                f"Cleaned up old data: {analyses_deleted} analyses, "
                f"{regimes_deleted} regimes, {searches_deleted} searches"
            )

            # Vacuum database to reclaim space
            cursor.execute("VACUUM")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Count records in each table
            for table in ['stock_analyses', 'market_regimes', 'watchlist', 'user_searches']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f'{table}_count'] = cursor.fetchone()[0]

            # Get database file size
            db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB
            stats['database_size_mb'] = round(db_size, 2)

            # Get date range
            cursor.execute("""
                SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest
                FROM stock_analyses
            """)
            row = cursor.fetchone()
            stats['oldest_analysis'] = row['oldest']
            stats['newest_analysis'] = row['newest']

            return stats

    def backup_database(self, backup_path: str):
        """
        Create database backup

        Args:
            backup_path: Path for backup file
        """
        import shutil
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
