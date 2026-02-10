/**
 * Application-wide constants
 * Centralizes magic numbers and hardcoded values
 */

export const DEFAULT_STOCK_SYMBOLS = [
  'TCS',
  'INFY',
  'RELIANCE',
  'HDFCBANK',
  'ICICIBANK',
] as const;

export const CACHE_DURATIONS = {
  TOP_PICKS: 15 * 60 * 1000,     // 15 minutes
  REGIME_DATA: 30 * 60 * 1000,   // 30 minutes
  HISTORICAL_DATA: 15 * 60 * 1000, // 15 minutes
  WATCHLIST_DATA: 5 * 60 * 1000, // 5 minutes
} as const;

export const API_LIMITS = {
  TOP_PICKS: 50,
  BACKTEST_RESULTS: 50,
  WATCHLIST_SUGGESTIONS: 20,
  QUICK_SYMBOLS: 5,
} as const;

export const TIMEOUTS = {
  API_REQUEST: 30000,  // 30 seconds
  BACKTEST: 120000,    // 2 minutes
} as const;

export const SCORE_THRESHOLDS = {
  STRONG_BUY: 75,
  BUY: 60,
  HOLD: 40,
  SELL: 25,
} as const;
