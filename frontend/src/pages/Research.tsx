import { useState } from 'react';
import { Lightbulb, Filter, Sparkles, LayoutGrid, Table } from 'lucide-react';
import Ideas from './Ideas';
import Screener from './Screener';
import Suggestions from './Suggestions';
import UniverseTable from '@/components/research/UniverseTable';

type ResearchTab = 'ideas' | 'screener' | 'suggestions' | 'universe';

export default function Research() {
  const [activeTab, setActiveTab] = useState<ResearchTab>('ideas');

  const tabs = [
    { id: 'ideas' as ResearchTab,       label: 'Top Ideas',         icon: Lightbulb, desc: 'Ranked picks with AI narratives' },
    { id: 'universe' as ResearchTab,    label: 'NIFTY50 Universe',  icon: Table,     desc: 'All 50 stocks ranked by score' },
    { id: 'screener' as ResearchTab,    label: 'Screener',          icon: Filter,    desc: 'Multi-factor filter & discovery' },
    { id: 'suggestions' as ResearchTab, label: 'Smart Suggestions', icon: Sparkles,  desc: 'Personalized based on watchlist' },
  ];

  return (
    <div className="space-y-0">
      {/* Tab Bar */}
      <div className="bg-white border-b border-gray-200 -mx-4 px-4 mb-6 sticky top-0 z-10">
        <div className="flex items-center gap-1">
          <div className="flex items-center gap-1 mr-4">
            <LayoutGrid className="h-4 w-4 text-gray-400" />
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Research</span>
          </div>
          <nav className="flex">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-5 py-4 border-b-2 text-sm font-medium transition-colors ${
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
      </div>

      {/* Render all three, hide inactive — preserves their state/fetch */}
      <div style={{ display: activeTab === 'ideas' ? 'block' : 'none' }}>
        <Ideas />
      </div>
      <div style={{ display: activeTab === 'screener' ? 'block' : 'none' }}>
        <Screener />
      </div>
      <div style={{ display: activeTab === 'suggestions' ? 'block' : 'none' }}>
        <Suggestions />
      </div>
      {activeTab === 'universe' && <UniverseTable />}
    </div>
  );
}
