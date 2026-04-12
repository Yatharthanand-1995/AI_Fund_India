/**
 * API Client for AI Hedge Fund Backend
 *
 * Communicates with FastAPI backend at http://localhost:8010
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
  StockHistoryResponse,
  RegimeHistoryResponse,
  SystemAnalyticsResponse,
  SectorAnalysisResponse,
  AgentAnalyticsResponse,
  WatchlistResponse,
  CollectorStatus,
  AlertsResponse,
  Alert,
  BacktestResults,
  BacktestRunResult,
  BacktestRunsResponse,
  BacktestAnalysis,
  CompareStocksResponse,
  BacktestConfig,
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
        // Pass through AbortController / axios cancel errors unchanged so
        // callers can detect them via err.name === 'CanceledError' or axios.isCancel()
        if (axios.isCancel(error)) {
          throw error;
        }
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
  async getRoot(): Promise<{ service: string; version: string; status: string }> {
    const response = await this.client.get<{ service: string; version: string; status: string }>('/');
    return response.data;
  }

  // ========================================================================
  // Historical Data Endpoints
  // ========================================================================

  /**
   * Get historical analysis for a stock
   */
  async getStockHistory(symbol: string, days: number = 30, includePrice: boolean = true): Promise<StockHistoryResponse> {
    const response = await this.client.get<StockHistoryResponse>(`/history/stock/${symbol}`, {
      params: { days, include_price: includePrice }
    });
    return response.data;
  }

  /**
   * Get market regime history
   */
  async getRegimeHistory(days: number = 30): Promise<RegimeHistoryResponse> {
    const response = await this.client.get<RegimeHistoryResponse>('/history/regime', {
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
  async getSystemAnalytics(): Promise<SystemAnalyticsResponse> {
    const response = await this.client.get<SystemAnalyticsResponse>('/analytics/system');
    return response.data;
  }

  /**
   * Get sector analysis
   */
  async getSectorAnalysis(days: number = 7): Promise<SectorAnalysisResponse> {
    const response = await this.client.get<SectorAnalysisResponse>('/analytics/sectors', {
      params: { days }
    });
    return response.data;
  }

  /**
   * Get agent performance analytics
   */
  async getAgentAnalytics(): Promise<AgentAnalyticsResponse> {
    const response = await this.client.get<AgentAnalyticsResponse>('/analytics/agents');
    return response.data;
  }

  // ========================================================================
  // Watchlist Endpoints
  // ========================================================================

  /**
   * Get user's watchlist
   */
  async getWatchlist(): Promise<WatchlistResponse> {
    const response = await this.client.get<WatchlistResponse>('/watchlist');
    return response.data;
  }

  /**
   * Add stock to watchlist
   */
  async addToWatchlist(symbol: string, notes?: string): Promise<{ message: string; symbol: string }> {
    const response = await this.client.post<{ message: string; symbol: string }>('/watchlist', { symbol, notes });
    return response.data;
  }

  /**
   * Remove stock from watchlist
   */
  async removeFromWatchlist(symbol: string): Promise<{ message: string }> {
    const response = await this.client.delete<{ message: string }>(`/watchlist/${symbol}`);
    return response.data;
  }

  // ========================================================================
  // Comparison Endpoint
  // ========================================================================

  /**
   * Compare multiple stocks side-by-side
   */
  async compareStocks(symbols: string[], includeHistory: boolean = false): Promise<CompareStocksResponse> {
    const response = await this.client.post<CompareStocksResponse>('/compare', {
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
  async exportAnalysis(symbol: string, format: 'json' | 'csv' = 'json'): Promise<StockAnalysis | Blob> {
    const response = await this.client.get<StockAnalysis | Blob>(`/export/analysis/${symbol}`, {
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
  async getCollectorStatus(): Promise<CollectorStatus> {
    const response = await this.client.get<CollectorStatus>('/collector/status');
    return response.data;
  }

  /**
   * Trigger manual data collection
   */
  async triggerCollection(): Promise<{ message: string; status: string }> {
    const response = await this.client.post<{ message: string; status: string }>('/collector/collect');
    return response.data;
  }

  // ========================================================================
  // Alerts Endpoints
  // ========================================================================

  async getAlerts(unreadOnly = false, limit = 50): Promise<AlertsResponse> {
    const response = await this.client.get<AlertsResponse>('/alerts', {
      params: { unread_only: unreadOnly, limit },
    });
    return response.data;
  }

  async markAlertRead(alertId: number): Promise<Alert> {
    const response = await this.client.post<Alert>(`/alerts/${alertId}/read`);
    return response.data;
  }

  async markAllAlertsRead(): Promise<{ message: string; updated_count: number }> {
    const response = await this.client.post<{ message: string; updated_count: number }>('/alerts/read-all');
    return response.data;
  }

  // ========================================================================
  // Backtest Endpoints
  // ========================================================================

  /**
   * Run a new backtest
   */
  async runBacktest(config: BacktestConfig): Promise<BacktestRunResult> {
    const response = await this.client.post<BacktestRunResult>('/backtest/run', {
      name: config.name,
      symbols: config.symbols,
      start_date: config.start_date,
      end_date: config.end_date,
      frequency: config.frequency || 'monthly',
      include_narrative: config.include_narrative || false
    }, { timeout: 600000 }); // 10-minute timeout for backtests
    return response.data;
  }

  /**
   * Re-run a previous backtest with saved configuration
   */
  async rerunBacktest(runId: string, updateDates: boolean = true): Promise<BacktestRunResult> {
    const response = await this.client.post<BacktestRunResult>(`/backtest/rerun/${runId}`, null, {
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
  }): Promise<BacktestRunsResponse> {
    const response = await this.client.get<BacktestRunsResponse>('/backtest/runs', { params });
    return response.data;
  }

  /**
   * Get detailed results for a specific backtest run
   */
  async getBacktestResults(
    runId: string,
    includeEquityCurve: boolean = true,
    includeSignals: boolean = true
  ): Promise<BacktestResults> {
    const response = await this.client.get<BacktestResults>(`/backtest/results/${runId}`, {
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
  async compareBacktests(runIds: string[]): Promise<BacktestResults[]> {
    const response = await this.client.get<BacktestResults[]>('/backtest/comparison', {
      params: { run_ids: runIds.join(',') }
    });
    return response.data;
  }

  /**
   * Delete a backtest run
   */
  async deleteBacktest(runId: string): Promise<{ message: string }> {
    const response = await this.client.delete<{ message: string }>(`/backtest/results/${runId}`);
    return response.data;
  }

  /**
   * Get backtest analysis
   */
  async getBacktestAnalysis(runId: string): Promise<BacktestAnalysis> {
    const response = await this.client.get<BacktestAnalysis>(`/backtest/analysis/${runId}`);
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
