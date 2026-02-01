import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import Header from './components/layout/Header';
import Dashboard from './pages/Dashboard';
import TopPicks from './pages/TopPicks';
import StockDetails from './pages/StockDetails';
import About from './pages/About';
import Analytics from './pages/Analytics';
import SectorAnalysis from './pages/SectorAnalysis';
import Watchlist from './pages/Watchlist';
import Comparison from './pages/Comparison';
import Toast from './components/ui/Toast';
import { useStore } from './store/useStore';
import api from './lib/api';

function App() {
  const { setMarketRegime, setStockUniverse, addToast } = useStore();

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Load market regime
      try {
        const regime = await api.getMarketRegime();
        setMarketRegime(regime);
      } catch (err) {
        console.warn('Could not load market regime:', err);
      }

      // Load stock universe (optional - continue if it fails)
      try {
        const universe = await api.getStockUniverse();
        setStockUniverse(universe);
      } catch (err) {
        console.warn('Could not load stock universe:', err);
        // Set default empty universe
        setStockUniverse({
          total_stocks: 0,
          indices: {},
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error('Failed to load initial data:', error);
      // Don't show toast if we got here, individual errors are handled above
    }
  };

  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <Header />
        <main className="flex-grow container mx-auto px-4 py-8">
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
        </main>
        <Toast />
      </div>
    </Router>
  );
}

export default App;
