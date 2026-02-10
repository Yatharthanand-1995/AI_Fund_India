import { useEffect, useState } from 'react';
import { Activity, Zap, Database, TrendingUp } from 'lucide-react';
import Card from '@/components/ui/Card';
import api from '@/lib/api';

export default function PerformanceMetrics() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
    const interval = setInterval(loadAnalytics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const loadAnalytics = async () => {
    try {
      const data = await api.getSystemAnalytics();
      setAnalytics(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <div className="p-6 text-center">
          <Activity className="h-8 w-8 text-gray-400 mx-auto mb-2 animate-pulse" />
          <p className="text-gray-600">Loading performance metrics...</p>
        </div>
      </Card>
    );
  }

  if (!analytics) {
    return (
      <Card>
        <div className="p-6 text-center text-gray-600">
          Performance metrics not available
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Performance Overview */}
      <Card>
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5" />
            System Performance
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Uptime */}
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-green-600" />
                <p className="text-xs font-medium text-gray-600">Uptime</p>
              </div>
              <p className="text-2xl font-bold text-green-700">
                {analytics.uptime_seconds != null ? `${(analytics.uptime_seconds / 3600).toFixed(1)}h` : 'N/A'}
              </p>
            </div>

            {/* Total Requests */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-4 w-4 text-blue-600" />
                <p className="text-xs font-medium text-gray-600">Total Requests</p>
              </div>
              <p className="text-2xl font-bold text-blue-700">
                {analytics.total_requests?.toLocaleString() || 0}
              </p>
            </div>

            {/* Avg Response Time */}
            <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-purple-600" />
                <p className="text-xs font-medium text-gray-600">Avg Response</p>
              </div>
              <p className="text-2xl font-bold text-purple-700">
                {analytics.avg_response_time_ms != null ? `${analytics.avg_response_time_ms.toFixed(0)}ms` : 'N/A'}
              </p>
            </div>

            {/* Cache Hit Rate */}
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Database className="h-4 w-4 text-yellow-600" />
                <p className="text-xs font-medium text-gray-600">Cache Hit Rate</p>
              </div>
              <p className="text-2xl font-bold text-yellow-700">
                {analytics.cache_hit_rate ? `${(analytics.cache_hit_rate * 100).toFixed(1)}%` : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Agent Performance */}
      {analytics.agent_performance && Object.keys(analytics.agent_performance).length > 0 && (
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Agent Avg Response Times</h3>
            <div className="space-y-3">
              {Object.entries(analytics.agent_performance as Record<string, number>).map(([agent, avgMs]) => (
                <div key={agent} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium text-gray-900 capitalize">
                    {agent.replace(/_/g, ' ')}
                  </p>
                  <p className="text-lg font-bold text-gray-900">
                    {typeof avgMs === 'number' ? `${avgMs.toFixed(0)}ms` : 'N/A'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* API Endpoints Performance */}
      {analytics.endpoint_stats && (
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Endpoint Statistics</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Endpoint
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Requests
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Avg Time
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Success Rate
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(analytics.endpoint_stats as Record<string, any>).map(([endpoint, stats]: [string, any]) => (
                    <tr key={endpoint} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">
                        {endpoint}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {stats.count?.toLocaleString() || 0}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {stats.avg_time ? `${stats.avg_time.toFixed(0)}ms` : 'N/A'}
                      </td>
                      <td className="px-4 py-2 text-sm">
                        <span className={`font-semibold ${
                          (stats.success_rate || 0) > 0.95 ? 'text-green-600' :
                          (stats.success_rate || 0) > 0.8 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {stats.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : 'N/A'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
