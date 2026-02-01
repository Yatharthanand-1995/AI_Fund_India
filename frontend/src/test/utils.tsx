/**
 * Test Utilities
 * Helper functions for testing React components
 */

import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

/**
 * Custom render function that includes providers
 */
export function renderWithRouter(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, {
    wrapper: ({ children }) => <BrowserRouter>{children}</BrowserRouter>,
    ...options
  });
}

/**
 * Mock stock analysis data for testing
 */
export const mockStockAnalysis = {
  symbol: 'TEST',
  composite_score: 75.5,
  recommendation: 'BUY',
  confidence: 85.0,
  agent_scores: {
    fundamentals: {
      score: 80.0,
      confidence: 85.0,
      reasoning: 'Good fundamentals',
      metrics: { pe_ratio: 15.5, roe: 18.2 },
      breakdown: {}
    },
    momentum: {
      score: 75.0,
      confidence: 80.0,
      reasoning: 'Positive momentum',
      metrics: { rsi: 65, sma_20: 1450 },
      breakdown: {}
    },
    quality: {
      score: 70.0,
      confidence: 75.0,
      reasoning: 'High quality',
      metrics: { debt_to_equity: 0.5 },
      breakdown: {}
    },
    sentiment: {
      score: 72.0,
      confidence: 70.0,
      reasoning: 'Positive sentiment',
      metrics: {},
      breakdown: {}
    },
    institutional_flow: {
      score: 78.0,
      confidence: 82.0,
      reasoning: 'Strong institutional buying',
      metrics: {},
      breakdown: {}
    }
  },
  weights: {
    fundamentals: 0.25,
    momentum: 0.20,
    quality: 0.20,
    sentiment: 0.15,
    institutional_flow: 0.20
  },
  market_regime: {
    regime: 'BULL',
    trend: 'BULL' as const,
    volatility: 'NORMAL' as const,
    weights: {
      fundamentals: 0.25,
      momentum: 0.20,
      quality: 0.20,
      sentiment: 0.15,
      institutional_flow: 0.20
    },
    metrics: {},
    timestamp: new Date().toISOString()
  },
  timestamp: new Date().toISOString(),
  cached: false
};

/**
 * Mock historical data for testing
 */
export const mockHistoricalData = {
  symbol: 'TEST',
  history: [
    {
      timestamp: '2026-01-01T00:00:00Z',
      composite_score: 70.0,
      recommendation: 'BUY',
      confidence: 80.0,
      price: 1400
    },
    {
      timestamp: '2026-01-15T00:00:00Z',
      composite_score: 75.0,
      recommendation: 'BUY',
      confidence: 82.0,
      price: 1450
    },
    {
      timestamp: '2026-02-01T00:00:00Z',
      composite_score: 75.5,
      recommendation: 'BUY',
      confidence: 85.0,
      price: 1500
    }
  ],
  trend: {
    direction: 'up',
    strength: 0.8
  },
  statistics: {
    avg_score: 73.5,
    min_score: 70.0,
    max_score: 75.5,
    current_score: 75.5,
    change: 5.5
  },
  timestamp: new Date().toISOString()
};

/**
 * Mock watchlist data
 */
export const mockWatchlist = [
  {
    symbol: 'TCS',
    added_at: '2026-01-01T00:00:00Z',
    notes: 'Good fundamentals',
    latest_score: 80.5,
    latest_recommendation: 'BUY'
  },
  {
    symbol: 'INFY',
    added_at: '2026-01-15T00:00:00Z',
    notes: 'Strong momentum',
    latest_score: 75.2,
    latest_recommendation: 'BUY'
  }
];

/**
 * Delay utility for async tests
 */
export const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
