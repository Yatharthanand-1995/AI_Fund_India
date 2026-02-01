/**
 * Watchlist Page - Portfolio Tracking
 *
 * Manage and track watchlist stocks
 */

import React from 'react';
import { useWatchlist } from '../hooks/useWatchlist';
import { Star, Trash2, RefreshCw, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Watchlist: React.FC = () => {
  const { watchlist, loading, error, remove, refresh, count } = useWatchlist();
  const navigate = useNavigate();

  const handleRemove = async (symbol: string) => {
    if (confirm(`Remove ${symbol} from watchlist?`)) {
      await remove(symbol);
    }
  };

  const handleAnalyze = (symbol: string) => {
    navigate(`/stock/${symbol}`);
  };

  if (loading && watchlist.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading watchlist...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Star className="w-8 h-8 text-yellow-500" />
            My Watchlist
          </h1>
          <p className="text-gray-600 mt-1">
            {count} stock{count !== 1 ? 's' : ''} in your watchlist
          </p>
        </div>
        <button
          onClick={() => refresh()}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh All
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-800">
            <AlertCircle className="w-5 h-5" />
            <p>Failed to load watchlist: {error.message}</p>
          </div>
        </div>
      )}

      {/* Watchlist Table */}
      {watchlist.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Latest Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Recommendation
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Added
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
                {watchlist.map((item) => (
                  <tr key={item.symbol} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => handleAnalyze(item.symbol)}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800"
                      >
                        {item.symbol}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {item.latest_score !== null && item.latest_score !== undefined ? (
                        <span className="text-sm font-semibold text-gray-900">
                          {item.latest_score.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {item.latest_recommendation ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {item.latest_recommendation}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600">
                        {new Date(item.added_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600">
                        {item.notes || '-'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleRemove(item.symbol)}
                        className="text-red-600 hover:text-red-900"
                        title="Remove from watchlist"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {watchlist.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Star className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Your watchlist is empty
          </h3>
          <p className="text-gray-600 mb-4">
            Add stocks to your watchlist to track their performance
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Analyze Stocks
          </button>
        </div>
      )}

      {/* Portfolio Performance Placeholder */}
      {watchlist.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Portfolio Performance
          </h2>
          <p className="text-gray-500 text-center py-12">
            Performance chart will be added in the next phase
          </p>
        </div>
      )}
    </div>
  );
};

export default Watchlist;
