/**
 * Screener Filters Component
 *
 * Collapsible filter sections for screening stocks
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, RotateCcw } from 'lucide-react';
import Card from '@/components/ui/Card';
import type { ScreenerFilters as Filters } from '@/pages/Screener';

interface ScreenerFiltersProps {
  filters: Filters;
  onApplyFilters: (filters: Filters) => void;
}

export default function ScreenerFilters({ filters, onApplyFilters }: ScreenerFiltersProps) {
  const [localFilters, setLocalFilters] = useState<Filters>(filters);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['score', 'recommendation', 'agents'])
  );

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const handleReset = () => {
    const emptyFilters: Filters = {};
    setLocalFilters(emptyFilters);
    onApplyFilters(emptyFilters);
  };

  const handleApply = () => {
    onApplyFilters(localFilters);
  };

  const updateFilter = (key: keyof Filters, value: any) => {
    setLocalFilters({ ...localFilters, [key]: value });
  };

  const toggleArrayFilter = (key: keyof Filters, value: string) => {
    const current = (localFilters[key] as string[]) || [];
    const updated = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value];
    updateFilter(key, updated.length > 0 ? updated : undefined);
  };

  const RECOMMENDATIONS = ['STRONG BUY', 'BUY', 'HOLD', 'SELL', 'STRONG SELL'];
  const SECTORS = [
    'Technology',
    'Financial Services',
    'Healthcare',
    'Consumer Discretionary',
    'Consumer Staples',
    'Industrials',
    'Basic Materials',
    'Energy',
    'Utilities',
    'Real Estate',
    'Communication Services',
  ];
  const TRENDS = ['strong_uptrend', 'uptrend', 'sideways', 'downtrend', 'strong_downtrend'];

  return (
    <div className="space-y-4">
      <Card>
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
            <button
              onClick={handleReset}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              <RotateCcw className="h-3 w-3" />
              Reset
            </button>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {/* Score Filter */}
          <FilterSection
            title="Composite Score"
            isExpanded={expandedSections.has('score')}
            onToggle={() => toggleSection('score')}
          >
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Minimum Score
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localFilters.scoreMin || ''}
                  onChange={(e) => updateFilter('scoreMin', e.target.value ? Number(e.target.value) : undefined)}
                  className="input text-sm w-full"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Maximum Score
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localFilters.scoreMax || ''}
                  onChange={(e) => updateFilter('scoreMax', e.target.value ? Number(e.target.value) : undefined)}
                  className="input text-sm w-full"
                  placeholder="100"
                />
              </div>
            </div>
          </FilterSection>

          {/* Recommendation Filter */}
          <FilterSection
            title="Recommendation"
            isExpanded={expandedSections.has('recommendation')}
            onToggle={() => toggleSection('recommendation')}
          >
            <div className="space-y-2">
              {RECOMMENDATIONS.map((rec) => (
                <label key={rec} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={localFilters.recommendations?.includes(rec) || false}
                    onChange={() => toggleArrayFilter('recommendations', rec)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{rec}</span>
                </label>
              ))}
            </div>
          </FilterSection>

          {/* Agent Scores Filter */}
          <FilterSection
            title="Agent Scores"
            isExpanded={expandedSections.has('agents')}
            onToggle={() => toggleSection('agents')}
          >
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Fundamentals ≥
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localFilters.fundamentalsMin || ''}
                  onChange={(e) => updateFilter('fundamentalsMin', e.target.value ? Number(e.target.value) : undefined)}
                  className="input text-sm w-full"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Momentum ≥
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localFilters.momentumMin || ''}
                  onChange={(e) => updateFilter('momentumMin', e.target.value ? Number(e.target.value) : undefined)}
                  className="input text-sm w-full"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Quality ≥
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localFilters.qualityMin || ''}
                  onChange={(e) => updateFilter('qualityMin', e.target.value ? Number(e.target.value) : undefined)}
                  className="input text-sm w-full"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Sentiment ≥
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localFilters.sentimentMin || ''}
                  onChange={(e) => updateFilter('sentimentMin', e.target.value ? Number(e.target.value) : undefined)}
                  className="input text-sm w-full"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Institutional Flow ≥
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localFilters.institutionalFlowMin || ''}
                  onChange={(e) => updateFilter('institutionalFlowMin', e.target.value ? Number(e.target.value) : undefined)}
                  className="input text-sm w-full"
                  placeholder="0"
                />
              </div>
            </div>
          </FilterSection>

          {/* Sector Filter */}
          <FilterSection
            title="Sector"
            isExpanded={expandedSections.has('sector')}
            onToggle={() => toggleSection('sector')}
          >
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {SECTORS.map((sector) => (
                <label key={sector} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={localFilters.sectors?.includes(sector) || false}
                    onChange={() => toggleArrayFilter('sectors', sector)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{sector}</span>
                </label>
              ))}
            </div>
          </FilterSection>

          {/* Returns Filter */}
          <FilterSection
            title="Returns"
            isExpanded={expandedSections.has('returns')}
            onToggle={() => toggleSection('returns')}
          >
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    1M Min %
                  </label>
                  <input
                    type="number"
                    value={localFilters.return1mMin || ''}
                    onChange={(e) => updateFilter('return1mMin', e.target.value ? Number(e.target.value) : undefined)}
                    className="input text-sm w-full"
                    placeholder="-50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    1M Max %
                  </label>
                  <input
                    type="number"
                    value={localFilters.return1mMax || ''}
                    onChange={(e) => updateFilter('return1mMax', e.target.value ? Number(e.target.value) : undefined)}
                    className="input text-sm w-full"
                    placeholder="100"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    3M Min %
                  </label>
                  <input
                    type="number"
                    value={localFilters.return3mMin || ''}
                    onChange={(e) => updateFilter('return3mMin', e.target.value ? Number(e.target.value) : undefined)}
                    className="input text-sm w-full"
                    placeholder="-50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    3M Max %
                  </label>
                  <input
                    type="number"
                    value={localFilters.return3mMax || ''}
                    onChange={(e) => updateFilter('return3mMax', e.target.value ? Number(e.target.value) : undefined)}
                    className="input text-sm w-full"
                    placeholder="100"
                  />
                </div>
              </div>
            </div>
          </FilterSection>

          {/* Technical Indicators */}
          <FilterSection
            title="Technical Indicators"
            isExpanded={expandedSections.has('technical')}
            onToggle={() => toggleSection('technical')}
          >
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    RSI Min
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={localFilters.rsiMin || ''}
                    onChange={(e) => updateFilter('rsiMin', e.target.value ? Number(e.target.value) : undefined)}
                    className="input text-sm w-full"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    RSI Max
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={localFilters.rsiMax || ''}
                    onChange={(e) => updateFilter('rsiMax', e.target.value ? Number(e.target.value) : undefined)}
                    className="input text-sm w-full"
                    placeholder="100"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-2">
                  Trend
                </label>
                <div className="space-y-2">
                  {TRENDS.map((trend) => (
                    <label key={trend} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={localFilters.trends?.includes(trend) || false}
                        onChange={() => toggleArrayFilter('trends', trend)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-700 capitalize">
                        {trend.replace('_', ' ')}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </FilterSection>
        </div>

        <div className="p-4 border-t border-gray-200">
          <button
            onClick={handleApply}
            className="btn-primary w-full"
          >
            Apply Filters
          </button>
        </div>
      </Card>
    </div>
  );
}

interface FilterSectionProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function FilterSection({ title, isExpanded, onToggle, children }: FilterSectionProps) {
  return (
    <div className="p-4">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-left"
      >
        <span className="font-medium text-gray-900 text-sm">{title}</span>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-gray-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-500" />
        )}
      </button>
      {isExpanded && (
        <div className="mt-3">
          {children}
        </div>
      )}
    </div>
  );
}
