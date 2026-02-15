/**
 * Tests for Backtest page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Backtest from '../Backtest';
import api from '@/lib/api';

// Mock API
vi.mock('@/lib/api', () => ({
  default: {
    getBacktestRuns: vi.fn(),
    runBacktest: vi.fn(),
  }
}));

// Mock heavy sub-components
vi.mock('@/components/backtest/BacktestConfigForm', () => ({
  default: ({ onSubmit }: any) => (
    <div data-testid="backtest-config-form">
      <button onClick={() => onSubmit({ symbols: ['TCS'], start_date: '2025-01-01', end_date: '2026-01-01' })}>
        Run Backtest
      </button>
    </div>
  )
}));

vi.mock('@/components/backtest/BacktestRunsList', () => ({
  default: ({ runs }: any) => (
    <div data-testid="backtest-runs-list">
      {runs.map((r: any) => (
        <div key={r.id} data-testid={`run-${r.id}`}>{r.id}</div>
      ))}
    </div>
  )
}));

vi.mock('@/components/backtest/BacktestResults', () => ({
  default: ({ runId }: any) => (
    <div data-testid="backtest-results">Results for {runId}</div>
  )
}));

vi.mock('@/store/useStore', () => ({
  useStore: () => ({
    addToast: vi.fn(),
  })
}));

const renderBacktest = () =>
  render(
    <BrowserRouter>
      <Backtest />
    </BrowserRouter>
  );

describe('Backtest page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderBacktest();
    expect(document.body).toBeTruthy();
  });

  it('shows the new backtest form by default', () => {
    renderBacktest();
    expect(screen.getByTestId('backtest-config-form')).toBeTruthy();
  });

  it('switches to history view when History tab is clicked', async () => {
    vi.mocked(api.getBacktestRuns).mockResolvedValueOnce({
      runs: [
        { id: 'run-001', created_at: '2026-01-01', status: 'completed' },
      ]
    } as any);

    const user = userEvent.setup();
    renderBacktest();

    const historyBtn = screen.getByText(/previous runs/i);
    await user.click(historyBtn);

    await waitFor(() => {
      expect(screen.getByTestId('backtest-runs-list')).toBeTruthy();
    });
  });

  it('shows run list after switching to history', async () => {
    vi.mocked(api.getBacktestRuns).mockResolvedValueOnce({
      runs: [
        { id: 'run-001', created_at: '2026-01-01', status: 'completed' },
        { id: 'run-002', created_at: '2026-01-15', status: 'completed' },
      ]
    } as any);

    const user = userEvent.setup();
    renderBacktest();

    const historyBtn = screen.getByText(/previous runs/i);
    await user.click(historyBtn);

    await waitFor(() => {
      expect(screen.getByTestId('run-run-001')).toBeTruthy();
      expect(screen.getByTestId('run-run-002')).toBeTruthy();
    });
  });

  it('shows empty state when history API returns no runs', async () => {
    vi.mocked(api.getBacktestRuns).mockResolvedValueOnce({ runs: [] } as any);

    const user = userEvent.setup();
    renderBacktest();

    const historyBtn = screen.getByText(/previous runs/i);
    await user.click(historyBtn);

    await waitFor(() => {
      expect(screen.getByText(/no backtest runs yet/i)).toBeTruthy();
    });
  });
});
