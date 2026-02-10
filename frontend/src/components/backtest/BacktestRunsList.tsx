import { useState } from 'react';
import { Eye, Trash2, RefreshCw, Calendar, TrendingUp, TrendingDown, Clock } from 'lucide-react';
import Card from '@/components/ui/Card';
import type { BacktestRun } from '@/types';

interface BacktestRunsListProps {
  runs: BacktestRun[];
  onViewResults: (runId: string) => void;
  onDelete: (runId: string) => void;
  onRefresh: () => void;
}

export default function BacktestRunsList({
  runs,
  onViewResults,
  onDelete,
  onRefresh
}: BacktestRunsListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (runId: string, name: string) => {
    if (confirm(`Delete backtest "${name}"? This action cannot be undone.`)) {
      setDeletingId(runId);
      try {
        await onDelete(runId);
      } finally {
        setDeletingId(null);
      }
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  const getStatusBadge = (status: BacktestRun['status']) => {
    const styles = {
      completed: 'bg-green-100 text-green-800',
      running: 'bg-blue-100 text-blue-800',
      failed: 'bg-red-100 text-red-800'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">
          Backtest History
        </h2>
        <button
          onClick={onRefresh}
          className="btn-secondary text-sm"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Runs List */}
      <div className="space-y-3">
        {runs.map((run) => (
          <Card key={run.run_id} className="hover:shadow-md transition-shadow">
            <div className="p-5">
              <div className="flex items-start justify-between">
                {/* Left: Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {run.name}
                    </h3>
                    {getStatusBadge(run.status)}
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      <span>
                        {formatDate(run.config.start_date)} → {formatDate(run.config.end_date)}
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      <span>
                        {run.config.frequency ? (run.config.frequency.charAt(0).toUpperCase() + run.config.frequency.slice(1)) : 'Monthly'} rebalance
                      </span>
                    </div>

                    {run.config.symbols === null ? (
                      <span className="text-blue-600 font-medium">NIFTY 50</span>
                    ) : (
                      <span className="text-blue-600 font-medium">
                        {run.config.symbols?.length || 0} stocks
                      </span>
                    )}
                  </div>

                  {/* Metrics Preview (if completed) */}
                  {run.status === 'completed' && run.metrics && (
                    <div className="mt-3 grid grid-cols-4 gap-4">
                      <div>
                        <p className="text-xs text-gray-500">Total Signals</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {run.metrics.total_signals}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Avg 3M Return</p>
                        <p className={`text-lg font-semibold ${run.metrics.avg_return_3m >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {run.metrics.avg_return_3m >= 0 ? <TrendingUp className="h-4 w-4 inline mr-1" /> : <TrendingDown className="h-4 w-4 inline mr-1" />}
                          {run.metrics.avg_return_3m.toFixed(2)}%
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">3M Hit Rate</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {run.metrics.hit_rate_3m.toFixed(1)}%
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Sharpe Ratio</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {run.metrics.sharpe_ratio_3m.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Footer info */}
                  <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                    <span>Created: {formatDate(run.created_at)}</span>
                    {run.completed_at && (
                      <span>Completed: {formatDate(run.completed_at)}</span>
                    )}
                    {run.duration_seconds && (
                      <span>Duration: {formatDuration(run.duration_seconds)}</span>
                    )}
                  </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2 ml-4">
                  {run.status === 'completed' && (
                    <button
                      onClick={() => onViewResults(run.run_id)}
                      className="btn-primary text-sm"
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      View Results
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(run.run_id, run.name)}
                    disabled={deletingId === run.run_id}
                    className="btn-secondary text-sm text-red-600 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {runs.length === 0 && (
        <Card>
          <div className="text-center py-8 text-gray-600">
            No backtest runs found
          </div>
        </Card>
      )}
    </div>
  );
}
