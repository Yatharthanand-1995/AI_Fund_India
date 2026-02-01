# AI Hedge Fund System - Architecture Diagrams

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │           React Frontend (TypeScript)                       │   │
│  │  • TanStack Query (data fetching & caching)                │   │
│  │  • Zustand (state management)                               │   │
│  │  • Recharts (data visualization)                            │   │
│  │  • Tailwind CSS (styling)                                   │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              ↕ HTTP/REST                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API LAYER                                    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              FastAPI Application                            │   │
│  │  • CORS Middleware                                          │   │
│  │  • Request Validation (Pydantic)                            │   │
│  │  • Response Caching (15-min TTL)                           │   │
│  │  • Concurrent Request Processing                            │   │
│  │  • Error Handling & Logging                                 │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              ↕                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              StockScorer (Orchestrator)                     │   │
│  │  • Coordinates all 5 agents                                 │   │
│  │  • Manages adaptive/static weights                          │   │
│  │  • Calculates composite scores                              │   │
│  │  • Determines recommendations                               │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              ↕                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │         Market Regime Service (Optional)                    │   │
│  │  • Detects bull/bear/sideways markets                       │   │
│  │  • Calculates volatility levels                             │   │
│  │  • Provides adaptive weights (6-hour cache)                 │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              ↕                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AGENT LAYER                                     │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Fundamentals │  │   Momentum   │  │   Quality    │            │
│  │    Agent     │  │    Agent     │  │    Agent     │            │
│  │    (36%)     │  │    (27%)     │  │    (18%)     │            │
│  │              │  │              │  │              │            │
│  │ • ROE        │  │ • RSI        │  │ • Volatility │            │
│  │ • P/E Ratio  │  │ • SMA/EMA    │  │ • Stability  │            │
│  │ • Revenue ↑  │  │ • MACD       │  │ • Drawdown   │            │
│  │ • Debt/Eq    │  │ • Rel.Str.   │  │              │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │  Sentiment   │  │ Inst. Flow   │                                │
│  │    Agent     │  │    Agent     │                                │
│  │    (9%)      │  │    (10%)     │                                │
│  │              │  │              │                                │
│  │ • Analysts   │  │ • OBV Trend  │                                │
│  │ • Target $   │  │ • MFI/CMF    │                                │
│  │ • LLM News   │  │ • Vol Spike  │                                │
│  │              │  │ • VWAP       │                                │
│  └──────────────┘  └──────────────┘                                │
│                              ↕                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                      │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │         EnhancedYahooProvider (Data Provider)               │   │
│  │  • Yahoo Finance API (yfinance)                             │   │
│  │  • 40+ Technical Indicators (TA-Lib)                        │   │
│  │  • 20-minute caching                                        │   │
│  │  • Circuit breaker (5 failures → 60s cooldown)             │   │
│  │  • 15-second API timeout                                    │   │
│  │  • Rate limiting (500ms delay)                              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              ↕                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              In-Memory Cache                                │   │
│  │  • TTL: 1200 seconds (20 minutes)                          │   │
│  │  • Stores: Historical data + Technical indicators          │   │
│  │  • Automatic cleanup on expiry                              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              ↕                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │           Yahoo Finance API                                 │   │
│  │  • Historical price data (OHLCV)                           │   │
│  │  • Company info (market cap, sector, etc.)                 │   │
│  │  • Financial statements                                     │   │
│  │  • Analyst recommendations                                  │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │           LLM Services (Optional)                           │   │
│  │  • OpenAI GPT-4                                            │   │
│  │  • Anthropic Claude 3                                       │   │
│  │  • Google Gemini 1.5                                        │   │
│  │  → Used for investment thesis generation                   │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Complete Analysis Request Flow

```
User Action: Analyze "AAPL"
    │
    │ 1. User clicks "Analyze" button
    ▼
┌──────────────────────────────────────┐
│   React Frontend (Browser)            │
│   • Validates input                   │
│   • Calls TanStack Query hook         │
└──────────────────────────────────────┘
    │
    │ 2. HTTP POST /analyze {"symbol": "AAPL"}
    ▼
┌──────────────────────────────────────┐
│   FastAPI Server (Port 8010)          │
│   • Request validation (Pydantic)     │
│   • Check analysis_cache (15 min)    │
│   • If cached → return immediately    │
└──────────────────────────────────────┘
    │
    │ 3. Cache miss → Initialize StockScorer
    ▼
┌──────────────────────────────────────┐
│   StockScorer.score_stock("AAPL")    │
│   • Get current weights               │
│   • Initialize data provider          │
└──────────────────────────────────────┘
    │
    │ 4. Request comprehensive data
    ▼
┌──────────────────────────────────────┐
│   EnhancedYahooProvider               │
│   • Check cache (20 min)              │
│   • If cached → return                │
│   • If not → fetch from Yahoo         │
└──────────────────────────────────────┘
    │
    │ 5. Yahoo Finance API call (with circuit breaker)
    ▼
┌──────────────────────────────────────┐
│   Yahoo Finance                       │
│   • Historical data (2 years)         │
│   • Company info                      │
│   • Financials                        │
│   • Returns raw data                  │
└──────────────────────────────────────┘
    │
    │ 6. Raw data returned
    ▼
┌──────────────────────────────────────┐
│   EnhancedYahooProvider               │
│   • Calculate 40+ indicators          │
│   • Cache result (20 min TTL)         │
│   • Return comprehensive data         │
└──────────────────────────────────────┘
    │
    │ 7. Comprehensive data received
    ▼
┌──────────────────────────────────────┐
│   StockScorer                         │
│   • Run 5 agents in parallel:         │
│     - FundamentalsAgent.analyze()     │
│     - MomentumAgent.analyze()         │
│     - QualityAgent.analyze()          │
│     - SentimentAgent.analyze()        │
│     - InstitutionalFlowAgent.analyze()│
└──────────────────────────────────────┘
    │
    │ 8. All agent results collected
    ▼
┌──────────────────────────────────────┐
│   StockScorer                         │
│   • Calculate weighted composite:     │
│     score = Σ(weight[i] * score[i])   │
│   • Calculate confidence              │
│   • Determine recommendation          │
└──────────────────────────────────────┘
    │
    │ 9. Pass to narrative engine
    ▼
┌──────────────────────────────────────┐
│   InvestmentNarrativeEngine           │
│   • Generate thesis (LLM or rules)    │
│   • Extract strengths/risks           │
│   • Format final narrative            │
└──────────────────────────────────────┘
    │
    │ 10. Complete analysis assembled
    ▼
┌──────────────────────────────────────┐
│   FastAPI Server                      │
│   • Cache result (15 min)             │
│   • Serialize to JSON                 │
│   • Return HTTP 200 response          │
└──────────────────────────────────────┘
    │
    │ 11. JSON response received
    ▼
┌──────────────────────────────────────┐
│   React Frontend                      │
│   • Parse JSON                        │
│   • Update UI components              │
│   • Render analysis results           │
└──────────────────────────────────────┘
    │
    │ 12. User sees results
    ▼
   User sees:
   • Composite Score: 72.5
   • Recommendation: STRONG BUY
   • Agent Scores (5 bars)
   • Investment Thesis
   • Key Strengths/Risks

Total Time: ~2-5 seconds
(First request: 3-5s, Cached: <500ms)
```

---

## Agent Interaction Diagram

### How Agents Collaborate

```
┌─────────────────────────────────────────────────────────────────┐
│                     StockScorer (Orchestrator)                   │
│                                                                  │
│  Input: symbol = "AAPL"                                          │
│  Output: Composite analysis with weighted scores                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Distribute work to agents
                              ▼
        ┌──────────────────────────────────────────────┐
        │                                              │
        ▼                ▼               ▼             ▼              ▼
┌────────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐
│ Fundamentals   │ │ Momentum │ │ Quality  │ │ Sentiment  │ │ Inst. Flow   │
│ Agent          │ │ Agent    │ │ Agent    │ │ Agent      │ │ Agent        │
└────────────────┘ └──────────┘ └──────────┘ └────────────┘ └──────────────┘
        │                │              │             │              │
        │ Input:         │              │             │              │
        │ • Financials   │              │             │              │
        │ • Balance      │              │             │              │
        │   sheet        │              │             │              │
        │                │              │             │              │
        │ Analyzes:      │ Input:       │ Input:      │ Input:       │ Input:
        │ • ROE          │ • OHLCV      │ • OHLCV     │ • Analyst    │ • OHLCV
        │ • P/E Ratio    │ • SPY data   │ • Hist.     │   ratings    │ • Volume
        │ • Growth       │              │   data      │ • News       │ • OBV/AD
        │ • Debt         │ Analyzes:    │             │              │
        │                │ • RSI        │ Analyzes:   │ Analyzes:    │ Analyzes:
        │ Returns:       │ • SMA/EMA    │ • Volatil.  │ • Recom.     │ • OBV trend
        │ {              │ • MACD       │ • Trend     │ • Target $   │ • MFI/CMF
        │   score: 75,   │ • Returns    │ • Quality   │ • Sentiment  │ • Vol spike
        │   conf: 0.9,   │              │             │              │ • VWAP
        │   metrics: {}, │ Returns:     │ Returns:    │ Returns:     │
        │   reasoning    │ {            │ {           │ {            │ Returns:
        │ }              │   score: 68  │   score: 72 │   score: 70  │ {
        │                │   conf: 0.95 │   conf: 0.9 │   conf: 0.7  │   score: 75
        │                │   ...        │   ...       │   ...        │   conf: 0.85
        │                │ }            │ }           │ }            │   ...
        │                │              │             │              │ }
        ▼                ▼              ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     StockScorer (Aggregation)                    │
│                                                                  │
│  Composite Score Calculation:                                   │
│  score = (0.36 × 75) + (0.27 × 68) + (0.18 × 72) +             │
│          (0.09 × 70) + (0.10 × 75)                              │
│        = 27.0 + 18.36 + 12.96 + 6.3 + 7.5                       │
│        = 72.12                                                  │
│                                                                  │
│  Composite Confidence:                                           │
│  conf = (0.36 × 0.9) + (0.27 × 0.95) + (0.18 × 0.9) +          │
│         (0.09 × 0.7) + (0.10 × 0.85)                            │
│       = 0.875 (87.5%)                                           │
│                                                                  │
│  Recommendation: Based on score threshold                        │
│  72.12 → STRONG BUY (>= 70)                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  InvestmentNarrativeEngine                       │
│                                                                  │
│  Takes agent results and generates:                              │
│  • Investment thesis (LLM or rule-based)                         │
│  • Key strengths extraction                                      │
│  • Risk identification                                           │
│  • Final recommendation                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Final Analysis Returned to User
```

---

## Caching Architecture

### Multi-Layer Caching Strategy

```
Layer 1: Frontend Query Cache (React Query)
┌───────────────────────────────────────────┐
│  Duration: 5 minutes (300s)                │
│  Scope: Client-side (browser memory)       │
│  Purpose: Avoid redundant API calls        │
│  Storage: In-memory (per browser tab)      │
│  Invalidation: Time-based or manual        │
└───────────────────────────────────────────┘
        │ Cache miss → API call
        ▼
Layer 2: API Analysis Cache (In-Memory)
┌───────────────────────────────────────────┐
│  Duration: 15 minutes (900s)               │
│  Scope: Server-side (API process)          │
│  Purpose: Fast response for repeated req.  │
│  Storage: Python dict in memory            │
│  Invalidation: TTL-based cleanup           │
│  Key: f"analysis_{symbol}"                 │
└───────────────────────────────────────────┘
        │ Cache miss → Calculate analysis
        ▼
Layer 3: Data Provider Cache (In-Memory)
┌───────────────────────────────────────────┐
│  Duration: 20 minutes (1200s)              │
│  Scope: Data provider instance             │
│  Purpose: Avoid Yahoo Finance API calls    │
│  Storage: Python dict + expiry dict        │
│  Invalidation: TTL-based                   │
│  Key: symbol                               │
│  Value: {                                  │
│    historical_data: pd.DataFrame           │
│    technical_data: dict                    │
│    info: dict                              │
│    ...                                     │
│  }                                         │
└───────────────────────────────────────────┘
        │ Cache miss → Fetch from Yahoo
        ▼
Layer 4: Market Regime Cache (In-Memory)
┌───────────────────────────────────────────┐
│  Duration: 6 hours (21600s)                │
│  Scope: Market regime service              │
│  Purpose: Reduce SPY analysis overhead     │
│  Storage: Singleton service cache          │
│  Invalidation: TTL-based                   │
│  Key: "current_regime"                     │
│  Value: {                                  │
│    regime: "BULL_NORMAL"                   │
│    trend: "BULL"                           │
│    volatility: "NORMAL"                    │
│    weights: {...}                          │
│  }                                         │
└───────────────────────────────────────────┘

Cache Hit Rates (Expected):
• Layer 1 (Frontend): 60-70% hit rate
• Layer 2 (API): 40-50% hit rate
• Layer 3 (Data Provider): 70-80% hit rate
• Layer 4 (Market Regime): 95%+ hit rate

Performance Impact:
• All cached: ~50ms (network latency only)
• Layer 1 miss: ~200ms (API processing)
• Layer 2 miss: ~1-2s (agent analysis)
• Layer 3 miss: ~3-5s (Yahoo API call + indicators)
```

---

## Deployment Architecture

### Production Deployment Options

#### Option 1: Monolithic Docker Deployment

```
┌──────────────────────────────────────────────────────────────┐
│                         Docker Host                           │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Container: api (Python)                                │ │
│  │  • FastAPI application                                  │ │
│  │  • Port: 8010                                           │ │
│  │  • Memory: 2GB                                          │ │
│  │  • CPU: 2 cores                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Container: frontend (Node.js)                          │ │
│  │  • React + Vite                                         │ │
│  │  • Port: 5174                                           │ │
│  │  • Memory: 512MB                                        │ │
│  │  • CPU: 1 core                                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Container: redis (optional)                            │ │
│  │  • Distributed caching                                  │ │
│  │  • Port: 6379                                           │ │
│  │  • Memory: 256MB                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Docker Compose orchestrates all containers                  │
└──────────────────────────────────────────────────────────────┘
```

#### Option 2: Kubernetes Cluster

```
┌──────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                         │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Ingress Controller (NGINX)                            │  │
│  │  • Routes traffic to services                          │  │
│  │  • SSL termination                                     │  │
│  │  • Load balancing                                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                        │                                      │
│        ┌───────────────┴───────────────┐                     │
│        ▼                               ▼                     │
│  ┌──────────────┐              ┌──────────────┐             │
│  │  Service:    │              │  Service:    │             │
│  │  api         │              │  frontend    │             │
│  └──────────────┘              └──────────────┘             │
│        │                               │                     │
│  ┌─────┴──────┐                 ┌─────┴──────┐             │
│  ▼            ▼                 ▼            ▼             │
│ ┌────┐      ┌────┐            ┌────┐      ┌────┐          │
│ │Pod1│      │Pod2│            │Pod1│      │Pod2│          │
│ │API │      │API │            │ FE │      │ FE │          │
│ └────┘      └────┘            └────┘      └────┘          │
│                                                               │
│  • Auto-scaling (HPA)                                        │
│  • Health checks                                             │
│  • Rolling updates                                           │
│  • Resource limits                                           │
└──────────────────────────────────────────────────────────────┘
```

#### Option 3: Serverless (AWS Lambda)

```
┌──────────────────────────────────────────────────────────────┐
│                         AWS Cloud                             │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  API Gateway                                            │ │
│  │  • REST API endpoints                                   │ │
│  │  • Request throttling                                   │ │
│  │  • API keys                                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                        │                                      │
│        ┌───────────────┴───────────────┐                     │
│        ▼                               ▼                     │
│  ┌──────────────┐              ┌──────────────┐             │
│  │  Lambda:     │              │  Lambda:     │             │
│  │  analyze     │              │  batch       │             │
│  │  (2GB RAM)   │              │  (3GB RAM)   │             │
│  └──────────────┘              └──────────────┘             │
│        │                               │                     │
│        └───────────────┬───────────────┘                     │
│                        ▼                                      │
│              ┌──────────────────┐                            │
│              │  ElastiCache     │                            │
│              │  (Redis)         │                            │
│              │  • Shared cache  │                            │
│              └──────────────────┘                            │
│                                                               │
│  Frontend: S3 + CloudFront (static hosting)                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

### Security Layers

```
┌──────────────────────────────────────────────────────────────┐
│                    Security Layers                            │
│                                                               │
│  Layer 1: Network Security                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  • HTTPS/TLS encryption                                 │ │
│  │  • CORS policy (whitelisted origins)                    │ │
│  │  • Rate limiting (per IP)                               │ │
│  │  • DDoS protection (CloudFlare/AWS Shield)              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Layer 2: Application Security                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  • Input validation (Pydantic)                          │ │
│  │  • SQL injection prevention (ORM/parameterized)         │ │
│  │  • XSS protection (React auto-escaping)                 │ │
│  │  • CSRF tokens                                          │ │
│  │  • API authentication (JWT/API keys)                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Layer 3: Data Security                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  • Environment variables for secrets                    │ │
│  │  • API keys stored in vault (AWS Secrets Manager)       │ │
│  │  • No sensitive data in logs                            │ │
│  │  • Data encryption at rest (if storing user data)       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Layer 4: Infrastructure Security                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  • Principle of least privilege                         │ │
│  │  • Security groups/firewall rules                       │ │
│  │  • Container scanning (Trivy/Snyk)                      │ │
│  │  • Dependency vulnerability scanning                    │ │
│  │  • Regular security updates                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Layer 5: Monitoring & Logging                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  • Centralized logging (CloudWatch/ELK)                 │ │
│  │  • Error tracking (Sentry)                              │ │
│  │  • Audit trails                                         │ │
│  │  • Anomaly detection                                    │ │
│  │  • Alerting (PagerDuty/Opsgenie)                        │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Scalability Architecture

### Horizontal Scaling Strategy

```
                    Load Balancer
                    (NGINX/ALB)
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │  API    │      │  API    │      │  API    │
   │Instance1│      │Instance2│      │Instance3│
   └─────────┘      └─────────┘      └─────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                  Shared Redis Cache
                  (ElastiCache/Redis Cluster)
                         │
                         ▼
                  External APIs
                  (Yahoo Finance)

Scaling Metrics:
• CPU Usage > 70% → Scale up
• Request Queue > 100 → Scale up
• Response Time > 5s → Scale up
• Error Rate > 5% → Alert + investigate

Auto-scaling Rules:
• Min instances: 2
• Max instances: 10
• Scale up: +2 instances when CPU > 70%
• Scale down: -1 instance when CPU < 30% for 5 min
• Cooldown period: 5 minutes
```

---

## Monitoring & Observability

### Monitoring Stack

```
┌──────────────────────────────────────────────────────────────┐
│                    Application Metrics                        │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Prometheus + Grafana                                   │ │
│  │  • API response times (p50, p95, p99)                   │ │
│  │  • Request rate (req/sec)                               │ │
│  │  • Error rate (%)                                       │ │
│  │  • Cache hit rates                                      │ │
│  │  • Agent execution times                                │ │
│  │  • Database query times                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Business Metrics                                       │ │
│  │  • Analyses per day                                     │ │
│  │  • Popular stocks                                       │ │
│  │  • Recommendation distribution                          │ │
│  │  • User engagement                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Infrastructure Metrics                                 │ │
│  │  • CPU/Memory/Disk usage                                │ │
│  │  • Network I/O                                          │ │
│  │  • Container health                                     │ │
│  │  • API availability (uptime)                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Error Tracking                                         │ │
│  │  • Sentry for Python exceptions                         │ │
│  │  • Frontend error tracking                              │ │
│  │  • Stack traces                                         │ │
│  │  • User context                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Alerting                                               │ │
│  │  • API downtime > 1 minute → PagerDuty                  │ │
│  │  • Error rate > 5% → Slack alert                        │ │
│  │  • Response time > 10s → Email alert                    │ │
│  │  • Circuit breaker open → Slack alert                   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0   | Jan 2026 | Initial architecture documentation |

---

**Maintained By**: AI Hedge Fund System Team
**Last Updated**: January 2026
