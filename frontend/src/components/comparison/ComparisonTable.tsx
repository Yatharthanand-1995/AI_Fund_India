/**
 * Comprehensive Comparison Table
 *
 * Shows detailed metrics for 2-5 stocks side-by-side
 * Highlights the winner in each category
 */

import { Crown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { StockAnalysis } from '@/types';

interface ComparisonTableProps {
  stocks: StockAnalysis[];
}

export default function ComparisonTable({ stocks }: ComparisonTableProps) {
  const findBest = (getValue: (stock: StockAnalysis) => number | undefined, higherIsBetter = true) => {
    const values = stocks.map((s, idx) => ({ idx, value: getValue(s) }));
    const validValues = values.filter(v => v.value !== undefined);

    if (validValues.length === 0) return -1;

    const best = higherIsBetter
      ? validValues.reduce((max, v) => (v.value! > max.value! ? v : max))
      : validValues.reduce((min, v) => (v.value! < min.value! ? v : min));

    return best.idx;
  };

  const renderCell = (value: any, isBest: boolean, format: 'number' | 'percent' | 'text' = 'text') => {
    if (value === undefined || value === null) {
      return <span className="text-gray-400">N/A</span>;
    }

    let displayValue: string;
    if (format === 'number') {
      displayValue = typeof value === 'number' ? value.toFixed(1) : String(value);
    } else if (format === 'percent') {
      displayValue = typeof value === 'number' ? `${value.toFixed(1)}%` : String(value);
    } else {
      displayValue = String(value);
    }

    return (
      <div className={cn(
        'flex items-center gap-2',
        isBest && 'font-bold'
      )}>
        {isBest && <Crown className="h-4 w-4 text-yellow-500" />}
        <span className={isBest ? 'text-blue-700' : 'text-gray-900'}>
          {displayValue}
        </span>
      </div>
    );
  };

  const renderReturnCell = (value: number | undefined, isBest: boolean) => {
    if (value === undefined) {
      return <span className="text-gray-400">N/A</span>;
    }

    const isPositive = value >= 0;
    return (
      <div className={cn(
        'flex items-center gap-2',
        isBest && 'font-bold'
      )}>
        {isBest && <Crown className="h-4 w-4 text-yellow-500" />}
        <span className={cn(
          isBest ? 'font-bold' : 'font-medium',
          isPositive ? 'text-green-600' : 'text-red-600'
        )}>
          {isPositive ? '+' : ''}{value.toFixed(1)}%
        </span>
      </div>
    );
  };

  // Find best in each category
  const bestScore = findBest(s => s.composite_score);
  const bestFundamentals = findBest(s => s.agent_scores.fundamentals?.score);
  const bestMomentum = findBest(s => s.agent_scores.momentum?.score);
  const bestQuality = findBest(s => s.agent_scores.quality?.score);
  const bestSentiment = findBest(s => s.agent_scores.sentiment?.score);
  const bestInstitutional = findBest(s => s.agent_scores.institutional_flow?.score);
  const best1m = findBest(s => s.agent_scores.momentum?.metrics?.['1m_return']);
  const best3m = findBest(s => s.agent_scores.momentum?.metrics?.['3m_return']);
  const best6m = findBest(s => s.agent_scores.momentum?.metrics?.['6m_return']);
  const best1y = findBest(s => s.agent_scores.momentum?.metrics?.['1y_return']);
  const bestRSI = findBest(s => {
    const rsi = s.agent_scores.momentum?.metrics?.rsi;
    if (!rsi) return undefined;
    // Best RSI is closest to 50 (neutral)
    return -Math.abs(rsi - 50);
  });
  const lowestVolatility = findBest(s => s.agent_scores.quality?.metrics?.volatility, false);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-gray-50 z-10">
              Metric
            </th>
            {stocks.map((stock) => (
              <th
                key={stock.symbol}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                <div className="flex flex-col">
                  <span className="font-bold text-gray-900 text-base">{stock.symbol}</span>
                  <span className="text-xs text-gray-500 normal-case">
                    {stock.agent_scores.quality?.metrics?.sector || 'Unknown'}
                  </span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {/* Overall Score & Recommendation */}
          <tr className="bg-blue-50">
            <td colSpan={stocks.length + 1} className="px-6 py-2 text-xs font-semibold text-gray-700 uppercase">
              Overall Assessment
            </td>
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Composite Score
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.composite_score, idx === bestScore, 'number')}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Recommendation
            </td>
            {stocks.map((stock) => (
              <td key={stock.symbol} className="px-6 py-4">
                <span className={cn(
                  'px-2 py-1 rounded text-xs font-medium',
                  stock.recommendation === 'STRONG BUY' && 'bg-green-100 text-green-800',
                  stock.recommendation === 'BUY' && 'bg-blue-100 text-blue-800',
                  stock.recommendation === 'HOLD' && 'bg-gray-100 text-gray-800',
                  stock.recommendation === 'SELL' && 'bg-orange-100 text-orange-800',
                  stock.recommendation === 'STRONG SELL' && 'bg-red-100 text-red-800'
                )}>
                  {stock.recommendation}
                </span>
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Confidence
            </td>
            {stocks.map((stock) => (
              <td key={stock.symbol} className="px-6 py-4">
                <span className="text-sm text-gray-900">
                  {(stock.confidence * 100).toFixed(0)}%
                </span>
              </td>
            ))}
          </tr>

          {/* Agent Scores */}
          <tr className="bg-blue-50">
            <td colSpan={stocks.length + 1} className="px-6 py-2 text-xs font-semibold text-gray-700 uppercase">
              Agent Scores
            </td>
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Fundamentals
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.agent_scores.fundamentals?.score, idx === bestFundamentals, 'number')}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Momentum
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.agent_scores.momentum?.score, idx === bestMomentum, 'number')}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Quality
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.agent_scores.quality?.score, idx === bestQuality, 'number')}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Sentiment
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.agent_scores.sentiment?.score, idx === bestSentiment, 'number')}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Institutional Flow
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.agent_scores.institutional_flow?.score, idx === bestInstitutional, 'number')}
              </td>
            ))}
          </tr>

          {/* Returns */}
          <tr className="bg-blue-50">
            <td colSpan={stocks.length + 1} className="px-6 py-2 text-xs font-semibold text-gray-700 uppercase">
              Returns Performance
            </td>
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              1 Month Return
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderReturnCell(stock.agent_scores.momentum?.metrics?.['1m_return'], idx === best1m)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              3 Month Return
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderReturnCell(stock.agent_scores.momentum?.metrics?.['3m_return'], idx === best3m)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              6 Month Return
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderReturnCell(stock.agent_scores.momentum?.metrics?.['6m_return'], idx === best6m)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              1 Year Return
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderReturnCell(stock.agent_scores.momentum?.metrics?.['1y_return'], idx === best1y)}
              </td>
            ))}
          </tr>

          {/* Technical Indicators */}
          <tr className="bg-blue-50">
            <td colSpan={stocks.length + 1} className="px-6 py-2 text-xs font-semibold text-gray-700 uppercase">
              Technical Indicators
            </td>
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              RSI
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.agent_scores.momentum?.metrics?.rsi, idx === bestRSI, 'number')}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Trend
            </td>
            {stocks.map((stock) => (
              <td key={stock.symbol} className="px-6 py-4">
                <span className="text-sm text-gray-900 capitalize">
                  {stock.agent_scores.momentum?.metrics?.trend?.replace('_', ' ') || 'N/A'}
                </span>
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Volatility
            </td>
            {stocks.map((stock, idx) => (
              <td key={stock.symbol} className="px-6 py-4">
                {renderCell(stock.agent_scores.quality?.metrics?.volatility, idx === lowestVolatility, 'percent')}
              </td>
            ))}
          </tr>

          {/* Market Info */}
          <tr className="bg-blue-50">
            <td colSpan={stocks.length + 1} className="px-6 py-2 text-xs font-semibold text-gray-700 uppercase">
              Market Information
            </td>
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Market Cap
            </td>
            {stocks.map((stock) => {
              const marketCap = stock.agent_scores.quality?.metrics?.market_cap;
              const displayCap = marketCap
                ? `₹${(marketCap / 1e9).toFixed(0)}B`
                : 'N/A';
              return (
                <td key={stock.symbol} className="px-6 py-4">
                  <span className="text-sm text-gray-900">{displayCap}</span>
                </td>
              );
            })}
          </tr>
          <tr>
            <td className="px-6 py-4 text-sm font-medium text-gray-900 sticky left-0 bg-white">
              Analyst Coverage
            </td>
            {stocks.map((stock) => (
              <td key={stock.symbol} className="px-6 py-4">
                <span className="text-sm text-gray-900">
                  {stock.agent_scores.sentiment?.metrics?.number_of_analyst_opinions || 'N/A'}
                </span>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
