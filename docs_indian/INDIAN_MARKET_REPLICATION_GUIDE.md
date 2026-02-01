# AI Hedge Fund System - Indian Market Replication Guide

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Component Deep Dive](#component-deep-dive)
4. [Data Flow](#data-flow)
5. [Indian Market Adaptation](#indian-market-adaptation)
6. [Step-by-Step Implementation](#step-by-step-implementation)
7. [API Specifications](#api-specifications)
8. [Configuration](#configuration)
9. [Deployment](#deployment)
10. [Testing & Validation](#testing--validation)

---

## System Overview

The AI Hedge Fund System is a professional-grade investment analysis platform that employs **5 specialized AI agents** to provide comprehensive stock analysis with human-readable narratives.

### Key Features
- **5-Agent Intelligence**: Fundamentals, Momentum, Quality, Sentiment, Institutional Flow
- **Weighted Scoring**: Configurable agent weights (default: 36/27/18/9/10)
- **Adaptive Weights**: ML-based regime detection adjusts weights based on market conditions
- **Narrative Generation**: LLM-powered investment thesis generation (OpenAI, Anthropic, Gemini)
- **Paper Trading**: Simulated portfolio with auto-buy capabilities
- **Real-time Analysis**: 20-minute caching for 50-stock universe
- **REST API**: FastAPI backend with comprehensive endpoints
- **Modern Frontend**: React + TypeScript + TanStack Query

### System Scores Range
- **80-100**: STRONG BUY
- **60-79**: BUY
- **52-59**: WEAK BUY
- **48-51**: HOLD
- **42-47**: WEAK SELL
- **0-41**: SELL

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT (React Frontend)                 │
│                    http://localhost:5174                     │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   API LAYER (FastAPI)                        │
│                  http://localhost:8010                       │
│  • /analyze - Single stock analysis                         │
│  • /analyze/batch - Batch analysis                          │
│  • /portfolio/* - Portfolio management                      │
│  • /market/regime - Market regime detection                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER (StockScorer)               │
│  • Coordinates all 5 agents                                  │
│  • Applies adaptive weights                                  │
│  • Calculates composite score                                │
└────┬────┬────┬────┬────┬──────────────────────────────────┘
     │    │    │    │    │
     ▼    ▼    ▼    ▼    ▼
┌─────────────────────────────────────────────────────────────┐
│                    5 SPECIALIZED AGENTS                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Fundamentals │ │  Momentum    │ │   Quality    │        │
│  │   (36%)      │ │   (27%)      │ │   (18%)      │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐                          │
│  │  Sentiment   │ │ Inst. Flow   │                          │
│  │   (9%)       │ │   (10%)      │                          │
│  └──────────────┘ └──────────────┘                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              DATA PROVIDER (EnhancedYahooProvider)           │
│  • Yahoo Finance API (yfinance)                              │
│  • 40+ Technical Indicators (TA-Lib)                         │
│  • 20-minute caching                                         │
│  • Circuit breaker pattern                                   │
│  • Timeout protection (15s)                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 NARRATIVE ENGINE (LLM)                       │
│  • OpenAI GPT-4 / Anthropic Claude / Google Gemini          │
│  • Investment thesis generation                              │
│  • Key strengths/risks extraction                           │
│  • Professional-grade narratives                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Frontend** | User interface, visualization | React, TypeScript, TanStack Query |
| **API Layer** | HTTP endpoints, request handling | FastAPI, Uvicorn |
| **StockScorer** | Agent orchestration, score aggregation | Python |
| **Agents** | Specialized analysis (5 agents) | Python, pandas, numpy |
| **Data Provider** | Market data fetching, caching | yfinance, TA-Lib |
| **Narrative Engine** | Investment thesis generation | LLM APIs (OpenAI/Anthropic/Gemini) |
| **Market Regime** | Adaptive weight calculation | scikit-learn, pandas |

---

## Component Deep Dive

### 1. Data Provider (`data/enhanced_provider.py`)

**Purpose**: Fetch and cache comprehensive market data with 40+ technical indicators

**Key Features**:
- **Yahoo Finance Integration**: Uses `yfinance` library
- **20-Minute Caching**: Optimized for 50-stock universe
- **Circuit Breaker**: Prevents API overload (5 failures → open circuit for 60s)
- **Timeout Protection**: 15-second timeout on all API calls
- **Comprehensive Indicators**: 40+ TA-Lib indicators

**Technical Indicators Calculated**:
```python
# Momentum Indicators
- RSI (Relative Strength Index)
- Stochastic Oscillator (K, D)
- Williams %R
- CCI (Commodity Channel Index)
- ROC (Rate of Change)
- Momentum
- TRIX

# Trend Indicators
- SMA (20-day)
- EMA (12-day, 26-day)
- DEMA, TEMA, KAMA
- ADX (Average Directional Index)
- MACD + Signal + Histogram
- Aroon (Up, Down, Oscillator)
- PPO (Percentage Price Oscillator)

# Volatility Indicators
- ATR (Average True Range)
- NATR (Normalized ATR)
- Bollinger Bands (Upper, Middle, Lower)
- True Range

# Volume Indicators (Institutional Flow)
- OBV (On-Balance Volume)
- Accumulation/Distribution
- MFI (Money Flow Index)
- CMF (Chaikin Money Flow)
- VWAP (Volume Weighted Average Price)
- Volume Z-Score (spike detection)

# Pattern Recognition
- Doji, Hammer, Shooting Star
- Engulfing, Harami
- Morning Star, Evening Star
- Spinning Top
```

**Cache Strategy**:
```python
cache = {}
cache_expiry = {}
cache_duration = 1200  # 20 minutes

def _is_cached_data_fresh(symbol):
    if symbol not in cache or symbol not in cache_expiry:
        return False
    return datetime.now() < cache_expiry[symbol]
```

**Circuit Breaker Pattern**:
```python
States:
- CLOSED: Normal operation (requests go through)
- OPEN: Too many failures (reject immediately)
- HALF_OPEN: Testing recovery (allow limited requests)

Configuration:
- failure_threshold: 5 failures → open circuit
- recovery_timeout: 60 seconds before testing recovery
- half_open_max_calls: 3 test calls during recovery
```

**API Call Pattern**:
```python
def get_comprehensive_data(symbol: str) -> Dict:
    """
    Returns:
    {
        'symbol': str,
        'current_price': float,
        'price_change_percent': float,
        'market_cap': int,
        'sector': str,
        'historical_data': pd.DataFrame,  # 2 years OHLCV
        'technical_data': {
            'rsi': float,
            'macd': float,
            'obv': np.array,
            # ... 40+ indicators
        },
        'info': dict,  # Company info from yfinance
        'financials': pd.DataFrame,
        'quarterly_financials': pd.DataFrame,
        'data_completeness': {
            'has_financials': bool,
            'has_quarterly': bool,
            'has_info': bool,
            'has_historical': bool
        }
    }
    """
```

---

### 2. Five Specialized Agents

#### Agent 1: Fundamentals Agent (36% weight)
**File**: `agents/fundamentals_agent.py`

**Purpose**: Analyze financial health, profitability, growth, and valuation

**Metrics Analyzed**:
```python
# Profitability
- ROE (Return on Equity)
- ROA (Return on Assets)
- Net Profit Margin
- Operating Margin

# Growth
- Revenue Growth (YoY, QoQ)
- Earnings Growth
- EPS Growth

# Valuation
- P/E Ratio
- P/B Ratio
- PEG Ratio
- EV/EBITDA

# Financial Health
- Debt-to-Equity Ratio
- Current Ratio
- Free Cash Flow
```

**Scoring Logic**:
```python
def analyze(symbol: str, cached_data: Optional[Dict] = None) -> Dict:
    """
    Returns:
    {
        'score': 0-100,
        'confidence': 0-1,
        'reasoning': str,
        'metrics': {
            'roe': float,
            'pe_ratio': float,
            'revenue_growth': float,
            'debt_to_equity': float,
            # ... other metrics
        }
    }
    """

    score = 0

    # Profitability scoring (40 points)
    if roe > 20: score += 40
    elif roe > 15: score += 30
    elif roe > 10: score += 20
    elif roe > 5: score += 10

    # Growth scoring (30 points)
    if revenue_growth > 20: score += 30
    elif revenue_growth > 10: score += 20
    elif revenue_growth > 5: score += 10

    # Valuation scoring (20 points)
    if pe_ratio < 15: score += 20
    elif pe_ratio < 20: score += 15
    elif pe_ratio < 25: score += 10

    # Financial health (10 points)
    if debt_to_equity < 0.5: score += 10
    elif debt_to_equity < 1.0: score += 5

    return {'score': score, 'confidence': confidence, ...}
```

#### Agent 2: Momentum Agent (27% weight)
**File**: `agents/momentum_agent.py`

**Purpose**: Technical analysis and price trend evaluation

**Metrics Analyzed**:
```python
# Price Momentum
- 1M, 3M, 6M, 1Y Returns
- RSI (14-day)
- Relative Strength vs SPY

# Trend Analysis
- 20-day SMA
- 50-day SMA
- 200-day SMA
- Price vs Moving Averages

# Volatility
- 30-day Volatility
- Beta vs Market
```

**Scoring Logic**:
```python
def analyze(symbol: str, price_data: pd.DataFrame, spy_data: pd.DataFrame) -> Dict:
    score = 0

    # RSI scoring (25 points)
    if 50 < rsi < 70: score += 25  # Bullish but not overbought
    elif 40 < rsi <= 50: score += 15
    elif rsi >= 70: score += 10  # Overbought
    elif rsi < 30: score += 5   # Oversold

    # Trend scoring (35 points)
    if price > sma_20 > sma_50: score += 35  # Strong uptrend
    elif price > sma_20: score += 20
    elif price < sma_20 < sma_50: score -= 15  # Downtrend

    # Return scoring (30 points)
    if three_month_return > 10: score += 30
    elif three_month_return > 5: score += 20
    elif three_month_return > 0: score += 10

    # Relative strength (10 points)
    if rel_strength_vs_spy > 1.1: score += 10
    elif rel_strength_vs_spy > 1.0: score += 5

    return {'score': max(0, min(100, score)), ...}
```

#### Agent 3: Quality Agent (18% weight)
**File**: `agents/quality_agent.py`

**Purpose**: Business quality and operational efficiency assessment

**Metrics Analyzed**:
```python
# Business Model
- Sector classification
- Market position
- Competitive moat indicators

# Operational Efficiency
- Price stability (volatility)
- Volume consistency
- Market cap size

# Historical Performance
- Long-term price trend
- Drawdown analysis
```

**Scoring Logic**:
```python
def analyze(symbol: str, price_data: pd.DataFrame) -> Dict:
    score = 50  # Base score

    # Volatility scoring (lower = better quality)
    volatility = price_data['Close'].pct_change().std() * np.sqrt(252)
    if volatility < 0.20: score += 20
    elif volatility < 0.30: score += 10
    elif volatility > 0.50: score -= 20

    # Long-term trend (1-year)
    one_year_return = (current_price / price_1y_ago - 1) * 100
    if one_year_return > 20: score += 20
    elif one_year_return > 10: score += 10
    elif one_year_return < -20: score -= 20

    # Drawdown analysis
    max_drawdown = calculate_max_drawdown(price_data)
    if max_drawdown < -50: score -= 10

    return {'score': max(0, min(100, score)), ...}
```

#### Agent 4: Sentiment Agent (9% weight)
**File**: `agents/sentiment_agent.py`

**Purpose**: Market sentiment and analyst outlook analysis

**Data Sources**:
```python
# Analyst Ratings (yfinance)
- Recommendation Mean (1=Strong Buy, 5=Sell)
- Number of Analysts
- Target Price vs Current Price

# Optional: News Sentiment (LLM-powered)
- Recent news headlines
- Sentiment analysis via GPT/Claude/Gemini
- Confidence scoring
```

**Scoring Logic**:
```python
def analyze(symbol: str, cached_data: Optional[Dict] = None) -> Dict:
    score = 50  # Neutral baseline

    # Analyst recommendation scoring (70% weight)
    recommendation_mean = info.get('recommendationMean')
    if recommendation_mean < 2.0: score += 35  # Strong Buy/Buy
    elif recommendation_mean < 2.5: score += 25
    elif recommendation_mean < 3.0: score += 10
    elif recommendation_mean > 4.0: score -= 35  # Sell

    # Target price vs current (30% weight)
    target_price = info.get('targetMeanPrice')
    current_price = info.get('currentPrice')
    upside = (target_price / current_price - 1) * 100

    if upside > 20: score += 15
    elif upside > 10: score += 10
    elif upside < -10: score -= 15

    # Optional LLM sentiment analysis
    if enable_llm and news_available:
        news_sentiment = analyze_news_sentiment_with_llm()
        score = score * 0.75 + news_sentiment * 0.25

    return {'score': max(0, min(100, score)), ...}
```

#### Agent 5: Institutional Flow Agent (10% weight)
**File**: `agents/institutional_flow_agent.py`

**Purpose**: Detect institutional buying/selling patterns ("smart money")

**Metrics Analyzed**:
```python
# Volume Flow Trends
- OBV (On-Balance Volume) trend
- Accumulation/Distribution trend
- 20-day OBV trend slope

# Money Flow Indicators
- MFI (Money Flow Index)
- CMF (Chaikin Money Flow)

# Volume Analysis
- Volume Z-Score (spike detection)
- Volume trend (20-day average)

# VWAP Analysis
- Price vs VWAP positioning
- VWAP trend
```

**Scoring Logic**:
```python
def analyze(symbol: str, price_data: pd.DataFrame, cached_data: Optional[Dict] = None) -> Dict:
    score = 50  # Neutral baseline

    # OBV trend analysis (30 points)
    obv_trend = calculate_trend(obv_array[-20:])
    if obv_trend > 0.15: score += 30  # Strong accumulation
    elif obv_trend > 0.05: score += 15
    elif obv_trend < -0.15: score -= 30  # Distribution

    # MFI analysis (25 points)
    if 60 < mfi < 80: score += 25  # Strong buying pressure
    elif 50 < mfi <= 60: score += 15
    elif mfi > 80: score += 10  # Overbought
    elif mfi < 30: score -= 15  # Weak

    # CMF analysis (20 points)
    if cmf > 0.15: score += 20  # Strong accumulation
    elif cmf > 0.05: score += 10
    elif cmf < -0.15: score -= 20  # Distribution

    # Volume spike detection (15 points)
    volume_zscore = calculate_volume_zscore()
    if volume_zscore > 2: score += 15  # Unusual activity

    # VWAP positioning (10 points)
    if price > vwap and vwap_trending_up: score += 10
    elif price < vwap and vwap_trending_down: score -= 10

    return {'score': max(0, min(100, score)), ...}
```

---

### 3. Stock Scorer Orchestration (`core/stock_scorer.py`)

**Purpose**: Coordinate all 5 agents and calculate composite score

**Agent Weights**:
```python
# Static Weights (Default)
STATIC_AGENT_WEIGHTS = {
    'fundamentals': 0.36,      # 36%
    'momentum': 0.27,          # 27%
    'quality': 0.18,           # 18%
    'sentiment': 0.09,         # 9%
    'institutional_flow': 0.10 # 10%
}

# Adaptive Weights (Market Regime-Based)
# Bull + Normal Vol: 36/27/18/9/10 (balanced)
# Bull + High Vol: 27/36/18/9/10 (momentum-focused)
# Bear + High Vol: 18/18/36/18/10 (quality & safety-focused)
# Bear + Normal Vol: 27/18/27/18/10 (fundamentals & quality)
```

**Scoring Flow**:
```python
def score_stock(symbol: str) -> Dict:
    # 1. Get current weights (adaptive or static)
    weights = _get_current_weights()

    # 2. Fetch comprehensive data (cached if fresh)
    cached_data = data_provider.get_comprehensive_data(symbol)

    # 3. Run all 5 agents
    fund_result = fundamentals_agent.analyze(symbol, cached_data)
    mom_result = momentum_agent.analyze(symbol, price_data, spy_data)
    qual_result = quality_agent.analyze(symbol, price_data)
    sent_result = sentiment_agent.analyze(symbol, cached_data)
    flow_result = institutional_flow_agent.analyze(symbol, price_data, cached_data)

    # 4. Calculate weighted composite score
    composite_score = (
        weights['fundamentals'] * fund_result['score'] +
        weights['momentum'] * mom_result['score'] +
        weights['quality'] * qual_result['score'] +
        weights['sentiment'] * sent_result['score'] +
        weights['institutional_flow'] * flow_result['score']
    )

    # 5. Calculate composite confidence
    composite_confidence = (
        weights['fundamentals'] * fund_result['confidence'] +
        weights['momentum'] * mom_result['confidence'] +
        weights['quality'] * qual_result['confidence'] +
        weights['sentiment'] * sent_result['confidence'] +
        weights['institutional_flow'] * flow_result['confidence']
    )

    # 6. Determine recommendation
    recommendation = _get_recommendation(composite_score, composite_confidence)

    return {
        'symbol': symbol,
        'composite_score': composite_score,
        'composite_confidence': composite_confidence,
        'recommendation': recommendation,
        'agent_scores': {...},
        'weights_used': weights
    }
```

---

### 4. Narrative Engine (`narrative_engine/narrative_engine.py`)

**Purpose**: Convert quantitative scores into human-readable investment theses

**LLM Integration**:
```python
# Supported LLM Providers
1. Google Gemini (default, free tier available)
2. OpenAI GPT-4
3. Anthropic Claude 3

# Environment Variables
LLM_PROVIDER=gemini  # or openai, anthropic
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

**Narrative Generation Flow**:
```python
def generate_comprehensive_thesis(symbol: str, agent_results: Dict) -> Dict:
    # 1. Calculate overall score
    overall_score = calculate_weighted_score(agent_results)

    # 2. Generate rule-based narratives (backup)
    agent_narratives = {
        'fundamentals': _generate_fundamentals_narrative(),
        'momentum': _generate_momentum_narrative(),
        'quality': _generate_quality_narrative(),
        'sentiment': _generate_sentiment_narrative()
    }

    # 3. Generate LLM-powered thesis (if enabled)
    if llm_enabled:
        investment_thesis = _generate_llm_thesis(symbol, agent_results)
    else:
        investment_thesis = _generate_rule_based_thesis()

    # 4. Extract strengths and risks
    strengths, risks = _extract_strengths_and_risks(agent_results)

    # 5. Determine recommendation
    recommendation = _get_recommendation(overall_score)

    return {
        'symbol': symbol,
        'investment_thesis': investment_thesis,
        'key_strengths': strengths,
        'key_risks': risks,
        'recommendation': recommendation,
        'confidence_level': confidence_level,
        'overall_score': overall_score,
        'agent_narratives': agent_narratives
    }
```

**LLM Prompt Template**:
```python
prompt = f"""
Generate a comprehensive investment thesis for {company_name} ({symbol})
based on our 5-agent quantitative analysis.

OVERALL SCORE: {overall_score:.1f}/100

AGENT ANALYSIS BREAKDOWN:
• Fundamentals Agent (36% weight): {fund_score}/100
• Momentum Agent (27% weight): {mom_score}/100
• Quality Agent (18% weight): {qual_score}/100
• Sentiment Agent (9% weight): {sent_score}/100
• Institutional Flow Agent (10% weight): {flow_score}/100

DETAILED METRICS: {json.dumps(metrics)}

Please provide a sophisticated investment thesis that includes:

1. EXECUTIVE SUMMARY (2-3 sentences)
2. QUANTITATIVE ASSESSMENT
3. FUNDAMENTAL ANALYSIS
4. TECHNICAL & MOMENTUM FACTORS
5. RISK ASSESSMENT
6. INVESTMENT RECOMMENDATION

Write in a professional, analytical tone suitable for institutional investors.
"""
```

---

### 5. Market Regime Detection (`core/market_regime_service.py`)

**Purpose**: Detect market regime and adjust agent weights adaptively

**Regime Classification**:
```python
# Trend Analysis (using SPY)
- BULL: 50-day SMA > 200-day SMA, price > 50-day SMA
- BEAR: 50-day SMA < 200-day SMA, price < 50-day SMA
- SIDEWAYS: Neither bull nor bear

# Volatility Analysis
- HIGH_VOL: 30-day volatility > 25%
- NORMAL_VOL: 15% < volatility <= 25%
- LOW_VOL: volatility <= 15%

# Combined Regime
regime = f"{trend}_{volatility}"
# Examples: "BULL_NORMAL", "BEAR_HIGH", "SIDEWAYS_LOW"
```

**Adaptive Weight Mapping**:
```python
ADAPTIVE_WEIGHTS_MAP = {
    'BULL_NORMAL': {
        'fundamentals': 0.36,
        'momentum': 0.27,
        'quality': 0.18,
        'sentiment': 0.09,
        'institutional_flow': 0.10
    },
    'BULL_HIGH': {
        'fundamentals': 0.27,
        'momentum': 0.36,  # Increase momentum in volatile bull markets
        'quality': 0.18,
        'sentiment': 0.09,
        'institutional_flow': 0.10
    },
    'BEAR_HIGH': {
        'fundamentals': 0.18,
        'momentum': 0.18,
        'quality': 0.36,  # Increase quality in volatile bear markets
        'sentiment': 0.18,
        'institutional_flow': 0.10
    },
    'BEAR_NORMAL': {
        'fundamentals': 0.27,
        'momentum': 0.18,
        'quality': 0.27,
        'sentiment': 0.18,
        'institutional_flow': 0.10
    }
}
```

**Caching Strategy**:
```python
# Regime is cached for 6 hours
cache_duration = 6 * 60 * 60  # 21600 seconds

# Auto-refresh when cache expires
if cache_expired:
    regime = detect_market_regime()
    cache_regime(regime, cache_duration)
```

---

## Data Flow

### Complete Analysis Flow

```
1. USER REQUEST
   Frontend → POST /analyze {"symbol": "AAPL"}

2. API LAYER
   FastAPI receives request
   Check analysis_cache (TTL: 15 minutes)
   If cached → return immediately
   If not cached → proceed

3. STOCK SCORER
   Initialize with adaptive/static weights
   Call data_provider.get_comprehensive_data("AAPL")

4. DATA PROVIDER
   Check cache (TTL: 20 minutes)
   If cached → return immediately
   If not cached:
     - Fetch from Yahoo Finance (with timeout & circuit breaker)
     - Calculate 40+ technical indicators
     - Cache result
     - Return comprehensive data

5. AGENT ORCHESTRATION
   Run 5 agents in parallel:
     - FundamentalsAgent.analyze()
     - MomentumAgent.analyze()
     - QualityAgent.analyze()
     - SentimentAgent.analyze()
     - InstitutionalFlowAgent.analyze()

6. SCORE CALCULATION
   Get current weights (adaptive or static)
   composite_score = Σ(weight[i] * agent_score[i])
   composite_confidence = Σ(weight[i] * agent_confidence[i])

7. NARRATIVE GENERATION
   Generate investment thesis using LLM (if enabled)
   Extract key strengths and risks
   Determine recommendation

8. RESPONSE ASSEMBLY
   Combine all results into comprehensive response
   Cache result in analysis_cache
   Return JSON to frontend

9. FRONTEND DISPLAY
   Render analysis results
   Display agent scores
   Show investment thesis
   Visualize trends
```

### Caching Layers

```
Layer 1: Frontend Query Cache (React Query)
- Duration: 5 minutes
- Scope: Client-side
- Purpose: Avoid redundant API calls

Layer 2: API Analysis Cache (In-Memory)
- Duration: 15 minutes
- Scope: Server-side
- Purpose: Fast response for repeated requests

Layer 3: Data Provider Cache (In-Memory)
- Duration: 20 minutes
- Scope: Data layer
- Purpose: Avoid redundant Yahoo Finance calls

Layer 4: Market Regime Cache (In-Memory)
- Duration: 6 hours
- Scope: Market regime service
- Purpose: Reduce SPY analysis overhead
```

---

## Indian Market Adaptation

### Key Differences: US vs Indian Market

| Aspect | US Market | Indian Market (NSE/BSE) |
|--------|-----------|------------------------|
| **Data Provider** | Yahoo Finance (yfinance) | NSE API, BSE API, NSEpy, yfinance (limited) |
| **Stock Symbols** | AAPL, MSFT, GOOGL | RELIANCE.NS, TCS.NS, HDFCBANK.NS |
| **Market Index** | SPY (S&P 500) | NIFTY50, SENSEX |
| **Technical Indicators** | Full TA-Lib support | Same TA-Lib support ✓ |
| **Trading Hours** | 9:30 AM - 4:00 PM ET | 9:15 AM - 3:30 PM IST |
| **Currency** | USD | INR |
| **Analyst Ratings** | Abundant via yfinance | Limited, may need alternate source |
| **News Sources** | English, plentiful | English + Hindi, fragmented |
| **Corporate Actions** | Standard | Bonus issues, rights issues (more frequent) |
| **Market Holidays** | US calendar | Indian calendar (Diwali, Holi, etc.) |

### Required Adaptations

#### 1. Data Provider Replacement

**Option A: NSEpy (Recommended for beginners)**
```python
# Replace: data/enhanced_provider.py
from nsepy import get_history
from datetime import datetime

class EnhancedNSEProvider:
    def get_comprehensive_data(self, symbol: str) -> Dict:
        # NSEpy uses different symbol format
        # Example: "RELIANCE" not "RELIANCE.NS"

        # Get historical data
        start = datetime.now() - timedelta(days=730)  # 2 years
        end = datetime.now()

        df = get_history(
            symbol=symbol,
            start=start,
            end=end,
            index=False  # For stocks (True for indices)
        )

        # Calculate technical indicators (TA-Lib works same way)
        technical_data = self._calculate_all_indicators(df)

        return {
            'symbol': symbol,
            'historical_data': df,
            'technical_data': technical_data,
            # ... rest of the structure
        }
```

**Option B: Yahoo Finance (Limited support for Indian stocks)**
```python
# Modify: data/enhanced_provider.py
# Use .NS suffix for NSE stocks
symbol_with_suffix = f"{symbol}.NS"  # or .BO for BSE

data = yf.download(symbol_with_suffix, period='2y')
```

**Option C: Official NSE API (Professional)**
```python
# Requires API credentials from NSE
import requests

class NSEAPIProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.nseindia.com/api"

    def get_quote(self, symbol: str):
        url = f"{self.base_url}/quote-equity?symbol={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        return response.json()
```

**Option D: Third-party APIs**
```python
# Paid services with better data quality
# 1. AlphaVantage (has India support)
# 2. Polygon.io (limited India coverage)
# 3. Quandl (via Nasdaq Data Link)
# 4. Financial Modeling Prep
```

#### 2. Stock Universe (Top 50 NSE Stocks)

```python
# Replace: data/us_top_100_stocks.py
# With: data/nse_top_50_stocks.py

NIFTY_TOP_50_STOCKS = [
    # Technology (8 stocks)
    'TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM', 'LTI', 'COFORGE', 'PERSISTENT',

    # Financial (12 stocks)
    'HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'SBIN', 'AXISBANK',
    'BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE', 'ICICIGI',
    'HDFCAMC', 'INDUSINDBK',

    # Consumer (8 stocks)
    'RELIANCE', 'BHARTIARTL', 'HINDUNILVR', 'ITC', 'NESTLEIND',
    'TITAN', 'ASIANPAINT', 'MARUTI',

    # Energy (4 stocks)
    'ONGC', 'BPCL', 'IOC', 'POWERGRID',

    # Healthcare (4 stocks)
    'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB',

    # Industrials (6 stocks)
    'LT', 'ULTRACEMCO', 'ADANIPORTS', 'TATASTEEL', 'HINDALCO', 'JSWSTEEL',

    # Materials (4 stocks)
    'TATAMOTORS', 'M&M', 'HEROMOTOCO', 'BAJAJ-AUTO',

    # Infrastructure (4 stocks)
    'NTPC', 'COALINDIA', 'GRASIM', 'ADANIENT'
]

# NSE symbols don't need suffix when using NSEpy
# But need .NS suffix for yfinance
def get_yahoo_symbol(nse_symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance format"""
    return f"{nse_symbol}.NS"
```

#### 3. Market Index (Replace SPY with NIFTY50)

```python
# In all agents where SPY is used, replace with NIFTY50

# Before (US):
spy_data = yf.download('SPY', period='2y')

# After (India):
nifty_data = yf.download('^NSEI', period='2y')  # NIFTY 50
# OR
sensex_data = yf.download('^BSESN', period='2y')  # SENSEX

# OR using NSEpy:
from nsepy import get_history

nifty_data = get_history(
    symbol="NIFTY",
    start=start_date,
    end=end_date,
    index=True  # Important: True for indices
)
```

#### 4. Fundamentals Agent Adaptation

**Challenge**: Indian financial data may have different formats

```python
# Modify: agents/fundamentals_agent.py

def analyze(self, symbol: str, cached_data: Optional[Dict] = None) -> Dict:
    # Indian-specific considerations:

    # 1. Adjust ROE benchmarks (Indian companies typically have lower ROE)
    if roe > 15:  # vs 20 in US
        score += 40
    elif roe > 12:  # vs 15 in US
        score += 30

    # 2. Adjust P/E benchmarks (Indian market typically trades at lower multiples)
    if pe_ratio < 12:  # vs 15 in US
        score += 20
    elif pe_ratio < 18:  # vs 20 in US
        score += 15

    # 3. Consider Indian-specific metrics
    # - Promoter holding (higher = better governance)
    # - FII/DII ownership
    # - Pledge percentage (lower = better)

    promoter_holding = info.get('promoterHolding', 0)
    if promoter_holding > 50:
        score += 5  # Bonus for high promoter confidence

    return {'score': score, ...}
```

#### 5. Sentiment Agent Adaptation

**Challenge**: Limited analyst coverage, language barriers

```python
# Modify: agents/sentiment_agent.py

def analyze(self, symbol: str, cached_data: Optional[Dict] = None) -> Dict:
    # Option 1: Use yfinance (limited coverage)
    info = cached_data.get('info', {})
    recommendation_mean = info.get('recommendationMean')

    # Option 2: Scrape Indian sources
    sources = [
        'https://www.moneycontrol.com/',
        'https://economictimes.indiatimes.com/',
        'https://www.livemint.com/'
    ]

    # Option 3: Use LLM for Hindi + English news
    if llm_enabled:
        news_sentiment = self._analyze_indian_news_sentiment(symbol)

    # Option 4: Use Telegram/WhatsApp trading groups (advanced)
    # sentiment = scrape_social_sentiment(symbol)

    return {'score': score, ...}
```

#### 6. Currency and Number Formatting

```python
# Modify: All display logic

# Before (US):
f"${price:.2f}"
f"Market Cap: ${market_cap/1e9:.2f}B"

# After (India):
f"₹{price:.2f}"
f"Market Cap: ₹{market_cap/1e7:.2f} Cr"  # Crores

# Helper function
def format_indian_currency(amount: float) -> str:
    """Format amount in Crores/Lakhs"""
    if amount >= 1e7:  # Crores
        return f"₹{amount/1e7:.2f} Cr"
    elif amount >= 1e5:  # Lakhs
        return f"₹{amount/1e5:.2f} L"
    else:
        return f"₹{amount:.2f}"
```

#### 7. Trading Hours and Timezone

```python
# Modify: core/buy_queue_manager.py and api/main.py

# Before (US):
import pytz
ET = pytz.timezone('US/Eastern')
MARKET_CLOSE = time(16, 0)  # 4 PM ET

# After (India):
IST = pytz.timezone('Asia/Kolkata')
MARKET_CLOSE = time(15, 30)  # 3:30 PM IST
MARKET_OPEN = time(9, 15)    # 9:15 AM IST

# Check if market is open
def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() > 4:  # Weekend
        return False
    if is_market_holiday(now.date()):  # Check Indian holidays
        return False
    current_time = now.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE
```

#### 8. Market Holidays

```python
# Add: utils/indian_market_calendar.py

INDIAN_MARKET_HOLIDAYS_2024 = [
    date(2024, 1, 26),  # Republic Day
    date(2024, 3, 8),   # Maha Shivaratri
    date(2024, 3, 25),  # Holi
    date(2024, 3, 29),  # Good Friday
    date(2024, 4, 11),  # Id-Ul-Fitr
    date(2024, 4, 17),  # Ram Navami
    date(2024, 4, 21),  # Mahavir Jayanti
    date(2024, 5, 1),   # Maharashtra Day
    date(2024, 6, 17),  # Eid-ul-Adha
    date(2024, 8, 15),  # Independence Day
    date(2024, 10, 2),  # Gandhi Jayanti
    date(2024, 11, 1),  # Diwali Laxmi Pujan
    date(2024, 11, 15), # Gurunanak Jayanti
    date(2024, 12, 25), # Christmas
]

def is_market_holiday(check_date: date) -> bool:
    return check_date in INDIAN_MARKET_HOLIDAYS_2024
```

---

## Step-by-Step Implementation

### Phase 1: Environment Setup (Day 1-2)

#### 1.1 Install Python Dependencies
```bash
# Create project directory
mkdir ai_hedge_fund_india
cd ai_hedge_fund_india

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies
pip install pandas numpy scipy
pip install yfinance nsepy  # Both data providers
pip install talib-binary    # Technical indicators
pip install fastapi uvicorn pydantic
pip install requests aiohttp httpx
pip install scikit-learn
pip install python-dotenv pytz
pip install cachetools psutil

# Optional: LLM support
pip install openai anthropic google-generativeai

# Development tools
pip install pytest black isort flake8
```

#### 1.2 Install System Dependencies (TA-Lib)
```bash
# macOS
brew install ta-lib

# Ubuntu/Debian
sudo apt-get install ta-lib

# Windows
# Download from: https://github.com/mrjbq7/ta-lib
# Follow installation instructions
```

#### 1.3 Setup Frontend
```bash
# Install Node.js (v18 or higher)
# Download from: https://nodejs.org/

# Create React + TypeScript project
npx create-vite@latest frontend --template react-ts
cd frontend

# Install dependencies
npm install @tanstack/react-query axios zustand
npm install @radix-ui/react-dialog @radix-ui/react-select
npm install recharts lucide-react
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p

npm install
cd ..
```

### Phase 2: Data Layer (Day 3-5)

#### 2.1 Create Data Provider

**File**: `data/nse_provider.py`

```python
"""
NSE Data Provider for Indian Stock Market
Comprehensive stock data collection with technical indicators
"""

import pandas as pd
import numpy as np
import talib
from nsepy import get_history
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)

class EnhancedNSEProvider:
    """Enhanced data provider for NSE stocks"""

    def __init__(self, cache_duration: int = 1200):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = cache_duration  # 20 minutes
        self.rate_limit_delay = 0.5  # 500ms between requests

    def get_comprehensive_data(self, symbol: str) -> Dict:
        """Get comprehensive stock data with technical indicators"""

        # Check cache
        if self._is_cached_data_fresh(symbol):
            logger.info(f"Using cached data for {symbol}")
            return self.cache[symbol]

        try:
            logger.info(f"Fetching fresh data for {symbol}")

            # Get 2 years of historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)

            # Fetch from NSEpy
            hist = get_history(
                symbol=symbol,
                start=start_date,
                end=end_date,
                index=False
            )

            if hist.empty:
                logger.warning(f"No historical data found for {symbol}")
                return self._create_empty_data(symbol)

            # Standardize column names to match yfinance
            hist = hist.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })

            # Calculate technical indicators
            technical_data = self._calculate_all_indicators(hist)

            # Get current price data
            current_data = self._get_current_price_data(hist)

            # Combine all data
            comprehensive_data = {
                **current_data,
                **technical_data,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'historical_data': hist,
                'technical_data': technical_data,
                'data_completeness': {
                    'has_historical': not hist.empty,
                    'has_financials': False,  # NSEpy doesn't provide financials
                    'has_quarterly': False,
                    'has_info': False
                }
            }

            # Cache the data
            self.cache[symbol] = comprehensive_data
            self.cache_expiry[symbol] = datetime.now() + timedelta(seconds=self.cache_duration)

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            return comprehensive_data

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return self._create_error_data(symbol, str(e))

    def _calculate_all_indicators(self, hist: pd.DataFrame) -> Dict:
        """Calculate comprehensive technical indicators"""

        if len(hist) < 14:
            logger.warning(f"Insufficient data for indicators: {len(hist)} days")
            return self._create_empty_indicators()

        try:
            # Convert to numpy arrays
            close = hist['Close'].values.astype(np.float64)
            high = hist['High'].values.astype(np.float64)
            low = hist['Low'].values.astype(np.float64)
            volume = hist['Volume'].values.astype(np.float64)

            # Momentum Indicators
            rsi = talib.RSI(close, timeperiod=14)
            stoch_k, stoch_d = talib.STOCH(high, low, close)
            williams_r = talib.WILLR(high, low, close, timeperiod=14)

            # Trend Indicators
            sma_20 = talib.SMA(close, timeperiod=20)
            ema_12 = talib.EMA(close, timeperiod=12)
            ema_26 = talib.EMA(close, timeperiod=26)

            # MACD
            macd, macd_signal, macd_histogram = talib.MACD(close)

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20)

            # Volume Indicators (for Institutional Flow Agent)
            obv = talib.OBV(close, volume)
            ad = talib.AD(high, low, close, volume)
            mfi = talib.MFI(high, low, close, volume, timeperiod=14)

            # Chaikin Money Flow
            cmf = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)

            # VWAP calculation
            vwap = self._calculate_vwap(high, low, close, volume)

            # Volume Z-score
            volume_zscore = self._calculate_volume_zscore(volume)

            return {
                # Momentum
                'rsi': round(float(rsi[-1]), 2) if not np.isnan(rsi[-1]) else None,
                'stoch_k': round(float(stoch_k[-1]), 2) if not np.isnan(stoch_k[-1]) else None,
                'stoch_d': round(float(stoch_d[-1]), 2) if not np.isnan(stoch_d[-1]) else None,
                'williams_r': round(float(williams_r[-1]), 2) if not np.isnan(williams_r[-1]) else None,

                # Trend
                'sma_20': round(float(sma_20[-1]), 2) if not np.isnan(sma_20[-1]) else None,
                'ema_12': round(float(ema_12[-1]), 2) if not np.isnan(ema_12[-1]) else None,
                'ema_26': round(float(ema_26[-1]), 2) if not np.isnan(ema_26[-1]) else None,

                # MACD
                'macd': round(float(macd[-1]), 4) if not np.isnan(macd[-1]) else None,
                'macd_signal': round(float(macd_signal[-1]), 4) if not np.isnan(macd_signal[-1]) else None,
                'macd_histogram': round(float(macd_histogram[-1]), 4) if not np.isnan(macd_histogram[-1]) else None,

                # Bollinger Bands
                'bb_upper': round(float(bb_upper[-1]), 2) if not np.isnan(bb_upper[-1]) else None,
                'bb_middle': round(float(bb_middle[-1]), 2) if not np.isnan(bb_middle[-1]) else None,
                'bb_lower': round(float(bb_lower[-1]), 2) if not np.isnan(bb_lower[-1]) else None,

                # Volume indicators
                'obv': obv,
                'ad': ad,
                'mfi': mfi,
                'cmf': cmf,
                'vwap': vwap,
                'volume_zscore': volume_zscore
            }

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return self._create_empty_indicators()

    # ... (copy other helper methods from original EnhancedYahooProvider)
    # _get_current_price_data()
    # _calculate_vwap()
    # _calculate_volume_zscore()
    # _is_cached_data_fresh()
    # _create_empty_data()
    # _create_error_data()
    # _create_empty_indicators()
```

#### 2.2 Create Stock Universe

**File**: `data/nse_top_50_stocks.py`

```python
"""
NSE Top 50 Stocks List
Elite Indian stocks from NIFTY 50
"""

from typing import List, Dict

# Top 50 NSE stocks across sectors
NIFTY_TOP_50_STOCKS = [
    # Technology (8 stocks - 16%)
    'TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM', 'LTI', 'COFORGE', 'PERSISTENT',

    # Financial Services (12 stocks - 24%)
    'HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'SBIN', 'AXISBANK',
    'BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE', 'ICICIGI',
    'HDFCAMC', 'INDUSINDBK',

    # Consumer & Retail (8 stocks - 16%)
    'RELIANCE', 'BHARTIARTL', 'HINDUNILVR', 'ITC', 'NESTLEIND',
    'TITAN', 'ASIANPAINT', 'MARUTI',

    # Energy & Utilities (4 stocks - 8%)
    'ONGC', 'BPCL', 'IOC', 'POWERGRID',

    # Healthcare & Pharma (4 stocks - 8%)
    'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB',

    # Industrials & Infrastructure (6 stocks - 12%)
    'LT', 'ULTRACEMCO', 'ADANIPORTS', 'TATASTEEL', 'HINDALCO', 'JSWSTEEL',

    # Auto & Auto Components (4 stocks - 8%)
    'TATAMOTORS', 'M&M', 'HEROMOTOCO', 'BAJAJ-AUTO',

    # Metals & Mining (4 stocks - 8%)
    'NTPC', 'COALINDIA', 'GRASIM', 'ADANIENT'
]

# Sector classifications
SECTOR_MAPPING = {
    'Technology': ['TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM', 'LTI', 'COFORGE', 'PERSISTENT'],
    'Financial Services': ['HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'SBIN', 'AXISBANK',
                           'BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE', 'ICICIGI',
                           'HDFCAMC', 'INDUSINDBK'],
    'Consumer': ['RELIANCE', 'BHARTIARTL', 'HINDUNILVR', 'ITC', 'NESTLEIND',
                 'TITAN', 'ASIANPAINT', 'MARUTI'],
    'Energy': ['ONGC', 'BPCL', 'IOC', 'POWERGRID'],
    'Healthcare': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB'],
    'Industrial': ['LT', 'ULTRACEMCO', 'ADANIPORTS', 'TATASTEEL', 'HINDALCO', 'JSWSTEEL'],
    'Auto': ['TATAMOTORS', 'M&M', 'HEROMOTOCO', 'BAJAJ-AUTO'],
    'Materials': ['NTPC', 'COALINDIA', 'GRASIM', 'ADANIENT']
}

def get_nifty_50() -> List[str]:
    """Get all NIFTY 50 stock symbols"""
    return NIFTY_TOP_50_STOCKS.copy()

def get_stocks_by_sector(sector: str) -> List[str]:
    """Get stocks by sector"""
    return SECTOR_MAPPING.get(sector, [])

def get_yahoo_symbol(nse_symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance format"""
    return f"{nse_symbol}.NS"
```

### Phase 3: Agent Implementation (Day 6-10)

#### 3.1 Copy and Modify Fundamentals Agent

**File**: `agents/fundamentals_agent.py`

```python
"""
Fundamentals Agent - Indian Market Version
Analyzes financial health, profitability, growth, and valuation
"""

class FundamentalsAgent:
    """Analyzes fundamental financial metrics for Indian stocks"""

    def analyze(self, symbol: str, cached_data: Optional[Dict] = None) -> Dict:
        """
        Analyze fundamental metrics

        Returns:
            {
                'score': 0-100,
                'confidence': 0-1,
                'reasoning': str,
                'metrics': dict
            }
        """

        try:
            # Get financial data
            # Note: NSEpy doesn't provide financials directly
            # Options:
            # 1. Use yfinance with .NS suffix
            # 2. Scrape from MoneyControl/Screener.in
            # 3. Use paid API (Financial Modeling Prep, etc.)

            # For now, use yfinance as fallback
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.info

            # Extract metrics
            roe = info.get('returnOnEquity', 0) * 100
            pe_ratio = info.get('trailingPE', 0)
            pb_ratio = info.get('priceToBook', 0)
            debt_to_equity = info.get('debtToEquity', 0) / 100

            # Revenue growth (if available)
            revenue_growth = info.get('revenueGrowth', 0) * 100

            # Scoring (adjusted for Indian market)
            score = 0

            # Profitability (40 points) - Lower benchmarks for India
            if roe > 15:
                score += 40
            elif roe > 12:
                score += 30
            elif roe > 8:
                score += 20
            elif roe > 5:
                score += 10

            # Valuation (30 points) - Lower multiples for India
            if 0 < pe_ratio < 12:
                score += 30
            elif pe_ratio < 18:
                score += 20
            elif pe_ratio < 25:
                score += 10

            # Growth (20 points)
            if revenue_growth > 20:
                score += 20
            elif revenue_growth > 10:
                score += 15
            elif revenue_growth > 5:
                score += 10

            # Financial Health (10 points)
            if debt_to_equity < 0.5:
                score += 10
            elif debt_to_equity < 1.0:
                score += 5

            # Calculate confidence based on data availability
            confidence = 0.8  # Assume moderate confidence
            if info.get('financialCurrency') == 'INR':
                confidence = 0.9  # Higher if data is in INR

            reasoning = f"ROE: {roe:.1f}%, P/E: {pe_ratio:.1f}, Revenue Growth: {revenue_growth:.1f}%"

            return {
                'score': max(0, min(100, score)),
                'confidence': confidence,
                'reasoning': reasoning,
                'metrics': {
                    'roe': roe,
                    'pe_ratio': pe_ratio,
                    'pb_ratio': pb_ratio,
                    'debt_to_equity': debt_to_equity,
                    'revenue_growth': revenue_growth
                }
            }

        except Exception as e:
            logger.error(f"Fundamentals analysis failed for {symbol}: {e}")
            return {
                'score': 50,
                'confidence': 0.1,
                'reasoning': f"Analysis failed: {str(e)}",
                'metrics': {}
            }
```

#### 3.2 Modify Momentum Agent

**File**: `agents/momentum_agent.py`

```python
"""
Momentum Agent - Indian Market Version
Technical analysis and price trend evaluation
"""

class MomentumAgent:
    """Analyzes technical momentum and price trends for Indian stocks"""

    def analyze(self, symbol: str, price_data: pd.DataFrame,
                nifty_data: pd.DataFrame) -> Dict:
        """
        Analyze momentum metrics

        Args:
            symbol: Stock symbol
            price_data: Historical price data
            nifty_data: NIFTY 50 index data for relative strength
        """

        try:
            # Same logic as US version, just replace SPY with NIFTY

            # Calculate returns
            current_price = price_data['Close'].iloc[-1]
            price_1m_ago = price_data['Close'].iloc[-20] if len(price_data) > 20 else current_price
            price_3m_ago = price_data['Close'].iloc[-60] if len(price_data) > 60 else current_price

            one_month_return = (current_price / price_1m_ago - 1) * 100
            three_month_return = (current_price / price_3m_ago - 1) * 100

            # RSI from cached data
            rsi = cached_data.get('technical_data', {}).get('rsi', 50)

            # SMA from cached data
            sma_20 = cached_data.get('technical_data', {}).get('sma_20', current_price)

            # Relative strength vs NIFTY
            nifty_current = nifty_data['Close'].iloc[-1]
            nifty_3m_ago = nifty_data['Close'].iloc[-60] if len(nifty_data) > 60 else nifty_current
            nifty_return = (nifty_current / nifty_3m_ago - 1) * 100

            rel_strength = three_month_return - nifty_return

            # Scoring (same as US version)
            score = 0

            # RSI scoring (25 points)
            if 50 < rsi < 70:
                score += 25
            elif 40 < rsi <= 50:
                score += 15
            # ... rest of scoring logic

            return {
                'score': score,
                'confidence': 0.9,
                'reasoning': f"RSI: {rsi:.1f}, 3M Return: {three_month_return:.1f}%",
                'metrics': {
                    '1m_return': one_month_return,
                    '3m_return': three_month_return,
                    'rsi': rsi,
                    'rel_strength_vs_nifty': rel_strength
                }
            }

        except Exception as e:
            logger.error(f"Momentum analysis failed for {symbol}: {e}")
            return {'score': 50, 'confidence': 0.1, 'reasoning': str(e), 'metrics': {}}
```

#### 3.3 Copy Quality, Sentiment, and Institutional Flow Agents

Copy the remaining agents from the US version with minimal modifications:

- `agents/quality_agent.py` - No changes needed (generic)
- `agents/sentiment_agent.py` - May need to adapt for limited analyst coverage
- `agents/institutional_flow_agent.py` - No changes needed (technical indicators work same way)

### Phase 4: Orchestration Layer (Day 11-12)

#### 4.1 Stock Scorer

**File**: `core/stock_scorer.py`

```python
"""
Stock Scorer - Indian Market Version
Orchestrates all agents and combines their scores
"""

from agents import FundamentalsAgent, MomentumAgent, QualityAgent, SentimentAgent
from agents.institutional_flow_agent import InstitutionalFlowAgent
from data.nse_provider import EnhancedNSEProvider

class StockScorer:
    """Combines all agent scores to rank stocks"""

    def __init__(self, sector_mapping: Optional[Dict] = None):
        self.fundamentals_agent = FundamentalsAgent()
        self.momentum_agent = MomentumAgent()
        self.quality_agent = QualityAgent(sector_mapping=sector_mapping)
        self.sentiment_agent = SentimentAgent()
        self.institutional_flow_agent = InstitutionalFlowAgent()
        self.data_provider = EnhancedNSEProvider()

        # Agent weights (same as US version)
        self.weights = {
            'fundamentals': 0.36,
            'momentum': 0.27,
            'quality': 0.18,
            'sentiment': 0.09,
            'institutional_flow': 0.10
        }

    def score_stock(self, symbol: str) -> Dict:
        """Score a single Indian stock using all agents"""

        try:
            # Get comprehensive data
            cached_data = self.data_provider.get_comprehensive_data(symbol)

            # Get price data
            price_data = cached_data.get('historical_data')

            # Get NIFTY 50 data for relative strength
            nifty_data = self.data_provider.get_comprehensive_data('NIFTY')

            # Run all agents
            fund_result = self.fundamentals_agent.analyze(symbol, cached_data)
            mom_result = self.momentum_agent.analyze(symbol, price_data, nifty_data)
            qual_result = self.quality_agent.analyze(symbol, price_data)
            sent_result = self.sentiment_agent.analyze(symbol, cached_data)
            flow_result = self.institutional_flow_agent.analyze(symbol, price_data, cached_data)

            # Calculate composite score
            composite_score = (
                self.weights['fundamentals'] * fund_result['score'] +
                self.weights['momentum'] * mom_result['score'] +
                self.weights['quality'] * qual_result['score'] +
                self.weights['sentiment'] * sent_result['score'] +
                self.weights['institutional_flow'] * flow_result['score']
            )

            # Calculate composite confidence
            composite_confidence = (
                self.weights['fundamentals'] * fund_result['confidence'] +
                self.weights['momentum'] * mom_result['confidence'] +
                self.weights['quality'] * qual_result['confidence'] +
                self.weights['sentiment'] * sent_result['confidence'] +
                self.weights['institutional_flow'] * flow_result['confidence']
            )

            # Determine recommendation
            recommendation = self._get_recommendation(composite_score)

            return {
                'symbol': symbol,
                'composite_score': round(composite_score, 2),
                'composite_confidence': round(composite_confidence, 2),
                'recommendation': recommendation,
                'agent_scores': {
                    'fundamentals': fund_result,
                    'momentum': mom_result,
                    'quality': qual_result,
                    'sentiment': sent_result,
                    'institutional_flow': flow_result
                },
                'weights_used': self.weights
            }

        except Exception as e:
            logger.error(f"Failed to score {symbol}: {e}")
            return {
                'symbol': symbol,
                'composite_score': 50.0,
                'composite_confidence': 0.0,
                'reasoning': f"Scoring failed: {str(e)}",
                'rank_category': 'Error'
            }

    def _get_recommendation(self, score: float) -> str:
        """Get investment recommendation"""
        if score >= 70:
            return "STRONG BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 52:
            return "WEAK BUY"
        elif score >= 48:
            return "HOLD"
        elif score >= 42:
            return "WEAK SELL"
        else:
            return "SELL"
```

### Phase 5: API Layer (Day 13-15)

#### 5.1 FastAPI Application

**File**: `api/main.py`

```python
"""
FastAPI Application for AI Hedge Fund System - Indian Market Version
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging

from core.stock_scorer import StockScorer
from data.nse_top_50_stocks import NIFTY_TOP_50_STOCKS, SECTOR_MAPPING
from narrative_engine.narrative_engine import InvestmentNarrativeEngine

# Initialize FastAPI
app = FastAPI(
    title="AI Hedge Fund System - India",
    description="Professional-grade investment analysis for Indian stocks",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
stock_scorer = StockScorer(sector_mapping=SECTOR_MAPPING)
narrative_engine = InvestmentNarrativeEngine(
    llm_provider='gemini',  # or 'openai', 'anthropic'
    enable_llm=True
)

# Request/Response models
class AnalyzeRequest(BaseModel):
    symbol: str

class BatchAnalyzeRequest(BaseModel):
    symbols: List[str]

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "market": "India (NSE/BSE)",
        "agents": 5
    }

@app.post("/analyze")
async def analyze_stock(request: AnalyzeRequest):
    """
    Analyze a single Indian stock

    Returns comprehensive analysis with:
    - Agent scores (5 agents)
    - Composite score
    - Investment thesis
    - Recommendation
    """

    try:
        symbol = request.symbol

        # Score the stock
        analysis = stock_scorer.score_stock(symbol)

        # Generate narrative
        narrative = narrative_engine.generate_comprehensive_thesis(
            symbol=symbol,
            agent_results=analysis['agent_scores'],
            stock_info={'shortName': symbol}  # Can enhance with real company name
        )

        # Combine results
        result = {
            **analysis,
            **narrative
        }

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/batch")
async def analyze_batch(request: BatchAnalyzeRequest):
    """
    Analyze multiple stocks in batch

    Max 50 symbols per request
    """

    if len(request.symbols) > 50:
        raise HTTPException(status_code=400, detail="Max 50 symbols per batch")

    results = []

    for symbol in request.symbols:
        try:
            analysis = stock_scorer.score_stock(symbol)
            results.append(analysis)
        except Exception as e:
            logger.error(f"Failed to analyze {symbol}: {e}")
            results.append({
                'symbol': symbol,
                'error': str(e)
            })

    # Sort by composite score
    results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

    return {
        'results': results,
        'count': len(results)
    }

@app.get("/portfolio/top-picks")
async def get_top_picks():
    """
    Get top investment picks from NIFTY 50

    Analyzes all 50 stocks and returns top 10
    """

    results = []

    for symbol in NIFTY_TOP_50_STOCKS:
        try:
            analysis = stock_scorer.score_stock(symbol)
            results.append(analysis)
        except Exception as e:
            logger.error(f"Failed to analyze {symbol}: {e}")

    # Sort by composite score
    results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

    # Return top 10
    return {
        'top_picks': results[:10],
        'analysis_date': datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

#### 5.2 Run API Server

```bash
# Start API server
python -m api.main

# Or with auto-reload for development
uvicorn api.main:app --reload --host 0.0.0.0 --port 8010

# Test endpoints
curl http://localhost:8010/health
curl -X POST http://localhost:8010/analyze -H "Content-Type: application/json" -d '{"symbol": "TCS"}'
```

### Phase 6: Frontend (Day 16-20)

#### 6.1 Minimal Frontend Setup

**File**: `frontend/src/App.tsx`

```tsx
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = 'http://localhost:8010';

interface AnalysisResult {
  symbol: string;
  composite_score: number;
  recommendation: string;
  agent_scores: {
    fundamentals: { score: number };
    momentum: { score: number };
    quality: { score: number };
    sentiment: { score: number };
    institutional_flow: { score: number };
  };
  investment_thesis?: string;
}

function App() {
  const [symbol, setSymbol] = useState('TCS');

  const { data, isLoading, error, refetch } = useQuery<AnalysisResult>({
    queryKey: ['analysis', symbol],
    queryFn: async () => {
      const response = await axios.post(`${API_URL}/analyze`, { symbol });
      return response.data;
    },
    enabled: false
  });

  const handleAnalyze = () => {
    refetch();
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">
          AI Hedge Fund System - India
        </h1>

        {/* Search Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex gap-4">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="Enter NSE symbol (e.g., TCS, INFY, RELIANCE)"
              className="flex-1 px-4 py-2 border rounded"
            />
            <button
              onClick={handleAnalyze}
              disabled={isLoading}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {isLoading ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-8">
            Error: {error.message}
          </div>
        )}

        {data && (
          <div className="space-y-8">
            {/* Score Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold mb-4">{data.symbol}</h2>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <div className="text-sm text-gray-600">Composite Score</div>
                  <div className="text-3xl font-bold">{data.composite_score}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Recommendation</div>
                  <div className={`text-2xl font-bold ${
                    data.recommendation === 'STRONG BUY' ? 'text-green-600' :
                    data.recommendation === 'BUY' ? 'text-green-500' :
                    data.recommendation === 'HOLD' ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {data.recommendation}
                  </div>
                </div>
              </div>

              {/* Agent Scores */}
              <div className="space-y-3">
                <h3 className="font-semibold mb-2">Agent Scores</h3>
                {Object.entries(data.agent_scores).map(([agent, details]) => (
                  <div key={agent}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="capitalize">{agent.replace('_', ' ')}</span>
                      <span className="font-semibold">{details.score}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${details.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Investment Thesis */}
            {data.investment_thesis && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-xl font-bold mb-4">Investment Thesis</h3>
                <p className="text-gray-700 whitespace-pre-wrap">
                  {data.investment_thesis}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
```

#### 6.2 Setup React Query

**File**: `frontend/src/main.tsx`

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
```

#### 6.3 Tailwind CSS Setup

**File**: `frontend/tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**File**: `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

#### 6.4 Run Frontend

```bash
cd frontend
npm run dev

# Frontend will start on http://localhost:5173 or 5174
```

### Phase 7: Testing & Validation (Day 21-23)

#### 7.1 Create Test Scripts

**File**: `test_system.py`

```python
"""
Test AI Hedge Fund System - Indian Market Version
"""

import sys
from datetime import datetime
from core.stock_scorer import StockScorer
from data.nse_top_50_stocks import NIFTY_TOP_50_STOCKS, SECTOR_MAPPING
from narrative_engine.narrative_engine import InvestmentNarrativeEngine

def test_single_stock(symbol: str):
    """Test analysis of a single stock"""
    print(f"\n{'='*80}")
    print(f"Testing {symbol}")
    print(f"{'='*80}\n")

    # Initialize components
    scorer = StockScorer(sector_mapping=SECTOR_MAPPING)
    narrative_engine = InvestmentNarrativeEngine(enable_llm=False)

    # Score the stock
    print("Running 5-agent analysis...")
    analysis = scorer.score_stock(symbol)

    print(f"\nResults for {symbol}:")
    print(f"  Composite Score: {analysis['composite_score']}")
    print(f"  Composite Confidence: {analysis['composite_confidence']}")
    print(f"  Recommendation: {analysis['recommendation']}")
    print(f"\nAgent Scores:")
    print(f"  Fundamentals: {analysis['agent_scores']['fundamentals']['score']}")
    print(f"  Momentum: {analysis['agent_scores']['momentum']['score']}")
    print(f"  Quality: {analysis['agent_scores']['quality']['score']}")
    print(f"  Sentiment: {analysis['agent_scores']['sentiment']['score']}")
    print(f"  Institutional Flow: {analysis['agent_scores']['institutional_flow']['score']}")

    # Generate narrative
    print("\nGenerating investment narrative...")
    narrative = narrative_engine.generate_comprehensive_thesis(
        symbol=symbol,
        agent_results=analysis['agent_scores']
    )

    print(f"\nInvestment Thesis:")
    print(f"{narrative['investment_thesis']}")

    return analysis, narrative

def test_top_10():
    """Test top 10 stocks from NIFTY 50"""
    print(f"\n{'='*80}")
    print("Testing Top 10 NIFTY Stocks")
    print(f"{'='*80}\n")

    scorer = StockScorer(sector_mapping=SECTOR_MAPPING)
    results = []

    # Test first 10 stocks
    test_symbols = NIFTY_TOP_50_STOCKS[:10]

    for i, symbol in enumerate(test_symbols, 1):
        print(f"[{i}/10] Analyzing {symbol}...", end=" ")
        try:
            analysis = scorer.score_stock(symbol)
            results.append(analysis)
            print(f"✓ Score: {analysis['composite_score']}")
        except Exception as e:
            print(f"✗ Error: {str(e)}")

    # Sort by score
    results.sort(key=lambda x: x['composite_score'], reverse=True)

    print(f"\nTop 10 Ranked Stocks:")
    print(f"{'Rank':<6} {'Symbol':<15} {'Score':<10} {'Recommendation':<15}")
    print(f"{'-'*50}")

    for i, result in enumerate(results, 1):
        print(f"{i:<6} {result['symbol']:<15} {result['composite_score']:<10.2f} {result['recommendation']:<15}")

    return results

if __name__ == "__main__":
    # Test specific stock
    test_single_stock("TCS")

    # Test top 10
    # test_top_10()
```

#### 7.2 Run Tests

```bash
# Test single stock
python test_system.py

# Test API endpoints
curl -X POST http://localhost:8010/analyze -H "Content-Type: application/json" -d '{"symbol": "TCS"}'
curl -X POST http://localhost:8010/analyze -H "Content-Type: application/json" -d '{"symbol": "INFY"}'
curl -X POST http://localhost:8010/analyze -H "Content-Type: application/json" -d '{"symbol": "RELIANCE"}'

# Test batch analysis
curl -X POST http://localhost:8010/analyze/batch -H "Content-Type: application/json" -d '{"symbols": ["TCS", "INFY", "HDFCBANK", "RELIANCE", "WIPRO"]}'

# Test top picks
curl http://localhost:8010/portfolio/top-picks
```

### Phase 8: Deployment (Day 24-25)

#### 8.1 Production Requirements

**File**: `requirements-production.txt`

```txt
# Extend base requirements.txt with production dependencies
gunicorn>=21.2.0  # WSGI server for production
redis>=5.0.0      # For distributed caching
celery>=5.3.0     # For background tasks
flower>=2.0.0     # Celery monitoring
sentry-sdk>=2.0.0 # Error tracking
prometheus-client>=0.20.0  # Metrics
```

#### 8.2 Docker Setup

**File**: `Dockerfile`

```dockerfile
# Multi-stage build for smaller image size

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy TA-Lib from builder
COPY --from=builder /usr/lib/libta_lib.so.0 /usr/lib/
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8010

# Run application
CMD ["python", "-m", "api.main"]
```

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8010:8010"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - ENABLE_ADAPTIVE_WEIGHTS=false
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "5174:5174"
    depends_on:
      - api
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

#### 8.3 Deployment Commands

```bash
# Build Docker images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Production deployment (with Gunicorn)
gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8010
```

---

## API Specifications

### Complete API Reference

#### Base URL
```
http://localhost:8010
```

#### Authentication
Currently no authentication required (add JWT/API keys for production)

#### Endpoints

##### 1. Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "market": "India (NSE/BSE)",
  "agents": 5
}
```

##### 2. Analyze Single Stock
```
POST /analyze
Content-Type: application/json

Request:
{
  "symbol": "TCS"
}

Response:
{
  "symbol": "TCS",
  "composite_score": 72.5,
  "composite_confidence": 0.85,
  "recommendation": "STRONG BUY",
  "agent_scores": {
    "fundamentals": {
      "score": 75,
      "confidence": 0.9,
      "reasoning": "ROE: 38.2%, P/E: 28.5, Revenue Growth: 12.3%",
      "metrics": {
        "roe": 38.2,
        "pe_ratio": 28.5,
        "revenue_growth": 12.3,
        "debt_to_equity": 0.15
      }
    },
    "momentum": {
      "score": 68,
      "confidence": 0.95,
      "reasoning": "RSI: 58.2, 3M Return: 8.5%",
      "metrics": {
        "1m_return": 3.2,
        "3m_return": 8.5,
        "rsi": 58.2,
        "rel_strength_vs_nifty": 2.1
      }
    },
    "quality": {
      "score": 72,
      "confidence": 0.9,
      "reasoning": "High quality business with stable metrics"
    },
    "sentiment": {
      "score": 70,
      "confidence": 0.7,
      "reasoning": "Positive analyst sentiment"
    },
    "institutional_flow": {
      "score": 75,
      "confidence": 0.85,
      "reasoning": "Strong institutional accumulation detected"
    }
  },
  "investment_thesis": "TCS presents a compelling investment opportunity with strong fundamentals...",
  "key_strengths": [
    "Strong fundamental financial metrics",
    "Positive technical momentum",
    "High-quality business characteristics"
  ],
  "key_risks": [
    "Premium valuation",
    "Market volatility"
  ],
  "weights_used": {
    "fundamentals": 0.36,
    "momentum": 0.27,
    "quality": 0.18,
    "sentiment": 0.09,
    "institutional_flow": 0.10
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

##### 3. Batch Analysis
```
POST /analyze/batch
Content-Type: application/json

Request:
{
  "symbols": ["TCS", "INFY", "HDFCBANK", "RELIANCE"]
}

Response:
{
  "results": [
    {
      "symbol": "TCS",
      "composite_score": 72.5,
      "recommendation": "STRONG BUY",
      ...
    },
    {
      "symbol": "INFY",
      "composite_score": 68.2,
      "recommendation": "BUY",
      ...
    }
  ],
  "count": 4
}

Constraints:
- Max 50 symbols per request
- Returns 400 error if limit exceeded
```

##### 4. Top Picks
```
GET /portfolio/top-picks

Response:
{
  "top_picks": [
    {
      "symbol": "TCS",
      "composite_score": 72.5,
      "recommendation": "STRONG BUY",
      ...
    },
    // ... top 10 stocks
  ],
  "analysis_date": "2024-01-15T10:30:00Z"
}
```

---

## Configuration

### Environment Variables

Create `.env` file:

```bash
# LLM Provider (optional)
LLM_PROVIDER=gemini  # or openai, anthropic
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Adaptive Weights (optional)
ENABLE_ADAPTIVE_WEIGHTS=false  # Set to true to enable

# Data Provider Settings
CACHE_DURATION=1200  # 20 minutes
RATE_LIMIT_DELAY=0.5  # 500ms between API calls

# API Settings
API_HOST=0.0.0.0
API_PORT=8010

# Frontend Settings
FRONTEND_PORT=5174
```

### Agent Weights Configuration

**File**: `config/agent_weights.py`

```python
"""
Agent Weights Configuration
"""

# Static weights (default)
STATIC_AGENT_WEIGHTS = {
    'fundamentals': 0.36,      # 36% - Financial health
    'momentum': 0.27,          # 27% - Technical trends
    'quality': 0.18,           # 18% - Business quality
    'sentiment': 0.09,         # 9% - Market sentiment
    'institutional_flow': 0.10 # 10% - Smart money
}

# Validation
assert sum(STATIC_AGENT_WEIGHTS.values()) == 1.0, "Weights must sum to 1.0"

def get_agent_weights(use_adaptive: bool = False) -> dict:
    """Get current agent weights"""
    if use_adaptive:
        # Import adaptive weights service
        from core.market_regime_service import get_market_regime_service
        service = get_market_regime_service()
        return service.get_adaptive_weights()
    else:
        return STATIC_AGENT_WEIGHTS.copy()
```

---

## Deployment

### Local Development

```bash
# 1. Clone and setup
git clone <your-repo>
cd ai_hedge_fund_india

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Start API server
python -m api.main

# 6. Start frontend (separate terminal)
cd frontend
npm install
npm run dev

# 7. Access application
# API: http://localhost:8010
# Frontend: http://localhost:5174
```

### Production Deployment (AWS/GCP/Azure)

#### Option 1: Docker Compose

```bash
# 1. Build and start services
docker-compose up -d

# 2. View logs
docker-compose logs -f

# 3. Scale API workers
docker-compose up -d --scale api=4

# 4. Stop services
docker-compose down
```

#### Option 2: Kubernetes

**File**: `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hedge-fund-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hedge-fund-api
  template:
    metadata:
      labels:
        app: hedge-fund-api
    spec:
      containers:
      - name: api
        image: your-registry/hedge-fund-api:latest
        ports:
        - containerPort: 8010
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: gemini-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: hedge-fund-api
spec:
  selector:
    app: hedge-fund-api
  ports:
  - port: 80
    targetPort: 8010
  type: LoadBalancer
```

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/hedge-fund-api

# Scale deployment
kubectl scale deployment/hedge-fund-api --replicas=5
```

#### Option 3: Serverless (AWS Lambda + API Gateway)

**File**: `serverless.yml`

```yaml
service: hedge-fund-india

provider:
  name: aws
  runtime: python3.11
  stage: prod
  region: ap-south-1  # Mumbai region
  memorySize: 2048
  timeout: 30
  environment:
    GEMINI_API_KEY: ${env:GEMINI_API_KEY}

functions:
  analyze:
    handler: api.lambda_handler.analyze
    events:
      - http:
          path: /analyze
          method: post
          cors: true

  batch_analyze:
    handler: api.lambda_handler.batch_analyze
    events:
      - http:
          path: /analyze/batch
          method: post
          cors: true
    timeout: 60  # Longer timeout for batch

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true
    layer: true
```

```bash
# Deploy to AWS
serverless deploy

# View logs
serverless logs -f analyze -t

# Remove deployment
serverless remove
```

---

## Testing & Validation

### Unit Tests

**File**: `tests/test_agents.py`

```python
"""
Unit tests for all 5 agents
"""

import pytest
from agents.fundamentals_agent import FundamentalsAgent
from agents.momentum_agent import MomentumAgent
from agents.quality_agent import QualityAgent
from agents.sentiment_agent import SentimentAgent
from agents.institutional_flow_agent import InstitutionalFlowAgent

def test_fundamentals_agent():
    """Test fundamentals agent"""
    agent = FundamentalsAgent()
    result = agent.analyze('TCS')

    assert 'score' in result
    assert 0 <= result['score'] <= 100
    assert 'confidence' in result
    assert 0 <= result['confidence'] <= 1
    assert 'metrics' in result

def test_momentum_agent():
    """Test momentum agent"""
    agent = MomentumAgent()
    # Mock price data needed

def test_quality_agent():
    """Test quality agent"""
    agent = QualityAgent()
    # Test logic

def test_sentiment_agent():
    """Test sentiment agent"""
    agent = SentimentAgent()
    # Test logic

def test_institutional_flow_agent():
    """Test institutional flow agent"""
    agent = InstitutionalFlowAgent()
    # Test logic
```

**Run tests**:
```bash
pytest tests/ -v
pytest tests/test_agents.py::test_fundamentals_agent -v
```

### Integration Tests

```bash
# Test complete analysis pipeline
python test_system.py

# Test API endpoints
pytest tests/test_api.py -v

# Load testing (optional)
locust -f tests/load_test.py --host http://localhost:8010
```

---

## Conclusion

This comprehensive guide provides everything needed to replicate the AI Hedge Fund System for the Indian stock market. The system architecture is modular and well-documented, making adaptation straightforward.

### Key Success Factors

1. **Data Quality**: Ensure reliable NSE/BSE data access
2. **Agent Calibration**: Tune scoring thresholds for Indian market norms
3. **Testing**: Validate with historical data before live deployment
4. **Monitoring**: Implement logging and error tracking
5. **Iteration**: Continuously improve based on real-world performance

### Next Steps

1. **Phase 1-2**: Setup environment and data layer (Days 1-5)
2. **Phase 3-4**: Implement agents and orchestration (Days 6-12)
3. **Phase 5-6**: Build API and frontend (Days 13-20)
4. **Phase 7-8**: Test and deploy (Days 21-25)

### Support & Resources

- **Original US System**: https://github.com/anthropics/ai-hedge-fund
- **NSEpy Documentation**: https://nsepy.xyz/
- **TA-Lib Documentation**: https://mrjbq7.github.io/ta-lib/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Query**: https://tanstack.com/query/latest

---

**Version**: 1.0.0
**Last Updated**: January 2026
**Maintained By**: AI Hedge Fund System Team
