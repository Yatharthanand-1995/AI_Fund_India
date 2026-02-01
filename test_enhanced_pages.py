#!/usr/bin/env python3
"""
Enhanced Pages Validation Test
Tests the new API endpoints and features
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, data=None, expected_keys=None):
    """Test an API endpoint"""
    print(f"\n🔍 Testing: {name}")
    print(f"   {method} {url}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            raise ValueError(f"Unknown method: {method}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {response.status_code}")

            # Check for expected keys
            if expected_keys:
                for key in expected_keys:
                    if key in result:
                        value = result[key]
                        if isinstance(value, list):
                            print(f"   ✅ {key}: {len(value)} items")
                        elif isinstance(value, dict):
                            print(f"   ✅ {key}: {len(value)} fields")
                        else:
                            print(f"   ✅ {key}: {value}")
                    else:
                        print(f"   ⚠️  {key}: MISSING")

            return True, result
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   Error: {response.text}")
            return False, None

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False, None

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 ENHANCED PAGES VALIDATION TEST")
    print("=" * 60)
    print(f"Testing backend at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Test 1: Health Check
    success, _ = test_endpoint(
        "Health Check",
        "GET",
        f"{BASE_URL}/health",
        expected_keys=["status", "components"]
    )
    results["health"] = success

    # Test 2: Market Regime
    success, regime_data = test_endpoint(
        "Market Regime",
        "GET",
        f"{BASE_URL}/market-regime",
        expected_keys=["regime", "trend", "weights"]
    )
    results["regime"] = success

    # Test 3: Stock Analysis (for StockDetails page)
    success, analysis_data = test_endpoint(
        "Stock Analysis (TCS)",
        "POST",
        f"{BASE_URL}/analyze",
        data={"symbol": "TCS", "include_narrative": True},
        expected_keys=["symbol", "composite_score", "agent_scores", "narrative"]
    )
    results["analysis"] = success

    # Test 4: Historical Stock Data (for StockDetails Historical tab)
    success, history_data = test_endpoint(
        "Historical Stock Data",
        "GET",
        f"{BASE_URL}/history/stock/TCS?days=30&include_price=true",
        expected_keys=["symbol", "history", "statistics"]
    )
    results["stock_history"] = success

    # Test 5: Market Regime History (for Dashboard timeline)
    success, _ = test_endpoint(
        "Market Regime History",
        "GET",
        f"{BASE_URL}/history/regime?days=30",
        expected_keys=["history"]
    )
    results["regime_history"] = success

    # Test 6: System Analytics (for Analytics page)
    success, analytics_data = test_endpoint(
        "System Analytics",
        "GET",
        f"{BASE_URL}/analytics/system",
        expected_keys=["total_requests", "cache_hit_rate"]
    )
    results["system_analytics"] = success

    # Test 7: Sector Analysis (for SectorAnalysis page)
    success, sector_data = test_endpoint(
        "Sector Analysis",
        "GET",
        f"{BASE_URL}/analytics/sectors?days=7",
        expected_keys=["sectors"]
    )
    results["sector_analysis"] = success

    # Test 8: Watchlist - Add
    success, _ = test_endpoint(
        "Add to Watchlist",
        "POST",
        f"{BASE_URL}/watchlist",
        data={"symbol": "TCS", "notes": "Test stock"},
        expected_keys=["success"]
    )
    results["watchlist_add"] = success

    # Test 9: Watchlist - Get
    success, watchlist_data = test_endpoint(
        "Get Watchlist",
        "GET",
        f"{BASE_URL}/watchlist",
        expected_keys=["watchlist", "count"]
    )
    results["watchlist_get"] = success

    # Test 10: Stock Comparison (for Comparison page and StockDetails Compare tab)
    success, comparison_data = test_endpoint(
        "Compare Stocks",
        "POST",
        f"{BASE_URL}/compare",
        data={"symbols": ["TCS", "INFY"], "include_history": False},
        expected_keys=["stocks", "comparison_matrix"]
    )
    results["comparison"] = success

    # Test 11: Top Picks (for TopPicks page)
    success, top_picks_data = test_endpoint(
        "Top Picks",
        "GET",
        f"{BASE_URL}/top-picks?limit=10&include_narrative=false",
        expected_keys=["top_picks", "market_regime"]
    )
    results["top_picks"] = success

    # Test 12: Export Analysis
    success, _ = test_endpoint(
        "Export Analysis",
        "GET",
        f"{BASE_URL}/export/analysis/TCS?format=json"
    )
    results["export"] = success

    # Test 13: Data Collector Status
    success, _ = test_endpoint(
        "Data Collector Status",
        "GET",
        f"{BASE_URL}/collector/status",
        expected_keys=["enabled", "interval_seconds"]
    )
    results["collector_status"] = success

    # Test 14: Watchlist - Remove (cleanup)
    success, _ = test_endpoint(
        "Remove from Watchlist",
        "DELETE",
        f"{BASE_URL}/watchlist/TCS",
        expected_keys=["success"]
    )
    results["watchlist_remove"] = success

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    print("\nDetailed Results:")
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}  {test_name}")

    print("\n" + "=" * 60)

    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("The enhanced pages are ready to use.")
    else:
        print("⚠️  Some tests failed. Check the backend is running.")
        print("   Run: uvicorn api.main:app --reload --port 8000")

    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
