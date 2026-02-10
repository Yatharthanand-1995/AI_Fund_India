/**
 * Sector Performance Analytics Component
 *
 * Analyzes sector performance, rotation, and trends
 */

import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';
import Card from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

export default function SectorPerformanceAnalytics() {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    loadSectorAnalytics();
  }, []);

  const loadSectorAnalytics = async () => {
    setLoading(true);
    try {
      // Get sector analysis from API
      await api.getSectorAnalysis(7);

      // Get top picks to analyze by sector
      const response = await api.getTopPicks(50, false);
      const stocks = response.top_picks || [];

      // Group stocks by sector
      const sectorGroups: Record<string, any[]> = {};
      stocks.forEach((stock: any) => {
        const sector = stock.agent_scores.quality?.metrics?.sector || 'Unknown';
        if (!sectorGroups[sector]) {
          sectorGroups[sector] = [];
        }
        sectorGroups[sector].push(stock);
      });

      // Calculate sector metrics
      const sectorMetrics = Object.entries(sectorGroups).map(([sector, stockList]) => {
        const avgScore = stockList.reduce((sum, s) => sum + s.composite_score, 0) / stockList.length;
        const avgReturn3m = stockList.reduce((sum, s) =>
          sum + (s.agent_scores.momentum?.metrics?.['3m_return'] || 0), 0) / stockList.length;
        const avgReturn6m = stockList.reduce((sum, s) =>
          sum + (s.agent_scores.momentum?.metrics?.['6m_return'] || 0), 0) / stockList.length;
        const avgVolatility = stockList.reduce((sum, s) =>
          sum + (s.agent_scores.quality?.metrics?.volatility || 0), 0) / stockList.length;

        const strongBuyCount = stockList.filter(s => s.recommendation === 'STRONG BUY').length;

        return {
          sector,
          count: stockList.length,
          avgScore,
          avgReturn3m,
          avgReturn6m,
          avgVolatility,
          strongBuyCount,
          stocks: stockList,
        };
      });

      // Sort by average score
      sectorMetrics.sort((a, b) => b.avgScore - a.avgScore);

      // Best and worst sectors
      const bestSector = sectorMetrics[0];
      const worstSector = sectorMetrics[sectorMetrics.length - 1];

      // Prepare chart data
      const sectorScoreData = sectorMetrics.map(s => ({
        sector: s.sector.length > 15 ? s.sector.substring(0, 15) + '...' : s.sector,
        'Avg Score': parseFloat(s.avgScore.toFixed(1)),
        'Stock Count': s.count,
      }));

      const sectorReturnData = sectorMetrics.map(s => ({
        sector: s.sector.length > 15 ? s.sector.substring(0, 15) + '...' : s.sector,
        '3M Return': parseFloat(s.avgReturn3m.toFixed(1)),
        '6M Return': parseFloat(s.avgReturn6m.toFixed(1)),
      }));

      setAnalytics({
        sectorMetrics,
        bestSector,
        worstSector,
        sectorScoreData,
        sectorReturnData,
        totalSectors: sectorMetrics.length,
      });
    } catch (error) {
      console.error('Failed to load sector analytics:', error);
      setAnalytics({ error: 'Failed to load analytics' });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <div className="p-12">
          <Loading size="lg" text="Analyzing sector performance..." />
        </div>
      </Card>
    );
  }

  if (!analytics || analytics.error) {
    return (
      <Card>
        <div className="p-6 text-center text-gray-600">
          {analytics?.error || 'Failed to load sector analytics'}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Best & Worst Sectors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <div className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <TrendingUp className="h-6 w-6 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Best Performing Sector</h3>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-2xl font-bold text-gray-900">{analytics.bestSector.sector}</p>
                <p className="text-sm text-gray-600">{analytics.bestSector.count} stocks analyzed</p>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-green-200">
                <div>
                  <p className="text-xs text-gray-600">Avg Score</p>
                  <p className="text-xl font-bold text-green-600">
                    {analytics.bestSector.avgScore.toFixed(1)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">3M Return</p>
                  <p className="text-xl font-bold text-green-600">
                    {analytics.bestSector.avgReturn3m > 0 ? '+' : ''}
                    {analytics.bestSector.avgReturn3m.toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card className="bg-gradient-to-br from-red-50 to-red-100 border-red-200">
          <div className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <TrendingDown className="h-6 w-6 text-red-600" />
              <h3 className="text-lg font-semibold text-gray-900">Lowest Performing Sector</h3>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-2xl font-bold text-gray-900">{analytics.worstSector.sector}</p>
                <p className="text-sm text-gray-600">{analytics.worstSector.count} stocks analyzed</p>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-red-200">
                <div>
                  <p className="text-xs text-gray-600">Avg Score</p>
                  <p className="text-xl font-bold text-red-600">
                    {analytics.worstSector.avgScore.toFixed(1)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">3M Return</p>
                  <p className="text-xl font-bold text-red-600">
                    {analytics.worstSector.avgReturn3m > 0 ? '+' : ''}
                    {analytics.worstSector.avgReturn3m.toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector Average Scores */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Sector Average Scores
            </h3>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={analytics.sectorScoreData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis type="category" dataKey="sector" width={120} />
                <Tooltip />
                <Bar dataKey="Avg Score" fill="#3B82F6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Sector Returns */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Sector Returns Comparison
            </h3>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={analytics.sectorReturnData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="sector" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                <Legend />
                <Bar dataKey="3M Return" fill="#10B981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="6M Return" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Detailed Sector Table */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Sector Performance Breakdown
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sector</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stocks</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">3M Return</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">6M Return</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Volatility</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Strong Buys</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {analytics.sectorMetrics.map((sector: any, idx: number) => (
                  <tr key={sector.sector} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-bold text-gray-900">#{idx + 1}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{sector.sector}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{sector.count}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'text-sm font-semibold',
                        sector.avgScore >= 70 ? 'text-green-600' :
                        sector.avgScore >= 50 ? 'text-yellow-600' : 'text-red-600'
                      )}>
                        {sector.avgScore.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'text-sm font-medium',
                        sector.avgReturn3m >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        {sector.avgReturn3m > 0 ? '+' : ''}{sector.avgReturn3m.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'text-sm font-medium',
                        sector.avgReturn6m >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        {sector.avgReturn6m > 0 ? '+' : ''}{sector.avgReturn6m.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {sector.avgVolatility.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-semibold text-green-600">
                        {sector.strongBuyCount}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    </div>
  );
}
