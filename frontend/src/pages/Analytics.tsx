import { useState, Suspense } from 'react';
import { BarChart3, Activity, PieChart, Settings, TrendingUp, Calculator } from 'lucide-react';
import Loading from '@/components/ui/Loading';
import PortfolioAnalytics from '@/components/analytics/PortfolioAnalytics';
import AgentPerformanceAnalytics from '@/components/analytics/AgentPerformanceAnalytics';
import SectorPerformanceAnalytics from '@/components/analytics/SectorPerformanceAnalytics';
import HealthMonitor from '@/components/system/HealthMonitor';
import DataFreshnessIndicator from '@/components/system/DataFreshnessIndicator';
import PerformanceMetrics from '@/components/system/PerformanceMetrics';
import ScoringCalculator from '@/components/analytics/ScoringCalculator';

type TabView = 'portfolio' | 'agents' | 'sectors' | 'scoring' | 'system';

export default function Analytics() {
  const [activeTab, setActiveTab] = useState<TabView>('portfolio');

  const tabs = [
    { id: 'portfolio' as TabView, label: 'Portfolio', icon: TrendingUp },
    { id: 'agents' as TabView,    label: 'Agent Performance', icon: Activity },
    { id: 'sectors' as TabView,   label: 'Sectors', icon: PieChart },
    { id: 'scoring' as TabView,   label: 'Scoring Calculator', icon: Calculator },
    { id: 'system' as TabView,    label: 'System', icon: Settings },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-blue-600" />
          Analytics
        </h1>
        <p className="text-gray-600 mt-1">
          Portfolio performance, agent accuracy, sector trends, score decomposition, and system health
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200 -mx-4 px-4">
        <nav className="flex space-x-1 overflow-x-auto">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-4 border-b-2 text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <Suspense fallback={<div className="py-12"><Loading size="lg" text="Loading..." /></div>}>
        <div>
          {activeTab === 'portfolio' && <PortfolioAnalytics />}
          {activeTab === 'agents'    && <AgentPerformanceAnalytics />}
          {activeTab === 'sectors'   && <SectorPerformanceAnalytics />}
          {activeTab === 'scoring'   && <ScoringCalculator />}
          {activeTab === 'system'    && <SystemPanel />}
        </div>
      </Suspense>
    </div>
  );
}

function SystemPanel() {
  const [sub, setSub] = useState<'health' | 'freshness' | 'performance'>('health');
  const subTabs = [
    { id: 'health' as const,      label: 'Health Monitor',  icon: Activity },
    { id: 'freshness' as const,   label: 'Data Freshness',  icon: BarChart3 },
    { id: 'performance' as const, label: 'Performance',     icon: TrendingUp },
  ];
  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        {subTabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setSub(id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
              sub === id
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>
      {sub === 'health'      && <HealthMonitor />}
      {sub === 'freshness'   && <DataFreshnessIndicator />}
      {sub === 'performance' && <PerformanceMetrics />}
    </div>
  );
}
