/**
 * Tests for useStockHistory hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useStockHistory } from '../useStockHistory';
import api from '@/lib/api';
import { mockHistoricalData } from '@/test/utils';

// Mock the API
vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn()
  }
}));

describe('useStockHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch stock history', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockHistoricalData });

    const { result } = renderHook(() =>
      useStockHistory('TEST', { days: 30 })
    );

    // Initially loading
    expect(result.current.loading).toBe(true);

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeTruthy();
    expect(result.current.data?.symbol).toBe('TEST');
    expect(result.current.data?.history).toHaveLength(3);
  });

  it('should not fetch when disabled', async () => {
    const { result } = renderHook(() =>
      useStockHistory('TEST', { enabled: false })
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(api.get).not.toHaveBeenCalled();
  });

  it('should not fetch when symbol is empty', async () => {
    const { result } = renderHook(() =>
      useStockHistory('', { days: 30 })
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(api.get).not.toHaveBeenCalled();
  });

  it('should handle errors', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('API Error'));

    const { result } = renderHook(() =>
      useStockHistory('TEST', { days: 30 })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeNull();
  });

  it('should refetch when requested', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: mockHistoricalData });

    const { result } = renderHook(() =>
      useStockHistory('TEST', { days: 30 })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Clear mock and refetch
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockHistoricalData });

    await result.current.refetch();

    expect(api.get).toHaveBeenCalledTimes(1);
  });
});
