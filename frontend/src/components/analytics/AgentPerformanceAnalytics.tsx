/**
 * Agent Performance Analytics Component
 *
 * Analyzes agent prediction accuracy and performance
 */

import { useState, useEffect } from 'react';
import { BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, TrendingUp, Award, Target } from 'lucide-react';
import Card from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';
import api from '@/lib/api';

const AGENT_NAMES = ['Fundamentals', 'Momentum', 'Quality', 'Sentiment', 'Institutional Flow'];

export default function AgentPerformanceAnalytics() {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    loadAgentAnalytics();
  }, []);

  const loadAgentAnalytics = async () => {
    setLoading(true);
    try {
      // Get top picks to analyze agent performance
      const response = await api.getTopPicks(50, false);
      const stocks = response.top_picks || [];

      if (stocks.length === 0) {
        setAnalytics({ error: 'No data available' });
        setLoading(false);
        return;
      }

      // Calculate average scores for each agent
      const agentAverages = {
        fundamentals: 0,
        momentum: 0,
        quality: 0,
        sentiment: 0,
        institutional_flow: 0,
      };

      const agentCounts = {
        fundamentals: 0,
        momentum: 0,
        quality: 0,
        sentiment: 0,
        institutional_flow: 0,
      };

      // Agent agreement analysis (how often agents agree on recommendations)
      let strongBuyCount = 0;
      let buyCount = 0;
      let holdCount = 0;

      stocks.forEach((stock: any) => {
        const scores = stock.agent_scores;

        Object.keys(agentAverages).forEach((agent) => {
          const score = scores[agent]?.score;
          if (score !== undefined && score !== null) {
            agentAverages[agent as keyof typeof agentAverages] += score;
            agentCounts[agent as keyof typeof agentCounts] += 1;
          }
        });

        // Count recommendations
        if (stock.recommendation === 'STRONG BUY') strongBuyCount++;
        else if (stock.recommendation === 'BUY') buyCount++;
        else if (stock.recommendation === 'HOLD') holdCount++;
      });

      // Calculate averages
      Object.keys(agentAverages).forEach((agent) => {
        const key = agent as keyof typeof agentAverages;
        agentAverages[key] = agentCounts[key] > 0
          ? agentAverages[key] / agentCounts[key]
          : 0;
      });

      // Agent correlation with positive returns
      const agentReturnCorrelation = {
        fundamentals: 0,
        momentum: 0,
        quality: 0,
        sentiment: 0,
        institutional_flow: 0,
      };

      stocks.forEach((stock: any) => {
        const return3m = stock.agent_scores.momentum?.metrics?.['3m_return'];
        if (return3m !== undefined && return3m > 0) {
          // If stock has positive returns, count how each agent scored it
          Object.keys(agentReturnCorrelation).forEach((agent) => {
            const score = stock.agent_scores[agent]?.score;
            if (score !== undefined && score > 60) {
              agentReturnCorrelation[agent as keyof typeof agentReturnCorrelation] += 1;
            }
          });
        }
      });

      // Calculate best performing agent (highest correlation with positive returns)
      const bestAgent = Object.entries(agentReturnCorrelation).reduce((best, [agent, count]) =>
        count > best[1] ? [agent, count] : best
      , ['', 0]);

      // Prepare chart data
      const agentScoreData = Object.entries(agentAverages).map(([agent, score]) => ({
        agent: agent.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
        score: parseFloat(score.toFixed(1)),
      }));

      const agentCorrelationData = Object.entries(agentReturnCorrelation).map(([agent, count]) => ({
        agent: agent.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
        'Positive Predictions': count,
      }));

      setAnalytics({
        agentAverages,
        agentReturnCorrelation,
        bestAgent: bestAgent[0].replace('_', ' ').split(' ').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
        bestAgentCount: bestAgent[1],
        agentScoreData,
        agentCorrelationData,
        totalAnalyzed: stocks.length,
        strongBuyCount,
        buyCount,
        holdCount,
      });
    } catch (error) {
      console.error('Failed to load agent analytics:', error);
      setAnalytics({ error: 'Failed to load analytics' });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <div className="p-12">
          <Loading size="lg" text="Analyzing agent performance..." />
        </div>
      </Card>
    );
  }

  if (!analytics || analytics.error) {
    return (
      <Card>
        <div className="p-6 text-center text-gray-600">
          {analytics?.error || 'Failed to load agent analytics'}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Stocks Analyzed</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.totalAnalyzed}
                </p>
              </div>
              <Activity className="h-8 w-8 text-blue-500" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Strong Buy Signals</p>
                <p className="text-3xl font-bold text-green-600 mt-1">
                  {analytics.strongBuyCount}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Best Agent</p>
                <p className="text-lg font-bold text-gray-900 mt-1">
                  {analytics.bestAgent}
                </p>
              </div>
              <Award className="h-8 w-8 text-yellow-500" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Positive Predictions</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.bestAgentCount}
                </p>
              </div>
              <Target className="h-8 w-8 text-purple-500" />
            </div>
          </div>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Average Agent Scores */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Average Agent Scores
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.agentScoreData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="agent" angle={-15} textAnchor="end" height={80} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="score" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Agent Correlation with Positive Returns */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Positive Return Predictions
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Number of stocks with positive 3M returns where agent scored {'>'}60
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.agentCorrelationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="agent" angle={-15} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="Positive Predictions" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Radar Chart */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Agent Performance Profile
          </h3>
          <div className="flex justify-center">
            <ResponsiveContainer width="100%" height={400}>
              <RadarChart data={analytics.agentScoreData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="agent" />
                <PolarRadiusAxis domain={[0, 100]} />
                <Tooltip />
                <Radar
                  name="Average Score"
                  dataKey="score"
                  stroke="#3B82F6"
                  fill="#3B82F6"
                  fillOpacity={0.6}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Card>

      {/* Agent Insights */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Agent Insights
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {AGENT_NAMES.map((name) => {
              const key = name.toLowerCase().replace(' ', '_');
              const avgScore = analytics.agentAverages[key as keyof typeof analytics.agentAverages] || 0;
              const correlationCount = analytics.agentReturnCorrelation[key as keyof typeof analytics.agentReturnCorrelation] || 0;

              return (
                <div key={name} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <h4 className="font-medium text-gray-900 mb-2">{name}</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Avg Score:</span>
                      <span className="font-semibold text-gray-900">{avgScore.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Positive Picks:</span>
                      <span className="font-semibold text-green-600">{correlationCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Accuracy:</span>
                      <span className="font-semibold text-blue-600">
                        {analytics.totalAnalyzed > 0
                          ? ((correlationCount / analytics.totalAnalyzed) * 100).toFixed(1)
                          : '0.0'}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Recommendation Distribution */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recommendation Distribution
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-6 bg-green-50 rounded-lg border-2 border-green-200">
              <p className="text-sm text-gray-600 mb-1">Strong Buy</p>
              <p className="text-4xl font-bold text-green-600">{analytics.strongBuyCount}</p>
              <p className="text-sm text-gray-600 mt-2">
                {((analytics.strongBuyCount / analytics.totalAnalyzed) * 100).toFixed(1)}% of total
              </p>
            </div>
            <div className="p-6 bg-blue-50 rounded-lg border-2 border-blue-200">
              <p className="text-sm text-gray-600 mb-1">Buy</p>
              <p className="text-4xl font-bold text-blue-600">{analytics.buyCount}</p>
              <p className="text-sm text-gray-600 mt-2">
                {((analytics.buyCount / analytics.totalAnalyzed) * 100).toFixed(1)}% of total
              </p>
            </div>
            <div className="p-6 bg-gray-50 rounded-lg border-2 border-gray-200">
              <p className="text-sm text-gray-600 mb-1">Hold</p>
              <p className="text-4xl font-bold text-gray-600">{analytics.holdCount}</p>
              <p className="text-sm text-gray-600 mt-2">
                {((analytics.holdCount / analytics.totalAnalyzed) * 100).toFixed(1)}% of total
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
