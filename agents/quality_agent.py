"""
Quality Agent - Business Quality Analysis (18% weight)

Scoring methodology aligned with NSE Quality 30 Index:
  - Return on Equity (ROE): 40 pts — primary quality signal
  - Debt/Equity leverage:   35 pts — balance sheet health
  - Earnings stability:     25 pts — EPS growth variability (σ)

No base-50 fallback. Stocks without fundamental data return score=None
and are excluded from the composite (weights renormalize to other agents).

Price metrics (volatility, drawdown) are still computed and exposed in
the metrics dict for screener filters and display, but do NOT contribute
to the quality score — those are momentum/risk signals, not quality signals.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

from utils.math_helpers import safe_divide
from utils.metric_extraction import MetricExtractor
from utils.validation import validate_price_dataframe_schema
from core.exceptions import DataValidationException, InsufficientDataException, CalculationException

logger = logging.getLogger(__name__)


class QualityAgent:
    """
    Quality Agent for Indian stock market — NSE Quality 30 methodology.

    Scoring breakdown (0–100, additive, no base offset):
      ROE score:       0–40 pts  (returnOnEquity from yfinance, 0-1 scale)
      Leverage score:  0–35 pts  (debtToEquity from yfinance, full ratio)
      Stability score: 0–25 pts  (σ of EPS growth or profit margin)
    """

    def __init__(self, sector_mapping: Optional[Dict] = None):
        self.agent_name = "QualityAgent"
        self.weight = 0.18
        self.sector_mapping = sector_mapping or {}

    def analyze(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        cached_data: Optional[Dict] = None,
        market_regime: Optional[str] = None
    ) -> Dict:
        """
        Analyze business quality using fundamental metrics.

        Returns score=None with status='no_data' when fundamental data is absent,
        causing the composite to renormalize weights rather than pull toward 50.
        """
        logger.info(f"Analyzing quality for {symbol}")

        try:
            validate_price_dataframe_schema(price_data, symbol)

            info = (cached_data or {}).get('info', {})
            metrics = self._extract_metrics(symbol, price_data, cached_data, info)

            # Require at least one fundamental signal to produce a score
            has_quality_data = any(
                metrics.get(f) is not None
                for f in ('roe', 'debt_to_equity_raw', 'eps_variability', 'profit_margin_stability')
            )
            if not has_quality_data:
                logger.info(f"No fundamental quality data for {symbol} — excluding from composite")
                return {
                    'score': None,
                    'confidence': 0.0,
                    'status': 'no_data',
                    'reasoning': 'No fundamental quality data available',
                    'metrics': metrics,
                    'breakdown': {},
                    'agent': self.agent_name
                }

            roe_score = self._score_roe(metrics)
            leverage_score = self._score_leverage(metrics)
            stability_score = self._score_earnings_stability(metrics)

            total_score = max(0.0, min(100.0, roe_score + leverage_score + stability_score))

            confidence = self._calculate_confidence(price_data, metrics)
            reasoning = self._generate_reasoning(metrics, roe_score, leverage_score, stability_score)

            return {
                'score': round(total_score, 2),
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'metrics': metrics,
                'breakdown': {
                    'roe_score': round(roe_score, 2),
                    'leverage_score': round(leverage_score, 2),
                    'stability_score': round(stability_score, 2),
                },
                'status': 'success',
                'agent': self.agent_name
            }

        except DataValidationException as e:
            logger.warning(f"Data validation failed for {symbol}: {e}")
            return self._error_result(symbol, str(e), 'validation')

        except InsufficientDataException as e:
            logger.info(f"Insufficient data for {symbol}: {e}")
            return self._error_result(symbol, str(e), 'insufficient_data')

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Data format error for {symbol}: {e}")
            return self._error_result(symbol, str(e), 'data_format')

        except Exception as e:
            logger.error(f"Unexpected error analyzing {symbol}: {e}", exc_info=True)
            return self._error_result(symbol, str(e), 'unknown')

    def _error_result(self, symbol: str, error: str, category: str) -> Dict:
        return {
            'score': None,
            'confidence': 0.0,
            'reasoning': f"Quality analysis failed: {error}",
            'metrics': {},
            'breakdown': {},
            'agent': self.agent_name,
            'status': 'error',
            'error': error,
            'error_category': category
        }

    # -------------------------------------------------------------------------
    # Metric extraction
    # -------------------------------------------------------------------------

    def _extract_metrics(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        cached_data: Optional[Dict],
        info: Dict
    ) -> Dict:
        metrics: Dict = {}

        # ---- Sector / market cap (display / screener) ----
        raw_sector = info.get('sector', 'Unknown')
        metrics['sector'] = raw_sector if raw_sector and raw_sector != 'None' else 'Unknown'
        metrics['market_cap'] = info.get('marketCap')

        # ---- NSE Quality 30 fundamental signals ----
        roe = info.get('returnOnEquity')           # yfinance: 0-1 scale (e.g. 0.18 = 18%)
        metrics['roe'] = float(roe) if roe is not None else None

        dte = info.get('debtToEquity')             # yfinance: full ratio (e.g. 45.2 = 0.452x)
        metrics['debt_to_equity_raw'] = float(dte) if dte is not None else None
        # Actual ratio for display (divide by 100 as per yfinance convention)
        metrics['debt_to_equity'] = round(float(dte) / 100, 3) if dte is not None else None

        metrics['return_on_assets'] = info.get('returnOnAssets')
        metrics['profit_margins'] = info.get('profitMargins')

        # Earnings/margin stability from historical data
        metrics['eps_variability'] = self._calc_eps_variability(cached_data)
        metrics['profit_margin_stability'] = self._calc_margin_stability(cached_data)

        # ---- Price metrics (for screener filters and display only — not scored) ----
        metrics['volatility'] = self._calculate_volatility(price_data)
        metrics['max_drawdown'] = self._calculate_max_drawdown(price_data)
        metrics['current_drawdown'] = self._calculate_current_drawdown(price_data)
        metrics['return_consistency'] = self._calculate_return_consistency(price_data)
        metrics['1y_return'] = self._calculate_return(price_data, days=252)
        metrics['6m_return'] = self._calculate_return(price_data, days=126)
        metrics['price_range_52w'] = self._calculate_52w_range(price_data)

        logger.debug(f"Extracted {sum(1 for v in metrics.values() if v is not None)} quality metrics")
        return metrics

    def _calc_eps_variability(self, cached_data: Optional[Dict]) -> Optional[float]:
        """σ of YoY EPS growth from earnings history."""
        try:
            if not cached_data:
                return None
            # Try dedicated earnings DataFrame first
            earnings = cached_data.get('earnings')
            if earnings is not None and isinstance(earnings, pd.DataFrame) and not earnings.empty:
                eps_col = next((c for c in earnings.columns if 'earnings' in c.lower() or 'eps' in c.lower()), None)
                if eps_col:
                    values = earnings[eps_col].dropna()
                    if len(values) >= 3:
                        growth = values.pct_change().dropna()
                        growth = growth[np.isfinite(growth)]
                        if len(growth) >= 2:
                            return float(growth.std())
            # Fall back: extract EPS rows from annual financials (yfinance stores as rows)
            financials = cached_data.get('financials')
            if financials is not None and isinstance(financials, pd.DataFrame) and not financials.empty:
                eps_row = next(
                    (r for r in financials.index if 'diluted eps' in str(r).lower() or 'basic eps' in str(r).lower()),
                    None
                )
                if eps_row:
                    values = pd.to_numeric(financials.loc[eps_row], errors='coerce').dropna().sort_index()
                    values = values[np.isfinite(values)]
                    if len(values) >= 3:
                        growth = values.pct_change().dropna()
                        growth = growth[np.isfinite(growth)]
                        if len(growth) >= 2:
                            return float(growth.std())
            return None
        except Exception:
            return None

    def _calc_margin_stability(self, cached_data: Optional[Dict]) -> Optional[float]:
        """σ of profit margins over available financials."""
        try:
            if not cached_data:
                return None
            financials = cached_data.get('financials') or cached_data.get('income_stmt')
            if financials is None or (isinstance(financials, pd.DataFrame) and financials.empty):
                return None
            if not isinstance(financials, pd.DataFrame):
                return None
            # Look for net income and revenue to compute margin
            net_income_row = next(
                (r for r in financials.index if 'net income' in str(r).lower()),
                None
            )
            revenue_row = next(
                (r for r in financials.index if 'total revenue' in str(r).lower() or 'revenue' in str(r).lower()),
                None
            )
            if net_income_row is None or revenue_row is None:
                return None
            net_income = pd.to_numeric(financials.loc[net_income_row], errors='coerce').dropna()
            revenue = pd.to_numeric(financials.loc[revenue_row], errors='coerce').dropna()
            if len(net_income) < 2 or len(revenue) < 2:
                return None
            margins = (net_income / revenue).dropna()
            margins = margins[np.isfinite(margins)]
            if len(margins) < 2:
                return None
            return float(margins.std())
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # NSE Quality 30 scoring functions — additive, 0-100 total, NO base-50
    # -------------------------------------------------------------------------

    def _score_roe(self, metrics: Dict) -> float:
        """ROE score (0–40 pts). NSE Quality 30 primary metric."""
        roe = metrics.get('roe')
        if roe is None:
            return 0
        roe_pct = roe * 100
        if roe_pct >= 25:  return 40   # Excellent (TCS, HDFC Bank territory)
        if roe_pct >= 18:  return 32   # Good
        if roe_pct >= 12:  return 22   # Above average
        if roe_pct >= 8:   return 14   # Average
        if roe_pct >= 0:   return 6    # Below average but profitable
        return 0                        # Negative ROE

    def _score_leverage(self, metrics: Dict) -> float:
        """Leverage score (0–35 pts). Lower D/E = higher quality."""
        dte_raw = metrics.get('debt_to_equity_raw')
        if dte_raw is None:
            return 18   # mid-point when unknown — not 0, not 35
        actual_dte = dte_raw / 100      # convert yfinance format to real ratio
        if actual_dte <= 0:    return 35   # Net cash
        if actual_dte <= 0.25: return 30   # Very low debt
        if actual_dte <= 0.5:  return 24   # Low debt
        if actual_dte <= 1.0:  return 16   # Moderate
        if actual_dte <= 2.0:  return 8    # High debt
        return 2                            # Very high debt

    def _score_earnings_stability(self, metrics: Dict) -> float:
        """Earnings stability score (0–25 pts). Lower σ = more stable = higher quality."""
        eps_var = metrics.get('eps_variability')
        margin_stability = metrics.get('profit_margin_stability')

        if eps_var is not None:
            if eps_var < 0.10:  return 25   # Very stable
            if eps_var < 0.20:  return 20   # Stable
            if eps_var < 0.35:  return 13   # Moderate
            if eps_var < 0.50:  return 7    # High variation
            return 2                         # Very volatile

        if margin_stability is not None:
            if margin_stability < 0.02: return 25
            if margin_stability < 0.04: return 18
            if margin_stability < 0.07: return 11
            return 4

        return 10   # Unknown — neutral, not 0

    # -------------------------------------------------------------------------
    # Price metric helpers (kept for screener / display, not scored)
    # -------------------------------------------------------------------------

    def _calculate_volatility(self, price_data: pd.DataFrame, window: int = 30) -> Optional[float]:
        try:
            returns = price_data['Close'].pct_change()
            vol = returns.rolling(window=window).std().iloc[-1]
            return float(vol * np.sqrt(252) * 100)
        except Exception:
            return None

    def _calculate_return(self, price_data: pd.DataFrame, days: int) -> Optional[float]:
        try:
            if len(price_data) < days:
                return None
            current = price_data['Close'].iloc[-1]
            past = price_data['Close'].iloc[-days]
            if pd.isna(current) or pd.isna(past) or past <= 0:
                return None
            return ((current - past) / past) * 100
        except Exception:
            return None

    def _calculate_max_drawdown(self, price_data: pd.DataFrame) -> Optional[float]:
        try:
            prices = price_data['Close']
            drawdown = (prices - prices.cummax()) / prices.cummax() * 100
            return float(drawdown.min())
        except Exception:
            return None

    def _calculate_current_drawdown(self, price_data: pd.DataFrame) -> Optional[float]:
        try:
            prices = price_data['Close']
            ath = prices.max()
            return ((prices.iloc[-1] - ath) / ath) * 100
        except Exception:
            return None

    def _calculate_return_consistency(self, price_data: pd.DataFrame) -> Optional[float]:
        try:
            if not isinstance(price_data.index, pd.DatetimeIndex):
                return None
            monthly = price_data['Close'].resample('M').last().pct_change().dropna()
            if len(monthly) < 6:
                return None
            mean = monthly.mean()
            if pd.isna(mean) or abs(mean) < 1e-10:
                return None
            std = monthly.std()
            if pd.isna(std) or std == 0:
                return 0.0
            cv = safe_divide(abs(std), abs(mean), default=None)
            return float(cv) if cv is not None else None
        except Exception:
            return None

    def _calculate_52w_range(self, price_data: pd.DataFrame) -> Optional[float]:
        try:
            if len(price_data) < 252:
                return None
            recent = price_data.tail(252)
            high = recent['High'].max()
            low = recent['Low'].min()
            current = price_data['Close'].iloc[-1]
            diff = high - low
            if pd.isna(diff) or abs(diff) < 1e-10:
                return None
            pct = safe_divide(current - low, diff, default=None)
            return float(pct * 100) if pct is not None else None
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Confidence and reasoning
    # -------------------------------------------------------------------------

    def _calculate_confidence(self, price_data: pd.DataFrame, metrics: Dict) -> float:
        confidence = 0.5  # base
        if metrics.get('roe') is not None:
            confidence += 0.2
        if metrics.get('debt_to_equity_raw') is not None:
            confidence += 0.15
        if metrics.get('eps_variability') is not None or metrics.get('profit_margin_stability') is not None:
            confidence += 0.15
        return min(1.0, confidence)

    def _generate_reasoning(
        self, metrics: Dict, roe_score: float, leverage_score: float, stability_score: float
    ) -> str:
        parts = []
        roe = metrics.get('roe')
        if roe is not None:
            parts.append(f"ROE {roe * 100:.1f}% → {roe_score:.0f}/40 pts")
        dte = metrics.get('debt_to_equity')
        if dte is not None:
            parts.append(f"D/E {dte:.2f}x → {leverage_score:.0f}/35 pts")
        eps_var = metrics.get('eps_variability')
        if eps_var is not None:
            parts.append(f"EPS σ {eps_var:.2f} → {stability_score:.0f}/25 pts")
        elif metrics.get('profit_margin_stability') is not None:
            parts.append(f"Margin σ {metrics['profit_margin_stability']:.3f} → {stability_score:.0f}/25 pts")
        return " | ".join(parts) if parts else "Quality metrics computed"
