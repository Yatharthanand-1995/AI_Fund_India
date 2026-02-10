import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, AlertCircle, Activity, Database, Cloud, Zap } from 'lucide-react';
import Card from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

interface ComponentStatus {
  status: 'healthy' | 'unhealthy' | 'degraded' | 'disabled';
  [key: string]: any;
}

interface HealthData {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  components: Record<string, ComponentStatus>;
  version: string;
}

export default function HealthMonitor() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Failed to load health:', error);
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'disabled':
        return <XCircle className="h-5 w-5 text-gray-400" />;
      default:
        return <Activity className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'degraded':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'unhealthy':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'disabled':
        return 'bg-gray-50 border-gray-200 text-gray-600';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const getComponentIcon = (componentName: string) => {
    if (componentName.includes('provider')) return <Database className="h-5 w-5" />;
    if (componentName.includes('scorer')) return <Zap className="h-5 w-5" />;
    if (componentName.includes('narrative')) return <Cloud className="h-5 w-5" />;
    return <Activity className="h-5 w-5" />;
  };

  if (loading) {
    return (
      <Card>
        <div className="p-6 text-center">
          <Activity className="h-8 w-8 text-gray-400 mx-auto mb-2 animate-pulse" />
          <p className="text-gray-600">Loading system health...</p>
        </div>
      </Card>
    );
  }

  if (!health) {
    return (
      <Card>
        <div className="p-6 text-center">
          <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <p className="text-gray-600">Failed to load system health</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">System Status</h2>
            <div className={cn('px-4 py-2 rounded-lg border-2 font-bold', getStatusColor(health.status))}>
              <div className="flex items-center gap-2">
                {getStatusIcon(health.status)}
                <span className="uppercase">{health.status}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Version</p>
              <p className="font-semibold text-gray-900">{health.version}</p>
            </div>
            <div>
              <p className="text-gray-600">Last Checked</p>
              <p className="font-semibold text-gray-900">
                {lastUpdate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Auto-refresh</p>
              <p className="font-semibold text-gray-900">Every 30 seconds</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Components Status */}
      <Card>
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Component Health</h2>
          <div className="space-y-3">
            {Object.entries(health.components).map(([name, component]) => (
              <div
                key={name}
                className={cn(
                  'p-4 rounded-lg border-2 transition-all',
                  getStatusColor(component.status)
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    {getComponentIcon(name)}
                    <div>
                      <h3 className="font-semibold capitalize">
                        {name.replace(/_/g, ' ')}
                      </h3>

                      {/* Component-specific details */}
                      {name === 'data_provider' && (
                        <div className="mt-2 space-y-1 text-xs">
                          <p>NSE Provider: <span className="font-semibold">{component.nse_provider || 'N/A'}</span></p>
                          <p>Yahoo Provider: <span className="font-semibold">{component.yahoo_provider || 'N/A'}</span></p>
                          <p>Preferred: <span className="font-semibold">{component.prefer_provider || 'N/A'}</span></p>
                          <p>Data Available: <span className="font-semibold">{component.data_available ? 'Yes' : 'No'}</span></p>
                        </div>
                      )}

                      {name === 'stock_scorer' && (
                        <div className="mt-2 space-y-1 text-xs">
                          <p>Agents: <span className="font-semibold">{component.agents || 'N/A'}</span></p>
                          <p>Adaptive Weights: <span className="font-semibold">{component.adaptive_weights ? 'Enabled' : 'Disabled'}</span></p>
                        </div>
                      )}

                      {name === 'narrative_engine' && (
                        <div className="mt-2 space-y-1 text-xs">
                          <p>Provider: <span className="font-semibold">{component.provider || 'N/A'}</span></p>
                          {component.model && <p>Model: <span className="font-semibold">{component.model}</span></p>}
                        </div>
                      )}

                      {name === 'historical_db' && (
                        <div className="mt-2 space-y-1 text-xs">
                          <p>Database: <span className="font-semibold">{component.database || 'N/A'}</span></p>
                          {component.total_records !== undefined && (
                            <p>Records: <span className="font-semibold">{component.total_records.toLocaleString()}</span></p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {getStatusIcon(component.status)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
