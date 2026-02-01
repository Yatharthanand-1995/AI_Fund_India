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

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import pandas as pd

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging and monitoring middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold_ms=2000)
app.add_middleware(ErrorTrackingMiddleware)

# Initialize components
data_provider = HybridDataProvider()
market_regime_service = MarketRegimeService()
stock_scorer = StockScorer(
    data_provider=data_provider,
    use_adaptive_weights=True
)
narrative_engine = InvestmentNarrativeEngine()
stock_universe = get_universe()

# Initialize historical database
db_path = os.getenv('DATABASE_PATH', 'data/analysis_history.db')
historical_db = HistoricalDatabase(db_path=db_path)

# Initialize data collector
data_collector = init_collector(
    db=historical_db,
    stock_scorer=stock_scorer,
    market_regime_service=market_regime_service
)

# Simple in-memory cache for API responses (15 minutes)
API_CACHE_DURATION = 900  # 15 minutes
api_cache: Dict[str, Dict[str, Any]] = {}

logger.info("FastAPI backend initialized successfully")


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request model for single stock analysis"""
    symbol: str = Field(..., description="Stock symbol (e.g., TCS, RELIANCE)")
    include_narrative: bool = Field(default=True, description="Include LLM-generated narrative")

    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format"""
        if not v or len(v) < 1:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

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
        if not v or len(v) < 1:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()


class CompareRequest(BaseModel):
    """Request model for stock comparison"""
    symbols: List[str] = Field(..., min_items=2, max_items=4)
    include_history: bool = Field(default=False)

    @validator('symbols')
    def validate_symbols(cls, v):
        if len(v) < 2:
            raise ValueError("At least 2 symbols required for comparison")
        if len(v) > 4:
            raise ValueError("Maximum 4 symbols allowed")
        return [s.strip().upper() for s in v]


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
    """Get from cache if valid"""
    if cache_key in api_cache:
        entry = api_cache[cache_key]
        age = time.time() - entry['timestamp']
        if age < API_CACHE_DURATION:
            logger.info(f"Cache hit: {cache_key} (age: {age:.1f}s)")
            return entry['data']
        else:
            # Expired
            del api_cache[cache_key]
    return None


def save_to_cache(cache_key: str, data: Dict):
    """Save to cache"""
    api_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }
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
async def analyze_stock(request: AnalyzeRequest):
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
        symbol = request.symbol
        logger.info(f"Analyzing stock: {symbol}")

        # Check cache
        cache_key = get_cache_key("analyze", f"{symbol}:{request.include_narrative}")
        cached = get_from_cache(cache_key)
        if cached:
            return StockAnalysisResponse(**{**cached, 'cached': True})

        # Fetch NIFTY data for market context
        nifty_cached = data_provider.get_comprehensive_data('^NSEI')
        nifty_data = nifty_cached.get('historical_data')

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
        if request.include_narrative:
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
async def analyze_batch(request: BatchAnalyzeRequest):
    """
    Analyze multiple stocks in batch

    Supports up to 50 stocks per request.
    Results are sorted by score (descending) by default.
    """
    try:
        logger.info(f"Batch analysis: {len(request.symbols)} stocks")

        start_time = time.time()

        # Fetch NIFTY data once
        nifty_cached = data_provider.get_comprehensive_data('^NSEI')
        nifty_data = nifty_cached.get('historical_data')

        # Get market regime once
        regime = stock_scorer.get_market_regime()

        # Score all stocks
        batch_results = stock_scorer.score_stocks_batch(symbols=request.symbols)

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
                if request.include_narrative:
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
        if request.sort_by == 'score':
            formatted_results.sort(key=lambda x: x.composite_score, reverse=True)
        elif request.sort_by == 'confidence':
            formatted_results.sort(key=lambda x: x.confidence, reverse=True)
        elif request.sort_by == 'symbol':
            formatted_results.sort(key=lambda x: x.symbol)

        duration = time.time() - start_time

        logger.info(f"Batch analysis completed: {successful} successful, {failed} failed in {duration:.2f}s")

        return BatchAnalysisResponse(
            total_analyzed=len(request.symbols),
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
        nifty_cached = data_provider.get_comprehensive_data('^NSEI')
        nifty_data = nifty_cached.get('historical_data')

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
        nifty_cached = data_provider.get_comprehensive_data('^NSEI')
        nifty_data = nifty_cached.get('historical_data')

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
        stats = metrics.get_stats()
        summary = metrics.get_summary()

        # Extract agent performance
        agent_perf = {}
        if 'agent_execution_times' in stats:
            for agent, times in stats['agent_execution_times'].items():
                if times:
                    agent_perf[agent] = sum(times) / len(times)

        # Calculate error rate
        total_requests = stats.get('request_count', 0)
        total_errors = stats.get('error_count', 0)
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

        # Get response times
        response_times = stats.get('response_times', [])
        avg_response = sum(response_times) / len(response_times) if response_times else 0

        # Calculate p95
        if response_times:
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_response = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
        else:
            p95_response = 0

        # Cache hit rate
        cache_hits = stats.get('cache_hits', 0)
        cache_misses = stats.get('cache_misses', 0)
        cache_total = cache_hits + cache_misses
        cache_hit_rate = (cache_hits / cache_total * 100) if cache_total > 0 else 0

        return SystemAnalyticsResponse(
            uptime_seconds=summary.get('uptime_seconds', 0),
            total_requests=total_requests,
            total_errors=total_errors,
            error_rate=round(error_rate, 2),
            avg_response_time_ms=round(avg_response * 1000, 2),
            p95_response_time_ms=round(p95_response * 1000, 2),
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
            sector = stock.get('sector', 'Unknown')
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
        for symbol in request.symbols:
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
                    api_cache[cache_key] = {
                        'data': analysis.dict(),
                        'timestamp': time.time()
                    }

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
    logger.info(f"Historical Database: {db_path}")

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
