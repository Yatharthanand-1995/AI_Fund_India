"""
Backtest Database - Store and retrieve backtest runs and results

This module provides:
1. Persistent storage for backtest runs
2. Historical analysis capabilities
3. Run comparison functionality
4. Performance tracking over time
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

from core.backtester import BacktestResult, BacktestSummary

logger = logging.getLogger(__name__)


@dataclass
class BacktestRun:
    """Complete backtest run metadata and results"""
    run_id: str
    name: str
    start_date: str  # ISO format
    end_date: str
    symbols: List[str]
    frequency: str
    created_at: str
    total_signals: int
    summary: Dict  # BacktestSummary as dict
    metadata: Dict  # Config, params, etc.


class BacktestDatabase:
    """
    SQLite database for storing backtest results

    Usage:
        db = BacktestDatabase()
        run_id = db.save_backtest_run(name, results, summary, analysis)
        run = db.get_backtest_run(run_id)
        all_runs = db.list_backtest_runs()
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file (default: data/backtest_history.db)
        """
        if db_path is None:
            # Default to data directory in project root
            project_root = Path(__file__).parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'backtest_history.db')

        self.db_path = db_path
        self._create_tables()
        logger.info(f"BacktestDatabase initialized at {db_path}")

    def _create_tables(self):
        """Create database schema if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Backtest runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_runs (
                run_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                symbols TEXT NOT NULL,  -- JSON array
                frequency TEXT NOT NULL,
                created_at TEXT NOT NULL,
                total_signals INTEGER NOT NULL,
                summary TEXT NOT NULL,  -- JSON
                metadata TEXT  -- JSON
            )
        """)

        # Individual backtest signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_signals (
                signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                composite_score REAL NOT NULL,
                confidence REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                forward_return_1m REAL,
                forward_return_3m REAL,
                forward_return_6m REAL,
                benchmark_return_1m REAL,
                benchmark_return_3m REAL,
                benchmark_return_6m REAL,
                alpha_1m REAL,
                alpha_3m REAL,
                alpha_6m REAL,
                agent_scores TEXT NOT NULL,  -- JSON
                market_regime TEXT,
                FOREIGN KEY (run_id) REFERENCES backtest_runs(run_id)
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_run_id
            ON backtest_signals(run_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_symbol
            ON backtest_signals(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_date
            ON backtest_signals(date)
        """)

        conn.commit()
        conn.close()

        logger.info("Database schema initialized")

    def save_backtest_run(
        self,
        name: str,
        results: List[BacktestResult],
        summary: BacktestSummary,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        frequency: str = 'monthly',
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Save a complete backtest run to database

        Args:
            name: Human-readable name for the run
            results: List of BacktestResult objects
            summary: BacktestSummary object
            start_date: Backtest start date
            end_date: Backtest end date
            symbols: List of symbols tested
            frequency: Rebalance frequency
            metadata: Additional metadata (config, params, etc.)

        Returns:
            run_id: UUID for the saved run
        """
        run_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        # Convert summary to dict (with numpy type conversion)
        def convert_to_python_type(obj):
            """Convert numpy types to Python types for JSON serialization"""
            import numpy as np
            if isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
                return int(obj)
            elif isinstance(obj, (np.float64, np.float32, np.float16)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_python_type(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_python_type(item) for item in obj]
            return obj

        summary_dict = {
            'total_signals': int(summary.total_signals),
            'total_buys': int(summary.total_buys),
            'total_sells': int(summary.total_sells),
            'hit_rate_1m': float(summary.hit_rate_1m),
            'hit_rate_3m': float(summary.hit_rate_3m),
            'hit_rate_6m': float(summary.hit_rate_6m),
            'avg_return_1m': float(summary.avg_return_1m),
            'avg_return_3m': float(summary.avg_return_3m),
            'avg_return_6m': float(summary.avg_return_6m),
            'avg_alpha_1m': float(summary.avg_alpha_1m),
            'avg_alpha_3m': float(summary.avg_alpha_3m),
            'avg_alpha_6m': float(summary.avg_alpha_6m),
            'sharpe_ratio_1m': float(summary.sharpe_ratio_1m),
            'sharpe_ratio_3m': float(summary.sharpe_ratio_3m),
            'sharpe_ratio_6m': float(summary.sharpe_ratio_6m),
            'max_drawdown': float(summary.max_drawdown),
            'win_rate': float(summary.win_rate),
            'avg_win': float(summary.avg_win),
            'avg_loss': float(summary.avg_loss),
            'win_loss_ratio': float(summary.win_loss_ratio),
            'performance_by_recommendation': convert_to_python_type(summary.performance_by_recommendation),
            'agent_correlations': convert_to_python_type(summary.agent_correlations),
            'performance_by_regime': convert_to_python_type(summary.performance_by_regime)
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert backtest run
            cursor.execute("""
                INSERT INTO backtest_runs
                (run_id, name, start_date, end_date, symbols, frequency, created_at, total_signals, summary, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                name,
                start_date.isoformat(),
                end_date.isoformat(),
                json.dumps(symbols),
                frequency,
                created_at,
                len(results),
                json.dumps(summary_dict),
                json.dumps(metadata or {})
            ))

            # Insert individual signals
            for result in results:
                cursor.execute("""
                    INSERT INTO backtest_signals
                    (run_id, symbol, date, recommendation, composite_score, confidence,
                     entry_price, exit_price,
                     forward_return_1m, forward_return_3m, forward_return_6m,
                     benchmark_return_1m, benchmark_return_3m, benchmark_return_6m,
                     alpha_1m, alpha_3m, alpha_6m,
                     agent_scores, market_regime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    result.symbol,
                    result.date.isoformat(),
                    result.recommendation,
                    result.composite_score,
                    result.confidence,
                    result.entry_price,
                    result.exit_price,
                    result.forward_return_1m,
                    result.forward_return_3m,
                    result.forward_return_6m,
                    result.benchmark_return_1m,
                    result.benchmark_return_3m,
                    result.benchmark_return_6m,
                    result.alpha_1m,
                    result.alpha_3m,
                    result.alpha_6m,
                    json.dumps(result.agent_scores),
                    result.market_regime
                ))

            conn.commit()
            logger.info(f"Saved backtest run {run_id} with {len(results)} signals")
            return run_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save backtest run: {e}")
            raise
        finally:
            conn.close()

    def get_backtest_run(self, run_id: str) -> Optional[Dict]:
        """
        Retrieve a complete backtest run by ID

        Args:
            run_id: UUID of the run

        Returns:
            Dict with run metadata, summary, and results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get run metadata
            cursor.execute("""
                SELECT run_id, name, start_date, end_date, symbols, frequency,
                       created_at, total_signals, summary, metadata
                FROM backtest_runs
                WHERE run_id = ?
            """, (run_id,))

            row = cursor.fetchone()
            if not row:
                logger.warning(f"Backtest run {run_id} not found")
                return None

            run_data = {
                'run_id': row[0],
                'name': row[1],
                'start_date': row[2],
                'end_date': row[3],
                'symbols': json.loads(row[4]),
                'frequency': row[5],
                'created_at': row[6],
                'total_signals': row[7],
                'summary': json.loads(row[8]),
                'metadata': json.loads(row[9]) if row[9] else {}
            }

            # Get all signals for this run
            cursor.execute("""
                SELECT signal_id, symbol, date, recommendation, composite_score, confidence,
                       entry_price, exit_price,
                       forward_return_1m, forward_return_3m, forward_return_6m,
                       benchmark_return_1m, benchmark_return_3m, benchmark_return_6m,
                       alpha_1m, alpha_3m, alpha_6m,
                       agent_scores, market_regime
                FROM backtest_signals
                WHERE run_id = ?
                ORDER BY date, symbol
            """, (run_id,))

            signals = []
            for row in cursor.fetchall():
                signals.append({
                    'signal_id': row[0],
                    'symbol': row[1],
                    'date': row[2],
                    'recommendation': row[3],
                    'composite_score': row[4],
                    'confidence': row[5],
                    'entry_price': row[6],
                    'exit_price': row[7],
                    'forward_return_1m': row[8],
                    'forward_return_3m': row[9],
                    'forward_return_6m': row[10],
                    'benchmark_return_1m': row[11],
                    'benchmark_return_3m': row[12],
                    'benchmark_return_6m': row[13],
                    'alpha_1m': row[14],
                    'alpha_3m': row[15],
                    'alpha_6m': row[16],
                    'agent_scores': json.loads(row[17]),
                    'market_regime': row[18]
                })

            run_data['signals'] = signals
            return run_data

        except Exception as e:
            logger.error(f"Failed to retrieve backtest run {run_id}: {e}")
            return None
        finally:
            conn.close()

    def list_backtest_runs(self, limit: int = 100) -> List[Dict]:
        """
        List all backtest runs (summary only)

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of run summaries (without individual signals)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT run_id, name, start_date, end_date, symbols, frequency,
                       created_at, total_signals, summary
                FROM backtest_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            runs = []
            for row in cursor.fetchall():
                runs.append({
                    'run_id': row[0],
                    'name': row[1],
                    'start_date': row[2],
                    'end_date': row[3],
                    'symbols': json.loads(row[4]),
                    'frequency': row[5],
                    'created_at': row[6],
                    'total_signals': row[7],
                    'summary': json.loads(row[8])
                })

            return runs

        except Exception as e:
            logger.error(f"Failed to list backtest runs: {e}")
            return []
        finally:
            conn.close()

    def delete_backtest_run(self, run_id: str) -> bool:
        """
        Delete a backtest run and all its signals

        Args:
            run_id: UUID of the run to delete

        Returns:
            True if deleted, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Delete signals first (foreign key)
            cursor.execute("DELETE FROM backtest_signals WHERE run_id = ?", (run_id,))

            # Delete run
            cursor.execute("DELETE FROM backtest_runs WHERE run_id = ?", (run_id,))

            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Deleted backtest run {run_id}")
                return True
            else:
                logger.warning(f"Backtest run {run_id} not found")
                return False

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete backtest run {run_id}: {e}")
            return False
        finally:
            conn.close()

    def get_signals_by_symbol(self, symbol: str, limit: int = 100) -> List[Dict]:
        """
        Get all historical backtest signals for a specific symbol

        Args:
            symbol: Stock symbol
            limit: Maximum number of signals to return

        Returns:
            List of signals across all backtest runs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT s.signal_id, s.run_id, r.name, s.symbol, s.date,
                       s.recommendation, s.composite_score, s.confidence,
                       s.alpha_3m, s.forward_return_3m
                FROM backtest_signals s
                JOIN backtest_runs r ON s.run_id = r.run_id
                WHERE s.symbol = ?
                ORDER BY s.date DESC
                LIMIT ?
            """, (symbol, limit))

            signals = []
            for row in cursor.fetchall():
                signals.append({
                    'signal_id': row[0],
                    'run_id': row[1],
                    'run_name': row[2],
                    'symbol': row[3],
                    'date': row[4],
                    'recommendation': row[5],
                    'composite_score': row[6],
                    'confidence': row[7],
                    'alpha_3m': row[8],
                    'forward_return_3m': row[9]
                })

            return signals

        except Exception as e:
            logger.error(f"Failed to get signals for {symbol}: {e}")
            return []
        finally:
            conn.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*70)
    print("BACKTEST DATABASE - Example Usage")
    print("="*70)

    # Initialize database
    db = BacktestDatabase()

    # List existing runs
    runs = db.list_backtest_runs()
    print(f"\nFound {len(runs)} existing backtest runs:")
    for run in runs:
        print(f"  - {run['name']} ({run['created_at']}) - {run['total_signals']} signals")

    if runs:
        # Get details of most recent run
        latest_run_id = runs[0]['run_id']
        print(f"\nRetrieving details for run: {latest_run_id}")
        run_details = db.get_backtest_run(latest_run_id)

        if run_details:
            print(f"\nRun: {run_details['name']}")
            print(f"Period: {run_details['start_date']} to {run_details['end_date']}")
            print(f"Signals: {len(run_details['signals'])}")
            print(f"\nSummary metrics:")
            summary = run_details['summary']
            print(f"  Hit Rate (3M): {summary.get('hit_rate_3m', 0):.1f}%")
            print(f"  Avg Alpha (3M): {summary.get('avg_alpha_3m', 0):+.2f}%")
            print(f"  Sharpe Ratio (3M): {summary.get('sharpe_ratio_3m', 0):.2f}")
