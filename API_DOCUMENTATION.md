# API Documentation

**Version**: 2.0
**Base URL**: `http://localhost:8000`
**Interactive Docs**: http://localhost:8000/docs

---

## Authentication

Currently, no authentication is required. All endpoints are publicly accessible.

---

## Core Endpoints

### 1. Analyze Stock

Analyze a single stock with AI agents.

**Endpoint**: `POST /analyze`

**Request Body**:
```json
{
  "symbol": "TCS",
  "include_narrative": true
}
```

**Response** (200 OK):
```json
{
  "symbol": "TCS",
  "composite_score": 78.5,
  "recommendation": "BUY",
  "confidence": 85.2,
  "agent_scores": {
    "fundamentals": {
      "score": 80.0,
      "confidence": 85.0,
      "reasoning": "Strong fundamentals...",
      "metrics": {...},
      "breakdown": {...}
    },
    "momentum": {...},
    "quality": {...},
    "sentiment": {...},
    "institutional_flow": {...}
  },
  "weights": {
    "fundamentals": 0.25,
    "momentum": 0.20,
    ...
  },
  "market_regime": {
    "regime": "BULL",
    "trend": "BULL",
    "volatility": "NORMAL",
    ...
  },
  "narrative": {
    "investment_thesis": "...",
    "key_strengths": [...],
    "key_risks": [...],
    "summary": "..."
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request` - Invalid symbol
- `404 Not Found` - Stock not found
- `500 Internal Server Error` - Analysis failed

---

### 2. Batch Analyze

Analyze multiple stocks in one request.

**Endpoint**: `POST /batch-analyze`

**Request Body**:
```json
{
  "symbols": ["TCS", "INFY", "WIPRO"],
  "include_narrative": false,
  "sort_by": "score"
}
```

**Parameters**:
- `symbols`: List of stock symbols
- `include_narrative`: Include LLM narratives (slower)
- `sort_by`: Sort results by "score", "confidence", or "symbol"

**Response** (200 OK):
```json
{
  "total_analyzed": 3,
  "successful": 3,
  "failed": 0,
  "results": [...],
  "timestamp": "2026-02-01T12:00:00Z",
  "duration_seconds": 12.5
}
```

---

### 3. Top Picks

Get top-performing stocks from NIFTY 50.

**Endpoint**: `GET /top-picks`

**Query Parameters**:
- `limit` (optional): Number of stocks (default: 10, max: 50)
- `include_narrative` (optional): Include narratives (default: false)

**Example**: `GET /top-picks?limit=15&include_narrative=false`

**Response** (200 OK):
```json
{
  "market_regime": {...},
  "top_picks": [...],
  "total_analyzed": 50,
  "timestamp": "2026-02-01T12:00:00Z",
  "duration_seconds": 45.2
}
```

---

### 4. Market Regime

Get current market regime.

**Endpoint**: `GET /market-regime`

**Response** (200 OK):
```json
{
  "regime": "BULL",
  "trend": "BULL",
  "volatility": "NORMAL",
  "weights": {
    "fundamentals": 0.25,
    "momentum": 0.20,
    "quality": 0.20,
    "sentiment": 0.15,
    "institutional_flow": 0.20
  },
  "metrics": {
    "nifty_return_20d": 5.2,
    "volatility_20d": 12.5,
    ...
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

## Historical Data Endpoints

### 5. Stock History

Get historical analysis data for a stock.

**Endpoint**: `GET /history/stock/{symbol}`

**Query Parameters**:
- `days` (optional): Number of days (default: 30, max: 1825)
- `include_price` (optional): Include price data (default: true)

**Example**: `GET /history/stock/TCS?days=90&include_price=true`

**Response** (200 OK):
```json
{
  "symbol": "TCS",
  "history": [
    {
      "timestamp": "2026-01-01T00:00:00Z",
      "composite_score": 75.5,
      "recommendation": "BUY",
      "confidence": 82.0,
      "price": 3850.50
    },
    ...
  ],
  "trend": {
    "direction": "up",
    "strength": 0.75
  },
  "statistics": {
    "avg_score": 76.2,
    "min_score": 70.0,
    "max_score": 80.5,
    "current_score": 78.5,
    "change": 3.5
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

### 6. Regime History

Get market regime timeline.

**Endpoint**: `GET /history/regime`

**Query Parameters**:
- `days` (optional): Number of days (default: 30)

**Example**: `GET /history/regime?days=60`

**Response** (200 OK):
```json
{
  "history": [
    {
      "timestamp": "2026-01-01T00:00:00Z",
      "regime": "BULL",
      "trend": "BULL",
      "volatility": "NORMAL",
      "weights": {...}
    },
    ...
  ],
  "current_regime": {...},
  "regime_changes": 3,
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

## Analytics Endpoints

### 7. System Analytics

Get system performance metrics.

**Endpoint**: `GET /analytics/system`

**Response** (200 OK):
```json
{
  "uptime_seconds": 86400,
  "total_requests": 1250,
  "avg_response_time_ms": 850,
  "error_rate": 0.02,
  "cache_hit_rate": 0.75,
  "agent_performance": {
    "fundamentals": {"avg_time_ms": 150, "success_rate": 0.98},
    ...
  },
  "database_stats": {
    "total_analyses": 5000,
    "total_regimes": 150,
    "watchlist_items": 25
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

### 8. Sector Analysis

Get sector performance analysis.

**Endpoint**: `GET /analytics/sectors`

**Query Parameters**:
- `days` (optional): Analysis period (default: 7)

**Example**: `GET /analytics/sectors?days=30`

**Response** (200 OK):
```json
{
  "sectors": [
    {
      "sector": "Information Technology",
      "avg_score": 78.5,
      "stock_count": 12,
      "top_pick": "TCS",
      "trend": "up",
      "change_percent": 2.5
    },
    ...
  ],
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

### 9. Agent Analytics

Get agent performance metrics.

**Endpoint**: `GET /analytics/agents`

**Response** (200 OK):
```json
{
  "agents": {
    "fundamentals": {
      "avg_execution_time_ms": 150,
      "success_rate": 0.98,
      "avg_score": 75.2,
      "total_executions": 1250
    },
    ...
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

## Watchlist Endpoints

### 10. Add to Watchlist

Add a stock to the watchlist.

**Endpoint**: `POST /watchlist`

**Request Body**:
```json
{
  "symbol": "TCS",
  "notes": "Strong fundamentals, good buy"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "symbol": "TCS",
  "added_at": "2026-02-01T12:00:00Z"
}
```

---

### 11. Get Watchlist

Get all watchlist items.

**Endpoint**: `GET /watchlist`

**Response** (200 OK):
```json
{
  "watchlist": [
    {
      "symbol": "TCS",
      "added_at": "2026-01-15T10:00:00Z",
      "notes": "Strong fundamentals",
      "latest_score": 78.5,
      "latest_recommendation": "BUY",
      "latest_update": "2026-02-01T12:00:00Z"
    },
    ...
  ],
  "count": 15,
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

### 12. Remove from Watchlist

Remove a stock from the watchlist.

**Endpoint**: `DELETE /watchlist/{symbol}`

**Example**: `DELETE /watchlist/TCS`

**Response** (200 OK):
```json
{
  "success": true,
  "symbol": "TCS",
  "removed_at": "2026-02-01T12:00:00Z"
}
```

---

## Comparison Endpoints

### 13. Compare Stocks

Compare multiple stocks side-by-side.

**Endpoint**: `POST /compare`

**Request Body**:
```json
{
  "symbols": ["TCS", "INFY", "WIPRO", "HCLTECH"],
  "include_history": false
}
```

**Parameters**:
- `symbols`: 2-4 stock symbols
- `include_history`: Include historical comparison

**Response** (200 OK):
```json
{
  "stocks": [
    {
      "symbol": "TCS",
      "composite_score": 78.5,
      "recommendation": "BUY",
      "agent_scores": {...},
      ...
    },
    ...
  ],
  "comparison_matrix": {
    "highest_score": "TCS",
    "lowest_score": "WIPRO",
    "best_fundamentals": "TCS",
    "best_momentum": "INFY",
    ...
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

## Export Endpoints

### 14. Export Analysis

Export stock analysis data.

**Endpoint**: `GET /export/analysis/{symbol}`

**Query Parameters**:
- `format`: "json" or "csv" (default: "json")
- `days` (optional): History period (default: 30)

**Example**: `GET /export/analysis/TCS?format=csv&days=90`

**Response** (200 OK):
- Content-Type: application/json or text/csv
- Body: Analysis data in requested format

---

## Data Collector Endpoints

### 15. Collector Status

Get data collector status.

**Endpoint**: `GET /collector/status`

**Response** (200 OK):
```json
{
  "enabled": true,
  "running": true,
  "interval_seconds": 14400,
  "last_run": "2026-02-01T08:00:00Z",
  "next_run": "2026-02-01T12:00:00Z",
  "total_collections": 125,
  "success_rate": 0.96
}
```

---

### 16. Manual Collection

Trigger manual data collection.

**Endpoint**: `POST /collector/collect`

**Request Body** (optional):
```json
{
  "symbols": ["TCS", "INFY"],  // Optional, defaults to all NIFTY 50
  "force": false
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "collected": 50,
  "failed": 0,
  "duration_seconds": 45.2,
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

## Utility Endpoints

### 17. Health Check

Check API health status.

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-02-01T12:00:00Z",
  "components": {
    "database": "healthy",
    "data_provider": "healthy",
    "market_regime": "healthy",
    "background_tasks": "healthy"
  },
  "version": "2.0"
}
```

---

### 18. Stock Universe

Get available stock symbols.

**Endpoint**: `GET /stock-universe`

**Response** (200 OK):
```json
{
  "total_stocks": 50,
  "indices": {
    "NIFTY50": ["TCS", "INFY", ...],
    "IT": ["TCS", "INFY", "WIPRO", ...],
    "Finance": ["HDFCBANK", "ICICIBANK", ...]
  },
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

## Error Responses

All endpoints may return standard HTTP error codes:

**400 Bad Request**:
```json
{
  "detail": "Invalid symbol: XYZ"
}
```

**404 Not Found**:
```json
{
  "detail": "Stock not found: ABC"
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Analysis failed: Connection timeout"
}
```

---

## Rate Limiting

Currently, no rate limiting is enforced. For production deployment, consider implementing rate limiting.

---

## Webhooks

Not currently supported. Planned for v3.0.

---

## WebSocket Support

Not currently supported. Planned for v3.0 for real-time updates.

---

## Best Practices

1. **Caching**: Results are cached for 15 minutes. Use `include_narrative=false` for faster responses.

2. **Batch Operations**: Use `/batch-analyze` instead of multiple `/analyze` calls.

3. **Historical Data**: Request only the data you need using `days` parameter.

4. **Error Handling**: Always handle potential errors gracefully.

5. **Timestamps**: All timestamps are in ISO 8601 format (UTC).

---

## Examples

### Python

```python
import requests

# Analyze stock
response = requests.post(
    "http://localhost:8000/analyze",
    json={"symbol": "TCS", "include_narrative": True}
)
data = response.json()
print(f"Score: {data['composite_score']}")

# Get top picks
response = requests.get("http://localhost:8000/top-picks?limit=10")
picks = response.json()
for pick in picks['top_picks']:
    print(f"{pick['symbol']}: {pick['composite_score']}")
```

### JavaScript

```javascript
// Analyze stock
const response = await fetch('http://localhost:8000/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ symbol: 'TCS', include_narrative: true })
});
const data = await response.json();
console.log(`Score: ${data.composite_score}`);

// Get watchlist
const watchlist = await fetch('http://localhost:8000/watchlist')
  .then(res => res.json());
console.log(`${watchlist.count} stocks in watchlist`);
```

---

**API Version**: 2.0
**Last Updated**: February 1, 2026
**Status**: Production Ready ✅
