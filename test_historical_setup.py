#!/usr/bin/env python3
"""
Test script to verify historical database setup
"""

import sys
from datetime import datetime
from data.historical_db import HistoricalDatabase

def test_database():
    """Test database operations"""
    print("="*60)
    print("Testing Historical Database Setup")
    print("="*60)

    try:
        # Initialize database
        print("\n1. Initializing database...")
        db = HistoricalDatabase(db_path="data/test_analysis_history.db")
        print("✓ Database initialized successfully")

        # Test saving stock analysis
        print("\n2. Testing stock analysis save...")
        analysis_id = db.save_stock_analysis(
            symbol="TCS",
            composite_score=85.5,
            recommendation="BUY",
            confidence=0.85,
            agent_scores={
                "fundamentals": {"score": 88, "confidence": 0.9},
                "momentum": {"score": 82, "confidence": 0.8},
                "quality": {"score": 87, "confidence": 0.85},
                "sentiment": {"score": 84, "confidence": 0.75},
                "institutional_flow": {"score": 85, "confidence": 0.8}
            },
            weights={
                "fundamentals": 0.36,
                "momentum": 0.27,
                "quality": 0.18,
                "sentiment": 0.09,
                "institutional_flow": 0.10
            },
            price=3850.50,
            sector="Information Technology"
        )
        print(f"✓ Stock analysis saved with ID: {analysis_id}")

        # Test retrieving stock history
        print("\n3. Testing stock history retrieval...")
        history = db.get_stock_history("TCS", days=30)
        print(f"✓ Retrieved {len(history)} historical records")

        # Test market regime save
        print("\n4. Testing market regime save...")
        regime_id = db.save_market_regime(
            regime="BULL",
            trend="UP",
            volatility="NORMAL",
            weights={
                "fundamentals": 0.36,
                "momentum": 0.27,
                "quality": 0.18,
                "sentiment": 0.09,
                "institutional_flow": 0.10
            },
            metrics={"confidence": 0.85}
        )
        print(f"✓ Market regime saved with ID: {regime_id}")

        # Test watchlist operations
        print("\n5. Testing watchlist operations...")
        added = db.add_to_watchlist("TCS", notes="Top IT stock")
        print(f"✓ Added to watchlist: {added}")

        watchlist = db.get_watchlist()
        print(f"✓ Watchlist has {len(watchlist)} items")

        is_in = db.is_in_watchlist("TCS")
        print(f"✓ TCS in watchlist: {is_in}")

        removed = db.remove_from_watchlist("TCS")
        print(f"✓ Removed from watchlist: {removed}")

        # Test database stats
        print("\n6. Getting database statistics...")
        stats = db.get_database_stats()
        print(f"✓ Database stats:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")

        print("\n" + "="*60)
        print("✓ All tests passed successfully!")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
