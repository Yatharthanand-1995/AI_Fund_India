"""
Stock Scorer - Orchestrates all 5 AI agents and calculates composite score

This is the main orchestration layer that:
1. Initializes all 5 agents
2. Fetches comprehensive data (once)
3. Runs all agents with shared data
4. Applies weights (static or adaptive)
5. Calculates composite score
6. Determines recommendation (STRONG BUY, BUY, HOLD, SELL)
7. Returns comprehensive analysis
"""

import logging
import os
from typing import Dict, Optional, List
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.fundamentals_agent import FundamentalsAgent
from agents.momentum_agent import MomentumAgent
from agents.quality_agent import QualityAgent
from agents.sentiment_agent import SentimentAgent
from agents.institutional_flow_agent import InstitutionalFlowAgent
from data.hybrid_provider import HybridDataProvider
from data.rbi_rate_provider import get_default_provider as get_rbi_provider
from core.market_regime_service import MarketRegimeService
from utils.validation import get_nifty_data
from core.exceptions import DataValidationException

logger = logging.getLogger(__name__)


class StockScorer:
    """
    Stock Scorer - Orchestrates all 5 agents to score stocks

    Manages:
    - Agent initialization
    - Data fetching and sharing
    - Score aggregation
    - Recommendation determination

    Default weights:
    - Fundamentals: 36%
    - Momentum: 27%
    - Quality: 18%
    - Sentiment: 9%
    - Institutional Flow: 10%
    """

    # Static weights (default)
    STATIC_WEIGHTS = {
        'fundamentals': 0.36,
        'momentum': 0.27,
        'quality': 0.18,
        'sentiment': 0.09,
        'institutional_flow': 0.10
    }

    # Recommendation thresholds — percentile-based after cross-sectional normalization.
    # Single-stock /analyze uses absolute scores (no universe to compare against).
    # Batch /score_stocks_batch normalizes to percentile [0, 100] before applying these.
    # NIFTY 50 universe (~50 stocks): STRONG BUY ≈ top 5, BUY ≈ top 15, HOLD ≈ middle 20.
    RECOMMENDATION_THRESHOLDS = {
        'STRONG BUY': 90,  # top 10% — always ~5 stocks in NIFTY 50
        'BUY':        70,  # top 30% — always ~15 stocks
        'WEAK BUY':   55,  # 55–70th percentile
        'HOLD_HIGH':  45,  # 45–55th percentile
        'HOLD_LOW':   30,  # 30–45th percentile
        'WEAK SELL':  10,  # 10–30th percentile
        'SELL':        0   # bottom 10%
    }

    def __init__(
        self,
        data_provider: Optional[HybridDataProvider] = None,
        use_adaptive_weights: bool = False,
        sector_mapping: Optional[Dict] = None
    ):
        """
        Initialize Stock Scorer

        Args:
            data_provider: Data provider instance (creates new if None)
            use_adaptive_weights: Use adaptive weights based on market regime
            sector_mapping: Mapping of symbols to sectors
        """
        logger.info("Initializing Stock Scorer with 5 agents")

        # Initialize data provider
        self.data_provider = data_provider or HybridDataProvider()

        # Initialize all 5 agents
        self.fundamentals_agent = FundamentalsAgent()
        self.momentum_agent = MomentumAgent()
        self.quality_agent = QualityAgent(sector_mapping=sector_mapping)
        self.sentiment_agent = SentimentAgent()
        self.institutional_flow_agent = InstitutionalFlowAgent()

        # Configuration
        self.use_adaptive_weights = use_adaptive_weights
        self.sector_mapping = sector_mapping or {}

        # Initialize market regime service for adaptive weights
        self.market_regime_service = MarketRegimeService() if use_adaptive_weights else None

        # Current weights (will be set to static or adaptive)
        self.current_weights = self.STATIC_WEIGHTS.copy()
        self._custom_weights: dict | None = None  # Set via set_weights(); overrides adaptive/static

        # USD/INR trend cache (refreshed hourly; avoids repeated yfinance calls per stock)
        self._usdinr_trend_cache: Optional[Dict] = None
        self._usdinr_cache_ts: Optional[datetime] = None

        # RBI rate cycle provider (reads local JSON config — no network call)
        self._rbi_provider = get_rbi_provider()

        # Stats tracking
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_score': 0.0,
            'recommendations': {
                'STRONG BUY': 0,
                'BUY': 0,
                'WEAK BUY': 0,
                'HOLD+': 0,
                'HOLD': 0,
                'WEAK SELL': 0,
                'SELL': 0
            }
        }

        logger.info(f"Stock Scorer initialized (adaptive_weights: {use_adaptive_weights})")

    # ── USD/INR sector adjustment (India-specific) ───────────────────────────
    # Sector sensitivity to USD/INR exchange rate movements.
    # Positive = benefits when INR weakens (USD appreciates).
    # IT firms bill USD, costs in INR → biggest beneficiary.
    # Oil marketing cos (in Energy sector) have ONGC (benefit) + BPCL (hurt) → skip Energy.
    # Keys use Yahoo Finance sector names (as returned by ticker.info['sector']).
    _SECTOR_CURRENCY_SENSITIVITY: Dict[str, float] = {
        'Technology':           +1.0,  # IT services: 100% USD billing, INR cost base
        'Healthcare':           +0.5,  # Pharma: US generic exports
        'Basic Materials':      +0.4,  # Metals: commodity exports priced in USD
        'Consumer Defensive':   -0.3,  # FMCG: import raw materials in USD
        'Consumer Cyclical':    -0.2,  # Auto: import components (EV transition)
        # Financial Services, Energy, Communication Services, Industrials: mixed/neutral
    }
    _USDINR_CACHE_TTL_SECONDS = 3600  # Refresh at most once per hour

    def _get_usdinr_trend(self) -> Optional[Dict]:
        """
        Fetch 20-day USD/INR change from yfinance (INR=X).
        Returns {'trend_pct': float, 'direction': str} or None on failure.
        Positive trend_pct means INR has weakened (USD buys more INR).
        Cached for 1 hour to avoid per-stock fetching overhead.
        """
        now = datetime.now()
        if (
            self._usdinr_trend_cache is not None
            and self._usdinr_cache_ts is not None
            and (now - self._usdinr_cache_ts).total_seconds() < self._USDINR_CACHE_TTL_SECONDS
        ):
            return self._usdinr_trend_cache

        try:
            import yfinance as yf
            inr = yf.Ticker("INR=X").history(period="30d")
            if len(inr) < 20:
                return None
            trend_pct = (inr['Close'].iloc[-1] / inr['Close'].iloc[-20] - 1) * 100
            direction = 'weakening' if trend_pct > 0 else 'strengthening'
            result = {'trend_pct': round(float(trend_pct), 2), 'direction': direction}
            self._usdinr_trend_cache = result
            self._usdinr_cache_ts = now
            logger.debug(f"USD/INR 20d trend: {trend_pct:+.2f}% ({direction})")
            return result
        except Exception as e:
            logger.debug(f"USD/INR fetch failed (skipping currency adjustment): {e}")
            return None

    def _compute_currency_adjustment(self, sector: Optional[str], usdinr: Optional[Dict]) -> float:
        """
        Returns a score adjustment (pts, capped ±4) based on USD/INR trend and sector.
        Only applied when INR movement is material (>1% over 20 days).
        """
        if not sector or not usdinr:
            return 0.0
        sensitivity = self._SECTOR_CURRENCY_SENSITIVITY.get(sector, 0.0)
        if sensitivity == 0.0:
            return 0.0
        trend_pct = usdinr.get('trend_pct', 0.0)
        if abs(trend_pct) < 1.0:
            return 0.0
        raw_adj = sensitivity * trend_pct * 0.6  # scaling: 5% move in IT → +3 pts
        return round(float(np.clip(raw_adj, -4.0, 4.0)), 2)

    def _compute_rs_acceleration(
        self,
        price_data: pd.DataFrame,
        nifty_data: Optional[pd.DataFrame],
    ) -> float:
        """
        RS Acceleration = (3M excess return vs NIFTY) - (6M excess return vs NIFTY).

        Positive → momentum building vs index (good early entry signal).
        Negative → momentum fading vs index (mean-reversion risk).

        Returns a score adjustment in range [-10, +10] pts.
        Threshold: reward only when clearly building (accel > +5pp),
        penalise only when strongly fading (accel < -10pp). Noise → 0.

        Mirrors rs_acceleration_score_at() in scripts/portfolio_backtest.py.
        """
        try:
            if price_data is None or price_data.empty:
                return 0.0
            if nifty_data is None or nifty_data.empty or len(nifty_data) < 127:
                return 0.0
            if len(price_data) < 127:
                return 0.0

            def pct_return(series: pd.Series, days: int) -> Optional[float]:
                if len(series) < days + 1:
                    return None
                p0 = series.iloc[-(days + 1)]
                p1 = series.iloc[-1]
                return (p1 - p0) / p0 if p0 > 0 else None

            stock_close = price_data['Close'] if 'Close' in price_data.columns else price_data.iloc[:, 0]
            nifty_close = nifty_data['Close'] if 'Close' in nifty_data.columns else nifty_data.iloc[:, 0]

            r3s = pct_return(stock_close, 63)
            r6s = pct_return(stock_close, 126)
            r3n = pct_return(nifty_close, 63)
            r6n = pct_return(nifty_close, 126)

            if any(v is None for v in [r3s, r6s, r3n, r6n]):
                return 0.0

            rs3 = (r3s - r3n) * 100   # stock 3M excess return vs NIFTY
            rs6 = (r6s - r6n) * 100   # stock 6M excess return vs NIFTY
            accel = rs3 - rs6          # positive = momentum building

            if accel > 5.0:
                return float(np.clip(accel * 0.5, 2.0, 10.0))   # +2 to +10 pts
            elif accel < -10.0:
                return float(np.clip(accel * 0.4, -10.0, -2.0)) # -2 to -10 pts
            return 0.0

        except Exception:
            return 0.0

    def _compute_earnings_acceleration(self, symbol: str, cached_data: Optional[Dict] = None) -> float:
        """
        Earnings Acceleration signal: measures whether EPS/revenue growth is speeding up or slowing down.

        Uses quarterly earnings data from yfinance. Returns a score adjustment in range [-8, +8] pts.

        Logic:
          - Fetch last 4 quarters of EPS (or revenue if EPS unavailable)
          - Compute QoQ growth for Q-1 vs Q-2, then Q-2 vs Q-3 (trend of growth rate)
          - Accelerating (growth rate rising): +2 to +8 pts
          - Decelerating (growth rate falling): -2 to -8 pts
          - Flat / no data: 0

        This catches the key pattern our system missed:
          HDFCBANK 2024-25: price was flat but EPS was accelerating → +28% forward return
          ASIANPAINT 2023-25: PE >60x AND EPS decelerating → -12% forward return
        """
        try:
            import yfinance as yf
            # Try getting quarterly earnings from cached_data first
            info = cached_data.get('raw_info') if cached_data else None
            ticker_sym = symbol if symbol.endswith('.NS') else f"{symbol}.NS"
            t = yf.Ticker(ticker_sym)

            # earningsGrowth = current quarter YoY; revenueGrowth = TTM
            # For acceleration we need the trend across quarters
            quarterly = t.quarterly_earnings
            if quarterly is None or quarterly.empty or len(quarterly) < 3:
                # Fall back to single growth metrics from info
                info_data = t.info
                eps_growth = info_data.get('earningsGrowth')    # current quarter YoY
                rev_growth = info_data.get('revenueGrowth')     # TTM
                # Without trend data, use magnitude as a proxy for momentum
                if eps_growth is not None and rev_growth is not None:
                    avg_growth = (eps_growth + rev_growth) / 2 * 100
                    if avg_growth > 20:
                        return 3.0   # solid growth, modest boost
                    elif avg_growth < -10:
                        return -3.0  # shrinking earnings
                return 0.0

            # Compute QoQ growth acceleration using last 3 quarters
            # quarterly.index is sorted newest-first by yfinance
            eps_vals = quarterly['Earnings'].dropna().values[:4]
            if len(eps_vals) < 3:
                return 0.0

            def safe_growth(a, b):
                # growth from b to a
                if b == 0 or np.isnan(b) or np.isnan(a):
                    return None
                return (a - b) / abs(b)

            g1 = safe_growth(eps_vals[0], eps_vals[1])   # most recent QoQ
            g2 = safe_growth(eps_vals[1], eps_vals[2])   # one period prior

            if g1 is None or g2 is None:
                return 0.0

            acceleration = g1 - g2   # positive = earnings growing faster
            if acceleration > 0.15:
                return float(np.clip(acceleration * 30, 2.0, 8.0))   # +2 to +8 pts
            elif acceleration < -0.15:
                return float(np.clip(acceleration * 25, -8.0, -2.0)) # -2 to -8 pts
            return 0.0

        except Exception:
            return 0.0

    def score_stock(
        self,
        symbol: str,
        nifty_data: Optional[pd.DataFrame] = None,
        cached_data: Optional[Dict] = None
    ) -> Dict:
        """
        Score a single stock using all 5 agents

        Args:
            symbol: Stock symbol (e.g., "TCS")
            nifty_data: NIFTY50 data for relative strength (optional, will fetch if None)
            cached_data: Pre-fetched point-in-time data (for backtesting, optional)

        Returns:
            {
                'symbol': str,
                'composite_score': float (0-100),
                'composite_confidence': float (0-1),
                'recommendation': str,
                'agent_scores': {
                    'fundamentals': {...},
                    'momentum': {...},
                    'quality': {...},
                    'sentiment': {...},
                    'institutional_flow': {...}
                },
                'weights_used': dict,
                'timestamp': str,
                'analysis_time_seconds': float
            }
        """
        self.stats['total_analyses'] += 1
        start_time = datetime.now()

        logger.info(f"{'='*60}")
        logger.info(f"Scoring stock: {symbol}")
        logger.info(f"{'='*60}")

        try:
            # Step 1: Get current weights (adaptive or static)
            weights = self._get_current_weights()
            logger.info(f"Using weights: {weights}")

            # Step 2: Fetch comprehensive data (once for all agents)
            # If cached_data provided (backtest mode), use it; otherwise fetch current data
            if cached_data is None:
                logger.info(f"Fetching comprehensive data for {symbol}...")
                cached_data = self.data_provider.get_comprehensive_data(symbol)
            else:
                logger.info(f"Using pre-fetched point-in-time data for {symbol} (backtest mode)")

            if cached_data.get('error'):
                raise ValueError(f"Data fetch failed: {cached_data.get('error')}")

            price_data = cached_data.get('historical_data')
            if price_data is None or price_data.empty:
                raise ValueError("No historical price data available")

            # Step 3: Fetch NIFTY50 data if needed and not provided
            if nifty_data is None or nifty_data.empty:
                logger.info("Fetching NIFTY50 data for relative strength...")
                try:
                    nifty_data = get_nifty_data(self.data_provider, min_rows=20)
                except DataValidationException as e:
                    logger.warning(f"Could not fetch NIFTY data: {e}")
                    nifty_data = pd.DataFrame()

            # Step 3b: Detect market regime from NIFTY data (cached after first call)
            regime_trend = 'SIDEWAYS'
            try:
                regime_info = self.get_market_regime()
                regime_trend = regime_info.get('trend', 'SIDEWAYS') if regime_info else 'SIDEWAYS'
                logger.info(f"Market regime for scoring: {regime_trend}")
            except Exception as _re:
                logger.warning(f"Could not detect regime before agents: {_re}. Using SIDEWAYS default.")

            # Step 4: Run all 5 agents IN PARALLEL (5x speedup!)
            logger.info("Running all 5 agents in parallel...")

            # Define agent tasks for parallel execution
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all agent tasks concurrently — pass regime for awareness
                future_to_agent = {
                    executor.submit(
                        self.fundamentals_agent.analyze,
                        symbol,
                        cached_data,
                        regime_trend
                    ): 'fundamentals',

                    executor.submit(
                        self.momentum_agent.analyze,
                        symbol,
                        price_data,
                        nifty_data,
                        cached_data,
                        regime_trend
                    ): 'momentum',

                    executor.submit(
                        self.quality_agent.analyze,
                        symbol,
                        price_data,
                        cached_data,
                        regime_trend
                    ): 'quality',

                    executor.submit(
                        self.sentiment_agent.analyze,
                        symbol,
                        cached_data,
                        regime_trend
                    ): 'sentiment',

                    executor.submit(
                        self.institutional_flow_agent.analyze,
                        symbol,
                        price_data,
                        cached_data,
                        regime_trend
                    ): 'institutional_flow'
                }

                # Collect results as they complete
                agent_results = {}
                for future in as_completed(future_to_agent):
                    agent_name = future_to_agent[future]
                    try:
                        result = future.result()
                        agent_results[agent_name] = result
                        logger.info(f"  ✓ {agent_name.title()} Agent completed")
                    except Exception as e:
                        logger.error(f"  ✗ {agent_name.title()} Agent failed: {e}")
                        # Mark as error — excluded from composite score calculation
                        agent_results[agent_name] = {
                            'score': None,
                            'confidence': 0.0,
                            'reasoning': f'Analysis failed: {str(e)}',
                            'metrics': {},
                            'breakdown': {},
                            'agent': f'{agent_name.title()}Agent',
                            'status': 'error',
                            'error': str(e)
                        }

            # Apply regime-aware score adjustment to each agent's score
            # Skip when adaptive weights are active (regime already captured in weights)
            if not self.use_adaptive_weights:
                _REGIME_AGENT_MULTIPLIERS = {
                    'BULL': {
                        'fundamentals': 1.05, 'momentum': 1.08, 'quality': 0.97,
                        'sentiment': 1.00, 'institutional_flow': 1.02
                    },
                    'BEAR': {
                        'fundamentals': 0.92, 'momentum': 0.88, 'quality': 1.08,
                        'sentiment': 1.05, 'institutional_flow': 1.00
                    },
                    'SIDEWAYS': {
                        'fundamentals': 1.0, 'momentum': 1.0, 'quality': 1.0,
                        'sentiment': 1.0, 'institutional_flow': 1.0
                    },
                }
                _agent_multipliers = _REGIME_AGENT_MULTIPLIERS.get(regime_trend, {})
                if _agent_multipliers:
                    for _agent_name, _result in agent_results.items():
                        _m = _agent_multipliers.get(_agent_name, 1.0)
                        if _m != 1.0 and _result.get('status') != 'error' and _result.get('score') is not None:
                            _result['regime_adjusted_score'] = round(min(100.0, max(0.0, _result['score'] * _m)), 2)
                    logger.info(f"  Applied agent-specific regime multipliers ({regime_trend})")

            # Extract results (maintain backward compatibility)
            fundamentals_result = agent_results['fundamentals']
            momentum_result = agent_results['momentum']
            quality_result = agent_results['quality']
            sentiment_result = agent_results['sentiment']
            flow_result = agent_results['institutional_flow']

            # Step 5: Calculate composite score
            logger.info("Calculating composite score...")
            composite_score, composite_confidence = self._calculate_composite_score(
                fundamentals_result,
                momentum_result,
                quality_result,
                sentiment_result,
                flow_result,
                weights
            )

            # Step 5b: USD/INR sector adjustment (India-specific overlay, ±4 pts max)
            stock_sector = cached_data.get('sector')
            usdinr_data = self._get_usdinr_trend()
            currency_adj = self._compute_currency_adjustment(stock_sector, usdinr_data)
            if currency_adj != 0.0:
                composite_score = float(np.clip(composite_score + currency_adj, 0.0, 100.0))
                logger.debug(f"  Currency adjustment ({stock_sector}): {currency_adj:+.2f} pts "
                             f"(USD/INR {usdinr_data['direction']} {usdinr_data['trend_pct']:+.1f}%)")

            # Step 5c: RBI rate cycle sector adjustment (India-specific overlay, ±3 pts max)
            rbi_adj = self._rbi_provider.get_sector_adjustment(stock_sector)
            if rbi_adj != 0.0:
                composite_score = float(np.clip(composite_score + rbi_adj, 0.0, 100.0))
                rbi_info = self._rbi_provider.get_rate_info()
                logger.debug(f"  RBI rate adjustment ({stock_sector}): {rbi_adj:+.2f} pts "
                             f"(cycle={rbi_info['cycle']}, repo={rbi_info['repo_rate']}%)")

            # Step 5d: Earnings Acceleration adjustment (±8 pts max)
            # Rewards stocks with accelerating QoQ EPS; penalises decelerating ones.
            # Catches value recovery (HDFCBANK type) and avoids extended PE stocks.
            earnings_acc_adj = self._compute_earnings_acceleration(symbol, cached_data)
            if earnings_acc_adj != 0.0:
                composite_score = float(np.clip(composite_score + earnings_acc_adj, 0.0, 100.0))
                logger.debug(f"  Earnings acceleration ({symbol}): {earnings_acc_adj:+.2f} pts")

            # Step 5e: RS Acceleration adjustment (±10 pts max)
            # Rewards building momentum vs NIFTY (3M RS > 6M RS),
            # penalises fading momentum (extended run, mean-reversion risk).
            rs_accel_adj = self._compute_rs_acceleration(price_data, nifty_data)
            if rs_accel_adj != 0.0:
                composite_score = float(np.clip(composite_score + rs_accel_adj, 0.0, 100.0))
                logger.debug(f"  RS acceleration ({symbol}): {rs_accel_adj:+.2f} pts")

            # Step 6: Determine recommendation
            recommendation = self._get_recommendation(composite_score, composite_confidence)

            # Step 7: Calculate analysis time
            analysis_time = (datetime.now() - start_time).total_seconds()

            # Step 8: Assemble complete result
            # Compute trading levels (stop loss, target price)
            current_price = cached_data.get('current_price')
            trading_levels = self._compute_trading_levels(
                current_price=current_price,
                momentum_metrics=momentum_result.get('metrics', {}),
                sentiment_metrics=sentiment_result.get('metrics', {}),
                week_52_high=cached_data.get('week_52_high'),
                week_52_low=cached_data.get('week_52_low'),
            )

            result = {
                'symbol': symbol,
                'composite_score': round(composite_score, 2),
                'composite_confidence': round(composite_confidence, 2),
                'recommendation': recommendation,
                'agent_scores': {
                    'fundamentals': fundamentals_result,
                    'momentum': momentum_result,
                    'quality': quality_result,
                    'sentiment': sentiment_result,
                    'institutional_flow': flow_result
                },
                'weights_used': weights,
                'current_price': current_price,
                'price_change_percent': cached_data.get('price_change_percent'),
                'market_cap': cached_data.get('market_cap'),
                'sector': cached_data.get('sector'),
                'company_name': cached_data.get('company_name'),
                'week_52_high': cached_data.get('week_52_high'),
                'week_52_low': cached_data.get('week_52_low'),
                'trading_levels': trading_levels,
                'timestamp': datetime.now().isoformat(),
                'analysis_time_seconds': round(analysis_time, 2),
                'data_provider': cached_data.get('provider'),
                'currency_adjustment': currency_adj if 'currency_adj' in locals() else 0.0,
                'usdinr_trend': usdinr_data if 'usdinr_data' in locals() else None,
                'rbi_adjustment': rbi_adj if 'rbi_adj' in locals() else 0.0,
                'rbi_rate_cycle': self._rbi_provider.get_rate_info().get('cycle'),
                'earnings_acceleration_adj': earnings_acc_adj if 'earnings_acc_adj' in locals() else 0.0,
                'rs_acceleration_adj': rs_accel_adj if 'rs_accel_adj' in locals() else 0.0,
            }

            # Update stats
            self.stats['successful_analyses'] += 1
            self.stats['recommendations'][recommendation] += 1
            self._update_average_score(composite_score)

            logger.info(f"✅ Analysis complete: {recommendation} ({composite_score:.1f}/100)")
            logger.info(f"   Analysis time: {analysis_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Failed to score {symbol}: {e}", exc_info=True)
            self.stats['failed_analyses'] += 1

            return {
                'symbol': symbol,
                'composite_score': 50.0,
                'composite_confidence': 0.0,
                'recommendation': 'ERROR',
                'error': str(e),
                'agent_scores': {},
                'weights_used': weights if 'weights' in locals() else self.STATIC_WEIGHTS,
                'timestamp': datetime.now().isoformat(),
                'analysis_time_seconds': (datetime.now() - start_time).total_seconds()
            }

    def score_stocks_batch(self, symbols: List[str]) -> List[Dict]:
        """
        Score multiple stocks in batch

        Args:
            symbols: List of stock symbols

        Returns:
            List of analysis results, sorted by composite score (descending)
        """
        # Deduplicate symbols while preserving order
        seen = set()
        symbols = [s for s in symbols if s not in seen and not seen.add(s)]

        logger.info(f"Batch scoring {len(symbols)} stocks...")
        results = []

        # Fetch NIFTY data once for all stocks
        try:
            nifty_data = get_nifty_data(self.data_provider, min_rows=20)
        except DataValidationException as e:
            logger.warning(f"Could not fetch NIFTY data: {e}")
            nifty_data = pd.DataFrame()

        # Conservative outer worker count — score_stock itself spawns an inner
        # ThreadPoolExecutor(5) per stock, so total threads = outer × 5.
        # Cap at 4 outer workers → max 20 agent threads at a time to avoid exhaustion.
        default_workers = min(4, len(symbols))
        max_workers = min(len(symbols), int(os.environ.get('BATCH_MAX_WORKERS', str(default_workers))))
        logger.info(f"Scoring {len(symbols)} stocks with up to {max_workers} parallel workers (max ~{max_workers * 5} agent threads)...")

        with ThreadPoolExecutor(max_workers=max_workers) as batch_executor:
            future_to_symbol = {
                batch_executor.submit(self.score_stock, symbol, nifty_data): symbol
                for symbol in symbols
            }
            completed = 0
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                logger.info(f"\nProgress: {completed}/{len(symbols)} - {symbol}")
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to score {symbol}: {e}")
                    results.append({
                        'symbol': symbol,
                        'composite_score': 0.0,
                        'error': str(e)
                    })

        # Sort by composite score (descending)
        results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

        # Apply cross-sectional percentile normalization (NSE/MSCI standard)
        results = self._normalize_batch_scores(results)

        logger.info(f"\n✅ Batch analysis complete: {len(results)} stocks scored")
        return results

    def _calculate_composite_score(
        self,
        fundamentals_result: Dict,
        momentum_result: Dict,
        quality_result: Dict,
        sentiment_result: Dict,
        flow_result: Dict,
        weights: Dict
    ) -> tuple[float, float]:
        """
        Calculate weighted composite score and confidence

        Returns:
            (composite_score, composite_confidence)
        """
        # Map agent results to their weight keys
        agent_map = {
            'fundamentals': fundamentals_result,
            'momentum': momentum_result,
            'quality': quality_result,
            'sentiment': sentiment_result,
            'institutional_flow': flow_result,
        }

        # Separate successful and failed agents
        successful_agents = {
            name: result for name, result in agent_map.items()
            if result.get('status') != 'error' and result.get('score') is not None
        }
        error_count = len(agent_map) - len(successful_agents)

        if error_count > 0:
            logger.warning(f"  {error_count}/5 agents failed — excluding from composite, renormalizing weights")

        if not successful_agents:
            # All agents failed — return floor score with zero confidence
            logger.error("  All 5 agents failed — cannot produce reliable score")
            return 35.0, 0.0

        # Renormalize weights to only include successful agents
        raw_weight_sum = sum(weights[name] for name in successful_agents)
        normalized_weights = {
            name: weights[name] / raw_weight_sum for name in successful_agents
        }

        # Calculate weighted composite score from successful agents only
        # Use regime_adjusted_score when present (set by regime multiplier path),
        # keeping result['score'] intact so breakdown values remain consistent.
        composite_score = sum(
            normalized_weights[name] * result.get('regime_adjusted_score', result['score'])
            for name, result in successful_agents.items()
        )

        # Calculate composite confidence (equal-weight mean across successful agents only)
        composite_confidence = sum(
            result.get('confidence', 0.5) for result in successful_agents.values()
        ) / len(successful_agents)

        # Penalize confidence proportionally when agents have failed
        if error_count >= 3:
            composite_confidence *= 0.3
            logger.warning("  Confidence heavily penalized — majority of agents failed")
        elif error_count == 2:
            composite_confidence *= 0.6
        elif error_count == 1:
            composite_confidence *= 0.85

        logger.info(f"  Composite Score: {composite_score:.2f}/100")
        logger.info(f"  Composite Confidence: {composite_confidence:.2%}")

        return composite_score, composite_confidence

    def _get_recommendation(self, score: float, confidence: float) -> str:
        """
        Determine recommendation based on score and confidence

        Args:
            score: Composite score (0-100)
            confidence: Composite confidence (0-1)

        Returns:
            Recommendation string
        """
        # FIX: Removed confidence factor - it was creating backwards logic
        # where low confidence made thresholds EASIER to pass instead of harder
        # Now using fixed thresholds for consistent signal generation

        if score >= self.RECOMMENDATION_THRESHOLDS['STRONG BUY']:
            return 'STRONG BUY'
        elif score >= self.RECOMMENDATION_THRESHOLDS['BUY']:
            return 'BUY'
        elif score >= self.RECOMMENDATION_THRESHOLDS['WEAK BUY']:
            return 'WEAK BUY'
        elif score >= self.RECOMMENDATION_THRESHOLDS['HOLD_HIGH']:
            return 'HOLD+'
        elif score >= self.RECOMMENDATION_THRESHOLDS['HOLD_LOW']:
            return 'HOLD'
        elif score >= self.RECOMMENDATION_THRESHOLDS['WEAK SELL']:
            return 'WEAK SELL'
        else:
            return 'SELL'

    def _normalize_batch_scores(self, results: List[Dict]) -> List[Dict]:
        """
        Apply cross-sectional percentile normalization to composite scores.
        NSE/MSCI standard: winsorize at 5th/95th pct → z-score → normal CDF percentile.

        Preserves raw_composite_score for debugging. Only applied in batch context —
        single-stock /analyze uses absolute scoring (no universe to compare against).
        """
        valid_indices = [
            i for i, r in enumerate(results)
            if r.get('recommendation') != 'ERROR'
            and r.get('composite_score') is not None
            and r.get('composite_confidence') is not None
        ]
        if len(valid_indices) < 5:
            logger.warning("Too few valid results for cross-sectional normalization — skipping")
            return results

        raw_scores = np.array([results[i]['composite_score'] for i in valid_indices], dtype=float)

        # Winsorize at 5th/95th pct (NSE uses 1/99 but 5/95 is more robust at <100 stocks)
        p5, p95 = np.percentile(raw_scores, [5, 95])
        winsorized = np.clip(raw_scores, p5, p95)

        mu = np.mean(winsorized)
        sigma = np.std(winsorized)
        if sigma < 0.01:
            logger.warning("Score standard deviation too small — skipping normalization")
            return results
        z_scores = (winsorized - mu) / sigma

        # Map to [0, 100] percentile rank via normal CDF
        percentile_scores = scipy_stats.norm.cdf(z_scores) * 100

        for rank_idx, result_idx in enumerate(valid_indices):
            r = results[result_idx]
            r['raw_composite_score'] = round(r['composite_score'], 2)
            r['composite_score'] = round(float(percentile_scores[rank_idx]), 1)
            r['recommendation'] = self._get_recommendation(r['composite_score'], r.get('composite_confidence', 0.5))

        logger.info(
            f"Cross-sectional normalization applied to {len(valid_indices)} stocks "
            f"(raw range: [{raw_scores.min():.1f}, {raw_scores.max():.1f}] → "
            f"percentile range: [{percentile_scores.min():.1f}, {percentile_scores.max():.1f}])"
        )

        results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        return results

    def _get_current_weights(self) -> Dict:
        """
        Get current weights: custom override > adaptive > static
        """
        if self._custom_weights is not None:
            return self._custom_weights.copy()
        if self.use_adaptive_weights and self.market_regime_service:
            try:
                # Get current market regime
                regime_info = self.market_regime_service.get_current_regime(
                    data_provider=self.data_provider
                )
                weights = regime_info['weights']
                logger.info(f"Using adaptive weights for regime: {regime_info['regime']}")
                return weights
            except Exception as e:
                logger.warning(f"Failed to get adaptive weights, using static: {e}")
                return self.STATIC_WEIGHTS.copy()
        else:
            return self.STATIC_WEIGHTS.copy()

    def set_weights(self, weights: Dict):
        """
        Manually set custom weights

        Args:
            weights: Dict with keys matching agent names
        """
        # Validate weights sum to 1.0
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.current_weights = weights
        self._custom_weights = weights.copy()
        logger.info(f"Custom weights set: {weights}")

    def _compute_trading_levels(
        self,
        current_price,
        momentum_metrics: Dict,
        sentiment_metrics: Dict,
        week_52_high=None,
        week_52_low=None,
    ) -> Dict:
        """Compute actionable trading levels: stop loss, target price, risk/reward."""
        if not current_price:
            return {}

        levels = {
            'week_52_high': week_52_high,
            'week_52_low': week_52_low,
        }

        # ATR-based stop loss (1.5x ATR below current price)
        atr = momentum_metrics.get('atr')
        if atr and atr > 0:
            levels['atr'] = round(float(atr), 2)
            atr_stop = round(current_price - (1.5 * atr), 2)
            # Ensure stop_loss is always positive and not greater than current price
            levels['stop_loss'] = max(atr_stop, round(current_price * 0.85, 2))
        else:
            # Fallback: 7% trailing stop
            levels['stop_loss'] = round(current_price * 0.93, 2)

        # Target price: analyst mean target first, then ATR-based (3x ATR above entry)
        target_mean = sentiment_metrics.get('target_mean_price')
        if target_mean and target_mean > current_price:
            levels['target_price'] = round(float(target_mean), 2)
        elif atr and atr > 0:
            levels['target_price'] = round(current_price + (3.0 * atr), 2)
        else:
            # Fallback: 15% upside target
            levels['target_price'] = round(current_price * 1.15, 2)

        # Risk/reward ratio (guard against zero risk to avoid division by zero)
        risk = current_price - levels['stop_loss']
        reward = levels['target_price'] - current_price
        if risk > 0:
            levels['risk_reward_ratio'] = round(reward / risk, 2)
        else:
            levels['risk_reward_ratio'] = None

        return levels

    def _update_average_score(self, new_score: float):
        """Update running average score"""
        current_avg = self.stats['average_score']
        successful = self.stats['successful_analyses']

        if successful == 1:
            self.stats['average_score'] = new_score
        else:
            # Running average
            self.stats['average_score'] = (
                (current_avg * (successful - 1) + new_score) / successful
            )

    def get_stats(self) -> Dict:
        """Get scorer statistics"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_analyses'] / self.stats['total_analyses'] * 100
                if self.stats['total_analyses'] > 0 else 0
            )
        }

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_score': 0.0,
            'recommendations': {k: 0 for k in self.stats['recommendations'].keys()}
        }
        logger.info("Statistics reset")

    def get_market_regime(self) -> Dict:
        """
        Get current market regime information

        Returns:
            Dict with regime, trend, volatility, and adaptive weights
        """
        if self.market_regime_service:
            return self.market_regime_service.get_current_regime(
                data_provider=self.data_provider
            )
        else:
            from datetime import datetime
            return {
                'regime': 'STATIC',
                'trend': 'N/A',
                'volatility': 'N/A',
                'weights': self.STATIC_WEIGHTS,
                'metrics': {
                    'message': 'Adaptive weights not enabled',
                    'mode': 'static'
                },
                'timestamp': datetime.now().isoformat(),
                'cached': False
            }


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize scorer
    scorer = StockScorer()

    # Test with a single stock
    print("\n" + "="*60)
    print("Testing Stock Scorer with TCS")
    print("="*60)

    result = scorer.score_stock("TCS")

    # Display results
    print(f"\n{'='*60}")
    print(f"Analysis Results for {result['symbol']}")
    print('='*60)
    print(f"Composite Score: {result['composite_score']}/100")
    print(f"Confidence: {result['composite_confidence']:.0%}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Analysis Time: {result['analysis_time_seconds']}s")

    print(f"\n{'Agent Scores':-^60}")
    for agent_name, agent_result in result['agent_scores'].items():
        score = agent_result.get('score', 'N/A')
        conf = agent_result.get('confidence', 0)
        reasoning = agent_result.get('reasoning', 'N/A')
        print(f"\n{agent_name.upper()}: {score}/100 (conf: {conf:.0%})")
        print(f"  {reasoning}")

    print(f"\n{'Weights Used':-^60}")
    for agent, weight in result['weights_used'].items():
        print(f"  {agent}: {weight:.0%}")

    # Test batch scoring
    print("\n\n" + "="*60)
    print("Testing Batch Scoring")
    print("="*60)

    test_symbols = ["TCS", "INFY", "RELIANCE"]
    batch_results = scorer.score_stocks_batch(test_symbols)

    print(f"\n{'Top Stocks':-^60}")
    for i, res in enumerate(batch_results[:5], 1):
        print(f"{i}. {res['symbol']}: {res['composite_score']:.1f}/100 - {res.get('recommendation', 'N/A')}")

    # Print stats
    print(f"\n{'Scorer Statistics':-^60}")
    stats = scorer.get_stats()
    print(f"Total Analyses: {stats['total_analyses']}")
    print(f"Success Rate: {stats['success_rate']:.1f}%")
    print(f"Average Score: {stats['average_score']:.1f}")
    print(f"\nRecommendation Distribution:")
    for rec, count in stats['recommendations'].items():
        if count > 0:
            print(f"  {rec}: {count}")
