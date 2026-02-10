/**
 * Portfolio Analytics Component
 *
 * Tracks watchlist performance over time with metrics and charts
 */

import { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Percent, AlertTriangle } from 'lucide-react';
import Card from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';
import { useWatchlist } from '@/hooks/useWatchlist';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6'];

export default function PortfolioAnalytics() {
  const { watchlist } = useWatchlist();
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    if (watchlist.length > 0) {
      loadAnalytics();
    } else {
      setLoading(false);
    }
  }, [watchlist]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      // Get latest analysis for all watchlist stocks
      const symbols = watchlist.map(w => w.symbol);
      const analyses = await Promise.all(
        symbols.slice(0, 10).map(symbol => // Limit to 10 for performance
          api.analyzeStock({ symbol, include_narrative: false })
            .catch(() => null)
        )
      );

      const validAnalyses = analyses.filter(a => a !== null);

      if (validAnalyses.length === 0) {
        setAnalytics({ error: 'Could not load analysis for watchlist stocks. Check your connection.' });
        setLoading(false);
        return;
      }

      // Calculate portfolio metrics
      const avgScore = validAnalyses.reduce((sum, a) => sum + a.composite_score, 0) / validAnalyses.length;
      const recommendations = validAnalyses.reduce((acc, a) => {
        acc[a.recommendation] = (acc[a.recommendation] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      // Sector distribution
      const sectors = validAnalyses.reduce((acc, a) => {
        const sector = a.agent_scores.fundamentals?.metrics?.sector ||
                       a.agent_scores.quality?.metrics?.sector || 'Unknown';
        acc[sector] = (acc[sector] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      // Returns distribution
      const returns = validAnalyses.map(a => ({
        symbol: a.symbol,
        '1m': a.agent_scores.momentum?.metrics?.['1m_return'] || 0,
        '3m': a.agent_scores.momentum?.metrics?.['3m_return'] || 0,
        '6m': a.agent_scores.momentum?.metrics?.['6m_return'] || 0,
      }));

      // Portfolio returns
      const returnCount = returns.length || 1; // avoid division by zero
      const avgReturns = {
        '1m': returns.reduce((sum, r) => sum + r['1m'], 0) / returnCount,
        '3m': returns.reduce((sum, r) => sum + r['3m'], 0) / returnCount,
        '6m': returns.reduce((sum, r) => sum + r['6m'], 0) / returnCount,
      };

      // Risk metrics
      const volatilities = validAnalyses.map(a => a.agent_scores.quality?.metrics?.volatility || 0);
      const avgVolatility = volatilities.length > 0
        ? volatilities.reduce((sum, v) => sum + v, 0) / volatilities.length
        : 0;

      setAnalytics({
        totalStocks: validAnalyses.length,
        avgScore,
        recommendations,
        sectors,
        returns,
        avgReturns,
        avgVolatility,
        stocks: validAnalyses,
      });
    } catch (error) {
      console.error('Failed to load portfolio analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (watchlist.length === 0) {
    return (
      <Card>
        <div className="p-12 text-center">
          <AlertTriangle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Watchlist Stocks
          </h3>
          <p className="text-gray-600">
            Add stocks to your watchlist to see portfolio analytics
          </p>
        </div>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <div className="p-12">
          <Loading size="lg" text="Analyzing portfolio..." />
        </div>
      </Card>
    );
  }

  if (!analytics) {
    return (
      <Card>
        <div className="p-6 text-center text-gray-600">
          Failed to load portfolio analytics
        </div>
      </Card>
    );
  }

  // Prepare data for charts
  const recommendationData = Object.entries(analytics.recommendations).map(([rec, count]) => ({
    recommendation: rec,
    count: count as number,
  }));

  const sectorData = Object.entries(analytics.sectors).map(([sector, count]) => ({
    sector,
    count: count as number,
  }));

  const returnsTimelineData = [
    { period: '1M', return: analytics.avgReturns['1m'] },
    { period: '3M', return: analytics.avgReturns['3m'] },
    { period: '6M', return: analytics.avgReturns['6m'] },
  ];

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Stocks</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.totalStocks}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-blue-500" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Score</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.avgScore.toFixed(1)}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg 3M Return</p>
                <p className={cn(
                  'text-3xl font-bold mt-1',
                  analytics.avgReturns['3m'] >= 0 ? 'text-green-600' : 'text-red-600'
                )}>
                  {analytics.avgReturns['3m'] > 0 ? '+' : ''}
                  {analytics.avgReturns['3m'].toFixed(1)}%
                </p>
              </div>
              {analytics.avgReturns['3m'] >= 0 ? (
                <TrendingUp className="h-8 w-8 text-green-500" />
              ) : (
                <TrendingDown className="h-8 w-8 text-red-500" />
              )}
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Volatility</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.avgVolatility.toFixed(1)}%
                </p>
              </div>
              <Percent className="h-8 w-8 text-yellow-500" />
            </div>
          </div>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recommendation Distribution */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Recommendation Distribution
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={recommendationData}
                  dataKey="count"
                  nameKey="recommendation"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(_entry) => `${_entry.recommendation}: ${_entry.count}`}
                >
                  {recommendationData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Sector Distribution */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Sector Distribution
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sectorData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="sector" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Returns Over Time */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Average Portfolio Returns
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={returnsTimelineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis />
                <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
                <Line
                  type="monotone"
                  dataKey="return"
                  stroke="#10B981"
                  strokeWidth={2}
                  dot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Individual Stock Returns */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              3M Returns by Stock
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.returns}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="symbol" />
                <YAxis />
                <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
                <Bar dataKey="3m" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Top Performers Table */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Top Performers (by 3M Return)
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">1M Return</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">3M Return</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">6M Return</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Recommendation</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {analytics.stocks
                  .sort((a: any, b: any) => {
                    const aRet = a.agent_scores.momentum?.metrics?.['3m_return'] || -Infinity;
                    const bRet = b.agent_scores.momentum?.metrics?.['3m_return'] || -Infinity;
                    return bRet - aRet;
                  })
                  .slice(0, 10)
                  .map((stock: any, idx: number) => {
                    const momentum = stock.agent_scores.momentum?.metrics;
                    return (
                      <tr key={stock.symbol} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-bold text-gray-900">#{idx + 1}</td>
                        <td className="px-4 py-3 text-sm font-bold text-blue-600">{stock.symbol}</td>
                        <td className="px-4 py-3 text-sm font-semibold text-gray-900">
                          {stock.composite_score.toFixed(1)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn(
                            'text-sm font-medium',
                            (momentum?.['1m_return'] || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                          )}>
                            {momentum?.['1m_return'] !== undefined
                              ? `${momentum['1m_return'] > 0 ? '+' : ''}${momentum['1m_return'].toFixed(1)}%`
                              : 'N/A'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn(
                            'text-sm font-medium',
                            (momentum?.['3m_return'] || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                          )}>
                            {momentum?.['3m_return'] !== undefined
                              ? `${momentum['3m_return'] > 0 ? '+' : ''}${momentum['3m_return'].toFixed(1)}%`
                              : 'N/A'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn(
                            'text-sm font-medium',
                            (momentum?.['6m_return'] || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                          )}>
                            {momentum?.['6m_return'] !== undefined
                              ? `${momentum['6m_return'] > 0 ? '+' : ''}${momentum['6m_return'].toFixed(1)}%`
                              : 'N/A'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn(
                            'px-2 py-1 rounded text-xs font-medium',
                            stock.recommendation === 'STRONG BUY' && 'bg-green-100 text-green-800',
                            stock.recommendation === 'BUY' && 'bg-blue-100 text-blue-800',
                            stock.recommendation === 'HOLD' && 'bg-gray-100 text-gray-800'
                          )}>
                            {stock.recommendation}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    </div>
  );
}
