// API Response Types

// ============================================================================
// Agent Metrics Interfaces (replacing Record<string, any>)
// ============================================================================

export interface FundamentalsMetrics {
  roe?: number;
  roa?: number;
  profit_margin?: number;
  operating_margin?: number;
  gross_margin?: number;
  revenue_growth?: number;
  earnings_growth?: number;
  pe_ratio?: number;
  pb_ratio?: number;
  peg_ratio?: number;
  debt_to_equity?: number;
  current_ratio?: number;
  quick_ratio?: number;
  free_cash_flow?: number;
  fcf_yield?: number;
  dividend_yield?: number;
  market_cap?: number;
  book_value?: number;
  sector?: string;
  industry?: string;
  promoter_holding?: number;
}

export interface MomentumMetrics {
  current_price?: number;
  '1m_return'?: number;
  '3m_return'?: number;
  '6m_return'?: number;
  '1y_return'?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  sma_20?: number;
  sma_50?: number;
  sma_200?: number;
  ema_12?: number;
  ema_26?: number;
  trend?: string;
  price_vs_sma20?: number;
  price_vs_sma50?: number;
  relative_strength?: number;
  nifty_3m_return?: number;
  volatility?: number;
  avg_volume?: number;
  recent_volume_ratio?: number;
  volume_trend?: string;
}

export interface QualityMetrics {
  sector?: string;
  market_cap?: number;
  volatility?: number;
  '1y_return'?: number;
  '6m_return'?: number;
  max_drawdown?: number;
  current_drawdown?: number;
  return_consistency?: number;
  price_range_52w?: number;
}

export interface SentimentMetrics {
  recommendation_mean?: number;
  recommendation_key?: string;
  target_mean_price?: number;
  target_high_price?: number;
  target_low_price?: number;
  current_price?: number;
  upside_percent?: number;
  number_of_analyst_opinions?: number;
  recommendation_trend?: any;
}

export interface InstitutionalFlowMetrics {
  obv_trend?: number;
  obv_current?: number;
  mfi?: number;
  cmf?: number | null;
  volume_zscore?: number;
  vwap?: number;
  price_vs_vwap?: number;
  vwap_position?: string;
  volume_trend?: number;
  pv_divergence?: string;
}

// Base AgentScore with generic metrics
export interface AgentScore<T = any> {
  score: number;
  confidence: number;
  reasoning: string;
  metrics: T;
  breakdown: Record<string, number>;
}

// Specific agent score types
export interface FundamentalsScore extends AgentScore<FundamentalsMetrics> {}
export interface MomentumScore extends AgentScore<MomentumMetrics> {}
export interface QualityScore extends AgentScore<QualityMetrics> {}
export interface SentimentScore extends AgentScore<SentimentMetrics> {}
export interface InstitutionalFlowScore extends AgentScore<InstitutionalFlowMetrics> {}

export interface Narrative {
  investment_thesis: string;
  key_strengths: string[];
  key_risks: string[];
  summary: string;
  provider: string;
}

export interface MarketRegimeMetrics {
  current_price?: number;
  sma_50?: number;
  sma_200?: number;
  price_vs_sma50_pct?: number;
  sma50_vs_sma200_pct?: number;
  volatility_pct?: number;
  volatility_trend?: string;
  volatility_window_days?: number;
}

export interface MarketRegime {
  regime: string;
  trend: 'BULL' | 'BEAR' | 'SIDEWAYS';
  volatility: 'HIGH' | 'NORMAL' | 'LOW';
  weights: Record<string, number>;
  metrics: MarketRegimeMetrics;
  timestamp: string;
  cached?: boolean;
}

export interface AgentScores {
  fundamentals?: FundamentalsScore;
  momentum?: MomentumScore;
  quality?: QualityScore;
  sentiment?: SentimentScore;
  institutional_flow?: InstitutionalFlowScore;
  // Index signature for dynamic access (e.g., agent_scores[key])
  [key: string]: AgentScore<any> | undefined;
}

export interface StockAnalysis {
  symbol: string;
  composite_score: number;
  recommendation: string;
  confidence: number;
  agent_scores: AgentScores;
  weights: Record<string, number>;
  market_regime?: MarketRegime;
  narrative?: Narrative;
  timestamp: string;
  cached?: boolean;
}

export interface BatchAnalysisResponse {
  total_analyzed: number;
  successful: number;
  failed: number;
  results: StockAnalysis[];
  timestamp: string;
  duration_seconds: number;
}

export interface TopPicksResponse {
  market_regime: MarketRegime;
  top_picks: StockAnalysis[];
  total_analyzed: number;
  timestamp: string;
  duration_seconds: number;
}

export interface HealthComponent {
  status: 'healthy' | 'unhealthy' | 'degraded' | 'disabled';
  [key: string]: any;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  components: Record<string, HealthComponent>;
  version: string;
}

export interface StockUniverseResponse {
  total_stocks: number;
  indices: Record<string, string[]>;
  timestamp: string;
}

// Request Types

export interface AnalyzeRequest {
  symbol: string;
  include_narrative?: boolean;
}

export interface BatchAnalyzeRequest {
  symbols: string[];
  include_narrative?: boolean;
  sort_by?: 'score' | 'confidence' | 'symbol';
}

// UI State Types

export type RecommendationType =
  | 'STRONG BUY'
  | 'BUY'
  | 'WEAK BUY'
  | 'HOLD'
  | 'WEAK SELL'
  | 'SELL';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  duration?: number;
}

// Backtest Types

export interface BacktestConfig {
  name?: string;
  symbols?: string[] | null;
  start_date: string;
  end_date: string;
  frequency?: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  include_narrative?: boolean;
}

export interface BacktestMetrics {
  total_signals: number;
  total_buys: number;
  total_sells: number;
  hit_rate_1m: number;
  hit_rate_3m: number;
  hit_rate_6m: number;
  avg_return_1m: number;
  avg_return_3m: number;
  avg_return_6m: number;
  avg_alpha_1m: number;
  avg_alpha_3m: number;
  avg_alpha_6m: number;
  sharpe_ratio_1m: number;
  sharpe_ratio_3m: number;
  sharpe_ratio_6m: number;
  max_drawdown: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  win_loss_ratio: number;
}

export interface BacktestSignal {
  symbol: string;
  date: string;
  recommendation: string;
  composite_score: number;
  confidence: number;
  entry_price: number;
  forward_return_1m?: number;
  forward_return_3m?: number;
  forward_return_6m?: number;
  alpha_1m?: number;
  alpha_3m?: number;
  alpha_6m?: number;
  agent_scores: Record<string, number>;
}

export interface BacktestRun {
  run_id: string;
  name: string;
  config: BacktestConfig;
  status: 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  duration_seconds?: number;
  metrics?: BacktestMetrics;
  total_signals?: number;
}

export interface RecommendationPerformance {
  count: number;
  avg_return: number;
  total_return: number;
  win_rate: number;
}

export interface BacktestResults {
  run: BacktestRun;
  metrics: BacktestMetrics;
  equity_curve?: Array<{ date: string; value: number; benchmark_value: number }>;
  signals?: BacktestSignal[];
  performance_by_recommendation?: Record<string, RecommendationPerformance>;
}

export interface BacktestAnalysis {
  run_id: string;
  agent_performance: Array<{
    agent_name: string;
    correlation_with_returns: number;
    avg_score: number;
    current_weight: number;
    optimal_weight: number;
    weight_change: number;
    predictive_power: string;
  }>;
  optimal_weights: {
    weights: Record<string, number>;
    expected_improvement: number;
    current_sharpe: number;
    optimal_sharpe: number;
    methodology: string;
  };
  recommendations: string[];
}
