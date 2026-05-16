import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, RefreshCw, Settings, Zap,
  ArrowUpRight, ArrowDownRight, Minus, Eye, AlertTriangle,
  CheckCircle2, XCircle, ChevronDown, ChevronUp, ShieldAlert,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import type {
  PortfolioConfig, PortfolioHolding, PortfolioSignal,
  EvaluationResult, PortfolioPerformance, ClosedTrade,
} from '@/types';

// ── helpers ──────────────────────────────────────────────────────────────────

function pct(v: number | null | undefined, digits = 1) {
  if (v == null) return '—';
  const s = v.toFixed(digits) + '%';
  return v >= 0 ? '+' + s : s;
}
function price(v: number | null | undefined) {
  if (v == null) return '—';
  return '₹' + v.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}
function score(v: number | null | undefined) {
  if (v == null) return '—';
  return v.toFixed(1);
}

const SIGNAL_META: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  BUY:        { label: 'BUY',       color: 'text-emerald-400 bg-emerald-400/10 border-emerald-500/30', icon: ArrowUpRight },
  HOLD:       { label: 'HOLD',      color: 'text-blue-400   bg-blue-400/10   border-blue-500/30',   icon: Minus },
  SELL_SCORE: { label: 'SELL',      color: 'text-red-400    bg-red-400/10    border-red-500/30',    icon: XCircle },
  SELL_STOP:  { label: 'STOP LOSS', color: 'text-red-500    bg-red-500/15    border-red-600/40',    icon: AlertTriangle },
  WATCH:      { label: 'WATCH',     color: 'text-amber-400  bg-amber-400/10  border-amber-500/30',  icon: Eye },
};

function SignalBadge({ signal }: { signal: string }) {
  const meta = SIGNAL_META[signal] ?? { label: signal, color: 'text-slate-400 bg-slate-700 border-slate-600', icon: Minus };
  const Icon = meta.icon;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-semibold', meta.color)}>
      <Icon className="w-3 h-3" />
      {meta.label}
    </span>
  );
}

function ReturnCell({ v }: { v: number | null | undefined }) {
  if (v == null) return <span className="text-slate-500">—</span>;
  return (
    <span className={cn('font-mono text-sm', v >= 0 ? 'text-emerald-400' : 'text-red-400')}>
      {pct(v)}
    </span>
  );
}

// ── Config panel ─────────────────────────────────────────────────────────────

function ConfigPanel({ config, onSave }: {
  config: PortfolioConfig;
  onSave: (c: Partial<PortfolioConfig>) => void;
}) {
  const [draft, setDraft] = useState(config);
  const [open, setOpen] = useState(false);

  const set = (k: keyof PortfolioConfig) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setDraft(d => ({ ...d, [k]: parseFloat(e.target.value) || 0 }));

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-slate-200"
      >
        <span className="flex items-center gap-2"><Settings className="w-4 h-4" /> Signal Thresholds</span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {open && (
        <div className="border-t border-slate-700 px-5 py-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {([
            ['buy_threshold',  'Buy ≥',         0, 100],
            ['sell_threshold', 'Sell <',         0, 100],
            ['stop_loss_pct',  'Stop Loss',    0.01,  0.3],
            ['max_positions',  'Max Positions',   1,   20],
            ['sector_cap_pct', 'Sector Cap',   0.1,    1],
          ] as [keyof PortfolioConfig, string, number, number][]).map(([key, label, min, max]) => (
            <label key={key} className="flex flex-col gap-1">
              <span className="text-xs text-slate-400">{label}</span>
              <input
                type="number" min={min} max={max}
                step={key === 'max_positions' ? 1 : key.includes('pct') ? 0.05 : 1}
                value={draft[key] as number}
                onChange={set(key)}
                className="w-full rounded-lg bg-slate-900 border border-slate-600 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
              />
            </label>
          ))}
          <div className="col-span-full flex justify-end">
            <button
              onClick={() => { onSave(draft); setOpen(false); }}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Score zone bar (shows score relative to sell/buy thresholds) ──────────────

function ScoreZoneBar({ s, sellThreshold = 50, buyThreshold = 65 }: {
  s: number; sellThreshold?: number; buyThreshold?: number;
}) {
  // Map score 0-100 to bar width; mark thresholds
  const sellPct = sellThreshold;
  const buyPct  = buyThreshold;
  const zone =
    s >= buyThreshold  ? 'bg-emerald-500' :
    s >= sellThreshold ? 'bg-amber-500'   : 'bg-red-500';

  return (
    <div className="relative h-2 bg-slate-700 rounded-full overflow-visible mt-2 mb-3">
      {/* Score fill */}
      <div
        className={cn('absolute h-full rounded-full transition-all duration-500', zone)}
        style={{ width: `${Math.min(s, 100)}%` }}
      />
      {/* Sell threshold marker */}
      <div
        className="absolute top-[-3px] bottom-[-3px] w-px bg-red-500/70"
        style={{ left: `${sellPct}%` }}
        title={`Sell threshold: ${sellPct}`}
      />
      {/* Buy threshold marker */}
      <div
        className="absolute top-[-3px] bottom-[-3px] w-px bg-emerald-500/70"
        style={{ left: `${buyPct}%` }}
        title={`Buy threshold: ${buyPct}`}
      />
      {/* Score label */}
      <span
        className={cn('absolute -top-5 text-[10px] font-mono font-bold -translate-x-1/2',
          s >= buyThreshold ? 'text-emerald-400' : s >= sellThreshold ? 'text-amber-400' : 'text-red-400'
        )}
        style={{ left: `${Math.min(Math.max(s, 4), 96)}%` }}
      >
        {s.toFixed(0)}
      </span>
    </div>
  );
}

// ── Signal rationale lines ────────────────────────────────────────────────────

function RationaleLine({ icon: Icon, text, color = 'text-slate-400' }: {
  icon: React.ElementType; text: string; color?: string;
}) {
  return (
    <div className={cn('flex items-start gap-1.5 text-[11px] leading-tight', color)}>
      <Icon className="w-3 h-3 mt-0.5 shrink-0" />
      <span>{text}</span>
    </div>
  );
}

// ── Signal card ───────────────────────────────────────────────────────────────

function SignalCard({ s, buyThreshold = 65, sellThreshold = 50 }: {
  s: PortfolioSignal; buyThreshold?: number; sellThreshold?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const sym = s.symbol.replace('.NS', '');

  // Build contextual rationale lines depending on signal type
  const rationale: Array<{ icon: React.ElementType; text: string; color?: string }> = [];

  if (s.signal === 'BUY') {
    rationale.push({ icon: ArrowUpRight, color: 'text-emerald-400',
      text: `Score ${s.composite_score.toFixed(1)} crossed buy threshold ≥ ${buyThreshold}` });
    if (s.recommendation) rationale.push({ icon: CheckCircle2, color: 'text-emerald-400',
      text: `System recommendation: ${s.recommendation}` });
    rationale.push({ icon: TrendingUp, color: 'text-slate-400',
      text: `Sector: ${s.sector}` });
  } else if (s.signal === 'SELL_SCORE') {
    rationale.push({ icon: TrendingDown, color: 'text-red-400',
      text: `Score ${s.composite_score.toFixed(1)} fell below sell threshold < ${sellThreshold}` });
    if (s.return_pct != null) rationale.push({
      icon: s.return_pct >= 0 ? ArrowUpRight : ArrowDownRight,
      color: s.return_pct >= 0 ? 'text-emerald-400' : 'text-red-400',
      text: `Exit with ${s.return_pct >= 0 ? 'gain' : 'loss'}: ${pct(s.return_pct)}`,
    });
    if (s.entry_price && s.current_price) rationale.push({ icon: Minus, color: 'text-slate-400',
      text: `Entry ${price(s.entry_price)} → Current ${price(s.current_price)}` });
  } else if (s.signal === 'SELL_STOP') {
    rationale.push({ icon: ShieldAlert, color: 'text-red-500',
      text: 'Trailing stop-loss triggered — price hit ATR-based floor' });
    if (s.return_pct != null) rationale.push({
      icon: ArrowDownRight, color: 'text-red-400',
      text: `Loss capped at: ${pct(s.return_pct)}`,
    });
    if (s.entry_price && s.current_price) rationale.push({ icon: Minus, color: 'text-slate-400',
      text: `Entry ${price(s.entry_price)} → Current ${price(s.current_price)}` });
  } else if (s.signal === 'HOLD') {
    rationale.push({ icon: Minus, color: 'text-blue-400',
      text: `Score ${s.composite_score.toFixed(1)} in hold zone (${sellThreshold}–${buyThreshold})` });
    if (s.return_pct != null) rationale.push({
      icon: s.return_pct >= 0 ? ArrowUpRight : ArrowDownRight,
      color: s.return_pct >= 0 ? 'text-emerald-400' : 'text-red-400',
      text: `Open P&L: ${pct(s.return_pct)}`,
    });
    if (s.entry_price) rationale.push({ icon: TrendingUp, color: 'text-slate-400',
      text: `Cost basis: ${price(s.entry_price)}` });
  } else if (s.signal === 'WATCH') {
    rationale.push({ icon: Eye, color: 'text-amber-400',
      text: `Score ${s.composite_score.toFixed(1)} qualifies but entry blocked` });
    rationale.push({ icon: AlertTriangle, color: 'text-amber-400',
      text: s.reason.length > 80 ? s.reason.slice(0, 80) + '…' : s.reason });
  }

  return (
    <div className={cn(
      'rounded-xl border bg-slate-800/60 p-4 hover:border-slate-500 transition-colors flex flex-col gap-0',
      s.signal === 'BUY'        ? 'border-emerald-500/30' :
      s.signal === 'SELL_STOP'  ? 'border-red-600/40' :
      s.signal === 'SELL_SCORE' ? 'border-red-500/30' :
      s.signal === 'WATCH'      ? 'border-amber-500/30' :
                                  'border-slate-700'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <Link to={`/stock/${sym}`}
          className="font-bold text-slate-100 hover:text-blue-400 transition-colors text-base">
          {sym}
        </Link>
        <SignalBadge signal={s.signal} />
      </div>
      <div className="text-[11px] text-slate-500 mt-0.5">{s.sector}</div>

      {/* Score zone bar */}
      <div className="mt-3">
        <ScoreZoneBar s={s.composite_score} buyThreshold={buyThreshold} sellThreshold={sellThreshold} />
        <div className="flex justify-between text-[9px] text-slate-600 -mt-1">
          <span>0</span>
          <span style={{ marginLeft: `${sellThreshold - 3}%` }} className="text-red-500/70">{sellThreshold}</span>
          <span style={{ marginLeft: `${buyThreshold - sellThreshold - 6}%` }} className="text-emerald-500/70">{buyThreshold}</span>
          <span>100</span>
        </div>
      </div>

      {/* Key metrics row */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
        <div>
          <div className="text-[10px] text-slate-500">Price</div>
          <div className="text-xs font-mono text-slate-200">{price(s.current_price)}</div>
        </div>
        {s.recommendation && (
          <div>
            <div className="text-[10px] text-slate-500">Rating</div>
            <div className="text-xs text-slate-300 font-medium">{s.recommendation}</div>
          </div>
        )}
        {s.entry_price != null && s.signal !== 'BUY' && (
          <div>
            <div className="text-[10px] text-slate-500">Entry</div>
            <div className="text-xs font-mono text-slate-300">{price(s.entry_price)}</div>
          </div>
        )}
        {s.return_pct != null && s.signal !== 'HOLD' && (
          <div>
            <div className="text-[10px] text-slate-500">P&amp;L</div>
            <ReturnCell v={s.return_pct} />
          </div>
        )}
      </div>

      {/* Rationale (always visible, condensed) */}
      {rationale.length > 0 && (
        <div className="mt-3 border-t border-slate-700/60 pt-2 space-y-1">
          {rationale.slice(0, expanded ? undefined : 2).map((r, i) => (
            <RationaleLine key={i} icon={r.icon} text={r.text} color={r.color} />
          ))}
          {rationale.length > 2 && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="text-[10px] text-slate-500 hover:text-slate-300 flex items-center gap-1 mt-0.5"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {expanded ? 'Less' : `+${rationale.length - 2} more`}
            </button>
          )}
        </div>
      )}

      {/* Full reason (collapsed, only for non-WATCH since WATCH shows reason in rationale) */}
      {s.signal !== 'WATCH' && s.reason && (
        <div className="mt-2 text-[10px] text-slate-600 line-clamp-2 leading-relaxed">
          {s.reason}
        </div>
      )}
    </div>
  );
}

// ── Stop proximity indicator ──────────────────────────────────────────────────

function StopProximity({ current, stop }: { current: number | undefined; stop: number | null | undefined }) {
  if (!current || !stop) return <span className="text-slate-600 text-xs">—</span>;
  const distPct = ((current - stop) / current) * 100;
  // stop > current means stop has already been breached (or stale data)
  if (distPct < 0) {
    return (
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-xs text-slate-300">{price(stop)}</span>
        <span className="text-[10px] flex items-center gap-0.5 text-red-500">
          <ShieldAlert className="w-2.5 h-2.5" /> Stop breached
        </span>
      </div>
    );
  }
  const danger = distPct < 5;
  const warning = distPct < 10;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-xs text-slate-300">{price(stop)}</span>
      <span className={cn('text-[10px] flex items-center gap-0.5',
        danger ? 'text-red-400' : warning ? 'text-amber-400' : 'text-slate-500'
      )}>
        {(danger || warning) && <ShieldAlert className="w-2.5 h-2.5" />}
        {distPct.toFixed(1)}% away
      </span>
    </div>
  );
}

// ── Holdings table ────────────────────────────────────────────────────────────

function HoldingsTable({ holdings }: { holdings: PortfolioHolding[] }) {
  if (!holdings.length) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 py-12 text-center text-slate-500">
        No open positions. Run <strong className="text-slate-300">Evaluate Signals</strong> to populate the portfolio.
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-slate-700 overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-800 text-slate-400 text-xs uppercase tracking-wide">
          <tr>
            {['Symbol', 'Sector', 'Entry', 'Current', 'Score', 'Return', 'Trailing Stop', 'Entry Date', 'Signal'].map(h => (
              <th key={h} className="px-4 py-3 text-left font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/60">
          {holdings.map(h => {
            const stopPct = h.trailing_stop_price && h.current_price
              ? ((h.current_price - h.trailing_stop_price) / h.current_price) * 100
              : null;
            const nearStop = stopPct != null && stopPct < 5;
            const sig = nearStop
              ? 'SELL_STOP'
              : h.current_score != null && h.current_score < 50
              ? 'SELL_SCORE'
              : 'HOLD';
            return (
              <tr key={h.id} className={cn(
                'hover:bg-slate-800/70 transition-colors',
                nearStop ? 'bg-red-900/10' : 'bg-slate-800/30'
              )}>
                <td className="px-4 py-3">
                  <Link to={`/stock/${h.symbol.replace('.NS', '')}`}
                    className="font-semibold text-slate-100 hover:text-blue-400">
                    {h.symbol.replace('.NS', '')}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">{h.sector}</td>
                <td className="px-4 py-3 font-mono text-slate-300 text-xs">{price(h.entry_price)}</td>
                <td className="px-4 py-3 font-mono text-slate-300 text-xs">{price(h.current_price)}</td>
                <td className="px-4 py-3 font-mono text-slate-300 text-xs">{score(h.current_score ?? h.entry_score)}</td>
                <td className="px-4 py-3"><ReturnCell v={h.return_pct} /></td>
                <td className="px-4 py-3">
                  <StopProximity current={h.current_price} stop={h.trailing_stop_price} />
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                  {new Date(h.entry_date).toLocaleDateString('en-IN')}
                </td>
                <td className="px-4 py-3"><SignalBadge signal={sig} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Closed trades table ───────────────────────────────────────────────────────

function ClosedTradesTable({ trades }: { trades: ClosedTrade[] }) {
  if (!trades.length) return null;
  return (
    <div className="rounded-xl border border-slate-700 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-800 text-slate-400 text-xs uppercase tracking-wide">
          <tr>
            {['Symbol', 'Sector', 'Entry', 'Exit', 'Return', 'Exit Reason', 'Date'].map(h => (
              <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/60">
          {trades.map(t => (
            <tr key={t.id} className="bg-slate-800/30 hover:bg-slate-800/70 transition-colors">
              <td className="px-4 py-3 font-semibold text-slate-100">{t.symbol.replace('.NS', '')}</td>
              <td className="px-4 py-3 text-slate-400">{t.sector}</td>
              <td className="px-4 py-3 font-mono text-slate-300">{price(t.entry_price)}</td>
              <td className="px-4 py-3 font-mono text-slate-300">{price(t.exit_price)}</td>
              <td className="px-4 py-3"><ReturnCell v={t.return_pct} /></td>
              <td className="px-4 py-3">
                <span className={cn('text-xs font-medium px-2 py-0.5 rounded',
                  t.exit_reason === 'stop_loss'
                    ? 'bg-red-900/40 text-red-400'
                    : t.exit_reason === 'manual'
                    ? 'bg-slate-700 text-slate-300'
                    : 'bg-orange-900/40 text-orange-400'
                )}>
                  {t.exit_reason.replace('_', ' ')}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-500 text-xs">
                {new Date(t.exit_date).toLocaleDateString('en-IN')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Performance stats bar ────────────────────────────────────────────────────

function PerfBar({ perf }: { perf: PortfolioPerformance | null }) {
  if (!perf) return null;
  const stats = [
    { label: 'Open',        v: perf.n_open,             fmt: (x: number) => x.toString(), color: '' },
    { label: 'Closed',      v: perf.n_closed,           fmt: (x: number) => x.toString(), color: '' },
    { label: 'Win Rate',    v: perf.win_rate * 100,      fmt: (x: number) => x.toFixed(1) + '%',
      color: perf.win_rate >= 0.5 ? 'text-emerald-400' : 'text-red-400' },
    { label: 'Avg Win',     v: perf.avg_win,             fmt: (x: number) => pct(x),
      color: 'text-emerald-400' },
    { label: 'Avg Loss',    v: perf.avg_loss,            fmt: (x: number) => pct(x),
      color: 'text-red-400' },
    { label: 'Best Trade',  v: perf.best_trade,          fmt: (x: number) => pct(x),
      color: 'text-emerald-400' },
    { label: 'Worst Trade', v: perf.worst_trade,         fmt: (x: number) => pct(x),
      color: 'text-red-400' },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
      {stats.map(s => (
        <div key={s.label} className="rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-3">
          <div className="text-xs text-slate-500 mb-1">{s.label}</div>
          <div className={cn('text-lg font-bold font-mono', s.color || 'text-slate-100')}>
            {s.fmt(s.v)}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Portfolio() {
  const [config, setConfig] = useState<PortfolioConfig | null>(null);
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [closedTrades, setClosedTrades] = useState<ClosedTrade[]>([]);
  const [perf, setPerf] = useState<PortfolioPerformance | null>(null);
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'signals' | 'holdings' | 'closed'>('signals');
  const [initialized, setInitialized] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cfg, h, c, p] = await Promise.all([
        api.getPortfolioConfig(),
        api.getPortfolioHoldings(),
        api.getClosedTrades(30),
        api.getPortfolioPerformance(),
      ]);
      setConfig(cfg);
      setHoldings(h.holdings);
      setClosedTrades(c.trades);
      setPerf(p);
      setInitialized(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Failed to load portfolio');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load on first render
  useState(() => { loadData(); });

  const handleEvaluate = async () => {
    setEvaluating(true);
    setError(null);
    try {
      const result = await api.evaluatePortfolio();
      setEvalResult(result);
      // Refresh holdings after evaluation (buys/sells may have changed)
      const [h, c, p] = await Promise.all([
        api.getPortfolioHoldings(),
        api.getClosedTrades(30),
        api.getPortfolioPerformance(),
      ]);
      setHoldings(h.holdings);
      setClosedTrades(c.trades);
      setPerf(p);
      setActiveTab('signals');
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Evaluation failed');
    } finally {
      setEvaluating(false);
    }
  };

  const handleSaveConfig = async (updates: Partial<PortfolioConfig>) => {
    try {
      const cfg = await api.updatePortfolioConfig(updates);
      setConfig(cfg);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to save config');
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all portfolio holdings and signal history? This cannot be undone.')) return;
    try {
      await api.resetPortfolio();
      setHoldings([]); setClosedTrades([]); setPerf(null); setEvalResult(null);
    } catch (e: any) {
      setError(e?.message ?? 'Reset failed');
    }
  };

  const buys    = evalResult?.buys    ?? [];
  const sells   = evalResult?.sells   ?? [];
  const holds   = evalResult?.holds   ?? [];
  const watches = evalResult?.watches ?? [];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-4 md:p-6 space-y-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Zap className="w-6 h-6 text-blue-400" />
            Live Portfolio
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Signal-driven paper portfolio — buy on score ≥ {config?.buy_threshold ?? 65},
            sell when score &lt; {config?.sell_threshold ?? 50} or stop-loss triggered
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-600 hover:border-slate-400 text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
            Refresh
          </button>
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-semibold transition-colors disabled:opacity-50"
          >
            <Zap className={cn('w-4 h-4', evaluating && 'animate-pulse')} />
            {evaluating ? 'Evaluating…' : 'Evaluate Signals'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-red-400 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Last evaluation summary */}
      {evalResult && (
        <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 px-5 py-4">
          <div className="flex flex-wrap items-center gap-6 text-sm">
            <span className="text-slate-400">
              Evaluated <span className="text-slate-200">{new Date(evalResult.evaluated_at).toLocaleString('en-IN')}</span>
            </span>
            <span className="text-slate-400">Regime: <span className="text-slate-200 font-medium">{evalResult.regime}</span></span>
            <span className="text-slate-400">Holdings: <span className="text-slate-200 font-medium">{evalResult.n_holdings}</span></span>
            {buys.length > 0 && (
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <ArrowUpRight className="w-3.5 h-3.5" />{buys.length} new buy{buys.length > 1 ? 's' : ''}
              </span>
            )}
            {sells.length > 0 && (
              <span className="flex items-center gap-1 text-red-400 font-medium">
                <ArrowDownRight className="w-3.5 h-3.5" />{sells.length} exit{sells.length > 1 ? 's' : ''}
              </span>
            )}
            {buys.length === 0 && sells.length === 0 && (
              <span className="flex items-center gap-1 text-slate-400">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> No changes — all positions in hold zone
              </span>
            )}
          </div>
        </div>
      )}

      {/* Config */}
      {config && <ConfigPanel config={config} onSave={handleSaveConfig} />}

      {/* Performance bar */}
      <PerfBar perf={perf} />

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-700">
        {([
          ['signals', 'Signals', evalResult ? buys.length + sells.length + holds.length : null],
          ['holdings', 'Open Positions', holdings.length],
          ['closed', 'Trade History', closedTrades.length],
        ] as [typeof activeTab, string, number | null][]).map(([tab, label, count]) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px',
              activeTab === tab
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            )}
          >
            {label}
            {count != null && (
              <span className={cn(
                'ml-2 text-xs px-1.5 py-0.5 rounded-full',
                activeTab === tab ? 'bg-blue-500/20 text-blue-300' : 'bg-slate-700 text-slate-400'
              )}>
                {count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'signals' && (
        <div className="space-y-6">
          {!evalResult && !evaluating && initialized && (
            <div className="rounded-xl border border-slate-700 bg-slate-800/40 py-16 text-center">
              <Zap className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 mb-4">Run the evaluator to generate live buy/hold/sell signals.</p>
              <button
                onClick={handleEvaluate}
                className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-semibold transition-colors"
              >
                Evaluate Signals Now
              </button>
            </div>
          )}

          {evalResult && (
            <>
              {buys.length > 0 && (
                <section>
                  <h2 className="text-base font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                    <ArrowUpRight className="w-4 h-4" /> New Buys ({buys.length})
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {buys.map(s => <SignalCard key={s.symbol} s={s}
                      buyThreshold={config?.buy_threshold ?? 65}
                      sellThreshold={config?.sell_threshold ?? 50} />)}
                  </div>
                </section>
              )}

              {sells.length > 0 && (
                <section>
                  <h2 className="text-base font-semibold text-red-400 mb-3 flex items-center gap-2">
                    <TrendingDown className="w-4 h-4" /> Exits ({sells.length})
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {sells.map(s => <SignalCard key={s.symbol} s={s}
                      buyThreshold={config?.buy_threshold ?? 65}
                      sellThreshold={config?.sell_threshold ?? 50} />)}
                  </div>
                </section>
              )}

              {holds.length > 0 && (
                <section>
                  <h2 className="text-base font-semibold text-blue-400 mb-3 flex items-center gap-2">
                    <Minus className="w-4 h-4" /> Held Positions ({holds.length})
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {holds.map(s => <SignalCard key={s.symbol} s={s}
                      buyThreshold={config?.buy_threshold ?? 65}
                      sellThreshold={config?.sell_threshold ?? 50} />)}
                  </div>
                </section>
              )}

              {watches.length > 0 && (
                <section>
                  <h2 className="text-base font-semibold text-amber-400 mb-3 flex items-center gap-2">
                    <Eye className="w-4 h-4" /> Watch List — High Score, Not Yet Bought ({watches.length})
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {watches.slice(0, 12).map(s => <SignalCard key={s.symbol} s={s}
                      buyThreshold={config?.buy_threshold ?? 65}
                      sellThreshold={config?.sell_threshold ?? 50} />)}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === 'holdings' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" /> Open Positions
            </h2>
            {holdings.length > 0 && (
              <button
                onClick={handleReset}
                className="text-xs text-red-400 hover:text-red-300 border border-red-500/30 px-3 py-1 rounded-lg transition-colors"
              >
                Reset Portfolio
              </button>
            )}
          </div>
          <HoldingsTable holdings={holdings} />
        </div>
      )}

      {activeTab === 'closed' && (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-slate-400" /> Closed Trades
          </h2>
          {closedTrades.length === 0
            ? <div className="rounded-xl border border-slate-700 bg-slate-800/40 py-12 text-center text-slate-500">No closed trades yet.</div>
            : <ClosedTradesTable trades={closedTrades} />
          }
        </div>
      )}

      {/* Methodology note */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-5 py-4 text-xs text-slate-500 space-y-1">
        <p className="font-medium text-slate-400">How it works</p>
        <p>
          <strong className="text-slate-300">Buy</strong> when composite score ≥ {config?.buy_threshold ?? 65} and sector limits allow.
          {' '}<strong className="text-slate-300">Hold</strong> as long as score stays above {config?.sell_threshold ?? 50} and position is above the stop-loss floor.
          {' '}<strong className="text-slate-300">Exit</strong> when score drops below {config?.sell_threshold ?? 50} (thesis broken) or price falls {((config?.stop_loss_pct ?? 0.1) * 100).toFixed(0)}%+ from entry (stop-loss).
          IT sector capped at 2 positions. All positions equal-weighted by score proportion.
          This is a paper portfolio — no real capital is traded.
        </p>
      </div>

    </div>
  );
}
