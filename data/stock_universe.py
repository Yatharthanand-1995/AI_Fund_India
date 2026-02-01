"""
Stock Universe Manager

Provides comprehensive utilities for managing stock universes:
- Multiple index support (NIFTY 50, NIFTY Bank, etc.)
- Sector and industry filtering
- Market cap categorization
- Stock metadata management
- Universe updates and validation

Usage:
    universe = StockUniverse()
    nifty_symbols = universe.get_symbols('NIFTY_50')
    it_stocks = universe.get_stocks_by_sector('Information Technology')
    stock_info = universe.get_stock_info('TCS')
"""

import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
import pandas as pd

from data.nifty_constituents import (
    NIFTY_50,
    NIFTY_BANK,
    NIFTY_IT,
    NIFTY_AUTO,
    NIFTY_PHARMA,
    NIFTY_FMCG,
    LAST_UPDATED,
    get_all_indices,
    get_symbols_by_index,
    get_symbols_by_sector,
    get_stock_info,
    get_sectors,
    get_market_cap_categories
)

logger = logging.getLogger(__name__)


class StockUniverse:
    """
    Stock Universe Manager

    Manages stock universe data with support for:
    - Multiple indices
    - Sector/industry filtering
    - Market cap categorization
    - Metadata enrichment
    """

    def __init__(self):
        """Initialize Stock Universe Manager"""
        self.indices = get_all_indices()
        self.last_updated = LAST_UPDATED

        # Build reverse lookups for efficiency
        self._symbol_to_indices = self._build_symbol_index_mapping()
        self._sector_to_symbols = self._build_sector_mapping()

        logger.info(f"Stock Universe initialized (updated: {self.last_updated})")
        logger.info(f"  Indices: {len(self.indices)}")
        logger.info(f"  Total unique symbols: {len(self._symbol_to_indices)}")

    def _build_symbol_index_mapping(self) -> Dict[str, List[str]]:
        """Build mapping of symbol -> list of indices"""
        mapping = {}
        for index_name, index_data in self.indices.items():
            for symbol in index_data.keys():
                if symbol not in mapping:
                    mapping[symbol] = []
                mapping[symbol].append(index_name)
        return mapping

    def _build_sector_mapping(self) -> Dict[str, Set[str]]:
        """Build mapping of sector -> set of symbols"""
        mapping = {}
        # Use NIFTY 50 as master list for sectors
        for symbol, data in NIFTY_50.items():
            sector = data['sector']
            if sector not in mapping:
                mapping[sector] = set()
            mapping[sector].add(symbol)
        return mapping

    # ========================================================================
    # Core Retrieval Methods
    # ========================================================================

    def get_symbols(
        self,
        index: str = 'NIFTY_50',
        sector: Optional[str] = None,
        market_cap: Optional[str] = None
    ) -> List[str]:
        """
        Get list of stock symbols with optional filtering

        Args:
            index: Index name (NIFTY_50, NIFTY_BANK, etc.)
            sector: Filter by sector (optional)
            market_cap: Filter by market cap (Large Cap, Mid Cap, Small Cap)

        Returns:
            List of stock symbols
        """
        # Get base symbols from index
        index_key = index.upper()
        if index_key not in self.indices:
            logger.warning(f"Unknown index: {index}. Using NIFTY_50")
            index_key = 'NIFTY_50'

        symbols = list(self.indices[index_key].keys())

        # Apply sector filter
        if sector:
            symbols = [
                s for s in symbols
                if self.indices[index_key][s]['sector'].lower() == sector.lower()
            ]

        # Apply market cap filter
        if market_cap:
            symbols = [
                s for s in symbols
                if self.indices[index_key][s]['market_cap'].lower() == market_cap.lower()
            ]

        return symbols

    def get_stock_info(self, symbol: str) -> Dict:
        """
        Get comprehensive stock information

        Args:
            symbol: Stock symbol

        Returns:
            {
                'symbol': str,
                'name': str,
                'sector': str,
                'industry': str,
                'market_cap': str,
                'weight': float,
                'indices': List[str]
            }
        """
        symbol = symbol.upper()

        # Check if symbol exists
        if symbol not in self._symbol_to_indices:
            logger.warning(f"Symbol not found: {symbol}")
            return {}

        # Get from first index that contains it
        first_index = self._symbol_to_indices[symbol][0]
        info = self.indices[first_index][symbol].copy()
        info['symbol'] = symbol
        info['indices'] = self._symbol_to_indices[symbol]

        return info

    def get_stocks_by_sector(self, sector: str, index: str = 'NIFTY_50') -> List[Dict]:
        """
        Get all stocks in a sector

        Args:
            sector: Sector name
            index: Index to search (default: NIFTY_50)

        Returns:
            List of stock info dicts
        """
        symbols = self.get_symbols(index=index, sector=sector)
        return [self.get_stock_info(s) for s in symbols]

    def get_stocks_by_market_cap(self, market_cap: str, index: str = 'NIFTY_50') -> List[Dict]:
        """
        Get all stocks in a market cap category

        Args:
            market_cap: Market cap category (Large Cap, Mid Cap, Small Cap)
            index: Index to search

        Returns:
            List of stock info dicts
        """
        symbols = self.get_symbols(index=index, market_cap=market_cap)
        return [self.get_stock_info(s) for s in symbols]

    def get_indices_for_symbol(self, symbol: str) -> List[str]:
        """
        Get all indices that contain a symbol

        Args:
            symbol: Stock symbol

        Returns:
            List of index names
        """
        symbol = symbol.upper()
        return self._symbol_to_indices.get(symbol, [])

    # ========================================================================
    # Metadata & Statistics
    # ========================================================================

    def get_available_indices(self) -> List[str]:
        """Get list of available indices"""
        return list(self.indices.keys())

    def get_available_sectors(self) -> List[str]:
        """Get list of available sectors"""
        return get_sectors()

    def get_available_market_caps(self) -> List[str]:
        """Get list of market cap categories"""
        return get_market_cap_categories()

    def get_index_summary(self, index: str = 'NIFTY_50') -> Dict:
        """
        Get summary statistics for an index

        Args:
            index: Index name

        Returns:
            {
                'name': str,
                'total_stocks': int,
                'sectors': Dict[str, int],
                'market_caps': Dict[str, int],
                'last_updated': str
            }
        """
        index_key = index.upper()
        if index_key not in self.indices:
            raise ValueError(f"Unknown index: {index}")

        index_data = self.indices[index_key]

        # Count by sector
        sectors = {}
        market_caps = {}
        for data in index_data.values():
            sector = data['sector']
            sectors[sector] = sectors.get(sector, 0) + 1

            mcap = data['market_cap']
            market_caps[mcap] = market_caps.get(mcap, 0) + 1

        return {
            'name': index_key,
            'total_stocks': len(index_data),
            'sectors': dict(sorted(sectors.items(), key=lambda x: x[1], reverse=True)),
            'market_caps': dict(sorted(market_caps.items())),
            'last_updated': self.last_updated
        }

    def get_universe_stats(self) -> Dict:
        """
        Get overall universe statistics

        Returns:
            {
                'total_unique_symbols': int,
                'indices_count': int,
                'sectors_count': int,
                'indices': Dict[str, int],
                'last_updated': str
            }
        """
        return {
            'total_unique_symbols': len(self._symbol_to_indices),
            'indices_count': len(self.indices),
            'sectors_count': len(self._sector_to_symbols),
            'indices': {
                name: len(data)
                for name, data in self.indices.items()
            },
            'last_updated': self.last_updated
        }

    # ========================================================================
    # Validation & Utilities
    # ========================================================================

    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if symbol exists in universe"""
        return symbol.upper() in self._symbol_to_indices

    def validate_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Validate multiple symbols

        Args:
            symbols: List of symbols to validate

        Returns:
            Dict mapping symbol -> is_valid (bool)
        """
        return {
            symbol: self.is_valid_symbol(symbol)
            for symbol in symbols
        }

    def filter_valid_symbols(self, symbols: List[str]) -> List[str]:
        """
        Filter list to only valid symbols

        Args:
            symbols: List of symbols

        Returns:
            List of valid symbols only
        """
        valid = [s for s in symbols if self.is_valid_symbol(s)]
        invalid = [s for s in symbols if not self.is_valid_symbol(s)]

        if invalid:
            logger.warning(f"Filtered out {len(invalid)} invalid symbols: {invalid[:5]}...")

        return valid

    # ========================================================================
    # Export Methods
    # ========================================================================

    def to_dataframe(
        self,
        index: str = 'NIFTY_50',
        include_weights: bool = True
    ) -> pd.DataFrame:
        """
        Convert index data to DataFrame

        Args:
            index: Index name
            include_weights: Include index weights

        Returns:
            DataFrame with stock information
        """
        index_key = index.upper()
        if index_key not in self.indices:
            raise ValueError(f"Unknown index: {index}")

        records = []
        for symbol, data in self.indices[index_key].items():
            record = {
                'symbol': symbol,
                'name': data['name'],
                'sector': data['sector'],
                'industry': data['industry'],
                'market_cap': data['market_cap']
            }
            if include_weights and 'weight' in data:
                record['weight'] = data['weight']

            records.append(record)

        df = pd.DataFrame(records)

        # Sort by weight if available
        if include_weights and 'weight' in df.columns:
            df = df.sort_values('weight', ascending=False)

        return df

    def export_to_json(self, index: str = 'NIFTY_50') -> Dict:
        """
        Export index data as JSON-serializable dict

        Args:
            index: Index name

        Returns:
            Dict with index data
        """
        index_key = index.upper()
        if index_key not in self.indices:
            raise ValueError(f"Unknown index: {index}")

        return {
            'index': index_key,
            'last_updated': self.last_updated,
            'total_stocks': len(self.indices[index_key]),
            'stocks': [
                {
                    'symbol': symbol,
                    **data
                }
                for symbol, data in self.indices[index_key].items()
            ]
        }

    # ========================================================================
    # Search & Discovery
    # ========================================================================

    def search_stocks(
        self,
        query: str,
        search_in: List[str] = ['symbol', 'name', 'sector']
    ) -> List[Dict]:
        """
        Search for stocks by query string

        Args:
            query: Search query
            search_in: Fields to search in (symbol, name, sector, industry)

        Returns:
            List of matching stock info dicts
        """
        query = query.lower()
        results = []

        for symbol in self._symbol_to_indices.keys():
            info = self.get_stock_info(symbol)

            match = False
            if 'symbol' in search_in and query in info['symbol'].lower():
                match = True
            if 'name' in search_in and query in info['name'].lower():
                match = True
            if 'sector' in search_in and query in info['sector'].lower():
                match = True
            if 'industry' in search_in and query in info['industry'].lower():
                match = True

            if match:
                results.append(info)

        return results

    def get_top_stocks_by_weight(self, index: str = 'NIFTY_50', limit: int = 10) -> List[Dict]:
        """
        Get top stocks by index weight

        Args:
            index: Index name
            limit: Number of stocks to return

        Returns:
            List of stock info dicts sorted by weight
        """
        index_key = index.upper()
        if index_key not in self.indices:
            raise ValueError(f"Unknown index: {index}")

        # Sort by weight
        sorted_stocks = sorted(
            self.indices[index_key].items(),
            key=lambda x: x[1].get('weight', 0),
            reverse=True
        )

        # Get top N
        return [
            {
                'symbol': symbol,
                **data
            }
            for symbol, data in sorted_stocks[:limit]
        ]


# Singleton instance
_universe_instance = None


def get_universe() -> StockUniverse:
    """Get or create singleton StockUniverse instance"""
    global _universe_instance
    if _universe_instance is None:
        _universe_instance = StockUniverse()
    return _universe_instance


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("="*70)
    print(" Stock Universe Manager - Test")
    print("="*70)

    # Initialize
    universe = StockUniverse()

    # Test 1: Get symbols
    print(f"\n{'Test 1: Get Symbols':-^70}")
    nifty_symbols = universe.get_symbols('NIFTY_50')
    print(f"NIFTY 50 has {len(nifty_symbols)} stocks")
    print(f"Sample: {nifty_symbols[:5]}")

    # Test 2: Get stock info
    print(f"\n{'Test 2: Stock Info':-^70}")
    tcs_info = universe.get_stock_info('TCS')
    print(f"TCS Info:")
    for key, value in tcs_info.items():
        print(f"  {key}: {value}")

    # Test 3: Sector filtering
    print(f"\n{'Test 3: Sector Filtering':-^70}")
    it_stocks = universe.get_stocks_by_sector('Information Technology')
    print(f"IT Sector has {len(it_stocks)} stocks:")
    for stock in it_stocks:
        print(f"  {stock['symbol']:12} {stock['name']}")

    # Test 4: Index summary
    print(f"\n{'Test 4: Index Summary':-^70}")
    summary = universe.get_index_summary('NIFTY_50')
    print(f"Index: {summary['name']}")
    print(f"Total Stocks: {summary['total_stocks']}")
    print(f"\nSector Distribution:")
    for sector, count in summary['sectors'].items():
        print(f"  {sector:25} {count:2} stocks")

    # Test 5: Search
    print(f"\n{'Test 5: Search':-^70}")
    results = universe.search_stocks('tata', search_in=['name'])
    print(f"Search 'tata' found {len(results)} stocks:")
    for stock in results:
        print(f"  {stock['symbol']:12} {stock['name']}")

    # Test 6: Top by weight
    print(f"\n{'Test 6: Top 5 by Weight':-^70}")
    top_stocks = universe.get_top_stocks_by_weight('NIFTY_50', limit=5)
    for stock in top_stocks:
        print(f"  {stock['symbol']:12} {stock['name']:30} {stock['weight']:.1f}%")

    # Test 7: DataFrame export
    print(f"\n{'Test 7: DataFrame Export':-^70}")
    df = universe.to_dataframe('NIFTY_50')
    print(df.head(10))

    # Test 8: Universe stats
    print(f"\n{'Test 8: Universe Stats':-^70}")
    stats = universe.get_universe_stats()
    print(f"Total Unique Symbols: {stats['total_unique_symbols']}")
    print(f"Total Indices: {stats['indices_count']}")
    print(f"Total Sectors: {stats['sectors_count']}")
    print(f"\nIndices:")
    for index_name, count in stats['indices'].items():
        print(f"  {index_name:15} {count:3} stocks")

    # Test 9: Validation
    print(f"\n{'Test 9: Symbol Validation':-^70}")
    test_symbols = ['TCS', 'INVALID', 'INFY', 'FAKE']
    validation = universe.validate_symbols(test_symbols)
    for symbol, is_valid in validation.items():
        status = "✓" if is_valid else "✗"
        print(f"  {status} {symbol}")

    print("\n" + "="*70)
    print("All tests completed!")
