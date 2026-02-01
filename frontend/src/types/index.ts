// API Response Types

export interface AgentScore {
  score: number;
  confidence: number;
  reasoning: string;
  metrics: Record<string, any>;
  breakdown: Record<string, number>;
}

export interface Narrative {
  investment_thesis: string;
  key_strengths: string[];
  key_risks: string[];
  summary: string;
  provider: string;
}

export interface MarketRegime {
  regime: string;
  trend: 'BULL' | 'BEAR' | 'SIDEWAYS';
  volatility: 'HIGH' | 'NORMAL' | 'LOW';
  weights: Record<string, number>;
  metrics: Record<string, any>;
  timestamp: string;
  cached?: boolean;
}

export interface StockAnalysis {
  symbol: string;
  composite_score: number;
  recommendation: string;
  confidence: number;
  agent_scores: Record<string, AgentScore>;
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
