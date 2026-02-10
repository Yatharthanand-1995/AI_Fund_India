import { useEffect, useState } from 'react';
import { Clock, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import Card from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

interface DataFreshnessProps {
  autoRefresh?: boolean;
}

export default function DataFreshnessIndicator({ autoRefresh = true }: DataFreshnessProps) {
  const [collectorStatus, setCollectorStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadStatus();
    if (autoRefresh) {
      const interval = setInterval(loadStatus, 60000); // Refresh every minute
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadStatus = async () => {
    try {
      const status = await api.getCollectorStatus();
      setCollectorStatus(status);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load collector status:', error);
      setLoading(false);
    }
  };

  const handleManualRefresh = async () => {
    setRefreshing(true);
    try {
      await api.triggerCollection();
      await loadStatus();
    } catch (error) {
      console.error('Failed to trigger collection:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const getDataAge = (timestamp?: string) => {
    if (!timestamp) return null;

    const now = new Date();
    const lastUpdate = new Date(timestamp);
    const diffMs = now.getTime() - lastUpdate.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return { value: diffDays, unit: 'day', isStale: diffDays > 1 };
    if (diffHours > 0) return { value: diffHours, unit: 'hour', isStale: diffHours > 6 };
    if (diffMins > 0) return { value: diffMins, unit: 'min', isStale: diffMins > 30 };
    return { value: 0, unit: 'just now', isStale: false };
  };

  if (loading) {
    return (
      <Card>
        <div className="p-6 text-center">
          <Clock className="h-8 w-8 text-gray-400 mx-auto mb-2 animate-pulse" />
          <p className="text-gray-600">Loading data freshness...</p>
        </div>
      </Card>
    );
  }

  const lastCollectionTime = collectorStatus?.last_collection_time;
  const dataAge = getDataAge(lastCollectionTime);
  const isRunning = collectorStatus?.is_running;
  const nextCollection = collectorStatus?.next_collection_time;

  return (
    <Card>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Data Freshness
          </h2>
          <button
            onClick={handleManualRefresh}
            disabled={refreshing || isRunning}
            className="btn-secondary text-sm disabled:opacity-50"
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', refreshing && 'animate-spin')} />
            {refreshing ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>

        {/* Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Last Update */}
          <div className={cn(
            'p-4 rounded-lg border-2',
            dataAge?.isStale ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200'
          )}>
            <div className="flex items-center gap-2 mb-2">
              {dataAge?.isStale ? (
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              ) : (
                <CheckCircle className="h-4 w-4 text-green-600" />
              )}
              <p className="text-xs font-medium text-gray-600">Last Updated</p>
            </div>
            {dataAge && dataAge.unit !== 'just now' ? (
              <p className={cn(
                'text-2xl font-bold',
                dataAge.isStale ? 'text-yellow-700' : 'text-green-700'
              )}>
                {dataAge.value} {dataAge.unit}{dataAge.value !== 1 ? 's' : ''} ago
              </p>
            ) : (
              <p className="text-2xl font-bold text-green-700">Just now</p>
            )}
          </div>

          {/* Collection Status */}
          <div className="p-4 rounded-lg border-2 bg-blue-50 border-blue-200">
            <p className="text-xs font-medium text-gray-600 mb-2">Collection Status</p>
            <p className="text-lg font-bold text-blue-700">
              {isRunning ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Running
                </span>
              ) : (
                'Idle'
              )}
            </p>
          </div>

          {/* Next Collection */}
          <div className="p-4 rounded-lg border-2 bg-gray-50 border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">Next Collection</p>
            <p className="text-lg font-bold text-gray-700">
              {nextCollection ? (
                new Date(nextCollection).toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit'
                })
              ) : (
                'Not scheduled'
              )}
            </p>
          </div>
        </div>

        {/* Collection Stats */}
        {collectorStatus?.stats && (
          <div className="pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Collection Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Total Collections</p>
                <p className="font-bold text-gray-900">
                  {collectorStatus.stats.total_collections?.toLocaleString() || 0}
                </p>
              </div>
              <div>
                <p className="text-gray-600">Success Rate</p>
                <p className="font-bold text-green-600">
                  {collectorStatus.stats.success_rate
                    ? `${(collectorStatus.stats.success_rate * 100).toFixed(1)}%`
                    : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-gray-600">Avg Duration</p>
                <p className="font-bold text-gray-900">
                  {collectorStatus.stats.avg_duration
                    ? `${collectorStatus.stats.avg_duration.toFixed(1)}s`
                    : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-gray-600">Last Error</p>
                <p className="font-bold text-gray-900">
                  {collectorStatus.stats.last_error || 'None'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Warning for stale data */}
        {dataAge?.isStale && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-900">Data May Be Stale</p>
                <p className="text-xs text-yellow-800 mt-1">
                  Data hasn't been updated in {dataAge.value} {dataAge.unit}{dataAge.value !== 1 ? 's' : ''}.
                  Consider triggering a manual refresh.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
