import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Trash2, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { cn, getRecommendationColor, getScoreColor } from '@/lib/utils';

interface WatchlistItem {
  symbol: string;
  latest_score?: number;
  latest_recommendation?: string;
  added_at: string;
  notes?: string;
}

interface PortfolioHoldingsTableProps {
  watchlist: WatchlistItem[];
  onRemove: (symbol: string) => void;
}

type SortField = 'symbol' | 'score' | 'recommendation' | 'added_at';
type SortOrder = 'asc' | 'desc';

export default function PortfolioHoldingsTable({ watchlist, onRemove }: PortfolioHoldingsTableProps) {
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

  const sortedWatchlist = [...watchlist].sort((a, b) => {
    let aVal: any, bVal: any;

    switch (sortField) {
      case 'symbol':
        aVal = a.symbol;
        bVal = b.symbol;
        break;
      case 'score':
        aVal = a.latest_score ?? -1;
        bVal = b.latest_score ?? -1;
        break;
      case 'recommendation':
        aVal = a.latest_recommendation || '';
        bVal = b.latest_recommendation || '';
        break;
      case 'added_at':
        aVal = new Date(a.added_at).getTime();
        bVal = new Date(b.added_at).getTime();
        break;
      default:
        return 0;
    }

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />;
  };

  const handleRemove = (symbol: string) => {
    if (confirm(`Remove ${symbol} from watchlist?`)) {
      onRemove(symbol);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                onClick={() => handleSort('symbol')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-1">
                  Symbol <SortIcon field="symbol" />
                </div>
              </th>
              <th
                onClick={() => handleSort('score')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-1">
                  Latest Score <SortIcon field="score" />
                </div>
              </th>
              <th
                onClick={() => handleSort('recommendation')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-1">
                  Recommendation <SortIcon field="recommendation" />
                </div>
              </th>
              <th
                onClick={() => handleSort('added_at')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-1">
                  Added <SortIcon field="added_at" />
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Notes
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedWatchlist.map((item) => (
              <tr key={item.symbol} className="hover:bg-gray-50 group">
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link
                    to={`/stock/${item.symbol}`}
                    className="text-sm font-bold text-blue-600 hover:text-blue-800 flex items-center gap-2"
                  >
                    {item.symbol}
                    <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {item.latest_score !== null && item.latest_score !== undefined ? (
                    <span className={cn('text-sm font-bold', getScoreColor(item.latest_score))}>
                      {item.latest_score.toFixed(1)}
                    </span>
                  ) : (
                    <span className="text-sm text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {item.latest_recommendation ? (
                    <span className={cn(
                      'px-2 py-1 rounded text-xs font-medium',
                      getRecommendationColor(item.latest_recommendation as any)
                    )}>
                      {item.latest_recommendation}
                    </span>
                  ) : (
                    <span className="text-sm text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-600">
                    {new Date(item.added_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                </td>
                <td className="px-6 py-4 max-w-xs">
                  <span className="text-sm text-gray-600 truncate block">
                    {item.notes || '-'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Link
                      to={`/stock/${item.symbol}`}
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="View analysis"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                    <button
                      onClick={() => handleRemove(item.symbol)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Remove from watchlist"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
