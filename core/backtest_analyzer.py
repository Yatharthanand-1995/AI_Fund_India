"""
Backtest Analyzer - Advanced analysis of backtest results

This module provides:
1. Agent performance correlation analysis
2. Optimal weight calculation using constrained optimization
3. Sector performance breakdown
4. Market regime performance analysis
5. Actionable recommendations for system improvement
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from collections import defaultdict

from core.backtester import BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent"""
    agent_name: str
    correlation_with_returns: float
    avg_score: float
    current_weight: float
    optimal_weight: float
    weight_change: float
    predictive_power: str  # 'Strong', 'Moderate', 'Weak'


@dataclass
class OptimalWeights:
    """Optimal weight recommendations"""
    weights: Dict[str, float]
    expected_improvement: float  # Expected improvement in Sharpe ratio
    current_sharpe: float
    optimal_sharpe: float
    methodology: str


class BacktestAnalyzer:
    """
    Advanced analyzer for backtest results

    Usage:
        analyzer = BacktestAnalyzer()
        analysis = analyzer.analyze_comprehensive(results)
        optimal_weights = analyzer.calculate_optimal_weights(results, current_weights)
        recommendations = analyzer.generate_recommendations(analysis)
    """

    def __init__(self):
        """Initialize backtest analyzer"""
        logger.info("BacktestAnalyzer initialized")

    def analyze_comprehensive(
        self,
        results: List[BacktestResult],
        current_weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Comprehensive analysis of backtest results

        Args:
            results: List of BacktestResult objects
            current_weights: Current agent weights

        Returns:
            Dict with all analysis results
        """
        logger.info(f"Running comprehensive analysis on {len(results)} results")

        if current_weights is None:
            current_weights = {
                'fundamentals': 0.36,
                'momentum': 0.27,
                'quality': 0.18,
                'sentiment': 0.09,
                'institutional_flow': 0.10
            }

        analysis = {
            'agent_performance': self.analyze_agent_performance(results, current_weights),
            'optimal_weights': self.calculate_optimal_weights(results, current_weights),
            'sector_performance': self.analyze_by_sector(results),
            'time_series_performance': self.analyze_time_series(results),
            'recommendations': []  # Will be filled after analysis
        }

        # Generate recommendations based on analysis
        analysis['recommendations'] = self.generate_recommendations(
            analysis['agent_performance'],
            analysis['optimal_weights'],
            analysis['sector_performance']
        )

        return analysis

    def analyze_agent_performance(
        self,
        results: List[BacktestResult],
        current_weights: Dict[str, float]
    ) -> List[AgentPerformance]:
        """
        Analyze correlation between agent scores and forward returns

        Args:
            results: List of BacktestResult objects
            current_weights: Current agent weights

        Returns:
            List of AgentPerformance objects sorted by correlation
        """
        logger.info("Analyzing agent performance correlations")

        agents = ['fundamentals', 'momentum', 'quality', 'sentiment', 'institutional_flow']
        performance_metrics = []

        # Extract returns (use 3M alpha as primary metric)
        returns = np.array([r.alpha_3m for r in results if r.alpha_3m is not None])

        if len(returns) < 10:
            logger.warning("Insufficient data for correlation analysis")
            return []

        for agent in agents:
            # Extract agent scores
            scores = np.array([
                r.agent_scores.get(agent, 50.0)
                for r in results
                if r.alpha_3m is not None
            ])

            # Calculate correlation
            if len(scores) > 1 and len(returns) > 1 and len(scores) == len(returns):
                correlation = np.corrcoef(scores, returns)[0, 1]
                avg_score = np.mean(scores)

                # Classify predictive power
                abs_corr = abs(correlation)
                if abs_corr > 0.4:
                    power = 'Strong'
                elif abs_corr > 0.2:
                    power = 'Moderate'
                else:
                    power = 'Weak'

                performance_metrics.append(AgentPerformance(
                    agent_name=agent,
                    correlation_with_returns=correlation,
                    avg_score=avg_score,
                    current_weight=current_weights.get(agent, 0.0),
                    optimal_weight=0.0,  # Will be calculated later
                    weight_change=0.0,
                    predictive_power=power
                ))
            else:
                logger.warning(f"Could not calculate correlation for {agent}")

        # Sort by absolute correlation (strongest predictors first)
        performance_metrics.sort(key=lambda x: abs(x.correlation_with_returns), reverse=True)

        logger.info(f"Agent performance analysis complete: {len(performance_metrics)} agents analyzed")
        return performance_metrics

    def calculate_optimal_weights(
        self,
        results: List[BacktestResult],
        current_weights: Dict[str, float]
    ) -> OptimalWeights:
        """
        Calculate optimal agent weights using constrained optimization

        Uses linear regression with constraints:
        - All weights sum to 1.0
        - All weights >= 0
        - Maximize correlation with forward returns

        Args:
            results: List of BacktestResult objects
            current_weights: Current agent weights

        Returns:
            OptimalWeights object with recommendations
        """
        logger.info("Calculating optimal agent weights")

        agents = ['fundamentals', 'momentum', 'quality', 'sentiment', 'institutional_flow']

        # Extract features (agent scores) and targets (forward returns)
        X = []
        y = []

        for result in results:
            if result.alpha_3m is not None:
                X.append([
                    result.agent_scores.get('fundamentals', 50.0),
                    result.agent_scores.get('momentum', 50.0),
                    result.agent_scores.get('quality', 50.0),
                    result.agent_scores.get('sentiment', 50.0),
                    result.agent_scores.get('institutional_flow', 50.0)
                ])
                y.append(result.alpha_3m)

        if len(X) < 20:
            logger.warning("Insufficient data for optimal weight calculation")
            return OptimalWeights(
                weights=current_weights,
                expected_improvement=0.0,
                current_sharpe=0.0,
                optimal_sharpe=0.0,
                methodology='Insufficient data - using current weights'
            )

        X = np.array(X)
        y = np.array(y)

        # Normalize features to 0-1 range for numerical stability
        X_norm = (X - 50.0) / 50.0

        try:
            from scipy.optimize import minimize

            # Objective: Minimize negative correlation (maximize correlation)
            def objective(weights):
                predictions = np.dot(X_norm, weights)
                correlation = np.corrcoef(predictions, y)[0, 1]
                return -correlation  # Negative because we minimize

            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},  # Sum to 1
            ]

            # Bounds: each weight between 0 and 0.6 (max 60%)
            bounds = [(0.0, 0.6) for _ in agents]

            # Initial weights
            initial_weights = np.array([current_weights[agent] for agent in agents])

            # Optimize
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )

            if result.success:
                optimal_weights_array = result.x

                # Normalize to exactly 1.0 (handle floating point errors)
                optimal_weights_array = optimal_weights_array / optimal_weights_array.sum()

                optimal_weights_dict = {
                    agent: float(weight)
                    for agent, weight in zip(agents, optimal_weights_array)
                }

                # Calculate current and optimal Sharpe ratios
                current_predictions = np.dot(X_norm, initial_weights)
                optimal_predictions = np.dot(X_norm, optimal_weights_array)

                current_sharpe = np.mean(current_predictions) / np.std(current_predictions) if np.std(current_predictions) > 0 else 0
                optimal_sharpe = np.mean(optimal_predictions) / np.std(optimal_predictions) if np.std(optimal_predictions) > 0 else 0

                expected_improvement = optimal_sharpe - current_sharpe

                logger.info(f"Optimal weights calculated: {optimal_weights_dict}")
                logger.info(f"Expected Sharpe improvement: {expected_improvement:.3f}")

                return OptimalWeights(
                    weights=optimal_weights_dict,
                    expected_improvement=expected_improvement,
                    current_sharpe=current_sharpe,
                    optimal_sharpe=optimal_sharpe,
                    methodology='Constrained optimization (SLSQP) maximizing correlation with 3M alpha'
                )
            else:
                logger.warning(f"Optimization failed: {result.message}")
                return OptimalWeights(
                    weights=current_weights,
                    expected_improvement=0.0,
                    current_sharpe=0.0,
                    optimal_sharpe=0.0,
                    methodology=f'Optimization failed - using current weights'
                )

        except ImportError:
            logger.warning("scipy not available for optimization")
            # Fallback: Use correlation-based weighting
            return self._calculate_correlation_based_weights(results, current_weights)

        except Exception as e:
            logger.error(f"Error calculating optimal weights: {e}")
            return OptimalWeights(
                weights=current_weights,
                expected_improvement=0.0,
                current_sharpe=0.0,
                optimal_sharpe=0.0,
                methodology=f'Error: {str(e)}'
            )

    def _calculate_correlation_based_weights(
        self,
        results: List[BacktestResult],
        current_weights: Dict[str, float]
    ) -> OptimalWeights:
        """
        Fallback method: Weight agents by their correlation with returns

        Args:
            results: List of BacktestResult objects
            current_weights: Current agent weights

        Returns:
            OptimalWeights based on correlation weighting
        """
        logger.info("Using correlation-based weight calculation (fallback)")

        agents = ['fundamentals', 'momentum', 'quality', 'sentiment', 'institutional_flow']
        returns = np.array([r.alpha_3m for r in results if r.alpha_3m is not None])

        correlations = {}
        for agent in agents:
            scores = np.array([
                r.agent_scores.get(agent, 50.0)
                for r in results
                if r.alpha_3m is not None
            ])

            if len(scores) > 1 and len(returns) > 1:
                corr = abs(np.corrcoef(scores, returns)[0, 1])
                correlations[agent] = max(0, corr)  # Positive correlations only
            else:
                correlations[agent] = 0.0

        # Normalize correlations to sum to 1.0
        total_corr = sum(correlations.values())
        if total_corr > 0:
            optimal_weights = {agent: corr / total_corr for agent, corr in correlations.items()}
        else:
            optimal_weights = current_weights

        return OptimalWeights(
            weights=optimal_weights,
            expected_improvement=0.0,
            current_sharpe=0.0,
            optimal_sharpe=0.0,
            methodology='Correlation-based weighting (fallback method)'
        )

    def analyze_by_sector(self, results: List[BacktestResult]) -> Dict[str, Dict]:
        """
        Analyze performance broken down by sector

        Args:
            results: List of BacktestResult objects

        Returns:
            Dict mapping sector to performance metrics
        """
        logger.info("Analyzing performance by sector")

        # Group results by sector (extract from symbol if available)
        sector_results = defaultdict(list)

        for result in results:
            # For now, just aggregate all results
            # TODO: Add sector mapping
            sector = 'ALL'
            sector_results[sector].append(result)

        sector_performance = {}
        for sector, sector_res in sector_results.items():
            alphas = [r.alpha_3m for r in sector_res if r.alpha_3m is not None]
            returns = [r.forward_return_3m for r in sector_res if r.forward_return_3m is not None]

            if alphas:
                sector_performance[sector] = {
                    'count': len(sector_res),
                    'avg_alpha': np.mean(alphas),
                    'avg_return': np.mean(returns) if returns else 0.0,
                    'hit_rate': sum(1 for a in alphas if a > 0) / len(alphas) * 100,
                    'sharpe': (np.mean(alphas) / np.std(alphas)) if np.std(alphas) > 0 else 0
                }

        return sector_performance

    def analyze_time_series(self, results: List[BacktestResult]) -> Dict:
        """
        Analyze performance over time

        Args:
            results: List of BacktestResult objects

        Returns:
            Dict with time series metrics
        """
        logger.info("Analyzing time series performance")

        # Sort by date
        sorted_results = sorted(results, key=lambda r: r.date)

        # Calculate cumulative returns
        cumulative_returns = []
        cumulative_alpha = []
        running_sum = 0.0
        running_alpha = 0.0

        for result in sorted_results:
            if result.forward_return_3m is not None:
                running_sum += result.forward_return_3m
                cumulative_returns.append(running_sum)

            if result.alpha_3m is not None:
                running_alpha += result.alpha_3m
                cumulative_alpha.append(running_alpha)

        return {
            'cumulative_returns': cumulative_returns,
            'cumulative_alpha': cumulative_alpha,
            'total_return': running_sum,
            'total_alpha': running_alpha,
            'num_periods': len(sorted_results)
        }

    def generate_recommendations(
        self,
        agent_performance: List[AgentPerformance],
        optimal_weights: OptimalWeights,
        sector_performance: Dict[str, Dict]
    ) -> List[str]:
        """
        Generate actionable recommendations for system improvement

        Args:
            agent_performance: List of AgentPerformance objects
            optimal_weights: OptimalWeights object
            sector_performance: Sector performance dict

        Returns:
            List of recommendation strings
        """
        logger.info("Generating recommendations")

        recommendations = []

        # Weight adjustment recommendations
        for agent_name, optimal_weight in optimal_weights.weights.items():
            # Find current weight
            agent_perf = next((ap for ap in agent_performance if ap.agent_name == agent_name), None)
            if agent_perf:
                current_weight = agent_perf.current_weight
                diff = optimal_weight - current_weight

                if abs(diff) > 0.03:  # >3% difference
                    direction = "Increase" if diff > 0 else "Decrease"
                    recommendations.append(
                        f"{direction} {agent_name} weight from {current_weight:.1%} to {optimal_weight:.1%} "
                        f"({diff:+.1%} change)"
                    )

        # Agent performance insights
        for agent_perf in agent_performance:
            correlation = agent_perf.correlation_with_returns

            if agent_perf.predictive_power == 'Strong':
                recommendations.append(
                    f"{agent_perf.agent_name.title()} shows strong predictive power "
                    f"(correlation: {correlation:+.2f}) - maintain or increase weight"
                )
            elif agent_perf.predictive_power == 'Weak':
                recommendations.append(
                    f"{agent_perf.agent_name.title()} shows weak correlation "
                    f"({correlation:+.2f}) - review algorithm or reduce weight"
                )

        # Sector insights
        if sector_performance:
            best_sector = max(sector_performance, key=lambda k: sector_performance[k]['avg_alpha'])
            best_metrics = sector_performance[best_sector]

            if best_sector != 'ALL':
                recommendations.append(
                    f"{best_sector} sector showing strongest signals "
                    f"(avg alpha: {best_metrics['avg_alpha']:+.2f}%, hit rate: {best_metrics['hit_rate']:.1f}%)"
                )

        # Overall system recommendations
        if optimal_weights.expected_improvement > 0.1:
            recommendations.append(
                f"Switching to optimal weights could improve Sharpe ratio by {optimal_weights.expected_improvement:.2f}"
            )

        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*70)
    print("BACKTEST ANALYZER - Example Usage")
    print("="*70)
    print("\nThis module provides advanced analysis of backtest results.")
    print("Use it after running a backtest to get optimal weight recommendations.")
