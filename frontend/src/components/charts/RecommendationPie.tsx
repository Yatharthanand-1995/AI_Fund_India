/**
 * Recommendation Distribution Pie Chart
 *
 * Pie/donut chart showing distribution of recommendations:
 * - Strong Buy, Buy, Weak Buy, Hold, Weak Sell, Sell
 *
 * Features:
 * - Click to filter by recommendation
 * - Percentage labels
 * - Color-coded by recommendation type
 */

import React, { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Label
} from 'recharts';
import {
  CHART_COLORS,
  CHART_DEFAULTS,
  getRecommendationColor
} from '../../lib/chartUtils';

// ============================================================================
// Types
// ============================================================================

export interface RecommendationData {
  recommendation: string;
  count: number;
}

export interface RecommendationPieProps {
  data: RecommendationData[];
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
  onRecommendationClick?: (recommendation: string) => void;
  className?: string;
}

// ============================================================================
// Custom Label
// ============================================================================

const renderCustomLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent
}: any) => {
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  // Only show label if slice is large enough (>5%)
  if (percent < 0.05) return null;

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      className="text-xs font-semibold"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

// ============================================================================
// Custom Tooltip
// ============================================================================

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0];

  return (
    <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg border border-gray-700">
      <p className="text-sm font-semibold mb-1">{data.name}</p>
      <div className="flex items-center gap-2 text-sm">
        <div
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: data.payload.fill }}
        />
        <span className="text-gray-300">Count:</span>
        <span className="font-semibold">{data.value}</span>
      </div>
      <p className="text-xs text-gray-400 mt-1">
        {data.payload.percent.toFixed(1)}% of total
      </p>
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const RecommendationPie: React.FC<RecommendationPieProps> = ({
  data,
  height = 300,
  innerRadius = 60,
  outerRadius = 100,
  onRecommendationClick,
  className = ''
}) => {
  // Process and sort data
  const chartData = useMemo(() => {
    if (!data || !Array.isArray(data)) return [];

    // Define recommendation order (from best to worst)
    const order = ['STRONG BUY', 'BUY', 'WEAK BUY', 'HOLD', 'WEAK SELL', 'SELL'];

    const total = data.reduce((sum, item) => sum + item.count, 0);

    return data
      .filter(item => item.count > 0)
      .map(item => ({
        name: item.recommendation,
        value: item.count,
        percent: (item.count / total) * 100,
        color: getRecommendationColor(item.recommendation)
      }))
      .sort((a, b) => {
        const aIndex = order.indexOf(a.name);
        const bIndex = order.indexOf(b.name);
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
      });
  }, [data]);

  const totalStocks = useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.value, 0);
  }, [chartData]);

  if (!chartData.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No recommendation data available</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Recommendation Distribution
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Total: {totalStocks} stocks
        </p>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            dataKey="value"
            animationDuration={CHART_DEFAULTS.animationDuration}
            onClick={(data) => {
              if (onRecommendationClick) {
                onRecommendationClick(data.name);
              }
            }}
            style={{ cursor: onRecommendationClick ? 'pointer' : 'default' }}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
            <Label
              value={totalStocks.toString()}
              position="center"
              className="text-2xl font-bold"
              fill={CHART_COLORS.axis}
            />
          </Pie>

          <Tooltip content={<CustomTooltip />} />

          <Legend
            verticalAlign="bottom"
            height={36}
            wrapperStyle={{
              fontSize: CHART_DEFAULTS.fontSizeSmall,
              paddingTop: '10px'
            }}
            formatter={(value, entry: any) => (
              <span style={{ color: entry.color }}>
                {value} ({entry.payload.value})
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Breakdown Table */}
      <div className="mt-4 space-y-2">
        {chartData.map((item, index) => (
          <div
            key={index}
            className={`flex items-center justify-between p-2 rounded-lg border transition-colors ${
              onRecommendationClick ? 'cursor-pointer hover:bg-gray-50' : ''
            }`}
            style={{ borderColor: `${item.color}40` }}
            onClick={() => onRecommendationClick?.(item.name)}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: item.color }}
              />
              <span className="font-medium text-gray-900">{item.name}</span>
            </div>
            <div className="text-right">
              <span className="font-semibold text-gray-900">{item.value}</span>
              <span className="text-sm text-gray-500 ml-2">
                ({item.percent.toFixed(1)}%)
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RecommendationPie;
