/**
 * UniverseTable — NIFTY50 stocks ranked by composite score.
 * Shows all analyzed stocks with sub-scores (F/M/Q/Sent/Flow), delta, sparkline position, reco badge.
 * Links to /stock/:symbol for full drill-down.
 */

import { useState, useEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { RefreshCw, ArrowUpDown, ArrowUp, ArrowDown, ExternalLink, Search, TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { useStore } from '@/store/useStore';
import { cn } from '@/lib/utils';
import type { StockAnalysis, MarketRegime } from '@/types';

const AGENT_WEIGHT_KEYS: { key: string; label: string; short: string }[] = [
  { key: 'fundamentals',       label: 'Fundamentals', short: 'F' },
  { key: 'momentum',           label: 'Momentum',     short: 'M' },
  { key: 'quality',            label: 'Quality',      short: 'Q' },
  { key: 'sentiment',          label: 'Sentiment',    short: 'Sent' },
  { key: 'institutional_flow', label: 'Inst. Flow',   short: 'Flow' },
];

const REGIME_IMPACTS: Record<string, { maxPos: number; buyBoost: string; color: string }> = {
  BULL:     { maxPos: 10, buyBoost: 'no boost',  color: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
  SIDEWAYS: { maxPos: 7,  buyBoost: '+3 pts',    color: 'text-amber-700 bg-amber-50 border-amber-200' },
  BEAR:     { maxPos: 4,  buyBoost: '+10 pts',   color: 'text-red-700 bg-red-50 border-red-200' },
};

function RegimeBanner({ regime }: { regime: MarketRegime }) {
  const impact = REGIME_IMPACTS[regime.trend] ?? REGIME_IMPACTS.BULL;
  const TrendIcon = regime.trend === 'BULL' ? TrendingUp : regime.trend === 'BEAR' ? TrendingDown : Minus;
  const totalWeight = AGENT_WEIGHT_KEYS.reduce((s, k) => s + (regime.weights[k.key] || 0), 0);

  return (
    <div className={cn('rounded-xl border p-4 flex flex-col gap-3', impact.color)}>
      {/* Top row: regime label + badges */}
      <div className="flex flex-wrap items-center gap-2">
        <Activity className="w-4 h-4 shrink-0" />
        <span className="font-semibold text-sm tracking-wide">{regime.regime}</span>
        <span className={cn('flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border', impact.color)}>
          <TrendIcon className="w-3 h-3" /> {regime.trend}
        </span>
        <span className="text-xs font-medium px-2 py-0.5 rounded-full border bg-white/60 border-current">
          {regime.volatility} VOL
        </span>
        <span className="text-xs text-current/70 ml-auto">
          Max positions: <strong>{impact.maxPos}</strong> · Buy threshold boost: <strong>{impact.buyBoost}</strong>
        </span>
      </div>

      {/* Weight pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium opacity-70 mr-1">Agent weights:</span>
        {AGENT_WEIGHT_KEYS.map(({ key, label, short }) => {
          const w = regime.weights[key] || 0;
          const pct = totalWeight > 0 ? w / totalWeight : 0;
          const barW = Math.round(pct * 80); // px, max 80
          return (
            <span
              key={key}
              title={`${label}: ${(w * 100).toFixed(0)}%`}
              className="flex items-center gap-1.5 bg-white/70 border border-current/20 rounded-lg px-2 py-1 text-xs font-medium"
            >
              <span className="opacity-80">{short}</span>
              <div className="w-10 h-1.5 bg-current/10 rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-current/50" style={{ width: `${barW}px` }} />
              </div>
              <span className="font-bold">{(w * 100).toFixed(0)}%</span>
            </span>
          );
        })}
        {regime.cached && <span className="text-xs opacity-50 ml-auto">cached</span>}
      </div>
    </div>
  );
}

type SortKey = 'composite' | 'fundamentals' | 'momentum' | 'quality' | 'sentiment' | 'institutional_flow' | 'symbol';
type SortDir = 'asc' | 'desc';

function ScoreBreakdownPopup({ s, anchorRect }: { s: StockAnalysis; anchorRect: DOMRect }) {
  const bd = (s as any).score_breakdown;
  if (!bd) return null;

  type Row = { label: string; val: number; note?: string; bold?: boolean; sign?: boolean };
  const rows: Row[] = [
    { label: 'Weighted sum',     val: bd.weighted_sum,     note: 'agents × weights', sign: false },
    { label: '+ Currency',       val: bd.currency_adj,     note: 'USD/INR sector', sign: true },
    { label: '+ RBI rate',       val: bd.rbi_adj,          note: 'rate cycle', sign: true },
    { label: '+ Earnings accel', val: bd.earnings_acc_adj, note: 'EPS momentum', sign: true },
    { label: '+ RS accel',       val: bd.rs_accel_adj,     note: 'rel. strength trend', sign: true },
    { label: '+ Crude',          val: bd.crude_adj,        note: 'Brent oil', sign: true },
    { label: '= Raw score',      val: bd.raw_score,        note: 'overlay capped ±10', bold: true, sign: false },
  ];
  if (bd.regime_adj !== 0) rows.push({ label: '+ Regime adj', val: bd.regime_adj, note: 'BULL/BEAR scalar', sign: true });

  const top = anchorRect.bottom + window.scrollY + 4;
  const left = anchorRect.left + window.scrollX;

  return createPortal(
    <div
      className="fixed w-72 bg-white border border-gray-200 rounded-xl shadow-xl p-3 text-xs pointer-events-none"
      style={{ top, left, zIndex: 9999 }}
    >
      <div className="font-semibold text-gray-700 mb-2 border-b pb-1">How this score is built</div>
      {rows.map(r => (
        <div key={r.label} className={cn('flex justify-between py-0.5', r.bold && 'font-semibold border-t mt-1 pt-1')}>
          <span className="text-gray-500">
            {r.label}{r.note && <span className="text-gray-400 font-normal"> ({r.note})</span>}
          </span>
          <span className={cn('tabular-nums ml-2', r.sign ? (r.val > 0 ? 'text-emerald-600' : r.val < 0 ? 'text-red-500' : 'text-gray-400') : 'text-gray-800')}>
            {r.sign && r.val > 0 ? '+' : ''}{r.val.toFixed(1)}
          </span>
        </div>
      ))}
      {bd.normalization_applied && (
        <div className="mt-2 pt-2 border-t">
          <div className="flex justify-between font-semibold">
            <span className="text-gray-700">Final <span className="text-gray-400 font-normal">(percentile vs NIFTY50)</span></span>
            <span className="text-blue-600">{bd.final.toFixed(1)}</span>
          </div>
          <p className="text-gray-400 mt-1 leading-tight" style={{fontSize:'10px'}}>
            Cross-sectional normalization: raw {bd.raw_score} → percentile {bd.final}
          </p>
        </div>
      )}
      {bd.failed_agents?.length > 0 && (
        <p className="text-amber-600 mt-2 pt-1 border-t leading-tight" style={{fontSize:'10px'}}>
          ⚠ {bd.failed_agents.join(', ')} failed — weights renormalized
        </p>
      )}
    </div>,
    document.body
  );
}

function CompositeScoreCell({ s }: { s: StockAnalysis }) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const ref = useRef<HTMLSpanElement>(null);
  return (
    <span
      ref={ref}
      className={cn('text-base font-bold tabular-nums cursor-help underline decoration-dotted decoration-gray-300',
        s.composite_score >= 70 ? 'text-emerald-600' : s.composite_score >= 50 ? 'text-amber-600' : 'text-red-500'
      )}
      onMouseEnter={() => ref.current && setRect(ref.current.getBoundingClientRect())}
      onMouseLeave={() => setRect(null)}
    >
      {s.composite_score.toFixed(1)}
      {rect && <ScoreBreakdownPopup s={s} anchorRect={rect} />}
    </span>
  );
}

function ScoreCell({ v }: { v: number | null | undefined }) {
  if (v == null) return <span className="text-gray-300">—</span>;
  const color = v >= 70 ? 'text-emerald-600' : v >= 50 ? 'text-amber-600' : 'text-red-500';
  return <span className={cn('font-semibold tabular-nums', color)}>{v.toFixed(0)}</span>;
}

function MiniBar({ v, max = 100 }: { v: number | null | undefined; max?: number }) {
  if (v == null) return <div className="w-12 h-1.5 bg-gray-100 rounded-full" />;
  const pct = Math.min(100, Math.max(0, (v / max) * 100));
  const color = v >= 70 ? 'bg-emerald-400' : v >= 50 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="w-12 h-1.5 bg-gray-100 rounded-full overflow-hidden">
      <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

function RecoBadge({ reco }: { reco: string }) {
  const map: Record<string, string> = {
    STRONG_BUY: 'bg-emerald-200 text-emerald-800',
    BUY: 'bg-emerald-100 text-emerald-700',
    HOLD: 'bg-amber-100 text-amber-700',
    SELL: 'bg-red-100 text-red-700',
  };
  return (
    <span className={cn('text-xs font-semibold px-2 py-0.5 rounded whitespace-nowrap', map[reco] || 'bg-gray-100 text-gray-600')}>
      {reco.replace('_', ' ')}
    </span>
  );
}

export default function UniverseTable() {
  const navigate = useNavigate();
  const { getCachedTopPicks, cacheTopPicks, marketRegime, setMarketRegime } = useStore();
  const [stocks, setStocks] = useState<StockAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('composite');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [filter, setFilter] = useState('');

  const load = async (force = false) => {
    const cacheKey = '50:false';
    if (!force) {
      const cached = getCachedTopPicks(cacheKey);
      if (cached) { setStocks((cached as any).top_picks || []); return; }
    }
    setLoading(true);
    try {
      const res = await api.getTopPicks(50, false);
      cacheTopPicks(cacheKey, res);
      setStocks(res.top_picks || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    if (!marketRegime) {
      api.getMarketRegime().then(setMarketRegime).catch(() => {});
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const agentScore = (s: StockAnalysis, key: string): number | null => {
    const a = (s.agent_scores as any)?.[key];
    return a?.score ?? null;
  };

  const sorted = useMemo(() => {
    let list = [...stocks];
    if (filter.trim()) {
      const q = filter.trim().toUpperCase();
      list = list.filter(s => s.symbol.includes(q) || s.company_name?.toUpperCase().includes(q));
    }
    list.sort((a, b) => {
      let av: number, bv: number;
      if (sortKey === 'symbol') {
        return sortDir === 'asc'
          ? a.symbol.localeCompare(b.symbol)
          : b.symbol.localeCompare(a.symbol);
      } else if (sortKey === 'composite') {
        av = a.composite_score; bv = b.composite_score;
      } else {
        av = agentScore(a, sortKey) ?? -1;
        bv = agentScore(b, sortKey) ?? -1;
      }
      return sortDir === 'asc' ? av - bv : bv - av;
    });
    return list;
  }, [stocks, sortKey, sortDir, filter]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ k }: { k: SortKey }) => {
    if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 text-gray-300" />;
    return sortDir === 'desc'
      ? <ArrowDown className="w-3 h-3 text-blue-500" />
      : <ArrowUp className="w-3 h-3 text-blue-500" />;
  };

  const headers: { key: SortKey; label: string; title?: string }[] = [
    { key: 'symbol',             label: '#  Symbol' },
    { key: 'composite',          label: 'Score',       title: 'Composite score (0-100)' },
    { key: 'fundamentals',       label: 'F',           title: 'Fundamentals agent score' },
    { key: 'momentum',           label: 'M',           title: 'Momentum agent score' },
    { key: 'quality',            label: 'Q',           title: 'Quality agent score' },
    { key: 'sentiment',          label: 'Sent',        title: 'Sentiment agent score' },
    { key: 'institutional_flow', label: 'Flow',        title: 'Institutional flow agent score' },
  ];

  return (
    <div className="space-y-4">
      {/* Regime banner */}
      {marketRegime && <RegimeBanner regime={marketRegime} />}

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="Filter by symbol or name…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <button
          onClick={() => load(true)}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:border-gray-300 transition-colors"
        >
          <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
          Refresh
        </button>
        <span className="text-sm text-gray-400">{sorted.length} stocks</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {headers.map(h => (
                  <th
                    key={h.key}
                    title={h.title}
                    onClick={() => toggleSort(h.key)}
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 select-none whitespace-nowrap"
                  >
                    <span className="flex items-center gap-1">
                      {h.label}
                      <SortIcon k={h.key} />
                    </span>
                  </th>
                ))}
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Signal</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Bar</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading && stocks.length === 0 && (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-gray-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                    Loading universe…
                  </td>
                </tr>
              )}
              {sorted.map((s, i) => (
                <tr
                  key={s.symbol}
                  className="hover:bg-blue-50/40 cursor-pointer transition-colors"
                  onClick={() => navigate(`/stock/${s.symbol}`)}
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-xs text-gray-400 mr-2 font-mono w-5 inline-block">{i + 1}</span>
                    <span className="font-semibold text-gray-900">{s.symbol}</span>
                    {s.company_name && (
                      <span className="text-xs text-gray-400 ml-2 hidden md:inline truncate max-w-[120px]">
                        {s.company_name}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                    <CompositeScoreCell s={s} />
                  </td>
                  <td className="px-4 py-3"><ScoreCell v={agentScore(s, 'fundamentals')} /></td>
                  <td className="px-4 py-3"><ScoreCell v={agentScore(s, 'momentum')} /></td>
                  <td className="px-4 py-3"><ScoreCell v={agentScore(s, 'quality')} /></td>
                  <td className="px-4 py-3"><ScoreCell v={agentScore(s, 'sentiment')} /></td>
                  <td className="px-4 py-3"><ScoreCell v={agentScore(s, 'institutional_flow')} /></td>
                  <td className="px-4 py-3"><RecoBadge reco={s.recommendation} /></td>
                  <td className="px-4 py-3"><MiniBar v={s.composite_score} /></td>
                  <td className="px-4 py-3">
                    <ExternalLink className="w-3.5 h-3.5 text-gray-300 hover:text-blue-500" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
