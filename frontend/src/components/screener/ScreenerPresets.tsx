/**
 * Screener Presets Component
 *
 * Save and load filter presets for quick screening
 */

import { useState, useEffect } from 'react';
import { Save, Trash2, X, TrendingUp, Shield, Zap, Clock } from 'lucide-react';
import Card from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import type { ScreenerFilters } from '@/pages/Screener';

interface Preset {
  id: string;
  name: string;
  description: string;
  filters: ScreenerFilters;
  icon: string;
  createdAt: string;
}

interface ScreenerPresetsProps {
  currentFilters: ScreenerFilters;
  onLoadPreset: (preset: Preset) => void;
  onClose: () => void;
}

const PRESET_ICONS: Record<string, any> = {
  trending: TrendingUp,
  quality: Shield,
  momentum: Zap,
  recent: Clock,
};

const DEFAULT_PRESETS: Preset[] = [
  {
    id: 'high-momentum',
    name: 'High Momentum',
    description: 'Stocks with strong momentum (80+) and positive 3M returns',
    icon: 'momentum',
    filters: {
      momentumMin: 80,
      return3mMin: 10,
      scoreMin: 60,
    },
    createdAt: new Date().toISOString(),
  },
  {
    id: 'quality-value',
    name: 'Quality Value',
    description: 'High quality stocks (70+) with strong fundamentals',
    icon: 'quality',
    filters: {
      qualityMin: 70,
      fundamentalsMin: 60,
      scoreMin: 65,
    },
    createdAt: new Date().toISOString(),
  },
  {
    id: 'strong-buy',
    name: 'Strong Buy Signals',
    description: 'All Strong Buy recommendations with score 70+',
    icon: 'trending',
    filters: {
      recommendations: ['STRONG BUY'],
      scoreMin: 70,
    },
    createdAt: new Date().toISOString(),
  },
  {
    id: 'tech-momentum',
    name: 'Tech Momentum',
    description: 'Technology sector with high momentum',
    icon: 'momentum',
    filters: {
      sectors: ['Technology'],
      momentumMin: 70,
      return3mMin: 5,
    },
    createdAt: new Date().toISOString(),
  },
  {
    id: 'oversold',
    name: 'Oversold Opportunities',
    description: 'Quality stocks with RSI below 30 (potentially oversold)',
    icon: 'recent',
    filters: {
      rsiMax: 30,
      qualityMin: 60,
      scoreMin: 50,
    },
    createdAt: new Date().toISOString(),
  },
];

export default function ScreenerPresets({ currentFilters, onLoadPreset, onClose }: ScreenerPresetsProps) {
  const [customPresets, setCustomPresets] = useState<Preset[]>([]);
  const [savingNew, setSavingNew] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetDescription, setNewPresetDescription] = useState('');
  const [selectedIcon, setSelectedIcon] = useState('trending');

  useEffect(() => {
    // Load custom presets from localStorage
    const saved = localStorage.getItem('screener-presets');
    if (saved) {
      try {
        setCustomPresets(JSON.parse(saved));
      } catch (err) {
        console.error('Failed to load presets:', err);
      }
    }
  }, []);

  const saveCustomPresets = (presets: Preset[]) => {
    localStorage.setItem('screener-presets', JSON.stringify(presets));
    setCustomPresets(presets);
  };

  const handleSavePreset = () => {
    if (!newPresetName.trim()) return;

    const newPreset: Preset = {
      id: `custom-${Date.now()}`,
      name: newPresetName,
      description: newPresetDescription,
      icon: selectedIcon,
      filters: currentFilters,
      createdAt: new Date().toISOString(),
    };

    saveCustomPresets([...customPresets, newPreset]);
    setSavingNew(false);
    setNewPresetName('');
    setNewPresetDescription('');
  };

  const handleDeletePreset = (id: string) => {
    saveCustomPresets(customPresets.filter(p => p.id !== id));
  };

  const allPresets = [...DEFAULT_PRESETS, ...customPresets];

  return (
    <Card>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Filter Presets</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Save Current Filters */}
        {!savingNew ? (
          <button
            onClick={() => setSavingNew(true)}
            className="btn-secondary w-full mb-6"
          >
            <Save className="h-4 w-4 mr-2" />
            Save Current Filters
          </button>
        ) : (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Save New Preset</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Preset Name
                </label>
                <input
                  type="text"
                  value={newPresetName}
                  onChange={(e) => setNewPresetName(e.target.value)}
                  className="input text-sm w-full"
                  placeholder="My Custom Filter"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={newPresetDescription}
                  onChange={(e) => setNewPresetDescription(e.target.value)}
                  className="input text-sm w-full"
                  rows={2}
                  placeholder="Describe what this filter does..."
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Icon
                </label>
                <div className="flex gap-2">
                  {Object.keys(PRESET_ICONS).map((iconKey) => {
                    const IconComponent = PRESET_ICONS[iconKey];
                    return (
                      <button
                        key={iconKey}
                        onClick={() => setSelectedIcon(iconKey)}
                        className={cn(
                          'p-2 rounded border-2 transition-colors',
                          selectedIcon === iconKey
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        )}
                      >
                        <IconComponent className="h-5 w-5" />
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSavePreset}
                  className="btn-primary flex-1"
                  disabled={!newPresetName.trim()}
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setSavingNew(false);
                    setNewPresetName('');
                    setNewPresetDescription('');
                  }}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Preset List */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Available Presets</h3>
          {allPresets.map((preset) => {
            const IconComponent = PRESET_ICONS[preset.icon] || TrendingUp;
            const isCustom = preset.id.startsWith('custom-');

            return (
              <div
                key={preset.id}
                className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors cursor-pointer group"
                onClick={() => onLoadPreset(preset)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <IconComponent className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-gray-900">{preset.name}</h4>
                        {isCustom && (
                          <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">
                            Custom
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{preset.description}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {Object.entries(preset.filters).map(([key, value]) => {
                          if (value === undefined) return null;
                          return (
                            <span
                              key={key}
                              className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                            >
                              {key}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                  {isCustom && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeletePreset(preset.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-red-600 hover:bg-red-50 rounded transition-opacity"
                      title="Delete preset"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}
