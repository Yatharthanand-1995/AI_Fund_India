import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Play, History, TrendingUp, AlertCircle } from 'lucide-react';
import BacktestConfigForm from '@/components/backtest/BacktestConfigForm';
import BacktestRunsList from '@/components/backtest/BacktestRunsList';
import BacktestResults from '@/components/backtest/BacktestResults';
import Loading from '@/components/ui/Loading';
import Card from '@/components/ui/Card';
import api from '@/lib/api';
import { useStore } from '@/store/useStore';
import type { BacktestRun } from '@/types';

type ViewMode = 'new' | 'history' | 'results';

export default function Backtest() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { addToast } = useStore();

  const [viewMode, setViewMode] = useState<ViewMode>('new');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);

  // Handle URL parameters for deep linking
  useEffect(() => {
    const runId = searchParams.get('run_id');
    const view = searchParams.get('view') as ViewMode;

    if (runId) {
      setSelectedRunId(runId);
      setViewMode('results');
    } else if (view) {
      setViewMode(view);
    }
  }, [searchParams]);

  // Load backtest runs when switching to history view
  useEffect(() => {
    if (viewMode === 'history') {
      loadBacktestRuns();
    }
  }, [viewMode]);

  const loadBacktestRuns = async () => {
    try {
      setIsLoadingRuns(true);
      const data = await api.getBacktestRuns({ limit: 50, sort_by: 'created_at', order: 'desc' });
      setRuns(data.runs || []);
    } catch (error) {
      console.error('Failed to load backtest runs:', error);
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load backtest runs'
      });
    } finally {
      setIsLoadingRuns(false);
    }
  };

  const handleRunBacktest = async (config: any) => {
    try {
      setIsRunning(true);
      addToast({ type: 'info', message: 'Starting backtest... This may take a few minutes.' });

      const result = await api.runBacktest(config);

      addToast({
        type: 'success',
        message: `Backtest completed! Analyzed ${result.metrics.total_signals} signals.`
      });

      // Switch to results view
      setSelectedRunId(result.run_id);
      setViewMode('results');
      setSearchParams({ run_id: result.run_id, view: 'results' });

      // Refresh runs list
      loadBacktestRuns();
    } catch (error) {
      console.error('Backtest failed:', error);
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to run backtest'
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleViewResults = (runId: string) => {
    setSelectedRunId(runId);
    setViewMode('results');
    setSearchParams({ run_id: runId, view: 'results' });
  };

  const handleDeleteRun = async (runId: string) => {
    try {
      await api.deleteBacktest(runId);
      addToast({ type: 'success', message: 'Backtest deleted successfully' });
      loadBacktestRuns();

      // If viewing deleted run, go back to history
      if (selectedRunId === runId) {
        setSelectedRunId(null);
        setViewMode('history');
        setSearchParams({ view: 'history' });
      }
    } catch (error) {
      console.error('Failed to delete backtest:', error);
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to delete backtest'
      });
    }
  };

  const handleBackToHistory = () => {
    setSelectedRunId(null);
    setViewMode('history');
    setSearchParams({ view: 'history' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <TrendingUp className="h-8 w-8 text-blue-600" />
            Strategy Backtesting
          </h1>
          <p className="mt-2 text-gray-600">
            Validate AI recommendations using historical data and measure performance
          </p>
        </div>
      </div>

      {/* View Mode Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => {
              setViewMode('new');
              setSearchParams({ view: 'new' });
            }}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${viewMode === 'new'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <Play className="h-4 w-4" />
            New Backtest
          </button>
          <button
            onClick={() => {
              setViewMode('history');
              setSearchParams({ view: 'history' });
            }}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${viewMode === 'history'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <History className="h-4 w-4" />
            Previous Runs
            {runs.length > 0 && (
              <span className="ml-1 bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full text-xs">
                {runs.length}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Content Area */}
      <div className="mt-6">
        {viewMode === 'new' && (
          <div className="max-w-3xl">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Configure Backtest
                </h2>
                <p className="text-gray-600 mb-6">
                  Test your AI strategy on historical data to validate performance and identify optimal settings.
                </p>

                {isRunning ? (
                  <div className="text-center py-12">
                    <Loading size="lg" text="Running backtest... This may take several minutes." />
                    <p className="mt-4 text-sm text-gray-600">
                      Analyzing historical data and calculating forward returns
                    </p>
                  </div>
                ) : (
                  <BacktestConfigForm onSubmit={handleRunBacktest} />
                )}
              </div>
            </Card>

            {/* Info Panel */}
            <Card className="mt-6 bg-blue-50 border-blue-200">
              <div className="p-4">
                <div className="flex gap-3">
                  <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-blue-900 mb-2">
                      How Backtesting Works
                    </h3>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• Analyzes stocks at historical points using only data available then (no look-ahead bias)</li>
                      <li>• Calculates forward returns (1M, 3M, 6M) and compares to NIFTY 50 benchmark</li>
                      <li>• Measures alpha (excess return), hit rate, Sharpe ratio, and other key metrics</li>
                      <li>• Identifies which agents have the strongest predictive power</li>
                    </ul>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {viewMode === 'history' && (
          <div>
            {isLoadingRuns ? (
              <div className="text-center py-12">
                <Loading size="lg" text="Loading backtest runs..." />
              </div>
            ) : runs.length === 0 ? (
              <Card>
                <div className="text-center py-12">
                  <History className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No Backtest Runs Yet
                  </h3>
                  <p className="text-gray-600 mb-6">
                    Run your first backtest to validate the AI strategy on historical data
                  </p>
                  <button
                    onClick={() => {
                      setViewMode('new');
                      setSearchParams({ view: 'new' });
                    }}
                    className="btn-primary"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Run First Backtest
                  </button>
                </div>
              </Card>
            ) : (
              <BacktestRunsList
                runs={runs}
                onViewResults={handleViewResults}
                onDelete={handleDeleteRun}
                onRefresh={loadBacktestRuns}
              />
            )}
          </div>
        )}

        {viewMode === 'results' && selectedRunId && (
          <BacktestResults
            runId={selectedRunId}
            onBack={handleBackToHistory}
          />
        )}
      </div>
    </div>
  );
}
