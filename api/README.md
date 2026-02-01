# FastAPI Backend - AI Hedge Fund System

REST API backend for the AI Hedge Fund stock analysis system.

## Quick Start

```bash
# Start the API server
make run-api

# Or directly with uvicorn
uvicorn api.main:app --reload --port 8000

# Test all endpoints
make test-api
```

The API will be available at: `http://localhost:8000`

## API Documentation

Once the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### 1. Root Endpoint
```http
GET /
```
Returns service information and available endpoints.

**Response:**
```json
{
  "service": "AI Hedge Fund - Indian Stock Market",
  "version": "1.0.0",
  "status": "operational",
  "docs": "/docs",
  "endpoints": {...}
}
```

---

### 2. Analyze Single Stock
```http
POST /analyze
```

Analyze a single stock with comprehensive AI agent scoring.

**Request Body:**
```json
{
  "symbol": "TCS",
  "include_narrative": true
}
```

**Response:**
```json
{
  "symbol": "TCS",
  "composite_score": 78.5,
  "recommendation": "BUY",
  "confidence": 0.82,
  "agent_scores": {
    "fundamentals": {
      "score": 85.0,
      "confidence": 0.9,
      "reasoning": "Excellent profitability | Fair valuation | Strong growth",
      "metrics": {...},
      "breakdown": {...}
    },
    "momentum": {...},
    "quality": {...},
    "sentiment": {...},
    "institutional_flow": {...}
  },
  "weights": {
    "fundamentals": 0.36,
    "momentum": 0.27,
    "quality": 0.18,
    "sentiment": 0.09,
    "institutional_flow": 0.10
  },
  "market_regime": {
    "regime": "BULL_NORMAL",
    "trend": "BULL",
    "volatility": "NORMAL",
    "weights": {...},
    "metrics": {...}
  },
  "narrative": {
    "investment_thesis": "TCS demonstrates strong fundamentals...",
    "key_strengths": [...],
    "key_risks": [...],
    "summary": "...",
    "provider": "gemini"
  },
  "timestamp": "2025-01-31T10:30:00",
  "cached": false
}
```

**Example:**
```bash
# Using curl
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TCS", "include_narrative": true}'

# Using make
make analyze SYMBOL=TCS
```

---

### 3. Batch Analysis
```http
POST /analyze/batch
```

Analyze multiple stocks in one request (up to 50 stocks).

**Request Body:**
```json
{
  "symbols": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
  "include_narrative": false,
  "sort_by": "score"
}
```

**Parameters:**
- `symbols` (required): List of stock symbols (1-50)
- `include_narrative` (optional): Include LLM narratives (default: false)
- `sort_by` (optional): Sort by `score`, `confidence`, or `symbol` (default: `score`)

**Response:**
```json
{
  "total_analyzed": 5,
  "successful": 5,
  "failed": 0,
  "results": [
    {
      "symbol": "TCS",
      "composite_score": 78.5,
      "recommendation": "BUY",
      ...
    },
    ...
  ],
  "timestamp": "2025-01-31T10:30:00",
  "duration_seconds": 12.5
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/analyze/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["TCS", "INFY", "WIPRO"],
    "include_narrative": false,
    "sort_by": "score"
  }'
```

---

### 4. Top Picks from NIFTY 50
```http
GET /portfolio/top-picks?limit=10&include_narrative=false
```

Get top stock picks from NIFTY 50 index.

**Query Parameters:**
- `limit` (optional): Number of top picks (1-50, default: 10)
- `include_narrative` (optional): Include narratives (default: false)

**Response:**
```json
{
  "market_regime": {
    "regime": "BULL_NORMAL",
    "trend": "BULL",
    "volatility": "NORMAL",
    ...
  },
  "top_picks": [
    {
      "symbol": "TCS",
      "composite_score": 82.3,
      "recommendation": "STRONG BUY",
      ...
    },
    ...
  ],
  "total_analyzed": 50,
  "timestamp": "2025-01-31T10:30:00",
  "duration_seconds": 45.2
}
```

**Example:**
```bash
# Get top 5 picks
curl "http://localhost:8000/portfolio/top-picks?limit=5"

# Using make
make top-picks
```

---

### 5. Market Regime
```http
GET /market/regime
```

Get current market regime based on NIFTY 50 analysis.

**Response:**
```json
{
  "regime": "BULL_NORMAL",
  "trend": "BULL",
  "volatility": "NORMAL",
  "weights": {
    "fundamentals": 0.36,
    "momentum": 0.27,
    "quality": 0.18,
    "sentiment": 0.09,
    "institutional_flow": 0.10
  },
  "metrics": {
    "current_price": 22150.5,
    "sma_50": 21800.0,
    "sma_200": 21200.0,
    "price_vs_sma50_pct": 1.6,
    "sma50_vs_sma200_pct": 2.8,
    "volatility_pct": 18.5,
    "volatility_trend": "decreasing"
  },
  "timestamp": "2025-01-31T10:30:00",
  "cached": false
}
```

**Example:**
```bash
curl "http://localhost:8000/market/regime"

# Using make
make regime
```

---

### 6. Health Check
```http
GET /health
```

Check API and component health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-31T10:30:00",
  "components": {
    "data_provider": {
      "status": "healthy",
      "primary": "NSEProvider",
      "fallback": "YahooProvider",
      "test_symbol": "TCS",
      "data_available": true
    },
    "stock_scorer": {
      "status": "healthy",
      "agents": 5,
      "adaptive_weights": true
    },
    "narrative_engine": {
      "status": "healthy",
      "provider": "gemini",
      "model": "gemini-1.5-flash"
    },
    "market_regime": {
      "status": "healthy",
      "cached": true,
      "cache_valid": true
    }
  },
  "version": "1.0.0"
}
```

**Example:**
```bash
curl "http://localhost:8000/health"

# Using make
make health
```

---

### 7. Stock Universe
```http
GET /stocks/universe
```

Get list of available stocks organized by index.

**Response:**
```json
{
  "total_stocks": 50,
  "indices": {
    "NIFTY_50": [
      "TCS", "INFY", "RELIANCE", "HDFCBANK", ...
    ]
  },
  "timestamp": "2025-01-31T10:30:00"
}
```

**Example:**
```bash
curl "http://localhost:8000/stocks/universe"
```

---

## Recommendations

The API returns one of the following recommendations:

| Recommendation | Score Range | Description |
|----------------|-------------|-------------|
| STRONG BUY | 80-100 | Exceptional opportunity |
| BUY | 60-79 | Strong buy signal |
| WEAK BUY | 52-59 | Moderate buy signal |
| HOLD | 48-51 | Neutral position |
| WEAK SELL | 42-47 | Moderate sell signal |
| SELL | 0-41 | Strong sell signal |

## Caching

The API implements multi-layer caching:

- **API Response Cache**: 15 minutes
- **Market Regime Cache**: 6 hours
- **Data Provider Cache**: 20 minutes

Cached responses include a `cached: true` field.

## Error Handling

All errors follow this format:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2025-01-31T10:30:00"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid input)
- `422`: Validation Error
- `500`: Internal Server Error

## Rate Limiting

Currently no rate limiting is implemented. For production:
- Add rate limiting middleware
- Implement API key authentication
- Set appropriate CORS origins

## Performance Tips

1. **Use batch endpoint** for multiple stocks instead of multiple single requests
2. **Disable narratives** when not needed (saves LLM API calls)
3. **Cache responses** on the client side for 15 minutes
4. **Use top-picks endpoint** instead of analyzing all NIFTY 50 stocks manually

## Production Deployment

```bash
# Production mode with multiple workers
make run-prod

# Or with uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Docker
make docker-build
make docker-run
```

## Environment Variables

Configure in `.env`:

```bash
# API Settings
API_PORT=8000
API_WORKERS=4
API_CACHE_DURATION=900  # 15 minutes

# LLM Provider (for narratives)
GEMINI_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here

# Data Providers
NSE_RATE_LIMIT_DELAY=0.5
YAHOO_RATE_LIMIT_DELAY=0.1
DATA_CACHE_DURATION=1200  # 20 minutes

# Market Regime
REGIME_CACHE_DURATION=21600  # 6 hours
```

## Testing

```bash
# Test all endpoints
make test-api

# Run unit tests
make test-unit

# Run integration tests
make test-integration
```

## Monitoring

Logs are written to:
- Console (stdout)
- `logs/app.log` (if configured)

Monitor with:
```bash
make logs
```

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review logs for error details
3. Test with the health endpoint
4. Verify environment variables are set correctly
