/**
 * Tests for useSectorAnalysis hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useSectorAnalysis } from '../useSectorAnalysis';
import { api } from '@/lib/api';

// The hook uses `import { api } from '../lib/api'` (named export).
// vi.mock is hoisted, so we can't reference variables from outer scope inside the factory.
// Instead both exports share the same vi.fn() created inside the factory.
vi.mock('@/lib/api', () => {
  const get = vi.fn();
  const shared = { get };
  return {
    default: shared,
    api: shared,
  };
});

const mockSectorData = {
  data: {
    sectors: [
      { sector: 'IT', stock_count: 10, avg_score: 75.5, top_pick: 'TCS', trend: 'UPTREND' },
      { sector: 'Banking', stock_count: 8, avg_score: 68.2, top_pick: 'HDFCBANK', trend: 'SIDEWAYS' },
      { sector: 'FMCG', stock_count: 5, avg_score: 62.1, top_pick: 'HUL', trend: 'SIDEWAYS' },
    ],
    total_sectors: 3,
    timestamp: '2026-02-15T10:00:00Z',
  }
};

describe('useSectorAnalysis', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches sector data on mount', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockSectorData);

    const { result } = renderHook(() => useSectorAnalysis());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.sectors).toHaveLength(3);
    });

    expect(api.get).toHaveBeenCalledWith('/analytics/sectors', expect.any(Object));
  });

  it('returns empty sectors array initially', () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockSectorData);

    const { result } = renderHook(() => useSectorAnalysis());

    // Before data loads
    expect(result.current.sectors).toEqual([]);
    expect(result.current.loading).toBe(true);
  });

  it('getTopSectors returns correct number of sectors', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockSectorData);

    const { result } = renderHook(() => useSectorAnalysis());

    await waitFor(() => expect(result.current.sectors).toHaveLength(3));

    const top2 = result.current.getTopSectors(2);
    expect(top2).toHaveLength(2);
    expect(top2[0].sector).toBe('IT');
    expect(top2[1].sector).toBe('Banking');
  });

  it('getSectorByName finds sector case-insensitively', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockSectorData);

    const { result } = renderHook(() => useSectorAnalysis());

    await waitFor(() => expect(result.current.sectors).toHaveLength(3));

    const sector = result.current.getSectorByName('it');
    expect(sector).toBeDefined();
    expect(sector?.top_pick).toBe('TCS');
  });

  it('getSectorByName returns undefined for unknown sector', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockSectorData);

    const { result } = renderHook(() => useSectorAnalysis());

    await waitFor(() => expect(result.current.sectors).toHaveLength(3));

    const sector = result.current.getSectorByName('NonExistent');
    expect(sector).toBeUndefined();
  });

  it('sets error state on API failure', async () => {
    const mockError = new Error('Failed to load sectors');
    vi.mocked(api.get).mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useSectorAnalysis());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeTruthy();
    });
  });

  it('does not fetch when enabled=false', () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockSectorData);

    renderHook(() => useSectorAnalysis({ enabled: false }));

    expect(api.get).not.toHaveBeenCalled();
  });

  it('reports total sectors correctly', async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockSectorData);

    const { result } = renderHook(() => useSectorAnalysis());

    await waitFor(() => expect(result.current.totalSectors).toBe(3));
  });
});
