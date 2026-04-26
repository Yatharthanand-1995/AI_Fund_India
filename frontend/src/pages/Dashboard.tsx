import { useState, useEffect, useRef, useCallback } from 'react';
import { TrendingUp, BarChart3, Star, Activity, PieChart, ArrowRight } from 'lucide-react'; // PieChart used in market overview
import { useNavigate } from 'react-router-dom';
import { useStore } from '@/store/useStore';
import api from '@/lib/api';
import Loading from '@/components/ui/Loading';
import { StockCardSkeleton, ChartSkeleton } from '@/components/ui/SkeletonLoader';
import StockCard from '@/components/StockCard';
import MarketRegimeCard from '@/components/MarketRegimeCard';
import { StockPriceChart } from '@/components/charts/StockPriceChart';
import { AgentScoresRadar } from '@/components/charts/AgentScoresRadar';
import ChartErrorBoundary from '@/components/charts/ChartErrorBoundary';
import { MarketRegimeTimeline } from '@/components/charts/MarketRegimeTimeline';
import { useWatchlist } from '@/hooks/useWatchlist';
import { useStockHistory } from '@/hooks/useStockHistory';
import { useSectorAnalysis } from '@/hooks/useSectorAnalysis';
import { SymbolInput } from '@/components/ui/SymbolInput';
import { DEFAULT_STOCK_SYMBOLS } from '@/lib/constants';
import type { StockAnalysis } from '@/types';

export default function Dashboard() {
  const navigate = useNavigate();
  const { addToast, setLoading, loading, marketRegime, recentSearches, addRecentSearch } = useStore();
  const { watchlist } = useWatchlist();
  const { getTopSectors } = useSectorAnalysis({ days: 7 });

  const [symbol, setSymbol] = useState('');
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [regimeHistory, setRegimeHistory] = useState<any[]>([]);
  const [systemStats, setSystemStats] = useState<any>(null);
  const analyzeDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load initial data
  useEffect(() => {
    loadDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Clean up pending debounce on unmount
  useEffect(() => {
    return () => {
      if (analyzeDebounceRef.current) clearTimeout(analyzeDebounceRef.current);
    };
  }, []);

  const loadDashboardData = async () => {
    try {
      // Load regime history
      const regimeData = await api.getRegimeHistory(30);
      setRegimeHistory(regimeData.history || []);

      // Load system stats
      const statsData = await api.getSystemAnalytics();
      setSystemStats(statsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.warn('[Dashboard] loadDashboardData failed:', message);
      addToast({
        type: 'info',
        message: 'Some dashboard metrics could not be loaded. The page will still function.',
      });
    }
  };

  const analyzeSymbol = useCallback((symbolToAnalyze: string) => {
    if (analyzeDebounceRef.current) {
      clearTimeout(analyzeDebounceRef.current);
    }
    analyzeDebounceRef.current = setTimeout(() => {
      doAnalyze(symbolToAnalyze);
    }, 300);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const doAnalyze = async (symbolToAnalyze: string) => {
    if (!symbolToAnalyze.trim()) {
      addToast({ type: 'warning', message: 'Please enter a stock symbol' });
      return;
    }

    setLoading('analyze', true);

    try {
      const result = await api.analyzeStock({
        symbol: symbolToAnalyze.toUpperCase(),
        include_narrative: true,
      });

      setAnalysis(result);
      addRecentSearch(symbolToAnalyze.toUpperCase());
      addToast({
        type: 'success',
        message: `Analysis complete for ${result.symbol}`,
      });
    } catch (error: any) {
      addToast({
        type: 'error',
        message: error.message || 'Failed to analyze stock',
      });
      setAnalysis(null);
    } finally {
      setLoading('analyze', false);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    await analyzeSymbol(symbol);
  };

  const quickSymbols = recentSearches.length > 0
    ? recentSearches.slice(0, 5)
    : [...DEFAULT_STOCK_SYMBOLS];

  const topSectors = getTopSectors(3);

  // Get historical data for analyzed stock
  const { data: historicalData, loading: historyLoading } = useStockHistory(
    analysis?.symbol || '',
    { days: 180, enabled: !!analysis }
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-4xl font-bold text-gray-900">
          AI-Powered Stock Analysis
        </h1>
        <p className="text-lg text-gray-600">
          Comprehensive analysis using 5 specialized AI agents
        </p>
      </div>

      {/* Market Overview — always visible when regime is available */}
      {marketRegime && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Current Market Regime */}
          <div className={`rounded-lg shadow p-6 ${
            marketRegime.trend === 'BULL' ? 'bg-green-50 border border-green-200' :
            marketRegime.trend === 'BEAR' ? 'bg-red-50 border border-red-200' :
            'bg-white'
          }`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Market Regime</p>
                <p className={`text-2xl font-bold mt-1 ${
                  marketRegime.trend === 'BULL' ? 'text-green-700' :
                  marketRegime.trend === 'BEAR' ? 'text-red-700' :
                  'text-gray-900'
                }`}>
                  {marketRegime.trend || 'N/A'}
                </p>
                <p className="text-xs text-gray-500 mt-1">{marketRegime.volatility || ''} volatility</p>
              </div>
              <Activity className="w-8 h-8 text-blue-500" />
            </div>
          </div>

          {/* Watchlist Count */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Watchlist</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{watchlist.length}</p>
                <p className="text-xs text-gray-500 mt-1">stocks tracked</p>
              </div>
              <Star className="w-8 h-8 text-yellow-500" />
            </div>
          </div>

          {/* Top Sectors */}
          {topSectors.length > 0 ? (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600">Top Sector</p>
                <PieChart className="w-6 h-6 text-indigo-500" />
              </div>
              <p className="text-lg font-bold text-gray-900">{topSectors[0]?.sector || 'N/A'}</p>
              <p className="text-xs text-gray-500 mt-1">avg score {topSectors[0]?.avg_score?.toFixed(1) || '—'}</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Analyses</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {systemStats?.total_requests?.toLocaleString() || '—'}
                  </p>
                </div>
                <BarChart3 className="w-8 h-8 text-green-500" />
              </div>
            </div>
          )}

          {/* Cache Hit Rate */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Cache Hit Rate</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {systemStats?.cache_hit_rate?.toFixed(1) || '—'}%
                </p>
                <p className="text-xs text-gray-500 mt-1">API efficiency</p>
              </div>
              <TrendingUp className="w-8 h-8 text-purple-500" />
            </div>
          </div>
        </div>
      )}

      {/* Two Column Layout - Only show when no analysis */}
      {!analysis && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Watchlist Widget */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-500" />
                My Watchlist
              </h3>
              <button
                onClick={() => navigate('/watchlist')}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                View All
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {watchlist?.length > 0 ? (
              <div className="space-y-2">
                {watchlist.slice(0, 5).map((item) => (
                  <button
                    key={item?.symbol || Math.random()}
                    onClick={() => {
                      if (item?.symbol) {
                        setSymbol(item.symbol);
                        analyzeSymbol(item.symbol);
                      }
                    }}
                    className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <span className="font-medium text-gray-900">{item?.symbol || 'Unknown'}</span>
                    <div className="flex items-center gap-3">
                      {item?.latest_score != null && (
                        <span className="text-sm font-semibold text-gray-900">
                          {item.latest_score.toFixed(1)}
                        </span>
                      )}
                      {item?.latest_recommendation && (
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                          {item.latest_recommendation}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-500 py-8">
                No stocks in watchlist yet
              </p>
            )}
          </div>

          {/* Top Sectors Widget */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-blue-500" />
                Top Sectors
              </h3>
              <button
                onClick={() => navigate('/sectors')}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                View All
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {topSectors.length > 0 ? (
              <div className="space-y-3">
                {topSectors.map((sector, index) => (
                  <div key={sector.sector} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-gray-500 w-6">
                        #{index + 1}
                      </span>
                      <div>
                        <p className="font-medium text-gray-900">{sector.sector}</p>
                        <p className="text-xs text-gray-500">{sector.stock_count} stocks</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-gray-900">
                        {sector.avg_score != null ? sector.avg_score.toFixed(1) : 'N/A'}
                      </p>
                      <p className="text-xs text-gray-500">{sector.top_pick}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-500 py-8">
                No sector data available yet
              </p>
            )}
          </div>
        </div>
      )}

      {/* Market Regime Timeline - Only show when no analysis */}
      {!analysis && regimeHistory.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <MarketRegimeTimeline
            data={regimeHistory}
            days={30}
            height={250}
            showWeights={false}
          />
        </div>
      )}

      {/* Market Regime Card */}
      {marketRegime && !analysis && (
        <div className="max-w-4xl mx-auto">
          <MarketRegimeCard regime={marketRegime} />
        </div>
      )}

      {/* Search Form */}
      <div className="max-w-2xl mx-auto">
        <form onSubmit={handleAnalyze} className="space-y-4">
          <SymbolInput
            value={symbol}
            onChange={setSymbol}
            onSubmit={analyzeSymbol}
            placeholder="Enter stock symbol (e.g., TCS, INFY, RELIANCE)"
            className="w-full pr-4 py-4 text-lg border-2 border-gray-300 rounded-lg focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none transition-all"
            disabled={loading.analyze}
            showIcon={true}
          />

          <button
            type="submit"
            disabled={loading.analyze}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white font-semibold py-4 px-6 rounded-lg transition-colors flex items-center justify-center space-x-2"
          >
            {loading.analyze ? (
              <>
                <Loading size="sm" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <BarChart3 className="h-5 w-5" />
                <span>Analyze Stock</span>
              </>
            )}
          </button>
        </form>

        {/* Quick Symbols */}
        <div className="mt-4">
          <p className="text-sm text-gray-600 mb-2">
            {recentSearches.length > 0 ? 'Recent searches:' : 'Quick analyze:'}
          </p>
          <div className="flex flex-wrap gap-2">
            {quickSymbols.map((sym) => (
              <button
                key={sym}
                onClick={() => setSymbol(sym)}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md text-sm font-medium transition-colors"
              >
                {sym}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading.analyze && (
        <div className="space-y-6 animate-fade-in">
          {/* Stock Card Skeleton */}
          <div className="max-w-6xl mx-auto">
            <StockCardSkeleton />
          </div>

          {/* Charts Skeletons */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>
        </div>
      )}

      {/* Analysis Result with Charts */}
      {analysis && !loading.analyze && (
        <div className="space-y-6 animate-fade-in">
          {/* Stock Card */}
          <div className="max-w-6xl mx-auto">
            <StockCard analysis={analysis} detailed />
          </div>

          {/* Charts Row */}
          {historyLoading && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartSkeleton />
              <ChartSkeleton />
            </div>
          )}
          {!historyLoading && historicalData && historicalData.history.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Price & Score Chart */}
              <div className="bg-white rounded-lg shadow p-6">
                <ChartErrorBoundary>
                  <StockPriceChart
                    symbol={analysis.symbol}
                    data={historicalData.history}
                    height={300}
                    defaultTimeRange="6M"
                  />
                </ChartErrorBoundary>
              </div>

              {/* Agent Scores Radar */}
              <div className="bg-white rounded-lg shadow p-6">
                <ChartErrorBoundary>
                  <AgentScoresRadar
                    agentScores={analysis.agent_scores}
                    height={300}
                    showHistorical={false}
                  />
                </ChartErrorBoundary>
              </div>
            </div>
          )}

          {/* Back to Search */}
          <div className="text-center">
            <button
              onClick={() => setAnalysis(null)}
              className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-colors"
            >
              Analyze Another Stock
            </button>
          </div>
        </div>
      )}

      {/* Call to Action */}
      {!analysis && !loading.analyze && (
        <div className="max-w-3xl mx-auto text-center space-y-6 py-12">
          <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl p-8 border border-primary-100">
            <TrendingUp className="h-12 w-12 text-primary-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Get Started
            </h3>
            <p className="text-gray-600 mb-4">
              Enter a stock symbol above to get comprehensive AI-powered analysis,
              or check out our top picks from NIFTY 50
            </p>
            <button
              onClick={() => navigate('/top-picks')}
              className="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              View Top Picks
            </button>
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            {[
              {
                title: '5 AI Agents',
                desc: 'Fundamentals, Momentum, Quality, Sentiment, Institutional Flow',
              },
              {
                title: 'Adaptive Weights',
                desc: 'Weights adjust based on market regime (Bull/Bear/Sideways)',
              },
              {
                title: 'LLM Narratives',
                desc: 'AI-generated investment thesis with strengths and risks',
              },
            ].map((feature, i) => (
              <div key={i} className="bg-white p-6 rounded-lg border border-gray-200">
                <h4 className="font-semibold text-gray-900 mb-2">{feature.title}</h4>
                <p className="text-sm text-gray-600">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
