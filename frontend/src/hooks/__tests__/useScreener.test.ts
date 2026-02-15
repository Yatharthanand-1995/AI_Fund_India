/**
 * Tests for useScreener hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useScreener } from '../useScreener';
import api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  default: {
    getTopPicks: vi.fn(),
  }
}));

// Helper: build a minimal StockAnalysis-shaped mock
function makeStock(symbol: string, score: number, rec: string) {
  return {
    symbol,
    composite_score: score,
    recommendation: rec,
    confidence: 0.8,
    agent_scores: {
      fundamentals: {
        score: score - 2,
        metrics: { sector: 'IT', pe_ratio: 20, roe: 15 },
      },
      momentum: {
        score: score + 2,
        metrics: {
          rsi: 60,
          trend: 'UPTREND',
          '1m_return': 3.5,
          '3m_return': 8.0,
          '6m_return': 12.0,
          '1y_return': 25.0,
        },
      },
      quality: {
        score: score - 5,
        metrics: { volatility: 0.15, market_cap: 1e12 },
      },
      sentiment: {
        score: score - 3,
        metrics: { number_of_analyst_opinions: 20 },
      },
      institutional_flow: { score: score + 1, metrics: {} },
    },
    timestamp: '2026-01-01T00:00:00Z',
    cached: false,
  };
}

describe('useScreener', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts with empty state', () => {
    const { result } = renderHook(() => useScreener());
    expect(result.current.stocks).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.totalCount).toBe(0);
    expect(result.current.filteredCount).toBe(0);
  });

  it('loads stocks when refresh() is called', async () => {
    vi.mocked(api.getTopPicks).mockResolvedValueOnce({
      top_picks: [makeStock('TCS', 80, 'BUY'), makeStock('INFY', 60, 'HOLD')],
    } as any);

    const { result } = renderHook(() => useScreener());

    await act(async () => { await result.current.refresh(); });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.totalCount).toBe(2);
      expect(result.current.filteredCount).toBe(2);
    });
  });

  it('applies scoreMin filter correctly', async () => {
    vi.mocked(api.getTopPicks).mockResolvedValueOnce({
      top_picks: [
        makeStock('TCS', 80, 'BUY'),
        makeStock('INFY', 60, 'HOLD'),
        makeStock('WIPRO', 40, 'SELL'),
      ],
    } as any);

    const { result } = renderHook(() => useScreener());
    await act(async () => { await result.current.refresh(); });
    await waitFor(() => expect(result.current.totalCount).toBe(3));

    act(() => result.current.applyFilters({ scoreMin: 65 }));

    expect(result.current.filteredCount).toBe(1);
    expect(result.current.stocks[0].symbol).toBe('TCS');
  });

  it('applies scoreMax filter correctly', async () => {
    vi.mocked(api.getTopPicks).mockResolvedValueOnce({
      top_picks: [
        makeStock('TCS', 80, 'BUY'),
        makeStock('INFY', 60, 'HOLD'),
      ],
    } as any);

    const { result } = renderHook(() => useScreener());
    await act(async () => { await result.current.refresh(); });
    await waitFor(() => expect(result.current.totalCount).toBe(2));

    act(() => result.current.applyFilters({ scoreMax: 70 }));

    expect(result.current.filteredCount).toBe(1);
    expect(result.current.stocks[0].symbol).toBe('INFY');
  });

  it('applies recommendation filter', async () => {
    vi.mocked(api.getTopPicks).mockResolvedValueOnce({
      top_picks: [makeStock('TCS', 80, 'BUY'), makeStock('INFY', 60, 'HOLD')],
    } as any);

    const { result } = renderHook(() => useScreener());
    await act(async () => { await result.current.refresh(); });
    await waitFor(() => expect(result.current.totalCount).toBe(2));

    act(() => result.current.applyFilters({ recommendations: ['BUY'] }));

    expect(result.current.filteredCount).toBe(1);
    expect(result.current.stocks[0].recommendation).toBe('BUY');
  });

  it('applies agent score filter (fundamentalsMin)', async () => {
    vi.mocked(api.getTopPicks).mockResolvedValueOnce({
      top_picks: [makeStock('TCS', 80, 'BUY'), makeStock('INFY', 60, 'HOLD')],
    } as any);

    const { result } = renderHook(() => useScreener());
    await act(async () => { await result.current.refresh(); });
    await waitFor(() => expect(result.current.totalCount).toBe(2));

    // TCS fundamentals score = 78, INFY = 58
    act(() => result.current.applyFilters({ fundamentalsMin: 70 }));

    expect(result.current.filteredCount).toBe(1);
    expect(result.current.stocks[0].symbol).toBe('TCS');
  });

  it('returns all stocks when no filters applied', async () => {
    vi.mocked(api.getTopPicks).mockResolvedValueOnce({
      top_picks: [makeStock('TCS', 80, 'BUY'), makeStock('INFY', 60, 'HOLD')],
    } as any);

    const { result } = renderHook(() => useScreener());
    await act(async () => { await result.current.refresh(); });
    await waitFor(() => expect(result.current.totalCount).toBe(2));

    act(() => result.current.applyFilters({}));

    expect(result.current.filteredCount).toBe(2);
  });

  it('sets error when API call fails', async () => {
    vi.mocked(api.getTopPicks).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useScreener());
    await act(async () => { await result.current.refresh(); });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBe('Network error');
      expect(result.current.stocks).toEqual([]);
    });
  });
});
