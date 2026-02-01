/**
 * Agent Scores Bar Chart Component
 *
 * Horizontal bar chart showing agent scores with:
 * - Color coding by score range (green >70, yellow 50-70, red <50)
 * - Optional weight overlay
 * - Confidence indicators
 *
 * Features:
 * - Clear visual hierarchy
 * - Score and weight display
 * - Sortable by score or weight
 */

import React, { useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  LabelList
} from 'recharts';
import {
  CHART_COLORS,
  CHART_DEFAULTS,
  formatTooltipValue,
  getScoreColor,
  transformAgentScores
} from '../../lib/chartUtils';

// ============================================================================
// Types
// ============================================================================

export interface AgentScore {
  score: number;
  confidence?: number;
  reasoning?: string;
}

export interface AgentScoresBarProps {
  agentScores: Record<string, AgentScore>;
  weights?: Record<string, number>;
  height?: number;
  showWeights?: boolean;
  sortBy?: 'score' | 'weight' | 'name';
  className?: string;
}

// ============================================================================
// Custom Tooltip
// ============================================================================

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg border border-gray-700">
      <p className="text-sm font-semibold mb-2">{data.agent}</p>
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-sm">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: data.color }}
          />
          <span className="text-gray-300">Score:</span>
          <span className="font-semibold">
            {formatTooltipValue(data.score, 'score')}
          </span>
        </div>
        {data.weight !== undefined && (
          <div className="flex items-center gap-2 text-sm">
            <div className="w-3 h-3 rounded-full bg-gray-500" />
            <span className="text-gray-300">Weight:</span>
            <span className="font-semibold">
              {formatTooltipValue(data.weight * 100, 'percent')}
            </span>
          </div>
        )}
        {data.confidence !== undefined && (
          <div className="flex items-center gap-2 text-sm">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-gray-300">Confidence:</span>
            <span className="font-semibold">
              {formatTooltipValue(data.confidence * 100, 'percent')}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const AgentScoresBar: React.FC<AgentScoresBarProps> = ({
  agentScores,
  weights,
  height = 300,
  showWeights = true,
  sortBy = 'score',
  className = ''
}) => {
  const [sortOrder, setSortOrder] = useState<'score' | 'weight' | 'name'>(sortBy);

  // Prepare chart data
  const chartData = useMemo(() => {
    const agentNames: Record<string, string> = {
      fundamentals: 'Fundamentals',
      momentum: 'Momentum',
      quality: 'Quality',
      sentiment: 'Sentiment',
      institutional_flow: 'Institutional'
    };

    let data = Object.entries(agentScores).map(([key, scoreData]) => ({
      agent: agentNames[key] || key,
      agentKey: key,
      score: scoreData.score,
      confidence: scoreData.confidence,
      weight: weights?.[key] || 0,
      color: getScoreColor(scoreData.score),
      reasoning: scoreData.reasoning
    }));

    // Sort data
    if (sortOrder === 'score') {
      data.sort((a, b) => b.score - a.score);
    } else if (sortOrder === 'weight') {
      data.sort((a, b) => b.weight - a.weight);
    } else {
      data.sort((a, b) => a.agent.localeCompare(b.agent));
    }

    return data;
  }, [agentScores, weights, sortOrder]);

  if (!chartData.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No agent scores available</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header with Sort Controls */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Agent Performance
        </h3>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Sort by:</span>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as any)}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="score">Score</option>
            <option value="weight">Weight</option>
            <option value="name">Name</option>
          </select>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ ...CHART_DEFAULTS.marginWithLabels, left: 100 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />

          <XAxis
            type="number"
            domain={[0, 100]}
            stroke={CHART_COLORS.axis}
            style={{ fontSize: CHART_DEFAULTS.fontSizeSmall }}
          />

          <YAxis
            type="category"
            dataKey="agent"
            stroke={CHART_COLORS.axis}
            width={90}
            style={{ fontSize: CHART_DEFAULTS.fontSize }}
          />

          <Tooltip content={<CustomTooltip />} />

          {showWeights && weights && (
            <Legend
              wrapperStyle={{ fontSize: CHART_DEFAULTS.fontSize }}
            />
          )}

          {/* Score Bars */}
          <Bar
            dataKey="score"
            name="Score"
            radius={[0, 4, 4, 0]}
            animationDuration={CHART_DEFAULTS.animationDuration}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
            <LabelList
              dataKey="score"
              position="right"
              formatter={(value: number) => formatTooltipValue(value, 'score')}
              style={{ fontSize: CHART_DEFAULTS.fontSizeSmall, fill: CHART_COLORS.axis }}
            />
          </Bar>

          {/* Weight Bars (if enabled) */}
          {showWeights && weights && (
            <Bar
              dataKey={(data: any) => data.weight * 100}
              name="Weight (%)"
              fill={CHART_COLORS.axis}
              opacity={0.3}
              radius={[0, 4, 4, 0]}
              animationDuration={CHART_DEFAULTS.animationDuration}
            />
          )}
        </BarChart>
      </ResponsiveContainer>

      {/* Score Legend */}
      <div className="mt-4 flex items-center gap-4 text-sm">
        <span className="text-gray-600">Score Ranges:</span>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: CHART_COLORS.strongBuy }} />
          <span className="text-gray-600">80-100 (Excellent)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: CHART_COLORS.buy }} />
          <span className="text-gray-600">70-80 (Good)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: CHART_COLORS.hold }} />
          <span className="text-gray-600">50-70 (Average)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: CHART_COLORS.sell }} />
          <span className="text-gray-600">&lt;50 (Poor)</span>
        </div>
      </div>

      {/* Detailed Breakdown */}
      {showWeights && weights && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          {chartData.map((agent, index) => (
            <div
              key={index}
              className="p-3 rounded-lg border"
              style={{
                borderColor: agent.color,
                backgroundColor: `${agent.color}10`
              }}
            >
              <p className="text-xs text-gray-600 mb-1">{agent.agent}</p>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold" style={{ color: agent.color }}>
                  {formatTooltipValue(agent.score, 'score')}
                </span>
                <span className="text-xs text-gray-500">
                  ({formatTooltipValue(agent.weight * 100, 'percent')})
                </span>
              </div>
              {agent.confidence !== undefined && (
                <p className="text-xs text-gray-500 mt-1">
                  Conf: {formatTooltipValue(agent.confidence * 100, 'score')}%
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AgentScoresBar;
