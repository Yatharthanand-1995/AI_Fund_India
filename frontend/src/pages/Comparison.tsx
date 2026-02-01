/**
 * Comparison Page
 *
 * Compare multiple stocks side-by-side (2-4 stocks)
 */

import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { Plus, X, AlertCircle, TrendingUp } from 'lucide-react';
import api from '../lib/api';

const Comparison: React.FC = () => {
  const {
    comparisonStocks,
    addToComparison,
    removeFromComparison,
    clearComparison,
    canAddToComparison
  } = useStore();

  const [searchSymbol, setSearchSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonData, setComparisonData] = useState<any[]>([]);

  const handleAddStock = () => {
    if (searchSymbol && canAddToComparison()) {
      addToComparison(searchSymbol.toUpperCase());
      setSearchSymbol('');
    }
  };

  const handleCompare = async () => {
    if (comparisonStocks.length < 2) {
      setError('Please select at least 2 stocks to compare');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.compareStocks(comparisonStocks, false);
      setComparisonData(response.comparisons || []);
    } catch (err: any) {
      setError(err.message || 'Failed to compare stocks');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Stock Comparison</h1>
        <p className="text-gray-600 mt-1">
          Compare up to 4 stocks side-by-side
        </p>
      </div>

      {/* Stock Selection */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Select Stocks to Compare
        </h2>

        {/* Selected Stocks */}
        <div className="flex flex-wrap gap-2 mb-4">
          {comparisonStocks.map((symbol) => (
            <div
              key={symbol}
              className="flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-800 rounded-lg"
            >
              <span className="font-medium">{symbol}</span>
              <button
                onClick={() => removeFromComparison(symbol)}
                className="hover:text-blue-900"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}

          {/* Add Stock Input */}
          {canAddToComparison() && (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddStock()}
                placeholder="Enter symbol..."
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleAddStock}
                disabled={!searchSymbol}
                className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleCompare}
            disabled={comparisonStocks.length < 2 || loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Comparing...' : 'Compare'}
          </button>
          {comparisonStocks.length > 0 && (
            <button
              onClick={clearComparison}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Clear All
            </button>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-lg">
            <AlertCircle className="w-5 h-5" />
            <p>{error}</p>
          </div>
        )}
      </div>

      {/* Comparison Results */}
      {comparisonData.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Comparison Results
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Metric
                  </th>
                  {comparisonData.map((stock) => (
                    <th
                      key={stock.symbol}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {stock.symbol}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    Composite Score
                  </td>
                  {comparisonData.map((stock) => (
                    <td key={stock.symbol} className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-semibold text-gray-900">
                        {stock.composite_score?.toFixed(1) || 'N/A'}
                      </span>
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    Recommendation
                  </td>
                  {comparisonData.map((stock) => (
                    <td key={stock.symbol} className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {stock.recommendation || 'N/A'}
                      </span>
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    Confidence
                  </td>
                  {comparisonData.map((stock) => (
                    <td key={stock.symbol} className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600">
                        {stock.confidence ? `${(stock.confidence * 100).toFixed(0)}%` : 'N/A'}
                      </span>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {comparisonStocks.length === 0 && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <TrendingUp className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No stocks selected
          </h3>
          <p className="text-gray-600">
            Add 2-4 stocks above to start comparing
          </p>
        </div>
      )}

      {/* Placeholder for Charts */}
      {comparisonData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Side-by-Side Charts
          </h2>
          <p className="text-gray-500 text-center py-12">
            Comparison charts will be added in the next phase
          </p>
        </div>
      )}
    </div>
  );
};

export default Comparison;
