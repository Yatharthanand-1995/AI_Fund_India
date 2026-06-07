/**
 * SignalFeed — "What changed" feed for watchlist stocks.
 *
 * For each watchlist symbol, fetches 7-day score history and surfaces:
 * - Stocks with biggest score moves (up or down)
 * - Recommendation changes (HOLD→BUY, BUY→SELL etc.)
 * - Stocks that just entered top-20 or dropped out
 */

import { useState, useEffect } from 'react';
import { Activity, Minus, RefreshCw, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { useWatchlist } from '@/hooks/useWatchlist';
import { cn } from '@/lib/utils';

interface ScoreEvent {
  symbol: string;
  currentScore: number;
  prevScore: number;
  delta: number;
  currentReco: string;
  prevReco: string;
  recoChanged: boolean;
}

function recoBadgeColor(r: string) {
  if (r === 'BUY' || r === 'STRONG_BUY') return 'bg-emerald-100 text-emerald-700';
  if (r === 'SELL') return 'bg-red-100 text-red-700';
  return 'bg-amber-100 text-amber-700';
}

export default function SignalFeed({ maxItems = 6, compact = false }: { maxItems?: number; compact?: boolean }) {
  const navigate = useNavigate();
  const { watchlist } = useWatchlist();
  const [events, setEvents] = useState<ScoreEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadFeed = async () => {
    if (watchlist.length === 0) return;
    setLoading(true);
    try {
      const results = await Promise.allSettled(
        watchlist.map(w => api.getStockHistory(w.symbol, 14, false))
      );

      const evts: ScoreEvent[] = [];
      results.forEach((r, i) => {
        if (r.status !== 'fulfilled') return;
        const history = r.value?.history;
        if (!history || history.length < 2) return;

        const sym = watchlist[i].symbol;
        const latest = history[history.length - 1];
        const weekAgo = history[Math.max(0, history.length - 8)];
        if (!latest || !weekAgo) return;

        const currentScore = latest.composite_score ?? 0;
        const prevScore = weekAgo.composite_score ?? 0;
        const delta = currentScore - prevScore;

        const currentReco = latest.recommendation ?? '';
        const prevReco = weekAgo.recommendation ?? '';
        const recoChanged = currentReco !== prevReco && !!prevReco;

        if (Math.abs(delta) >= 1.0 || recoChanged) {
          evts.push({ symbol: sym, currentScore, prevScore, delta, currentReco, prevReco, recoChanged });
        }
      });

      // Sort by absolute delta descending, reco changes first
      evts.sort((a, b) => {
        if (a.recoChanged && !b.recoChanged) return -1;
        if (!a.recoChanged && b.recoChanged) return 1;
        return Math.abs(b.delta) - Math.abs(a.delta);
      });

      setEvents(evts.slice(0, maxItems));
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeed();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchlist.length]);

  if (watchlist.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400">
        <p className="text-sm">Add stocks to your watchlist to see score changes here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-500" />
          Score Changes (7d)
        </h3>
        <button
          onClick={loadFeed}
          disabled={loading}
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
        </button>
      </div>

      {loading && events.length === 0 && (
        <div className="text-center py-6 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
          <p className="text-xs">Loading score history...</p>
        </div>
      )}

      {!loading && events.length === 0 && lastUpdated && (
        <div className="text-center py-6 text-gray-400">
          <Minus className="w-5 h-5 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No significant score changes in the last 7 days.</p>
        </div>
      )}

      {events.map(evt => (
        <button
          key={evt.symbol}
          onClick={() => navigate(`/stock/${evt.symbol}`)}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors text-left"
        >
          {/* Icon */}
          <div className={cn('w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0',
            evt.delta > 2 ? 'bg-emerald-100' : evt.delta < -2 ? 'bg-red-100' : 'bg-amber-100'
          )}>
            {evt.delta > 0
              ? <ArrowUpRight className="w-4 h-4 text-emerald-600" />
              : evt.delta < 0
              ? <ArrowDownRight className="w-4 h-4 text-red-600" />
              : <Minus className="w-4 h-4 text-amber-600" />
            }
          </div>

          {/* Symbol + reco change */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-gray-900">{evt.symbol}</span>
              {evt.recoChanged && (
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium', recoBadgeColor(evt.prevReco))}>
                    {evt.prevReco.replace('_', ' ')}
                  </span>
                  <span>→</span>
                  <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium', recoBadgeColor(evt.currentReco))}>
                    {evt.currentReco.replace('_', ' ')}
                  </span>
                </span>
              )}
            </div>
            {!compact && (
              <p className="text-xs text-gray-500 mt-0.5">
                {evt.prevScore.toFixed(1)} → {evt.currentScore.toFixed(1)} over 7d
              </p>
            )}
          </div>

          {/* Delta */}
          <span className={cn('text-sm font-bold tabular-nums',
            evt.delta > 0 ? 'text-emerald-600' : evt.delta < 0 ? 'text-red-600' : 'text-gray-400'
          )}>
            {evt.delta >= 0 ? '+' : ''}{evt.delta.toFixed(1)}
          </span>
        </button>
      ))}

      {lastUpdated && (
        <p className="text-xs text-gray-400 text-right">
          Updated {lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
    </div>
  );
}

