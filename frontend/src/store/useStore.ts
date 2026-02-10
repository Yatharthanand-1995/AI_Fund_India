/**
 * Global State Management with Zustand
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  StockAnalysis,
  MarketRegime,
  ToastMessage,
  StockUniverseResponse,
  TopPicksResponse,
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

export interface WatchlistItem {
  symbol: string;
  added_at: number;
  latest_score?: number;
  latest_recommendation?: string;
  latest_sector?: string;
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
  watchlist: WatchlistItem[];
  addToWatchlist: (symbol: string, stockData?: Partial<WatchlistItem>) => void;
  removeFromWatchlist: (symbol: string) => void;
  isInWatchlist: (symbol: string) => boolean;
  updateWatchlistItem: (symbol: string, updates: Partial<WatchlistItem>) => void;
  setWatchlist: (items: WatchlistItem[]) => void;

  // Historical data cache (with TTL)
  historicalCache: Map<string, { data: HistoricalData; timestamp: number }>;
  cacheHistoricalData: (symbol: string, data: HistoricalData) => void;
  getHistoricalData: (symbol: string, maxAge?: number) => HistoricalData | undefined;
  clearHistoricalCache: () => void;

  // Top picks cache (with TTL)
  topPicksCache: Map<string, { data: TopPicksResponse; timestamp: number }>;
  cacheTopPicks: (key: string, data: TopPicksResponse) => void;
  getCachedTopPicks: (key: string, maxAge?: number) => TopPicksResponse | undefined;
  clearTopPicksCache: () => void;

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

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
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

  addToWatchlist: (symbol, stockData) => {
    const normalized = symbol.toUpperCase();
    set((state) => {
      const exists = state.watchlist.find(item => item.symbol === normalized);
      if (!exists) {
        const newItem: WatchlistItem = {
          symbol: normalized,
          added_at: Date.now(),
          ...stockData
        };
        return { watchlist: [...state.watchlist, newItem] };
      }
      return state;
    });
  },

  removeFromWatchlist: (symbol) => {
    const normalized = symbol.toUpperCase();
    set((state) => ({
      watchlist: state.watchlist.filter((item) => item.symbol !== normalized),
    }));
  },

  isInWatchlist: (symbol) => {
    const normalized = symbol.toUpperCase();
    return get().watchlist.some(item => item.symbol === normalized);
  },

  updateWatchlistItem: (symbol, updates) => {
    const normalized = symbol.toUpperCase();
    set((state) => ({
      watchlist: state.watchlist.map(item =>
        item.symbol === normalized
          ? { ...item, ...updates }
          : item
      ),
    }));
  },

  setWatchlist: (items) => {
    set({ watchlist: items });
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
  // Top Picks Cache (with TTL)
  // ========================================================================

  topPicksCache: new Map(),

  cacheTopPicks: (key, data) => {
    const cache = new Map(get().topPicksCache);
    cache.set(key, {
      data,
      timestamp: Date.now(),
    });
    set({ topPicksCache: cache });
  },

  getCachedTopPicks: (key, maxAge = 900000) => {
    // Default maxAge: 15 minutes (900000ms)
    const cached = get().topPicksCache.get(key);
    if (!cached) return undefined;

    const age = Date.now() - cached.timestamp;
    if (age > maxAge) {
      // Cache expired, remove it
      const cache = new Map(get().topPicksCache);
      cache.delete(key);
      set({ topPicksCache: cache });
      return undefined;
    }

    return cached.data;
  },

  clearTopPicksCache: () => set({ topPicksCache: new Map() }),

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
    }),
    {
      name: 'indian-stock-fund-storage',
      storage: createJSONStorage(() => localStorage),
      version: 2, // Increment version for watchlist migration
      // Migration function to handle version upgrades
      migrate: (persistedState: any, version: number) => {
        if (version < 2) {
          // Migrate watchlist from string[] to WatchlistItem[]
          if (Array.isArray(persistedState.watchlist)) {
            persistedState.watchlist = persistedState.watchlist.map(
              (symbol: string) => ({
                symbol: typeof symbol === 'string' ? symbol : String(symbol),
                added_at: Date.now(),
              })
            );
          }
        }
        return persistedState;
      },
      // Only persist specific slices to avoid bloat and handle Maps gracefully
      partialize: (state) => ({
        watchlist: state.watchlist,
        recentSearches: state.recentSearches,
        topPicksFilters: state.topPicksFilters,
        comparisonStocks: state.comparisonStocks,
      }),
    }
  )
);
