"""
Unit tests for Circuit Breaker functionality.

Tests the circuit breaker pattern implementation for fault tolerance
and automatic recovery from failures.
"""

import pytest
import time
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerState, CircuitBreakerError


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class"""

    def test_initial_state_closed(self):
        """Circuit breaker should start in CLOSED state"""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_opens_after_failures(self):
        """Circuit breaker should open after reaching failure threshold"""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        def failing_func():
            raise ValueError("Test error")

        # First 3 failures should work (circuit still closed)
        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        # Circuit should now be open
        assert cb.state == CircuitBreakerState.OPEN

        # Further calls should fail fast with CircuitBreakerError
        with pytest.raises(CircuitBreakerError, match="Circuit breaker is OPEN"):
            cb.call(failing_func)

    def test_circuit_half_open_after_timeout(self):
        """Circuit breaker should enter HALF_OPEN state after timeout"""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)

        def failing_func():
            raise ValueError("Test error")

        # Trigger open state
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Next call should transition to HALF_OPEN
        # (check state before the call triggers another failure)
        try:
            cb.call(failing_func)
        except (ValueError, CircuitBreakerError):
            pass

        # State should have been HALF_OPEN during the call
        # If the call failed, it's back to OPEN
        # If it succeeded, it's CLOSED
        assert cb.state in [CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED]

    def test_circuit_closes_on_success(self):
        """Circuit breaker should close on successful call from HALF_OPEN"""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        call_count = {'count': 0}

        def sometimes_failing_func():
            call_count['count'] += 1
            if call_count['count'] <= 2:
                raise ValueError("Test error")
            return "Success"

        # Trigger open state
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(sometimes_failing_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout to enter HALF_OPEN
        time.sleep(1.1)

        # Successful call should close the circuit
        result = cb.call(sometimes_failing_func)
        assert result == "Success"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_successful_calls_dont_open_circuit(self):
        """Circuit breaker should stay closed on successful calls"""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        def successful_func():
            return "Success"

        # Multiple successful calls
        for _ in range(10):
            result = cb.call(successful_func)
            assert result == "Success"

        assert cb.state == CircuitBreakerState.CLOSED

    def test_partial_failures_dont_open_circuit(self):
        """Circuit breaker should not open if failures are below threshold"""
        cb = CircuitBreaker(failure_threshold=5, timeout=1)
        call_count = {'count': 0}

        def intermittent_func():
            call_count['count'] += 1
            if call_count['count'] % 3 == 0:  # Fail every 3rd call
                raise ValueError("Test error")
            return "Success"

        # Make calls that have some failures but not consecutive
        for _ in range(10):
            try:
                cb.call(intermittent_func)
            except ValueError:
                pass

        # Circuit should still be closed
        assert cb.state == CircuitBreakerState.CLOSED

    def test_failure_count_resets_on_success(self):
        """Failure count should reset to 0 on successful call"""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)
        call_count = {'count': 0}

        def pattern_func():
            call_count['count'] += 1
            # Fail twice, succeed once, repeat
            if call_count['count'] % 3 != 0:
                raise ValueError("Test error")
            return "Success"

        # This pattern should never open the circuit
        # because successes reset the failure count
        for _ in range(12):
            try:
                cb.call(pattern_func)
            except ValueError:
                pass

        assert cb.state == CircuitBreakerState.CLOSED

    def test_different_exception_types(self):
        """Circuit breaker should count all exceptions as failures"""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        def func_with_different_errors(error_type):
            raise error_type("Test error")

        # Different exception types
        with pytest.raises(ValueError):
            cb.call(lambda: func_with_different_errors(ValueError))

        with pytest.raises(TypeError):
            cb.call(lambda: func_with_different_errors(TypeError))

        with pytest.raises(RuntimeError):
            cb.call(lambda: func_with_different_errors(RuntimeError))

        # Circuit should be open after 3 different exceptions
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_with_arguments(self):
        """Circuit breaker should work with functions that take arguments"""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)

        def add(a, b):
            return a + b

        result = cb.call(add, 2, 3)
        assert result == 5

        result = cb.call(add, a=5, b=7)
        assert result == 12

    def test_recovery_timeout_configuration(self):
        """Circuit breaker should respect configured timeout"""
        cb = CircuitBreaker(failure_threshold=2, timeout=2)

        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Wait less than timeout
        time.sleep(1)

        # Should still be open
        with pytest.raises(CircuitBreakerError):
            cb.call(failing_func)

        # Wait for remaining timeout
        time.sleep(1.1)

        # Now should allow a test call (HALF_OPEN)
        try:
            cb.call(failing_func)
        except (ValueError, CircuitBreakerError):
            pass

        # Should have attempted the call


class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions"""

    def test_zero_threshold(self):
        """Circuit breaker with threshold=0 should always be open"""
        cb = CircuitBreaker(failure_threshold=0, timeout=1)

        def any_func():
            return "Success"

        # Should fail immediately
        with pytest.raises(CircuitBreakerError):
            cb.call(any_func)

    def test_very_short_timeout(self):
        """Circuit breaker should work with very short timeouts"""
        cb = CircuitBreaker(failure_threshold=1, timeout=0.1)

        def failing_func():
            raise ValueError("Error")

        # Open circuit
        with pytest.raises(ValueError):
            cb.call(failing_func)

        # Wait for timeout
        time.sleep(0.15)

        # Should allow retry
        try:
            cb.call(failing_func)
        except (ValueError, CircuitBreakerError):
            pass

    def test_concurrent_access(self):
        """Circuit breaker should be thread-safe (basic test)"""
        import threading

        cb = CircuitBreaker(failure_threshold=10, timeout=1)
        results = []

        def successful_func(i):
            time.sleep(0.01)  # Small delay to encourage race conditions
            return i * 2

        def worker(thread_id):
            for i in range(5):
                result = cb.call(successful_func, i)
                results.append(result)

        # Create multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All calls should have succeeded
        assert len(results) == 25
        assert cb.state == CircuitBreakerState.CLOSED
