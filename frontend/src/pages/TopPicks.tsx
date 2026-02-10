/**
 * TopPicks Page - Enhanced with Filters and Charts
 *
 * Features:
 * - Advanced filters (sector, recommendation, sort, top N)
 * - Recommendation distribution pie chart
 * - Export functionality (CSV/JSON)
 * - Enhanced stock cards with mini charts
 */

import { useEffect, useState, useMemo, useRef } from 'react';
import { TrendingUp, Download, Filter, RefreshCw } from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useStore } from '@/store/useStore';
import api from '@/lib/api';
import { StockCardSkeleton, ChartSkeleton, SkeletonLoader } from '@/components/ui/SkeletonLoader';
import StockCard from '@/components/StockCard';
import MarketRegimeCard from '@/components/MarketRegimeCard';
import { RecommendationPie } from '@/components/charts/RecommendationPie';
import type { TopPicksResponse, StockAnalysis } from '@/types';

/**
 * Virtual scrolling component for stock lists
 * Renders only visible items for better performance with large lists
 */
function VirtualStockList({ stocks }: { stocks: StockAnalysis[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: stocks.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 280, // Estimated height of each StockCard + margin
    overscan: 3, // Render 3 extra items above/below viewport
  });

  return (
    <div
      ref={parentRef}
      className="max-w-6xl mx-auto h-[calc(100vh-300px)] overflow-auto"
      style={{ contain: 'strict' }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const pick = stocks[virtualRow.index];
          return (
            <div
              key={virtualRow.key}
              data-index={virtualRow.index}
              ref={virtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <div className="relative mb-6">
                <div className="absolute -left-12 top-6 flex flex-col items-center">
                  <span className="text-3xl font-bold text-gray-300">
                    #{virtualRow.index + 1}
                  </span>
                  <span className="text-xs text-gray-400 mt-1">
                    {pick.composite_score.toFixed(1)}
                  </span>
                </div>
                <StockCard analysis={pick} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function TopPicks() {
  const {
    addToast,
    setLoading,
    loading,
    cacheTopPicks,
    getCachedTopPicks,
  } = useStore();
  const [data, setData] = useState<TopPicksResponse | null>(null);
  const [cacheAge, setCacheAge] = useState<number | null>(null);

  // Filters
  const [topCount, setTopCount] = useState(10);
  const [sortBy, setSortBy] = useState<'score' | 'confidence' | 'symbol'>('score');
  const [sectorFilter, setSectorFilter] = useState<string>('All');
  const [recommendationFilter, setRecommendationFilter] = useState<string>('All');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadTopPicks();
  }, []);

  const loadTopPicks = async (forceRefresh = false) => {
    // Generate cache key based on parameters
    const cacheKey = `50:false`; // limit=50, include_narrative=false

    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      const cachedData = getCachedTopPicks(cacheKey);
      if (cachedData) {
        setData(cachedData);
        const age = Date.now() - (cachedData as any).cachedTimestamp || 0;
        setCacheAge(age);
        console.log('[TopPicks] Using cached data from', Math.floor(age / 60000), 'minutes ago');
        return;
      }
    }

    setLoading('topPicks', true);
    setCacheAge(null);

    try {
      // Get all stocks (we'll filter client-side)
      const result = await api.getTopPicks(50, false);

      // Add timestamp to cached data for age calculation
      const dataWithTimestamp = {
        ...result,
        cachedTimestamp: Date.now(),
      };

      // Cache the result
      cacheTopPicks(cacheKey, dataWithTimestamp as TopPicksResponse);

      setData(dataWithTimestamp as TopPicksResponse);
      setCacheAge(0);

      addToast({
        type: 'success',
        message: `Loaded ${result.top_picks.length} stocks from NIFTY 50`,
      });
    } catch (error: any) {
      addToast({
        type: 'error',
        message: error.message || 'Failed to load top picks',
      });
    } finally {
      setLoading('topPicks', false);
    }
  };

  // Get unique sectors from data
  const sectors = useMemo(() => {
    if (!data?.top_picks) return ['All'];

    const uniqueSectors = new Set<string>();
    data.top_picks.forEach(pick => {
      // Extract sector from agent_scores if available
      const fundamentals = pick.agent_scores?.fundamentals;
      if (fundamentals?.metrics?.sector) {
        uniqueSectors.add(fundamentals.metrics.sector);
      }
    });

    return ['All', ...Array.from(uniqueSectors).sort()];
  }, [data]);

  // Get unique recommendations
  const recommendations = useMemo(() => {
    if (!data?.top_picks) return ['All'];

    const uniqueRecs = new Set<string>();
    data.top_picks.forEach(pick => {
      if (pick.recommendation) {
        uniqueRecs.add(pick.recommendation);
      }
    });

    return ['All', ...Array.from(uniqueRecs).sort()];
  }, [data]);

  // Filter and sort picks
  const filteredPicks = useMemo(() => {
    if (!data?.top_picks) return [];

    let filtered = [...data.top_picks];

    // Apply sector filter
    if (sectorFilter !== 'All') {
      filtered = filtered.filter(pick => {
        const sector = pick.agent_scores?.fundamentals?.metrics?.sector;
        return sector === sectorFilter;
      });
    }

    // Apply recommendation filter
    if (recommendationFilter !== 'All') {
      filtered = filtered.filter(pick => pick.recommendation === recommendationFilter);
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'score':
          return b.composite_score - a.composite_score;
        case 'confidence':
          return b.confidence - a.confidence;
        case 'symbol':
          return a.symbol.localeCompare(b.symbol);
        default:
          return 0;
      }
    });

    // Limit to topCount
    return filtered.slice(0, topCount);
  }, [data, sectorFilter, recommendationFilter, sortBy, topCount]);

  // Recommendation distribution data for pie chart
  const recommendationDistribution = useMemo(() => {
    if (!data?.top_picks) return [];

    const counts: Record<string, number> = {};
    data.top_picks.forEach(pick => {
      const rec = pick.recommendation || 'UNKNOWN';
      counts[rec] = (counts[rec] || 0) + 1;
    });

    return Object.entries(counts).map(([recommendation, count]) => ({
      recommendation,
      count,
      percentage: (count / data.top_picks.length) * 100
    }));
  }, [data]);

  // Export functions
  const exportToCSV = () => {
    if (!filteredPicks.length) return;

    const headers = [
      'Symbol',
      'Composite Score',
      'Recommendation',
      'Confidence',
      'Fundamentals',
      'Momentum',
      'Quality',
      'Sentiment',
      'Institutional'
    ];

    const rows = filteredPicks.map(pick => [
      pick.symbol,
      pick.composite_score.toFixed(2),
      pick.recommendation,
      pick.confidence.toFixed(2),
      pick.agent_scores?.fundamentals?.score?.toFixed(2) || 'N/A',
      pick.agent_scores?.momentum?.score?.toFixed(2) || 'N/A',
      pick.agent_scores?.quality?.score?.toFixed(2) || 'N/A',
      pick.agent_scores?.sentiment?.score?.toFixed(2) || 'N/A',
      pick.agent_scores?.institutional_flow?.score?.toFixed(2) || 'N/A'
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    downloadFile(csvContent, 'top-picks.csv', 'text/csv');
  };

  const exportToJSON = () => {
    if (!filteredPicks.length) return;

    const jsonContent = JSON.stringify({
      market_regime: data?.market_regime,
      timestamp: new Date().toISOString(),
      total_picks: filteredPicks.length,
      filters: {
        sector: sectorFilter,
        recommendation: recommendationFilter,
        sortBy,
        topCount
      },
      picks: filteredPicks
    }, null, 2);

    downloadFile(jsonContent, 'top-picks.json', 'application/json');
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    addToast({
      type: 'success',
      message: `Exported ${filteredPicks.length} stocks to ${filename}`,
    });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center space-x-3">
          <TrendingUp className="h-10 w-10 text-primary-600" />
          <h1 className="text-4xl font-bold text-gray-900">Top Picks</h1>
        </div>
        <p className="text-lg text-gray-600">
          Best opportunities from NIFTY 50 based on AI analysis
        </p>
      </div>

      {/* Market Regime */}
      {data?.market_regime && (
        <div className="max-w-4xl mx-auto">
          <MarketRegimeCard regime={data.market_regime} />
        </div>
      )}

      {/* Recommendation Distribution Chart */}
      {!loading.topPicks && recommendationDistribution.length > 0 && (
        <div className="max-w-4xl mx-auto bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recommendation Distribution
          </h3>
          <RecommendationPie
            data={recommendationDistribution}
            height={300}
          />
        </div>
      )}

      {/* Controls */}
      <div className="max-w-6xl mx-auto bg-white rounded-lg shadow border border-gray-200">
        {/* Main Controls Row */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              <Filter className="w-4 h-4" />
              {showFilters ? 'Hide' : 'Show'} Filters
            </button>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Top:</label>
              <select
                value={topCount}
                onChange={(e) => setTopCount(Number(e.target.value))}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none"
                disabled={loading.topPicks}
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={15}>15</option>
                <option value={20}>20</option>
                <option value={30}>30</option>
                <option value={50}>50</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Export Buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={exportToCSV}
                disabled={!filteredPicks.length}
                className="flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                title="Export to CSV"
              >
                <Download className="w-4 h-4" />
                CSV
              </button>
              <button
                onClick={exportToJSON}
                disabled={!filteredPicks.length}
                className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                title="Export to JSON"
              >
                <Download className="w-4 h-4" />
                JSON
              </button>
            </div>

            <button
              onClick={() => loadTopPicks(true)}
              disabled={loading.topPicks}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:bg-gray-300"
              title={cacheAge !== null ? 'Force refresh from server' : 'Refresh data'}
            >
              <RefreshCw className={`w-4 h-4 ${loading.topPicks ? 'animate-spin' : ''}`} />
              {cacheAge !== null ? 'Force Refresh' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Advanced Filters (Collapsible) */}
        {showFilters && (
          <div className="p-4 bg-gray-50 border-b border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none"
                >
                  <option value="score">Composite Score</option>
                  <option value="confidence">Confidence</option>
                  <option value="symbol">Symbol (A-Z)</option>
                </select>
              </div>

              {/* Sector Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sector
                </label>
                <select
                  value={sectorFilter}
                  onChange={(e) => setSectorFilter(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none"
                >
                  {sectors.map(sector => (
                    <option key={sector} value={sector}>{sector}</option>
                  ))}
                </select>
              </div>

              {/* Recommendation Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Recommendation
                </label>
                <select
                  value={recommendationFilter}
                  onChange={(e) => setRecommendationFilter(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none"
                >
                  {recommendations.map(rec => (
                    <option key={rec} value={rec}>{rec}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Filter Summary */}
            <div className="mt-4 flex items-center justify-between text-sm">
              <div className="text-gray-600">
                Showing {filteredPicks.length} of {data?.top_picks.length || 0} stocks
              </div>
              {(sectorFilter !== 'All' || recommendationFilter !== 'All') && (
                <button
                  onClick={() => {
                    setSectorFilter('All');
                    setRecommendationFilter('All');
                  }}
                  className="text-blue-600 hover:text-blue-700"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>
        )}

        {/* Metadata Row */}
        {data && (
          <div className="px-4 py-2 bg-gray-50 text-sm text-gray-600 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span>
                Analyzed {data.total_analyzed} stocks in {data.duration_seconds.toFixed(1)}s
              </span>
              {cacheAge !== null && cacheAge > 0 && (
                <span className="text-blue-600 text-xs font-medium">
                  📦 Cached from {Math.floor(cacheAge / 60000)} {Math.floor(cacheAge / 60000) === 1 ? 'minute' : 'minutes'} ago
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">
              Last updated: {new Date(data.timestamp).toLocaleString('en-IN')}
            </span>
          </div>
        )}
      </div>

      {/* Loading with Skeletons */}
      {loading.topPicks && (
        <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <ChartSkeleton />
            <SkeletonLoader type="text" count={3} />
          </div>
          {[...Array(5)].map((_, i) => (
            <StockCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Results with Virtual Scrolling */}
      {!loading.topPicks && filteredPicks.length > 0 && (
        <VirtualStockList stocks={filteredPicks} />
      )}

      {/* No Results */}
      {!loading.topPicks && data && filteredPicks.length === 0 && (
        <div className="text-center py-20">
          <Filter className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">No stocks match your filters</p>
          <button
            onClick={() => {
              setSectorFilter('All');
              setRecommendationFilter('All');
            }}
            className="text-blue-600 hover:text-blue-700"
          >
            Clear all filters
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading.topPicks && !data && (
        <div className="text-center py-20">
          <TrendingUp className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">No data available</p>
          <button
            onClick={() => loadTopPicks()}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
          >
            Load Top Picks
          </button>
        </div>
      )}
    </div>
  );
}
