/**
 * Tests for Watchlist page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Watchlist from '../Watchlist';

// Mock useWatchlist hook
const mockRemove = vi.fn();
const mockRefresh = vi.fn();

vi.mock('@/hooks/useWatchlist', () => ({
  useWatchlist: vi.fn(() => ({
    watchlist: [],
    loading: false,
    error: null,
    remove: mockRemove,
    refresh: mockRefresh,
    count: 0,
  }))
}));

// Mock confirm dialog
globalThis.confirm = vi.fn(() => true);

const renderWatchlist = () =>
  render(
    <BrowserRouter>
      <Watchlist />
    </BrowserRouter>
  );

describe('Watchlist page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWatchlist();
    expect(screen.getAllByRole('heading', { name: /watchlist/i }).length).toBeGreaterThan(0);
  });

  it('shows empty state when watchlist is empty', () => {
    renderWatchlist();
    expect(screen.getByText(/0 stock/i)).toBeTruthy();
  });

  it('shows stock count in header', async () => {
    const { useWatchlist } = await import('@/hooks/useWatchlist');
    vi.mocked(useWatchlist).mockReturnValueOnce({
      watchlist: [
        { symbol: 'TCS', added_at: 1704067200000, latest_score: 80.5, latest_recommendation: 'BUY' },
        { symbol: 'INFY', added_at: 1705276800000, latest_score: 75.2, latest_recommendation: 'BUY' },
      ],
      loading: false,
      error: null,
      remove: mockRemove,
      refresh: mockRefresh,
      count: 2,
    } as any);

    renderWatchlist();

    expect(screen.getByText(/2 stock/i)).toBeTruthy();
  });

  it('renders watchlist items', async () => {
    const { useWatchlist } = await import('@/hooks/useWatchlist');
    vi.mocked(useWatchlist).mockReturnValueOnce({
      watchlist: [
        { symbol: 'TCS', added_at: 1704067200000, latest_score: 80.5, latest_recommendation: 'BUY' },
      ],
      loading: false,
      error: null,
      remove: mockRemove,
      refresh: mockRefresh,
      count: 1,
    } as any);

    renderWatchlist();

    expect(screen.getByText('TCS')).toBeTruthy();
  });

  it('calls remove when delete is confirmed', async () => {
    const { useWatchlist } = await import('@/hooks/useWatchlist');
    vi.mocked(useWatchlist).mockReturnValueOnce({
      watchlist: [
        { symbol: 'TCS', added_at: 1704067200000, latest_score: 80.5, latest_recommendation: 'BUY' },
      ],
      loading: false,
      error: null,
      remove: mockRemove,
      refresh: mockRefresh,
      count: 1,
    } as any);

    const user = userEvent.setup();
    renderWatchlist();

    const deleteBtn = screen.getByTitle(/remove from watchlist/i);
    await user.click(deleteBtn);

    await waitFor(() => {
      expect(mockRemove).toHaveBeenCalledWith('TCS');
    });
  });

  it('calls refresh when Refresh All is clicked', async () => {
    const user = userEvent.setup();
    renderWatchlist();

    const refreshBtn = screen.getByText(/refresh all/i);
    await user.click(refreshBtn);

    expect(mockRefresh).toHaveBeenCalled();
  });

  it('shows error message when error is present', async () => {
    const { useWatchlist } = await import('@/hooks/useWatchlist');
    vi.mocked(useWatchlist).mockReturnValueOnce({
      watchlist: [],
      loading: false,
      error: new Error('Failed to load watchlist'),
      remove: mockRemove,
      refresh: mockRefresh,
      count: 0,
    } as any);

    renderWatchlist();

    expect(screen.getByText(/Failed to load watchlist/i)).toBeTruthy();
  });

  it('shows loading spinner when loading with empty watchlist', async () => {
    const { useWatchlist } = await import('@/hooks/useWatchlist');
    vi.mocked(useWatchlist).mockReturnValueOnce({
      watchlist: [],
      loading: true,
      error: null,
      remove: mockRemove,
      refresh: mockRefresh,
      count: 0,
    } as any);

    renderWatchlist();

    expect(screen.getByText(/loading watchlist/i)).toBeTruthy();
  });
});
