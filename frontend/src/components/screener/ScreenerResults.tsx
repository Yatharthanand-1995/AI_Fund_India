/**
 * Screener Results Component
 *
 * Displays filtered stocks in table or card view
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpDown, Eye, Star, StarOff } from 'lucide-react';
import Card from '@/components/ui/Card';
import InvestmentIdeaCard from '@/components/InvestmentIdeaCard';
import { cn } from '@/lib/utils';
import { useWatchlist } from '@/hooks/useWatchlist';
import type { StockAnalysis } from '@/types';
import type { ViewMode } from '@/pages/Screener';

interface ScreenerResultsProps {
  stocks: StockAnalysis[];
  viewMode: ViewMode;
}

type SortField = 'symbol' | 'score' | 'recommendation' | 'sector' | 'momentum' | 'quality';
type SortOrder = 'asc' | 'desc';

export default function ScreenerResults({ stocks, viewMode }: ScreenerResultsProps) {
  const navigate = useNavigate();
  const { watchlist, add, remove } = useWatchlist();
  const [sortField, setSortField] = useState<SortField>('score');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const sortedStocks = [...stocks].sort((a, b) => {
    let aVal: any;
    let bVal: any;

    switch (sortField) {
      case 'symbol':
        aVal = a.symbol;
        bVal = b.symbol;
        break;
      case 'score':
        aVal = a.composite_score;
        bVal = b.composite_score;
        break;
      case 'recommendation':
        const recOrder = { 'STRONG BUY': 0, 'BUY': 1, 'HOLD': 2, 'SELL': 3, 'STRONG SELL': 4 };
        aVal = recOrder[a.recommendation as keyof typeof recOrder] ?? 5;
        bVal = recOrder[b.recommendation as keyof typeof recOrder] ?? 5;
        break;
      case 'sector':
        aVal = a.agent_scores.quality?.metrics?.sector || '';
        bVal = b.agent_scores.quality?.metrics?.sector || '';
        break;
      case 'momentum':
        aVal = a.agent_scores.momentum?.score || 0;
        bVal = b.agent_scores.momentum?.score || 0;
        break;
      case 'quality':
        aVal = a.agent_scores.quality?.score || 0;
        bVal = b.agent_scores.quality?.score || 0;
        break;
      default:
        aVal = 0;
        bVal = 0;
    }

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const isInWatchlist = (symbol: string) => {
    return watchlist.some(item => item.symbol === symbol);
  };

  const handleWatchlistToggle = (symbol: string) => {
    if (isInWatchlist(symbol)) {
      remove(symbol);
    } else {
      add(symbol);
    }
  };

  if (stocks.length === 0) {
    return (
      <Card>
        <div className="p-12 text-center">
          <p className="text-gray-600">No stocks match your filters</p>
          <p className="text-sm text-gray-500 mt-2">
            Try adjusting your filter criteria
          </p>
        </div>
      </Card>
    );
  }

  if (viewMode === 'cards') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {sortedStocks.map((stock, index) => (
          <InvestmentIdeaCard key={stock.symbol} analysis={stock} rank={index + 1} />
        ))}
      </div>
    );
  }

  // Table view
  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('symbol')}
                  className="flex items-center gap-1 text-xs font-medium text-gray-500 uppercase hover:text-gray-700"
                >
                  Symbol
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('score')}
                  className="flex items-center gap-1 text-xs font-medium text-gray-500 uppercase hover:text-gray-700"
                >
                  Score
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('recommendation')}
                  className="flex items-center gap-1 text-xs font-medium text-gray-500 uppercase hover:text-gray-700"
                >
                  Recommendation
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('sector')}
                  className="flex items-center gap-1 text-xs font-medium text-gray-500 uppercase hover:text-gray-700"
                >
                  Sector
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('momentum')}
                  className="flex items-center gap-1 text-xs font-medium text-gray-500 uppercase hover:text-gray-700"
                >
                  Momentum
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('quality')}
                  className="flex items-center gap-1 text-xs font-medium text-gray-500 uppercase hover:text-gray-700"
                >
                  Quality
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-xs font-medium text-gray-500 uppercase">
                  Returns
                </span>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-xs font-medium text-gray-500 uppercase">
                  Actions
                </span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedStocks.map((stock) => {
              const momentum = stock.agent_scores.momentum;
              const quality = stock.agent_scores.quality;
              const return1m = momentum?.metrics?.['1m_return'];
              const return3m = momentum?.metrics?.['3m_return'];

              return (
                <tr key={stock.symbol} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <button
                      onClick={() => navigate(`/stock/${stock.symbol}`)}
                      className="font-bold text-blue-600 hover:text-blue-800"
                    >
                      {stock.symbol}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-gray-900">
                        {stock.composite_score.toFixed(1)}
                      </span>
                      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full',
                            stock.composite_score >= 70 ? 'bg-green-500' :
                            stock.composite_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                          )}
                          style={{ width: `${stock.composite_score}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      'px-2 py-1 rounded text-xs font-medium',
                      stock.recommendation === 'STRONG BUY' && 'bg-green-100 text-green-800',
                      stock.recommendation === 'BUY' && 'bg-blue-100 text-blue-800',
                      stock.recommendation === 'HOLD' && 'bg-gray-100 text-gray-800',
                      stock.recommendation === 'SELL' && 'bg-orange-100 text-orange-800',
                      stock.recommendation === 'STRONG SELL' && 'bg-red-100 text-red-800'
                    )}>
                      {stock.recommendation}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {quality?.metrics?.sector || 'N/A'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      'font-medium',
                      (momentum?.score || 0) >= 70 ? 'text-green-600' :
                      (momentum?.score || 0) >= 50 ? 'text-yellow-600' : 'text-red-600'
                    )}>
                      {momentum?.score?.toFixed(0) || 'N/A'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      'font-medium',
                      (quality?.score || 0) >= 70 ? 'text-green-600' :
                      (quality?.score || 0) >= 50 ? 'text-yellow-600' : 'text-red-600'
                    )}>
                      {quality?.score?.toFixed(0) || 'N/A'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="space-y-1">
                      <div className={cn(
                        'font-medium',
                        (return1m || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        1M: {return1m !== undefined ? `${return1m > 0 ? '+' : ''}${return1m.toFixed(1)}%` : 'N/A'}
                      </div>
                      <div className={cn(
                        'font-medium',
                        (return3m || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        3M: {return3m !== undefined ? `${return3m > 0 ? '+' : ''}${return3m.toFixed(1)}%` : 'N/A'}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => navigate(`/stock/${stock.symbol}`)}
                        className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleWatchlistToggle(stock.symbol)}
                        className={cn(
                          'p-1 rounded',
                          isInWatchlist(stock.symbol)
                            ? 'text-yellow-600 hover:bg-yellow-50'
                            : 'text-gray-400 hover:bg-gray-50'
                        )}
                        title={isInWatchlist(stock.symbol) ? 'Remove from Watchlist' : 'Add to Watchlist'}
                      >
                        {isInWatchlist(stock.symbol) ? (
                          <Star className="h-4 w-4 fill-current" />
                        ) : (
                          <StarOff className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
