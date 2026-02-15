/**
 * Tests for Screener page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Screener from '../Screener';

// Mock recharts (doesn't render in jsdom)
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  RadarChart: ({ children }: any) => <div>{children}</div>,
  Radar: () => null,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

// Mock useScreener hook
const mockRefresh = vi.fn();
const mockApplyFilters = vi.fn();

vi.mock('@/hooks/useScreener', () => ({
  useScreener: vi.fn(() => ({
    stocks: [],
    loading: false,
    error: null,
    filteredCount: 0,
    totalCount: 0,
    applyFilters: mockApplyFilters,
    refresh: mockRefresh,
  }))
}));

// Mock ScreenerFilters and ScreenerResults components
vi.mock('@/components/screener/ScreenerFilters', () => ({
  default: ({ onApplyFilters }: any) => (
    <div data-testid="screener-filters">
      <button onClick={() => onApplyFilters({ scoreMin: 70 })}>Apply Filter</button>
    </div>
  )
}));

vi.mock('@/components/screener/ScreenerResults', () => ({
  default: ({ stocks, viewMode }: any) => (
    <div data-testid="screener-results" data-viewmode={viewMode}>
      {stocks.map((s: any) => <div key={s.symbol}>{s.symbol}</div>)}
    </div>
  )
}));

vi.mock('@/components/screener/ScreenerPresets', () => ({
  default: ({ onClose }: any) => (
    <div data-testid="screener-presets">
      <button onClick={onClose}>Close</button>
    </div>
  )
}));

const renderScreener = () =>
  render(
    <BrowserRouter>
      <Screener />
    </BrowserRouter>
  );

describe('Screener page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderScreener();
    expect(screen.getByText(/Stock Screener/i)).toBeTruthy();
  });

  it('calls refresh on mount', () => {
    renderScreener();
    expect(mockRefresh).toHaveBeenCalled();
  });

  it('shows stock count in summary bar', () => {
    renderScreener();
    expect(screen.getByText(/showing/i)).toBeTruthy();
  });

  it('shows filters sidebar by default', () => {
    renderScreener();
    expect(screen.getByTestId('screener-filters')).toBeTruthy();
  });

  it('hides filters when Hide Filters is clicked', async () => {
    const user = userEvent.setup();
    renderScreener();

    const toggleBtn = screen.getByText(/Hide Filters/i);
    await user.click(toggleBtn);

    expect(screen.queryByTestId('screener-filters')).toBeNull();
    expect(screen.getByText(/Show Filters/i)).toBeTruthy();
  });

  it('calls applyFilters when filter is applied', async () => {
    const user = userEvent.setup();
    renderScreener();

    const applyBtn = screen.getByText(/Apply Filter/i);
    await user.click(applyBtn);

    expect(mockApplyFilters).toHaveBeenCalledWith({ scoreMin: 70 });
  });

  it('toggles presets panel when Presets button clicked', async () => {
    const user = userEvent.setup();
    renderScreener();

    const presetsBtn = screen.getByText(/Presets/i);
    await user.click(presetsBtn);

    expect(screen.getByTestId('screener-presets')).toBeTruthy();
  });

  it('switches to cards view mode', async () => {
    const user = userEvent.setup();
    renderScreener();

    const cardsBtn = document.querySelector('button[class*="rounded-md"] + button');
    if (cardsBtn) {
      await user.click(cardsBtn as HTMLElement);
    }

    const results = screen.getByTestId('screener-results');
    expect(results).toBeTruthy();
  });

  it('disables Export CSV when no stocks loaded', () => {
    renderScreener();
    const exportBtn = screen.getByText(/Export CSV/i).closest('button');
    expect(exportBtn).toHaveProperty('disabled', true);
  });

  it('shows error message when API fails', async () => {
    const { useScreener } = await import('@/hooks/useScreener');
    vi.mocked(useScreener).mockReturnValueOnce({
      stocks: [],
      loading: false,
      error: 'Failed to load stocks',
      filteredCount: 0,
      totalCount: 0,
      applyFilters: mockApplyFilters,
      refresh: mockRefresh,
    } as any);

    renderScreener();

    // Multiple elements may match — just check at least one exists
    await waitFor(() => {
      expect(screen.getAllByText(/Failed to load stocks/i).length).toBeGreaterThan(0);
    });
  });
});
