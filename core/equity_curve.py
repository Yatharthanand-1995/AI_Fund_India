"""
Equity Curve Calculator

Calculates portfolio performance over time for visualization and analysis.
Provides equity curves, drawdown analysis, and performance metrics.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class EquityCurveCalculator:
    """Calculate portfolio performance over time"""

    def __init__(self, initial_capital: float = 100000):
        """
        Initialize calculator

        Args:
            initial_capital: Starting portfolio value (default: 100,000)
        """
        self.initial_capital = initial_capital

    def calculate_equity_curve(
        self,
        signals: List[Dict],
        frequency: str = 'monthly',
        benchmark_symbol: str = '^NSEI'
    ) -> Dict:
        """
        Calculate portfolio equity curve

        Args:
            signals: List of backtest signals with returns
            frequency: Rebalancing frequency
            benchmark_symbol: Benchmark symbol for comparison

        Returns:
            Dict with equity curve data:
            {
                'dates': [...],  # List of datetime strings
                'portfolio_value': [...],  # Portfolio value at each date
                'benchmark_value': [...],  # Benchmark value at each date
                'cumulative_return': [...],  # % return from start
                'benchmark_return': [...],  # Benchmark % return
                'alpha': [...],  # Excess return vs benchmark
                'drawdown': [...]  # Current drawdown from peak
            }
        """
        if not signals:
            return self._empty_equity_curve()

        # Convert signals to DataFrame for easier manipulation
        df = pd.DataFrame(signals)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Group by rebalancing period
        rebalance_dates = sorted(df['date'].unique())

        # Initialize tracking arrays
        dates = []
        portfolio_values = []
        benchmark_values = []
        cumulative_returns = []
        benchmark_returns = []
        alphas = []
        drawdowns = []

        # Track portfolio state
        portfolio_value = self.initial_capital
        benchmark_value = self.initial_capital
        peak_value = self.initial_capital

        # Calculate returns for each period
        for date in rebalance_dates:
            period_signals = df[df['date'] == date]

            # Calculate equal-weight portfolio return (3-month forward)
            # Use 3-month returns as the primary metric
            period_returns = period_signals['forward_return_3m'].dropna()
            period_benchmark = period_signals['benchmark_return_3m'].dropna()

            if len(period_returns) == 0:
                continue

            # Equal-weight average return
            avg_return = period_returns.mean() / 100  # Convert % to decimal
            avg_benchmark = period_benchmark.mean() / 100 if len(period_benchmark) > 0 else 0

            # Update portfolio values
            portfolio_value *= (1 + avg_return)
            benchmark_value *= (1 + avg_benchmark)

            # Track peak for drawdown calculation
            if portfolio_value > peak_value:
                peak_value = portfolio_value

            # Calculate metrics
            cumulative_return = ((portfolio_value - self.initial_capital) / self.initial_capital) * 100
            benchmark_cumulative = ((benchmark_value - self.initial_capital) / self.initial_capital) * 100
            alpha = cumulative_return - benchmark_cumulative
            drawdown = ((portfolio_value - peak_value) / peak_value) * 100 if peak_value > 0 else 0

            # Store data
            dates.append(date.isoformat())
            portfolio_values.append(round(portfolio_value, 2))
            benchmark_values.append(round(benchmark_value, 2))
            cumulative_returns.append(round(cumulative_return, 2))
            benchmark_returns.append(round(benchmark_cumulative, 2))
            alphas.append(round(alpha, 2))
            drawdowns.append(round(drawdown, 2))

        return {
            'dates': dates,
            'portfolio_value': portfolio_values,
            'benchmark_value': benchmark_values,
            'cumulative_return': cumulative_returns,
            'benchmark_return': benchmark_returns,
            'alpha': alphas,
            'drawdown': drawdowns
        }

    def calculate_trade_statistics(
        self,
        signals: List[Dict]
    ) -> Dict:
        """
        Calculate detailed trade statistics

        Args:
            signals: List of backtest signals

        Returns:
            Dict with trade statistics
        """
        if not signals:
            return self._empty_statistics()

        df = pd.DataFrame(signals)

        # Focus on 3-month returns as primary metric
        returns_3m = df['forward_return_3m'].dropna()
        alpha_3m = df['alpha_3m'].dropna()

        if len(returns_3m) == 0:
            return self._empty_statistics()

        # Winning and losing trades
        wins = returns_3m[returns_3m > 0]
        losses = returns_3m[returns_3m < 0]

        total_trades = len(returns_3m)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Average returns
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Best and worst trades
        best_idx = returns_3m.idxmax() if len(returns_3m) > 0 else None
        worst_idx = returns_3m.idxmin() if len(returns_3m) > 0 else None

        best_trade = None
        worst_trade = None

        if best_idx is not None:
            best_signal = signals[best_idx]
            best_trade = {
                'symbol': best_signal['symbol'],
                'date': best_signal['date'],
                'return': round(best_signal['forward_return_3m'], 2),
                'alpha': round(best_signal.get('alpha_3m', 0), 2)
            }

        if worst_idx is not None:
            worst_signal = signals[worst_idx]
            worst_trade = {
                'symbol': worst_signal['symbol'],
                'date': worst_signal['date'],
                'return': round(worst_signal['forward_return_3m'], 2),
                'alpha': round(worst_signal.get('alpha_3m', 0), 2)
            }

        # Calculate Sharpe ratio (3-month)
        sharpe_ratio = 0
        if len(returns_3m) > 1:
            mean_return = returns_3m.mean()
            std_return = returns_3m.std()
            if std_return > 0:
                # Annualized Sharpe ratio (assuming monthly rebalancing)
                sharpe_ratio = (mean_return / std_return) * np.sqrt(12)

        # Total return and alpha
        total_return = returns_3m.mean()
        total_alpha = alpha_3m.mean() if len(alpha_3m) > 0 else 0

        # Calculate max drawdown
        equity_curve = self.calculate_equity_curve(signals)
        max_drawdown = min(equity_curve['drawdown']) if equity_curve['drawdown'] else 0

        # Calculate recovery time (days from max drawdown to recovery)
        recovery_time = self._calculate_recovery_time(equity_curve)

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'win_loss_ratio': round(win_loss_ratio, 2),
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_holding_period': 90,  # 3 months in days (simplified)
            'total_return': round(total_return, 2),
            'total_alpha': round(total_alpha, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'recovery_time': recovery_time
        }

    def _calculate_recovery_time(self, equity_curve: Dict) -> int:
        """Calculate time to recover from max drawdown (in days)"""
        if not equity_curve['drawdown']:
            return 0

        drawdowns = equity_curve['drawdown']
        max_dd_idx = drawdowns.index(min(drawdowns))

        # Find when drawdown returns to 0 after max drawdown
        for i in range(max_dd_idx, len(drawdowns)):
            if drawdowns[i] >= 0:
                # Assuming monthly rebalancing, convert to days
                return (i - max_dd_idx) * 30

        # Not recovered yet
        return (len(drawdowns) - max_dd_idx) * 30

    def _empty_equity_curve(self) -> Dict:
        """Return empty equity curve structure"""
        return {
            'dates': [],
            'portfolio_value': [],
            'benchmark_value': [],
            'cumulative_return': [],
            'benchmark_return': [],
            'alpha': [],
            'drawdown': []
        }

    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'win_loss_ratio': 0,
            'best_trade': None,
            'worst_trade': None,
            'avg_holding_period': 0,
            'total_return': 0,
            'total_alpha': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'recovery_time': 0
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example signals
    example_signals = [
        {
            'symbol': 'TCS',
            'date': '2024-01-01',
            'forward_return_3m': 12.5,
            'benchmark_return_3m': 8.0,
            'alpha_3m': 4.5
        },
        {
            'symbol': 'INFY',
            'date': '2024-01-01',
            'forward_return_3m': -5.2,
            'benchmark_return_3m': 8.0,
            'alpha_3m': -13.2
        },
        {
            'symbol': 'WIPRO',
            'date': '2024-02-01',
            'forward_return_3m': 18.3,
            'benchmark_return_3m': 10.5,
            'alpha_3m': 7.8
        }
    ]

    calculator = EquityCurveCalculator()

    # Calculate equity curve
    equity_curve = calculator.calculate_equity_curve(example_signals)
    print("\nEquity Curve:")
    print(f"Dates: {equity_curve['dates']}")
    print(f"Portfolio Value: {equity_curve['portfolio_value']}")
    print(f"Cumulative Return: {equity_curve['cumulative_return']}")
    print(f"Alpha: {equity_curve['alpha']}")

    # Calculate statistics
    stats = calculator.calculate_trade_statistics(example_signals)
    print("\nTrade Statistics:")
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate']}%")
    print(f"Sharpe Ratio: {stats['sharpe_ratio']}")
    print(f"Max Drawdown: {stats['max_drawdown']}%")
