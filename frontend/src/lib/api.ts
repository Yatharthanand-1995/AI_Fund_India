/**
 * API Client for AI Hedge Fund Backend
 *
 * Communicates with FastAPI backend at http://localhost:8000
 * All requests go through /api proxy in development
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { logger } from './logger';
import type {
  AnalyzeRequest,
  BatchAnalyzeRequest,
  StockAnalysis,
  BatchAnalysisResponse,
  TopPicksResponse,
  MarketRegime,
  HealthResponse,
  StockUniverseResponse,
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_URL || '/api';
const API_KEY = import.meta.env.VITE_API_KEY || '';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    logger.log('[APIClient] Initializing with BASE_URL:', BASE_URL);
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (API_KEY) {
      headers['X-API-Key'] = API_KEY;
    }
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 120000, // 2 minutes for batch operations
      headers,
    });
    logger.log('[APIClient] Axios baseURL:', this.client.defaults.baseURL);

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          // Server responded with error
          const message = (error.response.data as any)?.error || error.message;
          throw new Error(message);
        } else if (error.request) {
          // Request made but no response
          throw new Error('No response from server. Please check if the API is running.');
        } else {
          // Something else happened
          throw new Error(error.message);
        }
      }
    );
  }

  /**
   * Analyze a single stock
   */
  async analyzeStock(request: AnalyzeRequest): Promise<StockAnalysis> {
    const response = await this.client.post<StockAnalysis>('/analyze', request);
    return response.data;
  }

  /**
   * Analyze multiple stocks in batch
   */
  async analyzeBatch(request: BatchAnalyzeRequest): Promise<BatchAnalysisResponse> {
    const response = await this.client.post<BatchAnalysisResponse>('/analyze/batch', request);
    return response.data;
  }

  /**
   * Get top picks from NIFTY 50
   */
  async getTopPicks(limit: number = 10, include_narrative: boolean = false): Promise<TopPicksResponse> {
    const response = await this.client.get<TopPicksResponse>('/portfolio/top-picks', {
      params: { limit, include_narrative },
    });
    return response.data;
  }

  /**
   * Get current market regime
   */
  async getMarketRegime(): Promise<MarketRegime> {
    const response = await this.client.get<MarketRegime>('/market/regime');
    return response.data;
  }

  /**
   * Get system health status
   */
  async getHealth(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  /**
   * Get available stock universe
   */
  async getStockUniverse(): Promise<StockUniverseResponse> {
    const response = await this.client.get<StockUniverseResponse>('/stocks/universe');
    return response.data;
  }

  /**
   * Get API root info
   */
  async getRoot(): Promise<any> {
    const response = await this.client.get('/');
    return response.data;
  }

  // ========================================================================
  // Historical Data Endpoints
  // ========================================================================

  /**
   * Get historical analysis for a stock
   */
  async getStockHistory(symbol: string, days: number = 30, includePrice: boolean = true): Promise<any> {
    const response = await this.client.get(`/history/stock/${symbol}`, {
      params: { days, include_price: includePrice }
    });
    return response.data;
  }

  /**
   * Get market regime history
   */
  async getRegimeHistory(days: number = 30): Promise<any> {
    const response = await this.client.get('/history/regime', {
      params: { days }
    });
    return response.data;
  }

  // ========================================================================
  // Analytics Endpoints
  // ========================================================================

  /**
   * Get system analytics and performance metrics
   */
  async getSystemAnalytics(): Promise<any> {
    const response = await this.client.get('/analytics/system');
    return response.data;
  }

  /**
   * Get sector analysis
   */
  async getSectorAnalysis(days: number = 7): Promise<any> {
    const response = await this.client.get('/analytics/sectors', {
      params: { days }
    });
    return response.data;
  }

  /**
   * Get agent performance analytics
   */
  async getAgentAnalytics(): Promise<any> {
    const response = await this.client.get('/analytics/agents');
    return response.data;
  }

  // ========================================================================
  // Watchlist Endpoints
  // ========================================================================

  /**
   * Get user's watchlist
   */
  async getWatchlist(): Promise<any> {
    const response = await this.client.get('/watchlist');
    return response.data;
  }

  /**
   * Add stock to watchlist
   */
  async addToWatchlist(symbol: string, notes?: string): Promise<any> {
    const response = await this.client.post('/watchlist', { symbol, notes });
    return response.data;
  }

  /**
   * Remove stock from watchlist
   */
  async removeFromWatchlist(symbol: string): Promise<any> {
    const response = await this.client.delete(`/watchlist/${symbol}`);
    return response.data;
  }

  // ========================================================================
  // Comparison Endpoint
  // ========================================================================

  /**
   * Compare multiple stocks side-by-side
   */
  async compareStocks(symbols: string[], includeHistory: boolean = false): Promise<any> {
    const response = await this.client.post('/compare', {
      symbols,
      include_history: includeHistory
    });
    return response.data;
  }

  // ========================================================================
  // Export Endpoint
  // ========================================================================

  /**
   * Export stock analysis data
   */
  async exportAnalysis(symbol: string, format: 'json' | 'csv' = 'json'): Promise<any> {
    const response = await this.client.get(`/export/analysis/${symbol}`, {
      params: { format },
      responseType: format === 'csv' ? 'blob' : 'json'
    });
    return response.data;
  }

  // ========================================================================
  // Data Collector Endpoints
  // ========================================================================

  /**
   * Get data collector status
   */
  async getCollectorStatus(): Promise<any> {
    const response = await this.client.get('/collector/status');
    return response.data;
  }

  /**
   * Trigger manual data collection
   */
  async triggerCollection(): Promise<any> {
    const response = await this.client.post('/collector/collect');
    return response.data;
  }

  // ========================================================================
  // Backtest Endpoints
  // ========================================================================

  /**
   * Run a new backtest
   */
  async runBacktest(config: {
    name?: string;
    symbols?: string[] | null;
    start_date: string;
    end_date: string;
    frequency?: string;
    include_narrative?: boolean;
  }): Promise<any> {
    const response = await this.client.post('/backtest/run', {
      name: config.name,
      symbols: config.symbols,
      start_date: config.start_date,
      end_date: config.end_date,
      frequency: config.frequency || 'monthly',
      include_narrative: config.include_narrative || false
    });
    return response.data;
  }

  /**
   * Re-run a previous backtest with saved configuration
   */
  async rerunBacktest(runId: string, updateDates: boolean = true): Promise<any> {
    const response = await this.client.post(`/backtest/rerun/${runId}`, null, {
      params: { update_dates: updateDates }
    });
    return response.data;
  }

  /**
   * List all backtest runs
   */
  async getBacktestRuns(params?: {
    limit?: number;
    offset?: number;
    sort_by?: string;
    order?: string;
  }): Promise<any> {
    const response = await this.client.get('/backtest/runs', { params });
    return response.data;
  }

  /**
   * Get detailed results for a specific backtest run
   */
  async getBacktestResults(
    runId: string,
    includeEquityCurve: boolean = true,
    includeSignals: boolean = true
  ): Promise<any> {
    const response = await this.client.get(`/backtest/results/${runId}`, {
      params: {
        include_equity_curve: includeEquityCurve,
        include_signals: includeSignals
      }
    });
    return response.data;
  }

  /**
   * Compare multiple backtest runs
   */
  async compareBacktests(runIds: string[]): Promise<any> {
    const response = await this.client.get('/backtest/comparison', {
      params: { run_ids: runIds.join(',') }
    });
    return response.data;
  }

  /**
   * Delete a backtest run
   */
  async deleteBacktest(runId: string): Promise<any> {
    const response = await this.client.delete(`/backtest/results/${runId}`);
    return response.data;
  }

  /**
   * Get backtest analysis
   */
  async getBacktestAnalysis(runId: string): Promise<any> {
    const response = await this.client.get(`/backtest/analysis/${runId}`);
    return response.data;
  }

  // ========================================================================
  // Direct Client Access (for hooks)
  // ========================================================================

  /**
   * Get direct access to axios client for advanced usage
   */
  get axios() {
    return this.client;
  }

  /**
   * Make a GET request (for hooks)
   */
  async get(url: string, config?: any): Promise<any> {
    return this.client.get(url, config);
  }

  /**
   * Make a POST request (for hooks)
   */
  async post(url: string, data?: any, config?: any): Promise<any> {
    return this.client.post(url, data, config);
  }

  /**
   * Make a DELETE request (for hooks)
   */
  async delete(url: string, config?: any): Promise<any> {
    return this.client.delete(url, config);
  }

  /**
   * Make a PUT request (for hooks)
   */
  async put(url: string, data?: any, config?: any): Promise<any> {
    return this.client.put(url, data, config);
  }
}

// Singleton instance
export const api = new APIClient();

// Export for direct use
export default api;
