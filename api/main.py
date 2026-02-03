"""
FastAPI Backend for AI Hedge Fund System

Exposes REST API endpoints for:
- Single stock analysis
- Batch stock analysis
- Top picks from NIFTY 50
- Market regime detection
- Health checks
- Stock universe listing

Run with: uvicorn api.main:app --reload --port 8000
"""

import logging
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import pandas as pd
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.stock_scorer import StockScorer
from core.market_regime_service import MarketRegimeService
from core.data_collector import init_collector, start_collector, stop_collector, get_collector
from narrative_engine.narrative_engine import InvestmentNarrativeEngine
from data.hybrid_provider import HybridDataProvider
from data.historical_db import HistoricalDatabase
from data.stock_universe import get_universe
from utils.logging_config import setup_logging, get_logger
from utils.api_middleware import (
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    ErrorTrackingMiddleware,
)
from utils.metrics import metrics, track_api_request, track_api_error, Timer
from utils.validation import get_nifty_data
from core.exceptions import DataValidationException

# Setup comprehensive logging
setup_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    json_format=os.getenv('LOG_JSON', 'false').lower() == 'true'
)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Hedge Fund - Indian Stock Market",
    description="AI-powered stock analysis system for NSE/BSE with 5 specialized agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - Secure configuration
# Support multiple common dev server ports (3000-3002, 5173)
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:5173').split(',')
allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    max_age=600
)

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/hour"],
    enabled=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Logging and monitoring middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold_ms=2000)
app.add_middleware(ErrorTrackingMiddleware)

# Initialize dependency injection container
from core.di_container import get_container
from core.cache_manager import get_cache_manager
from core.config import get_global_config

config = get_global_config()
container = get_container()

# Get services from container
data_provider = container.get('data_provider')
market_regime_service = container.get('market_regime_service')
stock_scorer = container.get('stock_scorer')
narrative_engine = container.get('narrative_engine')
stock_universe = container.get('stock_universe')
historical_db = container.get('historical_db')

# Initialize data collector
data_collector = init_collector(
    db=historical_db,
    stock_scorer=stock_scorer,
    market_regime_service=market_regime_service
)

# Initialize unified cache manager
cache_manager = get_cache_manager()
api_cache = cache_manager.get_cache('api', max_size=1000, ttl=900)  # 15 minutes

logger.info("FastAPI backend initialized successfully")

# Cache duration constant (matches the TTL set above)
API_CACHE_DURATION = 900  # 15 minutes in seconds

# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request model for single stock analysis"""
    symbol: str = Field(..., description="Stock symbol (e.g., TCS, RELIANCE)")
    include_narrative: bool = Field(default=True, description="Include LLM-generated narrative")

    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format with security checks"""
        import re

        if not v or not isinstance(v, str):
            raise ValueError("Symbol must be a non-empty string")

        v = v.strip()

        # Check length
        if len(v) < 1:
            raise ValueError("Symbol cannot be empty")
        if len(v) > 20:
            raise ValueError("Symbol too long (max 20 characters)")

        # Check format: Only alphanumeric, dash, dot, underscore, caret
        if not re.match(r'^[\w\.\-\^]+$', v):
            raise ValueError("Symbol contains invalid characters. Only alphanumeric, dash, dot, underscore, and caret allowed")

        # Security: Block common SQL keywords
        sql_keywords = ['SELECT', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'UNION', 'ALTER', 'CREATE']
        upper_symbol = v.upper()
        if any(keyword in upper_symbol for keyword in sql_keywords):
            raise ValueError("Symbol contains invalid keywords")

        return v.upper()

    class Config:
        schema_extra = {
            "example": {
                "symbol": "TCS",
                "include_narrative": True
            }
        }


class BatchAnalyzeRequest(BaseModel):
    """Request model for batch stock analysis"""
    symbols: List[str] = Field(..., description="List of stock symbols", min_items=1, max_items=50)
    include_narrative: bool = Field(default=False, description="Include narratives (slower)")
    sort_by: str = Field(default="score", description="Sort by: score, confidence, symbol")

    @validator('symbols')
    def validate_symbols(cls, v):
        """Validate symbols list"""
        if not v:
            raise ValueError("Symbols list cannot be empty")
        if len(v) > 50:
            raise ValueError("Maximum 50 symbols allowed per batch")
        return [s.strip().upper() for s in v]

    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort_by field"""
        allowed = ['score', 'confidence', 'symbol']
        if v not in allowed:
            raise ValueError(f"sort_by must be one of: {allowed}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "symbols": ["TCS", "INFY", "WIPRO"],
                "include_narrative": False,
                "sort_by": "score"
            }
        }


class AgentScore(BaseModel):
    """Agent scoring details"""
    score: float = Field(..., description="Agent score (0-100)")
    confidence: float = Field(..., description="Confidence level (0-1)")
    reasoning: str = Field(..., description="Human-readable reasoning")
    metrics: Dict = Field(default_factory=dict, description="Detailed metrics")
    breakdown: Dict = Field(default_factory=dict, description="Score breakdown")


class NarrativeResponse(BaseModel):
    """Investment narrative"""
    investment_thesis: str
    key_strengths: List[str]
    key_risks: List[str]
    summary: str
    provider: str


class StockAnalysisResponse(BaseModel):
    """Response model for stock analysis"""
    symbol: str
    composite_score: float = Field(..., description="Final composite score (0-100)")
    recommendation: str = Field(..., description="Investment recommendation")
    confidence: float = Field(..., description="Overall confidence (0-1)")

    # Agent scores
    agent_scores: Dict[str, AgentScore]

    # Weights used
    weights: Dict[str, float] = Field(..., description="Agent weights applied")

    # Market regime
    market_regime: Optional[Dict] = Field(None, description="Current market regime")

    # Narrative (optional)
    narrative: Optional[NarrativeResponse] = None

    # Metadata
    timestamp: str
    cached: bool = Field(default=False, description="Whether result was cached")


class BatchAnalysisResponse(BaseModel):
    """Response model for batch analysis"""
    total_analyzed: int
    successful: int
    failed: int
    results: List[StockAnalysisResponse]
    timestamp: str
    duration_seconds: float


class TopPicksResponse(BaseModel):
    """Response model for top picks"""
    market_regime: Dict
    top_picks: List[StockAnalysisResponse]
    total_analyzed: int
    timestamp: str
    duration_seconds: float


class MarketRegimeResponse(BaseModel):
    """Response model for market regime"""
    regime: str = Field(..., description="Combined regime (e.g., BULL_NORMAL)")
    trend: str = Field(..., description="Trend: BULL, BEAR, SIDEWAYS")
    volatility: str = Field(..., description="Volatility: HIGH, NORMAL, LOW")
    weights: Dict[str, float] = Field(..., description="Adaptive agent weights")
    metrics: Dict = Field(..., description="Market metrics")
    timestamp: str
    cached: bool


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    components: Dict[str, Dict[str, Any]]
    version: str


class StockUniverseResponse(BaseModel):
    """Response model for stock universe"""
    total_stocks: int
    indices: Dict[str, List[str]]
    timestamp: str


# ============================================================================
# New Response Models for Enhanced Features
# ============================================================================

class HistoricalDataPoint(BaseModel):
    """Single historical data point"""
    timestamp: str
    composite_score: float
    recommendation: str
    confidence: float
    price: Optional[float] = None


class StockHistoryResponse(BaseModel):
    """Response model for stock history"""
    symbol: str
    history: List[HistoricalDataPoint]
    trend: Dict[str, Any]
    statistics: Dict[str, float]
    data_points: int
    timestamp: str


class RegimeHistoryPoint(BaseModel):
    """Single regime history point"""
    timestamp: str
    regime: str
    trend: str
    volatility: str
    weights: Dict[str, float]


class RegimeHistoryResponse(BaseModel):
    """Response model for regime history"""
    history: List[RegimeHistoryPoint]
    current_regime: Optional[RegimeHistoryPoint]
    data_points: int
    timestamp: str


class SystemAnalyticsResponse(BaseModel):
    """Response model for system analytics"""
    uptime_seconds: float
    total_requests: int
    total_errors: int
    error_rate: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    cache_hit_rate: float
    agent_performance: Dict[str, float]
    timestamp: str


class SectorStats(BaseModel):
    """Sector statistics"""
    sector: str
    stock_count: int
    avg_score: float
    top_pick: str
    trend: str


class SectorAnalysisResponse(BaseModel):
    """Response model for sector analysis"""
    sectors: List[SectorStats]
    total_sectors: int
    timestamp: str


class WatchlistItem(BaseModel):
    """Watchlist item"""
    symbol: str
    added_at: str
    notes: Optional[str]
    latest_score: Optional[float]
    latest_recommendation: Optional[str]


class WatchlistResponse(BaseModel):
    """Response model for watchlist"""
    watchlist: List[WatchlistItem]
    total_items: int
    timestamp: str


class AddToWatchlistRequest(BaseModel):
    """Request model for adding to watchlist"""
    symbol: str = Field(..., description="Stock symbol")
    notes: Optional[str] = Field(None, description="Optional notes")

    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format with security checks (same as AnalyzeRequest)"""
        import re

        if not v or not isinstance(v, str):
            raise ValueError("Symbol must be a non-empty string")

        v = v.strip()

        # Check length
        if len(v) < 1:
            raise ValueError("Symbol cannot be empty")
        if len(v) > 20:
            raise ValueError("Symbol too long (max 20 characters)")

        # Check format: Only alphanumeric, dash, dot, underscore, caret
        if not re.match(r'^[\w\.\-\^]+$', v):
            raise ValueError("Symbol contains invalid characters. Only alphanumeric, dash, dot, underscore, and caret allowed")

        # Security: Block common SQL keywords
        sql_keywords = ['SELECT', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'UNION', 'ALTER', 'CREATE']
        upper_symbol = v.upper()
        if any(keyword in upper_symbol for keyword in sql_keywords):
            raise ValueError("Symbol contains invalid keywords")

        return v.upper()


class CompareRequest(BaseModel):
    """Request model for stock comparison"""
    symbols: List[str] = Field(..., min_items=2, max_items=4)
    include_history: bool = Field(default=False)

    @validator('symbols')
    def validate_symbols(cls, v):
        """Validate symbols list with security checks"""
        import re

        if len(v) < 2:
            raise ValueError("At least 2 symbols required for comparison")
        if len(v) > 4:
            raise ValueError("Maximum 4 symbols allowed")

        # Validate each symbol
        validated = []
        for symbol in v:
            if not symbol or not isinstance(symbol, str):
                raise ValueError("Each symbol must be a non-empty string")

            symbol = symbol.strip()

            # Check length
            if len(symbol) < 1:
                raise ValueError("Symbol cannot be empty")
            if len(symbol) > 20:
                raise ValueError("Symbol too long (max 20 characters)")

            # Check format
            if not re.match(r'^[\w\.\-\^]+$', symbol):
                raise ValueError(f"Symbol '{symbol}' contains invalid characters")

            # Security: Block SQL keywords
            sql_keywords = ['SELECT', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'UNION', 'ALTER', 'CREATE']
            if any(keyword in symbol.upper() for keyword in sql_keywords):
                raise ValueError(f"Symbol '{symbol}' contains invalid keywords")

            validated.append(symbol.upper())

        return validated


class ComparisonResponse(BaseModel):
    """Response model for stock comparison"""
    comparisons: List[StockAnalysisResponse]
    total_stocks: int
    timestamp: str


# ============================================================================
# Helper Functions
# ============================================================================

def get_cache_key(endpoint: str, params: str) -> str:
    """Generate cache key"""
    return f"{endpoint}:{params}"


def get_from_cache(cache_key: str) -> Optional[Dict]:
    """Get from cache if valid (uses CacheManager)"""
    cached_value = api_cache.get(cache_key)
    if cached_value is not None:
        logger.info(f"Cache hit: {cache_key}")
        return cached_value
    return None


def save_to_cache(cache_key: str, data: Dict):
    """Save to cache (uses CacheManager with TTL)"""
    api_cache.set(cache_key, data, ttl=API_CACHE_DURATION)
    logger.info(f"Cached: {cache_key}")


def format_agent_scores(agent_results: Dict) -> Dict[str, AgentScore]:
    """Format agent results into AgentScore models"""
    formatted = {}
    for agent_name, result in agent_results.items():
        formatted[agent_name] = AgentScore(
            score=result.get('score', 0.0),
            confidence=result.get('confidence', 0.0),
            reasoning=result.get('reasoning', ''),
            metrics=result.get('metrics', {}),
            breakdown=result.get('breakdown', {})
        )
    return formatted


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "service": "AI Hedge Fund - Indian Stock Market",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "analyze": "POST /analyze",
            "batch": "POST /analyze/batch",
            "top_picks": "GET /portfolio/top-picks",
            "regime": "GET /market/regime",
            "health": "GET /health",
            "universe": "GET /stocks/universe"
        }
    }


@app.post("/analyze", response_model=StockAnalysisResponse, tags=["Analysis"])
@limiter.limit("30/minute")
async def analyze_stock(body: AnalyzeRequest, request: Request):
    """
    Analyze a single stock

    Returns comprehensive analysis with:
    - Composite score (0-100)
    - Recommendation (STRONG BUY to SELL)
    - All 5 agent scores with reasoning
    - Current market regime
    - Optional LLM-generated narrative
    """
    try:
        symbol = body.symbol
        logger.info(f"Analyzing stock: {symbol}")

        # Check cache
        cache_key = get_cache_key("analyze", f"{symbol}:{body.include_narrative}")
        cached = get_from_cache(cache_key)
        if cached:
            return StockAnalysisResponse(**{**cached, 'cached': True})

        # Fetch NIFTY data for market context
        try:
            nifty_data = get_nifty_data(data_provider, min_rows=20)
        except DataValidationException as e:
            logger.warning(f"Could not fetch NIFTY data: {e}. Proceeding without market context.")
            nifty_data = None

        # Score stock
        start_time = time.time()
        result = stock_scorer.score_stock(symbol, nifty_data=nifty_data)
        duration = time.time() - start_time

        logger.info(f"Scoring completed in {duration:.2f}s: {symbol} = {result['composite_score']:.1f}")

        # Format response
        response_data = {
            'symbol': symbol,
            'composite_score': result['composite_score'],
            'recommendation': result['recommendation'],
            'confidence': result['composite_confidence'],
            'agent_scores': format_agent_scores(result['agent_scores']),
            'weights': result.get('weights_used', {}),
            'market_regime': result.get('market_regime'),
            'timestamp': datetime.now().isoformat(),
            'cached': False
        }

        # Generate narrative if requested
        if body.include_narrative:
            try:
                narrative = narrative_engine.generate_narrative(
                    symbol=symbol,
                    agent_scores=result['agent_scores'],
                    composite_score=result['composite_score'],
                    recommendation=result['recommendation'],
                    stock_info={}  # Can pass additional info if needed
                )
                response_data['narrative'] = NarrativeResponse(**narrative)
            except Exception as e:
                logger.warning(f"Narrative generation failed: {e}")
                # Continue without narrative

        # Cache result
        save_to_cache(cache_key, response_data)

        # Save to historical database
        try:
            narrative_text = None
            if response_data.get('narrative'):
                narrative_text = response_data['narrative'].summary

            historical_db.save_stock_analysis(
                symbol=symbol,
                composite_score=result['composite_score'],
                recommendation=result['recommendation'],
                confidence=result['composite_confidence'],
                agent_scores=result.get('agent_scores', {}),
                weights=result.get('weights_used', {}),
                market_regime=result.get('market_regime'),
                narrative=narrative_text
            )

            # Track search
            historical_db.track_search(symbol, source='manual')
        except Exception as e:
            logger.warning(f"Failed to save analysis to database: {e}")

        return StockAnalysisResponse(**response_data)

    except Exception as e:
        logger.error(f"Analysis failed for {request.symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze/batch", response_model=BatchAnalysisResponse, tags=["Analysis"])
@limiter.limit("10/minute")
async def analyze_batch(body: BatchAnalyzeRequest, request: Request):
    """
    Analyze multiple stocks in batch

    Supports up to 50 stocks per request.
    Results are sorted by score (descending) by default.
    """
    try:
        logger.info(f"Batch analysis: {len(body.symbols)} stocks")

        start_time = time.time()

        # Fetch NIFTY data once for all stocks
        try:
            nifty_data = get_nifty_data(data_provider, min_rows=20)
        except DataValidationException as e:
            logger.warning(f"Could not fetch NIFTY data: {e}. Proceeding without market context.")
            nifty_data = None

        # Get market regime once
        regime = stock_scorer.get_market_regime()

        # Score all stocks
        batch_results = stock_scorer.score_stocks_batch(symbols=body.symbols)

        # Format results
        formatted_results = []
        successful = 0
        failed = 0

        for result in batch_results:
            try:
                response_data = {
                    'symbol': result['symbol'],
                    'composite_score': result['composite_score'],
                    'recommendation': result['recommendation'],
                    'confidence': result['composite_confidence'],
                    'agent_scores': format_agent_scores(result['agent_scores']),
                    'weights': result.get('weights_used', {}),
                    'market_regime': regime,
                    'timestamp': datetime.now().isoformat(),
                    'cached': False
                }

                # Generate narrative if requested
                if body.include_narrative:
                    try:
                        narrative = narrative_engine.generate_narrative(
                            symbol=result['symbol'],
                            agent_scores=result['agent_scores'],
                            composite_score=result['composite_score'],
                            recommendation=result['recommendation'],
                            stock_info={}
                        )
                        response_data['narrative'] = NarrativeResponse(**narrative)
                    except Exception as e:
                        logger.warning(f"Narrative generation failed for {result['symbol']}: {e}")

                formatted_results.append(StockAnalysisResponse(**response_data))
                successful += 1

            except Exception as e:
                logger.error(f"Failed to format result for {result.get('symbol', 'unknown')}: {e}")
                failed += 1

        # Sort results
        if body.sort_by == 'score':
            formatted_results.sort(key=lambda x: x.composite_score, reverse=True)
        elif body.sort_by == 'confidence':
            formatted_results.sort(key=lambda x: x.confidence, reverse=True)
        elif body.sort_by == 'symbol':
            formatted_results.sort(key=lambda x: x.symbol)

        duration = time.time() - start_time

        logger.info(f"Batch analysis completed: {successful} successful, {failed} failed in {duration:.2f}s")

        return BatchAnalysisResponse(
            total_analyzed=len(body.symbols),
            successful=successful,
            failed=failed,
            results=formatted_results,
            timestamp=datetime.now().isoformat(),
            duration_seconds=round(duration, 2)
        )

    except Exception as e:
        logger.error(f"Batch analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@app.get("/portfolio/top-picks", response_model=TopPicksResponse, tags=["Portfolio"])
async def get_top_picks(
    limit: int = Query(default=10, ge=1, le=50, description="Number of top picks"),
    include_narrative: bool = Query(default=False, description="Include narratives (slower)")
):
    """
    Get top stock picks from NIFTY 50

    Analyzes all NIFTY 50 stocks and returns top performers
    based on composite score.
    """
    try:
        logger.info(f"Generating top {limit} picks from NIFTY 50")

        # Check cache
        cache_key = get_cache_key("top_picks", f"{limit}:{include_narrative}")
        cached = get_from_cache(cache_key)
        if cached:
            return TopPicksResponse(**cached)

        start_time = time.time()

        # Get NIFTY 50 constituents from stock universe
        nifty_50_symbols = stock_universe.get_symbols('NIFTY_50')

        # Fetch NIFTY data
        try:
            nifty_data = get_nifty_data(data_provider, min_rows=20)
        except DataValidationException as e:
            logger.warning(f"Could not fetch NIFTY data: {e}. Using default market regime.")
            nifty_data = None

        # Get market regime
        regime = stock_scorer.get_market_regime()

        # Score all stocks
        logger.info(f"Scoring {len(nifty_50_symbols)} NIFTY 50 stocks...")
        batch_results = stock_scorer.score_stocks_batch(symbols=nifty_50_symbols)

        # Format and sort by score
        formatted_results = []
        for result in batch_results[:limit]:  # Top N
            try:
                response_data = {
                    'symbol': result['symbol'],
                    'composite_score': result['composite_score'],
                    'recommendation': result['recommendation'],
                    'confidence': result['composite_confidence'],
                    'agent_scores': format_agent_scores(result['agent_scores']),
                    'weights': result.get('weights_used', {}),
                    'market_regime': regime,
                    'timestamp': datetime.now().isoformat(),
                    'cached': False
                }

                # Generate narrative if requested
                if include_narrative:
                    try:
                        narrative = narrative_engine.generate_narrative(
                            symbol=result['symbol'],
                            agent_scores=result['agent_scores'],
                            composite_score=result['composite_score'],
                            recommendation=result['recommendation'],
                            stock_info={}
                        )
                        response_data['narrative'] = NarrativeResponse(**narrative)
                    except Exception as e:
                        logger.warning(f"Narrative generation failed for {result['symbol']}: {e}")

                formatted_results.append(StockAnalysisResponse(**response_data))

            except Exception as e:
                logger.error(f"Failed to format result for {result.get('symbol', 'unknown')}: {e}")

        duration = time.time() - start_time

        logger.info(f"Top picks generated: {len(formatted_results)} stocks in {duration:.2f}s")

        response_data = {
            'market_regime': regime,
            'top_picks': formatted_results,
            'total_analyzed': len(nifty_50_symbols),
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': round(duration, 2)
        }

        # Cache for 15 minutes
        save_to_cache(cache_key, response_data)

        return TopPicksResponse(**response_data)

    except Exception as e:
        logger.error(f"Top picks generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Top picks generation failed: {str(e)}")


@app.get("/market/regime", response_model=MarketRegimeResponse, tags=["Market"])
async def get_market_regime():
    """
    Get current market regime

    Returns:
    - Regime (BULL_NORMAL, BEAR_HIGH, etc.)
    - Trend (BULL, BEAR, SIDEWAYS)
    - Volatility (HIGH, NORMAL, LOW)
    - Adaptive weights for agents
    - Market metrics
    """
    try:
        logger.info("Fetching market regime")

        # Check cache
        cache_key = get_cache_key("regime", "current")
        cached = get_from_cache(cache_key)
        if cached:
            return MarketRegimeResponse(**{**cached, 'cached': True})

        # Fetch NIFTY data
        try:
            nifty_data = get_nifty_data(data_provider, min_rows=20)
        except DataValidationException as e:
            logger.error(f"Failed to fetch NIFTY data for regime detection: {e}")
            raise HTTPException(status_code=503, detail="Market regime data unavailable")

        # Get regime
        regime = stock_scorer.get_market_regime()

        response_data = {
            'regime': regime['regime'],
            'trend': regime['trend'],
            'volatility': regime['volatility'],
            'weights': regime['weights'],
            'metrics': regime['metrics'],
            'timestamp': regime['timestamp'],
            'cached': regime.get('cached', False)
        }

        # Cache
        save_to_cache(cache_key, response_data)

        return MarketRegimeResponse(**response_data)

    except Exception as e:
        logger.error(f"Market regime fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Market regime fetch failed: {str(e)}")


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """
    Health check endpoint

    Checks status of all critical components:
    - Data provider
    - Stock scorer
    - Narrative engine
    - Market regime service
    """
    try:
        components = {}
        overall_status = "healthy"

        # Check data provider
        try:
            test_data = data_provider.get_comprehensive_data('TCS')
            components['data_provider'] = {
                'status': 'healthy',
                'nse_provider': 'available' if hasattr(data_provider, 'nse_available') and data_provider.nse_available else 'unavailable',
                'yahoo_provider': 'available' if hasattr(data_provider, 'yahoo_available') and data_provider.yahoo_available else 'unavailable',
                'prefer_provider': data_provider.prefer_provider if hasattr(data_provider, 'prefer_provider') else 'unknown',
                'test_symbol': 'TCS',
                'data_available': not test_data.get('historical_data', pd.DataFrame()).empty
            }
        except Exception as e:
            components['data_provider'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            overall_status = "degraded"

        # Check stock scorer
        try:
            components['stock_scorer'] = {
                'status': 'healthy',
                'agents': 5,
                'adaptive_weights': stock_scorer.use_adaptive_weights
            }
        except Exception as e:
            components['stock_scorer'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            overall_status = "degraded"

        # Check narrative engine
        try:
            components['narrative_engine'] = {
                'status': 'healthy',
                'provider': narrative_engine.llm_provider if hasattr(narrative_engine, 'llm_provider') else 'unknown',
                'enabled': narrative_engine.enable_llm if hasattr(narrative_engine, 'enable_llm') else False
            }
        except Exception as e:
            components['narrative_engine'] = {
                'status': 'degraded',
                'error': str(e)
            }

        # Check market regime service
        try:
            if stock_scorer.market_regime_service:
                cache_info = stock_scorer.market_regime_service.get_cache_info()
                components['market_regime'] = {
                    'status': 'healthy',
                    'cached': cache_info['cached'],
                    'cache_valid': cache_info.get('cache_valid', False)
                }
            else:
                components['market_regime'] = {
                    'status': 'disabled'
                }
        except Exception as e:
            components['market_regime'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            overall_status = "degraded"

        # Check stock universe
        try:
            stats = stock_universe.get_universe_stats()
            components['stock_universe'] = {
                'status': 'healthy',
                'total_symbols': stats['total_unique_symbols'],
                'indices_count': stats['indices_count'],
                'last_updated': stock_universe.last_updated
            }
        except Exception as e:
            components['stock_universe'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            overall_status = "degraded"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            components=components,
            version="1.0.0"
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/metrics", tags=["General"])
async def get_metrics():
    """
    Get system metrics

    Returns performance and usage statistics:
    - Request counts and error rates
    - Response time percentiles
    - Agent execution times
    - Cache hit rates
    - Uptime
    """
    try:
        return metrics.get_stats()
    except Exception as e:
        logger.error(f"Metrics fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Metrics fetch failed: {str(e)}")


@app.get("/metrics/summary", tags=["General"])
async def get_metrics_summary():
    """
    Get metrics summary

    Returns key performance indicators
    """
    try:
        return metrics.get_summary()
    except Exception as e:
        logger.error(f"Metrics summary failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Metrics summary failed: {str(e)}")


@app.get("/stocks/universe", response_model=StockUniverseResponse, tags=["Stocks"])
async def get_stock_universe():
    """
    Get available stock universe

    Returns list of supported stocks organized by index
    """
    try:
        # Get all available indices from stock universe
        available_indices = stock_universe.get_available_indices()

        # Build universe dict with symbols for each index
        universe = {}
        for index_name in available_indices:
            universe[index_name] = stock_universe.get_symbols(index_name)

        total = sum(len(stocks) for stocks in universe.values())

        return StockUniverseResponse(
            total_stocks=total,
            indices=universe,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Universe fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Universe fetch failed: {str(e)}")


# ============================================================================
# Historical Data Endpoints
# ============================================================================

@app.get("/history/stock/{symbol}", response_model=StockHistoryResponse, tags=["Historical"])
async def get_stock_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365, description="Days to look back"),
    include_price: bool = Query(default=True, description="Include price data")
):
    """
    Get historical analysis data for a stock

    Returns historical composite scores, recommendations, and optionally price data
    """
    try:
        symbol = symbol.upper()

        # Get historical data from database
        history = historical_db.get_stock_history(symbol=symbol, days=days)

        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for {symbol}"
            )

        # Get trend statistics
        trend = historical_db.get_score_trend(symbol=symbol, days=days)

        # Build response
        history_points = []
        scores = []

        for record in history:
            point = HistoricalDataPoint(
                timestamp=record['timestamp'],
                composite_score=record['composite_score'],
                recommendation=record['recommendation'],
                confidence=record['confidence'],
                price=record['price'] if include_price else None
            )
            history_points.append(point)
            scores.append(record['composite_score'])

        # Calculate statistics
        statistics = {
            'avg_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'current_score': scores[0] if scores else 0,
            'change': scores[0] - scores[-1] if len(scores) > 1 else 0
        }

        return StockHistoryResponse(
            symbol=symbol,
            history=history_points,
            trend=trend,
            statistics=statistics,
            data_points=len(history_points),
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stock history fetch failed for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@app.get("/history/regime", response_model=RegimeHistoryResponse, tags=["Historical"])
async def get_regime_history(
    days: int = Query(default=30, ge=1, le=365, description="Days to look back")
):
    """
    Get market regime history

    Returns timeline of market regime changes
    """
    try:
        # Get regime history from database
        history = historical_db.get_regime_history(days=days)

        if not history:
            return RegimeHistoryResponse(
                history=[],
                current_regime=None,
                data_points=0,
                timestamp=datetime.now().isoformat()
            )

        # Build response
        history_points = [
            RegimeHistoryPoint(
                timestamp=record['timestamp'],
                regime=record['regime'],
                trend=record['trend'],
                volatility=record['volatility'],
                weights=record['weights']
            )
            for record in history
        ]

        # Get current regime
        current = history[0] if history else None
        current_regime = RegimeHistoryPoint(
            timestamp=current['timestamp'],
            regime=current['regime'],
            trend=current['trend'],
            volatility=current['volatility'],
            weights=current['weights']
        ) if current else None

        return RegimeHistoryResponse(
            history=history_points,
            current_regime=current_regime,
            data_points=len(history_points),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Regime history fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch regime history: {str(e)}")


# ============================================================================
# Analytics Endpoints
# ============================================================================

@app.get("/analytics/system", response_model=SystemAnalyticsResponse, tags=["Analytics"])
async def get_system_analytics():
    """
    Get system performance analytics

    Returns metrics about API performance, agent execution times, and error rates
    """
    try:
        # Get metrics from metrics service
        summary = metrics.get_summary()
        stats = metrics.get_stats()

        # Extract agent performance from timings
        agent_perf = {}
        for timing_key, timing_stats in stats.get('timings', {}).items():
            # Look for agent timing metrics (format: 'agent.{name}.duration')
            if timing_key.startswith('agent.') and timing_key.endswith('.duration'):
                agent_name = timing_key.replace('agent.', '').replace('.duration', '')
                agent_perf[agent_name] = timing_stats['avg_ms']

        # Get values from summary (already calculated)
        total_requests = summary.get('total_requests', 0)
        total_errors = summary.get('total_errors', 0)
        error_rate = summary.get('error_rate', 0.0)
        avg_response_time_ms = summary.get('avg_response_time_ms', 0.0)
        cache_hit_rate = summary.get('cache_hit_rate', 0.0)

        # Get p95 response time from timings
        api_timing = stats.get('timings', {}).get('api.response_time', {})
        p95_response_time_ms = api_timing.get('p95_ms', 0.0)

        return SystemAnalyticsResponse(
            uptime_seconds=summary.get('uptime_seconds', 0),
            total_requests=total_requests,
            total_errors=total_errors,
            error_rate=round(error_rate, 2),
            avg_response_time_ms=round(avg_response_time_ms, 2),
            p95_response_time_ms=round(p95_response_time_ms, 2),
            cache_hit_rate=round(cache_hit_rate, 2),
            agent_performance=agent_perf,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"System analytics fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@app.get("/analytics/sectors", response_model=SectorAnalysisResponse, tags=["Analytics"])
async def get_sector_analysis(
    days: int = Query(default=7, ge=1, le=90, description="Days to analyze")
):
    """
    Get sector-wise performance analysis

    Returns aggregated statistics by sector
    """
    try:
        # Get top performers from database
        top_stocks = historical_db.get_top_performers(days=days, limit=100)

        if not top_stocks:
            return SectorAnalysisResponse(
                sectors=[],
                total_sectors=0,
                timestamp=datetime.now().isoformat()
            )

        # Group by sector
        sector_data = {}
        for stock in top_stocks:
            # Ensure sector is a valid string (handle None, empty string, or 'None' string)
            raw_sector = stock.get('sector')
            if raw_sector is None or raw_sector == '' or str(raw_sector).strip().lower() == 'none':
                sector = 'Unknown'
            else:
                sector = str(raw_sector).strip()

            if sector not in sector_data:
                sector_data[sector] = {
                    'stocks': [],
                    'scores': [],
                    'top_pick': None,
                    'top_score': 0
                }

            sector_data[sector]['stocks'].append(stock['symbol'])
            sector_data[sector]['scores'].append(stock['composite_score'])

            # Track top pick
            if stock['composite_score'] > sector_data[sector]['top_score']:
                sector_data[sector]['top_score'] = stock['composite_score']
                sector_data[sector]['top_pick'] = stock['symbol']

        # Build response
        sectors = []
        for sector, data in sector_data.items():
            avg_score = sum(data['scores']) / len(data['scores'])

            # Determine trend (simplified - based on recent vs older scores)
            if len(data['scores']) >= 2:
                recent_avg = sum(data['scores'][:len(data['scores'])//2]) / (len(data['scores'])//2)
                older_avg = sum(data['scores'][len(data['scores'])//2:]) / (len(data['scores']) - len(data['scores'])//2)
                trend = 'UP' if recent_avg > older_avg else 'DOWN' if recent_avg < older_avg else 'STABLE'
            else:
                trend = 'STABLE'

            sectors.append(SectorStats(
                sector=sector,
                stock_count=len(data['stocks']),
                avg_score=round(avg_score, 2),
                top_pick=data['top_pick'] or 'N/A',
                trend=trend
            ))

        # Sort by avg score
        sectors.sort(key=lambda x: x.avg_score, reverse=True)

        return SectorAnalysisResponse(
            sectors=sectors,
            total_sectors=len(sectors),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Sector analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze sectors: {str(e)}")


@app.get("/analytics/agents", tags=["Analytics"])
async def get_agent_analytics():
    """
    Get agent performance analytics

    Returns historical performance data for all agents
    """
    try:
        # Get metrics for agent performance
        stats = metrics.get_stats()

        agent_stats = {}
        if 'agent_execution_times' in stats:
            for agent, times in stats['agent_execution_times'].items():
                if times:
                    agent_stats[agent] = {
                        'avg_execution_time_ms': round(sum(times) / len(times) * 1000, 2),
                        'total_executions': len(times),
                        'min_time_ms': round(min(times) * 1000, 2),
                        'max_time_ms': round(max(times) * 1000, 2)
                    }

        return {
            'agent_performance': agent_stats,
            'total_agents': len(agent_stats),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Agent analytics fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent analytics: {str(e)}")


# ============================================================================
# Watchlist Endpoints
# ============================================================================

@app.post("/watchlist", tags=["Watchlist"])
async def add_to_watchlist(request: AddToWatchlistRequest):
    """
    Add stock to watchlist

    Returns success status
    """
    try:
        # Track search
        historical_db.track_search(request.symbol, source='watchlist')

        # Add to watchlist
        added = historical_db.add_to_watchlist(
            symbol=request.symbol,
            notes=request.notes
        )

        if added:
            return {
                'success': True,
                'message': f'{request.symbol} added to watchlist',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': f'{request.symbol} already in watchlist',
                'timestamp': datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to add to watchlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add to watchlist: {str(e)}")


@app.get("/watchlist", response_model=WatchlistResponse, tags=["Watchlist"])
async def get_watchlist():
    """
    Get user's watchlist

    Returns all stocks in watchlist with latest analysis
    """
    try:
        # Get watchlist from database
        watchlist = historical_db.get_watchlist()

        # Enrich with latest analysis
        enriched_watchlist = []
        for item in watchlist:
            symbol = item['symbol']

            # Get latest analysis
            latest = historical_db.get_latest_stock_analysis(symbol)

            enriched_item = WatchlistItem(
                symbol=symbol,
                added_at=item['added_at'],
                notes=item['notes'],
                latest_score=latest['composite_score'] if latest else None,
                latest_recommendation=latest['recommendation'] if latest else None
            )
            enriched_watchlist.append(enriched_item)

        return WatchlistResponse(
            watchlist=enriched_watchlist,
            total_items=len(enriched_watchlist),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Watchlist fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch watchlist: {str(e)}")


@app.delete("/watchlist/{symbol}", tags=["Watchlist"])
async def remove_from_watchlist(symbol: str):
    """
    Remove stock from watchlist

    Returns success status
    """
    try:
        symbol = symbol.upper()

        # Remove from watchlist
        removed = historical_db.remove_from_watchlist(symbol)

        if removed:
            return {
                'success': True,
                'message': f'{symbol} removed from watchlist',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f'{symbol} not found in watchlist')

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from watchlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove from watchlist: {str(e)}")


# ============================================================================
# Comparison Endpoint
# ============================================================================

@app.post("/compare", response_model=ComparisonResponse, tags=["Analysis"])
async def compare_stocks(request: CompareRequest):
    """
    Compare multiple stocks side-by-side

    Analyzes 2-4 stocks and returns comparative data
    """
    try:
        results = []

        # Analyze each stock
        for symbol in body.symbols:
            # Try to get from cache first
            cache_key = get_cache_key('analyze', symbol)
            cached = get_from_cache(cache_key)

            if cached:
                analysis = cached
                analysis['cached'] = True
            else:
                # Analyze stock
                result = stock_scorer.score_stock(symbol)

                if result and not result.get('error'):
                    # Generate narrative if requested (but not for comparison by default)
                    narrative_data = None

                    # Build agent scores
                    agent_scores_dict = {}
                    for agent_name, score_data in result.get('agent_scores', {}).items():
                        agent_scores_dict[agent_name] = AgentScore(**score_data)

                    analysis = StockAnalysisResponse(
                        symbol=symbol,
                        composite_score=result['composite_score'],
                        recommendation=result['recommendation'],
                        confidence=result['composite_confidence'],
                        agent_scores=agent_scores_dict,
                        weights=result.get('weights_used', {}),
                        market_regime=result.get('market_regime'),
                        narrative=narrative_data,
                        timestamp=datetime.now().isoformat(),
                        cached=False
                    )

                    # Cache result
                    api_cache.set(cache_key, analysis.dict(), ttl=API_CACHE_DURATION)

                    # Track search
                    historical_db.track_search(symbol, source='comparison')

                    # Save to historical database
                    try:
                        historical_db.save_stock_analysis(
                            symbol=symbol,
                            composite_score=result['composite_score'],
                            recommendation=result['recommendation'],
                            confidence=result['composite_confidence'],
                            agent_scores=result.get('agent_scores', {}),
                            weights=result.get('weights_used', {}),
                            market_regime=result.get('market_regime')
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save analysis to database: {e}")
                else:
                    logger.warning(f"Analysis failed for {symbol}: {result.get('error', 'Unknown error')}")
                    continue

            results.append(analysis)

        if not results:
            raise HTTPException(status_code=500, detail="Failed to analyze any stocks")

        return ComparisonResponse(
            comparisons=results,
            total_stocks=len(results),
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stock comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


# ============================================================================
# Export Endpoint
# ============================================================================

@app.get("/export/analysis/{symbol}", tags=["Export"])
async def export_analysis(
    symbol: str,
    format: str = Query(default='json', regex='^(json|csv)$', description="Export format")
):
    """
    Export stock analysis data

    Returns analysis data in JSON or CSV format
    """
    try:
        symbol = symbol.upper()

        # Get historical data
        history = historical_db.get_stock_history(symbol=symbol, days=365)

        if not history:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        if format == 'json':
            return {
                'symbol': symbol,
                'history': history,
                'exported_at': datetime.now().isoformat()
            }
        elif format == 'csv':
            # Convert to CSV format
            import io
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'timestamp', 'symbol', 'composite_score', 'recommendation',
                'confidence', 'price', 'sector'
            ])

            # Write data
            for record in history:
                writer.writerow([
                    record['timestamp'],
                    record['symbol'],
                    record['composite_score'],
                    record['recommendation'],
                    record['confidence'],
                    record.get('price', ''),
                    record.get('sector', '')
                ])

            from fastapi.responses import StreamingResponse
            output.seek(0)

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={symbol}_analysis.csv"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ============================================================================
# Data Collector Status Endpoint
# ============================================================================

@app.get("/collector/status", tags=["System"])
async def get_collector_status():
    """
    Get data collector status

    Returns information about the background data collection service
    """
    try:
        collector = get_collector()
        status = collector.get_status()

        # Add database stats
        db_stats = historical_db.get_database_stats()
        status['database'] = db_stats

        return status

    except Exception as e:
        logger.error(f"Collector status fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get collector status: {str(e)}")


@app.post("/collector/collect", tags=["System"])
async def trigger_collection():
    """
    Manually trigger data collection (admin only)

    Starts immediate data collection
    """
    try:
        collector = get_collector()
        result = collector.collect_now()

        return {
            'success': True,
            'message': 'Data collection triggered',
            'result': result,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Manual collection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger collection: {str(e)}")


@app.get("/cache/stats", tags=["System"])
async def get_cache_stats():
    """
    Get cache statistics

    Returns statistics for all active caches including:
    - Hit/miss rates
    - Cache sizes
    - Utilization
    """
    try:
        stats = cache_manager.stats()

        return {
            'caches': stats,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Cache stats fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@app.post("/cache/clear", tags=["System"])
async def clear_caches():
    """
    Clear all caches (admin only)

    Removes all cached data to force fresh fetches
    """
    try:
        cache_manager.clear_all()

        return {
            'success': True,
            'message': 'All caches cleared',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Cache clear failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear caches: {str(e)}")


@app.post("/cache/cleanup", tags=["System"])
async def cleanup_expired_caches():
    """
    Cleanup expired cache entries

    Removes expired entries from all caches
    """
    try:
        results = cache_manager.cleanup_all_expired()

        return {
            'success': True,
            'message': 'Expired cache entries removed',
            'removed': results,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cleanup caches: {str(e)}")


# ============================================================================
# Backtest Endpoints
# ============================================================================

from core.backtester import Backtester
from data.backtest_db import BacktestDatabase
from core.backtest_analyzer import BacktestAnalyzer
from core.backtest_config import BacktestConfig, create_default_config
from core.equity_curve import EquityCurveCalculator

# Initialize backtest services
backtest_db = BacktestDatabase()
equity_calculator = EquityCurveCalculator()


class BacktestRequest(BaseModel):
    """Request model for running a backtest"""
    symbols: Optional[List[str]] = Field(None, description="List of stock symbols (None = NIFTY 50)")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    frequency: str = Field(default="monthly", description="Rebalance frequency: daily, weekly, monthly, quarterly")
    name: Optional[str] = Field(None, description="Human-readable name for the backtest run")
    include_narrative: bool = Field(default=False, description="Include narratives (slower)")


@app.post("/backtest/run", tags=["Backtest"])
@limiter.limit("5/hour")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Run a backtest on specified symbols and date range

    Saves configuration for easy re-running. Returns run_id immediately.
    """
    try:
        # Parse dates
        start_date = datetime.fromisoformat(request.start_date)
        end_date = datetime.fromisoformat(request.end_date)

        # Validate date range
        if end_date <= start_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")

        # Get symbols (default to NIFTY 50 if not provided)
        symbols = request.symbols
        if symbols is None:
            symbols = stock_universe.get_symbols('NIFTY_50')
            logger.info(f"Using default NIFTY 50 universe: {len(symbols)} stocks")

        # Generate name if not provided
        name = request.name or f"Backtest {start_date.date()} to {end_date.date()}"

        # Create configuration for saving
        config = BacktestConfig(
            name=name,
            symbols=request.symbols,  # Store original (None if NIFTY 50)
            start_date=start_date,
            end_date=end_date,
            frequency=request.frequency,
            benchmark='^NSEI'
        )

        # Create backtester
        backtester = Backtester(scorer=stock_scorer, data_provider=data_provider)

        # Run backtest (this may take a while)
        logger.info(f"Starting backtest: {name}")
        start_time = time.time()

        results = backtester.run_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency=request.frequency,
            parallel=True
        )

        if not results:
            raise HTTPException(status_code=500, detail="No backtest results generated")

        duration_seconds = time.time() - start_time

        # Generate summary
        summary = backtester.generate_summary(results)

        # Analyze results
        analyzer = BacktestAnalyzer()
        analysis = analyzer.analyze_comprehensive(results)

        # Convert analysis to JSON-serializable format
        serializable_analysis = {
            'agent_performance': [
                {
                    'agent_name': ap.agent_name,
                    'correlation_with_returns': float(ap.correlation_with_returns),
                    'avg_score': float(ap.avg_score),
                    'current_weight': float(ap.current_weight),
                    'optimal_weight': float(ap.optimal_weight),
                    'weight_change': float(ap.weight_change),
                    'predictive_power': ap.predictive_power
                }
                for ap in analysis.get('agent_performance', [])
            ],
            'optimal_weights': {
                'weights': analysis['optimal_weights'].weights,
                'expected_improvement': float(analysis['optimal_weights'].expected_improvement),
                'current_sharpe': float(analysis['optimal_weights'].current_sharpe),
                'optimal_sharpe': float(analysis['optimal_weights'].optimal_sharpe),
                'methodology': analysis['optimal_weights'].methodology
            } if 'optimal_weights' in analysis else {},
            'sector_performance': analysis.get('sector_performance', {}),
            'time_series_performance': analysis.get('time_series_performance', {}),
            'recommendations': analysis.get('recommendations', [])
        }

        # Save to database with configuration
        run_id = backtest_db.save_backtest_run(
            name=name,
            results=results,
            summary=summary,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,  # Use actual symbols (not None)
            frequency=request.frequency,
            metadata={
                'config': config.to_dict(),  # Save configuration for re-running
                'analysis': serializable_analysis,
                'requested_at': datetime.now().isoformat(),
                'duration_seconds': round(duration_seconds, 2)
            }
        )

        logger.info(f"Backtest complete: {run_id} with {len(results)} signals in {duration_seconds:.2f}s")

        return {
            'success': True,
            'run_id': run_id,
            'name': name,
            'total_signals': len(results),
            'summary': {
                'hit_rate_3m': summary.hit_rate_3m,
                'avg_alpha_3m': summary.avg_alpha_3m,
                'sharpe_ratio_3m': summary.sharpe_ratio_3m,
                'total_return': summary.avg_return_3m,
                'annualized_return': summary.avg_return_3m * 4  # Approximate annualized
            },
            'config': config.to_dict(),
            'duration_seconds': round(duration_seconds, 2),
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@app.post("/backtest/rerun/{run_id}", tags=["Backtest"])
@limiter.limit("5/hour")
async def rerun_backtest(run_id: str, update_dates: bool = Query(default=True), http_request: Request = None):
    """
    Re-run a previous backtest with saved configuration

    If update_dates=True, updates end_date to today while keeping same duration

    Example:
        - Original: 2020-01-01 to 2025-01-01 (5 years)
        - Re-run: 2021-02-03 to 2026-02-03 (5 years, updated to today)
    """
    try:
        # Get original run
        run_data = backtest_db.get_backtest_run(run_id)
        if not run_data:
            raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

        # Load configuration
        config_dict = run_data.get('metadata', {}).get('config')
        if not config_dict:
            raise HTTPException(status_code=400, detail="Run has no saved configuration")

        config = BacktestConfig.from_dict(config_dict)

        # Update dates if requested
        if update_dates:
            config = config.update_dates_to_present()
            logger.info(f"Updated dates: {config.start_date.date()} to {config.end_date.date()}")

        # Get symbols (use NIFTY 50 if original was None)
        symbols = config.symbols
        if symbols is None:
            symbols = stock_universe.get_symbols('NIFTY_50')

        # Create backtester and run
        backtester = Backtester(scorer=stock_scorer, data_provider=data_provider)

        logger.info(f"Re-running backtest: {config.name}")
        start_time = time.time()

        results = backtester.run_backtest(
            symbols=symbols,
            start_date=config.start_date,
            end_date=config.end_date,
            rebalance_frequency=config.frequency,
            parallel=True
        )

        if not results:
            raise HTTPException(status_code=500, detail="No backtest results generated")

        duration_seconds = time.time() - start_time

        # Generate summary and analysis
        summary = backtester.generate_summary(results)
        analyzer = BacktestAnalyzer()
        analysis = analyzer.analyze_comprehensive(results)

        # Convert analysis to serializable format (same as original)
        serializable_analysis = {
            'agent_performance': [
                {
                    'agent_name': ap.agent_name,
                    'correlation_with_returns': float(ap.correlation_with_returns),
                    'avg_score': float(ap.avg_score),
                    'current_weight': float(ap.current_weight),
                    'optimal_weight': float(ap.optimal_weight),
                    'weight_change': float(ap.weight_change),
                    'predictive_power': ap.predictive_power
                }
                for ap in analysis.get('agent_performance', [])
            ],
            'optimal_weights': {
                'weights': analysis['optimal_weights'].weights,
                'expected_improvement': float(analysis['optimal_weights'].expected_improvement),
                'current_sharpe': float(analysis['optimal_weights'].current_sharpe),
                'optimal_sharpe': float(analysis['optimal_weights'].optimal_sharpe),
                'methodology': analysis['optimal_weights'].methodology
            } if 'optimal_weights' in analysis else {},
            'sector_performance': analysis.get('sector_performance', {}),
            'time_series_performance': analysis.get('time_series_performance', {}),
            'recommendations': analysis.get('recommendations', [])
        }

        # Save new run
        new_run_id = backtest_db.save_backtest_run(
            name=config.name,
            results=results,
            summary=summary,
            start_date=config.start_date,
            end_date=config.end_date,
            symbols=symbols,
            frequency=config.frequency,
            metadata={
                'config': config.to_dict(),
                'analysis': serializable_analysis,
                'requested_at': datetime.now().isoformat(),
                'duration_seconds': round(duration_seconds, 2),
                'rerun_from': run_id
            }
        )

        logger.info(f"Backtest re-run complete: {new_run_id}")

        return {
            'success': True,
            'run_id': new_run_id,
            'original_run_id': run_id,
            'name': config.name,
            'total_signals': len(results),
            'summary': {
                'hit_rate_3m': summary.hit_rate_3m,
                'avg_alpha_3m': summary.avg_alpha_3m,
                'sharpe_ratio_3m': summary.sharpe_ratio_3m,
                'total_return': summary.avg_return_3m,
                'annualized_return': summary.avg_return_3m * 4
            },
            'config': config.to_dict(),
            'duration_seconds': round(duration_seconds, 2),
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest rerun failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest rerun failed: {str(e)}")


@app.get("/backtest/runs", tags=["Backtest"])
async def list_backtest_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default='created_at', description="Sort by: created_at, hit_rate_3m, avg_alpha_3m, sharpe_ratio_3m"),
    order: str = Query(default='desc', description="Order: asc or desc")
):
    """
    List all historical backtest runs with pagination and sorting

    Returns summary information for each run (without individual signals)
    """
    try:
        runs = backtest_db.list_backtest_runs(limit=limit)

        # Sort runs based on parameters
        if sort_by != 'created_at':
            # Sort by summary metrics
            def get_sort_key(run):
                summary = run.get('summary', {})
                if sort_by == 'hit_rate_3m':
                    return summary.get('hit_rate_3m', 0)
                elif sort_by == 'avg_alpha_3m':
                    return summary.get('avg_alpha_3m', 0)
                elif sort_by == 'sharpe_ratio_3m':
                    return summary.get('sharpe_ratio_3m', 0)
                return 0

            runs.sort(key=get_sort_key, reverse=(order == 'desc'))

        # Apply pagination
        total = len(runs)
        runs = runs[offset:offset + limit]

        return {
            'runs': runs,
            'total': total,
            'limit': limit,
            'offset': offset,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to list backtest runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list backtest runs: {str(e)}")


@app.get("/backtest/results/{run_id}", tags=["Backtest"])
async def get_backtest_results(
    run_id: str,
    include_equity_curve: bool = Query(default=True, description="Include equity curve data"),
    include_signals: bool = Query(default=True, description="Include individual signals")
):
    """
    Get detailed results for a specific backtest run

    Includes:
    - Run metadata and configuration
    - Summary metrics
    - Equity curve (optional, default True)
    - All individual signals (optional, default True)
    - Analysis results
    """
    try:
        run_data = backtest_db.get_backtest_run(run_id)

        if not run_data:
            raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

        # Calculate equity curve if requested
        equity_curve = None
        if include_equity_curve and run_data.get('signals'):
            try:
                equity_curve = equity_calculator.calculate_equity_curve(
                    signals=run_data['signals'],
                    frequency=run_data.get('frequency', 'monthly')
                )
                logger.info(f"Calculated equity curve for {run_id}: {len(equity_curve['dates'])} points")
            except Exception as e:
                logger.warning(f"Failed to calculate equity curve: {e}")

        # Remove signals if not requested (reduce response size)
        if not include_signals:
            run_data.pop('signals', None)

        # Build response
        response = {
            'run_id': run_data['run_id'],
            'name': run_data['name'],
            'start_date': run_data['start_date'],
            'end_date': run_data['end_date'],
            'symbols': run_data['symbols'],
            'frequency': run_data['frequency'],
            'created_at': run_data['created_at'],
            'total_signals': run_data['total_signals'],
            'summary': run_data['summary'],
            'config': run_data.get('metadata', {}).get('config'),
            'equity_curve': equity_curve,
            'timestamp': datetime.now().isoformat()
        }

        # Add signals if requested
        if include_signals:
            response['signals'] = run_data['signals']

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get backtest results: {str(e)}")


@app.get("/backtest/comparison", tags=["Backtest"])
async def compare_backtests(run_ids: str = Query(..., description="Comma-separated run IDs")):
    """
    Compare multiple backtest runs side-by-side

    Returns comparative data for 2-4 backtest runs including:
    - Summary metrics for each run
    - Equity curves
    - Best performer identification
    """
    try:
        # Parse run IDs
        run_id_list = [rid.strip() for rid in run_ids.split(',')]

        if len(run_id_list) < 2:
            raise HTTPException(status_code=400, detail="At least 2 run IDs required for comparison")

        if len(run_id_list) > 4:
            raise HTTPException(status_code=400, detail="Maximum 4 runs can be compared at once")

        # Fetch all runs
        runs = []
        for run_id in run_id_list:
            run_data = backtest_db.get_backtest_run(run_id)
            if not run_data:
                logger.warning(f"Run {run_id} not found, skipping")
                continue

            # Calculate equity curve
            equity_curve = None
            if run_data.get('signals'):
                try:
                    equity_curve = equity_calculator.calculate_equity_curve(
                        signals=run_data['signals'],
                        frequency=run_data.get('frequency', 'monthly')
                    )
                except Exception as e:
                    logger.warning(f"Failed to calculate equity curve for {run_id}: {e}")

            runs.append({
                'run_id': run_data['run_id'],
                'name': run_data['name'],
                'start_date': run_data['start_date'],
                'end_date': run_data['end_date'],
                'frequency': run_data['frequency'],
                'total_signals': run_data['total_signals'],
                'summary': run_data['summary'],
                'equity_curve': equity_curve
            })

        if len(runs) < 2:
            raise HTTPException(status_code=404, detail="Not enough valid runs found for comparison")

        # Identify best performers
        best_sharpe = max(runs, key=lambda r: r['summary'].get('sharpe_ratio_3m', 0))
        best_return = max(runs, key=lambda r: r['summary'].get('avg_return_3m', 0))
        best_alpha = max(runs, key=lambda r: r['summary'].get('avg_alpha_3m', 0))
        lowest_drawdown = max(runs, key=lambda r: r['summary'].get('max_drawdown', -100))  # Max because drawdown is negative

        comparison = {
            'best_sharpe': {
                'run_id': best_sharpe['run_id'],
                'name': best_sharpe['name'],
                'value': best_sharpe['summary'].get('sharpe_ratio_3m', 0)
            },
            'best_return': {
                'run_id': best_return['run_id'],
                'name': best_return['name'],
                'value': best_return['summary'].get('avg_return_3m', 0)
            },
            'best_alpha': {
                'run_id': best_alpha['run_id'],
                'name': best_alpha['name'],
                'value': best_alpha['summary'].get('avg_alpha_3m', 0)
            },
            'lowest_drawdown': {
                'run_id': lowest_drawdown['run_id'],
                'name': lowest_drawdown['name'],
                'value': lowest_drawdown['summary'].get('max_drawdown', 0)
            }
        }

        return {
            'runs': runs,
            'total_compared': len(runs),
            'comparison': comparison,
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.get("/backtest/analysis/{run_id}", tags=["Backtest"])
async def get_backtest_analysis(run_id: str):
    """
    Get deep analysis for a specific backtest run

    Includes:
    - Agent performance correlations
    - Optimal weight recommendations
    - Sector breakdown
    - System improvement recommendations
    """
    try:
        run_data = backtest_db.get_backtest_run(run_id)

        if not run_data:
            raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

        # Get analysis from metadata if available
        analysis = run_data.get('metadata', {}).get('analysis')

        if not analysis:
            # Regenerate analysis if not found
            logger.info(f"Regenerating analysis for run {run_id}")

            # Reconstruct BacktestResult objects from signals
            from core.backtester import BacktestResult
            results = []
            for signal in run_data['signals']:
                results.append(BacktestResult(
                    symbol=signal['symbol'],
                    date=datetime.fromisoformat(signal['date']),
                    recommendation=signal['recommendation'],
                    composite_score=signal['composite_score'],
                    confidence=signal['confidence'],
                    entry_price=signal['entry_price'],
                    exit_price=signal['exit_price'],
                    forward_return_1m=signal['forward_return_1m'],
                    forward_return_3m=signal['forward_return_3m'],
                    forward_return_6m=signal['forward_return_6m'],
                    benchmark_return_1m=signal['benchmark_return_1m'],
                    benchmark_return_3m=signal['benchmark_return_3m'],
                    benchmark_return_6m=signal['benchmark_return_6m'],
                    alpha_1m=signal['alpha_1m'],
                    alpha_3m=signal['alpha_3m'],
                    alpha_6m=signal['alpha_6m'],
                    agent_scores=signal['agent_scores'],
                    market_regime=signal['market_regime']
                ))

            analyzer = BacktestAnalyzer()
            analysis = analyzer.analyze_comprehensive(results)

        # Convert agent performance to serializable format
        agent_performance_list = []
        if 'agent_performance' in analysis:
            for ap in analysis['agent_performance']:
                agent_performance_list.append({
                    'agent_name': ap.agent_name,
                    'correlation_with_returns': ap.correlation_with_returns,
                    'avg_score': ap.avg_score,
                    'current_weight': ap.current_weight,
                    'optimal_weight': ap.optimal_weight,
                    'weight_change': ap.weight_change,
                    'predictive_power': ap.predictive_power
                })

        # Convert optimal weights to serializable format
        optimal_weights_dict = {}
        if 'optimal_weights' in analysis:
            ow = analysis['optimal_weights']
            optimal_weights_dict = {
                'weights': ow.weights,
                'expected_improvement': ow.expected_improvement,
                'current_sharpe': ow.current_sharpe,
                'optimal_sharpe': ow.optimal_sharpe,
                'methodology': ow.methodology
            }

        return {
            'run_id': run_id,
            'agent_performance': agent_performance_list,
            'optimal_weights': optimal_weights_dict,
            'sector_performance': analysis.get('sector_performance', {}),
            'time_series_performance': analysis.get('time_series_performance', {}),
            'recommendations': analysis.get('recommendations', []),
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get backtest analysis: {str(e)}")


@app.delete("/backtest/results/{run_id}", tags=["Backtest"])
async def delete_backtest_run(run_id: str):
    """
    Delete a backtest run and all its data

    This action cannot be undone.
    """
    try:
        success = backtest_db.delete_backtest_run(run_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

        return {
            'success': True,
            'message': f'Backtest run {run_id} deleted',
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backtest run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete backtest run: {str(e)}")


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("="*60)
    logger.info("AI Hedge Fund FastAPI Backend Starting...")
    logger.info("="*60)
    logger.info(f"Data Provider: Hybrid (NSEpy + Yahoo Finance)")
    logger.info(f"Stock Scorer: 5 agents with adaptive weights")
    logger.info(f"Narrative Engine: {narrative_engine.llm_provider if hasattr(narrative_engine, 'llm_provider') else 'unknown'}")
    logger.info(f"API Cache: {API_CACHE_DURATION}s")
    logger.info(f"Historical Database: {historical_db.db_path}")

    # Start data collector
    try:
        start_collector()
        collector_status = data_collector.get_status()
        logger.info(f"Data Collector: {'Running' if collector_status['is_running'] else 'Disabled'}")
        if collector_status['is_running']:
            logger.info(f"Collection Interval: {collector_status['collection_interval_hours']}h")
    except Exception as e:
        logger.warning(f"Data collector failed to start: {e}")

    logger.info("="*60)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("FastAPI backend shutting down...")

    # Stop data collector
    try:
        stop_collector()
        logger.info("Data collector stopped")
    except Exception as e:
        logger.warning(f"Error stopping data collector: {e}")

    # Cleanup tasks if needed


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or default to 8000
    port = int(os.getenv('API_PORT', 8000))

    logger.info(f"Starting FastAPI server on port {port}")

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
