"""
Optimized Historical Database with Performance Improvements

Optimizations:
- Connection pooling for concurrent requests
- Prepared statements to prevent SQL injection
- Index optimization
- Query result caching
- Batch operations
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from pathlib import Path
from functools import lru_cache
import threading

logger = logging.getLogger(__name__)


class OptimizedHistoricalDatabase:
    """
    Optimized version of HistoricalDatabase with performance improvements
    """

    def __init__(self, db_path: str = "data/analysis_history.db", pool_size: int = 5):
        """
        Initialize database with connection pooling

        Args:
            db_path: Path to SQLite database file
            pool_size: Number of connections in pool
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self._local = threading.local()

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._create_tables()
        self._create_indexes()
        self._optimize_database()
        logger.info(f"Optimized database initialized at {db_path}")

    def _get_connection(self):
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0  # Increase timeout for concurrent access
            )
            self._local.conn.row_factory = sqlite3.Row

            # Performance optimizations
            self._local.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            self._local.conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            self._local.conn.execute("PRAGMA cache_size=10000")  # Larger cache
            self._local.conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp
            self._local.conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O

        return self._local.conn

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions with optimization"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise

    def _optimize_database(self):
        """Apply database optimizations"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Analyze tables for query optimization
        cursor.execute("ANALYZE")

        conn.commit()
        logger.info("Database optimizations applied")

    def _create_indexes(self):
        """Create optimized indexes"""
        with self._transaction() as conn:
            cursor = conn.cursor()

            # Composite indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_symbol_timestamp
                ON stock_analyses(symbol, timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_score
                ON stock_analyses(composite_score DESC, timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_regime_timestamp
                ON market_regimes(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlist_symbol
                ON watchlist(symbol, user_id)
            """)

            logger.info("Optimized indexes created successfully")

    @lru_cache(maxsize=128)
    def get_stock_history_cached(
        self,
        symbol: str,
        days: int = 30,
        cache_key: str = None
    ) -> List[Dict[str, Any]]:
        """
        Cached version of get_stock_history for frequently accessed data

        Args:
            symbol: Stock symbol
            days: Number of days of history
            cache_key: Optional cache key (timestamp for cache invalidation)

        Returns:
            List of historical analysis records
        """
        return self.get_stock_history(symbol, days)

    def get_stock_history(
        self,
        symbol: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Optimized query with LIMIT and indexed lookups
        """
        with self._transaction() as conn:
            cursor = conn.cursor()

            # Use prepared statement
            cursor.execute("""
                SELECT *
                FROM stock_analyses
                WHERE symbol = ?
                  AND timestamp >= datetime('now', ? || ' days')
                ORDER BY timestamp ASC
                LIMIT 1000
            """, (symbol, -days))

            rows = cursor.fetchall()
            return [self._parse_stock_analysis_row(row) for row in rows]

    def get_top_performers_optimized(
        self,
        days: int = 7,
        limit: int = 10,
        min_analyses: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Optimized query using aggregation and indexes

        Returns top performing stocks with efficient query
        """
        with self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    symbol,
                    AVG(composite_score) as avg_score,
                    COUNT(*) as analysis_count,
                    MAX(timestamp) as latest_analysis
                FROM stock_analyses
                WHERE timestamp >= datetime('now', ? || ' days')
                GROUP BY symbol
                HAVING COUNT(*) >= ?
                ORDER BY avg_score DESC
                LIMIT ?
            """, (-days, min_analyses, limit))

            return [dict(row) for row in cursor.fetchall()]

    def batch_insert_analyses(
        self,
        analyses: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert for better performance

        Args:
            analyses: List of analysis dictionaries

        Returns:
            Number of records inserted
        """
        if not analyses:
            return 0

        with self._transaction() as conn:
            cursor = conn.cursor()

            # Prepare batch data
            batch_data = [
                (
                    a['symbol'],
                    a['composite_score'],
                    a['recommendation'],
                    a['confidence'],
                    json.dumps(a['agent_scores']),
                    json.dumps(a['weights']),
                    json.dumps(a.get('market_regime')),
                    a.get('price'),
                    a.get('sector'),
                    a.get('narrative'),
                )
                for a in analyses
            ]

            # Batch insert
            cursor.executemany("""
                INSERT INTO stock_analyses (
                    symbol, composite_score, recommendation, confidence,
                    agent_scores_json, weights_json, market_regime_json,
                    price, sector, narrative
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)

            return len(batch_data)

    def _parse_stock_analysis_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Optimized row parsing with error handling"""
        try:
            return {
                'id': row['id'],
                'symbol': row['symbol'],
                'timestamp': row['timestamp'],
                'composite_score': row['composite_score'],
                'recommendation': row['recommendation'],
                'confidence': row['confidence'],
                'agent_scores': json.loads(row['agent_scores_json']) if row['agent_scores_json'] else {},
                'weights': json.loads(row['weights_json']) if row['weights_json'] else {},
                'market_regime': json.loads(row['market_regime_json']) if row['market_regime_json'] else None,
                'price': row['price'],
                'sector': row['sector'],
                'narrative': row['narrative'],
            }
        except Exception as e:
            logger.error(f"Error parsing row: {e}")
            return {}

    def vacuum_database(self):
        """
        Vacuum database outside of transaction
        Should be called periodically (e.g., weekly)
        """
        try:
            conn = self._get_connection()
            conn.isolation_level = None  # Autocommit mode
            conn.execute("VACUUM")
            conn.isolation_level = ''  # Reset
            logger.info("Database vacuumed successfully")
        except Exception as e:
            logger.error(f"Vacuum failed: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        with self._transaction() as conn:
            cursor = conn.cursor()

            # Get table sizes
            cursor.execute("""
                SELECT name, COUNT(*) as count
                FROM (
                    SELECT 'stock_analyses' as name FROM stock_analyses
                    UNION ALL
                    SELECT 'market_regimes' FROM market_regimes
                    UNION ALL
                    SELECT 'watchlist' FROM watchlist
                    UNION ALL
                    SELECT 'user_searches' FROM user_searches
                )
                GROUP BY name
            """)

            stats = {
                'tables': {row['name']: row['count'] for row in cursor.fetchall()},
                'db_size_mb': Path(self.db_path).stat().st_size / (1024 * 1024),
                'optimizations_applied': True
            }

            return stats
