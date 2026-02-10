"""
Centralized configuration system for Indian Stock Fund application.

This module provides a structured configuration system with environment variable
support, validation, and default values.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

from core.exceptions import ConfigurationException

# Load environment variables
load_dotenv()


@dataclass
class AgentWeights:
    """Agent weight configuration"""
    fundamentals: float = 0.36
    momentum: float = 0.27
    quality: float = 0.18
    sentiment: float = 0.09
    institutional_flow: float = 0.10

    def to_dict(self) -> Dict[str, float]:
        """Convert weights to dictionary"""
        return {
            'fundamentals': self.fundamentals,
            'momentum': self.momentum,
            'quality': self.quality,
            'sentiment': self.sentiment,
            'institutional_flow': self.institutional_flow
        }

    def validate(self):
        """Validate that weights sum to 1.0"""
        total = sum(self.to_dict().values())
        if not 0.99 <= total <= 1.01:  # Allow small floating point errors
            raise ConfigurationException(
                f"Agent weights must sum to 1.0, got {total:.4f}"
            )

        # Check individual weights are in valid range
        for name, weight in self.to_dict().items():
            if not 0.0 <= weight <= 1.0:
                raise ConfigurationException(
                    f"Agent weight '{name}' must be between 0 and 1, got {weight}"
                )


@dataclass
class RecommendationThresholds:
    """Thresholds for stock recommendations"""
    strong_buy: float = 80
    buy: float = 68
    weak_buy: float = 58
    hold: float = 45
    weak_sell: float = 35


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    ttl_seconds: int = 1200
    max_size: int = 1000


@dataclass
class APIConfig:
    """API configuration"""
    allowed_origins: List[str]
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 30
    timeout_seconds: int = 60

    def __post_init__(self):
        """Initialize with defaults if not provided"""
        if self.allowed_origins is None:
            origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000')
            self.allowed_origins = [o.strip() for o in origins.split(',')]


@dataclass
class LLMConfig:
    """LLM configuration"""
    enabled: bool = True
    provider: str = 'gemini'
    timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class Config:
    """Main application configuration"""
    agent_weights: AgentWeights
    recommendation_thresholds: RecommendationThresholds
    cache: CacheConfig
    api: APIConfig
    llm: LLMConfig
    environment: str = 'development'
    debug: bool = False

    def validate(self):
        """Validate the entire configuration"""
        self.agent_weights.validate()

        # Validate thresholds are in order
        thresholds = self.recommendation_thresholds
        if not (thresholds.strong_buy > thresholds.buy > thresholds.weak_buy >
                thresholds.hold > thresholds.weak_sell):
            raise ConfigurationException(
                "Recommendation thresholds must be in descending order"
            )


def get_config() -> Config:
    """
    Get application configuration from environment variables.

    Returns:
        Config object with all settings loaded and validated

    Raises:
        ConfigurationException: If configuration is invalid
    """
    try:
        config = Config(
            agent_weights=AgentWeights(
                fundamentals=float(os.getenv('AGENT_WEIGHT_FUNDAMENTALS', '0.36')),
                momentum=float(os.getenv('AGENT_WEIGHT_MOMENTUM', '0.27')),
                quality=float(os.getenv('AGENT_WEIGHT_QUALITY', '0.18')),
                sentiment=float(os.getenv('AGENT_WEIGHT_SENTIMENT', '0.09')),
                institutional_flow=float(os.getenv('AGENT_WEIGHT_INSTITUTIONAL', '0.10'))
            ),
            recommendation_thresholds=RecommendationThresholds(
                strong_buy=float(os.getenv('THRESHOLD_STRONG_BUY', '80')),
                buy=float(os.getenv('THRESHOLD_BUY', '68')),
                weak_buy=float(os.getenv('THRESHOLD_WEAK_BUY', '58')),
                hold=float(os.getenv('THRESHOLD_HOLD', '45')),
                weak_sell=float(os.getenv('THRESHOLD_WEAK_SELL', '35'))
            ),
            cache=CacheConfig(
                enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
                ttl_seconds=int(os.getenv('CACHE_TTL_SECONDS', '1200')),
                max_size=int(os.getenv('CACHE_MAX_SIZE', '1000'))
            ),
            api=APIConfig(
                allowed_origins=None,  # Will be initialized in __post_init__
                rate_limit_enabled=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true',
                rate_limit_per_minute=int(os.getenv('RATE_LIMIT_PER_MINUTE', '30')),
                timeout_seconds=int(os.getenv('API_TIMEOUT_SECONDS', '60'))
            ),
            llm=LLMConfig(
                enabled=os.getenv('ENABLE_LLM_NARRATIVES', 'true').lower() == 'true',
                provider=os.getenv('LLM_PROVIDER', 'gemini').lower(),
                timeout_seconds=int(os.getenv('LLM_TIMEOUT', '30')),
                max_retries=int(os.getenv('LLM_MAX_RETRIES', '3'))
            ),
            environment=os.getenv('ENVIRONMENT', 'development').lower(),
            debug=os.getenv('DEBUG', 'false').lower() == 'true'
        )

        # Validate configuration
        config.validate()

        return config

    except ValueError as e:
        raise ConfigurationException(f"Invalid configuration value: {e}") from e
    except Exception as e:
        raise ConfigurationException(f"Configuration error: {e}") from e


# Global configuration instance
_config: Optional[Config] = None


def get_global_config() -> Config:
    """Get the global configuration instance (singleton pattern)"""
    global _config
    if _config is None:
        _config = get_config()
    return _config
