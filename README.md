# AI Hedge Fund — Indian Stock Market Analysis Platform

**Version**: 3.0  
**Status**: Production Ready  
**Last Updated**: April 2026

---

## Overview

An AI-powered stock analysis and portfolio management platform for Indian markets. Five specialized AI agents score every NIFTY 50 stock across fundamentals, momentum, quality, sentiment, and institutional flow. A signal-driven portfolio engine then acts on those scores the way an institutional fund manager would — buying on conviction, holding winners, and cutting losers when the thesis breaks.

---

## Features

| Category | What it does |
|---|---|
| **5 AI Agents** | Fundamentals · Momentum · Quality · Sentiment · Institutional Flow — run in parallel, results in ~3s per stock |
| **Adaptive Weights** | Regime detector (BULL/BEAR/SIDEWAYS × HIGH/NORMAL/LOW vol) blends agent weights using IC-calibrated coefficients |
| **Signal-Driven Portfolio** | Buy ≥ score threshold, hold until thesis breaks, sell on score drop or stop-loss — no calendar churn |
| **Backtester** | Full 3-year NIFTY50 simulation with sector caps, IT hard cap, equity curve, Sharpe, alpha, win rate |
| **Historical Tracking** | SQLite DB auto-populated by background collector every 4h during market hours |
| **Screener** | Server-side filtering by score, sector, recommendation, RSI, trend |
| **Sector Analysis** | Sector heatmap, rankings, top stock per sector |
| **Watchlist** | REST-backed watchlist with live scores |
| **Compare** | Side-by-side agent score comparison for up to 4 stocks |
| **Alerts** | Score-change and regime-shift alerts, badge on header |
| **Export** | CSV / JSON export of any analysis |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Setup

```bash
# 1. Clone
git clone https://github.com/Yatharthanand-1995/AI_Fund_India
cd "Indian Stock Fund"

# 2. Python dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Frontend dependencies
cd frontend && npm install && cd ..

# 4. Environment (optional — works without any keys)
cp .env.example .env
```

### Run

```bash
# Terminal 1 — Backend (port 8010)
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8010

# Terminal 2 — Frontend (port 3000)
cd frontend && npm run dev
```

Open http://localhost:3000

API docs: http://localhost:8010/docs

---

## Architecture

```
React + TypeScript + Tailwind (port 3000)
          │  REST via Vite proxy
FastAPI backend (port 8010)
    ├── 5 AI agents (parallel ThreadPoolExecutor)
    ├── Market regime detector (6h cache)
    ├── Portfolio manager (signal-driven, SQLite)
    ├── Backtester (3Y simulation engine)
    ├── Data collector (APScheduler, every 4h)
    └── Hybrid data provider (NSEpy → Yahoo fallback)
          │
SQLite databases
    ├── data/analysis_history.db  — stock score history, regime timeline, watchlist, alerts
    └── data/portfolio.db         — holdings, closed trades, signal log, config
```

### Tech Stack

**Backend**: FastAPI · Python 3.11+ · SQLite (WAL mode) · APScheduler · NSEpy · yfinance  
**Frontend**: React 18 · TypeScript · Vite · Recharts · Zustand · React Router · Tailwind · Axios

---

## Pages

| Route | Page | Description |
|---|---|---|
| `/` | Dashboard | Market regime, quick search, watchlist widget, top sectors |
| `/ideas` | Investment Ideas | Top NIFTY50 picks with filters and CSV export |
| `/screener` | Screener | Server-side filtering by score / sector / RSI / trend |
| `/suggestions` | Suggestions | AI-ranked stock suggestions |
| `/portfolio` | Live Portfolio | Signal engine — evaluate, buy, hold, sell with live P&L |
| `/backtest` | Backtester | Run / compare 3Y simulations with equity curve |
| `/stock/:symbol` | Stock Details | Deep dive: agents, historical chart, comparison tab |
| `/sectors` | Sector Analysis | Heatmap, sector rankings, top picks per sector |
| `/watchlist` | Watchlist | REST-backed watchlist with live scores |
| `/compare` | Compare | Side-by-side multi-stock comparison |
| `/analytics` | Analytics | System metrics, agent performance, data provider stats |
| `/system` | System Health | Health check, collector status, cache stats |
| `/about` | About | Agent methodology, market regime explanation |

---

## Portfolio Engine

The signal-driven portfolio (`/portfolio`) replicates institutional buy/hold/sell logic:

- **BUY** — composite score ≥ `buy_threshold` (default 65) and sector cap allows
- **HOLD** — score between `sell_threshold` (50) and `buy_threshold`; price above stop-loss floor
- **SELL_SCORE** — score drops below `sell_threshold` (thesis broken)
- **SELL_STOP** — price falls more than `stop_loss_pct` (10%) from entry
- **WATCH** — stocks near buy threshold not yet in portfolio

**Sector rules**: max 30% in any sector; IT hard-capped at 2 positions regardless.  
**Sizing**: score-proportional within position count limit (max 10).  
**Persistence**: all trades stored in `data/portfolio.db` and survive restarts.

### Portfolio API

```
GET  /portfolio/config              — current thresholds
POST /portfolio/config?buy_threshold=65&...  — update thresholds
GET  /portfolio/holdings            — open positions with live P&L
GET  /portfolio/closed              — closed trade history
POST /portfolio/evaluate            — score NIFTY50, apply signal logic, update DB
POST /portfolio/buy?symbol=X&entry_price=Y   — manual buy
POST /portfolio/sell?symbol=X&exit_price=Y  — manual sell
GET  /portfolio/performance         — win rate, avg win/loss, best/worst
GET  /portfolio/signals/history     — full signal log
POST /portfolio/reset               — wipe all holdings and trades
```

---

## Backtester

`scripts/portfolio_backtest.py` — 3-year monthly simulation over NIFTY50:

```bash
# Basic run
python3 scripts/portfolio_backtest.py --years 3 --top-n 10

# Signal-driven mode (institutional logic)
python3 scripts/portfolio_backtest.py --signal-mode --buy-threshold 60 --sell-threshold 40

# With sector cap
python3 scripts/portfolio_backtest.py --sector-cap 0.30

# Save and compare runs
python3 scripts/portfolio_backtest.py --name "signal_b60_s40" --signal-mode
python3 scripts/portfolio_backtest.py --compare
```

Results auto-append to `scripts/backtrack_results.csv`.

**Best configuration found** (signal_b60_s40_sl12_noQ):  
Total return +22.6% · Sharpe +0.10 · No IT overweight

---

## Key API Endpoints

```
POST /analyze                     — score a single stock
POST /analyze/batch               — score multiple stocks in parallel
GET  /portfolio/top-picks         — top NIFTY50 picks
GET  /screener                    — filtered stock list
GET  /market/regime               — current regime + weights
GET  /history/stock/{symbol}      — score history for a stock
GET  /history/regime              — market regime timeline
GET  /analytics/system            — system KPIs
GET  /analytics/sectors           — sector performance
GET  /analytics/agents            — agent performance stats
GET  /backtest/runs               — list past backtest runs
POST /backtest/run                — run a new backtest
GET  /backtest/results/{run_id}   — equity curve + signals
GET  /health                      — health check
```

---

## Configuration

### Backend (.env)

```bash
# Data collection
ENABLE_HISTORICAL_COLLECTION=true
HISTORICAL_COLLECTION_INTERVAL=14400   # seconds (4h)
DATA_RETENTION_DAYS=365

# Optional LLM for narratives
OPENAI_API_KEY=...

# Optional API key auth
ENABLE_API_KEY_AUTH=false
API_KEY=...

# Port
API_PORT=8010
```

### Frontend (.env)

```bash
VITE_API_URL=/api          # proxied to backend in dev
VITE_API_KEY=              # optional, sent as X-Api-Key header
```

---

## Testing

```bash
# Backend
python3 -m pytest tests/ -v

# Frontend
cd frontend && npm test
cd frontend && npm run test:coverage
```

---

## Known Limitations

- NSEpy (`nsepy` lib) has a Python 3.13 incompatibility (`FrameLocalsProxy` error). Yahoo Finance fallback activates automatically — no action needed.
- Narrative generation requires an OpenAI/compatible API key. Without one, rule-based narratives are used.
- Paper portfolio only — no broker integration.

---

## License

Proprietary. All rights reserved.
