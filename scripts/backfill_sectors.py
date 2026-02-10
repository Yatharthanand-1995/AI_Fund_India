"""
Backfill script to update NULL sectors in the database

This script:
1. Finds all records with sector=NULL
2. Fetches sector information from Yahoo Finance
3. Updates the database records
"""

import sys
import os
import logging
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.yahoo_provider import YahooFinanceProvider
from data.historical_db import HistoricalDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_sectors():
    """Backfill NULL sectors with data from Yahoo Finance"""

    logger.info("Starting sector backfill process...")

    # Initialize providers and database
    db = HistoricalDatabase()
    yahoo_provider = YahooFinanceProvider(cache_duration=3600)  # 1 hour cache

    # Get all records with NULL sector
    query = """
        SELECT DISTINCT symbol
        FROM stock_analyses
        WHERE sector IS NULL OR sector = ''
        ORDER BY symbol
    """

    with db._get_connection() as conn:
        cursor = conn.execute(query)
        symbols_with_null_sector = [row[0] for row in cursor.fetchall()]

    if not symbols_with_null_sector:
        logger.info("No records with NULL sectors found. Database is clean!")
        return

    logger.info(f"Found {len(symbols_with_null_sector)} symbols with NULL sectors")
    logger.info(f"Symbols to update: {', '.join(symbols_with_null_sector)}")

    updated_count = 0
    failed_count = 0

    for i, symbol in enumerate(symbols_with_null_sector, 1):
        try:
            logger.info(f"[{i}/{len(symbols_with_null_sector)}] Processing {symbol}...")

            # Fetch sector from Yahoo Finance
            stock_data = yahoo_provider.get_stock_data(symbol)

            if not stock_data:
                logger.warning(f"  No data returned for {symbol}")
                failed_count += 1
                continue

            sector = stock_data.get('sector') or 'Unknown'
            industry = stock_data.get('industry', '')

            logger.info(f"  Found: sector={sector}, industry={industry}")

            # Update database
            update_query = """
                UPDATE stock_analyses
                SET sector = ?
                WHERE symbol = ? AND (sector IS NULL OR sector = '')
            """

            with db._get_connection() as conn:
                conn.execute(update_query, (sector, symbol))

            updated_count += 1
            logger.info(f"  ✓ Updated {symbol} with sector: {sector}")

            # Rate limiting to avoid overwhelming Yahoo Finance
            if i < len(symbols_with_null_sector):  # Don't sleep after last item
                logger.debug(f"  Waiting 1 second before next request...")
                time.sleep(1)

        except Exception as e:
            logger.error(f"  ✗ Failed to update {symbol}: {e}")
            failed_count += 1
            continue

    logger.info("\n" + "="*60)
    logger.info("Backfill completed!")
    logger.info(f"  Successfully updated: {updated_count}")
    logger.info(f"  Failed: {failed_count}")
    logger.info("="*60)

    # Verify the fix
    with db._get_connection() as conn:
        cursor = conn.execute(query)
        remaining = len(cursor.fetchall())
    logger.info(f"\nRemaining NULL sectors: {remaining}")

    if remaining == 0:
        logger.info("✓ All sectors have been filled!")
    else:
        logger.warning(f"⚠ {remaining} sectors still NULL (may need manual review)")


if __name__ == "__main__":
    backfill_sectors()
