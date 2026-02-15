"""
Background Data Collector for Historical Analysis

Periodically analyzes stocks and stores results in database.
Runs during market hours on a configurable schedule.
"""

import logging
import os
from datetime import datetime, time as dt_time
from typing import Dict, Any, List
import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.stock_scorer import StockScorer
from core.market_regime_service import MarketRegimeService
from data.historical_db import HistoricalDatabase
from data.hybrid_provider import HybridDataProvider
from data.stock_universe import get_universe

logger = logging.getLogger(__name__)


class HistoricalDataCollector:
    """
    Background service that collects and stores stock analysis data
    """

    def __init__(
        self,
        db: HistoricalDatabase,
        stock_scorer: StockScorer,
        market_regime_service: MarketRegimeService,
        collection_interval_hours: int = 4,
        enabled: bool = True
    ):
        """
        Initialize data collector

        Args:
            db: Historical database instance
            stock_scorer: Stock scorer instance
            market_regime_service: Market regime service
            collection_interval_hours: Hours between collections
            enabled: Whether collection is enabled
        """
        self.db = db
        self.stock_scorer = stock_scorer
        self.market_regime_service = market_regime_service
        self.collection_interval_hours = collection_interval_hours
        self.enabled = enabled

        self.scheduler = BackgroundScheduler()
        self.is_running = False

        # Market hours (IST)
        self.market_open = dt_time(
            int(os.getenv('MARKET_OPEN_HOUR', '9')),
            int(os.getenv('MARKET_OPEN_MINUTE', '15'))
        )
        self.market_close = dt_time(
            int(os.getenv('MARKET_CLOSE_HOUR', '15')),
            int(os.getenv('MARKET_CLOSE_MINUTE', '30'))
        )

        # IST timezone
        self.ist = pytz.timezone('Asia/Kolkata')

        # Collection stats
        self.stats = {
            'total_collections': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'last_collection_time': None,
            'last_collection_duration': None
        }
        self.on_collection_complete = None

        logger.info(
            f"Historical data collector initialized "
            f"(interval: {collection_interval_hours}h, enabled: {enabled})"
        )

    def start(self):
        """Start background data collection"""
        if not self.enabled:
            logger.warning("Data collection is disabled")
            return

        if self.is_running:
            logger.warning("Data collector already running")
            return

        # Schedule periodic collection
        self.scheduler.add_job(
            func=self._collect_data,
            trigger=IntervalTrigger(hours=self.collection_interval_hours),
            id='historical_data_collection',
            name='Historical Data Collection',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(
            f"Data collector started - will run every {self.collection_interval_hours} hours"
        )

        # Run initial collection if during market hours
        if self._is_market_hours():
            logger.info("Running initial data collection")
            self._collect_data()

    def stop(self):
        """Stop background data collection"""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Data collector stopped")

    def _is_market_hours(self) -> bool:
        """Check if current time is during market hours (IST)"""
        now = datetime.now(self.ist)
        current_time = now.time()

        # Check if it's a weekday (Monday=0 to Friday=4)
        if now.weekday() >= 5:
            return False

        # Check if within market hours
        return self.market_open <= current_time <= self.market_close

    def _collect_data(self):
        """Collect stock analysis data"""
        start_time = datetime.now()

        # Skip if not market hours
        if not self._is_market_hours():
            logger.info("Skipping data collection - outside market hours")
            return

        logger.info("Starting historical data collection")

        try:
            # Get stock universe (NIFTY 50)
            universe = get_universe()
            stocks_to_analyze = universe.get_stock_list()

            logger.info(f"Analyzing {len(stocks_to_analyze)} stocks")

            # Collect market regime first
            self._collect_market_regime()

            # Analyze each stock
            success_count = 0
            fail_count = 0

            for symbol in stocks_to_analyze:
                try:
                    self._analyze_and_store_stock(symbol)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to analyze {symbol}: {e}")
                    fail_count += 1

            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            self.stats['total_collections'] += 1
            self.stats['successful_analyses'] += success_count
            self.stats['failed_analyses'] += fail_count
            self.stats['last_collection_time'] = start_time.isoformat()
            self.stats['last_collection_duration'] = duration

            logger.info(
                f"Data collection completed in {duration:.2f}s "
                f"(success: {success_count}, failed: {fail_count})"
            )

            # Trigger cache invalidation callback if registered
            if self.on_collection_complete:
                try:
                    self.on_collection_complete()
                    logger.info("Cache invalidation callback triggered")
                except Exception as cb_err:
                    logger.warning(f"Cache invalidation callback failed: {cb_err}")
            # Cleanup old data
            self._cleanup_old_data()

        except Exception as e:
            logger.error(f"Data collection failed: {e}", exc_info=True)

    def _collect_market_regime(self):
        """Collect and store current market regime"""
        try:
            regime_data = self.market_regime_service.get_market_regime()

            self.db.save_market_regime(
                regime=regime_data['regime'],
                trend=regime_data['trend'],
                volatility=regime_data['volatility'],
                weights=regime_data['weights'],
                metrics={
                    'confidence': regime_data.get('confidence'),
                    'factors': regime_data.get('factors', {})
                }
            )

            logger.info(f"Market regime saved: {regime_data['regime']}")

        except Exception as e:
            logger.error(f"Failed to collect market regime: {e}")

    def _analyze_and_store_stock(self, symbol: str):
        """
        Analyze a single stock and store results

        Args:
            symbol: Stock symbol to analyze
        """
        # Get stock analysis
        result = self.stock_scorer.score_stock(symbol)

        if not result or result.get('error'):
            raise ValueError(f"Analysis failed: {result.get('error', 'Unknown error')}")

        # Extract data
        composite_score = result.get('composite_score', 0)
        recommendation = result.get('recommendation', 'UNKNOWN')
        confidence = result.get('confidence', 0)
        agent_scores = result.get('agent_scores', {})
        weights = result.get('weights', {})
        market_regime = result.get('market_regime')

        # Get additional data
        price = None
        sector = 'Unknown'

        try:
            # Try to get current price from data provider
            data = self.stock_scorer.data_provider.get_stock_data(symbol)
            if data and 'current_price' in data:
                price = data['current_price']
            elif data and 'price' in data:
                price = data['price']
            # Get sector with fallback to 'Unknown'
            if data:
                sector = data.get('sector') or 'Unknown'
        except Exception as e:
            logger.debug(f"Could not fetch price/sector for {symbol}: {e}")

        # Save to database
        self.db.save_stock_analysis(
            symbol=symbol,
            composite_score=composite_score,
            recommendation=recommendation,
            confidence=confidence,
            agent_scores=agent_scores,
            weights=weights,
            market_regime=market_regime,
            price=price,
            sector=sector
        )

        logger.debug(f"Saved analysis for {symbol}: {composite_score:.2f} ({recommendation})")

    def _cleanup_old_data(self):
        """Clean up old data based on retention policy"""
        retention_days = int(os.getenv('DATA_RETENTION_DAYS', '365'))

        try:
            self.db.cleanup_old_data(retention_days=retention_days)
            logger.info(f"Old data cleaned up (retention: {retention_days} days)")
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def collect_now(self) -> Dict[str, Any]:
        """
        Manually trigger data collection (for testing/admin)

        Returns:
            Collection results
        """
        logger.info("Manual data collection triggered")
        self._collect_data()

        return {
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get collector status

        Returns:
            Status information
        """
        return {
            'enabled': self.enabled,
            'is_running': self.is_running,
            'collection_interval_hours': self.collection_interval_hours,
            'market_hours': f"{self.market_open} - {self.market_close} IST",
            'is_market_hours': self._is_market_hours(),
            'stats': self.stats,
            'next_run': self._get_next_run_time()
        }

    def _get_next_run_time(self) -> str:
        """Get next scheduled run time"""
        if not self.is_running:
            return 'Not running'

        job = self.scheduler.get_job('historical_data_collection')
        if job and job.next_run_time:
            return job.next_run_time.isoformat()

        return 'Unknown'


# Global collector instance (initialized in main.py)
_collector: HistoricalDataCollector = None


def init_collector(
    db: HistoricalDatabase,
    stock_scorer: StockScorer,
    market_regime_service: MarketRegimeService
) -> HistoricalDataCollector:
    """
    Initialize global data collector

    Args:
        db: Historical database
        stock_scorer: Stock scorer
        market_regime_service: Market regime service

    Returns:
        Collector instance
    """
    global _collector

    enabled = os.getenv('ENABLE_HISTORICAL_COLLECTION', 'true').lower() == 'true'
    interval_hours = int(os.getenv('HISTORICAL_COLLECTION_INTERVAL', '14400')) // 3600

    _collector = HistoricalDataCollector(
        db=db,
        stock_scorer=stock_scorer,
        market_regime_service=market_regime_service,
        collection_interval_hours=interval_hours,
        enabled=enabled
    )

    return _collector


def get_collector() -> HistoricalDataCollector:
    """Get global collector instance"""
    if _collector is None:
        raise RuntimeError("Data collector not initialized. Call init_collector() first.")
    return _collector


def start_collector():
    """Start global collector"""
    collector = get_collector()
    collector.start()


def stop_collector():
    """Stop global collector"""
    if _collector:
        _collector.stop()
