/**
 * Smart Stock Suggestions Page
 *
 * AI-powered stock recommendations based on:
 * - Watchlist patterns and preferences
 * - Portfolio gaps and diversification needs
 * - Trending opportunities
 * - Similar stocks discovery
 */

import { useState, useEffect, useMemo } from 'react';
import { Lightbulb, RefreshCw, TrendingUp, Target, Grid3x3, Sparkles } from 'lucide-react';
import Card from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';
import SuggestionCard from '@/components/suggestions/SuggestionCard';
import { useWatchlist } from '@/hooks/useWatchlist';
import api from '@/lib/api';
import { logger } from '@/lib/logger';
import type { StockAnalysis } from '@/types';
import {
  analyzePortfolioProfile,
  generatePersonalizedSuggestions,
  generateDiversificationSuggestions,
  generateTrendingSuggestions,
  type StockSuggestion,
  type PortfolioProfile,
} from '@/utils/suggestionEngine';

type SuggestionCategory = 'personalized' | 'diversification' | 'trending' | 'all';

export default function Suggestions() {
  const { watchlist } = useWatchlist();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<PortfolioProfile | null>(null);
  const [suggestions, setSuggestions] = useState<{
    personalized: StockSuggestion[];
    diversification: StockSuggestion[];
    trending: StockSuggestion[];
  }>({
    personalized: [],
    diversification: [],
    trending: [],
  });
  const [activeCategory, setActiveCategory] = useState<SuggestionCategory>('all');

  useEffect(() => {
    loadSuggestions();
  }, [watchlist]);

  const loadSuggestions = async () => {
    setLoading(true);
    try {
      // Load all stocks for analysis
      const response = await api.getTopPicks(100, false);
      const stocks = response.top_picks || [];

      // Load watchlist stock analyses
      const watchlistSymbols = watchlist.map(w => w.symbol);
      const watchlistAnalyses = await Promise.all(
        watchlistSymbols.slice(0, 20).map(symbol =>
          api.analyzeStock({ symbol, include_narrative: false }).catch(() => null)
        )
      );
      const validWatchlistStocks = watchlistAnalyses.filter(a => a !== null) as StockAnalysis[];

      // Analyze user profile
      const userProfile = analyzePortfolioProfile(validWatchlistStocks);
      setProfile(userProfile);

      // Generate suggestions
      const personalized = generatePersonalizedSuggestions(
        userProfile,
        stocks,
        watchlistSymbols,
        15
      );

      const diversification = generateDiversificationSuggestions(
        userProfile,
        stocks,
        watchlistSymbols,
        10
      );

      const trending = generateTrendingSuggestions(
        stocks,
        watchlistSymbols,
        15
      );

      setSuggestions({
        personalized,
        diversification,
        trending,
      });
    } catch (error) {
      logger.error('Failed to load suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  const displayedSuggestions = useMemo((): StockSuggestion[] => {
    switch (activeCategory) {
      case 'personalized':
        return suggestions.personalized;
      case 'diversification':
        return suggestions.diversification;
      case 'trending':
        return suggestions.trending;
      case 'all': {
        // Combine all, dedupe, and sort by relevance
        const allSugs = [
          ...suggestions.personalized,
          ...suggestions.diversification,
          ...suggestions.trending,
        ];
        const uniqueSugs = allSugs.reduce((acc, sug) => {
          if (!acc.find(s => s.stock.symbol === sug.stock.symbol)) {
            acc.push(sug);
          }
          return acc;
        }, [] as StockSuggestion[]);
        return uniqueSugs.sort((a, b) => b.relevanceScore - a.relevanceScore).slice(0, 20);
      }
      default:
        return [];
    }
  }, [activeCategory, suggestions]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Lightbulb className="h-8 w-8 text-blue-600" />
            Smart Suggestions
          </h1>
          <p className="text-gray-600 mt-2">
            AI-powered stock recommendations personalized for you
          </p>
        </div>
        <Card>
          <div className="p-12">
            <Loading size="lg" text="Generating personalized suggestions..." />
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Lightbulb className="h-8 w-8 text-blue-600" />
            Smart Suggestions
          </h1>
          <p className="text-gray-600 mt-2">
            {watchlist.length > 0
              ? `${displayedSuggestions.length} personalized recommendations based on your ${watchlist.length} watchlist stocks`
              : 'Add stocks to your watchlist to get personalized recommendations'}
          </p>
        </div>
        <button
          onClick={loadSuggestions}
          className="btn-primary"
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Portfolio Profile Summary */}
      {profile && watchlist.length > 0 && (
        <Card className="bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Target className="h-5 w-5 text-blue-600" />
              Your Investment Profile
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-600">Avg Score</p>
                <p className="text-xl font-bold text-gray-900">{profile.avgScore.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Avg 3M Return</p>
                <p
                  className={`text-xl font-bold ${
                    profile.avgReturn3m >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {profile.avgReturn3m > 0 ? '+' : ''}
                  {profile.avgReturn3m.toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Top Sectors</p>
                <p className="text-sm font-semibold text-gray-900">
                  {Object.entries(profile.sectors)
                    .sort(([, a], [, b]) => (b as number) - (a as number))
                    .slice(0, 2)
                    .map(([sector]) => sector.split(' ')[0])
                    .join(', ')}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Strong Agents</p>
                <p className="text-sm font-semibold text-gray-900">
                  {profile.strongAgents.length > 0
                    ? profile.strongAgents
                        .map(a => a.charAt(0).toUpperCase() + a.slice(1, 3))
                        .join(', ')
                    : 'Mixed'}
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Category Filters */}
      <Card>
        <div className="p-4">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setActiveCategory('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                activeCategory === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Grid3x3 className="h-4 w-4" />
              All Suggestions ({
                suggestions.personalized.length +
                suggestions.diversification.length +
                suggestions.trending.length
              })
            </button>
            <button
              onClick={() => setActiveCategory('personalized')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                activeCategory === 'personalized'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Sparkles className="h-4 w-4" />
              For You ({suggestions.personalized.length})
            </button>
            <button
              onClick={() => setActiveCategory('diversification')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                activeCategory === 'diversification'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Target className="h-4 w-4" />
              Diversify ({suggestions.diversification.length})
            </button>
            <button
              onClick={() => setActiveCategory('trending')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                activeCategory === 'trending'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <TrendingUp className="h-4 w-4" />
              Trending ({suggestions.trending.length})
            </button>
          </div>
        </div>
      </Card>

      {/* Suggestions Grid */}
      {displayedSuggestions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayedSuggestions.map(suggestion => (
            <SuggestionCard key={suggestion.stock.symbol} suggestion={suggestion} />
          ))}
        </div>
      ) : (
        <Card>
          <div className="p-12 text-center">
            <Lightbulb className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {watchlist.length === 0
                ? 'Add stocks to get started'
                : 'No suggestions available'}
            </h3>
            <p className="text-gray-600">
              {watchlist.length === 0
                ? 'Add stocks to your watchlist to receive personalized recommendations'
                : 'Try refreshing or adjusting your watchlist'}
            </p>
          </div>
        </Card>
      )}

      {/* Info Panel */}
      <Card className="bg-blue-50 border-blue-200">
        <div className="p-4">
          <h3 className="font-medium text-blue-900 mb-2">💡 How Suggestions Work</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>
              • <strong>For You</strong> - Based on your watchlist patterns (sectors, scores,
              agents)
            </li>
            <li>
              • <strong>Diversify</strong> - Fills gaps in your portfolio (missing sectors, risk
              balance)
            </li>
            <li>
              • <strong>Trending</strong> - High-scoring stocks with strong momentum and STRONG BUY
              signals
            </li>
            <li>
              • <strong>Relevance Score</strong> - Higher scores mean better match for your
              investment style
            </li>
          </ul>
        </div>
      </Card>
    </div>
  );
}
