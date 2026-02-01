/**
 * Global State Management with Zustand
 */

import { create } from 'zustand';
import type {
  StockAnalysis,
  MarketRegime,
  ToastMessage,
  StockUniverseResponse,
} from '@/types';
import { generateId } from '@/lib/utils';

// ============================================================================
// Additional Types
// ============================================================================

export interface HistoricalDataPoint {
  timestamp: string;
  composite_score: number;
  recommendation: string;
  confidence: number;
  price?: number;
}

export interface HistoricalData {
  symbol: string;
  history: HistoricalDataPoint[];
  trend: any;
  statistics: any;
  timestamp: string;
}

export interface TopPicksFilters {
  topCount: number;
  sortBy: 'score' | 'confidence' | 'symbol';
  sector: string;
  recommendation: string;
}

interface AppState {
  // Market regime
  marketRegime: MarketRegime | null;
  setMarketRegime: (regime: MarketRegime | null) => void;

  // Stock universe
  stockUniverse: StockUniverseResponse | null;
  setStockUniverse: (universe: StockUniverseResponse | null) => void;

  // Analysis cache
  analysisCache: Map<string, StockAnalysis>;
  cacheAnalysis: (symbol: string, analysis: StockAnalysis) => void;
  getCachedAnalysis: (symbol: string) => StockAnalysis | undefined;
  clearCache: () => void;

  // Loading states
  loading: {
    analyze: boolean;
    topPicks: boolean;
    regime: boolean;
    universe: boolean;
  };
  setLoading: (key: keyof AppState['loading'], value: boolean) => void;

  // Toast messages
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;

  // Selected stock for details view
  selectedStock: StockAnalysis | null;
  setSelectedStock: (stock: StockAnalysis | null) => void;

  // Search query
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  // ========================================================================
  // New State Slices for Enhanced Dashboard
  // ========================================================================

  // Watchlist management
  watchlist: string[];
  addToWatchlist: (symbol: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  isInWatchlist: (symbol: string) => boolean;
  setWatchlist: (symbols: string[]) => void;

  // Historical data cache (with TTL)
  historicalCache: Map<string, { data: HistoricalData; timestamp: number }>;
  cacheHistoricalData: (symbol: string, data: HistoricalData) => void;
  getHistoricalData: (symbol: string, maxAge?: number) => HistoricalData | undefined;
  clearHistoricalCache: () => void;

  // Comparison state (2-4 stocks)
  comparisonStocks: string[];
  addToComparison: (symbol: string) => void;
  removeFromComparison: (symbol: string) => void;
  clearComparison: () => void;
  canAddToComparison: () => boolean;

  // Top Picks filters
  topPicksFilters: TopPicksFilters;
  setTopPicksFilters: (filters: Partial<TopPicksFilters>) => void;
  resetTopPicksFilters: () => void;

  // Recent searches (for quick access)
  recentSearches: string[];
  addRecentSearch: (symbol: string) => void;
  clearRecentSearches: () => void;
}

export const useStore = create<AppState>((set, get) => ({
  // Market regime
  marketRegime: null,
  setMarketRegime: (regime) => set({ marketRegime: regime }),

  // Stock universe
  stockUniverse: null,
  setStockUniverse: (universe) => set({ stockUniverse: universe }),

  // Analysis cache
  analysisCache: new Map(),
  cacheAnalysis: (symbol, analysis) => {
    const cache = new Map(get().analysisCache);
    cache.set(symbol.toUpperCase(), analysis);
    set({ analysisCache: cache });
  },
  getCachedAnalysis: (symbol) => {
    return get().analysisCache.get(symbol.toUpperCase());
  },
  clearCache: () => set({ analysisCache: new Map() }),

  // Loading states
  loading: {
    analyze: false,
    topPicks: false,
    regime: false,
    universe: false,
  },
  setLoading: (key, value) =>
    set((state) => ({
      loading: { ...state.loading, [key]: value },
    })),

  // Toast messages
  toasts: [],
  addToast: (toast) => {
    const id = generateId();
    const newToast = { ...toast, id };
    set((state) => ({ toasts: [...state.toasts, newToast] }));

    // Auto-remove after duration
    const duration = toast.duration || 5000;
    setTimeout(() => {
      get().removeToast(id);
    }, duration);
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  // Selected stock
  selectedStock: null,
  setSelectedStock: (stock) => set({ selectedStock: stock }),

  // Search query
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  // ========================================================================
  // Watchlist Management
  // ========================================================================

  watchlist: [],

  addToWatchlist: (symbol) => {
    const normalized = symbol.toUpperCase();
    set((state) => {
      if (!state.watchlist.includes(normalized)) {
        return { watchlist: [...state.watchlist, normalized] };
      }
      return state;
    });
  },

  removeFromWatchlist: (symbol) => {
    const normalized = symbol.toUpperCase();
    set((state) => ({
      watchlist: state.watchlist.filter((s) => s !== normalized),
    }));
  },

  isInWatchlist: (symbol) => {
    const normalized = symbol.toUpperCase();
    return get().watchlist.includes(normalized);
  },

  setWatchlist: (symbols) => {
    set({ watchlist: symbols.map((s) => s.toUpperCase()) });
  },

  // ========================================================================
  // Historical Data Cache (with TTL)
  // ========================================================================

  historicalCache: new Map(),

  cacheHistoricalData: (symbol, data) => {
    const cache = new Map(get().historicalCache);
    cache.set(symbol.toUpperCase(), {
      data,
      timestamp: Date.now(),
    });
    set({ historicalCache: cache });
  },

  getHistoricalData: (symbol, maxAge = 900000) => {
    // Default maxAge: 15 minutes (900000ms)
    const cached = get().historicalCache.get(symbol.toUpperCase());
    if (!cached) return undefined;

    const age = Date.now() - cached.timestamp;
    if (age > maxAge) {
      // Cache expired, remove it
      const cache = new Map(get().historicalCache);
      cache.delete(symbol.toUpperCase());
      set({ historicalCache: cache });
      return undefined;
    }

    return cached.data;
  },

  clearHistoricalCache: () => set({ historicalCache: new Map() }),

  // ========================================================================
  // Comparison State (2-4 stocks)
  // ========================================================================

  comparisonStocks: [],

  addToComparison: (symbol) => {
    const normalized = symbol.toUpperCase();
    set((state) => {
      if (
        !state.comparisonStocks.includes(normalized) &&
        state.comparisonStocks.length < 4
      ) {
        return { comparisonStocks: [...state.comparisonStocks, normalized] };
      }
      return state;
    });
  },

  removeFromComparison: (symbol) => {
    const normalized = symbol.toUpperCase();
    set((state) => ({
      comparisonStocks: state.comparisonStocks.filter((s) => s !== normalized),
    }));
  },

  clearComparison: () => set({ comparisonStocks: [] }),

  canAddToComparison: () => {
    return get().comparisonStocks.length < 4;
  },

  // ========================================================================
  // Top Picks Filters
  // ========================================================================

  topPicksFilters: {
    topCount: 10,
    sortBy: 'score',
    sector: 'All',
    recommendation: 'All',
  },

  setTopPicksFilters: (filters) => {
    set((state) => ({
      topPicksFilters: { ...state.topPicksFilters, ...filters },
    }));
  },

  resetTopPicksFilters: () => {
    set({
      topPicksFilters: {
        topCount: 10,
        sortBy: 'score',
        sector: 'All',
        recommendation: 'All',
      },
    });
  },

  // ========================================================================
  // Recent Searches (persisted)
  // ========================================================================

  recentSearches: [],

  addRecentSearch: (symbol) => {
    const normalized = symbol.toUpperCase();
    set((state) => {
      // Remove if already exists to move to front
      const filtered = state.recentSearches.filter((s) => s !== normalized);
      // Add to front, keep only last 10
      return {
        recentSearches: [normalized, ...filtered].slice(0, 10),
      };
    });
  },

  clearRecentSearches: () => set({ recentSearches: [] }),
}));
