import React from 'react';
import { useSectorAnalysis } from '../hooks/useSectorAnalysis';
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react';
import { SectorHeatmap } from '../components/charts/SectorHeatmap';
import { ChartSkeleton, SkeletonLoader } from '../components/ui/SkeletonLoader';

function getTrendIcon(trend: string): React.ReactElement {
  switch (trend) {
    case 'UP':   return <TrendingUp className="w-4 h-4 text-green-600" />;
    case 'DOWN': return <TrendingDown className="w-4 h-4 text-red-600" />;
    default:     return <Minus className="w-4 h-4 text-gray-400" />;
  }
}

const SectorAnalysis: React.FC = () => {
  const { sectors, loading, error, refetch, totalSectors, lastUpdated } = useSectorAnalysis({
    days: 7,
    autoRefresh: false,
  });

  if (loading && sectors.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <SkeletonLoader type="text" count={2} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
        <SkeletonLoader type="table" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-600">Failed to load sector analysis</p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!loading && sectors.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-blue-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-800 mb-2">No Sector Data Yet</h3>
          <p className="text-gray-500 mb-4">
            Sector analysis is built from historical stock analyses. Run your first stock analysis on the Dashboard to start populating this view.
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  const heatmapData = sectors.map(sector => {
    const raw = sector.avg_score;
    const avgScore = typeof raw === 'number' && !isNaN(raw) ? raw : (raw ? parseFloat(String(raw)) : 0);
    return {
      sector: sector.sector ?? 'Unknown',
      stockCount: sector.stock_count ?? 0,
      avgScore: isNaN(avgScore) ? 0 : avgScore,
      topPick: sector.top_pick ?? 'N/A',
    };
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Sector Analysis</h1>
          <p className="text-gray-600 mt-1">Performance analysis across {totalSectors} sectors</p>
        </div>
        {lastUpdated && (
          <p className="text-sm text-gray-500">Last updated: {lastUpdated.toLocaleTimeString()}</p>
        )}
      </div>

      {sectors.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <SectorHeatmap
            data={heatmapData}
            height={400}
            onSectorClick={(_sector) => {}}
          />
        </div>
      )}

      {sectors.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Sector Rankings</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">Rank</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sector</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">Stocks</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">Avg Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Top Pick</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">Trend</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sectors.map((sector, idx) => (
                  <tr key={sector.sector} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-500">#{idx + 1}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{sector.sector}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{sector.stock_count ?? 0}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                      {sector.avg_score != null ? Number(sector.avg_score).toFixed(1) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">{sector.top_pick ?? '—'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getTrendIcon(sector.trend ?? 'NEUTRAL')}
                        <span className="text-sm text-gray-600">{sector.trend ?? 'NEUTRAL'}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default SectorAnalysis;
