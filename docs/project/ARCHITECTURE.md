# Architecture Documentation

Comprehensive overview of the AI Hedge Fund system architecture, design decisions, and component interactions.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Components](#components)
4. [Data Flow](#data-flow)
5. [Design Decisions](#design-decisions)
6. [Scalability](#scalability)
7. [Performance](#performance)
8. [Future Enhancements](#future-enhancements)

## System Overview

The AI Hedge Fund system is a multi-agent stock analysis platform that combines:
- **5 Specialized AI Agents** for different analysis aspects
- **Market Regime Detection** for adaptive strategy
- **LLM Integration** for human-readable narratives
- **Hybrid Data Sources** with automatic failover
- **REST API** for programmatic access
- **Modern Web UI** for user interaction

### Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (async web framework)
- Pandas & NumPy (data processing)
- TA-Lib (technical indicators)
- Pydantic (validation)

**Data Sources:**
- NSEpy (primary - NSE India official)
- Yahoo Finance (fallback)

**LLM Providers:**
- Google Gemini 1.5 Flash (primary)
- OpenAI GPT-4 (alternative)
- Anthropic Claude 3 (alternative)
- Rule-based fallback

**Frontend:**
- React 18
- TypeScript
- Vite (build tool)
- Tailwind CSS
- Zustand (state management)
- Axios (API client)

**Infrastructure:**
- Uvicorn (ASGI server)
- Nginx (reverse proxy)
- Docker (containerization)
- Systemd (process management)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Dashboard │  │Top Picks │  │ Details  │  │  About   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘       │
│       └─────────────┴─────────────┴──────────────┐             │
│                                                    │             │
│                      React + TypeScript + Vite    │             │
└────────────────────────────────────────────────────┼─────────────┘
                                                     │ HTTP/REST
┌────────────────────────────────────────────────────┼─────────────┐
│                        API Layer                   │             │
│  ┌─────────────────────────────────────────────────┴──────────┐ │
│  │                  FastAPI Application                       │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │
│  │  │ Analyze  │  │  Batch   │  │Top Picks │  │  Health  │  │ │
│  │  │ Endpoint │  │ Endpoint │  │ Endpoint │  │ Endpoint │  │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘  │ │
│  └───────┼─────────────┼─────────────┼──────────────────────┘ │
│          │             │             │                          │
│  ┌───────┴─────────────┴─────────────┴──────────────────────┐ │
│  │                   Middleware Layer                        │ │
│  │  • Request Logging    • Performance Monitoring            │ │
│  │  • Error Tracking     • Metrics Collection                │ │
│  └───────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                    Core Business Logic                           │
│  ┌──────────────────────────┴──────────────────────────┐        │
│  │              Stock Scorer (Orchestrator)             │        │
│  │  • Coordinates all agents                            │        │
│  │  • Applies weights (static or adaptive)              │        │
│  │  • Calculates composite score                        │        │
│  │  • Generates recommendation                          │        │
│  └───────────┬──────────────────────────────────────────┘        │
│              │                                                    │
│  ┌───────────┴────────────────────────────────────────────────┐ │
│  │              Market Regime Service (Optional)              │ │
│  │  • Analyzes NIFTY 50 trend (Bull/Bear/Sideways)            │ │
│  │  • Detects volatility (High/Normal/Low)                    │ │
│  │  • Provides adaptive weights (9 regime combinations)       │ │
│  │  • 6-hour caching                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    5 AI Agents                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │Fundamentals │  │  Momentum   │  │   Quality   │     │   │
│  │  │   (36%)     │  │    (27%)    │  │    (18%)    │     │   │
│  │  │• ROE, P/E   │  │• RSI, MACD  │  │• Volatility │     │   │
│  │  │• P/B, Debt  │  │• SMA, Trend │  │• Drawdown   │     │   │
│  │  │• Growth     │  │• Returns    │  │• Stability  │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  │  ┌─────────────┐  ┌─────────────┐                       │   │
│  │  │  Sentiment  │  │ Inst. Flow  │                       │   │
│  │  │    (9%)     │  │    (10%)    │                       │   │
│  │  │• Analysts   │  │• OBV, MFI   │                       │   │
│  │  │• Target $   │  │• Volume     │                       │   │
│  │  │• Coverage   │  │• VWAP, CMF  │                       │   │
│  │  └─────────────┘  └─────────────┘                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          Investment Narrative Engine                     │   │
│  │  • LLM-powered (Gemini/GPT-4/Claude)                     │   │
│  │  • Generates investment thesis                           │   │
│  │  • Extracts key strengths & risks                        │   │
│  │  • Rule-based fallback                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                        Data Layer                                │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │            Hybrid Data Provider                          │    │
│  │  • Primary: NSEpy                                        │    │
│  │  • Fallback: Yahoo Finance                               │    │
│  │  • Circuit breaker pattern                               │    │
│  │  • 20-minute caching                                     │    │
│  │  • Automatic failover                                    │    │
│  └────────────┬──────────────────────┬──────────────────────┘    │
│               │                      │                            │
│  ┌────────────┴────────┐  ┌─────────┴──────────┐                │
│  │   NSE Provider      │  │  Yahoo Provider    │                │
│  │  • NSEpy library    │  │  • yfinance lib    │                │
│  │  • Indian stocks    │  │  • .NS suffix      │                │
│  │  • Technical data   │  │  • Financials      │                │
│  │  • Rate limiting    │  │  • Info data       │                │
│  └─────────────────────┘  └────────────────────┘                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Stock Universe                              │   │
│  │  • NIFTY 50 (50 stocks)                                  │   │
│  │  • NIFTY Bank (12 stocks)                                │   │
│  │  • NIFTY IT (10 stocks)                                  │   │
│  │  • Sector & industry metadata                            │   │
│  │  • Market cap categorization                             │   │
│  │  • Singleton pattern                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                   Infrastructure Layer                           │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │            Logging & Monitoring                          │    │
│  │  • Structured logging (JSON/colored)                     │    │
│  │  • File rotation (size + time-based)                     │    │
│  │  • Metrics collection (counters, timings, gauges)        │    │
│  │  • Real-time dashboard                                   │    │
│  │  • Log analysis tools                                    │    │
│  └──────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend Layer

**Purpose**: User interface for stock analysis

**Components:**
- Dashboard page (search & analyze)
- Top Picks page (NIFTY 50 rankings)
- Stock Details page (detailed analysis)
- About page (system information)

**Communication:**
- REST API calls to backend via Axios
- State management with Zustand
- Client-side routing with React Router

### 2. API Layer

**Purpose**: REST API for all operations

**Endpoints:**
- `POST /analyze` - Single stock analysis
- `POST /analyze/batch` - Batch analysis (up to 50 stocks)
- `GET /portfolio/top-picks` - Top N from NIFTY 50
- `GET /market/regime` - Current market conditions
- `GET /health` - System health check
- `GET /stocks/universe` - Available stocks
- `GET /metrics` - Performance metrics

**Middleware:**
- Request logging (UUID, timing)
- Performance monitoring (slow request alerts)
- Error tracking (categorization, counting)
- CORS handling

### 3. Stock Scorer (Orchestrator)

**Purpose**: Coordinate agents and calculate final score

**Process:**
1. Receive symbol and optional NIFTY data
2. Fetch comprehensive data via HybridDataProvider
3. Determine current weights (static or adaptive)
4. Execute all 5 agents in parallel (conceptually)
5. Apply weights to agent scores
6. Calculate composite score (0-100)
7. Generate recommendation (STRONG BUY to SELL)
8. Return complete analysis

**Weights:**
- Static: Fundamentals 36%, Momentum 27%, Quality 18%, Sentiment 9%, Institutional Flow 10%
- Adaptive: Adjusted based on market regime (9 combinations)

### 4. Market Regime Service

**Purpose**: Detect market conditions and provide adaptive weights

**Detection:**
- **Trend**: BULL (50-SMA > 200-SMA, price > 50-SMA), BEAR (opposite), SIDEWAYS (mixed)
- **Volatility**: HIGH (>25%), NORMAL (15-25%), LOW (<15%)
- **Regime**: Combination of trend + volatility (e.g., BULL_NORMAL)

**Caching**: 6 hours

**Adaptive Weights:**
- BULL + NORMAL: Balanced (fundamentals 36%)
- BULL + HIGH: More momentum (momentum 36%)
- BEAR + HIGH: More quality/safety (quality 36%)
- etc.

### 5. AI Agents

#### Fundamentals Agent (36%)
- **Analyzes**: ROE, P/E, P/B, growth, debt, promoter holding
- **Scoring**: Profitability (40pts), Valuation (30pts), Growth (20pts), Health (10pts), Promoter bonus (+5pts)
- **Benchmarks**: Adjusted for Indian market (lower P/E, ROE thresholds)

#### Momentum Agent (27%)
- **Analyzes**: RSI, MACD, SMA, trend, returns, relative strength
- **Scoring**: RSI (25pts), Trend (35pts), Returns (30pts), Relative Strength (10pts)
- **Benchmark**: NIFTY 50 index for relative strength

#### Quality Agent (18%)
- **Analyzes**: Volatility, drawdowns, consistency, stability
- **Scoring**: Base 50 + volatility adjustment + trend + drawdown + consistency
- **Focus**: Low volatility, stable returns

#### Sentiment Agent (9%)
- **Analyzes**: Analyst recommendations, target prices, coverage
- **Scoring**: Recommendation (50pts), Target Price (30pts), Coverage (10pts)
- **Note**: Indian stocks have less analyst coverage than US

#### Institutional Flow Agent (10%)
- **Analyzes**: OBV, MFI, CMF, volume spikes, VWAP
- **Scoring**: OBV trend (30pts), MFI (25pts), CMF (20pts), Volume (15pts), VWAP (10pts)
- **Focus**: Smart money tracking

### 6. Narrative Engine

**Purpose**: Generate human-readable investment narrative

**Providers:**
1. Gemini 1.5 Flash (primary, free)
2. GPT-4 (alternative, paid)
3. Claude 3 (alternative, paid)
4. Rule-based (fallback)

**Output:**
- Investment thesis (2-3 sentences)
- Key strengths (3-5 bullet points)
- Key risks (3-5 bullet points)
- Summary (1-2 sentences)

### 7. Hybrid Data Provider

**Purpose**: Fetch stock data with automatic failover

**Pattern**: Circuit Breaker

**Flow:**
1. Try NSEpy (primary)
2. If fails 5 times, circuit opens
3. Use Yahoo Finance (fallback)
4. After 60s, try NSEpy again (half-open state)

**Features:**
- Rate limiting (500ms delay for NSE, 100ms for Yahoo)
- 20-minute caching
- Data enrichment (combine NSE + Yahoo data)
- 40+ technical indicators

### 8. Stock Universe

**Purpose**: Manage stock metadata and indices

**Data:**
- 92 unique stocks across 6 indices
- Sector and industry classification
- Market cap categories
- Index weights

**Features:**
- Symbol validation
- Search and filtering
- DataFrame/JSON export
- Singleton pattern

### 9. Logging & Monitoring

**Logging:**
- Colored console output (development)
- JSON structured logs (production)
- File rotation (10 MB, 5 backups)
- Daily rotation (30 days)
- Separate error log

**Monitoring:**
- Metrics collection (counters, timings, gauges)
- Percentile calculations (p50, p95, p99)
- Real-time dashboard
- Log analyzer
- Health checks

## Data Flow

### Single Stock Analysis Flow

```
User → Frontend → POST /analyze → API → Stock Scorer
                                            ↓
                                   Fetch NIFTY data
                                            ↓
                                   Get market regime (optional)
                                            ↓
                                   Determine weights
                                            ↓
                                   Fetch stock data
                                   (Hybrid Provider)
                                            ↓
            ┌───────────────────────────────┴──────────────────────────────┐
            ↓                ↓                ↓              ↓              ↓
    Fundamentals      Momentum          Quality      Sentiment      Inst. Flow
      Agent             Agent            Agent         Agent          Agent
        (36%)           (27%)            (18%)         (9%)           (10%)
            ↓                ↓                ↓              ↓              ↓
            └───────────────────────────────┬──────────────────────────────┘
                                            ↓
                              Apply weights & calculate
                              composite score
                                            ↓
                              Generate recommendation
                                            ↓
                              Generate narrative (optional)
                                            ↓
                              Return complete analysis
                                            ↓
                              Frontend ← JSON response
```

### Batch Analysis Flow

```
User → POST /analyze/batch (symbols: ["TCS", "INFY", ...])
            ↓
    Fetch NIFTY data once
            ↓
    Get market regime once
            ↓
    For each symbol:
      • Fetch stock data
      • Run all agents
      • Calculate score
      • (Skip narrative for performance)
            ↓
    Sort by score (descending)
            ↓
    Return all results
```

### Top Picks Flow

```
User → GET /portfolio/top-picks?limit=10
            ↓
    Get NIFTY 50 symbols (50 stocks)
            ↓
    Fetch NIFTY data
            ↓
    Get market regime
            ↓
    Batch analyze all 50 stocks
            ↓
    Sort by composite score
            ↓
    Return top N picks
```

## Design Decisions

### 1. Why Multi-Agent Architecture?

**Reasons:**
- **Modularity**: Each agent focuses on one aspect
- **Maintainability**: Easy to update individual agents
- **Transparency**: Clear breakdown of scoring logic
- **Flexibility**: Easy to add/remove agents or adjust weights

**Trade-off**: More complex than single model, but more interpretable

### 2. Why Hybrid Data Provider?

**Reasons:**
- NSEpy provides Indian-specific data but can be unreliable
- Yahoo Finance is more stable but less India-focused
- Circuit breaker prevents cascading failures
- Automatic failover ensures uptime

**Trade-off**: Additional complexity, but better reliability

### 3. Why Adaptive Weights?

**Reasons:**
- Market conditions change (bull vs bear)
- Different strategies work in different regimes
- Momentum less reliable in bear markets
- Quality more important in high volatility

**Trade-off**: More complex, but better performance

### 4. Why LLM Narratives?

**Reasons:**
- Human-readable explanations
- Context-aware insights
- Natural language generation
- Multiple provider support

**Trade-off**: Cost and latency, but better UX

### 5. Why FastAPI?

**Reasons:**
- Async support for concurrent requests
- Automatic API documentation (Swagger/ReDoc)
- Pydantic validation
- High performance
- Modern Python features

**Alternative**: Flask (simpler but less features)

### 6. Why React + TypeScript?

**Reasons:**
- Type safety reduces bugs
- Component-based architecture
- Large ecosystem
- Modern development experience

**Alternative**: Vue or vanilla JS

## Scalability

### Current Architecture

- **Vertical**: Single server, 4 workers
- **Capacity**: ~100 requests/minute
- **Bottleneck**: Data fetching from external APIs

### Horizontal Scaling

**Options:**
1. **Load Balancer + Multiple Instances**
   ```
   Nginx LB → [Backend 1, Backend 2, Backend 3]
   ```

2. **Distributed Caching (Redis)**
   - Share cache across instances
   - Reduce redundant API calls

3. **Task Queue (Celery)**
   - Offload heavy analysis to workers
   - Better for batch operations

4. **Database (PostgreSQL)**
   - Store analysis history
   - Reduce re-computation

### Database Schema (Future)

```sql
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    composite_score DECIMAL(5,2),
    recommendation VARCHAR(20),
    agent_scores JSONB,
    created_at TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_created_at (created_at)
);
```

## Performance

### Current Metrics

- **Single analysis**: 2-5 seconds
- **Batch (10 stocks)**: 15-30 seconds
- **Top picks (50 stocks)**: 60-120 seconds
- **Memory**: ~200 MB per worker

### Optimization Opportunities

1. **Parallel agent execution** (currently sequential)
2. **Cached technical indicators** (pre-compute)
3. **Database for historical data** (avoid re-fetching)
4. **CDN for frontend assets**
5. **Redis for distributed caching**

## Future Enhancements

### Short-term (1-3 months)

- [ ] Add more indices (NIFTY Next 50, Midcap 100)
- [ ] Implement portfolio tracking
- [ ] Add price alerts
- [ ] Historical analysis charts
- [ ] Email reports

### Medium-term (3-6 months)

- [ ] Machine learning for weight optimization
- [ ] Backtesting framework
- [ ] Mobile app (React Native)
- [ ] Webhook integrations
- [ ] Advanced charting (TradingView)

### Long-term (6-12 months)

- [ ] Options analysis
- [ ] Portfolio optimization (MPT)
- [ ] Social sentiment (Twitter, Reddit)
- [ ] News aggregation and analysis
- [ ] Automated trading signals
- [ ] Multi-market support (US, Europe)

## Security Considerations

### Current Implementation

- ✓ API key encryption in environment
- ✓ CORS configuration
- ✓ Input validation (Pydantic)
- ✓ Error handling
- ✓ Logging (no sensitive data)

### Recommended Additions

- [ ] Rate limiting per IP
- [ ] API authentication (JWT)
- [ ] User accounts and permissions
- [ ] Audit logging
- [ ] HTTPS enforcement
- [ ] Security headers (Helmet)

## Monitoring & Observability

### What We Track

- Request counts and rates
- Response times (avg, p50, p95, p99)
- Error rates and types
- Cache hit rates
- Agent execution times
- Data provider failures

### Tools

- Real-time dashboard (Python script)
- Log analyzer (Python script)
- Metrics API endpoints
- File-based logs

### Recommended Additions

- [ ] Prometheus + Grafana
- [ ] ELK stack (Elasticsearch, Logstash, Kibana)
- [ ] Sentry (error tracking)
- [ ] DataDog (APM)
- [ ] PagerDuty (alerting)

## Conclusion

The AI Hedge Fund system is designed as a modular, scalable, and maintainable stock analysis platform. The multi-agent architecture provides transparency and flexibility, while the hybrid data provider ensures reliability. The system is production-ready with comprehensive logging, monitoring, and testing.
