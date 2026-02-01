/**
 * Analytics Page - System Dashboard
 *
 * Displays system performance metrics and analytics
 */

import React from 'react';
import { useSystemMetrics } from '../hooks/useSystemMetrics';
import { Activity, TrendingUp, AlertCircle, Database, Zap } from 'lucide-react';

const Analytics: React.FC = () => {
  const { metrics, loading, error, refetch, lastUpdated } = useSystemMetrics({
    autoRefresh: true,
    refreshInterval: 30000 // 30 seconds
  });

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-600">Failed to load analytics</p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Analytics</h1>
          <p className="text-gray-600 mt-1">
            Monitor system performance and health metrics
          </p>
        </div>
        {lastUpdated && (
          <p className="text-sm text-gray-500">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* KPI Cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Uptime */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Uptime</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.uptime_formatted}
                </p>
              </div>
              <Activity className="w-8 h-8 text-blue-500" />
            </div>
          </div>

          {/* Total Requests */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Requests</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.total_requests.toLocaleString()}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-500" />
            </div>
          </div>

          {/* Avg Response Time */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Response</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.avg_response_time_ms.toFixed(0)}ms
                </p>
              </div>
              <Zap className="w-8 h-8 text-yellow-500" />
            </div>
          </div>

          {/* Error Rate */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Error Rate</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.error_rate_formatted}
                </p>
              </div>
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
          </div>

          {/* Cache Hit Rate */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Cache Hit</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.cache_hit_rate_formatted}
                </p>
              </div>
              <Database className="w-8 h-8 text-purple-500" />
            </div>
          </div>
        </div>
      )}

      {/* Agent Performance Section */}
      {metrics && metrics.agent_performance && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Agent Performance
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {Object.entries(metrics.agent_performance).map(([agent, time]) => (
              <div key={agent} className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 capitalize mb-1">
                  {agent.replace('_', ' ')}
                </p>
                <p className="text-lg font-semibold text-gray-900">
                  {(time * 1000).toFixed(0)}ms
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Placeholder for Charts */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Performance Charts
        </h2>
        <p className="text-gray-500 text-center py-12">
          Charts will be added in the next phase
        </p>
      </div>
    </div>
  );
};

export default Analytics;
