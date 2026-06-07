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
  regime_adjustment:         { label: 'Market Regime',     desc: 'Additive regime modifier: BULL +≤3 pts, BEAR −≤3 pts, scaled by regime confidence' },
  rs_acceleration_adj:       { label: 'RS Acceleration',   desc: '3M vs 6M relative strength vs NIFTY — rewards building momentum' },
  earnings_acceleration_adj: { label: 'Earnings Accel',    desc: 'QoQ EPS growth trend — rewards accelerating earnings' },
  rbi_adjustment:             { label: 'RBI Rate Cycle',   desc: 'Sector adjustment based on RBI cutting/hiking cycle' },
  currency_adjustment:        { label: 'USD/INR Overlay',  desc: '20-day INR trend × sector currency sensitivity' },
  crude_adjustment:           { label: 'Crude Oil',         desc: 'Brent price level and trend × sector oil sensitivity' },
};

// Breakdown sub-score metadata: label, max pts, optional description
// Max values match the scoring agent implementations exactly.
const BREAKDOWN_META: Record<string, Record<string, { label: string; max: number; desc?: string }>> = {
  fundamentals: {
    profitability_score:  { label: 'Profitability',     max: 40, desc: 'ROE, ROA, profit & operating margins' },
    valuation_score:      { label: 'Valuation',         max: 25, desc: 'P/E, P/B, EV/EBITDA vs sector median' },
    growth_score:         { label: 'Growth',            max: 15, desc: 'Revenue & earnings growth rates' },
    health_score:         { label: 'Financial Health',  max: 10, desc: 'Debt ratio, liquidity, cash flow' },
    dividend_score:       { label: 'Dividend',          max: 5,  desc: 'Dividend yield & payout ratio' },
    promoter_bonus:       { label: 'Promoter Holding',  max: 5,  desc: 'Bonus for high promoter stake (>50%)' },
    pledge_penalty:       { label: 'Pledge Penalty',    max: 0,  desc: 'Deduction for pledged promoter shares' },
    pe_sector_adj:        { label: 'Sector P/E Adj.',   max: 5,  desc: 'P/E premium/discount vs sector peers' },
    earnings_quality_adj: { label: 'Earnings Quality',  max: 5,  desc: 'Cash conversion ratio quality check' },
  },
  momentum: {
    rsi_score:               { label: 'RSI (14)',          max: 25, desc: 'Relative Strength Index momentum zone' },
    trend_score:             { label: 'Trend Strength',   max: 27, desc: 'SMA 20/50/200 alignment & slope' },
    returns_score:           { label: 'Multi-Period Returns', max: 27, desc: 'Weighted 1M/3M/6M/12M returns' },
    relative_strength_score: { label: 'vs NIFTY',         max: 10, desc: '3M return relative to NIFTY 50' },
    breakout_bonus:          { label: 'Breakout / Penalty', max: 5, desc: 'Trend bonus or near-52W-high penalty' },
  },
  quality: {
    roe_score:      { label: 'Return on Equity',  max: 40, desc: 'ROE — primary quality signal' },
    leverage_score: { label: 'Leverage (D/E)',    max: 35, desc: 'Debt-to-equity ratio quality score' },
    stability_score:{ label: 'EPS Stability',     max: 25, desc: 'Earnings consistency (low variability)' },
  },
  sentiment: {
    diffusion_score:       { label: 'Analyst Consensus',  max: 40, desc: 'Buy/Hold/Sell distribution across analysts' },
    target_price_score:    { label: 'Price Target Upside', max: 30, desc: 'Analyst target vs current market price' },
    coverage_score:        { label: 'Analyst Coverage',   max: 20, desc: 'Number of analysts covering the stock' },
    news_adjustment:       { label: 'News Sentiment',     max: 10, desc: 'Recent news headlines tone (RSS)' },
    revision_adjustment:   { label: 'Estimate Revisions', max: 5,  desc: '30-day upgrade vs downgrade trend' },
    earnings_surprise_adj: { label: 'Earnings Surprise',  max: 5,  desc: 'Most recent EPS beat or miss magnitude' },
  },
  institutional_flow: {
    base_score:              { label: 'Base Score',        max: 50 },
    obv_adjustment:          { label: 'OBV Trend',         max: 15, desc: 'On-Balance Volume accumulation trend' },
    mfi_adjustment:          { label: 'Money Flow (MFI)',  max: 15, desc: 'Money Flow Index — buying/selling pressure' },
    cmf_adjustment:          { label: 'Chaikin MF',        max: 10, desc: 'Chaikin Money Flow over 20 periods' },
    volume_spike_adjustment: { label: 'Volume Surge',      max: 5,  desc: 'Unusual volume spike signal' },
    vwap_adjustment:         { label: 'VWAP Position',     max: 5,  desc: 'Price position relative to VWAP' },
    divergence_adjustment:   { label: 'Price-Vol Divergence', max: 5, desc: 'Bullish/bearish price-volume divergence' },
    fii_dii_adjustment:      { label: 'FII/DII Flows',     max: 15, desc: 'Net institutional buying (₹ crore, 30d)' },
    delivery_adjustment:     { label: 'Delivery %',        max: 10, desc: 'High delivery % = institutional conviction' },
    deals_adjustment:        { label: 'Bulk/Block Deals',  max: 5,  desc: 'Large institutional deal activity' },
  },
};

// Key data metrics shown below score factors — field names match API exactly
const AGENT_SUB_METRICS: Record<string, { key: string; label: string; unit?: string }[]> = {
  fundamentals: [
    { key: 'pe_ratio',             label: 'P/E Ratio' },
    { key: 'roe',                  label: 'ROE',              unit: '%' },
    { key: 'revenue_growth',       label: 'Revenue Growth',   unit: '%' },
    { key: 'debt_to_equity',       label: 'Debt / Equity' },
    { key: 'profit_margin',        label: 'Profit Margin',    unit: '%' },
    { key: 'cash_conversion_ratio',label: 'Cash Conv. Ratio' },
    { key: 'pe_vs_sector_mid',     label: 'Sector P/E Mid' },
    { key: 'promoter_holding',     label: 'Promoter Holding', unit: '%' },
    { key: 'dividend_yield',       label: 'Dividend Yield',   unit: '%' },
  ],
  momentum: [
    { key: 'rsi',       label: 'RSI (14)' },
    { key: '1m_return', label: '1M Return',  unit: '%' },
    { key: '3m_return', label: '3M Return',  unit: '%' },
    { key: '6m_return', label: '6M Return',  unit: '%' },
    { key: '1y_return', label: '12M Return', unit: '%' },
    { key: 'pct_from_52w_high', label: 'From 52W High', unit: '%' },
  ],
  quality: [
    { key: 'roe',               label: 'ROE',             unit: '%' },
    { key: 'debt_to_equity',    label: 'D/E Ratio' },
    { key: 'volatility',        label: 'Ann. Volatility', unit: '%' },
    { key: 'max_drawdown',      label: 'Max Drawdown',    unit: '%' },
    { key: 'eps_variability',   label: 'EPS Variability' },
    { key: 'return_consistency',label: 'Return Consistency' },
  ],
  sentiment: [
    { key: 'number_of_analyst_opinions', label: 'Analyst Coverage' },
    { key: 'upside_percent',             label: 'Analyst Upside',   unit: '%' },
    { key: 'recommendation_key',         label: 'Consensus' },
    { key: 'earnings_surprise_pct',      label: 'EPS Surprise',     unit: '%' },
    { key: 'news_headline_count',        label: 'News Headlines' },
  ],
  institutional_flow: [
    { key: 'obv_trend',       label: 'OBV Trend' },
    { key: 'mfi',             label: 'MFI (14)' },
    { key: 'cmf',             label: 'Chaikin MF' },
    { key: 'delivery_pct',   label: 'Delivery %',      unit: '%' },
    { key: 'fii_net_30d',    label: 'FII Net 30d',     unit: '₹Cr' },
    { key: 'price_vs_vwap',  label: 'Price vs VWAP',   unit: '%' },
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

      {/* Expanded detail panel */}
      {!compact && expanded && (
        <div className="mx-3 mb-2 rounded-lg bg-slate-900/60 border border-slate-700/60 overflow-hidden">

          {/* ── Section 1: Score Factors ───────────────────────────── */}
          {Object.keys(breakdown).length > 0 && (
            <div className="p-3 space-y-2">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1">
                Score Factors
              </div>
              {Object.entries(breakdown).map(([k, rawVal]) => {
                const v = rawVal as number;
                const bMeta = BREAKDOWN_META[agentKey]?.[k];
                const label = bMeta?.label ?? k.replace(/_score|_adj|_bonus|_penalty/g, '').replace(/_/g, ' ');
                const max = bMeta?.max ?? Math.abs(v);
                const desc = bMeta?.desc;
                const isNegative = v < 0;
                const barPct = max > 0 ? Math.min(Math.abs(v) / max * 100, 100) : 0;

                return (
                  <div key={k} className="group/factor">
                    <div className="flex items-center gap-2">
                      {/* Label */}
                      <div className="w-36 shrink-0">
                        <span className="text-[11px] text-slate-300">{label}</span>
                        {desc && (
                          <span className="ml-1 text-[10px] text-slate-600 hidden group-hover/factor:inline">{desc}</span>
                        )}
                      </div>
                      {/* Bar */}
                      <div className="flex-1 h-1.5 bg-slate-700/70 rounded-full overflow-hidden">
                        {max > 0 && (
                          <div
                            className={cn('h-full rounded-full transition-all duration-500',
                              isNegative ? 'bg-red-500/70' : v === 0 ? 'bg-slate-600' : 'bg-emerald-500/80'
                            )}
                            style={{ width: `${barPct}%` }}
                          />
                        )}
                      </div>
                      {/* Value / max */}
                      <div className="w-16 text-right shrink-0">
                        <span className={cn('text-[11px] font-mono font-semibold',
                          isNegative ? 'text-red-400' : v === 0 ? 'text-slate-600' : 'text-slate-200'
                        )}>
                          {isNegative ? '' : (v > 0 ? '+' : '')}{v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}
                        </span>
                        {max > 0 && (
                          <span className="text-[10px] text-slate-600"> / {max}</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              {/* Subtotal row */}
              <div className="flex items-center justify-between pt-1.5 border-t border-slate-700/40 mt-1">
                <span className="text-[10px] text-slate-500 uppercase tracking-wide">Agent Score</span>
                <span className={cn('text-sm font-bold font-mono', scoreColor(score))}>
                  {score % 1 === 0 ? score.toFixed(0) : score.toFixed(1)} / 100
                </span>
              </div>
            </div>
          )}

          {/* ── Section 2: Key Data ───────────────────────────────── */}
          {subMetrics.length > 0 && (
            <div className="border-t border-slate-700/40 p-3">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-2">
                Key Data
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2">
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
              </div>
            </div>
          )}

          {/* ── Section 3: Reasoning ─────────────────────────────── */}
          {agentData?.reasoning && (
            <div className="border-t border-slate-700/40 px-3 py-2.5">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1">
                Summary
              </div>
              <div className="text-[11px] text-slate-400 leading-relaxed">
                {agentData.reasoning}
              </div>
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

  // Signal adjustments from the scorer — listed in application order.
  // Formula: composite = Σ(agent_score × weight) + regime_adj + overlays
  const adjustments = [
    { key: 'regime_adjustment',         value: analysis.regime_adjustment ?? 0 },
    { key: 'rs_acceleration_adj',       value: analysis.rs_acceleration_adj ?? 0 },
    { key: 'earnings_acceleration_adj', value: analysis.earnings_acceleration_adj ?? 0 },
    { key: 'rbi_adjustment',            value: analysis.rbi_adjustment ?? 0 },
    { key: 'currency_adjustment',       value: analysis.currency_adjustment ?? 0 },
    { key: 'crude_adjustment',          value: analysis.crude_adjustment ?? 0 },
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

      {/* Score formula + regime/cycle footnote */}
      {!compact && (
        <div className="border-t border-slate-700/40 px-4 py-2 space-y-1.5">
          {/* Verifiable formula */}
          <div className="text-[10px] text-slate-600 font-mono">
            Score = agents×weights
            {adjustments.length > 0 && (
              <span className="text-slate-500">
                {' '}+ adjustments ({adjustments.reduce((s, a) => s + a.value, 0) >= 0 ? '+' : ''}{adjustments.reduce((s, a) => s + a.value, 0).toFixed(1)} pts)
              </span>
            )}
            {' '}= <span className="text-slate-300 font-semibold">{analysis.composite_score.toFixed(1)}</span>
          </div>
          {/* Context tags */}
          <div className="flex flex-wrap gap-3 text-[10px] text-slate-500">
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
        </div>
      )}
    </div>
  );
}

export default ScoreBreakdown;
