/**
 * Optimized App Component with Code Splitting
 *
 * Performance Improvements:
 * - Lazy loading for route components
 * - Suspense boundaries for better UX
 * - Code splitting reduces initial bundle size
 */

import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/layout/Header';
import Toast from './components/ui/Toast';
import Loading from './components/ui/Loading';

// Lazy load route components for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const TopPicks = lazy(() => import('./pages/TopPicks'));
const StockDetails = lazy(() => import('./pages/StockDetails'));
const About = lazy(() => import('./pages/About'));
const Analytics = lazy(() => import('./pages/Analytics'));
const SectorAnalysis = lazy(() => import('./pages/SectorAnalysis'));
const Watchlist = lazy(() => import('./pages/Watchlist'));
const Comparison = lazy(() => import('./pages/Comparison'));

// Loading fallback component
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center">
    <Loading size="lg" text="Loading..." />
  </div>
);

function App() {

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header />

        <main className="flex-1 container mx-auto px-4 py-8">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/top-picks" element={<TopPicks />} />
              <Route path="/stock/:symbol" element={<StockDetails />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/sectors" element={<SectorAnalysis />} />
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/compare" element={<Comparison />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </Suspense>
        </main>


        {/* Toast Notifications */}
        <Toast />
      </div>
    </BrowserRouter>
  );
}

export default App;
