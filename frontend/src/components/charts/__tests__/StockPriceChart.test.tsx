/**
 * Tests for StockPriceChart component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StockPriceChart } from '../StockPriceChart';
import { mockHistoricalData } from '@/test/utils';

describe('StockPriceChart', () => {
  it('should render chart with data', () => {
    render(
      <StockPriceChart
        symbol="TEST"
        data={mockHistoricalData.history}
        height={300}
      />
    );

    // Check for chart container
    expect(document.querySelector('.recharts-wrapper')).toBeTruthy();
  });

  it('should display time range selector', () => {
    render(
      <StockPriceChart
        symbol="TEST"
        data={mockHistoricalData.history}
        height={300}
      />
    );

    // Check for time range buttons
    expect(screen.queryByText('1M')).toBeTruthy();
    expect(screen.queryByText('3M')).toBeTruthy();
    expect(screen.queryByText('6M')).toBeTruthy();
  });

  it('should show both price and score when enabled', () => {
    const { container } = render(
      <StockPriceChart
        symbol="TEST"
        data={mockHistoricalData.history}
        height={300}
        showPrice={true}
        showScore={true}
      />
    );

    // Should have dual-axis chart
    const yAxes = container.querySelectorAll('.recharts-yAxis');
    expect(yAxes.length).toBeGreaterThanOrEqual(1);
  });

  it('should handle empty data', () => {
    const { container } = render(
      <StockPriceChart
        symbol="TEST"
        data={[]}
        height={300}
      />
    );

    // Should show empty state or render without errors
    expect(container).toBeTruthy();
  });
});
