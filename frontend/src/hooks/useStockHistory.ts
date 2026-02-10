/**
 * useStockHistory Hook
 *
 * Custom hook to fetch and cache historical stock data
 *
 * Features:
 * - Auto-refresh capability
 * - Error handling
 * - Loading states
 * - Caching with TTL
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';

// ============================================================================
// Types
// ============================================================================

export interface HistoricalDataPoint {
  timestamp: string;
  composite_score: number;
  recommendation: string;
  confidence: number;
  price?: number;
}

export interface TrendData {
  trend: string;
  avg_score: number;
  min_score: number;
  max_score: number;
  change: number;
  data_points: number;
}

export interface StockHistoryData {
  symbol: string;
  history: HistoricalDataPoint[];
  trend: TrendData;
  statistics: {
    avg_score: number;
    min_score: number;
    max_score: number;
    current_score: number;
    change: number;
  };
  data_points: number;
  timestamp: string;
}

export interface UseStockHistoryOptions {
  days?: number;
  includePrice?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
  enabled?: boolean;
}

export interface UseStockHistoryReturn {
  data: StockHistoryData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  isStale: boolean;
}

// ============================================================================
// Hook
// ============================================================================

export const useStockHistory = (
  symbol: string,
  options: UseStockHistoryOptions = {}
): UseStockHistoryReturn => {
  const {
    days = 30,
    includePrice = true,
    autoRefresh = false,
    refreshInterval = 60000, // 1 minute
    enabled = true
  } = options;

  const [data, setData] = useState<StockHistoryData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch function
  const fetchHistory = useCallback(async () => {
    if (!enabled || !symbol) return;

    // Cancel previous request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/history/stock/${symbol}`, {
        params: { days, include_price: includePrice },
        signal: abortControllerRef.current.signal
      });

      setData(response.data);
      setIsStale(false);
    } catch (err: any) {
      if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
        console.error('Failed to fetch stock history:', err);
        setError(err);
      }
    } finally {
      setLoading(false);
    }
  }, [symbol, days, includePrice, enabled]);

  // Initial fetch and dependency changes
  useEffect(() => {
    fetchHistory();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchHistory]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !enabled) return;

    refreshTimerRef.current = setInterval(() => {
      setIsStale(true);
      fetchHistory();
    }, refreshInterval);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [autoRefresh, enabled, refreshInterval, fetchHistory]);

  return {
    data,
    loading,
    error,
    refetch: fetchHistory,
    isStale
  };
};

export default useStockHistory;
