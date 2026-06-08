import { useState, useEffect, useRef, useCallback } from 'react';
import {
  TrendingUp, Activity, Star, ArrowRight,
  BarChart3, RefreshCw, Search, Zap, PieChart, ChevronRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '@/store/useStore';
import api from '@/lib/api';
import Loading from '@/components/ui/Loading';
import { StockCardSkeleton } from '@/components/ui/SkeletonLoader';
import StockCard from '@/components/StockCard';
import { MarketRegimeTimeline } from '@/components/charts/MarketRegimeTimeline';
import { useWatchlist } from '@/hooks/useWatchlist';
import { useSectorAnalysis } from '@/hooks/useSectorAnalysis';
import { SymbolInput } from '@/components/ui/SymbolInput';
import { DEFAULT_STOCK_SYMBOLS } from '@/lib/constants';
import { AgentScoresRadar } from '@/components/charts/AgentScoresRadar';
import { StockPriceChart } from '@/components/charts/StockPriceChart';
import ChartErrorBoundary from '@/components/charts/ChartErrorBoundary';
import { useStockHistory } from '@/hooks/useStockHistory';
import SignalFeed from '@/components/SignalFeed';
import type { StockAnalysis } from '@/types';
import { cn } from '@/lib/utils';

// ── helpers ───────────────────────────────────────────────────────────────────

function pct(v: number | null | undefined) {
  if (v == null) return '—';
  const s = Math.abs(v).toFixed(1) + '%';
  return v >= 0 ? '+' + s : '-' + s;
}

function scoreColor(s: number) {
  if (s >= 70) return 'text-emerald-600';
  if (s >= 50) return 'text-amber-600';
  return 'text-red-500';
}

function SignalBadge({ signal }: { signal: string }) {
  const map: Record<string, string> = {
    BUY: 'bg-emerald-100 text-emerald-700',
    STRONG_BUY: 'bg-emerald-200 text-emerald-800',
    SELL: 'bg-red-100 text-red-700',
    HOLD: 'bg-amber-100 text-amber-700',
  };
  return (
    <span className={cn('text-xs font-semibold px-2 py-0.5 rounded', map[signal] || 'bg-gray-100 text-gray-600')}>
      {signal.replace('_', ' ')}
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate();
  const { addToast, setLoading, loading, marketRegime, recentSearches, addRecentSearch, getCachedTopPicks } = useStore();
  const { watchlist } = useWatchlist();
  const { getTopSectors } = useSectorAnalysis({ days: 7 });

  const [symbol, setSymbol] = useState('');
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [regimeHistory, setRegimeHistory] = useState<any[]>([]);
  const [portfolioPerf, setPortfolioPerf] = useState<any>(null);
  const [topPicks, setTopPicks] = useState<StockAnalysis[]>([]);
  const [topPicksLoading, setTopPicksLoading] = useState(false);
  const analyzeDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    loadDashboardData();
    return () => { if (analyzeDebounceRef.current) clearTimeout(analyzeDebounceRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadDashboardData = async () => {
    // Regime history
    try {
      const d = await api.getRegimeHistory(30);
      setRegimeHistory(d.history || []);
    } catch { /* non-critical */ }

    // Portfolio P&L
    try {
      const perf = await api.getPortfolioPerformance();
      setPortfolioPerf(perf);
    } catch { /* no portfolio yet */ }

    // Top 5 picks (use cache if available)
    const cached = getCachedTopPicks('10:false');
    if (cached) {
      setTopPicks((cached as any).top_picks?.slice(0, 5) || []);
    } else {
      setTopPicksLoading(true);
      try {
        const picks = await api.getTopPicks(10, false);
        setTopPicks(picks.top_picks?.slice(0, 5) || []);
      } catch { /* skip */ } finally {
        setTopPicksLoading(false);
      }
    }
  };

  const doAnalyze = useCallback(async (sym: string) => {
    const s = sym.trim();
    if (!s) { addToast({ type: 'warning', message: 'Enter a stock symbol' }); return; }
    setLoading('analyze', true);
    try {
      const result = await api.analyzeStock({ symbol: s.toUpperCase(), include_narrative: true });
      setAnalysis(result);
      addRecentSearch(s.toUpperCase());
      addToast({ type: 'success', message: `Analysis complete for ${result.symbol}` });
    } catch (err: any) {
      addToast({ type: 'error', message: err.message || 'Analysis failed' });
      setAnalysis(null);
    } finally {
      setLoading('analyze', false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const analyzeSymbol = useCallback((sym: string) => {
    if (analyzeDebounceRef.current) clearTimeout(analyzeDebounceRef.current);
    analyzeDebounceRef.current = setTimeout(() => doAnalyze(sym), 300);
  }, [doAnalyze]);

  const { data: historicalData, loading: historyLoading } = useStockHistory(
    analysis?.symbol || '', { days: 180, enabled: !!analysis }
  );

  const topSectors = getTopSectors(3);
  const quickSymbols = recentSearches.length > 0 ? recentSearches.slice(0, 5) : [...DEFAULT_STOCK_SYMBOLS].slice(0, 5);

  // Market regime display
  const regimeTrend = marketRegime?.trend;
  const regimeColor = regimeTrend === 'BULL' ? 'text-emerald-700' : regimeTrend === 'BEAR' ? 'text-red-700' : 'text-amber-700';
  const regimeBg = regimeTrend === 'BULL' ? 'bg-emerald-50 border-emerald-200' : regimeTrend === 'BEAR' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200';

  // Portfolio stats
  const totalReturn = portfolioPerf?.total_return_pct;
  const activeHoldings = portfolioPerf?.active_holdings ?? 0;

  return (
    <div className="space-y-6">

      {/* ── Row 1: KPI strip ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Market Regime */}
        <div className={cn('rounded-xl border p-5 flex items-center justify-between', regimeBg)}>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Market Regime</p>
            <p className={cn('text-2xl font-bold mt-1', regimeColor)}>{regimeTrend || '—'}</p>
            <p className="text-xs text-gray-400 mt-0.5">{marketRegime?.volatility || ''} vol</p>
          </div>
          <Activity className="w-8 h-8 text-gray-300" />
        </div>

        {/* Portfolio P&L */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Portfolio P&L</p>
            <p className={cn('text-2xl font-bold mt-1', totalReturn == null ? 'text-gray-400' : totalReturn >= 0 ? 'text-emerald-600' : 'text-red-600')}>
              {totalReturn == null ? '—' : pct(totalReturn)}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">{activeHoldings} active holdings</p>
          </div>
          <Zap className="w-8 h-8 text-gray-300" />
        </div>

        {/* Watchlist */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Watchlist</p>
            <p className="text-2xl font-bold mt-1 text-gray-900">{watchlist.length}</p>
            <p className="text-xs text-gray-400 mt-0.5">stocks tracked</p>
          </div>
          <Star className="w-8 h-8 text-gray-300" />
        </div>

        {/* Top Sector */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Top Sector</p>
            <p className="text-lg font-bold mt-1 text-gray-900 leading-tight">{topSectors[0]?.sector || '—'}</p>
            <p className="text-xs text-gray-400 mt-0.5">avg score {topSectors[0]?.avg_score?.toFixed(1) || '—'}</p>
          </div>
          <PieChart className="w-8 h-8 text-gray-300" />
        </div>
      </div>

      {/* ── Row 2: Top Picks + Watchlist + Sectors ───────────────────────────── */}
      {!analysis && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* Top 5 Picks */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-500" />
                Top Picks
              </h3>
              <button onClick={() => navigate('/research')} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
                All Ideas <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            {topPicksLoading ? (
              <div className="flex justify-center py-6"><Loading size="sm" /></div>
            ) : topPicks.length > 0 ? (
              <div className="space-y-2">
                {topPicks.map((s, i) => (
                  <button
                    key={s.symbol}
                    onClick={() => { setSymbol(s.symbol); analyzeSymbol(s.symbol); }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors text-left"
                  >
                    <span className="text-xs text-gray-400 w-4 font-mono">#{i + 1}</span>
                    <span className="font-semibold text-gray-900 flex-1 text-sm">{s.symbol}</span>
                    <span className={cn('text-sm font-bold', scoreColor(s.composite_score))}>
                      {s.composite_score.toFixed(1)}
                    </span>
                    <SignalBadge signal={s.recommendation} />
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-6">No picks loaded</p>
            )}
          </div>

          {/* Watchlist */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <Star className="w-4 h-4 text-yellow-500" />
                My Watchlist
              </h3>
              <button onClick={() => navigate('/watchlist')} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
                Manage <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            {watchlist.length > 0 ? (
              <div className="space-y-2">
                {watchlist.slice(0, 5).map(item => (
                  <button
                    key={item?.symbol}
                    onClick={() => { if (item?.symbol) { setSymbol(item.symbol); analyzeSymbol(item.symbol); } }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors text-left"
                  >
                    <span className="font-semibold text-gray-900 flex-1 text-sm">{item.symbol}</span>
                    {item.latest_score != null && (
                      <span className={cn('text-sm font-bold', scoreColor(item.latest_score))}>
                        {item.latest_score.toFixed(1)}
                      </span>
                    )}
                    {item.latest_recommendation && <SignalBadge signal={item.latest_recommendation} />}
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-sm text-gray-400 mb-3">No stocks in watchlist</p>
                <button
                  onClick={() => navigate('/research')}
                  className="text-xs text-blue-600 hover:text-blue-700 underline"
                >
                  Browse top picks →
                </button>
              </div>
            )}
          </div>

          {/* Sectors */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <PieChart className="w-4 h-4 text-indigo-500" />
                Sector Snapshot
              </h3>
              <button onClick={() => navigate('/analytics')} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
                Deep Dive <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            {topSectors.length > 0 ? (
              <div className="space-y-3">
                {topSectors.map((sector, i) => (
                  <div key={sector.sector} className="flex items-center gap-3">
                    <span className="text-xs font-bold text-gray-400 w-5">#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{sector.sector}</p>
                      <div className="mt-1 h-1.5 bg-gray-100 rounded-full">
                        <div
                          className="h-1.5 bg-blue-500 rounded-full"
                          style={{ width: `${Math.min(100, sector.avg_score)}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-sm font-bold text-gray-900 tabular-nums">
                      {sector.avg_score?.toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-6">No sector data yet</p>
            )}
          </div>
        </div>
      )}

      {/* ── Row 3: Signal Feed ──────────────────────────────────────────────── */}
      {!analysis && watchlist.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <SignalFeed maxItems={5} compact />
        </div>
      )}

      {/* ── Row 4: Regime Timeline ───────────────────────────────────────────── */}
      {!analysis && regimeHistory.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <MarketRegimeTimeline data={regimeHistory} days={30} height={200} showWeights={false} />
        </div>
      )}

      {/* ── Row 4: Quick Analyze ─────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Search className="w-4 h-4 text-gray-400" />
          Quick Analyze
        </h3>
        <form
          onSubmit={e => { e.preventDefault(); analyzeSymbol(symbol); }}
          className="flex gap-3 max-w-xl"
        >
          <div className="flex-1">
            <SymbolInput
              value={symbol}
              onChange={setSymbol}
              onSubmit={analyzeSymbol}
              placeholder="Symbol, e.g. TCS, INFY, RELIANCE"
              disabled={loading.analyze}
              showIcon={false}
            />
          </div>
          <button
            type="submit"
            disabled={loading.analyze}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            {loading.analyze ? <RefreshCw className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            Analyze
          </button>
        </form>
        <div className="flex flex-wrap gap-2 mt-3">
          {quickSymbols.map(s => (
            <button
              key={s}
              onClick={() => { setSymbol(s); analyzeSymbol(s); }}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* ── Analysis loading skeleton ────────────────────────────────────────── */}
      {loading.analyze && (
        <div className="space-y-5 animate-fade-in">
          <StockCardSkeleton />
        </div>
      )}

      {/* ── Analysis result ──────────────────────────────────────────────────── */}
      {analysis && !loading.analyze && (
        <div className="space-y-5 animate-fade-in">
          <StockCard analysis={analysis} detailed />

          {!historyLoading && historicalData && historicalData.history.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <ChartErrorBoundary>
                  <StockPriceChart symbol={analysis.symbol} data={historicalData.history} height={280} defaultTimeRange="6M" />
                </ChartErrorBoundary>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <ChartErrorBoundary>
                  <AgentScoresRadar agentScores={analysis.agent_scores} height={280} showHistorical={false} />
                </ChartErrorBoundary>
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={() => setAnalysis(null)}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg transition-colors"
            >
              ← Back to Dashboard
            </button>
            <button
              onClick={() => navigate(`/stock/${analysis.symbol}`)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1"
            >
              Full Analysis <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
