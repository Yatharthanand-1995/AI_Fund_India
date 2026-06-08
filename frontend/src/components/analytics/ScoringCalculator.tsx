/**
 * ScoringCalculator — Analytics tab: enter any symbol, see full score decomposition
 * + where that score sits in the NIFTY50 distribution.
 */

import { useState, useCallback } from 'react';
import { Search, RefreshCw, Info } from 'lucide-react';
import api from '@/lib/api';
import { ScoreBreakdown } from '@/components/ScoreBreakdown';
import Loading from '@/components/ui/Loading';
import { DEFAULT_STOCK_SYMBOLS } from '@/lib/constants';
import type { StockAnalysis } from '@/types';

// Formula constants (must match backtester v4)
const WEIGHTS = { fundamentals: 0.36, momentum: 0.27, quality: 0.18, sentiment: 0.10, institutional_flow: 0.09 };
const BASE_OFFSET = 9.5;

function ScoreGauge({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';
  const circumference = 2 * Math.PI * 54;
  const dash = (pct / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="54" fill="none" stroke="#e5e7eb" strokeWidth="12" />
        <circle
          cx="70" cy="70" r="54"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={`${dash} ${circumference}`}
          strokeDashoffset={circumference / 4}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text x="70" y="66" textAnchor="middle" fontSize="28" fontWeight="700" fill={color}>{score.toFixed(1)}</text>
        <text x="70" y="84" textAnchor="middle" fontSize="11" fill="#6b7280">/ 100</text>
      </svg>
      <div className="text-xs font-medium text-gray-500 -mt-2">Composite Score</div>
    </div>
  );
}

function FormulaStrip({ analysis }: { analysis: StockAnalysis }) {
  const scores = analysis.agent_scores;
  const parts = Object.entries(WEIGHTS).map(([key, w]) => {
    const agentScore = (scores as any)[key]?.score ?? 0;
    return { key, w, agentScore, contribution: agentScore * w };
  });
  const weightedSum = parts.reduce((s, p) => s + p.contribution, 0);

  const totalAdj = (analysis.total_overlay_adj ?? 0) + (analysis.regime_adjustment ?? 0);
  const final = weightedSum + BASE_OFFSET + totalAdj;

  return (
    <div className="bg-slate-900 rounded-xl p-5 font-mono text-sm overflow-x-auto">
      <div className="text-slate-400 text-xs mb-3 uppercase tracking-wider">Formula (v4)</div>
      <div className="flex flex-wrap gap-2 items-center text-slate-200">
        {parts.map(({ key, w, agentScore, contribution }, i) => (
          <span key={key}>
            {i > 0 && <span className="text-slate-500 mx-1">+</span>}
            <span className="text-blue-300">{w}</span>
            <span className="text-slate-500">×</span>
            <span className="text-emerald-300">{agentScore.toFixed(1)}</span>
            <span className="text-slate-500 text-xs ml-0.5">({contribution.toFixed(1)})</span>
          </span>
        ))}
        <span className="text-slate-500 mx-1">+</span>
        <span className="text-yellow-300">{BASE_OFFSET}</span>
        {totalAdj !== 0 && (
          <>
            <span className="text-slate-500 mx-1">{totalAdj >= 0 ? '+' : ''}</span>
            <span className={totalAdj >= 0 ? 'text-emerald-300' : 'text-red-400'}>{totalAdj.toFixed(1)}</span>
            <span className="text-slate-500 text-xs">(adj)</span>
          </>
        )}
        <span className="text-slate-500 mx-2">=</span>
        <span className="text-white font-bold text-base">{final.toFixed(1)}</span>
      </div>
    </div>
  );
}

function PercentileBar({ score, allScores }: { score: number; allScores: number[] }) {
  if (allScores.length < 2) return null;
  const sorted = [...allScores].sort((a, b) => a - b);
  const below = sorted.filter(s => s < score).length;
  const percentile = Math.round((below / sorted.length) * 100);
  const zone = percentile >= 75 ? 'Top quartile' : percentile >= 50 ? 'Above median' : percentile >= 25 ? 'Below median' : 'Bottom quartile';
  const zoneColor = percentile >= 75 ? 'text-emerald-600' : percentile >= 50 ? 'text-amber-600' : 'text-red-600';

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-2 mb-3">
        <Info className="h-4 w-4 text-gray-400" />
        <span className="text-sm font-semibold text-gray-700">Score Percentile vs NIFTY50</span>
      </div>
      <div className="flex items-center gap-4 mb-3">
        <div className="text-3xl font-bold text-gray-900">{percentile}th</div>
        <div>
          <div className={`text-sm font-semibold ${zoneColor}`}>{zone}</div>
          <div className="text-xs text-gray-500">Better than {below} of {sorted.length} stocks analyzed</div>
        </div>
      </div>
      {/* Distribution bar */}
      <div className="relative h-8 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-red-300 via-amber-300 to-emerald-400 opacity-60"
          style={{ width: '100%' }}
        />
        {/* Score marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-gray-900"
          style={{ left: `${percentile}%` }}
        />
        <div
          className="absolute -top-0.5 text-xs font-bold text-gray-900 bg-white border border-gray-300 rounded px-1"
          style={{ left: `${Math.min(percentile, 85)}%`, transform: 'translateX(-50%)' }}
        >
          {score.toFixed(1)}
        </div>
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>Weak (0)</span>
        <span>Neutral (50)</span>
        <span>Strong (100)</span>
      </div>
    </div>
  );
}

export default function ScoringCalculator() {
  const [symbol, setSymbol] = useState('');
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [universeScores, setUniverseScores] = useState<number[]>([]);

  const analyze = useCallback(async (sym: string) => {
    const s = sym.trim().toUpperCase();
    if (!s) return;
    setLoading(true);
    setError(null);
    try {
      const [result, topPicks] = await Promise.all([
        api.analyzeStock({ symbol: s, include_narrative: false }),
        api.getTopPicks(50, false).catch(() => null),
      ]);
      setAnalysis(result);
      if (topPicks?.top_picks) {
        setUniverseScores(topPicks.top_picks.map((p: any) => p.composite_score));
      }
    } catch (err: any) {
      setError(err.message || 'Analysis failed');
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    analyze(symbol);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Scoring Calculator</h2>
        <p className="text-sm text-gray-600">
          Enter any NIFTY50 symbol to see exactly how the composite score is built — agent weights,
          signal adjustments, and where the stock ranks.
        </p>
        <form onSubmit={handleSubmit} className="mt-4 flex gap-3 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. TCS, INFY, RELIANCE"
              className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !symbol.trim()}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Analyze
          </button>
        </form>
        {/* Quick picks */}
        <div className="flex flex-wrap gap-2 mt-3">
          {DEFAULT_STOCK_SYMBOLS.slice(0, 8).map(s => (
            <button
              key={s}
              onClick={() => { setSymbol(s); analyze(s); }}
              className="px-2.5 py-1 text-xs bg-white border border-gray-200 hover:border-blue-300 text-gray-700 rounded-md transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-16">
          <Loading size="lg" text="Running analysis..." />
        </div>
      )}

      {/* Results */}
      {analysis && !loading && (
        <div className="space-y-6">
          {/* Header row: gauge + formula */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col items-center justify-center">
              <div className="text-sm font-semibold text-gray-500 mb-1">{analysis.symbol}</div>
              {analysis.company_name && (
                <div className="text-xs text-gray-400 mb-3 text-center">{analysis.company_name}</div>
              )}
              <ScoreGauge score={analysis.composite_score} />
              <div className={`mt-2 px-3 py-1 rounded-full text-xs font-semibold ${
                analysis.recommendation === 'BUY' || analysis.recommendation === 'STRONG_BUY'
                  ? 'bg-emerald-100 text-emerald-700'
                  : analysis.recommendation === 'SELL'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-amber-100 text-amber-700'
              }`}>
                {analysis.recommendation}
              </div>
            </div>
            <div className="md:col-span-2 space-y-4">
              <FormulaStrip analysis={analysis} />
              {universeScores.length > 0 && (
                <PercentileBar score={analysis.composite_score} allScores={universeScores} />
              )}
            </div>
          </div>

          {/* Full breakdown */}
          <ScoreBreakdown analysis={analysis} />
        </div>
      )}

      {/* Empty state */}
      {!analysis && !loading && !error && (
        <div className="text-center py-16 text-gray-400">
          <Search className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Enter a symbol above to see its full scoring breakdown</p>
        </div>
      )}
    </div>
  );
}
