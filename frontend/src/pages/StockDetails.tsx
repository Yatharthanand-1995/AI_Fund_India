/**
 * StockDetails Page - Enhanced with Tabbed Interface
 *
 * Tabs:
 * - Overview: Current analysis with narrative
 * - Historical: Price/score charts and history
 * - Agents: Detailed agent breakdown
 * - Compare: Quick comparison tools
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Star,
  Activity,
  BarChart3,
  GitCompare,
  Calendar,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useWatchlist } from '@/hooks/useWatchlist';
import { useStockHistory } from '@/hooks/useStockHistory';
import api from '@/lib/api';
import Loading from '@/components/ui/Loading';
import { ChartSkeleton } from '@/components/ui/SkeletonLoader';
import StockCard from '@/components/StockCard';
import { StockPriceChart } from '@/components/charts/StockPriceChart';
import { AgentScoresRadar } from '@/components/charts/AgentScoresRadar';
import { AgentScoresBar } from '@/components/charts/AgentScoresBar';
import { CompositeScoreTrend } from '@/components/charts/CompositeScoreTrend';
import type { StockAnalysis } from '@/types';
import { ScoreBreakdown } from '@/components/ScoreBreakdown';

type TabType = 'overview' | 'historical' | 'agents' | 'compare';

export default function StockDetails() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const { addToast, setLoading, loading } = useStore();
  const { isInWatchlist, add: addToWatchlist, remove: removeFromWatchlist } = useWatchlist();

  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [comparisonSymbols, setComparisonSymbols] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<any>(null);

  // Fetch historical data for this stock
  const { data: historicalData, loading: historyLoading } = useStockHistory(
    symbol || '',
    { days: 180, enabled: !!symbol }
  );

  const inWatchlist = symbol ? isInWatchlist(symbol) : false;

  useEffect(() => {
    if (symbol) {
      loadAnalysis(symbol);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const loadAnalysis = async (sym: string) => {
    setLoading('analyze', true);
    setAnalysisError(null);

    try {
      const result = await api.analyzeStock({
        symbol: sym.toUpperCase(),
        include_narrative: true,
      });

      setAnalysis(result);
    } catch (error: any) {
      setAnalysisError(error.message || 'Failed to load stock analysis');
    } finally {
      setLoading('analyze', false);
    }
  };

  const handleWatchlistToggle = async () => {
    if (!symbol) return;

    if (inWatchlist) {
      const success = await removeFromWatchlist(symbol);
      if (success) {
        addToast({
          type: 'success',
          message: `${symbol} removed from watchlist`,
        });
      }
    } else {
      const success = await addToWatchlist(symbol);
      if (success) {
        addToast({
          type: 'success',
          message: `${symbol} added to watchlist`,
        });
      }
    }
  };

  const handleCompare = async () => {
    if (comparisonSymbols.length < 1 || !symbol) return;

    try {
      const symbols = [symbol, ...comparisonSymbols];
      const result = await api.post('/compare', { symbols, include_history: false });
      setComparisonData(result.data);
    } catch (error: any) {
      addToast({
        type: 'error',
        message: error.message || 'Failed to compare stocks',
      });
    }
  };

  if (loading.analyze) {
    return (
      <div className="py-20">
        <Loading size="lg" text={`Analyzing ${symbol}...`} />
      </div>
    );
  }

  if (analysisError) {
    return (
      <div className="py-20 text-center">
        <p className="text-red-600 font-medium mb-4">{analysisError}</p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => symbol && loadAnalysis(symbol)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: Activity },
    { id: 'historical' as TabType, label: 'Historical', icon: Calendar },
    { id: 'agents' as TabType, label: 'Agents', icon: BarChart3 },
    { id: 'compare' as TabType, label: 'Compare', icon: GitCompare },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
          <span>Back</span>
        </button>

        <button
          onClick={handleWatchlistToggle}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            inWatchlist
              ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          <Star className={`w-5 h-5 ${inWatchlist ? 'fill-current' : ''}`} />
          {inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
        </button>
      </div>

      {/* Stock Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">{analysis.symbol}</h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                Score: {analysis.composite_score.toFixed(1)}
              </span>
              <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                {analysis.recommendation}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm
                    ${isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <StockCard analysis={analysis} detailed={false} />

              {/* Entry / Exit Levels */}
              {analysis.trading_levels && (
                <div className="bg-gray-50 rounded-xl border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-500" />
                    Entry / Exit Levels
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'Stop Loss', value: analysis.trading_levels.stop_loss, prefix: '₹', color: 'text-red-600' },
                      { label: 'Target Price', value: analysis.trading_levels.target_price, prefix: '₹', color: 'text-emerald-600' },
                      { label: 'Risk / Reward', value: analysis.trading_levels.risk_reward_ratio, prefix: '', suffix: 'x', color: 'text-blue-600' },
                      { label: 'ATR (14d)', value: analysis.trading_levels.atr, prefix: '₹', color: 'text-gray-700' },
                    ].map(({ label, value, prefix, suffix, color }) => value != null && (
                      <div key={label} className="bg-white rounded-lg p-4 border border-gray-200">
                        <p className="text-xs text-gray-500 font-medium">{label}</p>
                        <p className={`text-xl font-bold mt-1 ${color}`}>
                          {prefix}{typeof value === 'number' ? value.toFixed(value < 10 ? 2 : 0) : value}{suffix || ''}
                        </p>
                      </div>
                    ))}
                  </div>
                  {analysis.week_52_high != null && analysis.week_52_low != null && (
                    <div className="mt-4">
                      <div className="flex justify-between text-xs text-gray-500 mb-1">
                        <span>52W Low: ₹{analysis.week_52_low?.toFixed(0)}</span>
                        <span>52W High: ₹{analysis.week_52_high?.toFixed(0)}</span>
                      </div>
                      <div className="relative h-2 bg-gray-200 rounded-full">
                        {analysis.current_price != null && analysis.week_52_high != null && analysis.week_52_low != null && (
                          <div
                            className="absolute h-full w-2 bg-blue-500 rounded-full -ml-1"
                            style={{
                              left: `${Math.min(100, Math.max(0, ((analysis.current_price - analysis.week_52_low) / (analysis.week_52_high - analysis.week_52_low)) * 100))}%`
                            }}
                          />
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-1 text-center">Current price position on 52W range</p>
                    </div>
                  )}
                </div>
              )}

              {/* News Sentiment */}
              {(() => {
                const s = analysis.agent_scores?.sentiment?.metrics;
                const headlines = s?.news_headline_count;
                if (!headlines || headlines === 0) return null;
                const bullish = s?.news_bullish_count ?? 0;
                const bearish = s?.news_bearish_count ?? 0;
                const neutral = headlines - bullish - bearish;
                const sentiment = s?.news_sentiment_score ?? 0;
                return (
                  <div className="bg-gray-50 rounded-xl border border-gray-200 p-5">
                    <h3 className="text-sm font-semibold text-gray-700 mb-4">News Sentiment ({headlines} headlines)</h3>
                    <div className="flex items-center gap-4 mb-3">
                      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden flex">
                        <div className="bg-emerald-400 h-full" style={{ width: `${(bullish / headlines) * 100}%` }} />
                        <div className="bg-red-400 h-full" style={{ width: `${(bearish / headlines) * 100}%` }} />
                        <div className="bg-gray-300 h-full flex-1" />
                      </div>
                      <span className={`text-sm font-bold ${sentiment > 0 ? 'text-emerald-600' : sentiment < 0 ? 'text-red-600' : 'text-gray-500'}`}>
                        {sentiment > 0 ? '+' : ''}{sentiment.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />{bullish} bullish</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" />{bearish} bearish</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />{neutral} neutral</span>
                    </div>
                  </div>
                );
              })()}

              {/* Score Breakdown */}
              <ScoreBreakdown analysis={analysis} />
            </div>
          )}

          {/* Historical Tab */}
          {activeTab === 'historical' && (
            <div className="space-y-6">
              {historyLoading ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ChartSkeleton />
                  <ChartSkeleton />
                </div>
              ) : historicalData && historicalData.history.length > 0 ? (
                <>
                  {/* Price & Score Chart */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Price & Score History
                    </h3>
                    <StockPriceChart
                      symbol={analysis.symbol}
                      data={historicalData.history}
                      height={400}
                      defaultTimeRange="6M"
                    />
                  </div>

                  {/* Composite Score Trend */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Composite Score Trend
                    </h3>
                    <CompositeScoreTrend
                      symbol={analysis.symbol}
                      data={historicalData.history}
                      height={300}
                    />
                  </div>

                  {/* Recommendation History Table */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Recent Recommendations
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Date
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Score
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Recommendation
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Confidence
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {historicalData.history.slice(0, 10).map((item: any, index: number) => (
                            <tr key={index} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {new Date(item.timestamp).toLocaleDateString('en-IN')}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                                {item.composite_score?.toFixed(1) || 'N/A'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  {item.recommendation}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                {item.confidence?.toFixed(1) || 'N/A'}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Statistics */}
                  {historicalData.statistics && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-sm text-gray-600">Average Score</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">
                          {historicalData.statistics.avg_score?.toFixed(1) || 'N/A'}
                        </p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-sm text-gray-600">Max Score</p>
                        <p className="text-2xl font-bold text-green-600 mt-1">
                          {historicalData.statistics.max_score?.toFixed(1) || 'N/A'}
                        </p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-sm text-gray-600">Min Score</p>
                        <p className="text-2xl font-bold text-red-600 mt-1">
                          {historicalData.statistics.min_score?.toFixed(1) || 'N/A'}
                        </p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-sm text-gray-600">Data Points</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">
                          {historicalData.history.length || 0}
                        </p>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12">
                  <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No historical data available yet</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Historical data will be collected automatically every 4 hours
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Agents Tab */}
          {activeTab === 'agents' && (
            <div className="space-y-6">
              {/* Score Breakdown — full interactive decomposition */}
              <ScoreBreakdown analysis={analysis} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Agent Scores Radar */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Agent Scores Overview
                  </h3>
                  <AgentScoresRadar
                    agentScores={analysis.agent_scores}
                    height={350}
                    showHistorical={false}
                  />
                </div>

                {/* Agent Scores Bar */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Agent Performance
                  </h3>
                  <AgentScoresBar
                    agentScores={analysis.agent_scores}
                    weights={analysis.weights}
                    height={350}
                    showWeights={true}
                  />
                </div>
              </div>

              {/* Individual Agent Details */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Individual Agent Analysis
                </h3>
                <div className="space-y-4">
                  {Object.entries(analysis.agent_scores).map(([agentKey, agentData]: [string, any]) => (
                    <div key={agentKey} className="bg-gray-50 rounded-lg p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-semibold text-gray-900 capitalize">
                          {agentKey.replace('_', ' ')}
                        </h4>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className="text-sm text-gray-600">Score</p>
                            <p className="text-2xl font-bold text-gray-900">
                              {agentData.score?.toFixed(1) || 'N/A'}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm text-gray-600">Weight</p>
                            <p className="text-xl font-semibold text-blue-600">
                              {((analysis.weights?.[agentKey] || 0) * 100).toFixed(0)}%
                            </p>
                          </div>
                        </div>
                      </div>
                      {agentData.reasoning && (
                        <div className="bg-white rounded p-4">
                          <p className="text-sm text-gray-700">{agentData.reasoning}</p>
                        </div>
                      )}
                      {agentData.metrics && (
                        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                          {Object.entries(agentData.metrics).map(([key, value]: [string, any]) => (
                            <div key={key} className="bg-white rounded p-3">
                              <p className="text-xs text-gray-600 capitalize">
                                {key.replace(/_/g, ' ')}
                              </p>
                              <p className="text-sm font-semibold text-gray-900 mt-1">
                                {typeof value === 'number' ? value.toFixed(2) : value}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Compare Tab */}
          {activeTab === 'compare' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Compare with Other Stocks
                </h3>

                {/* Stock Selector */}
                <div className="bg-gray-50 rounded-lg p-4 mb-6">
                  <p className="text-sm text-gray-600 mb-3">
                    Enter symbols to compare (comma-separated, max 3 additional stocks)
                  </p>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      placeholder="e.g., INFY, WIPRO, HCLTECH"
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      onChange={(e) => {
                        const symbols = e.target.value
                          .split(',')
                          .map(s => s.trim().toUpperCase())
                          .filter(s => s && s !== analysis.symbol);
                        setComparisonSymbols(symbols.slice(0, 3));
                      }}
                    />
                    <button
                      onClick={handleCompare}
                      disabled={comparisonSymbols.length === 0}
                      className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                    >
                      Compare
                    </button>
                  </div>
                  {comparisonSymbols.length > 0 && (
                    <div className="mt-3 flex gap-2">
                      <span className="text-sm text-gray-600">Comparing:</span>
                      <div className="flex gap-2">
                        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                          {analysis.symbol}
                        </span>
                        {comparisonSymbols.map(sym => (
                          <span key={sym} className="px-3 py-1 bg-gray-200 text-gray-800 rounded-full text-sm font-medium">
                            {sym}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Comparison Results */}
                {comparisonData ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Metric
                          </th>
                          {comparisonData.comparisons?.map((stock: any) => (
                            <th key={stock.symbol} className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                              {stock.symbol}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        <tr>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            Composite Score
                          </td>
                          {comparisonData.comparisons?.map((stock: any) => (
                            <td key={stock.symbol} className="px-6 py-4 whitespace-nowrap text-center text-sm font-bold text-gray-900">
                              {stock.composite_score?.toFixed(1) || 'N/A'}
                            </td>
                          ))}
                        </tr>
                        <tr className="bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            Recommendation
                          </td>
                          {comparisonData.comparisons?.map((stock: any) => (
                            <td key={stock.symbol} className="px-6 py-4 whitespace-nowrap text-center">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                {stock.recommendation || 'N/A'}
                              </span>
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            Confidence
                          </td>
                          {comparisonData.comparisons?.map((stock: any) => (
                            <td key={stock.symbol} className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                              {stock.confidence?.toFixed(1) || 'N/A'}%
                            </td>
                          ))}
                        </tr>
                        {/* Agent Scores */}
                        {['fundamentals', 'momentum', 'quality', 'sentiment', 'institutional_flow'].map(agent => (
                          <tr key={agent} className={agent === 'fundamentals' || agent === 'quality' ? 'bg-gray-50' : ''}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 capitalize">
                              {agent.replace('_', ' ')}
                            </td>
                            {comparisonData.comparisons?.map((stock: any) => (
                              <td key={stock.symbol} className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                                {stock.agent_scores?.[agent]?.score?.toFixed(1) || 'N/A'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <GitCompare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">Enter stock symbols above to compare</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
