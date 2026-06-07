/**
 * UniverseTable — NIFTY50 stocks ranked by composite score.
 * Shows all analyzed stocks with sub-scores (F/M/Q/Sent/Flow), delta, sparkline position, reco badge.
 * Links to /stock/:symbol for full drill-down.
 */

import { useState, useEffect, useMemo } from 'react';
import { RefreshCw, ArrowUpDown, ArrowUp, ArrowDown, ExternalLink, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { useStore } from '@/store/useStore';
import { cn } from '@/lib/utils';
import type { StockAnalysis } from '@/types';

type SortKey = 'composite' | 'fundamentals' | 'momentum' | 'quality' | 'sentiment' | 'institutional_flow' | 'symbol';
type SortDir = 'asc' | 'desc';

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
  const { getCachedTopPicks, cacheTopPicks } = useStore();
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

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
                  <td className="px-4 py-3">
                    <span className={cn('text-base font-bold tabular-nums',
                      s.composite_score >= 70 ? 'text-emerald-600' : s.composite_score >= 50 ? 'text-amber-600' : 'text-red-500'
                    )}>
                      {s.composite_score.toFixed(1)}
                    </span>
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
