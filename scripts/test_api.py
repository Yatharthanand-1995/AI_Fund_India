"""
Test script for FastAPI backend

Tests all API endpoints with sample requests.
Run the API server first: make run-api
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def print_response(response: requests.Response):
    """Pretty print API response"""
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2, default=str))
    else:
        print(f"Error: {response.text}")


def test_root():
    """Test root endpoint"""
    print_section("Test 1: Root Endpoint")
    response = requests.get(f"{BASE_URL}/")
    print_response(response)


def test_health():
    """Test health check"""
    print_section("Test 2: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)


def test_market_regime():
    """Test market regime endpoint"""
    print_section("Test 3: Market Regime")
    response = requests.get(f"{BASE_URL}/market/regime")
    print_response(response)


def test_stock_universe():
    """Test stock universe endpoint"""
    print_section("Test 4: Stock Universe")
    response = requests.get(f"{BASE_URL}/stocks/universe")
    print_response(response)


def test_single_analysis():
    """Test single stock analysis"""
    print_section("Test 5: Single Stock Analysis (TCS)")

    payload = {
        "symbol": "TCS",
        "include_narrative": True
    }

    print(f"Request: {json.dumps(payload, indent=2)}")

    response = requests.post(
        f"{BASE_URL}/analyze",
        json=payload
    )

    print_response(response)


def test_batch_analysis():
    """Test batch stock analysis"""
    print_section("Test 6: Batch Analysis (3 stocks)")

    payload = {
        "symbols": ["TCS", "INFY", "WIPRO"],
        "include_narrative": False,
        "sort_by": "score"
    }

    print(f"Request: {json.dumps(payload, indent=2)}")

    response = requests.post(
        f"{BASE_URL}/analyze/batch",
        json=payload
    )

    print_response(response)


def test_top_picks():
    """Test top picks endpoint"""
    print_section("Test 7: Top 5 Picks from NIFTY 50")

    response = requests.get(
        f"{BASE_URL}/portfolio/top-picks",
        params={
            "limit": 5,
            "include_narrative": False
        }
    )

    print_response(response)


def test_error_handling():
    """Test error handling"""
    print_section("Test 8: Error Handling (Invalid Symbol)")

    payload = {
        "symbol": "",
        "include_narrative": False
    }

    response = requests.post(
        f"{BASE_URL}/analyze",
        json=payload
    )

    print_response(response)


def test_cache():
    """Test caching behavior"""
    print_section("Test 9: Cache Test (Same request twice)")

    payload = {
        "symbol": "RELIANCE",
        "include_narrative": False
    }

    # First request
    print("First request (should fetch fresh data):")
    start = time.time()
    response1 = requests.post(f"{BASE_URL}/analyze", json=payload)
    duration1 = time.time() - start
    print(f"Duration: {duration1:.2f}s")
    print(f"Cached: {response1.json().get('cached', False)}")

    # Second request (should use cache)
    print("\nSecond request (should use cache):")
    start = time.time()
    response2 = requests.post(f"{BASE_URL}/analyze", json=payload)
    duration2 = time.time() - start
    print(f"Duration: {duration2:.2f}s")
    print(f"Cached: {response2.json().get('cached', False)}")

    print(f"\nSpeed improvement: {duration1/duration2:.1f}x faster")


def run_all_tests():
    """Run all API tests"""
    print("\n" + "🚀"*35)
    print(" AI Hedge Fund API - Test Suite")
    print("🚀"*35)

    print("\nAPI Base URL:", BASE_URL)
    print("Make sure the API server is running: make run-api")

    try:
        # Check if API is running
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("\n❌ Error: API is not responding correctly")
            return
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API")
        print("Please start the API server first: make run-api")
        return

    print("\n✅ API is running!")

    # Run tests
    tests = [
        test_root,
        test_health,
        test_market_regime,
        test_stock_universe,
        test_single_analysis,
        test_batch_analysis,
        test_top_picks,
        test_error_handling,
        test_cache
    ]

    for test_func in tests:
        try:
            test_func()
            time.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print(f"\n❌ Test failed: {e}")

    print_section("All Tests Completed")
    print("\n✅ API testing finished!")
    print("\nNext steps:")
    print("1. Check logs for any errors")
    print("2. View API docs at: http://localhost:8000/docs")
    print("3. Try the interactive ReDoc at: http://localhost:8000/redoc")


if __name__ == "__main__":
    run_all_tests()
