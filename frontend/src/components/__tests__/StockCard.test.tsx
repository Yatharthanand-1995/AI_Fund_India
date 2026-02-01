/**
 * Tests for StockCard component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import StockCard from '../StockCard';
import { mockStockAnalysis } from '@/test/utils';

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('StockCard', () => {
  it('should display stock symbol', () => {
    renderWithRouter(<StockCard analysis={mockStockAnalysis} />);
    expect(screen.getByText('TEST')).toBeTruthy();
  });

  it('should display composite score', () => {
    renderWithRouter(<StockCard analysis={mockStockAnalysis} />);
    expect(screen.getByText(/75\.5/)).toBeTruthy();
  });

  it('should display recommendation', () => {
    renderWithRouter(<StockCard analysis={mockStockAnalysis} />);
    expect(screen.getByText('BUY')).toBeTruthy();
  });

  it('should display agent scores', () => {
    renderWithRouter(<StockCard analysis={mockStockAnalysis} detailed />);

    // Check for agent names
    expect(screen.queryByText(/fundamentals/i)).toBeTruthy();
    expect(screen.queryByText(/momentum/i)).toBeTruthy();
  });

  it('should show narrative when detailed mode is enabled', () => {
    const analysisWithNarrative = {
      ...mockStockAnalysis,
      narrative: {
        investment_thesis: 'Strong buy thesis',
        key_strengths: ['Good fundamentals', 'Strong momentum'],
        key_risks: ['Market volatility'],
        summary: 'Overall positive outlook',
        provider: 'test'
      }
    };

    renderWithRouter(<StockCard analysis={analysisWithNarrative} detailed />);

    expect(screen.queryByText(/thesis/i)).toBeTruthy();
  });

  it('should handle missing optional fields', () => {
    const minimalAnalysis = {
      symbol: 'TEST',
      composite_score: 75.5,
      recommendation: 'BUY',
      confidence: 85.0,
      agent_scores: mockStockAnalysis.agent_scores,
      weights: mockStockAnalysis.weights,
      timestamp: new Date().toISOString()
    };

    renderWithRouter(<StockCard analysis={minimalAnalysis} />);

    // Should render without crashing
    expect(screen.getByText('TEST')).toBeTruthy();
  });
});
