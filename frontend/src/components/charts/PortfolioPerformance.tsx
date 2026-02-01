/**
 * Portfolio Performance Chart
 *
 * Multi-line chart showing watchlist performance over time:
 * - One line per stock
 * - Portfolio average line
 *
 * Features:
 * - Toggle individual stocks
 * - Highlight best/worst performers
 * - Color-coded lines
 */

import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
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
  formatTooltipDate
} from '../../lib/chartUtils';

// ============================================================================
// Types
// ============================================================================

export interface StockHistory {
  symbol: string;
  history: Array<{
    timestamp: string;
    composite_score: number;
  }>;
}

export interface PortfolioPerformanceProps {
  watchlistHistory: StockHistory[];
  height?: number;
  showAverage?: boolean;
  className?: string;
}

// ============================================================================
// Color Generation
// ============================================================================

const STOCK_COLORS = [
  CHART_COLORS.primary,
  CHART_COLORS.success,
  CHART_COLORS.warning,
  CHART_COLORS.danger,
  CHART_COLORS.info,
  CHART_COLORS.secondary,
  CHART_COLORS.fundamentals,
  CHART_COLORS.momentum,
  CHART_COLORS.quality,
  CHART_COLORS.institutional
];

// ============================================================================
// Custom Tooltip
// ============================================================================

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg border border-gray-700 max-w-sm">
      <p className="text-sm font-medium mb-2">
        {formatTooltipDate(label)}
      </p>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {payload
          .sort((a: any, b: any) => b.value - a.value)
          .map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-gray-300">{entry.name}:</span>
              </div>
              <span className="font-semibold">
                {formatTooltipValue(entry.value, 'score')}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const PortfolioPerformance: React.FC<PortfolioPerformanceProps> = ({
  watchlistHistory,
  height = 400,
  showAverage = true,
  className = ''
}) => {
  const [hiddenStocks, setHiddenStocks] = useState<Set<string>>(new Set());

  // Prepare chart data
  const { chartData, stockStats } = useMemo(() => {
    if (!watchlistHistory || !Array.isArray(watchlistHistory) || watchlistHistory.length === 0) {
      return { chartData: [], stockStats: [] };
    }

    // Get all unique timestamps
    const timestampSet = new Set<string>();
    watchlistHistory.forEach(stock => {
      stock.history.forEach(point => {
        timestampSet.add(point.timestamp);
      });
    });

    const timestamps = Array.from(timestampSet).sort();

    // Build chart data with all stocks
    const data = timestamps.map(timestamp => {
      const point: any = { timestamp };

      watchlistHistory.forEach(stock => {
        const dataPoint = stock.history.find(h => h.timestamp === timestamp);
        point[stock.symbol] = dataPoint?.composite_score || null;
      });

      // Calculate average (excluding nulls)
      if (showAverage) {
        const scores = watchlistHistory
          .map(stock => point[stock.symbol])
          .filter(score => score !== null);

        point.average = scores.length > 0
          ? scores.reduce((sum, score) => sum + score, 0) / scores.length
          : null;
      }

      return point;
    });

    // Calculate statistics for each stock
    const stats = watchlistHistory.map((stock, index) => {
      const scores = stock.history.map(h => h.composite_score);
      const current = scores[scores.length - 1] || 0;
      const previous = scores[0] || 0;
      const change = current - previous;

      return {
        symbol: stock.symbol,
        color: STOCK_COLORS[index % STOCK_COLORS.length],
        current,
        change,
        changePercent: previous !== 0 ? (change / previous) * 100 : 0,
        avg: scores.reduce((a, b) => a + b, 0) / scores.length
      };
    });

    return { chartData: data, stockStats: stats };
  }, [watchlistHistory, showAverage]);

  if (!chartData.length || !stockStats.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No portfolio data available</p>
      </div>
    );
  }

  const toggleStock = (symbol: string) => {
    const newHidden = new Set(hiddenStocks);
    if (newHidden.has(symbol)) {
      newHidden.delete(symbol);
    } else {
      newHidden.add(symbol);
    }
    setHiddenStocks(newHidden);
  };

  // Sort stats by performance
  const sortedStats = [...stockStats].sort((a, b) => b.change - a.change);
  const bestPerformer = sortedStats[0];
  const worstPerformer = sortedStats[sortedStats.length - 1];

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Portfolio Performance
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {stockStats.length} stocks • {chartData.length} data points
        </p>
      </div>

      {/* Performance Summary */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-xs text-green-600 mb-1">Best Performer</p>
          <p className="font-semibold text-green-900">{bestPerformer.symbol}</p>
          <p className="text-sm text-green-700">
            {bestPerformer.change >= 0 ? '+' : ''}
            {formatTooltipValue(bestPerformer.change, 'score')}
          </p>
        </div>

        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-xs text-red-600 mb-1">Worst Performer</p>
          <p className="font-semibold text-red-900">{worstPerformer.symbol}</p>
          <p className="text-sm text-red-700">
            {worstPerformer.change >= 0 ? '+' : ''}
            {formatTooltipValue(worstPerformer.change, 'score')}
          </p>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={CHART_DEFAULTS.margin}>
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

          <Legend
            onClick={(e) => toggleStock(e.value)}
            wrapperStyle={{
              fontSize: CHART_DEFAULTS.fontSizeSmall,
              cursor: 'pointer'
            }}
          />

          {/* Portfolio Average Line (if enabled) */}
          {showAverage && (
            <Line
              type="monotone"
              dataKey="average"
              stroke={CHART_COLORS.axis}
              strokeWidth={CHART_DEFAULTS.strokeWidthBold}
              strokeDasharray="5 5"
              dot={false}
              name="Portfolio Avg"
              animationDuration={CHART_DEFAULTS.animationDuration}
            />
          )}

          {/* Individual Stock Lines */}
          {stockStats.map((stock, index) => (
            <Line
              key={stock.symbol}
              type="monotone"
              dataKey={stock.symbol}
              stroke={stock.color}
              strokeWidth={CHART_DEFAULTS.strokeWidth}
              dot={false}
              name={stock.symbol}
              hide={hiddenStocks.has(stock.symbol)}
              animationDuration={CHART_DEFAULTS.animationDuration}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Stock List with Stats */}
      <div className="mt-4 space-y-2">
        {sortedStats.map((stock) => (
          <div
            key={stock.symbol}
            className={`flex items-center justify-between p-2 rounded-lg border transition-all cursor-pointer ${
              hiddenStocks.has(stock.symbol)
                ? 'opacity-40 border-gray-200'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onClick={() => toggleStock(stock.symbol)}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: stock.color }}
              />
              <span className="font-medium text-gray-900">{stock.symbol}</span>
            </div>

            <div className="flex items-center gap-6 text-sm">
              <div>
                <span className="text-gray-500">Current: </span>
                <span className="font-semibold">{formatTooltipValue(stock.current, 'score')}</span>
              </div>
              <div>
                <span className="text-gray-500">Change: </span>
                <span
                  className={`font-semibold ${
                    stock.change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {stock.change >= 0 ? '+' : ''}
                  {formatTooltipValue(stock.change, 'score')}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Avg: </span>
                <span className="font-semibold">{formatTooltipValue(stock.avg, 'score')}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-4 text-xs text-gray-500 text-center">
        Click on stocks in the legend or list to toggle visibility
      </p>
    </div>
  );
};

export default PortfolioPerformance;
