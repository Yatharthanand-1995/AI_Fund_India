/**
 * TypeScript type definitions for backtest system
 */

export interface BacktestConfig {
  name: string;
  symbols: string[] | null; // null = use default NIFTY 50
  start_date: string;
  end_date: string;
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  benchmark?: string;
}

export interface BacktestRun {
  run_id: string;
  name: string;
  start_date: string;
  end_date: string;
  symbols: string[];
  frequency: string;
  created_at: string;
  total_signals: number;
  summary: BacktestSummary;
  metadata?: {
    config?: BacktestConfig;
    duration_seconds?: number;
  };
}

export interface BacktestSummary {
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
  performance_by_recommendation: {
    [key: string]: {
      count: number;
      avg_return_3m: number;
      avg_alpha_3m: number;
      hit_rate_3m: number;
    };
  };
  agent_correlations: {
    fundamentals: number;
    momentum: number;
    quality: number;
    sentiment: number;
    institutional_flow: number;
  };
  performance_by_regime?: {
    [key: string]: any;
  };
}

export interface BacktestSignal {
  signal_id: number;
  symbol: string;
  date: string;
  recommendation: string;
  composite_score: number;
  confidence: number;
  entry_price: number;
  exit_price: number | null;
  forward_return_1m: number | null;
  forward_return_3m: number | null;
  forward_return_6m: number | null;
  benchmark_return_1m: number | null;
  benchmark_return_3m: number | null;
  benchmark_return_6m: number | null;
  alpha_1m: number | null;
  alpha_3m: number | null;
  alpha_6m: number | null;
  agent_scores: {
    fundamentals: number;
    momentum: number;
    quality: number;
    sentiment: number;
    institutional_flow: number;
  };
  market_regime: string | null;
}

export interface EquityCurveData {
  dates: string[];
  portfolio_value: number[];
  benchmark_value: number[];
  cumulative_return: number[];
  benchmark_return: number[];
  alpha: number[];
  drawdown: number[];
}

export interface BacktestResultsData {
  run_id: string;
  name: string;
  start_date: string;
  end_date: string;
  symbols: string[];
  frequency: string;
  created_at: string;
  total_signals: number;
  summary: BacktestSummary;
  config?: BacktestConfig;
  equity_curve?: EquityCurveData;
  signals?: BacktestSignal[];
  timestamp: string;
}

export interface BacktestRunResponse {
  success: boolean;
  run_id: string;
  name: string;
  total_signals: number;
  summary: {
    hit_rate_3m: number;
    avg_alpha_3m: number;
    sharpe_ratio_3m: number;
    total_return: number;
    annualized_return: number;
  };
  config: BacktestConfig;
  duration_seconds: number;
  timestamp: string;
}

export interface BacktestComparisonResponse {
  runs: Array<{
    run_id: string;
    name: string;
    start_date: string;
    end_date: string;
    frequency: string;
    total_signals: number;
    summary: BacktestSummary;
    equity_curve: EquityCurveData | null;
  }>;
  total_compared: number;
  comparison: {
    best_sharpe: {
      run_id: string;
      name: string;
      value: number;
    };
    best_return: {
      run_id: string;
      name: string;
      value: number;
    };
    best_alpha: {
      run_id: string;
      name: string;
      value: number;
    };
    lowest_drawdown: {
      run_id: string;
      name: string;
      value: number;
    };
  };
  timestamp: string;
}
