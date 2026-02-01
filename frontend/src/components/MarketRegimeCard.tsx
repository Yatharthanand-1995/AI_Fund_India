import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { MarketRegime } from '@/types';
import { getTrendColor, getVolatilityColor, formatPercent, cn } from '@/lib/utils';

interface MarketRegimeCardProps {
  regime: MarketRegime;
}

export default function MarketRegimeCard({ regime }: MarketRegimeCardProps) {
  const getTrendIcon = () => {
    switch (regime.trend) {
      case 'BULL':
        return <TrendingUp className="h-6 w-6" />;
      case 'BEAR':
        return <TrendingDown className="h-6 w-6" />;
      default:
        return <Minus className="h-6 w-6" />;
    }
  };

  const agentWeights = [
    { label: 'Fundamentals', key: 'fundamentals' },
    { label: 'Momentum', key: 'momentum' },
    { label: 'Quality', key: 'quality' },
    { label: 'Sentiment', key: 'sentiment' },
    { label: 'Institutional', key: 'institutional_flow' },
  ];

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Activity className="h-6 w-6 text-primary-600" />
          <h3 className="text-lg font-semibold text-gray-900">Current Market Regime</h3>
        </div>
        <div className="flex items-center space-x-2">
          <div className={cn('px-3 py-1 rounded-full text-sm font-medium border', getTrendColor(regime.trend))}>
            <div className="flex items-center space-x-1">
              {getTrendIcon()}
              <span>{regime.trend}</span>
            </div>
          </div>
          <div className={cn('px-3 py-1 rounded-full text-sm font-medium border', getVolatilityColor(regime.volatility))}>
            {regime.volatility} VOL
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Adaptive Weights */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Adaptive Agent Weights</h4>
          <div className="space-y-2">
            {agentWeights.map(({ label, key }) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{label}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full"
                      style={{ width: `${(regime.weights[key] || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-900 w-10 text-right">
                    {formatPercent((regime.weights[key] || 0) * 100, 0)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Market Metrics */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Market Metrics</h4>
          <div className="space-y-2">
            {regime.metrics.current_price && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">NIFTY Price</span>
                <span className="text-sm font-medium text-gray-900">
                  {regime.metrics.current_price.toFixed(2)}
                </span>
              </div>
            )}
            {regime.metrics.price_vs_sma50_pct !== undefined && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">vs 50-SMA</span>
                <span
                  className={cn(
                    'text-sm font-medium',
                    regime.metrics.price_vs_sma50_pct > 0 ? 'text-green-600' : 'text-red-600'
                  )}
                >
                  {regime.metrics.price_vs_sma50_pct > 0 ? '+' : ''}
                  {regime.metrics.price_vs_sma50_pct.toFixed(2)}%
                </span>
              </div>
            )}
            {regime.metrics.volatility_pct && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Volatility (30d)</span>
                <span className="text-sm font-medium text-gray-900">
                  {regime.metrics.volatility_pct.toFixed(1)}%
                </span>
              </div>
            )}
            {regime.metrics.volatility_trend && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Vol Trend</span>
                <span
                  className={cn(
                    'text-sm font-medium',
                    regime.metrics.volatility_trend === 'increasing' ? 'text-orange-600' : 'text-green-600'
                  )}
                >
                  {regime.metrics.volatility_trend}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {regime.cached && (
        <div className="mt-4 text-xs text-gray-400 text-center">
          Cached regime data
        </div>
      )}
    </div>
  );
}
