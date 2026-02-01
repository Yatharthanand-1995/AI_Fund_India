/**
 * Tests for Dashboard page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';
import api from '@/lib/api';
import { mockStockAnalysis } from '@/test/utils';

// Mock API
vi.mock('@/lib/api');

// Mock hooks
vi.mock('@/hooks/useWatchlist', () => ({
  useWatchlist: () => ({
    watchlist: [],
    loading: false,
    error: null
  })
}));

vi.mock('@/hooks/useSectorAnalysis', () => ({
  useSectorAnalysis: () => ({
    sectors: [],
    getTopSectors: () => [],
    loading: false
  })
}));

vi.mock('@/hooks/useStockHistory', () => ({
  useStockHistory: () => ({
    data: null,
    loading: false,
    error: null
  })
}));

const renderDashboard = () => {
  return render(
    <BrowserRouter>
      <Dashboard />
    </BrowserRouter>
  );
};

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render page title', () => {
    renderDashboard();
    expect(screen.getByText(/AI-Powered Stock Analysis/i)).toBeTruthy();
  });

  it('should render search input', () => {
    renderDashboard();
    const input = screen.getByPlaceholderText(/enter stock symbol/i);
    expect(input).toBeTruthy();
  });

  it('should render analyze button', () => {
    renderDashboard();
    const button = screen.getByRole('button', { name: /analyze stock/i });
    expect(button).toBeTruthy();
  });

  it('should show quick symbols', () => {
    renderDashboard();
    // Default quick symbols
    expect(screen.queryByText('TCS')).toBeTruthy();
    expect(screen.queryByText('INFY')).toBeTruthy();
  });

  it('should handle stock analysis', async () => {
    vi.mocked(api.analyzeStock).mockResolvedValueOnce(mockStockAnalysis);
    vi.mocked(api.get).mockResolvedValue({ data: { history: [] } });

    renderDashboard();

    const input = screen.getByPlaceholderText(/enter stock symbol/i);
    const button = screen.getByRole('button', { name: /analyze stock/i });

    // Type symbol
    await userEvent.type(input, 'TCS');

    // Click analyze
    await userEvent.click(button);

    // Wait for analysis to complete
    await waitFor(() => {
      expect(api.analyzeStock).toHaveBeenCalledWith({
        symbol: 'TCS',
        include_narrative: true
      });
    });
  });

  it('should show KPI cards when no analysis', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        total_requests: 100,
        cache_hit_rate: 75.5
      }
    });

    renderDashboard();

    await waitFor(() => {
      // KPI cards should be visible
      expect(screen.queryByText(/Total Analyses|Watchlist|Cache Hit Rate/i)).toBeTruthy();
    });
  });
});
