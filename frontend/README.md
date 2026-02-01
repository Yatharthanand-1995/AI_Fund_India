# AI Hedge Fund - React Frontend

Modern, responsive web interface for the AI Hedge Fund stock analysis system.

## Features

- **Stock Analysis Dashboard** - Search and analyze any Indian stock
- **Top Picks** - View best opportunities from NIFTY 50
- **Market Regime Display** - Real-time market conditions with adaptive weights
- **Detailed Stock Cards** - Comprehensive analysis with all 5 agents
- **LLM Narratives** - AI-generated investment thesis
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Real-time Updates** - Live data from FastAPI backend

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Zustand** - Lightweight state management
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Recharts** - Data visualization
- **Lucide React** - Beautiful icons

## Quick Start

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

### From Project Root

```bash
# Install frontend dependencies
make frontend-install

# Start frontend dev server
make frontend-dev

# Build for production
make frontend-build
```

## Development

### Available Scripts

```bash
# Development server with hot reload
npm run dev

# Type check without emitting files
npm run type-check

# Lint code
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

### Project Structure

```
frontend/
├── src/
│   ├── components/         # Reusable components
│   │   ├── layout/        # Layout components (Header, Footer)
│   │   ├── ui/            # UI components (Loading, Toast, etc.)
│   │   ├── StockCard.tsx  # Stock analysis card
│   │   └── MarketRegimeCard.tsx
│   ├── pages/             # Page components
│   │   ├── Dashboard.tsx  # Main search page
│   │   ├── TopPicks.tsx   # Top picks from NIFTY 50
│   │   ├── StockDetails.tsx
│   │   └── About.tsx      # About page
│   ├── lib/               # Utilities and helpers
│   │   ├── api.ts         # API client
│   │   └── utils.ts       # Helper functions
│   ├── store/             # State management
│   │   └── useStore.ts    # Zustand store
│   ├── types/             # TypeScript types
│   │   └── index.ts
│   ├── App.tsx            # Main app component
│   ├── main.tsx           # Entry point
│   └── index.css          # Global styles
├── public/                # Static assets
├── index.html             # HTML template
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Pages

### 1. Dashboard (`/`)
- Search bar for stock symbols
- Quick analyze buttons for popular stocks
- Market regime card
- Detailed analysis results
- Features showcase

### 2. Top Picks (`/top-picks`)
- Ranked list of best stocks from NIFTY 50
- Configurable number of results (5/10/15/20)
- Market regime display
- Quick overview cards

### 3. Stock Details (`/stock/:symbol`)
- Full detailed analysis
- All agent scores with reasoning
- Investment narrative (if available)
- Strengths and risks

### 4. About (`/about`)
- System overview
- Agent descriptions
- Feature list
- Tech stack
- Disclaimer

## API Integration

The frontend communicates with the FastAPI backend through the API client (`src/lib/api.ts`).

### API Endpoints Used

```typescript
// Analyze single stock
api.analyzeStock({ symbol: 'TCS', include_narrative: true })

// Batch analysis
api.analyzeBatch({ symbols: ['TCS', 'INFY'], sort_by: 'score' })

// Top picks
api.getTopPicks(limit, include_narrative)

// Market regime
api.getMarketRegime()

// Health check
api.getHealth()

// Stock universe
api.getStockUniverse()
```

### Development Proxy

In development, Vite proxies `/api/*` requests to `http://localhost:8000`:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

## State Management

Uses Zustand for global state:

```typescript
const {
  marketRegime,      // Current market regime
  stockUniverse,     // Available stocks
  analysisCache,     // Cached analyses
  loading,           // Loading states
  toasts,            // Toast notifications
  selectedStock,     // Selected stock
  searchQuery,       // Search query
} = useStore();
```

## Styling

Uses Tailwind CSS with custom configuration:

```javascript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      primary: { /* blue shades */ },
      success: { /* green shades */ },
      danger: { /* red shades */ },
      warning: { /* orange shades */ },
    },
  },
}
```

## Components

### StockCard
Displays comprehensive stock analysis with:
- Composite score and recommendation
- All 5 agent scores with progress bars
- Investment narrative (optional)
- Link to detailed view

### MarketRegimeCard
Shows current market conditions:
- Trend badge (BULL/BEAR/SIDEWAYS)
- Volatility level
- Adaptive agent weights
- Market metrics (NIFTY price, SMA, volatility)

### Loading
Reusable loading spinner:
- 3 sizes (sm/md/lg)
- Optional text
- Fullscreen mode

### Toast
Notification system:
- 4 types (success/error/warning/info)
- Auto-dismiss
- Manual close
- Stacked notifications

## Utilities

### Formatting
```typescript
formatNumber(1234567)       // "12,34,567"
formatPercent(0.15)         // "15.0%"
formatDate(new Date())      // "31 Jan 2026, 10:30"
```

### Colors
```typescript
getRecommendationColor('STRONG BUY')  // Tailwind classes
getScoreColor(85)                      // Score-based color
getTrendColor('BULL')                  // Trend badge color
```

### Clipboard
```typescript
await copyToClipboard('TCS')  // Copy to clipboard
```

## Build & Deploy

### Production Build

```bash
npm run build
```

Output: `dist/` directory

### Preview Production Build

```bash
npm run preview
```

### Deploy

The built files can be deployed to:
- **Vercel** (recommended)
- **Netlify**
- **GitHub Pages**
- **AWS S3 + CloudFront**
- Any static file hosting

#### Example: Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

#### Example: Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --dir=dist --prod
```

### Environment Variables

For production, set:

```bash
VITE_API_URL=https://your-api-domain.com
```

## TypeScript

Full TypeScript support with strict mode:

```typescript
// All API responses are typed
const analysis: StockAnalysis = await api.analyzeStock(...)

// State is typed
const loading: boolean = useStore((state) => state.loading.analyze)

// Component props are typed
interface StockCardProps {
  analysis: StockAnalysis;
  detailed?: boolean;
}
```

## Performance

### Optimizations
- Code splitting with React Router
- Lazy loading of pages (if needed)
- API response caching (15 minutes)
- Zustand for efficient state updates
- Tailwind CSS purging for small bundle size

### Bundle Size
- React + dependencies: ~150 KB (gzipped)
- Application code: ~50 KB (gzipped)
- Total: ~200 KB (gzipped)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Troubleshooting

### API Connection Issues

If you see "No response from server":

1. Check if backend is running: `curl http://localhost:8000/health`
2. Verify proxy configuration in `vite.config.ts`
3. Check CORS settings in backend

### Build Issues

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf .vite
```

### Type Errors

```bash
# Run type check
npm run type-check
```

## Contributing

1. Follow TypeScript best practices
2. Use Tailwind CSS for styling
3. Keep components small and focused
4. Add proper TypeScript types
5. Test with backend API

## License

Same as parent project
