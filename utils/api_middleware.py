"""
FastAPI Middleware for Logging, Monitoring & Error Tracking

Features:
- Request/response logging
- Performance tracking
- Error tracking
- Request ID generation
- Response time headers
- Exception handling
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Import metrics (with fallback if circular dependency)
try:
    from utils.metrics import metrics
except ImportError:
    metrics = None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging
    """

    def __init__(self, app: ASGIApp, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'query_params': dict(request.query_params),
                'client_host': request.client.host if request.client else None,
            }
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add custom headers
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                }
            )

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': duration_ms,
                    'error': str(e),
                },
                exc_info=True
            )

            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    'error': 'Internal server error',
                    'request_id': request_id,
                    'detail': str(e) if logger.level <= logging.DEBUG else None,
                },
                headers={
                    'X-Request-ID': request_id,
                    'X-Response-Time': f"{duration_ms:.2f}ms",
                }
            )


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for performance monitoring with alerting
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 1000.0
    ):
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        # Record metrics
        if metrics:
            # Track overall API requests
            metrics.increment('api.requests')
            metrics.record_timing('api.response_time', duration_ms)

            # Track per-endpoint metrics
            endpoint = request.url.path
            metrics.increment(f'api.requests.{endpoint}')
            metrics.record_timing(f'api.response_time.{endpoint}', duration_ms)

            # Track status codes
            if response.status_code >= 500:
                metrics.increment('api.errors.5xx')
                metrics.record_error(f'http_{response.status_code}')
            elif response.status_code >= 400:
                metrics.increment('api.errors.4xx')

        # Alert on slow requests
        if duration_ms > self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    'request_id': getattr(request.state, 'request_id', None),
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': duration_ms,
                    'threshold_ms': self.slow_request_threshold_ms,
                }
            )

        return response


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for error tracking and categorization
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.error_counts = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)

            # Track 4xx and 5xx errors
            if response.status_code >= 400:
                error_key = f"{request.url.path}:{response.status_code}"
                self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

                logger.warning(
                    f"HTTP error: {request.method} {request.url.path} - {response.status_code}",
                    extra={
                        'request_id': getattr(request.state, 'request_id', None),
                        'method': request.method,
                        'path': request.url.path,
                        'status_code': response.status_code,
                        'error_count': self.error_counts[error_key],
                    }
                )

            return response

        except Exception as e:
            error_key = f"{request.url.path}:exception"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

            logger.exception(
                f"Unhandled exception: {request.method} {request.url.path}",
                extra={
                    'request_id': getattr(request.state, 'request_id', None),
                    'method': request.method,
                    'path': request.url.path,
                    'exception_type': type(e).__name__,
                    'error_count': self.error_counts[error_key],
                }
            )

            raise

    def get_error_stats(self) -> dict:
        """Get error statistics"""
        return self.error_counts.copy()


# Utility functions

def get_request_id(request: Request) -> str:
    """Get request ID from request state"""
    return getattr(request.state, 'request_id', 'unknown')


def log_api_call(
    endpoint: str,
    method: str,
    request_id: str,
    **context
):
    """
    Log an API call with context

    Args:
        endpoint: API endpoint
        method: HTTP method
        request_id: Request ID
        **context: Additional context
    """
    logger.info(
        f"API call: {method} {endpoint}",
        extra={
            'request_id': request_id,
            'endpoint': endpoint,
            'method': method,
            **context
        }
    )


def log_api_error(
    endpoint: str,
    method: str,
    request_id: str,
    error: Exception,
    **context
):
    """
    Log an API error

    Args:
        endpoint: API endpoint
        method: HTTP method
        request_id: Request ID
        error: Exception that occurred
        **context: Additional context
    """
    logger.error(
        f"API error: {method} {endpoint} - {str(error)}",
        extra={
            'request_id': request_id,
            'endpoint': endpoint,
            'method': method,
            'error_type': type(error).__name__,
            'error_message': str(error),
            **context
        },
        exc_info=True
    )


# Example usage
if __name__ == "__main__":
    from utils.logging_config import setup_logging

    setup_logging(level='DEBUG')

    # Simulate request
    class FakeRequest:
        def __init__(self):
            self.method = 'POST'
            self.url = type('obj', (object,), {'path': '/analyze'})()
            self.state = type('obj', (object,), {})()
            self.client = type('obj', (object,), {'host': '127.0.0.1'})()
            self.query_params = {}

    request = FakeRequest()

    # Log API call
    log_api_call(
        '/analyze',
        'POST',
        'test-request-id',
        symbol='TCS',
        include_narrative=True
    )

    # Log API error
    try:
        raise ValueError("Invalid symbol")
    except Exception as e:
        log_api_error(
            '/analyze',
            'POST',
            'test-request-id',
            e,
            symbol='INVALID'
        )
