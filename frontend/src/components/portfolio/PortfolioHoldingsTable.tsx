import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Trash2, ExternalLink, ChevronDown, ChevronUp, TrendingUp, TrendingDown } from 'lucide-react';
import { cn, getRecommendationColor, getScoreColor } from '@/lib/utils';
import type { WatchlistItem } from '@/types';

interface PortfolioHoldingsTableProps {
  watchlist: WatchlistItem[];
  onRemove: (symbol: string) => void;
}

type SortField = 'symbol' | 'score' | 'recommendation' | 'added_at' | 'pnl';
type SortOrder = 'asc' | 'desc';

function calcPnlPct(item: WatchlistItem): number | null {
  if (item.entry_price == null || item.entry_price === 0) return null;
  if (item.current_price == null) return null;
  return ((item.current_price - item.entry_price) / item.entry_price) * 100;
}

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

  const hasPnl = watchlist.some(item => item.entry_price != null);

  const sortedWatchlist = [...watchlist].sort((a, b) => {
    let aVal: string | number, bVal: string | number;

    switch (sortField) {
      case 'symbol':
        aVal = a.symbol; bVal = b.symbol; break;
      case 'score':
        aVal = a.latest_score ?? -1; bVal = b.latest_score ?? -1; break;
      case 'recommendation':
        aVal = a.latest_recommendation || ''; bVal = b.latest_recommendation || ''; break;
      case 'added_at':
        aVal = typeof a.added_at === 'number' ? a.added_at : new Date(a.added_at).getTime();
        bVal = typeof b.added_at === 'number' ? b.added_at : new Date(b.added_at).getTime();
        break;
      case 'pnl':
        aVal = calcPnlPct(a) ?? -999; bVal = calcPnlPct(b) ?? -999; break;
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

  const formatDate = (ts: number | string) => {
    const d = typeof ts === 'number' ? new Date(ts) : new Date(ts);
    return d.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th onClick={() => handleSort('symbol')} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100">
                <div className="flex items-center gap-1">Symbol <SortIcon field="symbol" /></div>
              </th>
              <th onClick={() => handleSort('score')} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100">
                <div className="flex items-center gap-1">Score <SortIcon field="score" /></div>
              </th>
              <th onClick={() => handleSort('recommendation')} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100">
                <div className="flex items-center gap-1">Signal <SortIcon field="recommendation" /></div>
              </th>
              {hasPnl && (
                <th onClick={() => handleSort('pnl')} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100">
                  <div className="flex items-center gap-1">P&amp;L <SortIcon field="pnl" /></div>
                </th>
              )}
              <th onClick={() => handleSort('added_at')} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100">
                <div className="flex items-center gap-1">Added <SortIcon field="added_at" /></div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedWatchlist.map((item) => {
              const pnlPct = calcPnlPct(item);
              const pnlRupees = (item.entry_price != null && item.current_price != null && item.quantity != null)
                ? (item.current_price - item.entry_price) * item.quantity
                : null;

              return (
                <tr key={item.symbol} className="hover:bg-gray-50 group">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      to={`/stock/${item.symbol}`}
                      className="text-sm font-bold text-blue-600 hover:text-blue-800 flex items-center gap-2"
                    >
                      {item.symbol}
                      <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Link>
                    {item.entry_price != null && (
                      <p className="text-xs text-gray-400 mt-0.5">Entry ₹{item.entry_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</p>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {item.latest_score != null ? (
                      <span className={cn('text-sm font-bold', getScoreColor(item.latest_score))}>
                        {item.latest_score.toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {item.latest_recommendation ? (
                      <span className={cn('px-2 py-1 rounded text-xs font-medium', getRecommendationColor(item.latest_recommendation as any))}>
                        {item.latest_recommendation}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">—</span>
                    )}
                  </td>
                  {hasPnl && (
                    <td className="px-6 py-4 whitespace-nowrap">
                      {pnlPct != null ? (
                        <div className="flex items-center gap-1">
                          {pnlPct >= 0
                            ? <TrendingUp className="h-3.5 w-3.5 text-green-500" />
                            : <TrendingDown className="h-3.5 w-3.5 text-red-500" />
                          }
                          <div>
                            <span className={cn('text-sm font-semibold', pnlPct >= 0 ? 'text-green-600' : 'text-red-600')}>
                              {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                            </span>
                            {pnlRupees != null && (
                              <p className={cn('text-xs', pnlRupees >= 0 ? 'text-green-500' : 'text-red-500')}>
                                {pnlRupees >= 0 ? '+' : ''}₹{Math.abs(pnlRupees).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                              </p>
                            )}
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">Set entry price</span>
                      )}
                    </td>
                  )}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600">{formatDate(item.added_at)}</span>
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
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
