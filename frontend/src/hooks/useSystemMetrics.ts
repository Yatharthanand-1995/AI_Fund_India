/**
 * useSystemMetrics Hook
 *
 * Custom hook for system analytics and metrics
 *
 * Features:
 * - Auto-refresh every 30s
 * - Formatted performance data
 * - Error tracking
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';

// ============================================================================
// Types
// ============================================================================

export interface SystemMetrics {
  uptime_seconds: number;
  total_requests: number;
  total_errors: number;
  error_rate: number;
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  cache_hit_rate: number;
  agent_performance: Record<string, number>;
  timestamp: string;
}

export interface FormattedMetrics extends SystemMetrics {
  uptime_formatted: string;
  error_rate_formatted: string;
  cache_hit_rate_formatted: string;
}

export interface UseSystemMetricsOptions {
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
  enabled?: boolean;
}

export interface UseSystemMetricsReturn {
  metrics: FormattedMetrics | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  lastUpdated: Date | null;
}

// ============================================================================
// Utilities
// ============================================================================

const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`;
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else {
    return `${minutes}m`;
  }
};

const formatMetrics = (metrics: SystemMetrics): FormattedMetrics => {
  return {
    ...metrics,
    uptime_formatted: formatUptime(metrics.uptime_seconds),
    error_rate_formatted: `${metrics.error_rate.toFixed(2)}%`,
    cache_hit_rate_formatted: `${metrics.cache_hit_rate.toFixed(1)}%`
  };
};

// ============================================================================
// Hook
// ============================================================================

export const useSystemMetrics = (
  options: UseSystemMetricsOptions = {}
): UseSystemMetricsReturn => {
  const {
    autoRefresh = true,
    refreshInterval = 30000, // 30 seconds
    enabled = true
  } = options;

  const [metrics, setMetrics] = useState<FormattedMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch function
  const fetchMetrics = useCallback(async () => {
    if (!enabled) return;

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/analytics/system', {
        signal: abortControllerRef.current.signal
      });

      const formattedData = formatMetrics(response.data);
      setMetrics(formattedData);
      setLastUpdated(new Date());
    } catch (err: any) {
      if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
        console.error('Failed to fetch system metrics:', err);
        setError(err);
      }
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  // Initial fetch
  useEffect(() => {
    fetchMetrics();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchMetrics]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !enabled) return;

    refreshTimerRef.current = setInterval(() => {
      fetchMetrics();
    }, refreshInterval);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [autoRefresh, enabled, refreshInterval, fetchMetrics]);

  return {
    metrics,
    loading,
    error,
    refetch: fetchMetrics,
    lastUpdated
  };
};

export default useSystemMetrics;
