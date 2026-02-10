/**
 * Enhanced Stock Comparison Page
 *
 * Compare 2-5 stocks side-by-side with detailed analysis
 * Features:
 * - Comprehensive metrics comparison
 * - Visual charts (agent scores, returns, radar)
 * - Strengths/weaknesses analysis
 * - Category winners
 * - Export functionality
 */

import { useState } from 'react';
import { useStore } from '../store/useStore';
import { Plus, X, AlertCircle, TrendingUp, Download, BarChart3 } from 'lucide-react';
import { SymbolInput } from '../components/ui/SymbolInput';
import Card from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';
import ComparisonTable from '@/components/comparison/ComparisonTable';
import ComparisonCharts from '@/components/comparison/ComparisonCharts';
import ComparisonSummary from '@/components/comparison/ComparisonSummary';
import api from '../lib/api';
import type { StockAnalysis } from '@/types';

export default function Comparison() {
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
  const [comparisonData, setComparisonData] = useState<StockAnalysis[]>([]);
  const [activeView, setActiveView] = useState<'summary' | 'table' | 'charts'>('summary');

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
      setComparisonData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (comparisonData.length === 0) return;

    // Create CSV content
    const headers = ['Metric', ...comparisonData.map(s => s.symbol)];
    const rows = [
      ['Composite Score', ...comparisonData.map(s => s.composite_score.toFixed(1))],
      ['Recommendation', ...comparisonData.map(s => s.recommendation)],
      ['Confidence', ...comparisonData.map(s => (s.confidence * 100).toFixed(0) + '%')],
      ['Fundamentals', ...comparisonData.map(s => s.agent_scores.fundamentals?.score?.toFixed(1) || 'N/A')],
      ['Momentum', ...comparisonData.map(s => s.agent_scores.momentum?.score?.toFixed(1) || 'N/A')],
      ['Quality', ...comparisonData.map(s => s.agent_scores.quality?.score?.toFixed(1) || 'N/A')],
      ['Sentiment', ...comparisonData.map(s => s.agent_scores.sentiment?.score?.toFixed(1) || 'N/A')],
      ['Institutional Flow', ...comparisonData.map(s => s.agent_scores.institutional_flow?.score?.toFixed(1) || 'N/A')],
      ['1M Return %', ...comparisonData.map(s => s.agent_scores.momentum?.metrics?.['1m_return']?.toFixed(1) || 'N/A')],
      ['3M Return %', ...comparisonData.map(s => s.agent_scores.momentum?.metrics?.['3m_return']?.toFixed(1) || 'N/A')],
      ['6M Return %', ...comparisonData.map(s => s.agent_scores.momentum?.metrics?.['6m_return']?.toFixed(1) || 'N/A')],
      ['1Y Return %', ...comparisonData.map(s => s.agent_scores.momentum?.metrics?.['1y_return']?.toFixed(1) || 'N/A')],
      ['RSI', ...comparisonData.map(s => s.agent_scores.momentum?.metrics?.rsi?.toFixed(1) || 'N/A')],
      ['Volatility %', ...comparisonData.map(s => s.agent_scores.quality?.metrics?.volatility?.toFixed(1) || 'N/A')],
      ['Sector', ...comparisonData.map(s => s.agent_scores.quality?.metrics?.sector || 'N/A')],
    ];

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `stock-comparison-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <BarChart3 className="h-8 w-8 text-blue-600" />
            Stock Comparison
          </h1>
          <p className="text-gray-600 mt-1">
            Compare 2-5 stocks side-by-side with detailed analysis
          </p>
        </div>

        {comparisonData.length > 0 && (
          <button
            onClick={handleExport}
            className="btn-secondary"
          >
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </button>
        )}
      </div>

      {/* Stock Selection */}
      <Card>
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Select Stocks to Compare ({comparisonStocks.length}/5)
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
                <SymbolInput
                  value={searchSymbol}
                  onChange={setSearchSymbol}
                  onSubmit={handleAddStock}
                  placeholder="Enter symbol..."
                  className="input text-sm"
                />
                <button
                  onClick={handleAddStock}
                  disabled={!searchSymbol}
                  className="btn-primary text-sm"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleCompare}
              disabled={comparisonStocks.length < 2 || loading}
              className="btn-primary disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loading size="sm" />
                  <span className="ml-2">Comparing...</span>
                </>
              ) : (
                'Compare Stocks'
              )}
            </button>
            {comparisonStocks.length > 0 && (
              <button
                onClick={clearComparison}
                className="btn-secondary"
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
      </Card>

      {/* Comparison Results */}
      {comparisonData.length > 0 && (
        <>
          {/* View Tabs */}
          <Card>
            <div className="border-b border-gray-200">
              <nav className="flex space-x-8 px-6">
                <button
                  onClick={() => setActiveView('summary')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeView === 'summary'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Summary & Analysis
                </button>
                <button
                  onClick={() => setActiveView('table')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeView === 'table'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Detailed Table
                </button>
                <button
                  onClick={() => setActiveView('charts')}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeView === 'charts'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Visual Charts
                </button>
              </nav>
            </div>
          </Card>

          {/* View Content */}
          {activeView === 'summary' && (
            <ComparisonSummary stocks={comparisonData} />
          )}

          {activeView === 'table' && (
            <Card>
              <ComparisonTable stocks={comparisonData} />
            </Card>
          )}

          {activeView === 'charts' && (
            <ComparisonCharts stocks={comparisonData} />
          )}
        </>
      )}

      {/* Empty State */}
      {comparisonStocks.length === 0 && (
        <Card>
          <div className="p-12 text-center">
            <TrendingUp className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No stocks selected
            </h3>
            <p className="text-gray-600 mb-6">
              Add 2-5 stocks above to start comparing them side-by-side
            </p>
            <div className="max-w-md mx-auto text-left bg-blue-50 rounded-lg p-4">
              <p className="text-sm font-medium text-blue-900 mb-2">💡 Quick Tip:</p>
              <p className="text-sm text-blue-800">
                Try comparing stocks from the same sector to identify the best pick, or compare your watchlist stocks to make informed decisions!
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
