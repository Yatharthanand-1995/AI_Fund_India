# Quick Start Guide - Indian Market Adaptation

## 🚀 Quick Start (15 Minutes to First Analysis)

This guide will help you replicate the AI Hedge Fund System for Indian stocks in **under 30 minutes**.

---

## Prerequisites

- **Python 3.11+** installed
- **Node.js 18+** installed
- **Git** installed
- Basic command line knowledge

---

## Step 1: Clone and Setup Environment (5 minutes)

```bash
# Create project directory
mkdir ai_hedge_fund_india
cd ai_hedge_fund_india

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies
pip install pandas numpy yfinance nsepy talib-binary fastapi uvicorn pydantic requests scikit-learn python-dotenv

# Optional: Install LLM support
pip install google-generativeai  # Gemini (free tier)
```

---

## Step 2: Create Project Structure (2 minutes)

```bash
# Create directory structure
mkdir -p agents core data api narrative_engine config tests

# Create empty __init__.py files
touch agents/__init__.py core/__init__.py data/__init__.py api/__init__.py narrative_engine/__init__.py config/__init__.py
```

---

## Step 3: Create Data Provider (3 minutes)

**File**: `data/nse_provider.py`

```python
"""NSE Data Provider - Simplified Version"""

import pandas as pd
import numpy as np
import talib
from nsepy import get_history
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class EnhancedNSEProvider:
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 1200  # 20 minutes

    def get_comprehensive_data(self, symbol: str) -> Dict:
        """Get comprehensive stock data with technical indicators"""

        # Check cache
        if symbol in self.cache:
            if datetime.now() < self.cache_expiry.get(symbol, datetime.now()):
                return self.cache[symbol]

        try:
            # Get historical data (2 years)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)

            hist = get_history(symbol=symbol, start=start_date, end=end_date, index=False)

            if hist.empty:
                logger.warning(f"No data for {symbol}")
                return {'symbol': symbol, 'error': 'No data available'}

            # Calculate technical indicators
            close = hist['Close'].values.astype(np.float64)
            high = hist['High'].values.astype(np.float64)
            low = hist['Low'].values.astype(np.float64)
            volume = hist['Volume'].values.astype(np.float64)

            # Key indicators
            rsi = talib.RSI(close, timeperiod=14)
            sma_20 = talib.SMA(close, timeperiod=20)
            obv = talib.OBV(close, volume)

            technical_data = {
                'rsi': float(rsi[-1]) if not np.isnan(rsi[-1]) else None,
                'sma_20': float(sma_20[-1]) if not np.isnan(sma_20[-1]) else None,
                'obv': obv
            }

            data = {
                'symbol': symbol,
                'current_price': float(close[-1]),
                'historical_data': hist,
                'technical_data': technical_data,
                'timestamp': datetime.now().isoformat()
            }

            # Cache
            self.cache[symbol] = data
            self.cache_expiry[symbol] = datetime.now() + timedelta(seconds=self.cache_duration)

            return data

        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
```

---

## Step 4: Create Stock Universe (1 minute)

**File**: `data/nse_top_50_stocks.py`

```python
"""Top 50 NSE Stocks"""

NIFTY_TOP_50_STOCKS = [
    'TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM',
    'HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'SBIN', 'AXISBANK',
    'RELIANCE', 'BHARTIARTL', 'HINDUNILVR', 'ITC', 'NESTLEIND',
    'ONGC', 'BPCL', 'IOC', 'POWERGRID',
    'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB',
    'LT', 'ULTRACEMCO', 'ADANIPORTS', 'TATASTEEL', 'HINDALCO',
    'TATAMOTORS', 'M&M', 'HEROMOTOCO', 'BAJAJ-AUTO'
]

SECTOR_MAPPING = {
    'Technology': ['TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM'],
    'Financial': ['HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'SBIN', 'AXISBANK'],
    'Consumer': ['RELIANCE', 'BHARTIARTL', 'HINDUNILVR', 'ITC', 'NESTLEIND'],
    'Energy': ['ONGC', 'BPCL', 'IOC', 'POWERGRID'],
    'Healthcare': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB'],
    'Industrial': ['LT', 'ULTRACEMCO', 'ADANIPORTS', 'TATASTEEL', 'HINDALCO'],
    'Auto': ['TATAMOTORS', 'M&M', 'HEROMOTOCO', 'BAJAJ-AUTO']
}
```

---

## Step 5: Create Simple Agents (5 minutes)

**File**: `agents/momentum_agent.py`

```python
"""Momentum Agent - Simplified"""

import logging
import numpy as np
from typing import Dict

logger = logging.getLogger(__name__)

class MomentumAgent:
    """Analyzes technical momentum"""

    def analyze(self, symbol: str, price_data, nifty_data, cached_data: Dict = None) -> Dict:
        try:
            # Get RSI from cached data
            rsi = cached_data.get('technical_data', {}).get('rsi', 50)

            # Calculate returns
            current_price = float(price_data['Close'].iloc[-1])
            price_3m_ago = float(price_data['Close'].iloc[-60]) if len(price_data) > 60 else current_price
            three_month_return = (current_price / price_3m_ago - 1) * 100

            # Simple scoring
            score = 50

            # RSI scoring
            if 50 < rsi < 70:
                score += 25
            elif 40 < rsi <= 50:
                score += 15

            # Return scoring
            if three_month_return > 10:
                score += 25
            elif three_month_return > 5:
                score += 15

            return {
                'score': max(0, min(100, score)),
                'confidence': 0.9,
                'reasoning': f"RSI: {rsi:.1f}, 3M Return: {three_month_return:.1f}%",
                'metrics': {'rsi': rsi, '3m_return': three_month_return}
            }

        except Exception as e:
            logger.error(f"Momentum analysis failed: {e}")
            return {'score': 50, 'confidence': 0.1, 'reasoning': str(e), 'metrics': {}}
```

**File**: `agents/__init__.py`

```python
"""Agent package initialization"""

from agents.momentum_agent import MomentumAgent

# Placeholder agents (implement as needed)
class FundamentalsAgent:
    def analyze(self, symbol, cached_data=None):
        return {'score': 60, 'confidence': 0.7, 'reasoning': 'Basic fundamental analysis', 'metrics': {}}

class QualityAgent:
    def analyze(self, symbol, price_data):
        return {'score': 65, 'confidence': 0.8, 'reasoning': 'Quality assessment', 'metrics': {}}

class SentimentAgent:
    def analyze(self, symbol, cached_data=None):
        return {'score': 55, 'confidence': 0.6, 'reasoning': 'Sentiment analysis', 'metrics': {}}

class InstitutionalFlowAgent:
    def analyze(self, symbol, price_data, cached_data=None):
        return {'score': 58, 'confidence': 0.7, 'reasoning': 'Institutional flow analysis', 'metrics': {}}

__all__ = ['FundamentalsAgent', 'MomentumAgent', 'QualityAgent', 'SentimentAgent', 'InstitutionalFlowAgent']
```

---

## Step 6: Create Stock Scorer (3 minutes)

**File**: `core/stock_scorer.py`

```python
"""Stock Scorer - Simplified"""

from typing import Dict
from agents import FundamentalsAgent, MomentumAgent, QualityAgent, SentimentAgent, InstitutionalFlowAgent
from data.nse_provider import EnhancedNSEProvider
import logging

logger = logging.getLogger(__name__)

class StockScorer:
    """Combines all agent scores"""

    def __init__(self):
        self.fundamentals_agent = FundamentalsAgent()
        self.momentum_agent = MomentumAgent()
        self.quality_agent = QualityAgent()
        self.sentiment_agent = SentimentAgent()
        self.institutional_flow_agent = InstitutionalFlowAgent()
        self.data_provider = EnhancedNSEProvider()

        self.weights = {
            'fundamentals': 0.36,
            'momentum': 0.27,
            'quality': 0.18,
            'sentiment': 0.09,
            'institutional_flow': 0.10
        }

    def score_stock(self, symbol: str) -> Dict:
        """Score a single stock"""

        try:
            # Get data
            cached_data = self.data_provider.get_comprehensive_data(symbol)
            price_data = cached_data.get('historical_data')
            nifty_data = self.data_provider.get_comprehensive_data('NIFTY')

            # Run agents
            fund_result = self.fundamentals_agent.analyze(symbol, cached_data)
            mom_result = self.momentum_agent.analyze(symbol, price_data, nifty_data, cached_data)
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

            # Recommendation
            if composite_score >= 70:
                recommendation = "STRONG BUY"
            elif composite_score >= 60:
                recommendation = "BUY"
            elif composite_score >= 52:
                recommendation = "WEAK BUY"
            elif composite_score >= 48:
                recommendation = "HOLD"
            else:
                recommendation = "SELL"

            return {
                'symbol': symbol,
                'composite_score': round(composite_score, 2),
                'recommendation': recommendation,
                'agent_scores': {
                    'fundamentals': fund_result,
                    'momentum': mom_result,
                    'quality': qual_result,
                    'sentiment': sent_result,
                    'institutional_flow': flow_result
                }
            }

        except Exception as e:
            logger.error(f"Failed to score {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
```

---

## Step 7: Create API (3 minutes)

**File**: `api/main.py`

```python
"""FastAPI Application"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.stock_scorer import StockScorer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Hedge Fund - India", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stock_scorer = StockScorer()

class AnalyzeRequest(BaseModel):
    symbol: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "market": "India (NSE)"}

@app.post("/analyze")
async def analyze_stock(request: AnalyzeRequest):
    try:
        result = stock_scorer.score_stock(request.symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

---

## Step 8: Test the System (3 minutes)

**File**: `test_quick.py`

```python
"""Quick Test Script"""

from core.stock_scorer import StockScorer

def test_analysis(symbol: str):
    print(f"\n{'='*60}")
    print(f"Testing {symbol}")
    print(f"{'='*60}\n")

    scorer = StockScorer()
    result = scorer.score_stock(symbol)

    print(f"Symbol: {result['symbol']}")
    print(f"Composite Score: {result['composite_score']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"\nAgent Scores:")
    print(f"  Fundamentals: {result['agent_scores']['fundamentals']['score']}")
    print(f"  Momentum: {result['agent_scores']['momentum']['score']}")
    print(f"  Quality: {result['agent_scores']['quality']['score']}")
    print(f"  Sentiment: {result['agent_scores']['sentiment']['score']}")
    print(f"  Institutional Flow: {result['agent_scores']['institutional_flow']['score']}")

if __name__ == "__main__":
    # Test with TCS
    test_analysis("TCS")

    # Test with INFY
    test_analysis("INFY")
```

**Run the test**:

```bash
python test_quick.py
```

---

## Step 9: Start the API Server (1 minute)

```bash
# Start API server
python -m api.main

# In another terminal, test API
curl http://localhost:8010/health
curl -X POST http://localhost:8010/analyze -H "Content-Type: application/json" -d '{"symbol": "TCS"}'
```

---

## Step 10: Access API Documentation (1 minute)

Open browser and visit:
- **API Docs**: http://localhost:8010/docs
- **Interactive API**: Test endpoints directly in browser

---

## 🎉 Congratulations!

You now have a working AI Hedge Fund System for Indian stocks!

### What You've Built:

✅ Data provider (NSEpy integration)
✅ 5 specialized agents (simplified versions)
✅ Stock scorer (orchestration)
✅ REST API (FastAPI)
✅ Working system for NSE stocks

### Next Steps:

1. **Enhance Agents**: Implement full logic for each agent
2. **Add Frontend**: Build React UI (see main guide)
3. **Add LLM**: Integrate Gemini/OpenAI for narratives
4. **Improve Data**: Add more technical indicators
5. **Add Caching**: Optimize performance
6. **Deploy**: Use Docker for production

---

## Common Issues & Solutions

### Issue 1: NSEpy Installation Fails

```bash
# Use pip install with no cache
pip install --no-cache-dir nsepy
```

### Issue 2: TA-Lib Not Found

```bash
# macOS
brew install ta-lib
pip install talib-binary

# Ubuntu/Debian
sudo apt-get install ta-lib
pip install talib-binary

# Windows
# Download from: https://github.com/mrjbq7/ta-lib
# Install manually
```

### Issue 3: NSE Data Not Loading

```python
# NSEpy sometimes has connection issues
# Solution: Add retry logic or use yfinance as backup

import yfinance as yf

# Use Yahoo Finance with .NS suffix
data = yf.download("TCS.NS", period="2y")
```

### Issue 4: Port Already in Use

```bash
# Kill process on port 8010
lsof -ti :8010 | xargs kill -9

# Or use different port
uvicorn api.main:app --port 8011
```

---

## Testing Checklist

- [ ] Data provider fetches NSE data successfully
- [ ] All 5 agents return scores (0-100)
- [ ] Composite score calculated correctly
- [ ] API `/health` endpoint works
- [ ] API `/analyze` endpoint returns results
- [ ] Test with at least 3 different stocks
- [ ] Verify recommendations are reasonable
- [ ] Check logs for errors

---

## Performance Benchmarks

Expected performance (first run, no cache):
- Data fetch: 1-2 seconds
- Agent analysis: 0.5-1 second
- Total analysis: 2-3 seconds

Expected performance (cached):
- Data fetch: <50ms
- Agent analysis: 0.5-1 second
- Total analysis: <1 second

---

## Directory Structure

After completing this guide, your project should look like:

```
ai_hedge_fund_india/
├── venv/
├── agents/
│   ├── __init__.py
│   └── momentum_agent.py
├── core/
│   ├── __init__.py
│   └── stock_scorer.py
├── data/
│   ├── __init__.py
│   ├── nse_provider.py
│   └── nse_top_50_stocks.py
├── api/
│   ├── __init__.py
│   └── main.py
├── test_quick.py
└── requirements.txt
```

---

## Quick Reference Commands

```bash
# Activate environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run test
python test_quick.py

# Start API server
python -m api.main

# Test API
curl -X POST http://localhost:8010/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TCS"}'

# View API docs
open http://localhost:8010/docs
```

---

## Next: Full Implementation

For complete implementation with:
- Full agent logic
- Frontend UI
- LLM integration
- Caching optimization
- Deployment setup

See: `INDIAN_MARKET_REPLICATION_GUIDE.md` (comprehensive 25-day plan)

---

## Support

- **Issues**: Check logs in console
- **Questions**: Review main documentation
- **NSEpy Docs**: https://nsepy.xyz/
- **TA-Lib Docs**: https://mrjbq7.github.io/ta-lib/

---

**Version**: 1.0.0 (Quick Start)
**Time to Complete**: 15-30 minutes
**Difficulty**: Beginner-Intermediate
