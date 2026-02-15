"""
Circuit Breaker Pattern Implementation
Prevents cascading failures by temporarily blocking requests after repeated failures
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation, requests go through
    OPEN = "open"            # Too many failures, reject requests immediately
    HALF_OPEN = "half_open"  # Testing if service recovered

# Alias for backward compatibility with tests
CircuitBreakerState = CircuitState


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures

    States:
    - CLOSED: Normal operation
    - OPEN: After failure_threshold failures, block all requests for recovery_timeout
    - HALF_OPEN: After timeout, allow limited requests to test recovery

    Args:
        failure_threshold: Number of failures before opening circuit (default: 5)
        recovery_timeout: Seconds to wait before testing recovery (default: 60)
        half_open_max_calls: Max calls allowed in half-open state (default: 3)
        name: Name of the circuit breaker (for logging)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        name: str = "default",
        timeout: Optional[int] = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timeout if timeout is not None else recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.name = name

        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by func
        """
        if self.failure_threshold == 0:
            raise CircuitBreakerError("Circuit breaker is OPEN")

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. "
                    f"Retry after {self._time_until_retry():.0f} seconds."
                )

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is HALF_OPEN with max calls reached."
                )
            self.half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self._transition_to_closed()
            logger.info(f"Circuit breaker '{self.name}' recovered: HALF_OPEN -> CLOSED")

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
            logger.warning(
                f"Circuit breaker '{self.name}' failed during recovery: HALF_OPEN -> OPEN"
            )
        elif self.failure_threshold > 0 and self.failure_count >= self.failure_threshold:
            self._transition_to_open()
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures"
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _time_until_retry(self) -> float:
        """Calculate seconds until retry is allowed"""
        if self.last_failure_time is None:
            return 0
        elapsed = time.time() - self.last_failure_time
        return max(0, self.recovery_timeout - elapsed)

    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.half_open_calls = 0
        self.success_count = 0

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' testing recovery: OPEN -> HALF_OPEN")

    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0
        self.success_count = 0

    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self._transition_to_closed()

    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "time_until_retry": self._time_until_retry() if self.state == CircuitState.OPEN else 0
        }

    def __call__(self, func: Callable) -> Callable:
        """Decorator usage"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper


# Example usage:
if __name__ == "__main__":
    # As a decorator
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10, name="api")

    @breaker
    def unreliable_api_call():
        import random
        if random.random() < 0.7:
            raise Exception("API failure")
        return "Success"

    # Test circuit breaker
    for i in range(10):
        try:
            result = unreliable_api_call()
            print(f"Call {i+1}: {result}")
        except (CircuitBreakerError, Exception) as e:
            print(f"Call {i+1}: {type(e).__name__} - {e}")
        time.sleep(1)
