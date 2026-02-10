import { useState } from 'react';
import { Calendar, TrendingUp } from 'lucide-react';
import type { BacktestConfig } from '@/types';

interface BacktestConfigFormProps {
  onSubmit: (config: BacktestConfig) => void;
}

export default function BacktestConfigForm({ onSubmit }: BacktestConfigFormProps) {
  const [config, setConfig] = useState<BacktestConfig>({
    name: '',
    symbols: null, // null = NIFTY 50
    start_date: '2023-01-01',
    end_date: '2024-12-31',
    frequency: 'monthly',
    include_narrative: false
  });

  const [useCustomSymbols, setUseCustomSymbols] = useState(false);
  const [symbolsInput, setSymbolsInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const submitConfig: BacktestConfig = {
      ...config,
      symbols: useCustomSymbols && symbolsInput.trim()
        ? symbolsInput.split(',').map(s => s.trim()).filter(Boolean)
        : null,
      name: config.name?.trim() || `Backtest ${config.start_date} to ${config.end_date}`
    };

    onSubmit(submitConfig);
  };

  // Calculate approximate duration
  const getApproximateDuration = (): string => {
    const start = new Date(config.start_date);
    const end = new Date(config.end_date);
    const months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());

    const numSymbols = useCustomSymbols && symbolsInput.trim()
      ? symbolsInput.split(',').filter(s => s.trim()).length
      : 50; // NIFTY 50

    let periods = 0;
    switch (config.frequency) {
      case 'daily':
        periods = months * 20; // ~20 trading days per month
        break;
      case 'weekly':
        periods = months * 4;
        break;
      case 'monthly':
        periods = months;
        break;
      case 'quarterly':
        periods = Math.floor(months / 3);
        break;
    }

    const totalSignals = numSymbols * periods;
    const estimatedMinutes = Math.ceil(totalSignals / 50); // ~50 signals per minute

    if (estimatedMinutes < 1) return '< 1 minute';
    if (estimatedMinutes < 60) return `~${estimatedMinutes} minutes`;
    return `~${Math.ceil(estimatedMinutes / 60)} hours`;
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Backtest Name (Optional)
        </label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => setConfig({ ...config, name: e.target.value })}
          placeholder="e.g., NIFTY 50 Validation 2023-2024"
          className="input"
        />
        <p className="mt-1 text-xs text-gray-500">
          If not provided, will be auto-generated from date range
        </p>
      </div>

      {/* Stock Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Stocks to Backtest
        </label>
        <div className="space-y-3">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={!useCustomSymbols}
              onChange={() => setUseCustomSymbols(false)}
              className="h-4 w-4 text-blue-600"
            />
            <span className="text-sm">
              <span className="font-medium">NIFTY 50</span>
              <span className="text-gray-600 ml-2">(Recommended - 50 stocks)</span>
            </span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={useCustomSymbols}
              onChange={() => setUseCustomSymbols(true)}
              className="h-4 w-4 text-blue-600"
            />
            <span className="text-sm font-medium">Custom Stock List</span>
          </label>

          {useCustomSymbols && (
            <div className="ml-6">
              <input
                type="text"
                value={symbolsInput}
                onChange={(e) => setSymbolsInput(e.target.value)}
                placeholder="TCS, INFY, RELIANCE, HDFCBANK"
                className="input"
              />
              <p className="mt-1 text-xs text-gray-500">
                Enter comma-separated stock symbols
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Start Date
          </label>
          <input
            type="date"
            value={config.start_date}
            onChange={(e) => setConfig({ ...config, start_date: e.target.value })}
            max={config.end_date}
            required
            className="input"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            End Date
          </label>
          <input
            type="date"
            value={config.end_date}
            onChange={(e) => setConfig({ ...config, end_date: e.target.value })}
            min={config.start_date}
            max={new Date().toISOString().split('T')[0]}
            required
            className="input"
          />
        </div>
      </div>

      {/* Rebalance Frequency */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Rebalance Frequency
        </label>
        <select
          value={config.frequency}
          onChange={(e) => setConfig({ ...config, frequency: e.target.value as any })}
          className="input"
        >
          <option value="daily">Daily (Most granular, slowest)</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly (Recommended)</option>
          <option value="quarterly">Quarterly (Fastest)</option>
        </select>
        <p className="mt-1 text-xs text-gray-500">
          How often to generate trading signals and rebalance portfolio
        </p>
      </div>

      {/* Duration Estimate */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <TrendingUp className="h-5 w-5 text-gray-600 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-1">
              Estimated Duration
            </h4>
            <p className="text-sm text-gray-600">
              This backtest will take approximately <span className="font-semibold">{getApproximateDuration()}</span> to complete.
            </p>
            <p className="text-xs text-gray-500 mt-1">
              The backtest will run in the background. You can close this page and check back later.
            </p>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t">
        <button
          type="submit"
          className="btn-primary px-8"
        >
          Run Backtest
        </button>
      </div>
    </form>
  );
}
