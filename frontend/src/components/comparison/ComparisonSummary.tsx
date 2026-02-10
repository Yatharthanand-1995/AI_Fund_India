/**
 * Comparison Summary Component
 *
 * Shows strengths, weaknesses, and overall winner analysis
 */

import { Trophy, TrendingUp, TrendingDown, AlertCircle, CheckCircle } from 'lucide-react';
import Card from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import type { StockAnalysis } from '@/types';

interface ComparisonSummaryProps {
  stocks: StockAnalysis[];
}

export default function ComparisonSummary({ stocks }: ComparisonSummaryProps) {
  // Find overall winner (highest composite score)
  const winner = stocks.reduce((best, stock) =>
    stock.composite_score > best.composite_score ? stock : best
  , stocks[0]);

  // Analyze strengths and weaknesses for each stock
  const analyzeStock = (stock: StockAnalysis) => {
    const strengths: string[] = [];
    const weaknesses: string[] = [];

    // Agent scores analysis
    const agentScores = [
      { name: 'Fundamentals', score: stock.agent_scores.fundamentals?.score },
      { name: 'Momentum', score: stock.agent_scores.momentum?.score },
      { name: 'Quality', score: stock.agent_scores.quality?.score },
      { name: 'Sentiment', score: stock.agent_scores.sentiment?.score },
      { name: 'Institutional Flow', score: stock.agent_scores.institutional_flow?.score },
    ];

    agentScores.forEach(({ name, score }) => {
      if (score !== undefined) {
        if (score >= 80) strengths.push(`Strong ${name} (${score.toFixed(0)})`);
        else if (score < 40) weaknesses.push(`Weak ${name} (${score.toFixed(0)})`);
      }
    });

    // Returns analysis
    const momentum = stock.agent_scores.momentum?.metrics;
    if (momentum) {
      if (momentum['3m_return'] && momentum['3m_return'] > 15) {
        strengths.push(`Excellent 3M return (+${momentum['3m_return'].toFixed(1)}%)`);
      }
      if (momentum['3m_return'] && momentum['3m_return'] < -10) {
        weaknesses.push(`Poor 3M return (${momentum['3m_return'].toFixed(1)}%)`);
      }
      if (momentum['1y_return'] && momentum['1y_return'] > 30) {
        strengths.push(`Strong 1Y return (+${momentum['1y_return'].toFixed(1)}%)`);
      }
    }

    // Volatility analysis
    const quality = stock.agent_scores.quality?.metrics;
    if (quality?.volatility) {
      if (quality.volatility < 20) {
        strengths.push(`Low volatility (${quality.volatility.toFixed(1)}%)`);
      } else if (quality.volatility > 40) {
        weaknesses.push(`High volatility (${quality.volatility.toFixed(1)}%)`);
      }
    }

    // RSI analysis
    if (momentum?.rsi) {
      if (momentum.rsi < 30) {
        strengths.push('Potentially oversold (RSI: ' + momentum.rsi.toFixed(0) + ')');
      } else if (momentum.rsi > 70) {
        weaknesses.push('Potentially overbought (RSI: ' + momentum.rsi.toFixed(0) + ')');
      }
    }

    // Recommendation
    if (stock.recommendation === 'STRONG BUY') {
      strengths.push('Strong Buy recommendation');
    } else if (stock.recommendation === 'SELL' || stock.recommendation === 'STRONG SELL') {
      weaknesses.push(stock.recommendation + ' recommendation');
    }

    return { strengths, weaknesses };
  };

  // Category winners
  const categoryWinners = {
    'Highest Score': stocks.reduce((best, s) => s.composite_score > best.composite_score ? s : best),
    'Best Momentum': stocks.reduce((best, s) =>
      (s.agent_scores.momentum?.score || 0) > (best.agent_scores.momentum?.score || 0) ? s : best
    ),
    'Best Quality': stocks.reduce((best, s) =>
      (s.agent_scores.quality?.score || 0) > (best.agent_scores.quality?.score || 0) ? s : best
    ),
    'Best Returns': stocks.reduce((best, s) => {
      const bestReturn = best.agent_scores.momentum?.metrics?.['3m_return'] || -Infinity;
      const sReturn = s.agent_scores.momentum?.metrics?.['3m_return'] || -Infinity;
      return sReturn > bestReturn ? s : best;
    }),
  };

  return (
    <div className="space-y-6">
      {/* Overall Winner */}
      <Card className="bg-gradient-to-br from-yellow-50 to-yellow-100 border-yellow-200">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Trophy className="h-8 w-8 text-yellow-600" />
            <div>
              <h3 className="text-xl font-bold text-gray-900">Overall Winner</h3>
              <p className="text-sm text-gray-600">Highest composite score</p>
            </div>
          </div>
          <div className="flex items-center justify-between p-4 bg-white rounded-lg border-2 border-yellow-300">
            <div>
              <p className="text-2xl font-bold text-gray-900">{winner.symbol}</p>
              <p className="text-sm text-gray-600">
                {winner.agent_scores.quality?.metrics?.sector || 'Unknown Sector'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-blue-600">{winner.composite_score.toFixed(1)}</p>
              <p className="text-sm text-gray-600">Composite Score</p>
            </div>
          </div>
          <div className="mt-4 p-3 bg-white rounded-lg">
            <p className="text-sm font-medium text-gray-700 mb-2">Recommendation</p>
            <span className={cn(
              'px-3 py-1 rounded-full text-sm font-medium',
              winner.recommendation === 'STRONG BUY' && 'bg-green-100 text-green-800',
              winner.recommendation === 'BUY' && 'bg-blue-100 text-blue-800',
              winner.recommendation === 'HOLD' && 'bg-gray-100 text-gray-800'
            )}>
              {winner.recommendation}
            </span>
            <span className="ml-3 text-sm text-gray-600">
              {(winner.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
        </div>
      </Card>

      {/* Category Winners */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Category Winners</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(categoryWinners).map(([category, stock]) => (
              <div key={category} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-xs font-medium text-gray-600 mb-1">{category}</p>
                <p className="text-lg font-bold text-blue-600">{stock.symbol}</p>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Strengths & Weaknesses */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {stocks.map((stock) => {
          const analysis = analyzeStock(stock);
          return (
            <Card key={stock.symbol}>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-gray-900">{stock.symbol}</h3>
                  <span className="text-2xl font-bold text-blue-600">
                    {stock.composite_score.toFixed(1)}
                  </span>
                </div>

                {/* Strengths */}
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <p className="text-sm font-semibold text-gray-900">Strengths</p>
                  </div>
                  {analysis.strengths.length > 0 ? (
                    <ul className="space-y-1">
                      {analysis.strengths.map((strength, idx) => (
                        <li key={idx} className="text-sm text-green-700 flex items-start gap-2">
                          <TrendingUp className="h-3 w-3 mt-0.5 flex-shrink-0" />
                          <span>{strength}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500 italic">No notable strengths</p>
                  )}
                </div>

                {/* Weaknesses */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <p className="text-sm font-semibold text-gray-900">Weaknesses</p>
                  </div>
                  {analysis.weaknesses.length > 0 ? (
                    <ul className="space-y-1">
                      {analysis.weaknesses.map((weakness, idx) => (
                        <li key={idx} className="text-sm text-red-700 flex items-start gap-2">
                          <TrendingDown className="h-3 w-3 mt-0.5 flex-shrink-0" />
                          <span>{weakness}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500 italic">No notable weaknesses</p>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
