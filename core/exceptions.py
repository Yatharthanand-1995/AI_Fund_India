"""
Custom exception hierarchy for Indian Stock Fund application.

This module provides a structured exception hierarchy for better error handling,
debugging, and user feedback across the application.
"""


class StockFundException(Exception):
    """Base exception for all stock fund errors"""
    pass


class DataProviderException(StockFundException):
    """Data provider errors"""
    pass


class DataFetchException(DataProviderException):
    """Failed to fetch data from external source"""
    pass


class DataValidationException(DataProviderException):
    """Data validation failed"""
    pass


class AgentException(StockFundException):
    """Agent analysis errors"""
    pass


class InsufficientDataException(AgentException):
    """Not enough data to perform analysis"""
    pass


class CalculationException(AgentException):
    """Calculation error (division by zero, etc.)"""
    pass


class DatabaseException(StockFundException):
    """Database operation errors"""
    pass


class ConfigurationException(StockFundException):
    """Configuration errors"""
    pass


class CacheException(StockFundException):
    """Cache operation errors"""
    pass


from enum import Enum


class ErrorCode(str, Enum):
    """Structured error codes for API responses"""
    # Data layer
    DATA_FETCH_FAILED = "DATA_FETCH_FAILED"
    DATA_VALIDATION_FAILED = "DATA_VALIDATION_FAILED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
    # Analysis
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    BATCH_ANALYSIS_FAILED = "BATCH_ANALYSIS_FAILED"
    # System
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    # Auth
    INVALID_API_KEY = "INVALID_API_KEY"
    # Cache
    CACHE_OPERATION_FAILED = "CACHE_OPERATION_FAILED"
