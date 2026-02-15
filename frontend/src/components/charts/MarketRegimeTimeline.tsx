/**
 * Market Regime Timeline Component
 *
 * Timeline showing regime changes over time with:
 * - Color-coded areas (green=BULL, red=BEAR, gray=SIDEWAYS)
 * - Volatility overlay
 * - Click to see weights for that period
 *
 * Features:
 * - Area chart with custom fill
 * - Interactive regime details
 * - Trend indicators
 */

import React, { useState, useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import {
  CHART_COLORS,
  CHART_DEFAULTS,
  formatXAxis,
  formatTooltipDate,
  getRegimeColor
} from '../../lib/chartUtils';
import ChartErrorBoundary from './ChartErrorBoundary';

// ============================================================================
// Types
// ============================================================================

export interface RegimeDataPoint {
  timestamp: string;
  regime: string;
  trend: string;
  volatility: string;
  weights?: Record<string, number>;
}

export interface MarketRegimeTimelineProps {
  data: RegimeDataPoint[];
  days?: number;
  height?: number;
  showWeights?: boolean;
  className?: string;
}

// ============================================================================
// Custom Tooltip
// ============================================================================

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg border border-gray-700 max-w-sm">
      <p className="text-sm font-medium mb-2">
        {formatTooltipDate(data.timestamp)}
      </p>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: getRegimeColor(data.regime) }}
          />
          <span className="text-gray-300">Regime:</span>
          <span className="font-semibold">{data.regime}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-300">Trend:</span>
          <span className="font-semibold">{data.trend}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-300">Volatility:</span>
          <span className="font-semibold">{data.volatility}</span>
        </div>
      </div>
      {data.weights && (
        <div className="mt-2 pt-2 border-t border-gray-700">
          <p className="text-xs text-gray-400 mb-1">Agent Weights:</p>
          <div className="grid grid-cols-2 gap-1 text-xs">
            {Object.entries(data.weights).map(([agent, weight]: [string, any]) => (
              <div key={agent} className="flex justify-between">
                <span className="text-gray-300">{agent}:</span>
                <span className="font-semibold">{(weight * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const MarketRegimeTimeline: React.FC<MarketRegimeTimelineProps> = ({
  data,
  days = 30,
  height = 250,
  showWeights = false,
  className = ''
}) => {
  const [selectedRegime, setSelectedRegime] = useState<RegimeDataPoint | null>(null);

  // Transform data for chart
  const chartData = useMemo(() => {
    if (!data || !Array.isArray(data)) return [];

    return data
      .map(item => ({
        ...item,
        // Map regime to numeric value for chart
        value: item.regime.includes('BULL') ? 1 : item.regime.includes('BEAR') ? -1 : 0,
        color: getRegimeColor(item.regime)
      }))
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [data]);

  if (!chartData.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No regime data available</p>
      </div>
    );
  }

  // Get current regime
  const currentRegime = chartData[chartData.length - 1];

  // Count regime occurrences
  const regimeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    chartData.forEach(item => {
      const regime = item.regime.split('_')[0]; // Get base regime (BULL, BEAR, SIDEWAYS)
      counts[regime] = (counts[regime] || 0) + 1;
    });
    return counts;
  }, [chartData]);

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Market Regime Timeline
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Last {days} days
          </p>
        </div>

        {/* Current Regime Badge */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Current:</span>
          <div
            className="px-3 py-1 rounded-full text-sm font-semibold text-white"
            style={{ backgroundColor: currentRegime.color }}
          >
            {currentRegime.regime}
          </div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={chartData}
          margin={CHART_DEFAULTS.margin}
          onClick={(e) => {
            if (e && e.activePayload && e.activePayload[0]) {
              setSelectedRegime(e.activePayload[0].payload);
            }
          }}
        >
          <defs>
            {/* Gradients for each regime */}
            <linearGradient id="bullGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.bull} stopOpacity={0.8} />
              <stop offset="95%" stopColor={CHART_COLORS.bull} stopOpacity={0.2} />
            </linearGradient>
            <linearGradient id="bearGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.bear} stopOpacity={0.2} />
              <stop offset="95%" stopColor={CHART_COLORS.bear} stopOpacity={0.8} />
            </linearGradient>
            <linearGradient id="sidewaysGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.sideways} stopOpacity={0.6} />
              <stop offset="95%" stopColor={CHART_COLORS.sideways} stopOpacity={0.3} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />

          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) => formatXAxis(value, 'short')}
            stroke={CHART_COLORS.axis}
            style={{ fontSize: CHART_DEFAULTS.fontSizeSmall }}
          />

          <YAxis
            domain={[-1, 1]}
            ticks={[-1, 0, 1]}
            tickFormatter={(value) => {
              if (value === 1) return 'BULL';
              if (value === -1) return 'BEAR';
              return 'SIDEWAYS';
            }}
            stroke={CHART_COLORS.axis}
            style={{ fontSize: CHART_DEFAULTS.fontSizeSmall }}
          />

          <Tooltip content={<CustomTooltip />} />

          <ReferenceLine y={0} stroke={CHART_COLORS.axis} strokeDasharray="3 3" />

          <Area
            type="stepAfter"
            dataKey="value"
            stroke={CHART_COLORS.axis}
            strokeWidth={2}
            fill="url(#bullGradient)"
            animationDuration={CHART_DEFAULTS.animationDuration}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Regime Statistics */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        {Object.entries(regimeCounts).map(([regime, count]) => {
          const percentage = ((count / chartData.length) * 100).toFixed(1);
          return (
            <div
              key={regime}
              className="p-3 rounded-lg border"
              style={{
                borderColor: getRegimeColor(regime),
                backgroundColor: `${getRegimeColor(regime)}10`
              }}
            >
              <p className="text-xs text-gray-600 mb-1">{regime}</p>
              <p className="text-lg font-bold" style={{ color: getRegimeColor(regime) }}>
                {percentage}%
              </p>
              <p className="text-xs text-gray-500">{count} periods</p>
            </div>
          );
        })}
      </div>

      {/* Selected Regime Details */}
      {selectedRegime && showWeights && selectedRegime.weights && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-sm font-semibold text-gray-900 mb-2">
            Selected Period: {formatTooltipDate(selectedRegime.timestamp)}
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {Object.entries(selectedRegime.weights).map(([agent, weight]: [string, any]) => (
              <div key={agent} className="text-sm">
                <p className="text-gray-600 capitalize">{agent}:</p>
                <p className="font-semibold">{(weight * 100).toFixed(1)}%</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const _MarketRegimeTimelineWrapped = (props: MarketRegimeTimelineProps) => (
  <ChartErrorBoundary title="Market Regime Timeline">
    <MarketRegimeTimeline {...props} />
  </ChartErrorBoundary>
);
export default _MarketRegimeTimelineWrapped;
