/**
 * Stock Screener Hook
 *
 * Manages screener state, filtering logic, and data fetching
 */

import { useState, useCallback } from 'react';
import api from '@/lib/api';
import type { StockAnalysis } from '@/types';
import type { ScreenerFilters } from '@/pages/Screener';

export function useScreener(_initialFilters: ScreenerFilters = {}) {
  const [allStocks, setAllStocks] = useState<StockAnalysis[]>([]);
  const [filteredStocks, setFilteredStocks] = useState<StockAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch all stocks
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch a large batch of stocks for screening
      const response = await api.getTopPicks(100, false);
      const stocks = response.top_picks || [];

      setAllStocks(stocks);
      setFilteredStocks(stocks);
    } catch (err) {
      console.error('Failed to fetch stocks for screener:', err);
      setError(err instanceof Error ? err.message : 'Failed to load stocks');
    } finally {
      setLoading(false);
    }
  }, []);

  // Apply filters to stocks
  const applyFilters = useCallback((filters: ScreenerFilters) => {
    if (allStocks.length === 0) {
      setFilteredStocks([]);
      return;
    }

    let filtered = [...allStocks];

    // Score range filter
    if (filters.scoreMin !== undefined) {
      filtered = filtered.filter(s => s.composite_score >= filters.scoreMin!);
    }
    if (filters.scoreMax !== undefined) {
      filtered = filtered.filter(s => s.composite_score <= filters.scoreMax!);
    }

    // Recommendation filter
    if (filters.recommendations && filters.recommendations.length > 0) {
      filtered = filtered.filter(s => filters.recommendations!.includes(s.recommendation));
    }

    // Sector filter
    if (filters.sectors && filters.sectors.length > 0) {
      filtered = filtered.filter(s => {
        const sector = s.agent_scores.quality?.metrics?.sector;
        return sector && filters.sectors!.includes(sector);
      });
    }

    // Market cap filter
    if (filters.marketCapMin !== undefined) {
      filtered = filtered.filter(s => {
        const marketCap = s.agent_scores.quality?.metrics?.market_cap;
        return marketCap && marketCap >= filters.marketCapMin! * 1e9; // Convert crores to actual value
      });
    }
    if (filters.marketCapMax !== undefined) {
      filtered = filtered.filter(s => {
        const marketCap = s.agent_scores.quality?.metrics?.market_cap;
        return marketCap && marketCap <= filters.marketCapMax! * 1e9;
      });
    }

    // Returns filters
    if (filters.return1mMin !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['1m_return'];
        return ret !== undefined && ret >= filters.return1mMin!;
      });
    }
    if (filters.return1mMax !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['1m_return'];
        return ret !== undefined && ret <= filters.return1mMax!;
      });
    }
    if (filters.return3mMin !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['3m_return'];
        return ret !== undefined && ret >= filters.return3mMin!;
      });
    }
    if (filters.return3mMax !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['3m_return'];
        return ret !== undefined && ret <= filters.return3mMax!;
      });
    }
    if (filters.return6mMin !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['6m_return'];
        return ret !== undefined && ret >= filters.return6mMin!;
      });
    }
    if (filters.return6mMax !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['6m_return'];
        return ret !== undefined && ret <= filters.return6mMax!;
      });
    }
    if (filters.return1yMin !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['1y_return'];
        return ret !== undefined && ret >= filters.return1yMin!;
      });
    }
    if (filters.return1yMax !== undefined) {
      filtered = filtered.filter(s => {
        const ret = s.agent_scores.momentum?.metrics?.['1y_return'];
        return ret !== undefined && ret <= filters.return1yMax!;
      });
    }

    // RSI filter
    if (filters.rsiMin !== undefined) {
      filtered = filtered.filter(s => {
        const rsi = s.agent_scores.momentum?.metrics?.rsi;
        return rsi !== undefined && rsi >= filters.rsiMin!;
      });
    }
    if (filters.rsiMax !== undefined) {
      filtered = filtered.filter(s => {
        const rsi = s.agent_scores.momentum?.metrics?.rsi;
        return rsi !== undefined && rsi <= filters.rsiMax!;
      });
    }

    // Trend filter
    if (filters.trends && filters.trends.length > 0) {
      filtered = filtered.filter(s => {
        const trend = s.agent_scores.momentum?.metrics?.trend;
        return trend && filters.trends!.includes(trend);
      });
    }

    // Volatility filter
    if (filters.volatilityMin !== undefined) {
      filtered = filtered.filter(s => {
        const vol = s.agent_scores.quality?.metrics?.volatility;
        return vol !== undefined && vol >= filters.volatilityMin!;
      });
    }
    if (filters.volatilityMax !== undefined) {
      filtered = filtered.filter(s => {
        const vol = s.agent_scores.quality?.metrics?.volatility;
        return vol !== undefined && vol <= filters.volatilityMax!;
      });
    }

    // Agent score filters
    if (filters.fundamentalsMin !== undefined) {
      filtered = filtered.filter(s => (s.agent_scores.fundamentals?.score ?? 0) >= filters.fundamentalsMin!);
    }
    if (filters.momentumMin !== undefined) {
      filtered = filtered.filter(s => (s.agent_scores.momentum?.score ?? 0) >= filters.momentumMin!);
    }
    if (filters.qualityMin !== undefined) {
      filtered = filtered.filter(s => (s.agent_scores.quality?.score ?? 0) >= filters.qualityMin!);
    }
    if (filters.sentimentMin !== undefined) {
      filtered = filtered.filter(s => (s.agent_scores.sentiment?.score ?? 0) >= filters.sentimentMin!);
    }
    if (filters.institutionalFlowMin !== undefined) {
      filtered = filtered.filter(s => (s.agent_scores.institutional_flow?.score ?? 0) >= filters.institutionalFlowMin!);
    }

    // Analyst coverage filter
    if (filters.analystCountMin !== undefined) {
      filtered = filtered.filter(s => {
        const count = s.agent_scores.sentiment?.metrics?.number_of_analyst_opinions;
        return count !== undefined && count >= filters.analystCountMin!;
      });
    }

    setFilteredStocks(filtered);
  }, [allStocks]);

  return {
    stocks: filteredStocks,
    loading,
    error,
    filteredCount: filteredStocks.length,
    totalCount: allStocks.length,
    applyFilters,
    refresh,
  };
}
