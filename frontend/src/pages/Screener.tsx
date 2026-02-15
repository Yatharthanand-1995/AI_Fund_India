/**
 * Stock Screener Page
 *
 * Multi-dimensional filtering and stock discovery tool
 * Features:
 * - Score-based filters
 * - Recommendation filters
 * - Sector and market cap filters
 * - Technical indicator filters (RSI, trend, returns)
 * - Agent-specific filters
 * - Saved filter presets
 * - Export capabilities
 */

import { useState, useEffect } from 'react';
import { Filter, Save, Download, RefreshCw, LayoutGrid, Table } from 'lucide-react';
import Card from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';
import ScreenerFilters from '@/components/screener/ScreenerFilters';
import ScreenerResults from '@/components/screener/ScreenerResults';
import ScreenerPresets from '@/components/screener/ScreenerPresets';
import { useScreener } from '@/hooks/useScreener';
import { useUrlFilters } from '@/hooks/useUrlFilters';
import type { StockAnalysis } from '@/types';

export type ViewMode = 'cards' | 'table';

export interface ScreenerFilters {
  // Score filters
  scoreMin?: number;
  scoreMax?: number;

  // Recommendation
  recommendations?: string[];

  // Sector
  sectors?: string[];

  // Market cap (in crores)
  marketCapMin?: number;
  marketCapMax?: number;

  // Returns
  return1mMin?: number;
  return1mMax?: number;
  return3mMin?: number;
  return3mMax?: number;
  return6mMin?: number;
  return6mMax?: number;
  return1yMin?: number;
  return1yMax?: number;

  // Technical indicators
  rsiMin?: number;
  rsiMax?: number;
  trends?: string[];

  // Volatility
  volatilityMin?: number;
  volatilityMax?: number;

  // Agent scores
  fundamentalsMin?: number;
  momentumMin?: number;
  qualityMin?: number;
  sentimentMin?: number;
  institutionalFlowMin?: number;

  // Analyst coverage
  analystCountMin?: number;
}

// Keys for URL param parsing (must match ScreenerFilters interface)
const ARRAY_KEYS = ['recommendations', 'sectors', 'trends'];
const NUMBER_KEYS = [
  'scoreMin', 'scoreMax', 'marketCapMin', 'marketCapMax',
  'return1mMin', 'return1mMax', 'return3mMin', 'return3mMax',
  'return6mMin', 'return6mMax', 'return1yMin', 'return1yMax',
  'rsiMin', 'rsiMax', 'volatilityMin', 'volatilityMax',
  'fundamentalsMin', 'momentumMin', 'qualityMin', 'sentimentMin',
  'institutionalFlowMin', 'analystCountMin',
];

export default function Screener() {
  const [urlFilters, setUrlFilters] = useUrlFilters<ScreenerFilters>({
    arrayKeys: ARRAY_KEYS,
    numberKeys: NUMBER_KEYS,
  });

  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [filters, setFilters] = useState<ScreenerFilters>(urlFilters);
  const [showFilters, setShowFilters] = useState(true);
  const [showPresets, setShowPresets] = useState(false);

  const { stocks, loading, error, filteredCount, totalCount, applyFilters, refresh } = useScreener(filters);

  useEffect(() => {
    refresh();
  }, []);

  const handleApplyFilters = (newFilters: ScreenerFilters) => {
    setFilters(newFilters);
    setUrlFilters(newFilters);
    applyFilters(newFilters);
  };

  const handleLoadPreset = (preset: any) => {
    setFilters(preset.filters);
    applyFilters(preset.filters);
    setShowPresets(false);
  };

  const handleExport = (format: 'csv' | 'json') => {
    const dataStr = format === 'json'
      ? JSON.stringify(stocks, null, 2)
      : convertToCSV(stocks);

    const blob = new Blob([dataStr], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `screener-results-${new Date().toISOString().split('T')[0]}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const convertToCSV = (data: StockAnalysis[]): string => {
    const headers = ['Symbol', 'Score', 'Recommendation', 'Sector', 'Market Cap', '1M Return', '3M Return', '6M Return', 'RSI', 'Trend'];
    const rows = data.map(stock => [
      stock.symbol,
      stock.composite_score,
      stock.recommendation,
      stock.agent_scores.quality?.metrics?.sector || 'N/A',
      stock.agent_scores.quality?.metrics?.market_cap || 'N/A',
      stock.agent_scores.momentum?.metrics?.['1m_return']?.toFixed(2) || 'N/A',
      stock.agent_scores.momentum?.metrics?.['3m_return']?.toFixed(2) || 'N/A',
      stock.agent_scores.momentum?.metrics?.['6m_return']?.toFixed(2) || 'N/A',
      stock.agent_scores.momentum?.metrics?.rsi?.toFixed(1) || 'N/A',
      stock.agent_scores.momentum?.metrics?.trend || 'N/A',
    ]);

    return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Filter className="h-8 w-8 text-blue-600" />
            Stock Screener
          </h1>
          <p className="mt-2 text-gray-600">
            Discover stocks using advanced multi-dimensional filters
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'table'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Table className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('cards')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'cards'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>

          {/* Action Buttons */}
          <button
            onClick={() => setShowPresets(!showPresets)}
            className="btn-secondary"
          >
            <Save className="h-4 w-4 mr-2" />
            Presets
          </button>

          <button
            onClick={() => handleExport('csv')}
            className="btn-secondary"
            disabled={stocks.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </button>

          <button
            onClick={refresh}
            className="btn-primary"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Results Summary */}
      <Card>
        <div className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">
              Showing <span className="font-bold text-gray-900">{filteredCount}</span> of{' '}
              <span className="font-bold text-gray-900">{totalCount}</span> stocks
            </p>
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            {showFilters ? 'Hide' : 'Show'} Filters
          </button>
        </div>
      </Card>

      {/* Presets Panel */}
      {showPresets && (
        <ScreenerPresets
          currentFilters={filters}
          onLoadPreset={handleLoadPreset}
          onClose={() => setShowPresets(false)}
        />
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        {showFilters && (
          <div className="lg:col-span-1">
            <ScreenerFilters
              filters={filters}
              onApplyFilters={handleApplyFilters}
            />
          </div>
        )}

        {/* Results */}
        <div className={showFilters ? 'lg:col-span-3' : 'lg:col-span-4'}>
          {loading ? (
            <Card>
              <div className="p-12">
                <Loading size="lg" text="Loading stocks..." />
              </div>
            </Card>
          ) : error ? (
            <Card>
              <div className="p-6 text-center text-red-600">
                <p className="font-medium">Failed to load stocks</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </Card>
          ) : (
            <ScreenerResults
              stocks={stocks}
              viewMode={viewMode}
            />
          )}
        </div>
      </div>
    </div>
  );
}
