"""
Backtesting Framework - Validate Agent Performance on Historical Data

This module provides:
1. Historical performance testing of stock recommendations
2. Agent effectiveness measurement
3. Regime-specific performance validation
4. Forward return analysis

Key Metrics:
- Hit Rate: % of BUY recommendations that outperform benchmark
- Average Return: Mean return of recommendations
- Sharpe Ratio: Risk-adjusted returns
- Win/Loss Ratio: Average win / Average loss
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.stock_scorer import StockScorer
from data.hybrid_provider import HybridDataProvider
from core.exceptions import DataValidationException

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from a single backtest trade"""
    symbol: str
    date: datetime
    recommendation: str
    composite_score: float
    confidence: float
    entry_price: float
    exit_price: Optional[float]
    forward_return_1m: Optional[float]
    forward_return_3m: Optional[float]
    forward_return_6m: Optional[float]
    benchmark_return_1m: Optional[float]
    benchmark_return_3m: Optional[float]
    benchmark_return_6m: Optional[float]
    alpha_1m: Optional[float]  # Excess return vs benchmark
    alpha_3m: Optional[float]
    alpha_6m: Optional[float]
    agent_scores: Dict[str, float]
    market_regime: Optional[str]


@dataclass
class BacktestSummary:
    """Aggregate backtest performance metrics"""
    total_signals: int
    total_buys: int
    total_sells: int

    # Hit rates (% positive alpha)
    hit_rate_1m: float
    hit_rate_3m: float
    hit_rate_6m: float

    # Average returns
    avg_return_1m: float
    avg_return_3m: float
    avg_return_6m: float

    # Average alpha (excess return vs benchmark)
    avg_alpha_1m: float
    avg_alpha_3m: float
    avg_alpha_6m: float

    # Risk metrics
    sharpe_ratio_1m: float
    sharpe_ratio_3m: float
    sharpe_ratio_6m: float
    max_drawdown: float

    # Win/Loss analysis
    win_rate: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float

    # By recommendation
    performance_by_recommendation: Dict[str, Dict]

    # By agent
    agent_correlations: Dict[str, float]  # Correlation between agent score and alpha

    # By regime
    performance_by_regime: Dict[str, Dict]


class Backtester:
    """
    Backtesting framework for validating stock analysis system

    Usage:
        backtester = Backtester(scorer, data_provider)
        results = backtester.run_backtest(
            symbols=['TCS', 'INFY', 'RELIANCE'],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 12, 31),
            rebalance_frequency='monthly'
        )
        summary = backtester.generate_summary(results)
    """

    def __init__(
        self,
        scorer: Optional[StockScorer] = None,
        data_provider: Optional[HybridDataProvider] = None,
        benchmark_symbol: str = '^NSEI'  # NIFTY 50
    ):
        """
        Initialize backtester

        Args:
            scorer: StockScorer instance (creates new if None)
            data_provider: Data provider (creates new if None)
            benchmark_symbol: Benchmark index symbol (default: NIFTY 50)
        """
        self.scorer = scorer or StockScorer()
        self.data_provider = data_provider or HybridDataProvider()
        self.benchmark_symbol = benchmark_symbol

        # Cache for benchmark data
        self.benchmark_data: Optional[pd.DataFrame] = None

        logger.info(f"Backtester initialized with benchmark: {benchmark_symbol}")

    def run_backtest(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        rebalance_frequency: str = 'monthly',  # 'daily', 'weekly', 'monthly', 'quarterly'
        forward_periods: List[int] = [20, 60, 120],  # Trading days for 1M, 3M, 6M
        parallel: bool = True
    ) -> List[BacktestResult]:
        """
        Run backtest across multiple stocks and dates

        Args:
            symbols: List of stock symbols to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            rebalance_frequency: How often to generate signals
            forward_periods: Forward periods to measure returns (in trading days)
            parallel: Run backtests in parallel

        Returns:
            List of BacktestResult objects
        """
        logger.info(f"Starting backtest: {len(symbols)} stocks, {start_date.date()} to {end_date.date()}")
        logger.info(f"Rebalance frequency: {rebalance_frequency}")

        # Generate backtest dates
        backtest_dates = self._generate_backtest_dates(start_date, end_date, rebalance_frequency)
        logger.info(f"Generated {len(backtest_dates)} backtest dates")

        # Load benchmark data once
        self._load_benchmark_data(start_date, end_date, max(forward_periods))

        # Run backtest for each symbol and date
        results = []

        if parallel:
            results = self._run_backtest_parallel(symbols, backtest_dates, forward_periods)
        else:
            results = self._run_backtest_sequential(symbols, backtest_dates, forward_periods)

        logger.info(f"Backtest complete: {len(results)} signals generated")
        return results

    def _run_backtest_sequential(
        self,
        symbols: List[str],
        dates: List[datetime],
        forward_periods: List[int]
    ) -> List[BacktestResult]:
        """Run backtest sequentially"""
        results = []
        total = len(symbols) * len(dates)
        count = 0

        for symbol in symbols:
            for date in dates:
                count += 1
                if count % 10 == 0:
                    logger.info(f"Progress: {count}/{total} ({count/total*100:.1f}%)")

                try:
                    result = self._backtest_single_point(symbol, date, forward_periods)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to backtest {symbol} on {date.date()}: {e}")

        return results

    def _run_backtest_parallel(
        self,
        symbols: List[str],
        dates: List[datetime],
        forward_periods: List[int]
    ) -> List[BacktestResult]:
        """Run backtest in parallel"""
        results = []
        tasks = [(symbol, date) for symbol in symbols for date in dates]

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_task = {
                executor.submit(self._backtest_single_point, symbol, date, forward_periods): (symbol, date)
                for symbol, date in tasks
            }

            completed = 0
            total = len(tasks)

            for future in as_completed(future_to_task):
                completed += 1
                if completed % 10 == 0:
                    logger.info(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)")

                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    symbol, date = future_to_task[future]
                    logger.warning(f"Failed to backtest {symbol} on {date.date()}: {e}")

        return results

    def _backtest_single_point(
        self,
        symbol: str,
        date: datetime,
        forward_periods: List[int]
    ) -> Optional[BacktestResult]:
        """
        Backtest a single stock at a single point in time

        This simulates: "What if we analyzed this stock on this date?"
        """
        try:
            logger.info(f"Backtesting {symbol} on {date.date()}")

            # Get historical data up to this date (point-in-time data)
            historical_data = self._get_point_in_time_data(symbol, date)
            if historical_data is None or historical_data.empty:
                logger.warning(f"Skipping {symbol} on {date.date()}: No historical data available")
                return None

            logger.debug(f"Fetched {len(historical_data)} days of data for {symbol}")

            # Get entry price (close on analysis date)
            # Use nearest available trading day if exact date doesn't exist
            entry_date = date
            if date not in historical_data.index:
                try:
                    # Find nearest trading day
                    nearest_idx = historical_data.index.get_indexer([date], method='nearest')[0]
                    if nearest_idx >= 0 and nearest_idx < len(historical_data):
                        entry_date = historical_data.index[nearest_idx]
                        logger.debug(f"Using nearest trading day {entry_date.date()} for backtest date {date.date()}")
                    else:
                        logger.warning(f"Skipping {symbol} on {date.date()}: Could not find nearest trading day")
                        return None
                except Exception as e:
                    logger.warning(f"Skipping {symbol} on {date.date()}: Error finding nearest date - {e}")
                    return None

            entry_price = float(historical_data.loc[entry_date, 'Close'])

            # CRITICAL FIX: Create cached_data dict with point-in-time historical data
            # This prevents look-ahead bias by passing only data available as of the backtest date
            cached_data = {
                'symbol': symbol,
                'historical_data': historical_data,
                'provider': 'backtest',
                'current_price': entry_price,
                # Note: We don't have historical fundamentals, so agents will work with price data only
            }

            # Score the stock as of this date (using only data available then)
            analysis = self.scorer.score_stock(symbol, nifty_data=self.benchmark_data, cached_data=cached_data)

            if 'error' in analysis:
                logger.warning(f"Skipping {symbol} on {date.date()}: Analysis error: {analysis.get('error')}")
                return None

            if analysis.get('composite_score', 0) == 0:
                logger.warning(f"Skipping {symbol} on {date.date()}: Zero composite score")
                return None

            # FIX: Fetch future data separately from past data to prevent look-ahead bias
            # Get max forward period needed (plus buffer for trading days)
            max_period = max(forward_periods) if forward_periods else 120
            future_data = self._get_future_data(symbol, entry_date, forward_days=max_period + 50)

            # Calculate forward returns using ONLY future data
            forward_returns = self._calculate_forward_returns(
                future_data, entry_date, forward_periods
            )

            # Calculate benchmark returns (use entry_date, not original date)
            benchmark_returns = self._calculate_benchmark_returns(entry_date, forward_periods)

            # Calculate alpha (excess return vs benchmark)
            alpha_1m = forward_returns.get(forward_periods[0], 0) - benchmark_returns.get(forward_periods[0], 0) if forward_returns.get(forward_periods[0]) and benchmark_returns.get(forward_periods[0]) else None
            alpha_3m = forward_returns.get(forward_periods[1], 0) - benchmark_returns.get(forward_periods[1], 0) if forward_returns.get(forward_periods[1]) and benchmark_returns.get(forward_periods[1]) else None
            alpha_6m = forward_returns.get(forward_periods[2], 0) - benchmark_returns.get(forward_periods[2], 0) if forward_returns.get(forward_periods[2]) and benchmark_returns.get(forward_periods[2]) else None

            # Extract agent scores
            agent_scores = {
                'fundamentals': analysis.get('agent_scores', {}).get('fundamentals', {}).get('score', 0),
                'momentum': analysis.get('agent_scores', {}).get('momentum', {}).get('score', 0),
                'quality': analysis.get('agent_scores', {}).get('quality', {}).get('score', 0),
                'sentiment': analysis.get('agent_scores', {}).get('sentiment', {}).get('score', 0),
                'institutional_flow': analysis.get('agent_scores', {}).get('institutional_flow', {}).get('score', 0)
            }

            return BacktestResult(
                symbol=symbol,
                date=entry_date,  # Use actual trading day, not backtest date
                recommendation=analysis.get('recommendation', 'UNKNOWN'),
                composite_score=analysis.get('composite_score', 0),
                confidence=analysis.get('composite_confidence', 0),
                entry_price=entry_price,
                exit_price=None,  # Not used for forward return testing
                forward_return_1m=forward_returns.get(forward_periods[0]),
                forward_return_3m=forward_returns.get(forward_periods[1]),
                forward_return_6m=forward_returns.get(forward_periods[2]),
                benchmark_return_1m=benchmark_returns.get(forward_periods[0]),
                benchmark_return_3m=benchmark_returns.get(forward_periods[1]),
                benchmark_return_6m=benchmark_returns.get(forward_periods[2]),
                alpha_1m=alpha_1m,
                alpha_3m=alpha_3m,
                alpha_6m=alpha_6m,
                agent_scores=agent_scores,
                market_regime=None  # TODO: Add regime detection
            )

        except Exception as e:
            logger.error(f"Backtest failed for {symbol} on {date.date()}: {e}")
            return None

    def _generate_backtest_dates(
        self,
        start_date: datetime,
        end_date: datetime,
        frequency: str
    ) -> List[datetime]:
        """Generate list of dates to run backtest on"""
        dates = []
        current = start_date

        freq_map = {
            'daily': timedelta(days=1),
            'weekly': timedelta(days=7),
            'monthly': timedelta(days=30),
            'quarterly': timedelta(days=90)
        }

        delta = freq_map.get(frequency, timedelta(days=30))

        while current <= end_date:
            dates.append(current)
            current += delta

        return dates

    def _get_point_in_time_data(
        self,
        symbol: str,
        as_of_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Get historical data as it would have been available on a specific date
        (avoids look-ahead bias)
        """
        try:
            # FIX: Increased lookback from 2 years to 5 years for better context
            # This ensures sufficient historical data for all technical indicators
            df = self.data_provider.get_historical_data(
                symbol,
                start_date=as_of_date - timedelta(days=1825),  # 5 years back
                end_date=as_of_date
            )

            # VALIDATION: Ensure no future data leaked in
            if df is not None and not df.empty:
                max_date = df.index.max()
                if max_date > as_of_date:
                    logger.warning(f"Future data detected! Filtering out dates after {as_of_date.date()}")
                    df = df[df.index <= as_of_date]

            return df
        except Exception as e:
            logger.warning(f"Could not fetch point-in-time data for {symbol}: {e}")
            return None

    def _get_future_data(
        self,
        symbol: str,
        from_date: datetime,
        forward_days: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        Get future data for forward return calculation
        Separated from point-in-time data to prevent look-ahead bias
        """
        try:
            # Fetch data starting from the entry date going forward
            df = self.data_provider.get_historical_data(
                symbol,
                start_date=from_date,
                end_date=from_date + timedelta(days=forward_days)
            )

            # VALIDATION: Ensure data starts at or after from_date
            if df is not None and not df.empty:
                min_date = df.index.min()
                if min_date < from_date:
                    logger.debug(f"Filtering out dates before {from_date.date()}")
                    df = df[df.index >= from_date]

            return df
        except Exception as e:
            logger.warning(f"Could not fetch future data for {symbol}: {e}")
            return None

    def _calculate_forward_returns(
        self,
        future_data: pd.DataFrame,
        entry_date: datetime,
        periods: List[int]
    ) -> Dict[int, float]:
        """
        Calculate forward returns for specified periods using actual trading days

        FIX: Uses proper trading day counting instead of row-based arithmetic
        to handle market holidays and gaps correctly
        """
        returns = {}

        if future_data is None or future_data.empty:
            logger.debug("No future data available for return calculation")
            return returns

        # Check if entry_date exists in the index
        if entry_date not in future_data.index:
            logger.debug(f"Entry date {entry_date.date()} not in future data")
            # Try to find nearest FUTURE date (use bfill to avoid past dates)
            try:
                nearest_idx = future_data.index.get_indexer([entry_date], method='bfill')[0]
                if nearest_idx >= 0 and nearest_idx < len(future_data):
                    entry_date = future_data.index[nearest_idx]
                    logger.debug(f"Using nearest future date: {entry_date.date()}")
                else:
                    logger.debug("Could not find valid entry date in future data")
                    return {}
            except Exception as e:
                logger.debug(f"Could not find nearest date: {e}")
                return {}

        try:
            entry_price = float(future_data.loc[entry_date, 'Close'])

            # FIX: Calculate returns using actual trading days, not row indices
            # Get all trading days from entry date forward
            trading_days = future_data.index[future_data.index >= entry_date]

            for period in periods:
                # Count actual trading days forward
                if len(trading_days) > period:
                    exit_date = trading_days[period]  # Actual date X trading days later
                    exit_price = float(future_data.loc[exit_date, 'Close'])
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    returns[period] = return_pct

                    # VALIDATION: Verify exit is actually after entry
                    if exit_date <= entry_date:
                        logger.error(f"Exit date {exit_date.date()} is not after entry date {entry_date.date()}!")
                        returns.pop(period)  # Remove invalid return
                    else:
                        logger.debug(f"{period}-day return: {entry_date.date()} → {exit_date.date()} = {return_pct:.2f}%")
                else:
                    logger.debug(f"Insufficient future data for {period}-day return (need {period+1} days, have {len(trading_days)})")

        except Exception as e:
            logger.error(f"Error calculating forward returns: {e}")
            return {}

        return returns

    def _load_benchmark_data(
        self,
        start_date: datetime,
        end_date: datetime,
        max_forward_period: int
    ):
        """Load benchmark data for the entire backtest period"""
        try:
            # Add buffer for forward periods
            buffer_end = end_date + timedelta(days=max_forward_period * 2)

            self.benchmark_data = self.data_provider.get_historical_data(
                self.benchmark_symbol,
                start_date=start_date - timedelta(days=365),
                end_date=buffer_end
            )
            logger.info(f"Loaded {len(self.benchmark_data)} days of benchmark data")
        except Exception as e:
            logger.error(f"Failed to load benchmark data: {e}")
            self.benchmark_data = pd.DataFrame()

    def _calculate_benchmark_returns(
        self,
        date: datetime,
        periods: List[int]
    ) -> Dict[int, float]:
        """
        Calculate benchmark returns for comparison

        FIX: Added nearest-date fallback to prevent silent failures when
        stock and benchmark dates don't align exactly
        """
        returns = {}

        if self.benchmark_data is None or self.benchmark_data.empty:
            logger.warning("No benchmark data available for return calculation")
            return returns

        # FIX: Add nearest-date fallback instead of silent failure
        entry_date = date
        if date not in self.benchmark_data.index:
            logger.debug(f"Benchmark date {date.date()} not found, finding nearest")
            try:
                # Find nearest trading day in benchmark data
                nearest_idx = self.benchmark_data.index.get_indexer([date], method='nearest')[0]

                if nearest_idx >= 0 and nearest_idx < len(self.benchmark_data):
                    entry_date = self.benchmark_data.index[nearest_idx]
                    date_diff = abs((entry_date - date).days)

                    if date_diff > 5:
                        # More than 5 days off = warn user
                        logger.warning(f"Benchmark date shifted by {date_diff} days: {date.date()} → {entry_date.date()}")
                    else:
                        logger.debug(f"Using nearest benchmark date: {entry_date.date()} (off by {date_diff} days)")
                else:
                    logger.error(f"Could not find nearest benchmark date for {date.date()}")
                    return returns
            except Exception as e:
                logger.error(f"Error finding nearest benchmark date: {e}")
                return returns

        try:
            entry_price = float(self.benchmark_data.loc[entry_date, 'Close'])
            entry_idx = self.benchmark_data.index.get_loc(entry_date)

            # FIX: Use actual trading days like stock returns
            trading_days = self.benchmark_data.index[self.benchmark_data.index >= entry_date]

            for period in periods:
                # Count actual trading days forward
                if len(trading_days) > period:
                    exit_date = trading_days[period]
                    exit_price = float(self.benchmark_data.loc[exit_date, 'Close'])
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    returns[period] = return_pct
                    logger.debug(f"Benchmark {period}-day return: {entry_date.date()} → {exit_date.date()} = {return_pct:.2f}%")
                else:
                    logger.debug(f"Insufficient benchmark data for {period}-day return")

        except Exception as e:
            logger.error(f"Error calculating benchmark returns: {e}")
            return {}

        return returns

    def generate_summary(self, results: List[BacktestResult]) -> BacktestSummary:
        """Generate aggregate performance summary from backtest results"""
        if not results:
            raise ValueError("No backtest results to summarize")

        # Filter by recommendation type
        buys = [r for r in results if 'BUY' in r.recommendation]
        sells = [r for r in results if 'SELL' in r.recommendation]

        # Calculate hit rates (% with positive alpha)
        hit_rate_1m = sum(1 for r in buys if r.alpha_1m and r.alpha_1m > 0) / len(buys) * 100 if buys else 0
        hit_rate_3m = sum(1 for r in buys if r.alpha_3m and r.alpha_3m > 0) / len(buys) * 100 if buys else 0
        hit_rate_6m = sum(1 for r in buys if r.alpha_6m and r.alpha_6m > 0) / len(buys) * 100 if buys else 0

        # Average returns (only BUY recommendations)
        returns_1m = [r.forward_return_1m for r in buys if r.forward_return_1m is not None]
        returns_3m = [r.forward_return_3m for r in buys if r.forward_return_3m is not None]
        returns_6m = [r.forward_return_6m for r in buys if r.forward_return_6m is not None]

        avg_return_1m = np.mean(returns_1m) if returns_1m else 0
        avg_return_3m = np.mean(returns_3m) if returns_3m else 0
        avg_return_6m = np.mean(returns_6m) if returns_6m else 0

        # Average alpha
        alphas_1m = [r.alpha_1m for r in buys if r.alpha_1m is not None]
        alphas_3m = [r.alpha_3m for r in buys if r.alpha_3m is not None]
        alphas_6m = [r.alpha_6m for r in buys if r.alpha_6m is not None]

        avg_alpha_1m = np.mean(alphas_1m) if alphas_1m else 0
        avg_alpha_3m = np.mean(alphas_3m) if alphas_3m else 0
        avg_alpha_6m = np.mean(alphas_6m) if alphas_6m else 0

        # Sharpe ratios
        sharpe_1m = (avg_return_1m / np.std(returns_1m)) if returns_1m and np.std(returns_1m) > 0 else 0
        sharpe_3m = (avg_return_3m / np.std(returns_3m)) if returns_3m and np.std(returns_3m) > 0 else 0
        sharpe_6m = (avg_return_6m / np.std(returns_6m)) if returns_6m and np.std(returns_6m) > 0 else 0

        # Win/Loss analysis
        wins = [r for r in returns_3m if r > 0]
        losses = [r for r in returns_3m if r < 0]
        win_rate = len(wins) / len(returns_3m) * 100 if returns_3m else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # Max drawdown (simplified)
        cumulative_returns = np.cumsum(returns_3m) if returns_3m else [0]
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = running_max - cumulative_returns
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0

        # Performance by recommendation
        performance_by_recommendation = self._analyze_by_recommendation(results)

        # Agent correlations
        agent_correlations = self._analyze_agent_correlations(results)

        # Performance by regime (placeholder)
        performance_by_regime = {}

        return BacktestSummary(
            total_signals=len(results),
            total_buys=len(buys),
            total_sells=len(sells),
            hit_rate_1m=hit_rate_1m,
            hit_rate_3m=hit_rate_3m,
            hit_rate_6m=hit_rate_6m,
            avg_return_1m=avg_return_1m,
            avg_return_3m=avg_return_3m,
            avg_return_6m=avg_return_6m,
            avg_alpha_1m=avg_alpha_1m,
            avg_alpha_3m=avg_alpha_3m,
            avg_alpha_6m=avg_alpha_6m,
            sharpe_ratio_1m=sharpe_1m,
            sharpe_ratio_3m=sharpe_3m,
            sharpe_ratio_6m=sharpe_6m,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=win_loss_ratio,
            performance_by_recommendation=performance_by_recommendation,
            agent_correlations=agent_correlations,
            performance_by_regime=performance_by_regime
        )

    def _analyze_by_recommendation(self, results: List[BacktestResult]) -> Dict:
        """Analyze performance broken down by recommendation type"""
        by_rec = {}

        for rec_type in ['STRONG BUY', 'BUY', 'WEAK BUY', 'HOLD', 'WEAK SELL', 'SELL']:
            filtered = [r for r in results if r.recommendation == rec_type]
            if not filtered:
                continue

            alphas_3m = [r.alpha_3m for r in filtered if r.alpha_3m is not None]

            by_rec[rec_type] = {
                'count': len(filtered),
                'avg_alpha_3m': np.mean(alphas_3m) if alphas_3m else 0,
                'hit_rate_3m': sum(1 for a in alphas_3m if a > 0) / len(alphas_3m) * 100 if alphas_3m else 0
            }

        return by_rec

    def _analyze_agent_correlations(self, results: List[BacktestResult]) -> Dict[str, float]:
        """Calculate correlation between agent scores and alpha"""
        correlations = {}

        alphas = [r.alpha_3m for r in results if r.alpha_3m is not None]

        for agent in ['fundamentals', 'momentum', 'quality', 'sentiment', 'institutional_flow']:
            scores = [r.agent_scores.get(agent, 0) for r in results if r.alpha_3m is not None]

            if len(scores) > 1 and len(alphas) > 1:
                correlation = np.corrcoef(scores, alphas)[0, 1]
                correlations[agent] = correlation
            else:
                correlations[agent] = 0.0

        return correlations

    def print_summary(self, summary: BacktestSummary):
        """Pretty print backtest summary"""
        print("\n" + "="*70)
        print("BACKTEST PERFORMANCE SUMMARY")
        print("="*70)

        print(f"\n📊 SIGNAL STATISTICS")
        print(f"  Total Signals: {summary.total_signals}")
        print(f"  BUY Signals: {summary.total_buys}")
        print(f"  SELL Signals: {summary.total_sells}")

        print(f"\n🎯 HIT RATES (% Positive Alpha)")
        print(f"  1 Month:  {summary.hit_rate_1m:.1f}%")
        print(f"  3 Months: {summary.hit_rate_3m:.1f}%")
        print(f"  6 Months: {summary.hit_rate_6m:.1f}%")

        print(f"\n📈 AVERAGE RETURNS (BUY signals)")
        print(f"  1 Month:  {summary.avg_return_1m:+.2f}%")
        print(f"  3 Months: {summary.avg_return_3m:+.2f}%")
        print(f"  6 Months: {summary.avg_return_6m:+.2f}%")

        print(f"\n⚡ ALPHA (Excess Return vs NIFTY 50)")
        print(f"  1 Month:  {summary.avg_alpha_1m:+.2f}%")
        print(f"  3 Months: {summary.avg_alpha_3m:+.2f}%")
        print(f"  6 Months: {summary.avg_alpha_6m:+.2f}%")

        print(f"\n📉 RISK METRICS")
        print(f"  Sharpe Ratio (3M): {summary.sharpe_ratio_3m:.2f}")
        print(f"  Max Drawdown: {summary.max_drawdown:.2f}%")
        print(f"  Win Rate: {summary.win_rate:.1f}%")
        print(f"  Avg Win: {summary.avg_win:.2f}%")
        print(f"  Avg Loss: {summary.avg_loss:.2f}%")
        print(f"  Win/Loss Ratio: {summary.win_loss_ratio:.2f}x")

        print(f"\n🏆 PERFORMANCE BY RECOMMENDATION")
        for rec, perf in summary.performance_by_recommendation.items():
            print(f"  {rec:12s}: {perf['count']:3d} signals | "
                  f"Avg Alpha: {perf['avg_alpha_3m']:+.2f}% | "
                  f"Hit Rate: {perf['hit_rate_3m']:.1f}%")

        print(f"\n🤖 AGENT CORRELATIONS (with 3M Alpha)")
        for agent, corr in sorted(summary.agent_correlations.items(), key=lambda x: abs(x[1]), reverse=True):
            print(f"  {agent:20s}: {corr:+.3f}")

        print("\n" + "="*70)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*70)
    print("BACKTESTING FRAMEWORK - Example Usage")
    print("="*70)

    # Initialize backtester
    backtester = Backtester()

    # Run backtest on NIFTY 50 top stocks
    test_symbols = ['TCS', 'INFY', 'RELIANCE']

    print(f"\nRunning backtest on {test_symbols}...")
    print("Period: 2023-01-01 to 2024-06-30")
    print("Frequency: Monthly rebalancing")

    results = backtester.run_backtest(
        symbols=test_symbols,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 6, 30),
        rebalance_frequency='monthly',
        parallel=True
    )

    # Generate and print summary
    if results:
        summary = backtester.generate_summary(results)
        backtester.print_summary(summary)
    else:
        print("\n⚠️  No backtest results generated (data may not be available)")
