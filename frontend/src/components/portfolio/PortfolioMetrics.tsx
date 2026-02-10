import { TrendingUp, Target, Award, AlertCircle } from 'lucide-react';
import Card from '@/components/ui/Card';
import { cn } from '@/lib/utils';

interface WatchlistItem {
  symbol: string;
  latest_score?: number;
  latest_recommendation?: string;
  added_at: string;
  notes?: string;
}

interface PortfolioMetricsProps {
  watchlist: WatchlistItem[];
}

export default function PortfolioMetrics({ watchlist }: PortfolioMetricsProps) {
  // Calculate portfolio metrics
  const totalStocks = watchlist.length;

  // Calculate average score
  const scoresAvailable = watchlist.filter(item => item.latest_score !== null && item.latest_score !== undefined);
  const avgScore = scoresAvailable.length > 0
    ? scoresAvailable.reduce((sum, item) => sum + (item.latest_score || 0), 0) / scoresAvailable.length
    : 0;

  // Count recommendations
  const recommendations = watchlist.reduce((acc, item) => {
    const rec = item.latest_recommendation || 'UNKNOWN';
    acc[rec] = (acc[rec] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const strongBuyCount = (recommendations['STRONG BUY'] || 0) + (recommendations['BUY'] || 0);
  const holdCount = recommendations['HOLD'] || 0;
  const sellCount = (recommendations['SELL'] || 0) + (recommendations['WEAK SELL'] || 0);

  // Determine portfolio health
  const getPortfolioHealth = () => {
    if (avgScore >= 80) return { label: 'Strong', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' };
    if (avgScore >= 60) return { label: 'Good', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' };
    if (avgScore >= 40) return { label: 'Moderate', color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' };
    return { label: 'Weak', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' };
  };

  const health = getPortfolioHealth();

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {/* Total Stocks */}
      <Card>
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Total Stocks</p>
            <Target className="h-5 w-5 text-blue-600" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{totalStocks}</p>
          <p className="text-xs text-gray-500 mt-1">
            {scoresAvailable.length} with scores
          </p>
        </div>
      </Card>

      {/* Average Score */}
      <Card>
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Avg Score</p>
            <Award className="h-5 w-5 text-purple-600" />
          </div>
          <p className={cn('text-3xl font-bold', avgScore >= 70 ? 'text-green-600' : avgScore >= 50 ? 'text-yellow-600' : 'text-red-600')}>
            {avgScore.toFixed(1)}
          </p>
          <div className={cn('mt-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium', health.bg, health.color, `border ${health.border}`)}>
            {health.label}
          </div>
        </div>
      </Card>

      {/* Buy Recommendations */}
      <Card>
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Buy Signals</p>
            <TrendingUp className="h-5 w-5 text-green-600" />
          </div>
          <p className="text-3xl font-bold text-green-600">{strongBuyCount}</p>
          <p className="text-xs text-gray-500 mt-1">
            {((strongBuyCount / totalStocks) * 100).toFixed(0)}% of portfolio
          </p>
        </div>
      </Card>

      {/* Hold/Sell Count */}
      <Card>
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Hold/Sell</p>
            <AlertCircle className="h-5 w-5 text-yellow-600" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {holdCount + sellCount}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {holdCount} hold • {sellCount} sell
          </p>
        </div>
      </Card>
    </div>
  );
}
