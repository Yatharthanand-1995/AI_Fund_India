/**
 * Agent Scores Radar Chart Component
 *
 * 5-point radar chart showing scores from all agents:
 * - Fundamentals
 * - Momentum
 * - Quality
 * - Sentiment
 * - Institutional Flow
 *
 * Features:
 * - Compare current vs historical average
 * - Interactive tooltips with reasoning
 * - Legend toggle
 */

import React, { useMemo } from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import {
  CHART_COLORS,
  CHART_DEFAULTS,
  formatTooltipValue,
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

export interface AgentScoresRadarProps {
  agentScores: Record<string, AgentScore>;
  historicalAvg?: Record<string, AgentScore>;
  height?: number;
  showHistorical?: boolean;
  className?: string;
}

// ============================================================================
// Custom Tooltip
// ============================================================================

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg border border-gray-700 max-w-xs">
      <p className="text-sm font-semibold mb-2">{data.agent}</p>
      {payload.map((entry: any, index: number) => (
        <div key={index} className="mb-2">
          <div className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-300">{entry.name}:</span>
            <span className="font-semibold">
              {formatTooltipValue(entry.value, 'score')}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// Component
// ============================================================================

export const AgentScoresRadar: React.FC<AgentScoresRadarProps> = ({
  agentScores,
  historicalAvg,
  height = 400,
  showHistorical = true,
  className = ''
}) => {
  // Transform agent scores for radar chart
  const chartData = useMemo(() => {
    const currentScores = transformAgentScores(agentScores);

    if (historicalAvg && showHistorical) {
      const avgScores = transformAgentScores(historicalAvg);

      // Merge current and historical
      return currentScores.map((current, index) => ({
        ...current,
        avgScore: avgScores[index]?.score || 0
      }));
    }

    return currentScores;
  }, [agentScores, historicalAvg, showHistorical]);

  if (!chartData.length) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <p className="text-gray-500">No agent scores available</p>
      </div>
    );
  }

  const hasHistorical = historicalAvg && showHistorical;

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Agent Scores Breakdown
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {hasHistorical
            ? 'Current scores (blue) vs Historical average (green)'
            : 'Current agent scores'}
        </p>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <RadarChart data={chartData}>
          <PolarGrid stroke={CHART_COLORS.grid} />

          <PolarAngleAxis
            dataKey="agent"
            tick={{
              fill: CHART_COLORS.axis,
              fontSize: CHART_DEFAULTS.fontSize
            }}
          />

          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{
              fill: CHART_COLORS.axis,
              fontSize: CHART_DEFAULTS.fontSizeSmall
            }}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend
            wrapperStyle={{
              fontSize: CHART_DEFAULTS.fontSize,
              paddingTop: '20px'
            }}
          />

          {/* Current scores */}
          <Radar
            name="Current Score"
            dataKey="score"
            stroke={CHART_COLORS.primary}
            fill={CHART_COLORS.primary}
            fillOpacity={0.6}
            strokeWidth={CHART_DEFAULTS.strokeWidth}
            animationDuration={CHART_DEFAULTS.animationDuration}
          />

          {/* Historical average (if available) */}
          {hasHistorical && (
            <Radar
              name="Historical Avg"
              dataKey="avgScore"
              stroke={CHART_COLORS.success}
              fill={CHART_COLORS.success}
              fillOpacity={0.3}
              strokeWidth={CHART_DEFAULTS.strokeWidth}
              strokeDasharray="5 5"
              animationDuration={CHART_DEFAULTS.animationDuration}
            />
          )}
        </RadarChart>
      </ResponsiveContainer>

      {/* Score Summary */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-3">
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
            <p className="text-lg font-bold" style={{ color: agent.color }}>
              {formatTooltipValue(agent.score, 'score')}
            </p>
            {hasHistorical && (
              <p className="text-xs text-gray-500 mt-1">
                Avg: {formatTooltipValue(agent.avgScore || 0, 'score')}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Agent Details (if reasoning available) */}
      <div className="mt-6 space-y-2">
        {Object.entries(agentScores).map(([agentKey, agentData]) => {
          if (!agentData.reasoning) return null;

          const agentInfo = chartData.find(a =>
            a.agent.toLowerCase().includes(agentKey.split('_')[0].toLowerCase())
          );

          return (
            <details
              key={agentKey}
              className="p-3 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
            >
              <summary className="cursor-pointer font-medium text-gray-900 flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: agentInfo?.color || CHART_COLORS.axis }}
                />
                {agentInfo?.agent || agentKey}
                <span className="ml-auto text-sm text-gray-500">
                  Score: {formatTooltipValue(agentData.score, 'score')}
                  {agentData.confidence && (
                    <> • Confidence: {formatTooltipValue(agentData.confidence * 100, 'score')}%</>
                  )}
                </span>
              </summary>
              <p className="mt-2 text-sm text-gray-600 pl-5">
                {agentData.reasoning}
              </p>
            </details>
          );
        })}
      </div>
    </div>
  );
};

export default AgentScoresRadar;
