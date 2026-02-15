/**
 * Stock Price Chart Component
 *
 * Dual-axis chart showing:
 * - Stock price (left axis)
 * - Composite score (right axis)
 *
 * Features:
 * - Time range selector
 * - Zoom capability
 * - Interactive tooltips
 * - Export to PNG
 */

import React, { useState, useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import {
  CHART_COLORS,
  CHART_DEFAULTS,
  formatXAxis,
  formatYAxis,
  formatTooltipValue,
  formatTooltipDate,
  TIME_RANGES,
  TimeRange,
  filterByTimeRange,
  transformHistoryData,
  sampleData
} from '../../lib/chartUtils';
import ChartErrorBoundary from './ChartErrorBoundary';

// ============================================================================
// Types
// ============================================================================

export interface HistoricalDataPoint {
  timestamp: string;
  composite_score: number;
  price?: number;
  recommendation?: string;
}

export interface StockPriceChartProps {
  symbol: string;
  data: HistoricalDataPoint[];
  height?: number;
  showPrice?: boolean;
  showScore?: boolean;
  defaultTimeRange?: TimeRange;
  className?: string;
}

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
        <div key={index} className="flex items-center gap-2 text-sm mt-1">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-300">{entry.name}:</span>
          <span className="font-semibold">
            {entry.dataKey === 'price'
              ? formatTooltipValue(entry.value, 'price')
              : formatTooltipValue(entry.value, 'score')}
          </span>
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const StockPriceChart: React.FC<StockPriceChartProps> = ({
  symbol,
  data,
  height = CHART_DEFAULTS.height,
  showPrice = true,
  showScore = true,
  defaultTimeRange = '6M',
  className = ''
}) => {
  const [timeRange, setTimeRange] = useState<TimeRange>(defaultTimeRange);

  // Transform and filter data
  const chartData = useMemo(() => {
    const transformed = transformHistoryData(data);
    const filtered = filterByTimeRange(transformed, timeRange);
    // Sample if too many points (performance optimization)
    return sampleData(filtered, 200);
  }, [data, timeRange]);

  // Calculate min/max for better axis scaling
  const { minPrice, maxPrice, minScore: _minScore, maxScore: _maxScore } = useMemo(() => {
    if (!chartData.length) {
      return { minPrice: 0, maxPrice: 1000, minScore: 0, maxScore: 100 };
    }

    const prices = chartData.filter(d => d.price).map(d => d.price!);
    const scores = chartData.map(d => d.score);

    return {
      minPrice: prices.length ? Math.min(...prices) * 0.95 : 0,
      maxPrice: prices.length ? Math.max(...prices) * 1.05 : 1000,
      minScore: Math.min(...scores) * 0.9,
      maxScore: Math.max(...scores) * 1.1
    };
  }, [chartData]);

  // Check if we have price data
  const hasPriceData = chartData.some(d => d.price !== null && d.price !== undefined);

  if (!chartData.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No historical data available</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Time Range Selector */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {symbol} - Price & Score History
        </h3>

        <div className="flex gap-1">
          {(Object.keys(TIME_RANGES) as TimeRange[]).map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={chartData}
          margin={CHART_DEFAULTS.marginWithLabels}
        >
          <defs>
            {/* Gradient for score area */}
            <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />

          {/* X Axis - Time */}
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) => formatXAxis(value, 'short')}
            stroke={CHART_COLORS.axis}
            style={{ fontSize: CHART_DEFAULTS.fontSizeSmall }}
          />

          {/* Left Y Axis - Price */}
          {showPrice && hasPriceData && (
            <YAxis
              yAxisId="price"
              orientation="left"
              domain={[minPrice, maxPrice]}
              tickFormatter={(value) => formatYAxis(value, 'price')}
              stroke={CHART_COLORS.axis}
              style={{ fontSize: CHART_DEFAULTS.fontSizeSmall }}
              label={{
                value: 'Price (₹)',
                angle: -90,
                position: 'insideLeft',
                style: { fontSize: CHART_DEFAULTS.fontSize }
              }}
            />
          )}

          {/* Right Y Axis - Score */}
          {showScore && (
            <YAxis
              yAxisId="score"
              orientation="right"
              domain={[0, 100]}
              tickFormatter={(value) => formatYAxis(value, 'score')}
              stroke={CHART_COLORS.axis}
              style={{ fontSize: CHART_DEFAULTS.fontSizeSmall }}
              label={{
                value: 'Composite Score',
                angle: 90,
                position: 'insideRight',
                style: { fontSize: CHART_DEFAULTS.fontSize }
              }}
            />
          )}

          <Tooltip content={<CustomTooltip />} />

          <Legend
            wrapperStyle={{ fontSize: CHART_DEFAULTS.fontSize }}
            iconType="line"
          />

          {/* Price Line */}
          {showPrice && hasPriceData && (
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="price"
              stroke={CHART_COLORS.success}
              strokeWidth={CHART_DEFAULTS.strokeWidth}
              dot={false}
              name="Price"
              animationDuration={CHART_DEFAULTS.animationDuration}
            />
          )}

          {/* Score Area */}
          {showScore && (
            <Area
              yAxisId="score"
              type="monotone"
              dataKey="score"
              stroke={CHART_COLORS.primary}
              strokeWidth={CHART_DEFAULTS.strokeWidth}
              fill="url(#scoreGradient)"
              name="Composite Score"
              animationDuration={CHART_DEFAULTS.animationDuration}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Chart Statistics */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        {hasPriceData && (
          <>
            <div>
              <p className="text-gray-500">Current Price</p>
              <p className="font-semibold text-gray-900">
                {chartData[chartData.length - 1]?.price
                  ? formatTooltipValue(chartData[chartData.length - 1].price!, 'price')
                  : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Price Change</p>
              <p className="font-semibold text-gray-900">
                {chartData.length >= 2 && chartData[0]?.price && chartData[chartData.length - 1]?.price
                  ? (() => {
                      const change = chartData[chartData.length - 1].price! - chartData[0].price!;
                      const changePercent = (change / chartData[0].price!) * 100;
                      return (
                        <span className={change >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {change >= 0 ? '+' : ''}
                          {formatTooltipValue(changePercent, 'percent')}
                        </span>
                      );
                    })()
                  : 'N/A'}
              </p>
            </div>
          </>
        )}
        <div>
          <p className="text-gray-500">Current Score</p>
          <p className="font-semibold text-gray-900">
            {chartData[chartData.length - 1]?.score
              ? formatTooltipValue(chartData[chartData.length - 1].score, 'score')
              : 'N/A'}
          </p>
        </div>
        <div>
          <p className="text-gray-500">Score Change</p>
          <p className="font-semibold text-gray-900">
            {chartData.length >= 2
              ? (() => {
                  const change = chartData[chartData.length - 1].score - chartData[0].score;
                  return (
                    <span className={change >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {change >= 0 ? '+' : ''}
                      {formatTooltipValue(change, 'score')}
                    </span>
                  );
                })()
              : 'N/A'}
          </p>
        </div>
      </div>
    </div>
  );
};

const _StockPriceChartWrapped = (props: StockPriceChartProps) => (
  <ChartErrorBoundary title="Stock Price Chart">
    <StockPriceChart {...props} />
  </ChartErrorBoundary>
);
export default _StockPriceChartWrapped;
