# AI Hedge Fund — React Frontend

React + TypeScript frontend for the AI Hedge Fund platform. Connects to FastAPI backend on port 8010 via Vite proxy.

## Tech Stack

- **React 18** + **TypeScript** — UI and type safety
- **Vite** — dev server (port 3000), proxies `/api` → `localhost:8010`
- **Tailwind CSS** — utility-first styling
- **Zustand** — global state (market regime, stock universe, cache)
- **React Router v6** — client-side routing with lazy loading
- **Axios** — HTTP client with retry logic (5xx only) and API key header
- **Recharts** — 8 chart types, all wrapped in `ChartErrorBoundary`
- **Lucide React** — icons

## Pages

| Route | Component | Notes |
|---|---|---|
| `/` | `Dashboard` | Market regime, quick search, watchlist widget |
| `/ideas` | `Ideas` | Top NIFTY50 picks, filters, CSV export |
| `/screener` | `Screener` | Server-side filtered stock list |
| `/suggestions` | `Suggestions` | AI-ranked suggestions |
| `/portfolio` | `Portfolio` | Signal-driven portfolio — evaluate, buy/hold/sell, P&L |
| `/stock/:symbol` | `StockDetails` | Deep dive: agents, history, comparison |
| `/sectors` | `SectorAnalysis` | Sector heatmap and rankings |
| `/backtest` | `Backtest` | Run and compare 3Y simulations |
| `/watchlist` | `WatchlistEnhanced` | REST-backed watchlist |
| `/compare` | `Comparison` | Side-by-side stock comparison |
| `/analytics` | `Analytics` | System metrics and agent stats |
| `/system` | `SystemHealth` | Health check and collector status |
| `/about` | `About` | Methodology and agent descriptions |

All heavy pages are lazy-loaded via `React.lazy`.

## Quick Start

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production build → dist/
npm test           # Vitest unit tests
npm run test:coverage
```

## Environment

```bash
# frontend/.env
VITE_API_URL=/api        # Vite proxies to localhost:8010 in dev
VITE_API_KEY=            # optional — sent as X-Api-Key header
```

## Key Architecture Notes

- **API client** (`src/lib/api.ts`): Axios singleton with 3-retry exponential backoff on 5xx only. Connection errors fail fast (no retry).
- **State** (`src/store/useStore.ts`): Zustand for market regime and stock universe. Watchlist state is in `useWatchlist` hook (REST-backed), NOT in Zustand.
- **Watchlist badge** in `Header.tsx` reads from `useWatchlist()`, not `useStore`.
- **git staging**: `git add frontend/src/lib/api.ts` fails due to `.gitignore` `lib/` pattern. Use `git add frontend/` instead.

## Testing

55/69 tests pass. 14 pre-existing failures:
- recharts doesn't render in jsdom
- Some hook test API mock setup issues
- Multiple-element text match in a few component tests
