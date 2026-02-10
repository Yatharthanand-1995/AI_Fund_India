/**
 * Enhanced Watchlist Page - Portfolio Performance Tracking
 *
 * Features:
 * - Portfolio metrics dashboard
 * - Holdings table with sorting
 * - Portfolio insights (top/bottom performers, alerts)
 * - Score history tracking (placeholder for future)
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Star, RefreshCw, AlertCircle, BarChart3, List, Lightbulb } from 'lucide-react';
import { useWatchlist } from '@/hooks/useWatchlist';
import PortfolioMetrics from '@/components/portfolio/PortfolioMetrics';
import PortfolioHoldingsTable from '@/components/portfolio/PortfolioHoldingsTable';
import PortfolioInsights from '@/components/portfolio/PortfolioInsights';
import PortfolioScoreHistory from '@/components/portfolio/PortfolioScoreHistory';

type ViewTab = 'overview' | 'holdings' | 'insights';

export default function WatchlistEnhanced() {
  const { watchlist, loading, error, remove, refresh, count } = useWatchlist();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<ViewTab>('overview');

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
            <Star className="w-8 h-8 text-yellow-500 fill-current" />
            Portfolio Tracker
          </h1>
          <p className="text-gray-600 mt-1">
            {count} stock{count !== 1 ? 's' : ''} in your watchlist
          </p>
        </div>
        <button
          onClick={() => refresh()}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
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
            onClick={() => navigate('/ideas')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Browse Investment Ideas
          </button>
        </div>
      )}

      {/* Content */}
      {watchlist.length > 0 && (
        <>
          {/* Portfolio Metrics */}
          <PortfolioMetrics watchlist={watchlist} />

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('overview')}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
                  ${activeTab === 'overview'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <BarChart3 className="h-4 w-4" />
                Overview
              </button>
              <button
                onClick={() => setActiveTab('holdings')}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
                  ${activeTab === 'holdings'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <List className="h-4 w-4" />
                Holdings ({count})
              </button>
              <button
                onClick={() => setActiveTab('insights')}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
                  ${activeTab === 'insights'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Lightbulb className="h-4 w-4" />
                Insights
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="mt-6">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Score History */}
                <PortfolioScoreHistory watchlist={watchlist} />

                {/* Holdings Table */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    Holdings
                  </h2>
                  <PortfolioHoldingsTable
                    watchlist={watchlist}
                    onRemove={remove}
                  />
                </div>
              </div>
            )}

            {activeTab === 'holdings' && (
              <PortfolioHoldingsTable
                watchlist={watchlist}
                onRemove={remove}
              />
            )}

            {activeTab === 'insights' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <PortfolioInsights watchlist={watchlist} />
                </div>
                <div>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <h3 className="text-sm font-semibold text-blue-900 mb-3">
                      Portfolio Tips
                    </h3>
                    <ul className="space-y-2 text-sm text-blue-800">
                      <li className="flex items-start gap-2">
                        <span className="text-blue-600 font-bold mt-0.5">•</span>
                        <span>Regularly review stocks with scores below 50</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-blue-600 font-bold mt-0.5">•</span>
                        <span>Diversify across sectors to reduce risk</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-blue-600 font-bold mt-0.5">•</span>
                        <span>Monitor recommendation changes frequently</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-blue-600 font-bold mt-0.5">•</span>
                        <span>Keep portfolio size manageable (10-15 stocks)</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
