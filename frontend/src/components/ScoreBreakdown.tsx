/**
 * ScoreBreakdown — Interactive composite score decomposition panel
 *
 * Shows exactly how a stock's composite score was built:
 *   1. Each agent's contribution  (score × weight = pts)
 *   2. Signal adjustments         (RS accel, earnings accel, RBI overlay, currency)
 *   3. Per-agent sub-metrics on expand
 *
 * Used in StockDetails (full view) and StockCard / SignalCard (compact view).
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { StockAnalysis } from '@/types';

// ── helpers ──────────────────────────────────────────────────────────────────

function scoreColor(s: number) {
  if (s >= 70) return 'text-emerald-400';
  if (s >= 50) return 'text-amber-400';
  return 'text-red-400';
}

function barColor(s: number) {
  if (s >= 70) return 'bg-emerald-500';
  if (s >= 50) return 'bg-amber-500';
  return 'bg-red-500';
}

function adjColor(v: number) {
  if (v > 0) return 'text-emerald-400';
  if (v < 0) return 'text-red-400';
  return 'text-slate-500';
}

function fmtAdj(v: number) {
  return (v >= 0 ? '+' : '') + v.toFixed(1) + ' pts';
}

function fmt(v: number | null | undefined, digits = 1) {
  if (v == null) return '—';
  return v.toFixed(digits);
}

// Human-readable labels for each agent
const AGENT_META: Record<string, { label: string; desc: string; color: string }> = {
  fundamentals:      { label: 'Fundamentals',      color: 'bg-blue-500',    desc: 'P/E, ROE, growth, debt, cash flow quality' },
  momentum:          { label: 'Momentum',           color: 'bg-violet-500',  desc: 'RSI, MACD, 1–12M returns, relative strength' },
  quality:           { label: 'Quality',            color: 'bg-sky-500',     desc: 'Volatility, drawdown, return consistency, moat' },
  sentiment:         { label: 'Sentiment',          color: 'bg-amber-500',   desc: 'Analyst ratings, price targets, news' },
  institutional_flow:{ label: 'Institutional Flow', color: 'bg-rose-500',    desc: 'OBV, MFI, CMF, FII/DII flows, delivery %' },
};

// Human-readable labels for signal adjustments
const ADJ_META: Record<string, { label: string; desc: string }> = {
  rs_acceleration_adj:      { label: 'RS Acceleration',   desc: '3M vs 6M relative strength vs NIFTY — rewards building momentum' },
  earnings_acceleration_adj:{ label: 'Earnings Accel',    desc: 'QoQ EPS growth trend — rewards accelerating earnings' },
  rbi_adjustment:            { label: 'RBI Rate Cycle',    desc: 'Sector adjustment based on RBI cutting/hiking cycle' },
  currency_adjustment:       { label: 'USD/INR Overlay',   desc: '20-day INR trend × sector currency sensitivity' },
};

// Sub-metrics to show when an agent row is expanded
const AGENT_SUB_METRICS: Record<string, { key: string; label: string; unit?: string }[]> = {
  fundamentals: [
    { key: 'pe_ratio',            label: 'P/E Ratio' },
    { key: 'roe',                 label: 'ROE',             unit: '%' },
    { key: 'revenue_growth',      label: 'Revenue Growth',  unit: '%' },
    { key: 'debt_to_equity',      label: 'Debt / Equity' },
    { key: 'profit_margin',       label: 'Profit Margin',   unit: '%' },
    { key: 'cash_conversion_ratio',label: 'Cash Conv. Ratio' },
    { key: 'pe_vs_sector_mid',    label: 'Sector P/E Mid' },
    { key: 'promoter_holding',    label: 'Promoter Holding', unit: '%' },
    { key: 'dividend_yield',      label: 'Dividend Yield',  unit: '%' },
  ],
  momentum: [
    { key: 'rsi',                 label: 'RSI (14)' },
    { key: 'return_1m',           label: '1M Return',       unit: '%' },
    { key: 'return_3m',           label: '3M Return',       unit: '%' },
    { key: 'return_6m',           label: '6M Return',       unit: '%' },
    { key: 'return_12m',          label: '12M Return',      unit: '%' },
    { key: 'atr',                 label: 'ATR (14)' },
  ],
  quality: [
    { key: 'volatility',          label: 'Annualised Vol',  unit: '%' },
    { key: 'max_drawdown',        label: 'Max Drawdown',    unit: '%' },
    { key: 'return_consistency',  label: 'Return Consistency' },
  ],
  sentiment: [
    { key: 'analyst_count',       label: 'Analyst Coverage' },
    { key: 'target_upside_pct',   label: 'Analyst Upside',  unit: '%' },
    { key: 'buy_pct',             label: 'Buy Ratings',     unit: '%' },
  ],
  institutional_flow: [
    { key: 'obv_trend',           label: 'OBV Trend' },
    { key: 'mfi',                 label: 'MFI (14)' },
    { key: 'delivery_pct',        label: 'Delivery %',      unit: '%' },
    { key: 'fii_net_30d',         label: 'FII Net 30d (Cr)' },
  ],
};

// ── Sub-component: one agent row ─────────────────────────────────────────────

function AgentRow({
  agentKey,
  agentData,
  weight,
  compact,
}: {
  agentKey: string;
  agentData: any;
  weight: number;
  compact: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = AGENT_META[agentKey] ?? { label: agentKey, color: 'bg-slate-500', desc: '' };
  const score = agentData?.score ?? 0;
  const contribution = +(score * weight).toFixed(1);
  const subMetrics = AGENT_SUB_METRICS[agentKey] ?? [];
  const metrics = agentData?.metrics ?? {};
  const breakdown = agentData?.breakdown ?? {};

  return (
    <div className="space-y-1">
      <button
        onClick={() => !compact && setExpanded(e => !e)}
        className={cn(
          'w-full text-left',
          !compact && 'hover:bg-slate-700/40 rounded-lg transition-colors',
        )}
        disabled={compact}
      >
        <div className={cn('flex items-center gap-3', compact ? 'py-1' : 'px-3 py-2')}>
          {/* Label */}
          <div className="w-36 shrink-0">
            <div className="text-xs font-medium text-slate-300">{meta.label}</div>
            {!compact && (
              <div className="text-[10px] text-slate-500 leading-tight mt-0.5">{meta.desc}</div>
            )}
          </div>

          {/* Score bar */}
          <div className="flex-1 flex items-center gap-2">
            <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-500', meta.color)}
                style={{ width: `${Math.min(score, 100)}%` }}
              />
            </div>
            <span className={cn('text-xs font-mono w-8 text-right shrink-0', scoreColor(score))}>
              {score.toFixed(0)}
            </span>
          </div>

          {/* Weight pill */}
          <div className="w-10 text-right">
            <span className="text-xs text-slate-500">{(weight * 100).toFixed(0)}%</span>
          </div>

          {/* Contribution */}
          <div className="w-14 text-right">
            <span className={cn('text-xs font-mono font-semibold', scoreColor(score))}>
              +{contribution}
            </span>
          </div>

          {/* Expand chevron */}
          {!compact && subMetrics.length > 0 && (
            <div className="w-4 shrink-0 text-slate-600">
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </div>
          )}
        </div>
      </button>

      {/* Expanded sub-metrics */}
      {!compact && expanded && (
        <div className="mx-3 mb-2 rounded-lg bg-slate-900/60 border border-slate-700/60 p-3 grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2">
          {subMetrics.map(({ key, label, unit }) => {
            const val = metrics[key];
            if (val == null) return null;
            return (
              <div key={key}>
                <div className="text-[10px] text-slate-500">{label}</div>
                <div className="text-xs font-mono text-slate-200">
                  {typeof val === 'number' ? fmt(val, 2) : String(val)}
                  {unit && <span className="text-slate-500 ml-0.5">{unit}</span>}
                </div>
              </div>
            );
          })}
          {/* Breakdown sub-scores */}
          {Object.keys(breakdown).length > 0 && (
            <div className="col-span-full border-t border-slate-700/40 mt-1 pt-2 flex flex-wrap gap-x-4 gap-y-1">
              {Object.entries(breakdown).map(([k, v]) => (
                <div key={k}>
                  <span className="text-[10px] text-slate-500">{k.replace(/_score|_adj|_bonus|_penalty/g, '').replace(/_/g, ' ')}: </span>
                  <span className={cn('text-[10px] font-mono', (v as number) >= 0 ? 'text-slate-300' : 'text-red-400')}>
                    {(v as number) >= 0 ? '+' : ''}{(v as number).toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          )}
          {/* Reasoning snippet */}
          {agentData?.reasoning && (
            <div className="col-span-full text-[10px] text-slate-500 leading-relaxed border-t border-slate-700/40 mt-1 pt-2 line-clamp-3">
              {agentData.reasoning}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface ScoreBreakdownProps {
  analysis: StockAnalysis;
  compact?: boolean;        // true = no expand, smaller padding — for card use
  className?: string;
}

export function ScoreBreakdown({ analysis, compact = false, className }: ScoreBreakdownProps) {
  const weights = analysis.weights_used ?? analysis.weights ?? {};
  const agents = analysis.agent_scores ?? {};

  // Signal adjustments from the scorer
  const adjustments = [
    { key: 'rs_acceleration_adj',       value: analysis.rs_acceleration_adj ?? 0 },
    { key: 'earnings_acceleration_adj', value: analysis.earnings_acceleration_adj ?? 0 },
    { key: 'rbi_adjustment',            value: analysis.rbi_adjustment ?? 0 },
    { key: 'currency_adjustment',       value: analysis.currency_adjustment ?? 0 },
  ].filter(a => a.value !== 0);

  const rawScore = analysis.raw_composite_score ?? null;
  const finalScore = analysis.composite_score;

  return (
    <div className={cn('rounded-xl border border-slate-700 bg-slate-800/60 overflow-hidden', className)}>
      {/* Header row */}
      <div className={cn('flex items-center justify-between border-b border-slate-700/60', compact ? 'px-4 py-2.5' : 'px-4 py-3')}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Score Breakdown</span>
          {!compact && (
            <span className="text-[10px] text-slate-600 flex items-center gap-1">
              <Info className="w-3 h-3" /> Click an agent to see sub-metrics
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {rawScore != null && rawScore !== finalScore && (
            <span className="text-xs text-slate-500 font-mono">raw {rawScore.toFixed(1)} →</span>
          )}
          <span className={cn('text-lg font-bold font-mono', scoreColor(finalScore))}>
            {finalScore.toFixed(1)}
          </span>
          <span className="text-xs text-slate-500">/ 100</span>
        </div>
      </div>

      {/* Composite bar */}
      <div className={cn(compact ? 'px-4 py-2' : 'px-4 py-3')}>
        <div className="h-2.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-700', barColor(finalScore))}
            style={{ width: `${Math.min(finalScore, 100)}%` }}
          />
        </div>
      </div>

      {/* Column header */}
      {!compact && (
        <div className="px-6 pb-1 flex items-center gap-3 text-[10px] text-slate-600 uppercase tracking-wide">
          <div className="w-36 shrink-0">Agent</div>
          <div className="flex-1">Score</div>
          <div className="w-10 text-right">Weight</div>
          <div className="w-14 text-right">Contrib.</div>
          <div className="w-4" />
        </div>
      )}

      {/* Agent rows */}
      <div className={cn('space-y-0.5', compact ? 'px-2 pb-2' : 'px-1 pb-2')}>
        {Object.entries(agents).map(([key, data]) => {
          if (!data || data.score == null) return null;
          const w = weights[key] ?? 0;
          if (w === 0) return null;
          return (
            <AgentRow
              key={key}
              agentKey={key}
              agentData={data}
              weight={w}
              compact={compact}
            />
          );
        })}
      </div>

      {/* Signal adjustments */}
      {adjustments.length > 0 && (
        <div className={cn('border-t border-slate-700/60', compact ? 'px-4 py-2' : 'px-4 py-3')}>
          <div className="text-[10px] text-slate-500 uppercase tracking-wide mb-2 font-semibold">
            Signal Adjustments
          </div>
          <div className="space-y-1.5">
            {adjustments.map(({ key, value }) => {
              const meta = ADJ_META[key] ?? { label: key, desc: '' };
              return (
                <div key={key} className="flex items-center justify-between group">
                  <div>
                    <span className="text-xs text-slate-300">{meta.label}</span>
                    {!compact && (
                      <span className="ml-2 text-[10px] text-slate-600 hidden group-hover:inline">
                        {meta.desc}
                      </span>
                    )}
                  </div>
                  <span className={cn('text-xs font-mono font-semibold', adjColor(value))}>
                    {fmtAdj(value)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Regime + cycle footnote */}
      {!compact && (analysis.market_regime || analysis.rbi_rate_cycle) && (
        <div className="border-t border-slate-700/40 px-4 py-2 flex flex-wrap gap-3 text-[10px] text-slate-500">
          {analysis.market_regime && (
            <span>Regime: <span className="text-slate-300 font-medium">{analysis.market_regime.regime}</span></span>
          )}
          {analysis.rbi_rate_cycle && (
            <span>RBI cycle: <span className={cn('font-medium',
              analysis.rbi_rate_cycle === 'cutting' ? 'text-emerald-400' :
              analysis.rbi_rate_cycle === 'hiking'  ? 'text-red-400' : 'text-slate-300'
            )}>{analysis.rbi_rate_cycle}</span></span>
          )}
          {analysis.usdinr_trend && (
            <span>USD/INR: <span className="text-slate-300 font-medium">
              {analysis.usdinr_trend.direction} {analysis.usdinr_trend.trend_pct > 0 ? '+' : ''}{analysis.usdinr_trend.trend_pct.toFixed(1)}%
            </span></span>
          )}
        </div>
      )}
    </div>
  );
}

export default ScoreBreakdown;
