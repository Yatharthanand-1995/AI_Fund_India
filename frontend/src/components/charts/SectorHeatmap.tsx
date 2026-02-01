/**
 * Sector Heatmap Component
 *
 * Treemap visualization of sector performance:
 * - Size = number of stocks in sector
 * - Color = average composite score
 *
 * Features:
 * - Click to filter stocks by sector
 * - Drill-down capability
 * - Color scale from red (poor) to green (excellent)
 */

import React, { useMemo } from 'react';
import {
  Treemap,
  ResponsiveContainer,
  Tooltip
} from 'recharts';
import {
  CHART_COLORS,
  getScoreColor,
  formatTooltipValue
} from '../../lib/chartUtils';

// ============================================================================
// Types
// ============================================================================

export interface SectorData {
  sector: string;
  stockCount: number;
  avgScore: number;
  topPick?: string;
}

export interface SectorHeatmapProps {
  data: SectorData[];
  height?: number;
  onSectorClick?: (sector: string) => void;
  className?: string;
}

// ============================================================================
// Custom Content Renderer
// ============================================================================

const CustomContent = (props: any) => {
  const { x, y, width, height, name, value, avgScore } = props;

  // Don't render if too small
  if (width < 40 || height < 30) return null;

  const color = getScoreColor(avgScore);

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: color,
          stroke: '#fff',
          strokeWidth: 2,
          opacity: 0.9
        }}
      />
      {width > 60 && height > 40 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 10}
            textAnchor="middle"
            fill="#fff"
            fontSize={14}
            fontWeight="bold"
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 8}
            textAnchor="middle"
            fill="#fff"
            fontSize={12}
          >
            Score: {avgScore.toFixed(1)}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 24}
            textAnchor="middle"
            fill="#fff"
            fontSize={10}
            opacity={0.9}
          >
            {value} stock{value !== 1 ? 's' : ''}
          </text>
        </>
      )}
    </g>
  );
};

// ============================================================================
// Custom Tooltip
// ============================================================================

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg border border-gray-700">
      <p className="text-sm font-semibold mb-2">{data.name}</p>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-4 text-sm">
          <span className="text-gray-300">Avg Score:</span>
          <span className="font-semibold">
            {formatTooltipValue(data.avgScore, 'score')}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4 text-sm">
          <span className="text-gray-300">Stocks:</span>
          <span className="font-semibold">{data.value}</span>
        </div>
        {data.topPick && (
          <div className="flex items-center justify-between gap-4 text-sm">
            <span className="text-gray-300">Top Pick:</span>
            <span className="font-semibold">{data.topPick}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const SectorHeatmap: React.FC<SectorHeatmapProps> = ({
  data,
  height = 400,
  onSectorClick,
  className = ''
}) => {
  // Transform data for treemap
  const treemapData = useMemo(() => {
    if (!data || !Array.isArray(data)) return [];

    return data
      .filter(sector => sector.stockCount > 0)
      .map(sector => ({
        name: sector.sector,
        value: sector.stockCount,
        avgScore: sector.avgScore,
        topPick: sector.topPick,
        color: getScoreColor(sector.avgScore)
      }))
      .sort((a, b) => b.avgScore - a.avgScore);
  }, [data]);

  if (!treemapData.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No sector data available</p>
      </div>
    );
  }

  const totalStocks = treemapData.reduce((sum, sector) => sum + sector.value, 0);

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Sector Performance Heatmap
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {treemapData.length} sectors • {totalStocks} stocks
        </p>
      </div>

      {/* Heatmap */}
      <ResponsiveContainer width="100%" height={height}>
        <Treemap
          data={treemapData}
          dataKey="value"
          aspectRatio={4 / 3}
          stroke="#fff"
          fill="#8884d8"
          content={<CustomContent />}
          onClick={(data) => {
            if (onSectorClick && data) {
              onSectorClick(data.name);
            }
          }}
          style={{ cursor: onSectorClick ? 'pointer' : 'default' }}
        >
          <Tooltip content={<CustomTooltip />} />
        </Treemap>
      </ResponsiveContainer>

      {/* Color Scale Legend */}
      <div className="mt-4">
        <p className="text-xs text-gray-600 mb-2">Performance Scale:</p>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Poor</span>
          <div className="flex-1 h-6 rounded-lg overflow-hidden flex">
            <div className="flex-1" style={{ backgroundColor: CHART_COLORS.sell }} />
            <div className="flex-1" style={{ backgroundColor: CHART_COLORS.weakSell }} />
            <div className="flex-1" style={{ backgroundColor: CHART_COLORS.hold }} />
            <div className="flex-1" style={{ backgroundColor: CHART_COLORS.weakBuy }} />
            <div className="flex-1" style={{ backgroundColor: CHART_COLORS.buy }} />
            <div className="flex-1" style={{ backgroundColor: CHART_COLORS.strongBuy }} />
          </div>
          <span className="text-xs text-gray-500">Excellent</span>
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>&lt;40</span>
          <span>40-50</span>
          <span>50-60</span>
          <span>60-70</span>
          <span>70-80</span>
          <span>80+</span>
        </div>
      </div>

      {/* Sector Rankings */}
      <div className="mt-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Sector Rankings</h4>
        <div className="space-y-2">
          {treemapData.map((sector, index) => (
            <div
              key={sector.name}
              className={`flex items-center justify-between p-2 rounded-lg border transition-colors ${
                onSectorClick ? 'cursor-pointer hover:bg-gray-50' : ''
              }`}
              style={{ borderColor: `${sector.color}40` }}
              onClick={() => onSectorClick?.(sector.name)}
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-gray-500 w-6">
                  #{index + 1}
                </span>
                <div
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: sector.color }}
                />
                <span className="font-medium text-gray-900">{sector.name}</span>
              </div>

              <div className="flex items-center gap-6 text-sm">
                <div>
                  <span className="text-gray-500">Score: </span>
                  <span className="font-semibold">
                    {formatTooltipValue(sector.avgScore, 'score')}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Stocks: </span>
                  <span className="font-semibold">{sector.value}</span>
                </div>
                {sector.topPick && (
                  <div>
                    <span className="text-gray-500">Top: </span>
                    <span className="font-semibold">{sector.topPick}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {onSectorClick && (
        <p className="mt-4 text-xs text-gray-500 text-center">
          Click on a sector to filter stocks
        </p>
      )}
    </div>
  );
};

export default SectorHeatmap;
