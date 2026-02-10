"""
Unit tests for configuration system
"""

import pytest
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from core.config import AgentWeights, Config, get_config
from core.exceptions import ConfigurationException


class TestAgentWeights:
    """Test AgentWeights configuration"""

    def test_default_weights(self):
        """Test default weights sum to 1.0"""
        weights = AgentWeights()
        total = sum(weights.to_dict().values())
        assert 0.99 <= total <= 1.01

    def test_to_dict(self):
        """Test conversion to dictionary"""
        weights = AgentWeights()
        d = weights.to_dict()

        assert 'fundamentals' in d
        assert 'momentum' in d
        assert 'quality' in d
        assert 'sentiment' in d
        assert 'institutional_flow' in d

    def test_validation_success(self):
        """Test validation passes with valid weights"""
        weights = AgentWeights(
            fundamentals=0.3,
            momentum=0.3,
            quality=0.2,
            sentiment=0.1,
            institutional_flow=0.1
        )
        # Should not raise
        weights.validate()

    def test_validation_failure_sum_too_low(self):
        """Test validation fails if weights sum too low"""
        weights = AgentWeights(
            fundamentals=0.1,
            momentum=0.1,
            quality=0.1,
            sentiment=0.1,
            institutional_flow=0.1
        )
        with pytest.raises(ConfigurationException):
            weights.validate()

    def test_validation_failure_sum_too_high(self):
        """Test validation fails if weights sum too high"""
        weights = AgentWeights(
            fundamentals=0.5,
            momentum=0.5,
            quality=0.5,
            sentiment=0.5,
            institutional_flow=0.5
        )
        with pytest.raises(ConfigurationException):
            weights.validate()

    def test_validation_failure_negative_weight(self):
        """Test validation fails with negative weight"""
        weights = AgentWeights(
            fundamentals=-0.1,
            momentum=0.4,
            quality=0.3,
            sentiment=0.2,
            institutional_flow=0.2
        )
        with pytest.raises(ConfigurationException):
            weights.validate()


class TestConfig:
    """Test main Config class"""

    def test_get_config(self):
        """Test getting configuration"""
        config = get_config()

        assert config is not None
        assert config.agent_weights is not None
        assert config.recommendation_thresholds is not None
        assert config.cache is not None
        assert config.api is not None

    def test_config_validation(self):
        """Test configuration validation"""
        config = get_config()
        # Should not raise
        config.validate()

    def test_agent_weights_from_env(self, monkeypatch):
        """Test loading agent weights from environment"""
        monkeypatch.setenv('AGENT_WEIGHT_FUNDAMENTALS', '0.4')
        monkeypatch.setenv('AGENT_WEIGHT_MOMENTUM', '0.3')
        monkeypatch.setenv('AGENT_WEIGHT_QUALITY', '0.15')
        monkeypatch.setenv('AGENT_WEIGHT_SENTIMENT', '0.1')
        monkeypatch.setenv('AGENT_WEIGHT_INSTITUTIONAL', '0.05')

        config = get_config()

        assert config.agent_weights.fundamentals == 0.4
        assert config.agent_weights.momentum == 0.3
        assert config.agent_weights.quality == 0.15

    def test_cache_config_from_env(self, monkeypatch):
        """Test loading cache config from environment"""
        monkeypatch.setenv('CACHE_ENABLED', 'true')
        monkeypatch.setenv('CACHE_TTL_SECONDS', '3600')
        monkeypatch.setenv('CACHE_MAX_SIZE', '500')

        config = get_config()

        assert config.cache.enabled is True
        assert config.cache.ttl_seconds == 3600
        assert config.cache.max_size == 500

    def test_threshold_ordering(self):
        """Test that thresholds are in correct order"""
        config = get_config()
        t = config.recommendation_thresholds

        assert t.strong_buy > t.buy
        assert t.buy > t.weak_buy
        assert t.weak_buy > t.hold
        assert t.hold > t.weak_sell


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
