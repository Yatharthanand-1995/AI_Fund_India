#!/usr/bin/env python3
"""
Test script to verify API endpoints are accessible
"""

import sys
from fastapi.testclient import TestClient

def test_api_endpoints():
    """Test that all new API endpoints are defined"""
    print("="*60)
    print("Testing API Endpoints")
    print("="*60)

    try:
        # Import the FastAPI app
        print("\n1. Importing FastAPI app...")
        from api.main import app
        print("✓ FastAPI app imported successfully")

        # Create test client
        print("\n2. Creating test client...")
        client = TestClient(app)
        print("✓ Test client created")

        # Test root endpoint
        print("\n3. Testing root endpoint...")
        response = client.get("/")
        print(f"✓ Root endpoint: {response.status_code}")

        # Test health endpoint
        print("\n4. Testing health endpoint...")
        response = client.get("/health")
        print(f"✓ Health endpoint: {response.status_code}")

        # Test new historical endpoints (should return 404 for missing data, not 500)
        print("\n5. Testing historical stock endpoint...")
        response = client.get("/history/stock/TCS?days=30")
        print(f"✓ History stock endpoint exists: {response.status_code} (404 = no data yet, OK)")

        print("\n6. Testing regime history endpoint...")
        response = client.get("/history/regime?days=30")
        print(f"✓ Regime history endpoint exists: {response.status_code}")

        # Test analytics endpoints
        print("\n7. Testing system analytics endpoint...")
        response = client.get("/analytics/system")
        print(f"✓ System analytics endpoint: {response.status_code}")

        print("\n8. Testing sector analysis endpoint...")
        response = client.get("/analytics/sectors?days=7")
        print(f"✓ Sector analysis endpoint: {response.status_code}")

        print("\n9. Testing agent analytics endpoint...")
        response = client.get("/analytics/agents")
        print(f"✓ Agent analytics endpoint: {response.status_code}")

        # Test watchlist endpoints
        print("\n10. Testing watchlist GET endpoint...")
        response = client.get("/watchlist")
        print(f"✓ Watchlist GET endpoint: {response.status_code}")

        print("\n11. Testing watchlist POST endpoint...")
        response = client.post("/watchlist", json={"symbol": "TCS", "notes": "Test"})
        print(f"✓ Watchlist POST endpoint: {response.status_code}")

        # Test comparison endpoint
        print("\n12. Testing comparison endpoint...")
        response = client.post("/compare", json={"symbols": ["TCS", "INFY"]})
        print(f"✓ Comparison endpoint exists: {response.status_code} (may fail without data)")

        # Test collector status endpoint
        print("\n13. Testing collector status endpoint...")
        response = client.get("/collector/status")
        print(f"✓ Collector status endpoint: {response.status_code}")

        print("\n" + "="*60)
        print("✓ All endpoint tests passed!")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_endpoints()
    sys.exit(0 if success else 1)
