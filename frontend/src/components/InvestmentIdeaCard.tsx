import { memo } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  Star,
  ExternalLink,
  GitCompare,
  Lightbulb,
  TrendingUp,
  TrendingDown,
  Target,
  ShieldAlert,
} from 'lucide-react';
import type { StockAnalysis } from '@/types';
import { getRecommendationColor, cn } from '@/lib/utils';
import { AgentScoresRadar } from '@/components/charts/AgentScoresRadar';
import { useWatchlist } from '@/hooks/useWatchlist';

interface InvestmentIdeaCardProps {
  analysis: StockAnalysis;
  rank: number;
}

function InvestmentIdeaCard({ analysis, rank }: InvestmentIdeaCardProps) {
  const {
    symbol,
    composite_score,
    recommendation,
    confidence,
    agent_scores,
    current_price,
    price_change_percent,
    company_name,
    week_52_high,
    week_52_low,
    trading_levels,
  } = analysis;
  const { watchlist, add, remove } = useWatchlist();
  const isInWatchlist = watchlist.some(item => item.symbol === symbol);

  // Extract key metrics for "Why This Stock?"
  const getKeyInsights = () => {
    const insights: string[] = [];

    // Fundamentals insights
    const fundamentals = agent_scores?.fundamentals;
    if (fundamentals && fundamentals.score > 70) {
      const metrics = fundamentals.metrics;
      if (metrics?.roe) {
        insights.push(`Strong fundamentals (ROE ${(metrics.roe as number).toFixed(1)}%)`);
      } else {
        insights.push(`Strong fundamentals (score ${fundamentals.score.toFixed(0)}/100)`);
      }
    }

    // Momentum insights
    const momentum = agent_scores?.momentum;
    if (momentum && momentum.score > 70) {
      insights.push(`Positive momentum (score ${momentum.score.toFixed(0)}/100)`);
    }

    // Quality insights
    const quality = agent_scores?.quality;
    if (quality && quality.score > 80) {
      insights.push(`High quality score (${quality.score.toFixed(0)}/100, top decile)`);
    }

    // Institutional flow
    const instFlow = agent_scores?.institutional_flow;
    if (instFlow && instFlow.score > 70) {
      insights.push(`Strong institutional interest (score ${instFlow.score.toFixed(0)}/100)`);
    }

    // Sentiment
    const sentiment = agent_scores?.sentiment;
    if (sentiment && sentiment.score > 70) {
      insights.push(`Positive market sentiment (score ${sentiment.score.toFixed(0)}/100)`);
    }

    return insights.slice(0, 4); // Max 4 insights
  };

  // Extract risk indicators
  const getRisks = () => {
    const risks: string[] = [];

    // Check for low scores
    Object.entries(agent_scores || {}).forEach(([key, agent]) => {
      if (agent && agent.score < 50) {
        const name = key.replace('_', ' ');
        risks.push(`${name.charAt(0).toUpperCase() + name.slice(1)}: Below average (${agent.score.toFixed(0)}/100)`);
      }
    });

    // Generic risks if no specific ones
    if (risks.length === 0 && composite_score < 85) {
      risks.push('Moderate volatility expected');
    }

    return risks.slice(0, 3); // Max 3 risks
  };

  const insights = getKeyInsights();
  const risks = getRisks();

  const handleWatchlistToggle = () => {
    if (isInWatchlist) {
      remove(symbol);
    } else {
      add(symbol);
    }
  };

  // Get sector from fundamentals or top-level
  const sector = analysis.sector || agent_scores?.fundamentals?.metrics?.sector || 'Unknown';

  // Momentum metrics
  const momentum = agent_scores?.momentum?.metrics;
  const rsi = momentum?.rsi;
  const trend = momentum?.trend;
  const return3m = momentum?.['3m_return'];

  // Analyst upside
  const analystUpside = agent_scores?.sentiment?.metrics?.upside_percent;
  const peRatio = agent_scores?.fundamentals?.metrics?.pe_ratio;

  // 52W range position (0-100%)
  const week52Position =
    week_52_high && week_52_low && current_price && week_52_high > week_52_low
      ? Math.max(0, Math.min(100, ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100))
      : null;

  const fmt = (n: number | undefined | null, decimals = 2, prefix = '₹') =>
    n != null ? `${prefix}${n.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}` : 'N/A';

  return (
    <div className="bg-white rounded-lg shadow-md border-2 border-gray-200 hover:shadow-lg transition-shadow overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-4xl font-bold">#{rank}</div>
              <div className="text-xs text-blue-100">RANK</div>
            </div>
            <div>
              <h2 className="text-2xl font-bold">{symbol}</h2>
              {company_name && (
                <p className="text-blue-200 text-xs truncate max-w-[160px]">{company_name}</p>
              )}
              <p className="text-blue-100 text-sm flex items-center gap-2 mt-1">
                <span
                  className={cn(
                    'px-2 py-0.5 rounded text-xs font-medium',
                    getRecommendationColor(recommendation as any)
                  )}
                >
                  {recommendation}
                </span>
                <span>•</span>
                <span>{sector}</span>
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold">{composite_score.toFixed(1)}</div>
            <div className="text-blue-100 text-xs">SCORE</div>
          </div>
        </div>
      </div>

      {/* Price & Day Change */}
      {current_price != null && (
        <div className="px-4 py-3 sm:px-6 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">Current Price</p>
            <p className="text-2xl font-bold text-gray-900">
              ₹{current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          {price_change_percent != null && (
            <div className={cn(
              'flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold',
              price_change_percent >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            )}>
              {price_change_percent >= 0
                ? <TrendingUp className="h-4 w-4" />
                : <TrendingDown className="h-4 w-4" />}
              {price_change_percent >= 0 ? '+' : ''}{price_change_percent.toFixed(2)}% today
            </div>
          )}
        </div>
      )}

      {/* Trading Levels — THE KEY ACTIONABLE SECTION */}
      {(trading_levels?.stop_loss || trading_levels?.target_price) && (
        <div className="px-4 py-3 sm:px-6 border-b border-gray-200">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Trading Levels</h3>
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center bg-red-50 border border-red-200 rounded-lg p-2">
              <div className="flex items-center justify-center gap-1 mb-1">
                <ShieldAlert className="h-3 w-3 text-red-500" />
                <p className="text-xs font-medium text-red-700">Stop Loss</p>
              </div>
              <p className="text-base font-bold text-red-700">
                {fmt(trading_levels.stop_loss)}
              </p>
            </div>
            <div className="text-center bg-blue-50 border border-blue-200 rounded-lg p-2">
              <p className="text-xs font-medium text-blue-700 mb-1">Entry (CMP)</p>
              <p className="text-base font-bold text-blue-700">
                {fmt(current_price)}
              </p>
            </div>
            <div className="text-center bg-green-50 border border-green-200 rounded-lg p-2">
              <div className="flex items-center justify-center gap-1 mb-1">
                <Target className="h-3 w-3 text-green-600" />
                <p className="text-xs font-medium text-green-700">Target</p>
              </div>
              <p className="text-base font-bold text-green-700">
                {fmt(trading_levels.target_price)}
              </p>
            </div>
          </div>
          {trading_levels.risk_reward_ratio && (
            <p className="text-xs text-center text-gray-500 mt-2">
              Risk:Reward = 1:{trading_levels.risk_reward_ratio.toFixed(1)}
              {analystUpside != null && (
                <span className="ml-3 text-blue-600 font-medium">
                  Analyst Upside: {analystUpside > 0 ? '+' : ''}{analystUpside.toFixed(1)}%
                </span>
              )}
            </p>
          )}
        </div>
      )}

      {/* Key Metrics Row */}
      <div className="px-4 py-3 sm:px-6 border-b border-gray-200">
        <div className="grid grid-cols-4 gap-2 text-center">
          {rsi != null && (
            <div>
              <p className="text-xs text-gray-500">RSI</p>
              <p className={cn(
                'text-sm font-bold',
                rsi > 70 ? 'text-red-600' : rsi < 30 ? 'text-green-600' : 'text-gray-900'
              )}>
                {rsi.toFixed(0)}
              </p>
            </div>
          )}
          {trend && (
            <div>
              <p className="text-xs text-gray-500">Trend</p>
              <p className={cn(
                'text-xs font-bold',
                trend === 'UPTREND' ? 'text-green-600' :
                trend === 'DOWNTREND' ? 'text-red-600' : 'text-yellow-600'
              )}>
                {trend}
              </p>
            </div>
          )}
          {return3m != null && (
            <div>
              <p className="text-xs text-gray-500">3M Return</p>
              <p className={cn('text-sm font-bold', return3m >= 0 ? 'text-green-600' : 'text-red-600')}>
                {return3m > 0 ? '+' : ''}{return3m.toFixed(1)}%
              </p>
            </div>
          )}
          {peRatio != null && (
            <div>
              <p className="text-xs text-gray-500">P/E</p>
              <p className="text-sm font-bold text-gray-900">{peRatio.toFixed(1)}x</p>
            </div>
          )}
        </div>

        {/* 52-Week Range Bar */}
        {week52Position != null && week_52_high != null && week_52_low != null && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>52W Low: ₹{week_52_low.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
              <span>52W High: ₹{week_52_high.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            </div>
            <div className="relative w-full bg-gray-200 rounded-full h-2">
              <div
                className="absolute h-4 w-1 bg-blue-600 rounded-full -top-1 transform -translate-x-1/2"
                style={{ left: `${week52Position}%` }}
                title={`Current: ₹${current_price}`}
              />
              <div className="bg-gradient-to-r from-red-300 via-yellow-300 to-green-400 h-2 rounded-full" />
            </div>
            <p className="text-xs text-center text-gray-500 mt-1">
              At {week52Position.toFixed(0)}% of 52W range
            </p>
          </div>
        )}
      </div>

      <div className="p-4 sm:p-6">
        {/* Why This Stock? */}
        {insights.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-yellow-500" />
              WHY THIS STOCK?
            </h3>
            <ul className="space-y-2">
              {insights.map((insight, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-green-600 font-bold mt-0.5">✓</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Risks */}
        {risks.length > 0 && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-yellow-900 mb-2 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              RISKS TO CONSIDER
            </h3>
            <ul className="space-y-1">
              {risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs text-yellow-800">
                  <span className="mt-0.5">•</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Agent Breakdown */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">AGENT BREAKDOWN</h3>
          <div>
            <AgentScoresRadar agentScores={agent_scores} height={200} />
          </div>
        </div>

        {/* Confidence Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-600">Confidence</span>
            <span className="font-bold text-gray-900">{(confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-stretch gap-2">
          <button
            onClick={handleWatchlistToggle}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors',
              isInWatchlist
                ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border border-yellow-300'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            )}
          >
            <Star className={cn('h-4 w-4', isInWatchlist && 'fill-current')} />
            {isInWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
          </button>

          <Link
            to={`/stock/${symbol}`}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium text-sm transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            Full Analysis
          </Link>

          <Link
            to={`/compare?symbols=${symbol}`}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium text-sm transition-colors"
          >
            <GitCompare className="h-4 w-4" />
            <span className="hidden sm:inline">Compare</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default memo(InvestmentIdeaCard);
