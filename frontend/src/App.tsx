import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useEffect, lazy, Suspense } from 'react';
import Header from './components/layout/Header';
import { logger } from './lib/logger';
import Dashboard from './pages/Dashboard';
import Ideas from './pages/Ideas';
import About from './pages/About';
import NotFound from './pages/NotFound';
import Toast from './components/ui/Toast';
import ErrorBoundary from './components/ErrorBoundary';
import Loading from './components/ui/Loading';
import { useStore } from './store/useStore';
import api from './lib/api';

// Lazy load heavy/less frequently accessed pages
const StockDetails = lazy(() => import('./pages/StockDetails'));
const Analytics = lazy(() => import('./pages/Analytics'));
const SectorAnalysis = lazy(() => import('./pages/SectorAnalysis'));
const WatchlistEnhanced = lazy(() => import('./pages/WatchlistEnhanced'));
const Comparison = lazy(() => import('./pages/Comparison'));
const Backtest = lazy(() => import('./pages/Backtest'));
const SystemHealth = lazy(() => import('./pages/SystemHealth'));
const Screener = lazy(() => import('./pages/Screener'));
const Suggestions = lazy(() => import('./pages/Suggestions'));

function App() {
  const { setMarketRegime, setStockUniverse, cacheTopPicks } = useStore();

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Load market regime
      try {
        logger.log('[App] Loading market regime...');
        const regime = await api.getMarketRegime();
        logger.log('[App] Market regime loaded:', regime);
        setMarketRegime(regime);
      } catch (err) {
        // Market regime load failed, but not critical
        logger.error('[App] Market regime failed:', err);
      }

      // Load stock universe (optional - continue if it fails)
      try {
        logger.log('[App] Loading stock universe...');
        const universe = await api.getStockUniverse();
        logger.log('[App] Stock universe loaded:', universe);
        setStockUniverse(universe);
      } catch (err) {
        // Log the actual error so we can see what's failing
        logger.error('[App] Failed to load stock universe:', err);
        logger.error('[App] Error details:', err instanceof Error ? err.message : String(err));
        // Set default empty universe on error
        setStockUniverse({
          total_stocks: 0,
          indices: {},
          timestamp: new Date().toISOString()
        });
      }

      // Preload top picks in background (optional - silently fails)
      try {
        logger.log('[App] Preloading top picks...');
        const topPicks = await api.getTopPicks(50, false);
        const cacheKey = `50:false`;
        // cacheTopPicks already adds timestamp internally
        cacheTopPicks(cacheKey, topPicks);
        logger.log('[App] Top picks preloaded and cached');
      } catch (err) {
        // Silently fail - not critical
        logger.log('[App] Top picks preloading failed (non-critical):', err instanceof Error ? err.message : String(err));
      }
    } catch (error) {
      // Failed to load initial data, but app can still function
    }
  };

  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <ErrorBoundary>
          <Header />
        </ErrorBoundary>
        <main className="flex-grow container mx-auto px-4 py-8">
          <ErrorBoundary>
            <Suspense fallback={<div className="py-20"><Loading size="lg" text="Loading page..." /></div>}>
              <Routes>
                <Route path="/" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
                <Route path="/ideas" element={<ErrorBoundary><Ideas /></ErrorBoundary>} />
                <Route path="/top-picks" element={<ErrorBoundary><Ideas /></ErrorBoundary>} /> {/* Legacy redirect */}
                <Route path="/screener" element={<ErrorBoundary><Screener /></ErrorBoundary>} />
                <Route path="/suggestions" element={<ErrorBoundary><Suggestions /></ErrorBoundary>} />
                <Route path="/stock/:symbol" element={<ErrorBoundary><StockDetails /></ErrorBoundary>} />
                <Route path="/analytics" element={<ErrorBoundary><Analytics /></ErrorBoundary>} />
                <Route path="/sectors" element={<ErrorBoundary><SectorAnalysis /></ErrorBoundary>} />
                <Route path="/watchlist" element={<ErrorBoundary><WatchlistEnhanced /></ErrorBoundary>} />
                <Route path="/compare" element={<ErrorBoundary><Comparison /></ErrorBoundary>} />
                <Route path="/backtest" element={<ErrorBoundary><Backtest /></ErrorBoundary>} />
                <Route path="/system" element={<ErrorBoundary><SystemHealth /></ErrorBoundary>} />
                <Route path="/about" element={<ErrorBoundary><About /></ErrorBoundary>} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </main>
        <Toast />
      </div>
    </Router>
  );
}

export default App;
