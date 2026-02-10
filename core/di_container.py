"""
Dependency injection container for managing service lifecycle.

Provides centralized service initialization and dependency management
for better testability and maintainability.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Dependency injection container for managing service lifecycle"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False

    def initialize(self):
        """Initialize all services in correct order"""
        if self._initialized:
            logger.debug("Service container already initialized")
            return

        try:
            from core.config import get_config
            from data.hybrid_provider import HybridDataProvider
            from core.market_regime_service import MarketRegimeService
            from core.stock_scorer import StockScorer
            from narrative_engine.narrative_engine import InvestmentNarrativeEngine
            from data.historical_db import HistoricalDatabase
            from data.stock_universe import get_universe
            import os

            # Configuration (must be first)
            config = get_config()
            config.validate()
            self._services['config'] = config
            logger.info("Configuration loaded and validated")

            # Data layer
            self._services['data_provider'] = HybridDataProvider()
            logger.info("Data provider initialized")

            db_path = os.getenv('DATABASE_PATH', 'data/analysis_history.db')
            self._services['historical_db'] = HistoricalDatabase(db_path=db_path)
            logger.info(f"Historical database initialized: {db_path}")

            self._services['stock_universe'] = get_universe()
            logger.info("Stock universe loaded")

            # Core services
            self._services['market_regime_service'] = MarketRegimeService()
            logger.info("Market regime service initialized")

            self._services['stock_scorer'] = StockScorer(
                data_provider=self._services['data_provider'],
                use_adaptive_weights=True
            )
            logger.info("Stock scorer initialized")

            # Narrative engine
            self._services['narrative_engine'] = InvestmentNarrativeEngine()
            logger.info("Narrative engine initialized")

            self._initialized = True
            logger.info("Service container initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize service container: {e}", exc_info=True)
            raise

    def get(self, service_name: str) -> Any:
        """
        Get a service by name.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            Service instance

        Raises:
            KeyError: If service not found
        """
        if not self._initialized:
            self.initialize()

        if service_name not in self._services:
            raise KeyError(f"Service '{service_name}' not found in container")

        return self._services[service_name]

    def override(self, service_name: str, service: Any):
        """
        Override a service (for testing).

        Args:
            service_name: Name of the service
            service: Service instance to use
        """
        self._services[service_name] = service
        logger.debug(f"Service '{service_name}' overridden")

    def reset(self):
        """Reset the container (for testing)"""
        self._services.clear()
        self._initialized = False
        logger.debug("Service container reset")

    def is_initialized(self) -> bool:
        """Check if container is initialized"""
        return self._initialized


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    Get the global service container.

    Returns:
        Global ServiceContainer instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
        _container.initialize()
    return _container


def reset_container():
    """Reset the global container (for testing)"""
    global _container
    if _container is not None:
        _container.reset()
    _container = None
