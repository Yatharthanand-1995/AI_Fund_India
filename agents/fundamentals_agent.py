"""
Fundamentals Agent - Financial Health Analysis (36% weight)

Analyzes:
- Profitability: ROE, ROA, Net Profit Margin, Operating Margin
- Growth: Revenue growth, Earnings growth, EPS growth
- Valuation: P/E, P/B, PEG ratios (adjusted for Indian market)
- Financial Health: Debt-to-Equity, Current Ratio, Free Cash Flow
- Indian-specific: Promoter holding percentage

Scoring: 0-100 with confidence level
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FundamentalsAgent:
    """
    Fundamentals Agent for Indian stock market

    Scoring breakdown (0-100):
    - Profitability: 40 points
    - Valuation: 30 points
    - Growth: 20 points
    - Financial Health: 10 points
    - Bonus: Promoter holding (+5 points)

    Confidence factors:
    - Base: 0.5
    - +0.2 if has financials
    - +0.1 if has quarterly data
    - +0.1 if data is in INR
    - +0.1 if has promoter holding
    """

    # Indian market benchmarks (lower than US market)
    BENCHMARKS = {
        # ROE thresholds (Indian companies typically have lower ROE)
        'roe_excellent': 15.0,    # vs 20% in US
        'roe_good': 12.0,         # vs 15% in US
        'roe_fair': 8.0,          # vs 10% in US
        'roe_poor': 5.0,

        # P/E ratio thresholds (Indian market trades at lower multiples)
        'pe_undervalued': 12.0,   # vs 15 in US
        'pe_fair': 18.0,          # vs 20 in US
        'pe_expensive': 25.0,     # vs 30 in US
        'pe_overvalued': 35.0,

        # P/B ratio
        'pb_undervalued': 1.5,
        'pb_fair': 3.0,
        'pb_expensive': 5.0,

        # Growth thresholds
        'revenue_growth_high': 20.0,
        'revenue_growth_medium': 10.0,
        'revenue_growth_low': 5.0,

        # Debt levels
        'debt_low': 0.5,
        'debt_moderate': 1.0,
        'debt_high': 2.0,

        # Promoter holding (important in India)
        'promoter_high': 50.0,    # High promoter confidence
        'promoter_medium': 30.0,
    }

    def __init__(self):
        """Initialize Fundamentals Agent"""
        self.agent_name = "FundamentalsAgent"
        self.weight = 0.36  # 36% of total score

    def analyze(self, symbol: str, cached_data: Optional[Dict] = None) -> Dict:
        """
        Analyze fundamental metrics for a stock

        Args:
            symbol: Stock symbol (e.g., "TCS")
            cached_data: Pre-fetched comprehensive data from provider

        Returns:
            {
                'score': float (0-100),
                'confidence': float (0-1),
                'reasoning': str,
                'metrics': {
                    'roe': float,
                    'pe_ratio': float,
                    'pb_ratio': float,
                    'revenue_growth': float,
                    'debt_to_equity': float,
                    'current_ratio': float,
                    'profit_margin': float,
                    'promoter_holding': float,
                    ...
                },
                'breakdown': {
                    'profitability_score': float,
                    'valuation_score': float,
                    'growth_score': float,
                    'health_score': float
                }
            }
        """
        logger.info(f"Analyzing fundamentals for {symbol}")

        try:
            # Extract financial data
            info = cached_data.get('info', {}) if cached_data else {}
            financials = cached_data.get('financials', pd.DataFrame()) if cached_data else pd.DataFrame()

            # Extract key metrics
            metrics = self._extract_metrics(symbol, info, financials)

            # Calculate component scores
            profitability_score = self._score_profitability(metrics)
            valuation_score = self._score_valuation(metrics)
            growth_score = self._score_growth(metrics)
            health_score = self._score_financial_health(metrics)
            promoter_bonus = self._score_promoter_holding(metrics)

            # Calculate total score (max 105, capped at 100)
            total_score = min(100,
                profitability_score +
                valuation_score +
                growth_score +
                health_score +
                promoter_bonus
            )

            # Calculate confidence
            confidence = self._calculate_confidence(metrics, financials)

            # Generate reasoning
            reasoning = self._generate_reasoning(metrics, {
                'profitability': profitability_score,
                'valuation': valuation_score,
                'growth': growth_score,
                'health': health_score
            })

            return {
                'score': round(total_score, 2),
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'metrics': metrics,
                'breakdown': {
                    'profitability_score': round(profitability_score, 2),
                    'valuation_score': round(valuation_score, 2),
                    'growth_score': round(growth_score, 2),
                    'health_score': round(health_score, 2),
                    'promoter_bonus': round(promoter_bonus, 2)
                },
                'agent': self.agent_name
            }

        except Exception as e:
            logger.error(f"Fundamentals analysis failed for {symbol}: {e}", exc_info=True)
            return {
                'score': 50.0,  # Neutral score on failure
                'confidence': 0.1,
                'reasoning': f"Analysis failed: {str(e)}",
                'metrics': {},
                'breakdown': {},
                'agent': self.agent_name,
                'error': str(e)
            }

    def _extract_metrics(self, symbol: str, info: Dict, financials: pd.DataFrame) -> Dict:
        """Extract all relevant financial metrics"""
        metrics = {}

        # Profitability metrics
        metrics['roe'] = self._get_safe_value(info, 'returnOnEquity', multiply=100)
        metrics['roa'] = self._get_safe_value(info, 'returnOnAssets', multiply=100)
        metrics['profit_margin'] = self._get_safe_value(info, 'profitMargins', multiply=100)
        metrics['operating_margin'] = self._get_safe_value(info, 'operatingMargins', multiply=100)

        # Valuation metrics
        metrics['pe_ratio'] = self._get_safe_value(info, 'trailingPE')
        metrics['forward_pe'] = self._get_safe_value(info, 'forwardPE')
        metrics['pb_ratio'] = self._get_safe_value(info, 'priceToBook')
        metrics['peg_ratio'] = self._get_safe_value(info, 'pegRatio')
        metrics['ev_to_ebitda'] = self._get_safe_value(info, 'enterpriseToEbitda')

        # Growth metrics
        metrics['revenue_growth'] = self._get_safe_value(info, 'revenueGrowth', multiply=100)
        metrics['earnings_growth'] = self._get_safe_value(info, 'earningsGrowth', multiply=100)
        metrics['earnings_quarterly_growth'] = self._get_safe_value(info, 'earningsQuarterlyGrowth', multiply=100)

        # Financial health metrics
        metrics['debt_to_equity'] = self._get_safe_value(info, 'debtToEquity', divide=100)
        metrics['current_ratio'] = self._get_safe_value(info, 'currentRatio')
        metrics['quick_ratio'] = self._get_safe_value(info, 'quickRatio')
        metrics['free_cash_flow'] = self._get_safe_value(info, 'freeCashflow')

        # Indian-specific metrics
        metrics['promoter_holding'] = self._get_safe_value(info, 'heldPercentInsiders', multiply=100)
        # Alternative names for promoter holding
        if metrics['promoter_holding'] is None:
            metrics['promoter_holding'] = self._get_safe_value(info, 'insiderOwnership', multiply=100)

        # Market metrics
        metrics['market_cap'] = self._get_safe_value(info, 'marketCap')
        metrics['book_value'] = self._get_safe_value(info, 'bookValue')

        # Additional context
        metrics['sector'] = info.get('sector', 'Unknown')
        metrics['industry'] = info.get('industry', 'Unknown')

        logger.debug(f"Extracted {len([v for v in metrics.values() if v is not None])} metrics for {symbol}")
        return metrics

    def _get_safe_value(self, data: Dict, key: str, multiply: float = 1.0, divide: float = 1.0) -> Optional[float]:
        """Safely extract and convert a value"""
        try:
            value = data.get(key)
            if value is None or value == 'N/A':
                return None
            value = float(value)
            if multiply != 1.0:
                value *= multiply
            if divide != 1.0:
                value /= divide
            # Sanity check for unrealistic values
            if abs(value) > 1e10:
                return None
            return value
        except (ValueError, TypeError):
            return None

    def _score_profitability(self, metrics: Dict) -> float:
        """
        Score profitability (40 points max)

        Components:
        - ROE: 25 points
        - Profit margins: 10 points
        - ROA: 5 points
        """
        score = 0.0
        roe = metrics.get('roe')
        profit_margin = metrics.get('profit_margin')
        roa = metrics.get('roa')

        # ROE scoring (25 points) - Most important for Indian stocks
        if roe is not None:
            if roe >= self.BENCHMARKS['roe_excellent']:
                score += 25
            elif roe >= self.BENCHMARKS['roe_good']:
                score += 20
            elif roe >= self.BENCHMARKS['roe_fair']:
                score += 15
            elif roe >= self.BENCHMARKS['roe_poor']:
                score += 10
            elif roe > 0:
                score += 5

        # Profit margin scoring (10 points)
        if profit_margin is not None:
            if profit_margin >= 20:
                score += 10
            elif profit_margin >= 15:
                score += 8
            elif profit_margin >= 10:
                score += 6
            elif profit_margin >= 5:
                score += 4
            elif profit_margin > 0:
                score += 2

        # ROA scoring (5 points)
        if roa is not None:
            if roa >= 10:
                score += 5
            elif roa >= 7:
                score += 4
            elif roa >= 5:
                score += 3
            elif roa > 0:
                score += 1

        return min(40, score)

    def _score_valuation(self, metrics: Dict) -> float:
        """
        Score valuation (30 points max)

        Components:
        - P/E ratio: 20 points
        - P/B ratio: 7 points
        - PEG ratio: 3 points
        """
        score = 0.0
        pe = metrics.get('pe_ratio')
        pb = metrics.get('pb_ratio')
        peg = metrics.get('peg_ratio')

        # P/E scoring (20 points) - Adjusted for Indian market
        if pe is not None and pe > 0:
            if pe < self.BENCHMARKS['pe_undervalued']:
                score += 20  # Undervalued
            elif pe < self.BENCHMARKS['pe_fair']:
                score += 16  # Fair value
            elif pe < self.BENCHMARKS['pe_expensive']:
                score += 12  # Slightly expensive
            elif pe < self.BENCHMARKS['pe_overvalued']:
                score += 6   # Expensive
            else:
                score += 2   # Very expensive

        # P/B scoring (7 points)
        if pb is not None and pb > 0:
            if pb < self.BENCHMARKS['pb_undervalued']:
                score += 7
            elif pb < self.BENCHMARKS['pb_fair']:
                score += 5
            elif pb < self.BENCHMARKS['pb_expensive']:
                score += 3
            else:
                score += 1

        # PEG ratio scoring (3 points) - Growth adjusted
        if peg is not None and peg > 0:
            if peg < 1.0:
                score += 3  # Undervalued relative to growth
            elif peg < 1.5:
                score += 2
            elif peg < 2.0:
                score += 1

        return min(30, score)

    def _score_growth(self, metrics: Dict) -> float:
        """
        Score growth (20 points max)

        Components:
        - Revenue growth: 12 points
        - Earnings growth: 8 points
        """
        score = 0.0
        revenue_growth = metrics.get('revenue_growth')
        earnings_growth = metrics.get('earnings_growth')

        # Revenue growth scoring (12 points)
        if revenue_growth is not None:
            if revenue_growth >= self.BENCHMARKS['revenue_growth_high']:
                score += 12
            elif revenue_growth >= self.BENCHMARKS['revenue_growth_medium']:
                score += 9
            elif revenue_growth >= self.BENCHMARKS['revenue_growth_low']:
                score += 6
            elif revenue_growth > 0:
                score += 3
            # Negative growth penalty
            elif revenue_growth < -10:
                score -= 3

        # Earnings growth scoring (8 points)
        if earnings_growth is not None:
            if earnings_growth >= 20:
                score += 8
            elif earnings_growth >= 10:
                score += 6
            elif earnings_growth >= 5:
                score += 4
            elif earnings_growth > 0:
                score += 2
            # Negative growth penalty
            elif earnings_growth < -10:
                score -= 2

        return max(0, min(20, score))

    def _score_financial_health(self, metrics: Dict) -> float:
        """
        Score financial health (10 points max)

        Components:
        - Debt-to-Equity: 6 points
        - Current Ratio: 4 points
        """
        score = 0.0
        debt_to_equity = metrics.get('debt_to_equity')
        current_ratio = metrics.get('current_ratio')

        # Debt-to-Equity scoring (6 points) - Lower is better
        if debt_to_equity is not None:
            if debt_to_equity < self.BENCHMARKS['debt_low']:
                score += 6  # Very low debt
            elif debt_to_equity < self.BENCHMARKS['debt_moderate']:
                score += 4  # Moderate debt
            elif debt_to_equity < self.BENCHMARKS['debt_high']:
                score += 2  # High debt
            else:
                score += 0  # Very high debt (concerning)

        # Current Ratio scoring (4 points) - Liquidity
        if current_ratio is not None:
            if current_ratio >= 2.0:
                score += 4  # Excellent liquidity
            elif current_ratio >= 1.5:
                score += 3
            elif current_ratio >= 1.0:
                score += 2
            else:
                score += 0  # Poor liquidity

        return min(10, score)

    def _score_promoter_holding(self, metrics: Dict) -> float:
        """
        Score promoter holding (bonus up to 5 points)

        In India, high promoter holding indicates:
        - Strong promoter confidence
        - Less risk of hostile takeover
        - Alignment with shareholders
        """
        promoter = metrics.get('promoter_holding')

        if promoter is None:
            return 0.0

        if promoter >= self.BENCHMARKS['promoter_high']:
            return 5.0  # High promoter confidence
        elif promoter >= self.BENCHMARKS['promoter_medium']:
            return 3.0  # Medium promoter holding
        elif promoter >= 10.0:
            return 1.0  # Low promoter holding
        else:
            return 0.0

    def _calculate_confidence(self, metrics: Dict, financials: pd.DataFrame) -> float:
        """
        Calculate confidence level (0-1)

        Factors:
        - Base: 0.5
        - Has key metrics: +0.2
        - Has financials: +0.1
        - Has growth data: +0.1
        - Has promoter data: +0.1
        """
        confidence = 0.5  # Base confidence

        # Check for key metrics
        key_metrics = ['roe', 'pe_ratio', 'revenue_growth', 'debt_to_equity']
        available_key_metrics = sum(1 for m in key_metrics if metrics.get(m) is not None)
        if available_key_metrics >= 3:
            confidence += 0.2
        elif available_key_metrics >= 2:
            confidence += 0.1

        # Has financials
        if not financials.empty:
            confidence += 0.1

        # Has growth data
        if metrics.get('revenue_growth') is not None:
            confidence += 0.1

        # Has promoter holding (Indian-specific)
        if metrics.get('promoter_holding') is not None:
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_reasoning(self, metrics: Dict, breakdown: Dict) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        # ROE
        roe = metrics.get('roe')
        if roe is not None:
            if roe >= self.BENCHMARKS['roe_excellent']:
                reasons.append(f"Excellent ROE: {roe:.1f}%")
            elif roe >= self.BENCHMARKS['roe_good']:
                reasons.append(f"Strong ROE: {roe:.1f}%")
            elif roe < self.BENCHMARKS['roe_poor']:
                reasons.append(f"Weak ROE: {roe:.1f}%")

        # P/E ratio
        pe = metrics.get('pe_ratio')
        if pe is not None:
            if pe < self.BENCHMARKS['pe_undervalued']:
                reasons.append(f"Undervalued P/E: {pe:.1f}")
            elif pe > self.BENCHMARKS['pe_expensive']:
                reasons.append(f"High P/E: {pe:.1f}")

        # Revenue growth
        rev_growth = metrics.get('revenue_growth')
        if rev_growth is not None:
            if rev_growth >= self.BENCHMARKS['revenue_growth_high']:
                reasons.append(f"High growth: {rev_growth:.1f}%")
            elif rev_growth < 0:
                reasons.append(f"Declining revenue: {rev_growth:.1f}%")

        # Debt
        debt = metrics.get('debt_to_equity')
        if debt is not None:
            if debt < self.BENCHMARKS['debt_low']:
                reasons.append(f"Low debt: {debt:.2f}")
            elif debt > self.BENCHMARKS['debt_high']:
                reasons.append(f"High debt: {debt:.2f}")

        # Promoter holding
        promoter = metrics.get('promoter_holding')
        if promoter is not None and promoter >= self.BENCHMARKS['promoter_high']:
            reasons.append(f"High promoter confidence: {promoter:.1f}%")

        if not reasons:
            reasons.append("Limited financial data available")

        return " | ".join(reasons)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = FundamentalsAgent()

    # Test with sample data
    sample_data = {
        'info': {
            'returnOnEquity': 0.18,  # 18% ROE
            'trailingPE': 15.5,
            'priceToBook': 2.8,
            'revenueGrowth': 0.12,  # 12% growth
            'debtToEquity': 45,  # 0.45 after conversion
            'currentRatio': 1.8,
            'heldPercentInsiders': 0.55,  # 55% promoter holding
            'profitMargins': 0.15,
            'sector': 'Technology'
        },
        'financials': pd.DataFrame({'Revenue': [1000, 1200, 1350]})
    }

    result = agent.analyze("TCS", sample_data)

    print(f"\n{'='*60}")
    print(f"Fundamentals Analysis for TCS")
    print('='*60)
    print(f"Score: {result['score']}/100")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"\nBreakdown:")
    for key, value in result['breakdown'].items():
        print(f"  {key}: {value}")
    print(f"\nKey Metrics:")
    for key, value in result['metrics'].items():
        if value is not None and isinstance(value, (int, float)):
            print(f"  {key}: {value:.2f}")
