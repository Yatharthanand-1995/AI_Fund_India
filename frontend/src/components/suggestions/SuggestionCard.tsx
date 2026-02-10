/**
 * Suggestion Card Component
 *
 * Displays a stock suggestion with reasons and quick actions
 */

import { Star, Eye, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Card from '@/components/ui/Card';
import { cn, getRecommendationColor } from '@/lib/utils';
import { useWatchlist } from '@/hooks/useWatchlist';
import type { StockSuggestion } from '@/utils/suggestionEngine';

interface SuggestionCardProps {
  suggestion: StockSuggestion;
}

export default function SuggestionCard({ suggestion }: SuggestionCardProps) {
  const navigate = useNavigate();
  const { watchlist, add } = useWatchlist();
  const { stock, reasons, relevanceScore } = suggestion;

  const isInWatchlist = watchlist.some(w => w.symbol === stock.symbol);

  const handleAddToWatchlist = () => {
    if (!isInWatchlist) {
      add(stock.symbol);
    }
  };

  const handleViewDetails = () => {
    navigate(`/stock/${stock.symbol}`);
  };

  // Get reason type icon
  const getReasonIcon = (type: string) => {
    switch (type) {
      case 'similar':
        return <CheckCircle className="h-3 w-3 text-blue-600" />;
      case 'sector':
        return <TrendingUp className="h-3 w-3 text-purple-600" />;
      case 'diversification':
        return <AlertCircle className="h-3 w-3 text-orange-600" />;
      case 'trending':
        return <TrendingUp className="h-3 w-3 text-green-600" />;
      case 'gap':
        return <AlertCircle className="h-3 w-3 text-yellow-600" />;
      default:
        return null;
    }
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="text-lg font-bold text-gray-900">{stock.symbol}</h3>
            <p className="text-xs text-gray-600">
              {stock.agent_scores.quality?.metrics?.sector || 'Unknown Sector'}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">
              {stock.composite_score.toFixed(1)}
            </div>
            <div className="text-xs text-gray-500">Relevance: {relevanceScore}</div>
          </div>
        </div>

        {/* Recommendation Badge */}
        <div className="mb-3">
          <span
            className={cn(
              'px-2 py-1 rounded text-xs font-medium',
              getRecommendationColor(stock.recommendation as any)
            )}
          >
            {stock.recommendation}
          </span>
          <span className="ml-2 text-xs text-gray-600">
            {(stock.confidence * 100).toFixed(0)}% confidence
          </span>
        </div>

        {/* Reasons */}
        <div className="mb-4 space-y-2">
          <p className="text-xs font-semibold text-gray-700 uppercase">Why this stock?</p>
          {reasons.slice(0, 3).map((reason, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2 text-xs text-gray-700 bg-gray-50 p-2 rounded"
            >
              {getReasonIcon(reason.type)}
              <span>{reason.description}</span>
            </div>
          ))}
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-2 mb-4 text-xs">
          <div className="text-center p-2 bg-blue-50 rounded">
            <p className="text-gray-600">Momentum</p>
            <p className="font-bold text-gray-900">
              {stock.agent_scores.momentum?.score?.toFixed(0) || 'N/A'}
            </p>
          </div>
          <div className="text-center p-2 bg-green-50 rounded">
            <p className="text-gray-600">Quality</p>
            <p className="font-bold text-gray-900">
              {stock.agent_scores.quality?.score?.toFixed(0) || 'N/A'}
            </p>
          </div>
          <div className="text-center p-2 bg-purple-50 rounded">
            <p className="text-gray-600">3M Return</p>
            <p
              className={cn(
                'font-bold',
                (stock.agent_scores.momentum?.metrics?.['3m_return'] || 0) >= 0
                  ? 'text-green-600'
                  : 'text-red-600'
              )}
            >
              {stock.agent_scores.momentum?.metrics?.['3m_return']
                ? `${stock.agent_scores.momentum.metrics['3m_return'] > 0 ? '+' : ''}${stock.agent_scores.momentum.metrics['3m_return'].toFixed(1)}%`
                : 'N/A'}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={handleViewDetails}
            className="flex-1 btn-secondary text-sm py-2"
          >
            <Eye className="h-4 w-4 mr-1 inline" />
            View Details
          </button>
          {!isInWatchlist && (
            <button
              onClick={handleAddToWatchlist}
              className="flex-1 btn-primary text-sm py-2"
            >
              <Star className="h-4 w-4 mr-1 inline" />
              Add to Watchlist
            </button>
          )}
          {isInWatchlist && (
            <div className="flex-1 flex items-center justify-center text-sm text-green-600 font-medium">
              <CheckCircle className="h-4 w-4 mr-1" />
              In Watchlist
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
