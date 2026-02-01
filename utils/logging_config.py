"""
Comprehensive Logging Configuration

Features:
- Structured logging with JSON format
- Multiple log levels and handlers
- File rotation (size-based and time-based)
- Colored console output for development
- Separate error log file
- Request ID tracking
- Performance metrics
- Custom formatters

Usage:
    from utils.logging_config import setup_logging, get_logger

    setup_logging()
    logger = get_logger(__name__)
    logger.info("Application started")
"""

import logging
import logging.handlers
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add extra fields
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        if hasattr(record, 'symbol'):
            log_data['symbol'] = record.symbol

        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data)


class PerformanceLogger:
    """Context manager for performance logging"""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting: {self.operation}", extra=self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds() * 1000

        extra = {**self.extra, 'duration_ms': duration}

        if exc_type:
            self.logger.error(
                f"Failed: {self.operation} ({duration:.2f}ms)",
                extra=extra,
                exc_info=(exc_type, exc_val, exc_tb)
            )
        else:
            self.logger.info(
                f"Completed: {self.operation} ({duration:.2f}ms)",
                extra=extra
            )

        return False  # Don't suppress exceptions


def setup_logging(
    level: str = None,
    log_file: str = "app.log",
    error_log_file: str = "error.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    json_format: bool = False,
    console_output: bool = True,
) -> None:
    """
    Setup comprehensive logging configuration

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Main log file path
        error_log_file: Error-only log file path
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        json_format: Use JSON format for file logs
        console_output: Enable console output
    """
    # Get log level from environment or parameter
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (colored output for development)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if json_format:
            console_formatter = JSONFormatter()
        else:
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler (rotating, all levels)
    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    if json_format:
        file_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Error file handler (errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)

    if json_format:
        error_formatter = JSONFormatter()
    else:
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            'Location: %(pathname)s:%(lineno)d\n'
            'Function: %(funcName)s\n',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)

    # Time-based rotating handler (daily rotation)
    daily_handler = logging.handlers.TimedRotatingFileHandler(
        LOGS_DIR / 'daily.log',
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days
        encoding='utf-8'
    )
    daily_handler.setLevel(logging.INFO)
    daily_handler.setFormatter(file_formatter)
    root_logger.addHandler(daily_handler)

    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('nsepy').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)

    # Log configuration summary
    root_logger.info("="*60)
    root_logger.info("Logging configured successfully")
    root_logger.info(f"Level: {level.upper()}")
    root_logger.info(f"Main log: {LOGS_DIR / log_file}")
    root_logger.info(f"Error log: {LOGS_DIR / error_log_file}")
    root_logger.info(f"Daily log: {LOGS_DIR / 'daily.log'}")
    root_logger.info(f"JSON format: {json_format}")
    root_logger.info("="*60)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context
) -> None:
    """
    Log with additional context

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra=context)


def log_exception(
    logger: logging.Logger,
    message: str,
    **context
) -> None:
    """
    Log an exception with full traceback

    Args:
        logger: Logger instance
        message: Error message
        **context: Additional context
    """
    logger.exception(message, extra=context)


def log_performance(
    logger: logging.Logger,
    operation: str,
    **context
) -> PerformanceLogger:
    """
    Create a performance logging context manager

    Args:
        logger: Logger instance
        operation: Operation name
        **context: Additional context

    Returns:
        PerformanceLogger context manager

    Example:
        with log_performance(logger, "fetch_data", symbol="TCS"):
            data = fetch_data("TCS")
    """
    return PerformanceLogger(logger, operation, **context)


# Example usage
if __name__ == "__main__":
    # Setup logging
    setup_logging(level='DEBUG', json_format=False)

    # Get logger
    logger = get_logger(__name__)

    # Basic logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Logging with context
    log_with_context(
        logger,
        'info',
        'Stock analyzed',
        symbol='TCS',
        score=85.5,
        recommendation='BUY'
    )

    # Performance logging
    with log_performance(logger, 'analyze_stock', symbol='TCS'):
        import time
        time.sleep(0.1)  # Simulate work

    # Exception logging
    try:
        1 / 0
    except Exception:
        log_exception(logger, "Division by zero error", symbol='TCS')

    logger.info("Logging test completed")
