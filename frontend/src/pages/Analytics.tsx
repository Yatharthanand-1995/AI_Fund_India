/**
 * Enhanced Analytics Dashboard
 *
 * Comprehensive investment analytics and insights
 * Features:
 * - Portfolio performance tracking
 * - Agent prediction accuracy analysis
 * - Sector performance and rotation
 * - System health metrics
 */

import { useState } from 'react';
import { BarChart3, Activity, PieChart, Settings, TrendingUp } from 'lucide-react';
import Card from '@/components/ui/Card';
import PortfolioAnalytics from '@/components/analytics/PortfolioAnalytics';
import AgentPerformanceAnalytics from '@/components/analytics/AgentPerformanceAnalytics';
import SectorPerformanceAnalytics from '@/components/analytics/SectorPerformanceAnalytics';
import PerformanceMetrics from '@/components/system/PerformanceMetrics';

type TabView = 'portfolio' | 'agents' | 'sectors' | 'system';

export default function Analytics() {
  const [activeTab, setActiveTab] = useState<TabView>('portfolio');

  const tabs = [
    { id: 'portfolio' as TabView, label: 'Portfolio Analytics', icon: TrendingUp },
    { id: 'agents' as TabView, label: 'Agent Performance', icon: Activity },
    { id: 'sectors' as TabView, label: 'Sector Analysis', icon: PieChart },
    { id: 'system' as TabView, label: 'System Metrics', icon: Settings },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-blue-600" />
          Advanced Analytics
        </h1>
        <p className="text-gray-600 mt-2">
          Deep insights into portfolio performance, agent accuracy, and market trends
        </p>
      </div>

      {/* Tab Navigation */}
      <Card>
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
                  ${activeTab === id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </nav>
        </div>
      </Card>

      {/* Tab Content */}
      <div>
        {activeTab === 'portfolio' && <PortfolioAnalytics />}
        {activeTab === 'agents' && <AgentPerformanceAnalytics />}
        {activeTab === 'sectors' && <SectorPerformanceAnalytics />}
        {activeTab === 'system' && <PerformanceMetrics />}
      </div>

      {/* Info Panel */}
      <Card className="bg-blue-50 border-blue-200">
        <div className="p-4">
          <h3 className="font-medium text-blue-900 mb-2">
            💡 Analytics Tips
          </h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• <strong>Portfolio Analytics</strong> - Track your watchlist performance and identify top performers</li>
            <li>• <strong>Agent Performance</strong> - See which agents are most accurate in predicting positive returns</li>
            <li>• <strong>Sector Analysis</strong> - Identify sector rotation and best performing industries</li>
            <li>• <strong>System Metrics</strong> - Monitor system health, uptime, and API performance</li>
          </ul>
        </div>
      </Card>
    </div>
  );
}
