/**
 * Tests for useWatchlist hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useWatchlist } from '../useWatchlist';
import api from '@/lib/api';

// Mock the API
vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}));

describe('useWatchlist', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch watchlist on mount', async () => {
    const mockWatchlist = {
      watchlist: [
        { symbol: 'TCS', added_at: '2026-01-01', latest_score: 80 },
        { symbol: 'INFY', added_at: '2026-01-02', latest_score: 75 }
      ],
      count: 2
    };

    vi.mocked(api.get).mockResolvedValueOnce({ data: mockWatchlist });

    const { result } = renderHook(() => useWatchlist());

    // Initially loading
    expect(result.current.loading).toBe(true);

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.watchlist).toHaveLength(2);
    expect(result.current.count).toBe(2);
    expect(result.current.watchlist[0].symbol).toBe('TCS');
  });

  it('should add stock to watchlist', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { watchlist: [], count: 0 } });
    vi.mocked(api.post).mockResolvedValueOnce({ data: { success: true } });
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        watchlist: [{ symbol: 'TCS', added_at: '2026-01-01' }],
        count: 1
      }
    });

    const { result } = renderHook(() => useWatchlist());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Add stock
    const success = await result.current.add('TCS', 'Test note');

    expect(success).toBe(true);
    expect(api.post).toHaveBeenCalledWith('/watchlist', {
      symbol: 'TCS',
      notes: 'Test note'
    });
  });

  it('should remove stock from watchlist', async () => {
    const mockWatchlist = {
      watchlist: [{ symbol: 'TCS', added_at: '2026-01-01' }],
      count: 1
    };

    vi.mocked(api.get).mockResolvedValueOnce({ data: mockWatchlist });
    vi.mocked(api.delete).mockResolvedValueOnce({ data: { success: true } });
    vi.mocked(api.get).mockResolvedValueOnce({ data: { watchlist: [], count: 0 } });

    const { result } = renderHook(() => useWatchlist());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Remove stock
    const success = await result.current.remove('TCS');

    expect(success).toBe(true);
    expect(api.delete).toHaveBeenCalledWith('/watchlist/TCS');
  });

  it('should check if stock is in watchlist', async () => {
    const mockWatchlist = {
      watchlist: [{ symbol: 'TCS', added_at: '2026-01-01' }],
      count: 1
    };

    vi.mocked(api.get).mockResolvedValueOnce({ data: mockWatchlist });

    const { result } = renderHook(() => useWatchlist());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.isInWatchlist('TCS')).toBe(true);
    expect(result.current.isInWatchlist('INFY')).toBe(false);
  });

  it('should handle errors gracefully', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useWatchlist());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.watchlist).toHaveLength(0);
  });
});
