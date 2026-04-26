/**
 * Stock Screener Hook
 *
 * Fetches from the backend /screener endpoint for server-side filtering,
 * then applies any remaining client-side filters for fields the backend
 * doesn't support (market cap, return ranges, volatility, analyst count,
 * multi-value sector/recommendation/trend arrays).
 */

import { useState, useCallback, useEffect } from 'react';
import api from '@/lib/api';
import type { StockAnalysis } from '@/types';
import type { ScreenerFilters } from '@/pages/Screener';

export function useScreener(_initialFilters: ScreenerFilters = {}) {
  const [allStocks, setAllStocks] = useState<StockAnalysis[]>([]);
  const [filteredStocks, setFilteredStocks] = useState<StockAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch from backend /screener with server-side filters applied
  const refresh = useCallback(async (filters: ScreenerFilters = {}) => {
    setLoading(true);
    setError(null);

    try {
      // Map ScreenerFilters → backend query params.
      // Backend accepts single-value strings for sector/recommendation/trend,
      // so only pass them when there's exactly one value selected.
      const params: Record<string, string | number> = { limit: 200 };

      if (filters.scoreMin !== undefined) params.score_min = filters.scoreMin;
      if (filters.scoreMax !== undefined) params.score_max = filters.scoreMax;
      if (filters.sectors?.length === 1) params.sector = filters.sectors[0];
      if (filters.recommendations?.length === 1) params.recommendation = filters.recommendations[0];
      if (filters.rsiMin !== undefined) params.rsi_min = filters.rsiMin;
      if (filters.rsiMax !== undefined) params.rsi_max = filters.rsiMax;
      if (filters.trends?.length === 1) params.trend = filters.trends[0];
      if (filters.fundamentalsMin !== undefined) params.fundamentals_min = filters.fundamentalsMin;
      if (filters.momentumMin !== undefined) params.momentum_min = filters.momentumMin;
      if (filters.qualityMin !== undefined) params.quality_min = filters.qualityMin;
      if (filters.sentimentMin !== undefined) params.sentiment_min = filters.sentimentMin;
      if (filters.institutionalFlowMin !== undefined) params.institutional_min = filters.institutionalFlowMin;

      const response = await api.get('/screener', { params });
      const stocks: StockAnalysis[] = (response as any).results || [];

      setAllStocks(stocks);

      // Apply client-side filters for fields not handled server-side
      setFilteredStocks(applyClientFilters(stocks, filters));
    } catch (err) {
      console.error('Failed to fetch stocks for screener:', err);
      setError(err instanceof Error ? err.message : 'Failed to load stocks');
    } finally {
      setLoading(false);
    }
  }, []);

  // Apply initial filters once on mount
  useEffect(() => {
    if (Object.keys(_initialFilters).length > 0) {
      refresh(_initialFilters);
    } else {
      refresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once on mount

  // Re-filter client-side when filters change (without re-fetching)
  const applyFilters = useCallback((filters: ScreenerFilters) => {
    // Re-fetch with new server-side params — this also re-applies client filters
    refresh(filters);
  }, [refresh]);

  return {
    stocks: filteredStocks,
    loading,
    error,
    filteredCount: filteredStocks.length,
    totalCount: allStocks.length,
    applyFilters,
    refresh: () => refresh(),
  };
}

function applyClientFilters(stocks: StockAnalysis[], filters: ScreenerFilters): StockAnalysis[] {
  let result = stocks;

  // Multi-value arrays (when >1 value selected, backend skipped these)
  if (filters.sectors && filters.sectors.length > 1) {
    result = result.filter(s => {
      const sector = s.sector ||
                     s.agent_scores.fundamentals?.metrics?.sector ||
                     s.agent_scores.quality?.metrics?.sector;
      return sector && filters.sectors!.includes(sector);
    });
  }
  if (filters.recommendations && filters.recommendations.length > 1) {
    result = result.filter(s => filters.recommendations!.includes(s.recommendation));
  }
  if (filters.trends && filters.trends.length > 1) {
    result = result.filter(s => {
      const trend = s.agent_scores.momentum?.metrics?.trend;
      return trend && filters.trends!.includes(trend);
    });
  }

  // Market cap (in crores → rupees)
  if (filters.marketCapMin !== undefined) {
    result = result.filter(s => {
      const mc = s.agent_scores.quality?.metrics?.market_cap;
      return mc && mc >= filters.marketCapMin! * 1e7;
    });
  }
  if (filters.marketCapMax !== undefined) {
    result = result.filter(s => {
      const mc = s.agent_scores.quality?.metrics?.market_cap;
      return mc && mc <= filters.marketCapMax! * 1e7;
    });
  }

  // Return filters
  const returnFilters: Array<[keyof ScreenerFilters, string, 'min' | 'max']> = [
    ['return1mMin', '1m_return', 'min'], ['return1mMax', '1m_return', 'max'],
    ['return3mMin', '3m_return', 'min'], ['return3mMax', '3m_return', 'max'],
    ['return6mMin', '6m_return', 'min'], ['return6mMax', '6m_return', 'max'],
    ['return1yMin', '1y_return', 'min'], ['return1yMax', '1y_return', 'max'],
  ];
  for (const [filterKey, metricKey, dir] of returnFilters) {
    const val = filters[filterKey] as number | undefined;
    if (val !== undefined) {
      result = result.filter(s => {
        const ret = (s.agent_scores.momentum?.metrics as any)?.[metricKey];
        return ret !== undefined && (dir === 'min' ? ret >= val : ret <= val);
      });
    }
  }

  // Volatility
  if (filters.volatilityMin !== undefined) {
    result = result.filter(s => {
      const vol = s.agent_scores.quality?.metrics?.volatility;
      return vol !== undefined && vol >= filters.volatilityMin!;
    });
  }
  if (filters.volatilityMax !== undefined) {
    result = result.filter(s => {
      const vol = s.agent_scores.quality?.metrics?.volatility;
      return vol !== undefined && vol <= filters.volatilityMax!;
    });
  }

  // Analyst coverage
  if (filters.analystCountMin !== undefined) {
    result = result.filter(s => {
      const count = s.agent_scores.sentiment?.metrics?.number_of_analyst_opinions;
      return count !== undefined && count >= filters.analystCountMin!;
    });
  }

  return result;
}
