import { Link } from 'react-router-dom';
import { ExternalLink, Star, TrendingUp, TrendingDown } from 'lucide-react';
import type { StockAnalysis } from '@/types';
import { getRecommendationColor, getScoreColor, cn } from '@/lib/utils';
import { useWatchlist } from '@/hooks/useWatchlist';

interface IdeasComparisonTableProps {
  stocks: StockAnalysis[];
}

export default function IdeasComparisonTable({ stocks }: IdeasComparisonTableProps) {
  const { watchlist, add, remove } = useWatchlist();

  const isInWatchlist = (symbol: string) => watchlist.some(item => item.symbol === symbol);

  const handleWatchlistToggle = (symbol: string) => {
    if (isInWatchlist(symbol)) {
      remove(symbol);
    } else {
      add(symbol);
    }
  };

  if (stocks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-600">
        No stocks to compare
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="sticky left-0 z-20 bg-gray-50 px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rank / Symbol
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Score
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Recommendation
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Confidence
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Fundamentals
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Momentum
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quality
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sentiment
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Inst. Flow
              </th>
              <th className="sticky right-0 z-20 bg-gray-50 px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {stocks.map((stock, idx) => (
              <tr key={stock.symbol} className="hover:bg-gray-50">
                {/* Rank / Symbol */}
                <td className="sticky left-0 z-10 bg-white px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-bold text-gray-300">
                      #{idx + 1}
                    </span>
                    <div>
                      <Link
                        to={`/stock/${stock.symbol}`}
                        className="text-sm font-bold text-blue-600 hover:text-blue-700"
                      >
                        {stock.symbol}
                      </Link>
                      <p className="text-xs text-gray-500">
                        {stock.agent_scores?.fundamentals?.metrics?.sector || 'N/A'}
                      </p>
                    </div>
                  </div>
                </td>

                {/* Score */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className={cn('text-xl font-bold', getScoreColor(stock.composite_score))}>
                    {stock.composite_score.toFixed(1)}
                  </div>
                </td>

                {/* Recommendation */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={cn(
                      'px-2 py-1 rounded text-xs font-medium',
                      getRecommendationColor(stock.recommendation as any)
                    )}
                  >
                    {stock.recommendation}
                  </span>
                </td>

                {/* Confidence */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-2 w-20">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${stock.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-gray-700">
                      {(stock.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </td>

                {/* Agent Scores */}
                {['fundamentals', 'momentum', 'quality', 'sentiment', 'institutional_flow'].map(agent => {
                  const score = stock.agent_scores?.[agent]?.score || 0;
                  return (
                    <td key={agent} className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className={cn('text-sm font-bold', getScoreColor(score))}>
                          {score.toFixed(0)}
                        </div>
                        {score >= 80 && <TrendingUp className="h-3 w-3 text-green-600" />}
                        {score < 50 && <TrendingDown className="h-3 w-3 text-red-600" />}
                      </div>
                    </td>
                  );
                })}

                {/* Actions */}
                <td className="sticky right-0 z-10 bg-white px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleWatchlistToggle(stock.symbol)}
                      className={cn(
                        'p-2 rounded-lg transition-colors',
                        isInWatchlist(stock.symbol)
                          ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100'
                          : 'text-gray-400 hover:text-blue-600 hover:bg-blue-50'
                      )}
                      title={isInWatchlist(stock.symbol) ? 'Remove from watchlist' : 'Add to watchlist'}
                    >
                      <Star className={cn('h-4 w-4', isInWatchlist(stock.symbol) && 'fill-current')} />
                    </button>
                    <Link
                      to={`/stock/${stock.symbol}`}
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="View full analysis"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {stocks.length > 10 && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-center text-sm text-gray-600">
          Showing top {stocks.length} stocks. Use filters to refine your search.
        </div>
      )}
    </div>
  );
}
