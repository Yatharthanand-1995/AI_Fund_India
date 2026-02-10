/**
 * useSectorAnalysis Hook
 *
 * Custom hook for sector analysis data
 *
 * Features:
 * - Sector performance data
 * - Caching
 * - Sector filtering
 * - Auto-refresh capability
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../lib/api';

// ============================================================================
// Types
// ============================================================================

export interface SectorStat {
  sector: string;
  stock_count: number;
  avg_score: number;
  top_pick: string;
  trend: string;
}

export interface SectorAnalysisData {
  sectors: SectorStat[];
  total_sectors: number;
  timestamp: string;
}

export interface UseSectorAnalysisOptions {
  days?: number;
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
  enabled?: boolean;
}

export interface UseSectorAnalysisReturn {
  sectors: SectorStat[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  getSectorByName: (name: string) => SectorStat | undefined;
  getTopSectors: (n: number) => SectorStat[];
  totalSectors: number;
  lastUpdated: Date | null;
}

// ============================================================================
// Hook
// ============================================================================

export const useSectorAnalysis = (
  options: UseSectorAnalysisOptions = {}
): UseSectorAnalysisReturn => {
  const {
    days = 7,
    autoRefresh = false,
    refreshInterval = 300000, // 5 minutes
    enabled = true
  } = options;

  const [data, setData] = useState<SectorAnalysisData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch function
  const fetchSectorAnalysis = useCallback(async () => {
    if (!enabled) return;

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/analytics/sectors', {
        params: { days },
        signal: abortControllerRef.current.signal
      });

      setData(response.data);
      setLastUpdated(new Date());
    } catch (err: any) {
      if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
        console.error('Failed to fetch sector analysis:', err);
        setError(err);
      }
    } finally {
      setLoading(false);
    }
  }, [days, enabled]);

  // Initial fetch
  useEffect(() => {
    fetchSectorAnalysis();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchSectorAnalysis]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !enabled) return;

    refreshTimerRef.current = setInterval(() => {
      fetchSectorAnalysis();
    }, refreshInterval);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [autoRefresh, enabled, refreshInterval, fetchSectorAnalysis]);

  // Helper: Get sector by name
  const getSectorByName = useCallback((name: string): SectorStat | undefined => {
    if (!data) return undefined;
    return data.sectors.find(s => s.sector.toLowerCase() === name.toLowerCase());
  }, [data]);

  // Helper: Get top N sectors
  const getTopSectors = useCallback((n: number): SectorStat[] => {
    if (!data) return [];
    return data.sectors.slice(0, n);
  }, [data]);

  // Memoized sectors
  const sectors = useMemo(() => {
    return data?.sectors || [];
  }, [data]);

  return {
    sectors,
    loading,
    error,
    refetch: fetchSectorAnalysis,
    getSectorByName,
    getTopSectors,
    totalSectors: data?.total_sectors || 0,
    lastUpdated
  };
};

export default useSectorAnalysis;
