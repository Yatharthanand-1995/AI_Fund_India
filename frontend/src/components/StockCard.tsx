import { TrendingUp, TrendingDown, Activity, Shield, Users, MessageSquare } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { StockAnalysis } from '@/types';
import {
  formatNumber,
  formatPercent,
  getRecommendationColor,
  getScoreColor,
  getScoreBgColor,
  cn,
} from '@/lib/utils';

interface StockCardProps {
  analysis: StockAnalysis;
  detailed?: boolean;
}

export default function StockCard({ analysis, detailed = false }: StockCardProps) {
  const { symbol, composite_score, recommendation, confidence, agent_scores, narrative } = analysis;

  const agents = [
    { key: 'fundamentals', label: 'Fundamentals', icon: TrendingUp, color: 'text-blue-600' },
    { key: 'momentum', label: 'Momentum', icon: Activity, color: 'text-green-600' },
    { key: 'quality', label: 'Quality', icon: Shield, color: 'text-purple-600' },
    { key: 'sentiment', label: 'Sentiment', icon: MessageSquare, color: 'text-orange-600' },
    { key: 'institutional_flow', label: 'Inst. Flow', icon: Users, color: 'text-indigo-600' },
  ];

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-blue-600 text-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold">{symbol}</h2>
            <p className="text-primary-100 text-sm">Stock Analysis</p>
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold">{composite_score.toFixed(1)}</div>
            <div className="text-primary-100 text-sm">Composite Score</div>
          </div>
        </div>
      </div>

      {/* Recommendation */}
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 mb-1">Recommendation</p>
            <div
              className={cn(
                'inline-block px-4 py-2 rounded-lg border-2 font-bold text-lg',
                getRecommendationColor(recommendation as any)
              )}
            >
              {recommendation}
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600 mb-1">Confidence</p>
            <div className="text-2xl font-bold text-gray-900">
              {formatPercent(confidence * 100, 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Agent Scores */}
      <div className="px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Agent Analysis</h3>
        <div className="space-y-3">
          {agents.map(({ key, label, icon: Icon, color }) => {
            const agentData = agent_scores[key];
            if (!agentData) return null;

            return (
              <div key={key} className="flex items-center space-x-3">
                <Icon className={cn('h-5 w-5 flex-shrink-0', color)} />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{label}</span>
                    <span className={cn('font-bold', getScoreColor(agentData.score))}>
                      {agentData.score.toFixed(1)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={cn('h-2 rounded-full', getScoreBgColor(agentData.score))}
                      style={{ width: `${agentData.score}%` }}
                    />
                  </div>
                  {detailed && (
                    <p className="text-xs text-gray-500 mt-1">{agentData.reasoning}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Narrative */}
      {detailed && narrative && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Investment Narrative</h3>

          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-700 mb-2">Thesis</h4>
              <p className="text-sm text-gray-600">{narrative.investment_thesis}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-green-700 mb-2 flex items-center">
                  <TrendingUp className="h-4 w-4 mr-1" />
                  Key Strengths
                </h4>
                <ul className="space-y-1">
                  {narrative.key_strengths.map((strength, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start">
                      <span className="text-green-600 mr-2">•</span>
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-medium text-red-700 mb-2 flex items-center">
                  <TrendingDown className="h-4 w-4 mr-1" />
                  Key Risks
                </h4>
                <ul className="space-y-1">
                  {narrative.key_risks.map((risk, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start">
                      <span className="text-red-600 mr-2">•</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-700 mb-2">Summary</h4>
              <p className="text-sm text-gray-600">{narrative.summary}</p>
            </div>

            <div className="text-xs text-gray-400">
              Generated by {narrative.provider}
            </div>
          </div>
        </div>
      )}

      {/* View Details Link */}
      {!detailed && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <Link
            to={`/stock/${symbol}`}
            className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center justify-center space-x-1"
          >
            <span>View Full Analysis</span>
            <TrendingUp className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}
