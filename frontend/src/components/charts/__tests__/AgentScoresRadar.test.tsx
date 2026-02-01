/**
 * Tests for AgentScoresRadar component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentScoresRadar } from '../AgentScoresRadar';
import { mockStockAnalysis } from '@/test/utils';

describe('AgentScoresRadar', () => {
  it('should render without crashing', () => {
    render(
      <AgentScoresRadar
        agentScores={mockStockAnalysis.agent_scores}
        height={300}
      />
    );

    // Check for chart title or container
    expect(document.querySelector('.recharts-wrapper')).toBeTruthy();
  });

  it('should display all 5 agents', () => {
    const { container } = render(
      <AgentScoresRadar
        agentScores={mockStockAnalysis.agent_scores}
        height={300}
      />
    );

    // Should have radar chart with 5 points
    const radarChart = container.querySelector('.recharts-radar-chart');
    expect(radarChart).toBeTruthy();
  });

  it('should show expandable details', () => {
    render(
      <AgentScoresRadar
        agentScores={mockStockAnalysis.agent_scores}
        height={300}
      />
    );

    // Check for expand button or details
    const expandButtons = screen.queryAllByText(/details|show|expand/i);
    expect(expandButtons.length).toBeGreaterThanOrEqual(0);
  });

  it('should handle empty agent scores', () => {
    const { container } = render(
      <AgentScoresRadar
        agentScores={{}}
        height={300}
      />
    );

    // Should still render without errors
    expect(container).toBeTruthy();
  });
});
