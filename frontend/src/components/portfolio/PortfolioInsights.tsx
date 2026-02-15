import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, AlertTriangle, Star, Info } from 'lucide-react';
import Card from '@/components/ui/Card';
import { cn } from '@/lib/utils';

interface WatchlistItem {
  symbol: string;
  latest_score?: number;
  latest_recommendation?: string;
  added_at: number;
  notes?: string;
}

interface PortfolioInsightsProps {
  watchlist: WatchlistItem[];
}

export default function PortfolioInsights({ watchlist }: PortfolioInsightsProps) {
  // Filter stocks with scores
  const stocksWithScores = watchlist.filter(item =>
    item.latest_score !== null && item.latest_score !== undefined
  );

  if (stocksWithScores.length === 0) {
    return (
      <Card>
        <div className="p-6 text-center text-gray-600">
          <Info className="h-8 w-8 mx-auto mb-2 text-gray-400" />
          <p>Add stocks to your watchlist to see portfolio insights</p>
        </div>
      </Card>
    );
  }

  // Sort by score
  const sortedByScore = [...stocksWithScores].sort((a, b) =>
    (b.latest_score || 0) - (a.latest_score || 0)
  );

  // Get top and bottom performers
  const topPerformers = sortedByScore.slice(0, 3);
  const bottomPerformers = sortedByScore.slice(-3).reverse();

  // Find stocks needing attention (low score or SELL recommendation)
  const needsAttention = watchlist.filter(item => {
    const hasLowScore = (item.latest_score || 0) < 50;
    const hasSellRec = item.latest_recommendation?.includes('SELL');
    return hasLowScore || hasSellRec;
  });

  return (
    <Card>
      <div className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Star className="h-5 w-5 text-yellow-500" />
          Portfolio Insights
        </h2>

        <div className="space-y-6">
          {/* Top Performers */}
          <div>
            <h3 className="text-sm font-semibold text-green-700 mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Top Performers
            </h3>
            <div className="space-y-2">
              {topPerformers.map((stock, idx) => (
                <Link
                  key={stock.symbol}
                  to={`/stock/${stock.symbol}`}
                  className="flex items-center justify-between p-3 bg-green-50 hover:bg-green-100 rounded-lg transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl font-bold text-green-300">
                      #{idx + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-gray-900 group-hover:text-blue-600">
                        {stock.symbol}
                      </p>
                      {stock.latest_recommendation && (
                        <p className="text-xs text-gray-600">
                          {stock.latest_recommendation}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-green-600">
                      {stock.latest_score?.toFixed(1)}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Needs Attention */}
          {needsAttention.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-yellow-700 mb-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Needs Attention ({needsAttention.length})
              </h3>
              <div className="space-y-2">
                {needsAttention.slice(0, 3).map((stock) => (
                  <Link
                    key={stock.symbol}
                    to={`/stock/${stock.symbol}`}
                    className="flex items-center justify-between p-3 bg-yellow-50 hover:bg-yellow-100 rounded-lg transition-colors group"
                  >
                    <div>
                      <p className="text-sm font-semibold text-gray-900 group-hover:text-blue-600">
                        {stock.symbol}
                      </p>
                      <p className="text-xs text-gray-600">
                        {stock.latest_recommendation || 'No recent data'}
                      </p>
                    </div>
                    <div className="text-right">
                      {stock.latest_score !== null && stock.latest_score !== undefined ? (
                        <p className={cn(
                          'text-sm font-bold',
                          stock.latest_score < 50 ? 'text-red-600' : 'text-yellow-600'
                        )}>
                          {stock.latest_score.toFixed(1)}
                        </p>
                      ) : (
                        <p className="text-xs text-gray-400">No score</p>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Bottom Performers */}
          {bottomPerformers.length > 0 && needsAttention.length === 0 && (
            <div>
              <h3 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
                <TrendingDown className="h-4 w-4" />
                Lower Scores
              </h3>
              <div className="space-y-2">
                {bottomPerformers.map((stock) => (
                  <Link
                    key={stock.symbol}
                    to={`/stock/${stock.symbol}`}
                    className="flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors group"
                  >
                    <div>
                      <p className="text-sm font-semibold text-gray-900 group-hover:text-blue-600">
                        {stock.symbol}
                      </p>
                      {stock.latest_recommendation && (
                        <p className="text-xs text-gray-600">
                          {stock.latest_recommendation}
                        </p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-gray-600">
                        {stock.latest_score?.toFixed(1)}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Quick Stats */}
          <div className="pt-4 border-t border-gray-200">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Highest Score</p>
                <p className="font-bold text-gray-900">
                  {topPerformers[0]?.latest_score?.toFixed(1) || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-gray-600">Lowest Score</p>
                <p className="font-bold text-gray-900">
                  {bottomPerformers[bottomPerformers.length - 1]?.latest_score?.toFixed(1) || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-gray-600">Stocks Above 70</p>
                <p className="font-bold text-green-600">
                  {stocksWithScores.filter(s => (s.latest_score || 0) >= 70).length}
                </p>
              </div>
              <div>
                <p className="text-gray-600">Stocks Below 50</p>
                <p className="font-bold text-red-600">
                  {stocksWithScores.filter(s => (s.latest_score || 0) < 50).length}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
