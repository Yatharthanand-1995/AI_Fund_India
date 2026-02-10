"""
Pytest Configuration
Shared fixtures and configuration for all tests
"""

import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_comprehensive_data():
    """Sample comprehensive stock data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=300, freq='D')

    # Generate realistic price data
    np.random.seed(42)
    base_price = 1000
    returns = np.random.randn(300) * 0.02  # 2% daily volatility
    prices = base_price * (1 + returns).cumprod()

    historical_data = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, 300)
    }, index=dates)

    return {
        'symbol': 'TEST',
        'current_price': float(prices[-1]),
        'price_change_percent': 2.5,
        'market_cap': 100000000000,  # 100B
        'sector': 'Technology',
        'company_name': 'Test Company',
        'historical_data': historical_data,
        'info': {
            'returnOnEquity': 0.20,
            'returnOnAssets': 0.15,
            'profitMargins': 0.18,
            'trailingPE': 22.0,
            'priceToBook': 4.5,
            'revenueGrowth': 0.15,
            'earningsGrowth': 0.18,
            'debtToEquity': 45,  # Will be divided by 100
            'currentRatio': 1.8,
            'freeCashflow': 5000000000,
            'operatingCashflow': 8000000000,
            'dividendYield': 0.025,
            'payoutRatio': 0.40,
            'heldPercentInsiders': 0.55,
            'marketCap': 100000000000,
            'sector': 'Technology',
            'industry': 'Software'
        },
        'financials': pd.DataFrame({
            'Revenue': [80000000000, 90000000000, 100000000000],
            'Net Income': [14000000000, 16000000000, 18000000000]
        }),
        'technical_data': {
            'rsi': 55.0,
            'macd': 10.5,
            'macd_signal': 8.2,
            'sma_20': prices[-20:].mean(),
            'sma_50': prices[-50:].mean(),
            'sma_200': prices[-200:].mean(),
            'obv': 50000000,
            'mfi': 58.0
        },
        'provider': 'TestProvider',
        'data_completeness': {
            'has_historical': True,
            'has_financials': True,
            'has_technical': True,
            'has_quarterly': False
        }
    }


@pytest.fixture
def sample_historical_data():
    """Sample historical price data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=300, freq='D')

    np.random.seed(42)
    base_price = 1000
    returns = np.random.randn(300) * 0.02
    prices = base_price * (1 + returns).cumprod()

    return pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, 300)
    }, index=dates)


@pytest.fixture
def sample_nifty_data():
    """Sample NIFTY 50 index data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=300, freq='D')

    np.random.seed(123)
    base_price = 18000
    returns = np.random.randn(300) * 0.015  # Lower volatility for index
    prices = base_price * (1 + returns).cumprod()

    return pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(100000000, 500000000, 300)
    }, index=dates)
