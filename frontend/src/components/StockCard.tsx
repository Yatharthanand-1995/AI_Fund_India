import { memo } from 'react';
import { TrendingUp, TrendingDown, Activity, Shield, Users, MessageSquare, Target, ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { StockAnalysis } from '@/types';
import {
  formatPercent,
  getRecommendationColor,
  getScoreColor,
  getScoreBgColor,
  cn,
} from '@/lib/utils';

interface StockCardProps {
  analysis: StockAnalysis;
  detailed?: boolean;
}

function StockCard({ analysis, detailed = false }: StockCardProps) {
  const {
    symbol,
    composite_score,
    recommendation,
    confidence,
    agent_scores,
    narrative,
    current_price,
    price_change_percent,
    company_name,
    week_52_high,
    week_52_low,
    trading_levels,
  } = analysis;

  const agents = [
    { key: 'fundamentals', label: 'Fundamentals', icon: TrendingUp, color: 'text-blue-600' },
    { key: 'momentum', label: 'Momentum', icon: Activity, color: 'text-green-600' },
    { key: 'quality', label: 'Quality', icon: Shield, color: 'text-purple-600' },
    { key: 'sentiment', label: 'Sentiment', icon: MessageSquare, color: 'text-orange-600' },
    { key: 'institutional_flow', label: 'Inst. Flow', icon: Users, color: 'text-indigo-600' },
  ];

  // Key momentum metrics
  const momentum = agent_scores?.momentum?.metrics;
  const rsi = momentum?.rsi;
  const trend = momentum?.trend;

  // 52W range position
  const week52Position =
    week_52_high && week_52_low && current_price && week_52_high > week_52_low
      ? Math.max(0, Math.min(100, ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100))
      : null;

  const peRatio = agent_scores?.fundamentals?.metrics?.pe_ratio;
  const analystUpside = agent_scores?.sentiment?.metrics?.upside_percent;

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-blue-600 text-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold">{symbol}</h2>
            {company_name && (
              <p className="text-blue-200 text-xs mt-0.5 truncate max-w-[200px]">{company_name}</p>
            )}
            <p className="text-primary-100 text-sm mt-1">Stock Analysis</p>
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold">{composite_score.toFixed(1)}</div>
            <div className="text-primary-100 text-sm">Composite Score</div>
          </div>
        </div>
      </div>

      {/* Current Price & Day Change */}
      {current_price != null && (
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
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
              {price_change_percent >= 0 ? '+' : ''}{price_change_percent.toFixed(2)}%
            </div>
          )}
        </div>
      )}

      {/* Trading Levels */}
      {(trading_levels?.stop_loss || trading_levels?.target_price) && (
        <div className="px-6 py-3 border-b border-gray-200">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Trading Levels</h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center bg-red-50 border border-red-200 rounded-lg p-2">
              <div className="flex items-center justify-center gap-1 mb-1">
                <ShieldAlert className="h-3 w-3 text-red-500" />
                <p className="text-xs font-medium text-red-700">Stop Loss</p>
              </div>
              <p className="text-sm font-bold text-red-700">
                ₹{trading_levels.stop_loss?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? 'N/A'}
              </p>
            </div>
            <div className="text-center bg-blue-50 border border-blue-200 rounded-lg p-2">
              <p className="text-xs font-medium text-blue-700 mb-1">CMP</p>
              <p className="text-sm font-bold text-blue-700">
                {current_price != null
                  ? `₹${current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : 'N/A'}
              </p>
            </div>
            <div className="text-center bg-green-50 border border-green-200 rounded-lg p-2">
              <div className="flex items-center justify-center gap-1 mb-1">
                <Target className="h-3 w-3 text-green-600" />
                <p className="text-xs font-medium text-green-700">Target</p>
              </div>
              <p className="text-sm font-bold text-green-700">
                ₹{trading_levels.target_price?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? 'N/A'}
              </p>
            </div>
          </div>
          {trading_levels.risk_reward_ratio != null && (
            <p className="text-xs text-center text-gray-500 mt-1">
              Risk:Reward = 1:{trading_levels.risk_reward_ratio.toFixed(1)}
              {analystUpside != null && (
                <span className="ml-3 font-medium text-blue-600">
                  Analyst Upside: {analystUpside > 0 ? '+' : ''}{analystUpside.toFixed(1)}%
                </span>
              )}
            </p>
          )}
        </div>
      )}

      {/* Quick Metrics */}
      {(rsi != null || trend || peRatio != null || week52Position != null) && (
        <div className="px-6 py-3 border-b border-gray-200">
          <div className="grid grid-cols-4 gap-2 text-center mb-3">
            {rsi != null && (
              <div>
                <p className="text-xs text-gray-500">RSI</p>
                <p className={cn(
                  'text-sm font-bold',
                  rsi > 70 ? 'text-red-600' : rsi < 30 ? 'text-green-600' : 'text-gray-900'
                )}>
                  {rsi.toFixed(0)}
                  <span className="text-xs font-normal ml-0.5">
                    {rsi > 70 ? ' OB' : rsi < 30 ? ' OS' : ''}
                  </span>
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
                  {trend === 'UPTREND' ? '↑ UP' : trend === 'DOWNTREND' ? '↓ DOWN' : '→ FLAT'}
                </p>
              </div>
            )}
            {peRatio != null && (
              <div>
                <p className="text-xs text-gray-500">P/E</p>
                <p className="text-sm font-bold text-gray-900">{peRatio.toFixed(1)}x</p>
              </div>
            )}
            {analystUpside != null && (
              <div>
                <p className="text-xs text-gray-500">Upside</p>
                <p className={cn('text-sm font-bold', analystUpside >= 0 ? 'text-green-600' : 'text-red-600')}>
                  {analystUpside > 0 ? '+' : ''}{analystUpside.toFixed(0)}%
                </p>
              </div>
            )}
          </div>

          {/* 52-Week Range Bar */}
          {week52Position != null && week_52_high != null && week_52_low != null && (
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>52W Low: ₹{week_52_low.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                <span>52W High: ₹{week_52_high.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
              </div>
              <div className="relative w-full bg-gray-200 rounded-full h-2">
                <div className="bg-gradient-to-r from-red-300 via-yellow-300 to-green-400 h-2 rounded-full" />
                <div
                  className="absolute h-4 w-1.5 bg-blue-600 rounded-full -top-1 transform -translate-x-1/2 shadow"
                  style={{ left: `${week52Position}%` }}
                  title={`Current: ₹${current_price}`}
                />
              </div>
              <p className="text-xs text-center text-gray-400 mt-1">
                At {week52Position.toFixed(0)}% of 52W range
              </p>
            </div>
          )}
        </div>
      )}

      {/* Recommendation */}
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 mb-1">Recommendation</p>
            <div
              className={cn(
                'inline-block px-4 py-2 rounded-lg border-2 font-bold text-lg',
                getRecommendationColor(recommendation as any)
              )}
            >
              {recommendation}
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600 mb-1">Confidence</p>
            <div className="text-2xl font-bold text-gray-900">
              {formatPercent(confidence * 100, 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Agent Scores */}
      <div className="px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Agent Analysis</h3>
        <div className="space-y-3">
          {agents.map(({ key, label, icon: Icon, color }) => {
            const agentData = agent_scores[key];
            if (!agentData) return null;

            return (
              <div key={key} className="flex items-center space-x-3">
                <Icon className={cn('h-5 w-5 flex-shrink-0', color)} />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{label}</span>
                    <span className={cn('font-bold', getScoreColor(agentData.score))}>
                      {agentData.score.toFixed(1)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={cn('h-2 rounded-full', getScoreBgColor(agentData.score))}
                      style={{ width: `${agentData.score}%` }}
                    />
                  </div>
                  {detailed && (
                    <p className="text-xs text-gray-500 mt-1">{agentData.reasoning}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Narrative */}
      {detailed && narrative && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Investment Narrative</h3>

          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-700 mb-2">Thesis</h4>
              <p className="text-sm text-gray-600">{narrative.investment_thesis}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-green-700 mb-2 flex items-center">
                  <TrendingUp className="h-4 w-4 mr-1" />
                  Key Strengths
                </h4>
                <ul className="space-y-1">
                  {narrative.key_strengths.map((strength, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start">
                      <span className="text-green-600 mr-2">•</span>
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-medium text-red-700 mb-2 flex items-center">
                  <TrendingDown className="h-4 w-4 mr-1" />
                  Key Risks
                </h4>
                <ul className="space-y-1">
                  {narrative.key_risks.map((risk, i) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start">
                      <span className="text-red-600 mr-2">•</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-700 mb-2">Summary</h4>
              <p className="text-sm text-gray-600">{narrative.summary}</p>
            </div>

            <div className="text-xs text-gray-400">
              Generated by {narrative.provider}
            </div>
          </div>
        </div>
      )}

      {/* View Details Link */}
      {!detailed && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <Link
            to={`/stock/${symbol}`}
            className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center justify-center space-x-1"
          >
            <span>View Full Analysis</span>
            <TrendingUp className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}

// Export memoized component for better performance
export default memo(StockCard);
