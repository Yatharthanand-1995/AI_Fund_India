/**
 * Smart Stock Suggestion Engine
 *
 * Generates personalized stock recommendations based on:
 * - Watchlist patterns
 * - Sector preferences
 * - Risk profile
 * - Agent score patterns
 */

import type { StockAnalysis } from '@/types';

export interface SuggestionReason {
  type: 'similar' | 'sector' | 'diversification' | 'trending' | 'gap';
  description: string;
  score: number;
}

export interface StockSuggestion {
  stock: StockAnalysis;
  reasons: SuggestionReason[];
  relevanceScore: number;
}

export interface PortfolioProfile {
  sectors: Record<string, number>;
  avgScore: number;
  avgReturn3m: number;
  avgVolatility: number;
  strongAgents: string[]; // Which agents score high in watchlist
  preferredMarketCap: 'large' | 'mid' | 'small' | 'mixed';
}

/**
 * Analyze watchlist to build user's investment profile
 */
export function analyzePortfolioProfile(watchlistStocks: StockAnalysis[]): PortfolioProfile {
  if (watchlistStocks.length === 0) {
    return {
      sectors: {},
      avgScore: 0,
      avgReturn3m: 0,
      avgVolatility: 0,
      strongAgents: [],
      preferredMarketCap: 'mixed',
    };
  }

  // Sector distribution
  const sectors: Record<string, number> = {};
  watchlistStocks.forEach(stock => {
    const sector = stock.agent_scores.quality?.metrics?.sector || 'Unknown';
    sectors[sector] = (sectors[sector] || 0) + 1;
  });

  // Average metrics
  const avgScore = watchlistStocks.reduce((sum, s) => sum + s.composite_score, 0) / watchlistStocks.length;
  const avgReturn3m = watchlistStocks.reduce((sum, s) =>
    sum + (s.agent_scores.momentum?.metrics?.['3m_return'] || 0), 0) / watchlistStocks.length;
  const avgVolatility = watchlistStocks.reduce((sum, s) =>
    sum + (s.agent_scores.quality?.metrics?.volatility || 0), 0) / watchlistStocks.length;

  // Which agents are strong in portfolio
  const agentScores = {
    fundamentals: 0,
    momentum: 0,
    quality: 0,
    sentiment: 0,
    institutional_flow: 0,
  };

  watchlistStocks.forEach(stock => {
    Object.keys(agentScores).forEach(agent => {
      const score = stock.agent_scores[agent as keyof typeof agentScores]?.score || 0;
      agentScores[agent as keyof typeof agentScores] += score;
    });
  });

  const avgAgentScores = Object.entries(agentScores).map(([agent, total]) => ({
    agent,
    avg: total / watchlistStocks.length,
  }));

  const strongAgents = avgAgentScores
    .filter(a => a.avg > 70)
    .map(a => a.agent);

  // Market cap preference
  const marketCaps = watchlistStocks.map(s => s.agent_scores.quality?.metrics?.market_cap || 0);
  const avgMarketCap = marketCaps.reduce((sum, mc) => sum + mc, 0) / marketCaps.length;

  let preferredMarketCap: 'large' | 'mid' | 'small' | 'mixed' = 'mixed';
  if (avgMarketCap > 5e11) preferredMarketCap = 'large'; // > 50k crores
  else if (avgMarketCap > 1e11) preferredMarketCap = 'mid'; // > 10k crores
  else if (avgMarketCap > 0) preferredMarketCap = 'small';

  return {
    sectors,
    avgScore,
    avgReturn3m,
    avgVolatility,
    strongAgents,
    preferredMarketCap,
  };
}

/**
 * Find similar stocks based on a reference stock
 */
export function findSimilarStocks(
  referenceStock: StockAnalysis,
  allStocks: StockAnalysis[],
  count: number = 5
): StockSuggestion[] {
  const suggestions: StockSuggestion[] = [];

  allStocks.forEach(stock => {
    if (stock.symbol === referenceStock.symbol) return;

    const reasons: SuggestionReason[] = [];
    let relevanceScore = 0;

    // Same sector
    const refSector = referenceStock.agent_scores.quality?.metrics?.sector;
    const stockSector = stock.agent_scores.quality?.metrics?.sector;
    if (refSector && stockSector && refSector === stockSector) {
      reasons.push({
        type: 'sector',
        description: `Same sector: ${stockSector}`,
        score: 25,
      });
      relevanceScore += 25;
    }

    // Similar score
    const scoreDiff = Math.abs(stock.composite_score - referenceStock.composite_score);
    if (scoreDiff < 10) {
      reasons.push({
        type: 'similar',
        description: `Similar score: ${stock.composite_score.toFixed(1)} vs ${referenceStock.composite_score.toFixed(1)}`,
        score: 20,
      });
      relevanceScore += 20;
    }

    // Similar agent pattern
    let agentSimilarity = 0;
    ['fundamentals', 'momentum', 'quality', 'sentiment', 'institutional_flow'].forEach(agent => {
      const refScore = referenceStock.agent_scores[agent as keyof typeof referenceStock.agent_scores]?.score || 0;
      const stockScore = stock.agent_scores[agent as keyof typeof stock.agent_scores]?.score || 0;
      const diff = Math.abs(refScore - stockScore);
      if (diff < 15) agentSimilarity += 1;
    });

    if (agentSimilarity >= 3) {
      reasons.push({
        type: 'similar',
        description: `Similar agent profile (${agentSimilarity}/5 agents match)`,
        score: 15,
      });
      relevanceScore += 15;
    }

    // Similar market cap
    const refMC = referenceStock.agent_scores.quality?.metrics?.market_cap || 0;
    const stockMC = stock.agent_scores.quality?.metrics?.market_cap || 0;
    if (refMC > 0 && stockMC > 0) {
      const mcRatio = Math.min(refMC, stockMC) / Math.max(refMC, stockMC);
      if (mcRatio > 0.5) { // Within 2x market cap
        reasons.push({
          type: 'similar',
          description: 'Similar market capitalization',
          score: 10,
        });
        relevanceScore += 10;
      }
    }

    if (reasons.length > 0) {
      suggestions.push({
        stock,
        reasons,
        relevanceScore,
      });
    }
  });

  return suggestions
    .sort((a, b) => b.relevanceScore - a.relevanceScore)
    .slice(0, count);
}

/**
 * Generate personalized recommendations
 */
export function generatePersonalizedSuggestions(
  profile: PortfolioProfile,
  allStocks: StockAnalysis[],
  watchlistSymbols: string[],
  count: number = 10
): StockSuggestion[] {
  const suggestions: StockSuggestion[] = [];

  allStocks.forEach(stock => {
    // Skip if already in watchlist
    if (watchlistSymbols.includes(stock.symbol)) return;

    const reasons: SuggestionReason[] = [];
    let relevanceScore = 0;

    // Sector match
    const stockSector = stock.agent_scores.quality?.metrics?.sector;
    if (stockSector && profile.sectors[stockSector]) {
      const sectorCount = profile.sectors[stockSector];
      reasons.push({
        type: 'sector',
        description: `You have ${sectorCount} ${stockSector} stocks`,
        score: 20,
      });
      relevanceScore += 20;
    }

    // Score match
    const scoreDiff = Math.abs(stock.composite_score - profile.avgScore);
    if (scoreDiff < 15) {
      reasons.push({
        type: 'similar',
        description: `Score matches your average (${profile.avgScore.toFixed(1)})`,
        score: 15,
      });
      relevanceScore += 15;
    }

    // Strong agents match
    profile.strongAgents.forEach(agent => {
      const agentScore = stock.agent_scores[agent as keyof typeof stock.agent_scores]?.score || 0;
      if (agentScore > 70) {
        reasons.push({
          type: 'similar',
          description: `Strong ${agent.replace('_', ' ')} (${agentScore.toFixed(0)})`,
          score: 10,
        });
        relevanceScore += 10;
      }
    });

    // High quality (always good)
    if (stock.composite_score >= 75 && stock.recommendation === 'STRONG BUY') {
      reasons.push({
        type: 'trending',
        description: 'High score with STRONG BUY recommendation',
        score: 25,
      });
      relevanceScore += 25;
    }

    if (reasons.length > 0) {
      suggestions.push({
        stock,
        reasons,
        relevanceScore,
      });
    }
  });

  return suggestions
    .sort((a, b) => b.relevanceScore - a.relevanceScore)
    .slice(0, count);
}

/**
 * Identify portfolio gaps and suggest diversification
 */
export function generateDiversificationSuggestions(
  profile: PortfolioProfile,
  allStocks: StockAnalysis[],
  watchlistSymbols: string[],
  count: number = 5
): StockSuggestion[] {
  const suggestions: StockSuggestion[] = [];

  // Find underrepresented sectors
  const allSectors = new Set(
    allStocks
      .map(s => s.agent_scores.quality?.metrics?.sector)
      .filter(Boolean)
  );

  const missingSectors = Array.from(allSectors).filter(
    sector => !profile.sectors[sector as string] || profile.sectors[sector as string] < 2
  );

  allStocks.forEach(stock => {
    if (watchlistSymbols.includes(stock.symbol)) return;
    if (stock.composite_score < 60) return; // Only suggest quality stocks

    const reasons: SuggestionReason[] = [];
    let relevanceScore = 0;

    const stockSector = stock.agent_scores.quality?.metrics?.sector;

    // Missing sector
    if (stockSector && missingSectors.includes(stockSector)) {
      reasons.push({
        type: 'gap',
        description: `Missing sector: ${stockSector}`,
        score: 30,
      });
      relevanceScore += 30;
    }

    // Diversification by volatility
    const stockVol = stock.agent_scores.quality?.metrics?.volatility || 0;
    const volDiff = Math.abs(stockVol - profile.avgVolatility);
    if (volDiff > 10) {
      const volType = stockVol < profile.avgVolatility ? 'lower' : 'higher';
      reasons.push({
        type: 'diversification',
        description: `${volType} volatility (${stockVol.toFixed(1)}% vs your avg ${profile.avgVolatility.toFixed(1)}%)`,
        score: 20,
      });
      relevanceScore += 20;
    }

    // Quality score for diversification
    if (stock.composite_score >= 70) {
      reasons.push({
        type: 'diversification',
        description: 'High quality pick for diversification',
        score: 15,
      });
      relevanceScore += 15;
    }

    if (reasons.length > 0) {
      suggestions.push({
        stock,
        reasons,
        relevanceScore,
      });
    }
  });

  return suggestions
    .sort((a, b) => b.relevanceScore - a.relevanceScore)
    .slice(0, count);
}

/**
 * Find trending opportunities
 */
export function generateTrendingSuggestions(
  allStocks: StockAnalysis[],
  watchlistSymbols: string[],
  count: number = 10
): StockSuggestion[] {
  const suggestions: StockSuggestion[] = [];

  allStocks.forEach(stock => {
    if (watchlistSymbols.includes(stock.symbol)) return;

    const reasons: SuggestionReason[] = [];
    let relevanceScore = 0;

    // Strong buy with high score
    if (stock.recommendation === 'STRONG BUY' && stock.composite_score >= 70) {
      reasons.push({
        type: 'trending',
        description: `STRONG BUY with ${stock.composite_score.toFixed(1)} score`,
        score: 30,
      });
      relevanceScore += 30;
    }

    // High momentum
    const momentum = stock.agent_scores.momentum?.score || 0;
    if (momentum >= 80) {
      reasons.push({
        type: 'trending',
        description: `High momentum (${momentum.toFixed(0)})`,
        score: 25,
      });
      relevanceScore += 25;
    }

    // Strong recent returns
    const return3m = stock.agent_scores.momentum?.metrics?.['3m_return'] || 0;
    if (return3m > 15) {
      reasons.push({
        type: 'trending',
        description: `Strong 3M return (+${return3m.toFixed(1)}%)`,
        score: 20,
      });
      relevanceScore += 20;
    }

    // All agents agree (high confidence)
    const agentScores = [
      stock.agent_scores.fundamentals?.score || 0,
      stock.agent_scores.momentum?.score || 0,
      stock.agent_scores.quality?.score || 0,
      stock.agent_scores.sentiment?.score || 0,
      stock.agent_scores.institutional_flow?.score || 0,
    ];
    const highScoreCount = agentScores.filter(s => s >= 70).length;
    if (highScoreCount >= 4) {
      reasons.push({
        type: 'trending',
        description: `${highScoreCount}/5 agents bullish`,
        score: 25,
      });
      relevanceScore += 25;
    }

    if (reasons.length > 0) {
      suggestions.push({
        stock,
        reasons,
        relevanceScore,
      });
    }
  });

  return suggestions
    .sort((a, b) => b.relevanceScore - a.relevanceScore)
    .slice(0, count);
}
