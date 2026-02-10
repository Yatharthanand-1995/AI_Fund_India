import { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp, TrendingDown, Award, AlertTriangle, BarChart3, LineChart } from 'lucide-react';
import Card from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';
import EquityCurveChart from './EquityCurveChart';
import DrawdownChart from './DrawdownChart';
import AgentAttributionChart from './AgentAttributionChart';
import BacktestSignalsTable from './BacktestSignalsTable';
import api from '@/lib/api';
import { useStore } from '@/store/useStore';
import type { BacktestResults as BacktestResultsType, BacktestAnalysis } from '@/types';

interface BacktestResultsProps {
  runId: string;
  onBack: () => void;
}

export default function BacktestResults({ runId, onBack }: BacktestResultsProps) {
  const { addToast } = useStore();
  const [results, setResults] = useState<BacktestResultsType | null>(null);
  const [analysis, setAnalysis] = useState<BacktestAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'signals' | 'analysis'>('overview');

  useEffect(() => {
    loadResults();
  }, [runId]);

  const loadResults = async () => {
    try {
      setIsLoading(true);

      // Load results and analysis in parallel
      const [resultsData, analysisData] = await Promise.all([
        api.getBacktestResults(runId, true, true),
        api.getBacktestAnalysis(runId).catch(() => null) // Analysis might not be available
      ]);

      setResults(resultsData);
      setAnalysis(analysisData);
    } catch (error) {
      console.error('Failed to load backtest results:', error);
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load backtest results'
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <Loading size="lg" text="Loading backtest results..." />
      </div>
    );
  }

  if (!results) {
    return (
      <Card>
        <div className="text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Failed to Load Results
          </h3>
          <p className="text-gray-600 mb-6">
            Could not load backtest results. The run may have failed or been deleted.
          </p>
          <button onClick={onBack} className="btn-primary">
            Back to History
          </button>
        </div>
      </Card>
    );
  }

  const { run, metrics } = results;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="btn-secondary"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {run.name}
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              {run.config.start_date} → {run.config.end_date} • {run.config.frequency} rebalance
            </p>
          </div>
        </div>
      </div>

      {/* Key Metrics Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="p-4">
            <p className="text-sm text-gray-600 mb-1">Total Signals</p>
            <p className="text-2xl font-bold text-gray-900">{metrics.total_signals}</p>
            <p className="text-xs text-gray-500 mt-1">
              {metrics.total_buys} BUY • {metrics.total_sells} SELL
            </p>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <p className="text-sm text-gray-600 mb-1">Avg 3M Return</p>
            <p className={`text-2xl font-bold ${metrics.avg_return_3m >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {metrics.avg_return_3m >= 0 ? <TrendingUp className="h-5 w-5 inline mr-1" /> : <TrendingDown className="h-5 w-5 inline mr-1" />}
              {metrics.avg_return_3m.toFixed(2)}%
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Alpha: {metrics.avg_alpha_3m >= 0 ? '+' : ''}{metrics.avg_alpha_3m.toFixed(2)}%
            </p>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <p className="text-sm text-gray-600 mb-1">3M Hit Rate</p>
            <p className="text-2xl font-bold text-gray-900">
              {metrics.hit_rate_3m.toFixed(1)}%
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Outperformed benchmark
            </p>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <p className="text-sm text-gray-600 mb-1">Sharpe Ratio (3M)</p>
            <p className="text-2xl font-bold text-gray-900">
              {metrics.sharpe_ratio_3m.toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Risk-adjusted return
            </p>
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <LineChart className="h-4 w-4" />
            Overview
          </button>
          <button
            onClick={() => setActiveTab('signals')}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${activeTab === 'signals'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <BarChart3 className="h-4 w-4" />
            Signals ({results.signals?.length || 0})
          </button>
          {analysis && (
            <button
              onClick={() => setActiveTab('analysis')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
                ${activeTab === 'analysis'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <Award className="h-4 w-4" />
              Agent Analysis
            </button>
          )}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Equity Curve */}
          {results.equity_curve && results.equity_curve.length > 0 && (
            <Card>
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Equity Curve
                </h2>
                <EquityCurveChart data={results.equity_curve} />
              </div>
            </Card>
          )}

          {/* Performance Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Returns by Period */}
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Returns by Period
                </h3>
                <div className="space-y-3">
                  {[
                    { period: '1 Month', return: metrics.avg_return_1m, alpha: metrics.avg_alpha_1m, hitRate: metrics.hit_rate_1m },
                    { period: '3 Months', return: metrics.avg_return_3m, alpha: metrics.avg_alpha_3m, hitRate: metrics.hit_rate_3m },
                    { period: '6 Months', return: metrics.avg_return_6m, alpha: metrics.avg_alpha_6m, hitRate: metrics.hit_rate_6m }
                  ].map(({ period, return: ret, alpha, hitRate }) => (
                    <div key={period} className="flex items-center justify-between py-2 border-b last:border-0">
                      <span className="text-sm font-medium text-gray-700">{period}</span>
                      <div className="text-right">
                        <p className={`text-sm font-semibold ${ret >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {ret >= 0 ? '+' : ''}{ret.toFixed(2)}%
                        </p>
                        <p className="text-xs text-gray-500">
                          Alpha: {alpha >= 0 ? '+' : ''}{alpha.toFixed(2)}% • Hit: {hitRate.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            {/* Risk Metrics */}
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Risk Metrics
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-sm font-medium text-gray-700">Max Drawdown</span>
                    <span className="text-sm font-semibold text-red-600">
                      -{metrics.max_drawdown.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-sm font-medium text-gray-700">Win Rate</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {metrics.win_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-sm font-medium text-gray-700">Avg Win</span>
                    <span className="text-sm font-semibold text-green-600">
                      +{metrics.avg_win.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-sm font-medium text-gray-700">Avg Loss</span>
                    <span className="text-sm font-semibold text-red-600">
                      -{metrics.avg_loss.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm font-medium text-gray-700">Win/Loss Ratio</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {metrics.win_loss_ratio.toFixed(2)}x
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Drawdown Chart */}
          {results.equity_curve && results.equity_curve.length > 0 && (
            <Card>
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Drawdown Analysis
                </h2>
                <DrawdownChart data={results.equity_curve} />
              </div>
            </Card>
          )}
        </div>
      )}

      {activeTab === 'signals' && (
        <BacktestSignalsTable signals={results.signals || []} />
      )}

      {activeTab === 'analysis' && analysis && (
        <div className="space-y-6">
          {/* Agent Attribution */}
          <Card>
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Agent Performance Attribution
              </h2>
              <AgentAttributionChart data={analysis.agent_performance} />
            </div>
          </Card>

          {/* Optimal Weights */}
          <Card>
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Optimal Weight Recommendations
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                {analysis.optimal_weights.methodology}
              </p>

              <div className="space-y-3">
                {Object.entries(analysis.optimal_weights.weights).map(([agent, weight]) => {
                  const current = analysis.agent_performance.find(a => a.agent_name === agent);
                  const change = weight - (current?.current_weight || 0);

                  return (
                    <div key={agent} className="flex items-center justify-between py-2 border-b">
                      <span className="text-sm font-medium text-gray-700 capitalize">
                        {agent.replace('_', ' ')}
                      </span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-gray-500">
                          Current: {((current?.current_weight || 0) * 100).toFixed(1)}%
                        </span>
                        <span className="text-sm font-semibold text-gray-900">
                          → {(weight * 100).toFixed(1)}%
                        </span>
                        <span className={`text-xs ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ({change >= 0 ? '+' : ''}{(change * 100).toFixed(1)}%)
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {analysis.optimal_weights.expected_improvement > 0.1 && (
                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-900">
                    <strong>Expected Improvement:</strong> Sharpe ratio could improve by{' '}
                    {analysis.optimal_weights.expected_improvement.toFixed(2)} using these weights.
                  </p>
                </div>
              )}
            </div>
          </Card>

          {/* Recommendations */}
          {analysis.recommendations.length > 0 && (
            <Card>
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Actionable Recommendations
                </h2>
                <ul className="space-y-2">
                  {analysis.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-blue-600 font-bold mt-0.5">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
