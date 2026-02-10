/**
 * Sector Analysis Page
 *
 * Displays sector-wise performance analysis and rankings
 */

import React, { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useSectorAnalysis } from '../hooks/useSectorAnalysis';
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react';
import { SectorHeatmap } from '../components/charts/SectorHeatmap';
import { ChartSkeleton, SkeletonLoader } from '../components/ui/SkeletonLoader';

/**
 * Virtual scrolling container for sector table
 */
function VirtualSectorTable({ sectors, getTrendIcon }: { sectors: any[]; getTrendIcon: (trend: string) => JSX.Element }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: sectors.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64, // Estimated row height
    overscan: 5,
  });

  return (
    <div className="overflow-x-auto">
      {/* Table header */}
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50 sticky top-0 z-10">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
              Rank
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sector
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
              Stocks
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">
              Avg Score
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Top Pick
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
              Trend
            </th>
          </tr>
        </thead>
      </table>

      {/* Virtual scrolling container */}
      <div
        ref={parentRef}
        className="bg-white divide-y divide-gray-200"
        style={{
          height: '600px',
          overflow: 'auto',
        }}
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const sector = sectors[virtualRow.index];
            return (
              <div
                key={virtualRow.key}
                data-index={virtualRow.index}
                ref={virtualizer.measureElement}
                className="hover:bg-gray-50 border-b border-gray-200"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {/* Grid layout matching table columns */}
                <div className="px-6 py-4 whitespace-nowrap w-20 flex-shrink-0">
                  <span className="text-sm font-semibold text-gray-900">
                    #{virtualRow.index + 1}
                  </span>
                </div>
                <div className="px-6 py-4 whitespace-nowrap flex-1">
                  <span className="text-sm font-medium text-gray-900">
                    {sector.sector}
                  </span>
                </div>
                <div className="px-6 py-4 whitespace-nowrap w-24 flex-shrink-0">
                  <span className="text-sm text-gray-600">
                    {sector.stock_count ?? 0}
                  </span>
                </div>
                <div className="px-6 py-4 whitespace-nowrap w-28 flex-shrink-0">
                  <span className="text-sm font-semibold text-gray-900">
                    {sector.avg_score != null ? sector.avg_score.toFixed(1) : 'N/A'}
                  </span>
                </div>
                <div className="px-6 py-4 whitespace-nowrap flex-1">
                  <span className="text-sm font-medium text-blue-600">
                    {sector.top_pick ?? 'N/A'}
                  </span>
                </div>
                <div className="px-6 py-4 whitespace-nowrap w-32 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    {getTrendIcon(sector.trend ?? 'NEUTRAL')}
                    <span className="text-sm text-gray-600">
                      {sector.trend ?? 'NEUTRAL'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const SectorAnalysis: React.FC = () => {
  const { sectors, loading, error, refetch, totalSectors, lastUpdated } = useSectorAnalysis({
    days: 7,
    autoRefresh: false
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
        <div className="space-y-4">
          <SkeletonLoader type="table" />
        </div>
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

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'UP':
        return <TrendingUp className="w-5 h-5 text-green-600" />;
      case 'DOWN':
        return <TrendingDown className="w-5 h-5 text-red-600" />;
      default:
        return <Minus className="w-5 h-5 text-gray-600" />;
    }
  };

  // Transform sectors for heatmap (with null checks and type safety)
  const heatmapData = sectors.map(sector => {
    const avgScore = typeof sector.avg_score === 'number' && !isNaN(sector.avg_score)
      ? sector.avg_score
      : (sector.avg_score ? parseFloat(String(sector.avg_score)) : 0);

    return {
      sector: sector.sector ?? 'Unknown',
      stockCount: sector.stock_count ?? 0,
      avgScore: !isNaN(avgScore) ? avgScore : 0,
      topPick: sector.top_pick ?? 'N/A'
    };
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Sector Analysis</h1>
          <p className="text-gray-600 mt-1">
            Performance analysis across {totalSectors} sectors
          </p>
        </div>
        {lastUpdated && (
          <p className="text-sm text-gray-500">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* Sector Heatmap */}
      {sectors.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <SectorHeatmap
            data={heatmapData}
            height={400}
            onSectorClick={(_sector) => {
              // Sector clicked - could navigate or show details
            }}
          />
        </div>
      )}

      {/* Sector Rankings Table */}
      {sectors.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Sector Rankings
            </h2>
          </div>
          <VirtualSectorTable sectors={sectors} getTrendIcon={getTrendIcon} />
        </div>
      )}

      {/* Empty State */}
      {sectors.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">No sector data available</p>
          <p className="text-sm text-gray-500 mt-2">
            Wait for the data collector to gather sector information
          </p>
        </div>
      )}
    </div>
  );
};

export default SectorAnalysis;
