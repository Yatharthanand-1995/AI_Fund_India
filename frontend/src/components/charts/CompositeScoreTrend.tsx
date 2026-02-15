/**
 * Composite Score Trend Chart
 *
 * Simple line chart showing score trend over time with:
 * - Trend line (linear regression)
 * - Trend indicator (improving/declining/stable)
 *
 * Features:
 * - Clean visualization
 * - Mathematical trend calculation
 * - Visual trend indicators
 */

import React, { useMemo } from 'react';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart
} from 'recharts';
import {
  CHART_COLORS,
  CHART_DEFAULTS,
  formatXAxis,
  formatYAxis,
  formatTooltipValue,
  formatTooltipDate,
  transformHistoryData
} from '../../lib/chartUtils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import ChartErrorBoundary from './ChartErrorBoundary';

// ============================================================================
// Types
// ============================================================================

export interface ScoreDataPoint {
  timestamp: string;
  composite_score: number;
}

export interface CompositeScoreTrendProps {
  symbol: string;
  data: ScoreDataPoint[];
  height?: number;
  showTrendLine?: boolean;
  className?: string;
}

// ============================================================================
// Trend Calculation
// ============================================================================

const calculateLinearRegression = (data: { x: number; y: number }[]) => {
  const n = data.length;
  if (n < 2) return { slope: 0, intercept: 0 };

  const sumX = data.reduce((sum, point) => sum + point.x, 0);
  const sumY = data.reduce((sum, point) => sum + point.y, 0);
  const sumXY = data.reduce((sum, point) => sum + point.x * point.y, 0);
  const sumXX = data.reduce((sum, point) => sum + point.x * point.x, 0);

  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  return { slope, intercept };
};

// ============================================================================
// Custom Tooltip
// ============================================================================

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg border border-gray-700">
      <p className="text-sm font-medium mb-2">
        {formatTooltipDate(label)}
      </p>
      {payload.map((entry: any, index: number) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-300">{entry.name}:</span>
          <span className="font-semibold">
            {formatTooltipValue(entry.value, 'score')}
          </span>
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const CompositeScoreTrend: React.FC<CompositeScoreTrendProps> = ({
  symbol,
  data,
  height = 250,
  showTrendLine = true,
  className = ''
}) => {
  // Transform and prepare data
  const { chartData, trendData: _trendData, trendInfo } = useMemo(() => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      return { chartData: [], trendData: [], trendInfo: { direction: 'stable', slope: 0 } };
    }

    const transformed = transformHistoryData(data);

    // Calculate trend line
    const points = transformed.map((item, index) => ({
      x: index,
      y: item.score
    }));

    const { slope, intercept } = calculateLinearRegression(points);

    const trendLine = transformed.map((item, index) => ({
      ...item,
      trend: slope * index + intercept
    }));

    // Determine trend direction
    let direction: 'improving' | 'declining' | 'stable';
    const slopeThreshold = 0.5; // Points per day threshold

    if (slope > slopeThreshold) {
      direction = 'improving';
    } else if (slope < -slopeThreshold) {
      direction = 'declining';
    } else {
      direction = 'stable';
    }

    return {
      chartData: trendLine,
      trendData: trendLine,
      trendInfo: { direction, slope }
    };
  }, [data]);

  if (!chartData.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No score data available</p>
      </div>
    );
  }

  // Calculate statistics
  const stats = useMemo(() => {
    const scores = chartData.map(d => d.score);
    const current = scores[scores.length - 1];
    const previous = scores[0];
    const change = current - previous;
    const changePercent = (change / previous) * 100;

    return {
      current,
      previous,
      change,
      changePercent,
      min: Math.min(...scores),
      max: Math.max(...scores),
      avg: scores.reduce((a, b) => a + b, 0) / scores.length
    };
  }, [chartData]);

  // Get trend icon and color
  const getTrendDisplay = () => {
    switch (trendInfo.direction) {
      case 'improving':
        return {
          icon: <TrendingUp className="w-5 h-5" />,
          color: CHART_COLORS.success,
          text: 'Improving'
        };
      case 'declining':
        return {
          icon: <TrendingDown className="w-5 h-5" />,
          color: CHART_COLORS.danger,
          text: 'Declining'
        };
      default:
        return {
          icon: <Minus className="w-5 h-5" />,
          color: CHART_COLORS.hold,
          text: 'Stable'
        };
    }
  };

  const trendDisplay = getTrendDisplay();

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {symbol} - Score Trend
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {chartData.length} data points
          </p>
        </div>

        {/* Trend Indicator */}
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-lg"
          style={{ backgroundColor: `${trendDisplay.color}20`, color: trendDisplay.color }}
        >
          {trendDisplay.icon}
          <span className="font-semibold">{trendDisplay.text}</span>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={CHART_DEFAULTS.margin}>
          <defs>
            <linearGradient id="scoreTrendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
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
            domain={[0, 100]}
            tickFormatter={(value) => formatYAxis(value, 'score')}
            stroke={CHART_COLORS.axis}
            style={{ fontSize: CHART_DEFAULTS.fontSizeSmall }}
            label={{
              value: 'Composite Score',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: CHART_DEFAULTS.fontSize }
            }}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Reference lines for score ranges */}
          <ReferenceLine y={80} stroke={CHART_COLORS.success} strokeDasharray="3 3" opacity={0.5} />
          <ReferenceLine y={60} stroke={CHART_COLORS.hold} strokeDasharray="3 3" opacity={0.5} />
          <ReferenceLine y={40} stroke={CHART_COLORS.danger} strokeDasharray="3 3" opacity={0.5} />

          {/* Score Area */}
          <Area
            type="monotone"
            dataKey="score"
            stroke={CHART_COLORS.primary}
            strokeWidth={CHART_DEFAULTS.strokeWidthBold}
            fill="url(#scoreTrendGradient)"
            name="Score"
            animationDuration={CHART_DEFAULTS.animationDuration}
          />

          {/* Trend Line */}
          {showTrendLine && (
            <Line
              type="monotone"
              dataKey="trend"
              stroke={trendDisplay.color}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Trend"
              animationDuration={CHART_DEFAULTS.animationDuration}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Statistics */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Current</p>
          <p className="text-lg font-bold text-gray-900">
            {formatTooltipValue(stats.current, 'score')}
          </p>
        </div>

        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Change</p>
          <p
            className={`text-lg font-bold ${
              stats.change >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {stats.change >= 0 ? '+' : ''}
            {formatTooltipValue(stats.change, 'score')}
          </p>
        </div>

        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Average</p>
          <p className="text-lg font-bold text-gray-900">
            {formatTooltipValue(stats.avg, 'score')}
          </p>
        </div>

        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Range</p>
          <p className="text-lg font-bold text-gray-900">
            {formatTooltipValue(stats.min, 'score')} - {formatTooltipValue(stats.max, 'score')}
          </p>
        </div>
      </div>
    </div>
  );
};

const _CompositeScoreTrendWrapped = (props: CompositeScoreTrendProps) => (
  <ChartErrorBoundary title="Composite Score Trend">
    <CompositeScoreTrend {...props} />
  </ChartErrorBoundary>
);
export default _CompositeScoreTrendWrapped;
