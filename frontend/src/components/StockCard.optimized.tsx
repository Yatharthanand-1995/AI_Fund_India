/**
 * Optimized StockCard Component
 *
 * Performance Improvements:
 * - React.memo to prevent unnecessary re-renders
 * - useMemo for expensive calculations
 * - Lazy loading for narrative sections
 */

import { memo, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import type { StockAnalysis } from '@/types';
import { getRecommendationColor } from '@/lib/chartUtils';

interface StockCardProps {
  analysis: StockAnalysis;
  detailed?: boolean;
  showNarrative?: boolean;
}

const StockCard = memo(function StockCard({
  analysis,
  detailed = false,
  showNarrative = true,
}: StockCardProps) {
  const navigate = useNavigate();
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());

  // Memoize expensive calculations
  const recommendationColor = useMemo(
    () => getRecommendationColor(analysis.recommendation),
    [analysis.recommendation]
  );

  const sortedAgentScores = useMemo(() => {
    return Object.entries(analysis.agent_scores).sort(
      ([, a], [, b]) => b.score - a.score
    );
  }, [analysis.agent_scores]);

  const toggleAgent = (agentKey: string) => {
    setExpandedAgents((prev) => {
      const next = new Set(prev);
      if (next.has(agentKey)) {
        next.delete(agentKey);
      } else {
        next.add(agentKey);
      }
      return next;
    });
  };

  const handleViewDetails = () => {
    navigate(`/stock/${analysis.symbol}`);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-blue-600 text-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-2xl font-bold">{analysis.symbol}</h3>
            {analysis.market_regime && (
              <p className="text-sm text-primary-100 mt-1">
                Market: {analysis.market_regime.trend} ({analysis.market_regime.volatility})
              </p>
            )}
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{analysis.composite_score.toFixed(1)}</div>
            <div className="text-sm text-primary-100">Composite Score</div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 space-y-4">
        {/* Recommendation Badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span
              className="px-4 py-2 rounded-full text-sm font-semibold"
              style={{
                backgroundColor: recommendationColor + '20',
                color: recommendationColor,
              }}
            >
              {analysis.recommendation}
            </span>
            <span className="text-sm text-gray-600">
              Confidence: {analysis.confidence.toFixed(1)}%
            </span>
          </div>

          {!detailed && (
            <button
              onClick={handleViewDetails}
              className="flex items-center space-x-1 text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              <span>View Details</span>
              <ExternalLink className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Agent Scores */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Agent Scores</h4>
          <div className="space-y-2">
            {sortedAgentScores.map(([agentKey, agentData]) => (
              <div key={agentKey} className="space-y-2">
                <div
                  className="flex items-center justify-between cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
                  onClick={() => detailed && toggleAgent(agentKey)}
                >
                  <div className="flex items-center space-x-3 flex-1">
                    <span className="text-sm font-medium text-gray-700 capitalize w-32">
                      {agentKey.replace('_', ' ')}
                    </span>
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-primary-600"
                        style={{ width: `${agentData.score}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-900 w-12 text-right">
                      {agentData.score.toFixed(1)}
                    </span>
                  </div>
                  {detailed && (
                    <div className="ml-2">
                      {expandedAgents.has(agentKey) ? (
                        <ChevronUp className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                  )}
                </div>

                {/* Expanded Agent Details (lazy loaded) */}
                {detailed && expandedAgents.has(agentKey) && agentData.reasoning && (
                  <div className="ml-8 p-3 bg-gray-50 rounded text-sm text-gray-600">
                    {agentData.reasoning}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Narrative (conditionally rendered) */}
        {detailed && showNarrative && analysis.narrative && (
          <div className="border-t pt-4 mt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Investment Thesis
            </h4>
            <div className="space-y-3 text-sm">
              <p className="text-gray-700">{analysis.narrative.investment_thesis}</p>

              {analysis.narrative.key_strengths.length > 0 && (
                <div>
                  <h5 className="font-medium text-green-700 mb-1">Key Strengths</h5>
                  <ul className="list-disc list-inside space-y-1 text-gray-600">
                    {analysis.narrative.key_strengths.map((strength, i) => (
                      <li key={i}>{strength}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysis.narrative.key_risks.length > 0 && (
                <div>
                  <h5 className="font-medium text-red-700 mb-1">Key Risks</h5>
                  <ul className="list-disc list-inside space-y-1 text-gray-600">
                    {analysis.narrative.key_risks.map((risk, i) => (
                      <li key={i}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

export default StockCard;
