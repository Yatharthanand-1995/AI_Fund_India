"""
Market Regime Detection Service

Analyzes market conditions (NIFTY50) and provides adaptive weights:
- Trend Detection: Bull, Bear, Sideways
- Volatility Detection: High, Normal, Low (uses India VIX as primary signal)
- Adaptive Weights: Adjust agent weights based on regime

Strategy (IC-calibrated 2026-04-26, 29 NIFTY50 stocks):
- Bull + Normal Vol: Momentum+Institutional dominant (27/32/12/9/20)
- Bull + High Vol:   Maximum Momentum (22/38/10/10/20)
- Bear + High Vol:   Maximum Quality/Safety (22/8/38/20/12)
- Bear + Normal:     Quality + Fundamentals (28/10/32/18/12)
- Sideways:          Balanced with raised Institutional (30/25/18/10/17)

Volatility Source (India-specific):
  Primary  : India VIX (^NSEINDVIX) — forward-looking implied vol from NIFTY options
  Secondary: 30-day realized vol (backward-looking, always available)
  Blend    : 70% VIX + 30% realized when VIX is available; 100% realized as fallback.
  India VIX responds faster to FII exodus, election uncertainty, and global shocks.

FII Flow Integration (2026-05):
  FII net 30-day flow from NSE is used as a third regime confirmation input.
  Heavy FII selling during a BULL regime caps confidence (prevents overconfident
  momentum weights when foreigners are structurally exiting). Conversely, strong
  FII buying during a BEAR regime reduces conviction in defensive positioning.
  Thresholds: ±₹10,000 Cr 30d = strong signal, ±₹5,000 Cr = moderate.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

from data.fii_dii_provider import get_default_provider as get_fii_provider
from data.nse_pcr_provider import get_default_provider as get_pcr_provider
from data.market_breadth_provider import get_default_provider as get_breadth_provider

logger = logging.getLogger(__name__)


class MarketRegimeService:
    """
    Market Regime Detection Service

    Analyzes NIFTY50 index to determine:
    1. Trend: BULL, BEAR, SIDEWAYS
    2. Volatility: HIGH, NORMAL, LOW
    3. Combined Regime: BULL_NORMAL, BEAR_HIGH, etc.

    Provides adaptive weights based on regime with 6-hour caching.
    """

    # Trend thresholds
    TREND_THRESHOLDS = {
        'sma_50_200_diff_bull': 0.02,    # 50-SMA > 200-SMA by 2%
        'sma_50_200_diff_bear': -0.02,   # 50-SMA < 200-SMA by 2%
        'price_sma_50_bull': 0.01,       # Price > 50-SMA by 1%
        'price_sma_50_bear': -0.01,      # Price < 50-SMA by 1%
    }

    # Volatility thresholds (annualized %)
    # Calibrated to institutional practice: India VIX >22 triggers defensive rotation
    # (NSE/BlackRock standard). Prior threshold of 25 missed early stress signals.
    VOLATILITY_THRESHOLDS = {
        'high': 22,      # >22% = high volatility (India VIX institutional standard)
        'normal': 15,    # 15-25% = normal
        'low': 12,       # <12% = low volatility (distinct from normal)
    }

    # Adaptive weight mappings — IC-calibrated (2026-04-26)
    #
    # Source: Spearman IC measured on 29 NIFTY50 stocks:
    #   BULL regime:  Momentum IC(3M)=+0.57**, Institutional IC(3M)=+0.55**
    #                 Quality IC(3M)=-0.51** (negative in bull — risk-on market)
    #                 Fundamentals IC(3M)=-0.06 (long-horizon, near zero short-term)
    #                 Sentiment IC(3M)=-0.41  (lagging in trending markets)
    #   BEAR regime:  Quality and Fundamentals switch to positive (capital preservation)
    #                 Momentum turns negative (falling stocks keep falling in bear)
    #                 Sentiment useful for reversal detection
    #
    # Weights are proportional to absolute IC, with floors to prevent total exclusion.
    # All rows sum to 1.0.
    ADAPTIVE_WEIGHTS = {
        # ── BULL regimes: Momentum + Institutional dominate ──────────────────
        'BULL_NORMAL': {
            'fundamentals':     0.27,   # long-horizon anchor, reduced from 0.36
            'momentum':         0.32,   # top predictor in bull (IC+0.57)
            'quality':          0.12,   # negative IC in bull, kept as risk filter
            'sentiment':        0.09,   # lagging in trending market
            'institutional_flow': 0.20, # strong predictor (IC+0.55), raised from 0.10
        },
        'BULL_HIGH': {
            # High-vol bull: momentum signal even stronger; quality cut further
            'fundamentals':     0.22,
            'momentum':         0.38,
            'quality':          0.10,
            'sentiment':        0.10,
            'institutional_flow': 0.20,
        },
        'BULL_LOW': {
            # Low-vol stable bull: fundamentals matter more; room for quality recovery
            'fundamentals':     0.32,
            'momentum':         0.28,
            'quality':          0.15,
            'sentiment':        0.10,
            'institutional_flow': 0.15,
        },

        # ── BEAR regimes: Quality + Fundamentals dominate ────────────────────
        'BEAR_NORMAL': {
            # Capital preservation: quality and fundamentals are top predictors
            'fundamentals':     0.28,
            'momentum':         0.10,   # negative IC in bear (falling knives)
            'quality':          0.32,   # primary safety factor in bear
            'sentiment':        0.18,   # contrarian reversal signals
            'institutional_flow': 0.12,
        },
        'BEAR_HIGH': {
            # Panic/high-vol bear: maximum quality + fundamentals for safety
            'fundamentals':     0.22,
            'momentum':         0.08,
            'quality':          0.38,   # max quality weight in crisis
            'sentiment':        0.20,   # oversold reversal signals
            'institutional_flow': 0.12,
        },
        'BEAR_LOW': {
            # Slow bear / grinding down: quality + fundamentals balanced
            'fundamentals':     0.30,
            'momentum':         0.12,
            'quality':          0.30,
            'sentiment':        0.16,
            'institutional_flow': 0.12,
        },

        # ── SIDEWAYS regimes: Balanced, fundamentals as anchor ───────────────
        'SIDEWAYS_NORMAL': {
            # Default balanced weights — used as fallback
            'fundamentals':     0.30,
            'momentum':         0.25,
            'quality':          0.18,
            'sentiment':        0.10,
            'institutional_flow': 0.17,
        },
        'SIDEWAYS_HIGH': {
            # High-vol sideways: quality for protection, institutional for direction
            'fundamentals':     0.26,
            'momentum':         0.20,
            'quality':          0.25,
            'sentiment':        0.12,
            'institutional_flow': 0.17,
        },
        'SIDEWAYS_LOW': {
            # Low-vol range-bound: fundamentals dominate, momentum less useful
            'fundamentals':     0.34,
            'momentum':         0.22,
            'quality':          0.18,
            'sentiment':        0.10,
            'institutional_flow': 0.16,
        },
    }

    # India VIX symbol (NSE implied volatility index — forward-looking)
    INDIA_VIX_SYMBOL = "^INDIAVIX"
    # Blend weight: how much India VIX contributes vs realized vol when VIX is available
    VIX_BLEND_WEIGHT = 0.70  # 70% VIX (forward-looking) + 30% realized (backward-looking)

    # How many % the SMA gap needs to be before we consider a trend "established".
    # Below this we blend toward neutral to avoid reacting to fresh crossovers.
    SMA_GAP_FULL_CONFIDENCE_PCT = 5.0   # 5% gap → 100% regime weights
    PRICE_SMA_FULL_CONFIDENCE_PCT = 3.0  # 3% price vs SMA50 → 100% confidence

    def __init__(self, cache_duration_hours: int = 6):
        """
        Initialize Market Regime Service

        Args:
            cache_duration_hours: How long to cache regime (default: 6 hours)
        """
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cached_regime: Optional[Dict] = None
        self.cache_timestamp: Optional[datetime] = None

        logger.info(f"Market Regime Service initialized (cache: {cache_duration_hours}h)")

    def _compute_regime_confidence(self, trend: str, trend_metrics: Dict) -> float:
        """
        How firmly established is the detected regime? Returns 0.0 – 1.0.

        A freshly-crossed SMA (small gap) → low confidence → blend toward neutral.
        A well-established trend (large SMA gap + price well above/below SMA50) → 1.0.

        This is stateless — computed purely from current price data each call.
        It solves the "early regime transition" problem where e.g. a brand-new
        BEAR signal should not immediately slash momentum weights to 10%, because
        momentum keeps working for 4-8 weeks after a SMA crossover.
        """
        if trend == 'SIDEWAYS':
            return 0.6   # sideways is always somewhat certain (it's the null hypothesis)

        sma_gap_pct  = abs(trend_metrics.get('sma50_vs_sma200_pct', 0))
        price_gap_pct = abs(trend_metrics.get('price_vs_sma50_pct', 0))

        # Each metric contributes to confidence; clamp 0–1
        sma_conf   = min(1.0, sma_gap_pct  / self.SMA_GAP_FULL_CONFIDENCE_PCT)
        price_conf = min(1.0, price_gap_pct / self.PRICE_SMA_FULL_CONFIDENCE_PCT)

        # SMA gap is the primary signal; price vs SMA is secondary
        confidence = 0.6 * sma_conf + 0.4 * price_conf
        return round(float(confidence), 3)

    def _blend_weights(self, regime_weights: Dict, alpha: float) -> Dict:
        """
        Blend regime weights toward neutral (SIDEWAYS_NORMAL) by alpha.

        alpha = 1.0 → pure regime weights (fully confirmed trend)
        alpha = 0.0 → pure SIDEWAYS_NORMAL (no regime signal at all)

        Minimum alpha is clamped to 0.3 so we never go fully neutral —
        even a borderline signal deserves some regime tilt.
        """
        alpha = max(0.3, min(1.0, alpha))
        neutral = self.ADAPTIVE_WEIGHTS['SIDEWAYS_NORMAL']
        blended = {
            k: round(alpha * regime_weights[k] + (1.0 - alpha) * neutral[k], 4)
            for k in regime_weights
        }
        # Normalise to ensure exact sum = 1.0 (float arithmetic safety)
        total = sum(blended.values())
        return {k: round(v / total, 4) for k, v in blended.items()}

    def _fetch_fii_regime_signal(self, trend: str) -> Tuple[float, Dict]:
        """
        Fetch FII 30-day net flow and compute a confidence modifier for the detected trend.

        Returns (confidence_modifier, fii_metrics):
          modifier > 0  → FII flow confirms trend (e.g. buying in BULL)
          modifier < 0  → FII flow contradicts trend (e.g. selling in BULL) — cap confidence
          modifier = 0  → neutral / data unavailable

        The modifier is applied as: final_confidence = clamp(sma_confidence + modifier, 0.3, 1.0)
        Max modifier is ±0.25 — FII is a strong but not sole determinant.
        """
        try:
            provider = get_fii_provider()
            flow = provider.get_flow_data()

            if flow.get('source') == 'default' or flow.get('days_available', 0) == 0:
                return 0.0, {'fii_signal': 'unavailable'}

            fii_net = flow.get('fii_net_30d', 0.0)
            fii_trend = flow.get('fii_recent_trend', 'neutral')

            # Magnitude-based modifier (absolute crores)
            if abs(fii_net) > 10_000:
                magnitude = 0.25   # strong
            elif abs(fii_net) > 5_000:
                magnitude = 0.15   # moderate
            elif abs(fii_net) > 2_000:
                magnitude = 0.08   # mild
            else:
                magnitude = 0.0    # noise

            if magnitude == 0.0:
                return 0.0, {'fii_net_30d': fii_net, 'fii_signal': 'neutral'}

            fii_direction = 1.0 if fii_net > 0 else -1.0

            # Does FII direction agree with the trend?
            # BULL expects FII buying → fii_direction=+1 confirms → positive modifier
            # BEAR expects FII selling → fii_direction=-1 confirms → positive modifier
            if trend == 'BULL':
                modifier = fii_direction * magnitude      # +ve if buying, -ve if selling
            elif trend == 'BEAR':
                modifier = -fii_direction * magnitude     # +ve if selling, -ve if buying
            else:
                modifier = 0.0  # SIDEWAYS — FII direction doesn't clarify which way

            signal_label = (
                'confirms' if modifier > 0
                else 'contradicts' if modifier < 0
                else 'neutral'
            )
            logger.info(
                f"  FII regime signal: {fii_net:+,.0f} Cr 30d ({fii_trend}) "
                f"→ {signal_label} {trend} trend (modifier={modifier:+.2f})"
            )
            return modifier, {
                'fii_net_30d': fii_net,
                'fii_recent_trend': fii_trend,
                'fii_regime_modifier': round(modifier, 3),
                'fii_signal': signal_label,
            }
        except Exception as e:
            logger.debug(f"FII regime signal fetch failed: {e}")
            return 0.0, {'fii_signal': 'error'}

    def _fetch_pcr_regime_signal(self, trend: str) -> Tuple[float, Dict]:
        """
        Fetch NIFTY Put/Call Ratio and compute a confidence modifier.

        PCR is a contrarian indicator:
          High PCR (fear) during BULL → confirms oversold bounce, boosts confidence
          High PCR (fear) during BEAR → everyone hedged, potential reversal risk
          Low PCR (greed) during BULL → complacency, reduces confidence
          Low PCR (greed) during BEAR → no hedging = further downside risk

        Returns (modifier, pcr_metrics). Max modifier ±0.10 — smaller than FII
        because PCR is noisier (expiry week distortions, strike anchoring effects).
        """
        try:
            provider = get_pcr_provider()
            pcr_data = provider.get_pcr()

            if pcr_data.get('source') == 'default':
                return 0.0, {'pcr_signal': 'unavailable'}

            pcr = pcr_data.get('pcr', 1.0)
            signal = pcr_data.get('signal', 'neutral')
            raw_modifier = pcr_data.get('regime_modifier', 0.0)

            # PCR modifier interpretation is regime-direction-dependent
            # Fear (high PCR) is bullish for BULL (confirms buy-the-dip), bearish for BEAR (capitulation not yet)
            # Greed (low PCR) is bearish for BULL (crowded longs), bullish for BEAR (short squeeze risk)
            if trend == 'BULL':
                modifier = raw_modifier   # fear=+, greed=-
            elif trend == 'BEAR':
                modifier = -raw_modifier  # fear=- (no capitulation), greed=+ (short squeeze)
            else:
                modifier = 0.0  # SIDEWAYS — PCR doesn't clarify direction

            # Cap at ±0.10 (PCR is noisier than FII flows)
            modifier = float(np.clip(modifier, -0.10, 0.10))

            logger.info(
                f"  PCR regime signal: {pcr:.2f} ({signal}) "
                f"→ modifier={modifier:+.2f} for {trend} trend"
            )
            return modifier, {
                'nifty_pcr': pcr,
                'pcr_signal': signal,
                'pcr_regime_modifier': round(modifier, 3),
            }
        except Exception as e:
            logger.debug(f"PCR regime signal failed: {e}")
            return 0.0, {'pcr_signal': 'error'}

    def _fetch_breadth_regime_signal(self, trend: str) -> Tuple[float, Dict]:
        """
        Fetch NIFTY50 market breadth (% stocks above 200-SMA) and compute a confidence modifier.

        Breadth confirms or contradicts the index-level SMA trend:
          BULL + broad_bull (>70%) → fully confirmed, boost confidence
          BULL + broad_bear (<30%) → narrow market rally, reduce confidence significantly
          BEAR + broad_bear → fully confirmed
          BEAR + broad_bull → divergence, BEAR may be premature

        Returns (modifier, breadth_metrics). Breadth is the most reliable
        confirmation signal because it can't be distorted by a single large-cap.
        """
        try:
            provider = get_breadth_provider()
            breadth_data = provider.get_breadth()

            if breadth_data.get('source') == 'default':
                return 0.0, {'breadth_signal': 'unavailable'}

            breadth_pct = breadth_data.get('breadth_pct', 50.0)
            signal = breadth_data.get('signal', 'unknown')
            raw_modifier = breadth_data.get('regime_modifier', 0.0)

            # Breadth modifier interpretation is trend-direction-aware
            if trend == 'BULL':
                modifier = raw_modifier    # wide breadth confirms bull; narrow breadth warns
            elif trend == 'BEAR':
                modifier = -raw_modifier   # wide breadth contradicts bear; narrow confirms
            else:
                # SIDEWAYS: breadth at extremes suggests the next break direction
                modifier = raw_modifier * 0.5  # halved — less directional conviction

            modifier = float(np.clip(modifier, -0.15, 0.15))

            logger.info(
                f"  Breadth regime signal: {breadth_pct:.0f}% above 200-SMA ({signal}) "
                f"→ modifier={modifier:+.2f} for {trend} trend"
            )
            return modifier, {
                'breadth_pct': breadth_pct,
                'breadth_signal': signal,
                'breadth_regime_modifier': round(modifier, 3),
            }
        except Exception as e:
            logger.debug(f"Breadth regime signal failed: {e}")
            return 0.0, {'breadth_signal': 'error'}

    def get_current_regime(
        self,
        nifty_data: Optional[pd.DataFrame] = None,
        data_provider = None
    ) -> Dict:
        """
        Get current market regime with caching

        Args:
            nifty_data: Pre-fetched NIFTY50 data (optional)
            data_provider: Data provider to fetch NIFTY if needed

        Returns:
            {
                'regime': str (e.g., "BULL_NORMAL"),
                'trend': str ("BULL", "BEAR", "SIDEWAYS"),
                'volatility': str ("HIGH", "NORMAL", "LOW"),
                'weights': dict,
                'metrics': {
                    'current_price': float,
                    'sma_50': float,
                    'sma_200': float,
                    'volatility_pct': float,
                    ...
                },
                'timestamp': str,
                'cached': bool
            }
        """
        # Check cache
        if self._is_cache_valid():
            logger.info("Using cached market regime")
            return {**self.cached_regime, 'cached': True}

        logger.info("Detecting current market regime...")

        try:
            # Fetch NIFTY data if not provided
            if nifty_data is None or nifty_data.empty:
                if data_provider is None:
                    raise ValueError("Must provide either nifty_data or data_provider")

                logger.info("Fetching NIFTY50 data...")
                from utils.validation import get_nifty_data
                from core.exceptions import DataValidationException

                try:
                    nifty_data = get_nifty_data(data_provider, min_rows=20)
                except DataValidationException as e:
                    logger.warning(f"Could not fetch NIFTY data, using default regime: {e}")
                    # Return default regime instead of failing
                    default_weights = self.ADAPTIVE_WEIGHTS['SIDEWAYS_NORMAL']
                    return {
                        'regime': 'SIDEWAYS_NORMAL',
                        'trend': 'SIDEWAYS',
                        'volatility': 'NORMAL',
                        'weights': default_weights,
                        'base_weights': default_weights,
                        'regime_confidence': 0.3,
                        'timestamp': datetime.now().isoformat(),
                        'description': 'Default regime (NIFTY data unavailable)',
                        'metrics': {}
                    }

            # Fetch India VIX (forward-looking; graceful None on failure)
            india_vix = self._fetch_india_vix()

            # Detect regime
            trend, trend_metrics = self._detect_trend(nifty_data)
            volatility, vol_metrics = self._detect_volatility(nifty_data, india_vix=india_vix)

            # Combine regime
            regime = f"{trend}_{volatility}"

            # Get base regime weights
            base_weights = self.ADAPTIVE_WEIGHTS.get(regime, self.ADAPTIVE_WEIGHTS['SIDEWAYS_NORMAL'])

            # Compute confidence from SMA gap/price position
            sma_confidence = self._compute_regime_confidence(trend, trend_metrics)

            # FII flow: third confirmation input — adjusts confidence up or down
            fii_modifier, fii_metrics = self._fetch_fii_regime_signal(trend)

            # PCR: fourth input — extreme put/call positioning flags sentiment extremes
            pcr_modifier, pcr_metrics = self._fetch_pcr_regime_signal(trend)

            # Breadth: fifth input — % of NIFTY50 stocks above 200-SMA (most reliable)
            breadth_modifier, breadth_metrics = self._fetch_breadth_regime_signal(trend)

            # Combined confidence: SMA base + FII + PCR + Breadth, floored at 0.3
            # Breadth is cached 4h so it's cheap; FII/PCR are 15-60min cached
            confidence = float(np.clip(
                sma_confidence + fii_modifier + pcr_modifier + breadth_modifier, 0.3, 1.0
            ))

            weights = self._blend_weights(base_weights, alpha=confidence)

            logger.info(
                f"   Regime confidence: {confidence:.2f} "
                f"(sma={sma_confidence:.2f}, fii={fii_modifier:+.2f}, "
                f"pcr={pcr_modifier:+.2f}, breadth={breadth_modifier:+.2f}) "
                f"[{'established' if confidence >= 0.7 else 'transitioning' if confidence >= 0.4 else 'borderline'}]"
            )
            if confidence < 1.0:
                logger.info(f"   Blended weights (alpha={confidence:.2f}): "
                            f"F={weights['fundamentals']:.0%} M={weights['momentum']:.0%} "
                            f"Q={weights['quality']:.0%} S={weights['sentiment']:.0%} "
                            f"I={weights['institutional_flow']:.0%}")

            # Assemble result
            result = {
                'regime': regime,
                'trend': trend,
                'volatility': volatility,
                'weights': weights,
                'base_weights': base_weights,  # unblended, for inspection
                'regime_confidence': confidence,
                'sma_confidence': sma_confidence,
                'metrics': {
                    **trend_metrics,
                    **vol_metrics,
                    **fii_metrics,
                    **pcr_metrics,
                    **breadth_metrics,
                },
                'timestamp': datetime.now().isoformat(),
                'cached': False
            }

            # Cache result
            self.cached_regime = result
            self.cache_timestamp = datetime.now()

            logger.info(f"✅ Market Regime: {regime} (confidence: {confidence:.2f})")
            logger.info(f"   Trend: {trend}, Volatility: {volatility}")

            return result

        except Exception as e:
            logger.error(f"Failed to detect market regime: {e}", exc_info=True)

            # Return default regime on error
            default_weights = self.ADAPTIVE_WEIGHTS['SIDEWAYS_NORMAL']
            return {
                'regime': 'SIDEWAYS_NORMAL',
                'trend': 'SIDEWAYS',
                'volatility': 'NORMAL',
                'weights': default_weights,
                'base_weights': default_weights,
                'regime_confidence': 0.3,
                'metrics': {},
                'timestamp': datetime.now().isoformat(),
                'cached': False,
                'error': str(e)
            }

    def _detect_trend(self, nifty_data: pd.DataFrame) -> Tuple[str, Dict]:
        """
        Detect market trend

        Rules:
        - BULL: 50-SMA > 200-SMA AND price > 50-SMA
        - BEAR: 50-SMA < 200-SMA AND price < 50-SMA
        - SIDEWAYS: Mixed signals

        Returns:
            (trend_str, metrics_dict)
        """
        try:
            # Get current price
            current_price = float(nifty_data['Close'].iloc[-1])

            # Calculate moving averages
            sma_50 = nifty_data['Close'].rolling(window=50).mean().iloc[-1]
            sma_200 = nifty_data['Close'].rolling(window=200).mean().iloc[-1]

            # Calculate relative positions
            price_vs_sma50 = (current_price - sma_50) / sma_50
            sma50_vs_sma200 = (sma_50 - sma_200) / sma_200

            metrics = {
                'current_price': float(current_price),
                'sma_50': float(sma_50),
                'sma_200': float(sma_200),
                'price_vs_sma50_pct': float(price_vs_sma50 * 100),
                'sma50_vs_sma200_pct': float(sma50_vs_sma200 * 100)
            }

            # Determine trend
            if (sma50_vs_sma200 > self.TREND_THRESHOLDS['sma_50_200_diff_bull'] and
                price_vs_sma50 > self.TREND_THRESHOLDS['price_sma_50_bull']):
                trend = 'BULL'
            elif (sma50_vs_sma200 < self.TREND_THRESHOLDS['sma_50_200_diff_bear'] and
                  price_vs_sma50 < self.TREND_THRESHOLDS['price_sma_50_bear']):
                trend = 'BEAR'
            else:
                trend = 'SIDEWAYS'

            logger.info(f"  Trend: {trend}")
            logger.info(f"    Price vs 50-SMA: {price_vs_sma50*100:+.2f}%")
            logger.info(f"    50-SMA vs 200-SMA: {sma50_vs_sma200*100:+.2f}%")

            return trend, metrics

        except Exception as e:
            logger.error(f"Trend detection failed: {e}")
            return 'SIDEWAYS', {}

    def _fetch_india_vix(self) -> Optional[float]:
        """
        Fetch the latest India VIX level from yfinance.
        Returns the most recent closing VIX value, or None on failure.
        India VIX is the implied volatility index derived from NIFTY 50 options.
        """
        try:
            import yfinance as yf
            vix_ticker = yf.Ticker(self.INDIA_VIX_SYMBOL)
            vix_hist = vix_ticker.history(period="5d")
            if vix_hist.empty:
                return None
            vix_level = float(vix_hist['Close'].iloc[-1])
            logger.info(f"  India VIX: {vix_level:.2f}")
            return vix_level
        except Exception as e:
            logger.debug(f"India VIX fetch failed (will use realized vol): {e}")
            return None

    def _detect_volatility(
        self,
        nifty_data: pd.DataFrame,
        window: int = 30,
        india_vix: Optional[float] = None
    ) -> Tuple[str, Dict]:
        """
        Detect market volatility.

        Uses India VIX as primary signal (forward-looking implied vol) blended
        with 30-day realized vol (backward-looking). Falls back to realized vol
        only when VIX is unavailable.

        Returns:
            (volatility_str, metrics_dict)
        """
        try:
            # Calculate realized returns-based volatility
            returns = nifty_data['Close'].pct_change()
            realized_vol = returns.rolling(window=window).std().iloc[-1]
            realized_vol_pct = float(realized_vol * np.sqrt(252) * 100)

            vol_series = returns.rolling(window=window).std() * np.sqrt(252) * 100
            vol_trend = 'increasing' if vol_series.iloc[-1] > vol_series.iloc[-10] else 'decreasing'

            # Blend India VIX (forward-looking) with realized vol (backward-looking)
            if india_vix is not None and india_vix > 0:
                effective_vol_pct = (
                    self.VIX_BLEND_WEIGHT * india_vix
                    + (1.0 - self.VIX_BLEND_WEIGHT) * realized_vol_pct
                )
                vol_source = 'india_vix_blend'
            else:
                effective_vol_pct = realized_vol_pct
                vol_source = 'realized_only'

            metrics = {
                'volatility_pct': round(effective_vol_pct, 2),
                'realized_vol_pct': round(realized_vol_pct, 2),
                'india_vix': round(india_vix, 2) if india_vix is not None else None,
                'volatility_source': vol_source,
                'volatility_trend': vol_trend,
                'volatility_window_days': window,
            }

            # Classify using blended effective volatility
            if effective_vol_pct > self.VOLATILITY_THRESHOLDS['high']:
                vol_class = 'HIGH'
            elif effective_vol_pct > self.VOLATILITY_THRESHOLDS['normal']:
                vol_class = 'NORMAL'
            else:
                vol_class = 'LOW'

            vix_str = f"{india_vix:.1f}" if india_vix is not None else "N/A"
            logger.info(
                f"  Volatility: {vol_class} (effective={effective_vol_pct:.1f}%, "
                f"vix={vix_str}, realized={realized_vol_pct:.1f}%, source={vol_source})"
            )

            return vol_class, metrics

        except Exception as e:
            logger.error(f"Volatility detection failed: {e}")
            return 'NORMAL', {}

    def _is_cache_valid(self) -> bool:
        """Check if cached regime is still valid"""
        if self.cached_regime is None or self.cache_timestamp is None:
            return False

        age = datetime.now() - self.cache_timestamp
        return age < self.cache_duration

    def clear_cache(self):
        """Manually clear cache"""
        self.cached_regime = None
        self.cache_timestamp = None
        logger.info("Market regime cache cleared")

    def get_cache_info(self) -> Dict:
        """Get cache information"""
        if self.cache_timestamp is None:
            return {
                'cached': False,
                'age_seconds': None,
                'expires_in_seconds': None
            }

        age = datetime.now() - self.cache_timestamp
        remaining = self.cache_duration - age

        return {
            'cached': True,
            'cached_regime': self.cached_regime.get('regime') if self.cached_regime else None,
            'age_seconds': age.total_seconds(),
            'expires_in_seconds': max(0, remaining.total_seconds()),
            'cache_valid': self._is_cache_valid()
        }

    def get_all_regimes_weights(self) -> Dict:
        """Get all available regime weight configurations"""
        return self.ADAPTIVE_WEIGHTS.copy()


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize service
    regime_service = MarketRegimeService(cache_duration_hours=6)

    # Create sample NIFTY data (bull market)
    print("\n" + "="*60)
    print("Testing Market Regime Detection")
    print("="*60)

    # Simulate bull market
    dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq='D')
    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(300).cumsum() * 0.01)  # Uptrend

    sample_nifty = pd.DataFrame({
        'Close': prices,
        'High': prices * 1.01,
        'Low': prices * 0.99,
        'Volume': np.random.randint(1000000, 10000000, 300)
    }, index=dates)

    # Detect regime
    regime_info = regime_service.get_current_regime(nifty_data=sample_nifty)

    # Display results
    print(f"\n{'Detected Regime':-^60}")
    print(f"Regime: {regime_info['regime']}")
    print(f"Trend: {regime_info['trend']}")
    print(f"Volatility: {regime_info['volatility']}")

    print(f"\n{'Market Metrics':-^60}")
    for key, value in regime_info['metrics'].items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    print(f"\n{'Adaptive Weights':-^60}")
    for agent, weight in regime_info['weights'].items():
        print(f"  {agent}: {weight:.0%}")

    # Test cache
    print(f"\n{'Cache Test':-^60}")
    regime_info2 = regime_service.get_current_regime(nifty_data=sample_nifty)
    print(f"Second call used cache: {regime_info2['cached']}")

    cache_info = regime_service.get_cache_info()
    print(f"Cache age: {cache_info['age_seconds']:.1f}s")
    print(f"Cache expires in: {cache_info['expires_in_seconds']/3600:.1f}h")

    # Display all regime configurations
    print(f"\n{'All Regime Weight Configurations':-^60}")
    all_weights = regime_service.get_all_regimes_weights()
    for regime_name, weights in all_weights.items():
        print(f"\n{regime_name}:")
        for agent, weight in weights.items():
            print(f"  {agent}: {weight:.0%}")
