/**
 * useWatchlist Hook
 *
 * Custom hook for watchlist operations
 *
 * Features:
 * - Add/remove stocks
 * - Optimistic updates
 * - Sync with backend
 * - Check if stock is in watchlist
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

// ============================================================================
// Types
// ============================================================================

export interface WatchlistItem {
  symbol: string;
  added_at: string;
  notes?: string;
  latest_score?: number;
  latest_recommendation?: string;
}

export interface UseWatchlistReturn {
  watchlist: WatchlistItem[];
  loading: boolean;
  error: Error | null;
  add: (symbol: string, notes?: string) => Promise<boolean>;
  remove: (symbol: string) => Promise<boolean>;
  refresh: () => Promise<void>;
  isInWatchlist: (symbol: string) => boolean;
  count: number;
}

// ============================================================================
// Hook
// ============================================================================

export const useWatchlist = (): UseWatchlistReturn => {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  // Fetch watchlist
  const fetchWatchlist = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/watchlist');
      setWatchlist(response.data.watchlist || []);
    } catch (err: any) {
      console.error('Failed to fetch watchlist:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  // Add to watchlist
  const add = useCallback(async (symbol: string, notes?: string): Promise<boolean> => {
    try {
      // Optimistic update
      const newItem: WatchlistItem = {
        symbol: symbol.toUpperCase(),
        added_at: new Date().toISOString(),
        notes
      };
      setWatchlist(prev => [newItem, ...prev]);

      // API call
      const response = await api.post('/watchlist', { symbol, notes });

      // Refresh to get latest data
      await fetchWatchlist();

      return response.data.success;
    } catch (err: any) {
      console.error('Failed to add to watchlist:', err);

      // Revert optimistic update on error
      setWatchlist(prev => prev.filter(item => item.symbol !== symbol.toUpperCase()));
      setError(err);

      return false;
    }
  }, [fetchWatchlist]);

  // Remove from watchlist
  const remove = useCallback(async (symbol: string): Promise<boolean> => {
    const symbolUpper = symbol.toUpperCase();

    try {
      // Optimistic update
      const previousWatchlist = watchlist;
      setWatchlist(prev => prev.filter(item => item.symbol !== symbolUpper));

      // API call
      await api.delete(`/watchlist/${symbolUpper}`);

      return true;
    } catch (err: any) {
      console.error('Failed to remove from watchlist:', err);

      // Revert optimistic update on error
      setWatchlist(watchlist);
      setError(err);

      return false;
    }
  }, [watchlist]);

  // Check if symbol is in watchlist
  const isInWatchlist = useCallback((symbol: string): boolean => {
    return watchlist.some(item => item.symbol === symbol.toUpperCase());
  }, [watchlist]);

  return {
    watchlist,
    loading,
    error,
    add,
    remove,
    refresh: fetchWatchlist,
    isInWatchlist,
    count: watchlist.length
  };
};

export default useWatchlist;
