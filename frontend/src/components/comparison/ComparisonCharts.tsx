/**
 * Comparison Charts Component
 *
 * Visual comparison charts for multiple stocks
 */

import { BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import Card from '@/components/ui/Card';
import type { StockAnalysis } from '@/types';

interface ComparisonChartsProps {
  stocks: StockAnalysis[];
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

export default function ComparisonCharts({ stocks }: ComparisonChartsProps) {
  // Prepare agent scores data for radar chart
  const agentScoresData = [
    {
      agent: 'Fundamentals',
      ...stocks.reduce((acc, stock, _idx) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.fundamentals?.score || 0
      }), {})
    },
    {
      agent: 'Momentum',
      ...stocks.reduce((acc, stock, _idx) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.momentum?.score || 0
      }), {})
    },
    {
      agent: 'Quality',
      ...stocks.reduce((acc, stock, _idx) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.quality?.score || 0
      }), {})
    },
    {
      agent: 'Sentiment',
      ...stocks.reduce((acc, stock, _idx) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.sentiment?.score || 0
      }), {})
    },
    {
      agent: 'Inst. Flow',
      ...stocks.reduce((acc, stock, _idx) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.institutional_flow?.score || 0
      }), {})
    },
  ];

  // Prepare returns data for bar chart
  const returnsData = [
    {
      period: '1M',
      ...stocks.reduce((acc, stock) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.momentum?.metrics?.['1m_return'] || 0
      }), {})
    },
    {
      period: '3M',
      ...stocks.reduce((acc, stock) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.momentum?.metrics?.['3m_return'] || 0
      }), {})
    },
    {
      period: '6M',
      ...stocks.reduce((acc, stock) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.momentum?.metrics?.['6m_return'] || 0
      }), {})
    },
    {
      period: '1Y',
      ...stocks.reduce((acc, stock) => ({
        ...acc,
        [stock.symbol]: stock.agent_scores.momentum?.metrics?.['1y_return'] || 0
      }), {})
    },
  ];

  // Prepare composite scores data
  const scoresData = stocks.map(stock => ({
    symbol: stock.symbol,
    score: stock.composite_score
  }));

  return (
    <div className="space-y-6">
      {/* Agent Scores Comparison */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Agent Scores Comparison
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={agentScoresData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="agent" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              {stocks.map((stock, idx) => (
                <Bar
                  key={stock.symbol}
                  dataKey={stock.symbol}
                  fill={COLORS[idx % COLORS.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Returns Comparison */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Returns Comparison
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={returnsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis />
                <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                <Legend />
                {stocks.map((stock, idx) => (
                  <Bar
                    key={stock.symbol}
                    dataKey={stock.symbol}
                    fill={COLORS[idx % COLORS.length]}
                    radius={[4, 4, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Composite Scores Comparison */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Composite Scores
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={scoresData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis type="category" dataKey="symbol" />
                <Tooltip />
                <Bar
                  dataKey="score"
                  fill="#3B82F6"
                  radius={[0, 4, 4, 0]}
                  label={{ position: 'right', formatter: (value: number) => value.toFixed(1) }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Radar Chart for Overall Profile */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Overall Profile Comparison
          </h3>
          <div className="flex justify-center">
            <ResponsiveContainer width="100%" height={400}>
              <RadarChart data={agentScoresData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="agent" />
                <PolarRadiusAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                {stocks.map((stock, idx) => (
                  <Radar
                    key={stock.symbol}
                    name={stock.symbol}
                    dataKey={stock.symbol}
                    stroke={COLORS[idx % COLORS.length]}
                    fill={COLORS[idx % COLORS.length]}
                    fillOpacity={0.3}
                  />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Card>
    </div>
  );
}
