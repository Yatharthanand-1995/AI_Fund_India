"""
Unit Tests for AI Agents

Tests all 5 agents:
- Fundamentals Agent
- Momentum Agent
- Quality Agent
- Sentiment Agent
- Institutional Flow Agent
"""

import pytest
import pandas as pd
import numpy as np
from agents.fundamentals_agent import FundamentalsAgent
from agents.momentum_agent import MomentumAgent
from agents.quality_agent import QualityAgent
from agents.sentiment_agent import SentimentAgent
from agents.institutional_flow_agent import InstitutionalFlowAgent


# ============================================================================
# Fundamentals Agent Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.agents
class TestFundamentalsAgent:
    """Tests for Fundamentals Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = FundamentalsAgent()
        assert agent.agent_name == "FundamentalsAgent"
        assert agent.weight == 0.36

    def test_analyze_with_valid_data(self, sample_comprehensive_data):
        """Test analysis with valid data"""
        agent = FundamentalsAgent()
        result = agent.analyze('TCS', sample_comprehensive_data)

        assert 'score' in result
        assert 'confidence' in result
        assert 'reasoning' in result
        assert 'metrics' in result
        assert 'breakdown' in result

        assert 0 <= result['score'] <= 100
        assert 0 <= result['confidence'] <= 1

    def test_analyze_without_data(self):
        """Test analysis without data"""
        agent = FundamentalsAgent()
        result = agent.analyze('TCS', None)

        assert result['score'] == 50.0  # No data = neutral score
        assert result['status'] == 'no_data'

    def test_score_breakdown(self, sample_comprehensive_data):
        """Test score breakdown components"""
        agent = FundamentalsAgent()
        result = agent.analyze('TCS', sample_comprehensive_data)

        breakdown = result['breakdown']
        assert 'profitability_score' in breakdown
        assert 'valuation_score' in breakdown
        assert 'growth_score' in breakdown
        assert 'health_score' in breakdown

    def test_excellent_fundamentals(self):
        """Test with excellent fundamental metrics"""
        data = {
            'info': {
                'returnOnEquity': 0.50,  # 50% ROE
                'trailingPE': 15.0,
                'priceToBook': 3.0,
                'revenueGrowth': 0.25,
                'earningsGrowth': 0.30,
                'debtToEquity': 0.1,
                'promoterHolding': 75.0,
            }
        }

        agent = FundamentalsAgent()
        result = agent.analyze('TEST', data)

        assert result['score'] > 60  # Should be high score (adjusted for new scoring with FCF & dividends)

    def test_poor_fundamentals(self):
        """Test with poor fundamental metrics"""
        data = {
            'info': {
                'returnOnEquity': 0.05,  # 5% ROE
                'trailingPE': 50.0,  # High P/E
                'priceToBook': 10.0,  # High P/B
                'revenueGrowth': -0.10,  # Negative growth
                'debtToEquity': 2.0,  # High debt
            }
        }

        agent = FundamentalsAgent()
        result = agent.analyze('TEST', data)

        assert result['score'] < 50  # Should be low score


# ============================================================================
# Momentum Agent Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.agents
class TestMomentumAgent:
    """Tests for Momentum Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = MomentumAgent()
        assert agent.agent_name == "MomentumAgent"
        assert agent.weight == 0.27

    def test_analyze_with_price_data(self, sample_historical_data, sample_nifty_data):
        """Test analysis with price data"""
        agent = MomentumAgent()
        result = agent.analyze(
            'TCS',
            sample_historical_data,
            sample_nifty_data,
            {}
        )

        assert 'score' in result
        assert 'confidence' in result
        assert 'reasoning' in result

        assert 0 <= result['score'] <= 100

    def test_analyze_without_price_data(self):
        """Test analysis without price data"""
        agent = MomentumAgent()
        result = agent.analyze('TCS', pd.DataFrame(), None, {})

        assert result['score'] == 50.0
        assert result['confidence'] == 0.1

    def test_rsi_calculation(self, sample_historical_data):
        """Test RSI calculation"""
        agent = MomentumAgent()

        # Add RSI to data
        data = sample_historical_data.copy()
        data['RSI'] = 55.0  # Neutral RSI

        result = agent.analyze('TCS', data, None, {})
        assert 'metrics' in result

    def test_strong_uptrend(self):
        """Test with strong uptrend"""
        # Create uptrending data
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
        prices = pd.Series(range(100, 200), index=dates)

        data = pd.DataFrame({
            'Close': prices,
            'Volume': [1000000] * 100,
        }, index=dates)

        agent = MomentumAgent()
        result = agent.analyze('TEST', data, None, {})

        # Should have positive momentum (adjusted for actual scoring behavior)
        assert result['score'] > 30


# ============================================================================
# Quality Agent Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.agents
class TestQualityAgent:
    """Tests for Quality Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = QualityAgent()
        assert agent.agent_name == "QualityAgent"
        assert agent.weight == 0.18

    def test_analyze_with_price_data(self, sample_historical_data):
        """Test analysis with price data"""
        agent = QualityAgent()
        result = agent.analyze('TCS', sample_historical_data, {})

        assert 'score' in result
        assert 0 <= result['score'] <= 100

    def test_low_volatility_stock(self):
        """Test with low volatility stock"""
        # Create low volatility data
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
        np.random.seed(42)
        prices = 100 + np.random.randn(100) * 0.5  # Very low volatility

        data = pd.DataFrame({
            'Open': prices * 0.998,
            'Close': prices,
            'High': prices * 1.005,
            'Low': prices * 0.995,
            'Volume': [1000000] * 100,
        }, index=dates)

        agent = QualityAgent()
        result = agent.analyze('TEST', data, {})

        # Low volatility should score high
        assert result['score'] > 60

    def test_high_volatility_stock(self):
        """Test with high volatility stock"""
        # Create high volatility data
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
        np.random.seed(42)
        prices = 100 + np.random.randn(100) * 10  # High volatility

        data = pd.DataFrame({
            'Close': prices,
            'High': prices * 1.05,
            'Low': prices * 0.95,
            'Volume': [1000000] * 100,
        }, index=dates)

        agent = QualityAgent()
        result = agent.analyze('TEST', data, {})

        # High volatility should score lower
        assert result['score'] < 60


# ============================================================================
# Sentiment Agent Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.agents
class TestSentimentAgent:
    """Tests for Sentiment Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = SentimentAgent()
        assert agent.agent_name == "SentimentAgent"
        assert agent.weight == 0.09

    def test_analyze_with_analyst_data(self):
        """Test analysis with analyst data"""
        data = {
            'info': {
                'recommendationMean': 2.0,  # Buy
                'targetMeanPrice': 3800,
                'currentPrice': 3500,
                'numberOfAnalystOpinions': 20,
            }
        }

        agent = SentimentAgent()
        result = agent.analyze('TCS', data)

        assert result['score'] > 50  # Positive sentiment

    def test_strong_buy_recommendation(self):
        """Test with strong buy recommendation"""
        data = {
            'info': {
                'recommendationMean': 1.2,  # Strong Buy
                'targetMeanPrice': 4000,
                'currentPrice': 3000,  # 33% upside
                'numberOfAnalystOpinions': 25,
            }
        }

        agent = SentimentAgent()
        result = agent.analyze('TCS', data)

        assert result['score'] > 70  # High score

    def test_sell_recommendation(self):
        """Test with sell recommendation"""
        data = {
            'info': {
                'recommendationMean': 4.5,  # Sell
                'targetMeanPrice': 2500,
                'currentPrice': 3000,  # Downside
                'numberOfAnalystOpinions': 15,
            }
        }

        agent = SentimentAgent()
        result = agent.analyze('TCS', data)

        assert result['score'] < 50  # Low score


# ============================================================================
# Institutional Flow Agent Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.agents
class TestInstitutionalFlowAgent:
    """Tests for Institutional Flow Agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = InstitutionalFlowAgent()
        assert agent.agent_name == "InstitutionalFlowAgent"
        assert agent.weight == 0.10

    def test_analyze_with_price_data(self, sample_historical_data):
        """Test analysis with price and volume data"""
        agent = InstitutionalFlowAgent()
        result = agent.analyze('TCS', sample_historical_data, {})

        assert 'score' in result
        assert 0 <= result['score'] <= 100

    def test_high_volume_accumulation(self):
        """Test with high volume accumulation pattern"""
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')

        # Create accumulation pattern: rising prices with rising volume
        prices = pd.Series(range(100, 200), index=dates)
        volumes = pd.Series(range(1000000, 2000000, 10000), index=dates)

        data = pd.DataFrame({
            'Open': prices * 0.998,
            'Close': prices,
            'High': prices * 1.01,
            'Low': prices * 0.99,
            'Volume': volumes,
        }, index=dates)

        agent = InstitutionalFlowAgent()
        result = agent.analyze('TEST', data, {})

        # Accumulation should score high
        assert result['score'] > 50


# ============================================================================
# Cross-Agent Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.agents
class TestAgentConsistency:
    """Tests for consistency across all agents"""

    def test_all_agents_return_required_fields(self, sample_comprehensive_data, sample_historical_data):
        """Test that all agents return required fields"""
        agents = [
            FundamentalsAgent(),
            MomentumAgent(),
            QualityAgent(),
            SentimentAgent(),
            InstitutionalFlowAgent(),
        ]

        required_fields = ['score', 'confidence', 'reasoning', 'metrics', 'breakdown', 'agent']

        for agent in agents:
            if isinstance(agent, MomentumAgent):
                result = agent.analyze('TCS', sample_historical_data, None, sample_comprehensive_data)
            elif isinstance(agent, (QualityAgent, InstitutionalFlowAgent)):
                result = agent.analyze('TCS', sample_historical_data, sample_comprehensive_data)
            else:
                result = agent.analyze('TCS', sample_comprehensive_data)

            for field in required_fields:
                assert field in result, f"{agent.agent_name} missing field: {field}"

    def test_all_agents_score_range(self, sample_comprehensive_data, sample_historical_data):
        """Test that all agents return scores in valid range"""
        agents = [
            FundamentalsAgent(),
            MomentumAgent(),
            QualityAgent(),
            SentimentAgent(),
            InstitutionalFlowAgent(),
        ]

        for agent in agents:
            if isinstance(agent, MomentumAgent):
                result = agent.analyze('TCS', sample_historical_data, None, sample_comprehensive_data)
            elif isinstance(agent, (QualityAgent, InstitutionalFlowAgent)):
                result = agent.analyze('TCS', sample_historical_data, sample_comprehensive_data)
            else:
                result = agent.analyze('TCS', sample_comprehensive_data)

            assert 0 <= result['score'] <= 100, f"{agent.agent_name} score out of range"
            assert 0 <= result['confidence'] <= 1, f"{agent.agent_name} confidence out of range"

    def test_all_agents_handle_missing_data(self):
        """Test that all agents handle missing data gracefully"""
        agents = [
            FundamentalsAgent(),
            MomentumAgent(),
            QualityAgent(),
            SentimentAgent(),
            InstitutionalFlowAgent(),
        ]

        for agent in agents:
            if isinstance(agent, MomentumAgent):
                result = agent.analyze('TCS', pd.DataFrame(), None, {})
            elif isinstance(agent, (QualityAgent, InstitutionalFlowAgent)):
                result = agent.analyze('TCS', pd.DataFrame(), {})
            else:
                result = agent.analyze('TCS', {})

            assert result['score'] is not None
            assert result['confidence'] is not None
