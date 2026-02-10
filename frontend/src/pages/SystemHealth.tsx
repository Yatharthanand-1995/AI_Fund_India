/**
 * System Health Dashboard
 *
 * Features:
 * - Real-time system health monitoring
 * - Data freshness indicators
 * - Performance metrics
 * - Component status tracking
 */

import { useState } from 'react';
import { Activity, Clock, BarChart3, Settings } from 'lucide-react';
import HealthMonitor from '@/components/system/HealthMonitor';
import DataFreshnessIndicator from '@/components/system/DataFreshnessIndicator';
import PerformanceMetrics from '@/components/system/PerformanceMetrics';
import Card from '@/components/ui/Card';

type TabView = 'health' | 'freshness' | 'performance' | 'settings';

export default function SystemHealth() {
  const [activeTab, setActiveTab] = useState<TabView>('health');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Activity className="h-8 w-8 text-blue-600" />
          System Health & Monitoring
        </h1>
        <p className="mt-2 text-gray-600">
          Monitor system status, data freshness, and performance metrics
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('health')}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${activeTab === 'health'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <Activity className="h-4 w-4" />
            System Health
          </button>
          <button
            onClick={() => setActiveTab('freshness')}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${activeTab === 'freshness'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <Clock className="h-4 w-4" />
            Data Freshness
          </button>
          <button
            onClick={() => setActiveTab('performance')}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${activeTab === 'performance'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <BarChart3 className="h-4 w-4" />
            Performance
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
              ${activeTab === 'settings'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <Settings className="h-4 w-4" />
            Settings
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'health' && <HealthMonitor />}

        {activeTab === 'freshness' && <DataFreshnessIndicator />}

        {activeTab === 'performance' && <PerformanceMetrics />}

        {activeTab === 'settings' && (
          <Card>
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                System Settings
              </h2>
              <p className="text-gray-600 mb-6">
                Configure system preferences and monitoring settings.
              </p>

              <div className="space-y-6">
                {/* Auto-refresh */}
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <h3 className="font-medium text-gray-900">Auto-refresh</h3>
                    <p className="text-sm text-gray-600">
                      Automatically refresh health data every 30 seconds
                    </p>
                  </div>
                  <div className="flex items-center">
                    <span className="text-sm text-gray-600 mr-3">Enabled</span>
                    <div className="w-11 h-6 bg-blue-600 rounded-full relative">
                      <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
                    </div>
                  </div>
                </div>

                {/* Notifications */}
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <h3 className="font-medium text-gray-900">Health Alerts</h3>
                    <p className="text-sm text-gray-600">
                      Show notifications when system health degrades
                    </p>
                  </div>
                  <div className="flex items-center">
                    <span className="text-sm text-gray-600 mr-3">Enabled</span>
                    <div className="w-11 h-6 bg-blue-600 rounded-full relative">
                      <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
                    </div>
                  </div>
                </div>

                {/* Data freshness threshold */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-medium text-gray-900 mb-2">Data Staleness Threshold</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Show warning when data is older than this threshold
                  </p>
                  <select className="input text-sm w-full md:w-auto">
                    <option>15 minutes</option>
                    <option selected>30 minutes</option>
                    <option>1 hour</option>
                    <option>6 hours</option>
                    <option>24 hours</option>
                  </select>
                </div>

                {/* Cache settings */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-medium text-gray-900 mb-2">Cache TTL</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Time-to-live for cached data
                  </p>
                  <select className="input text-sm w-full md:w-auto">
                    <option>5 minutes</option>
                    <option selected>15 minutes</option>
                    <option>30 minutes</option>
                    <option>1 hour</option>
                  </select>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <button className="btn-primary">
                  Save Settings
                </button>
                <button className="btn-secondary ml-3">
                  Reset to Defaults
                </button>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Info Panel */}
      <Card className="bg-blue-50 border-blue-200">
        <div className="p-4">
          <h3 className="font-medium text-blue-900 mb-2">
            Monitoring Tips
          </h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Green status indicates all systems operational</li>
            <li>• Yellow (degraded) means some components have issues but service continues</li>
            <li>• Red (unhealthy) indicates critical system failures requiring attention</li>
            <li>• Check data freshness regularly to ensure up-to-date analysis</li>
            <li>• Monitor agent response times to identify performance bottlenecks</li>
          </ul>
        </div>
      </Card>
    </div>
  );
}
