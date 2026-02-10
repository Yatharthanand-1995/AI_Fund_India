import { useState } from 'react';
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp } from 'lucide-react';
import Card from '@/components/ui/Card';
import type { BacktestSignal } from '@/types';

interface BacktestSignalsTableProps {
  signals: BacktestSignal[];
}

type SortField = 'date' | 'symbol' | 'score' | 'return_3m' | 'alpha_3m';
type SortOrder = 'asc' | 'desc';

export default function BacktestSignalsTable({ signals }: BacktestSignalsTableProps) {
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [filterRec, setFilterRec] = useState<string>('all');

  const itemsPerPage = 25;

  // Filter signals
  const filteredSignals = signals.filter(signal => {
    if (filterRec === 'all') return true;
    return signal.recommendation === filterRec;
  });

  // Sort signals
  const sortedSignals = [...filteredSignals].sort((a, b) => {
    let aVal: any, bVal: any;

    switch (sortField) {
      case 'date':
        aVal = new Date(a.date).getTime();
        bVal = new Date(b.date).getTime();
        break;
      case 'symbol':
        aVal = a.symbol;
        bVal = b.symbol;
        break;
      case 'score':
        aVal = a.composite_score;
        bVal = b.composite_score;
        break;
      case 'return_3m':
        aVal = a.forward_return_3m || 0;
        bVal = b.forward_return_3m || 0;
        break;
      case 'alpha_3m':
        aVal = a.alpha_3m || 0;
        bVal = b.alpha_3m || 0;
        break;
      default:
        return 0;
    }

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  // Paginate
  const totalPages = Math.ceil(sortedSignals.length / itemsPerPage);
  const startIdx = (currentPage - 1) * itemsPerPage;
  const paginatedSignals = sortedSignals.slice(startIdx, startIdx + itemsPerPage);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
    setCurrentPage(1);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getRecBadge = (rec: string) => {
    const styles: Record<string, string> = {
      'STRONG BUY': 'bg-green-100 text-green-800',
      'BUY': 'bg-green-50 text-green-700',
      'WEAK BUY': 'bg-yellow-100 text-yellow-800',
      'HOLD': 'bg-gray-100 text-gray-800',
      'WEAK SELL': 'bg-red-50 text-red-700',
      'SELL': 'bg-red-100 text-red-800'
    };

    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${styles[rec] || 'bg-gray-100 text-gray-800'}`}>
        {rec}
      </span>
    );
  };

  const recommendations = ['STRONG BUY', 'BUY', 'WEAK BUY', 'HOLD', 'WEAK SELL', 'SELL'];

  return (
    <Card>
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Backtest Signals ({filteredSignals.length})
          </h2>

          {/* Filter */}
          <select
            value={filterRec}
            onChange={(e) => {
              setFilterRec(e.target.value);
              setCurrentPage(1);
            }}
            className="input text-sm"
          >
            <option value="all">All Recommendations</option>
            {recommendations.map(rec => (
              <option key={rec} value={rec}>{rec}</option>
            ))}
          </select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  onClick={() => handleSort('date')}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                >
                  <div className="flex items-center gap-1">
                    Date <SortIcon field="date" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('symbol')}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                >
                  <div className="flex items-center gap-1">
                    Symbol <SortIcon field="symbol" />
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Recommendation
                </th>
                <th
                  onClick={() => handleSort('score')}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                >
                  <div className="flex items-center gap-1">
                    Score <SortIcon field="score" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('return_3m')}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                >
                  <div className="flex items-center gap-1">
                    3M Return <SortIcon field="return_3m" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('alpha_3m')}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                >
                  <div className="flex items-center gap-1">
                    3M Alpha <SortIcon field="alpha_3m" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {paginatedSignals.map((signal, idx) => (
                <tr key={`${signal.symbol}-${signal.date}-${idx}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {formatDate(signal.date)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    {signal.symbol}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {getRecBadge(signal.recommendation)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {signal.composite_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm">
                    {signal.forward_return_3m !== null && signal.forward_return_3m !== undefined ? (
                      <span className={signal.forward_return_3m >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                        {signal.forward_return_3m >= 0 ? <TrendingUp className="h-3 w-3 inline mr-1" /> : <TrendingDown className="h-3 w-3 inline mr-1" />}
                        {signal.forward_return_3m >= 0 ? '+' : ''}{signal.forward_return_3m.toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm">
                    {signal.alpha_3m !== null && signal.alpha_3m !== undefined ? (
                      <span className={signal.alpha_3m >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                        {signal.alpha_3m >= 0 ? '+' : ''}{signal.alpha_3m.toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <p className="text-sm text-gray-600">
              Showing {startIdx + 1}-{Math.min(startIdx + itemsPerPage, sortedSignals.length)} of {sortedSignals.length} signals
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {filteredSignals.length === 0 && (
          <div className="text-center py-8 text-gray-600">
            No signals found matching the filter
          </div>
        )}
      </div>
    </Card>
  );
}
