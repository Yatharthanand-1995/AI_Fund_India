"""
Sector-Specific Benchmarks for Indian Stock Market

Different sectors have fundamentally different financial characteristics:
- IT: High margins, high ROE, high P/E multiples
- Banking: Lower ROE, moderate P/E, asset-light
- Pharma: High margins, R&D intensive, volatile
- Auto: Capital intensive, cyclical, lower margins
- FMCG: Stable, high margins, premium multiples

Benchmarks calibrated for 2025-2026 Indian market conditions
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SectorBenchmarks:
    """
    Sector-specific financial benchmarks for Indian stocks

    Based on:
    - NSE sector averages (2023-2025)
    - Historical performance analysis
    - Industry best practices
    - Accounting for Indian market specifics
    """

    # Default benchmarks (market-wide averages)
    DEFAULT_BENCHMARKS = {
        # ROE thresholds (%)
        'roe_excellent': 15.0,
        'roe_good': 12.0,
        'roe_fair': 8.0,
        'roe_poor': 5.0,

        # P/E ratio thresholds
        'pe_undervalued': 15.0,
        'pe_fair': 22.0,
        'pe_expensive': 30.0,
        'pe_overvalued': 40.0,

        # P/B ratio thresholds
        'pb_undervalued': 2.0,
        'pb_fair': 4.0,
        'pb_expensive': 6.0,

        # Growth thresholds (%)
        'revenue_growth_high': 20.0,
        'revenue_growth_medium': 12.0,
        'revenue_growth_low': 6.0,

        # Debt levels (Debt/Equity)
        'debt_low': 0.5,
        'debt_moderate': 1.0,
        'debt_high': 2.0,

        # Margins (%)
        'margin_excellent': 20.0,
        'margin_good': 15.0,
        'margin_fair': 10.0,

        # Dividend yield (%)
        'dividend_high': 3.0,
        'dividend_medium': 2.0,
        'dividend_low': 1.0,

        # Promoter holding (%) — Indian-specific
        'promoter_high': 50.0,
        'promoter_medium': 30.0,
    }

    # Sector-specific benchmarks
    SECTOR_BENCHMARKS = {

        # INFORMATION TECHNOLOGY
        # Characteristics: High margins, high ROE, premium multiples, USD revenue
        'Technology': {
            'roe_excellent': 25.0,   # IT companies have higher ROE
            'roe_good': 20.0,
            'roe_fair': 15.0,
            'roe_poor': 10.0,

            'pe_undervalued': 20.0,  # IT trades at premium
            'pe_fair': 28.0,
            'pe_expensive': 35.0,
            'pe_overvalued': 45.0,

            'pb_undervalued': 4.0,   # Asset-light business
            'pb_fair': 8.0,
            'pb_expensive': 12.0,

            'revenue_growth_high': 15.0,  # Mature industry, lower growth
            'revenue_growth_medium': 10.0,
            'revenue_growth_low': 5.0,

            'debt_low': 0.1,         # Typically debt-free
            'debt_moderate': 0.3,
            'debt_high': 0.5,

            'margin_excellent': 25.0,  # High margin business
            'margin_good': 20.0,
            'margin_fair': 15.0,

            'dividend_high': 2.5,    # Lower dividends, growth focus
            'dividend_medium': 1.5,
            'dividend_low': 0.8,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # FINANCIAL SERVICES - BANKS
        # Characteristics: Lower ROE, moderate P/E, asset-heavy, NIM-driven
        'Financial Services': {
            'roe_excellent': 18.0,   # Banks have lower ROE than IT
            'roe_good': 14.0,
            'roe_fair': 10.0,
            'roe_poor': 6.0,

            'pe_undervalued': 12.0,  # Banks trade at discount
            'pe_fair': 18.0,
            'pe_expensive': 25.0,
            'pe_overvalued': 35.0,

            'pb_undervalued': 1.5,   # P/B more relevant for banks
            'pb_fair': 2.5,
            'pb_expensive': 4.0,

            'revenue_growth_high': 18.0,  # Credit growth driven
            'revenue_growth_medium': 12.0,
            'revenue_growth_low': 8.0,

            'debt_low': 5.0,         # Debt is their business (D/E not applicable)
            'debt_moderate': 8.0,    # Use different metrics
            'debt_high': 12.0,

            'margin_excellent': 4.0,   # NIM ~3-4%
            'margin_good': 3.0,
            'margin_fair': 2.5,

            'dividend_high': 3.5,    # Good dividend payers
            'dividend_medium': 2.5,
            'dividend_low': 1.5,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # PHARMACEUTICALS
        # Characteristics: High margins, R&D intensive, binary outcomes, volatile
        'Healthcare': {
            'roe_excellent': 20.0,
            'roe_good': 15.0,
            'roe_fair': 10.0,
            'roe_poor': 5.0,

            'pe_undervalued': 18.0,
            'pe_fair': 25.0,
            'pe_expensive': 35.0,
            'pe_overvalued': 50.0,   # Can trade at very high multiples

            'pb_undervalued': 2.5,
            'pb_fair': 5.0,
            'pb_expensive': 8.0,

            'revenue_growth_high': 20.0,  # Launch-driven growth
            'revenue_growth_medium': 12.0,
            'revenue_growth_low': 6.0,

            'debt_low': 0.3,
            'debt_moderate': 0.8,
            'debt_high': 1.5,

            'margin_excellent': 25.0,  # High margin business
            'margin_good': 18.0,
            'margin_fair': 12.0,

            'dividend_high': 2.0,
            'dividend_medium': 1.2,
            'dividend_low': 0.5,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # AUTOMOBILE
        # Characteristics: Capital intensive, cyclical, lower margins
        'Automobile': {
            'roe_excellent': 15.0,
            'roe_good': 12.0,
            'roe_fair': 8.0,
            'roe_poor': 4.0,

            'pe_undervalued': 12.0,  # Cyclical, lower multiples
            'pe_fair': 18.0,
            'pe_expensive': 25.0,
            'pe_overvalued': 35.0,

            'pb_undervalued': 1.5,
            'pb_fair': 3.0,
            'pb_expensive': 5.0,

            'revenue_growth_high': 15.0,  # Volume + pricing driven
            'revenue_growth_medium': 10.0,
            'revenue_growth_low': 5.0,

            'debt_low': 0.5,         # Capital intensive
            'debt_moderate': 1.2,
            'debt_high': 2.5,

            'margin_excellent': 12.0,  # Lower margin business
            'margin_good': 9.0,
            'margin_fair': 6.0,

            'dividend_high': 3.0,    # Mature companies pay dividends
            'dividend_medium': 2.0,
            'dividend_low': 1.0,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # FMCG (Fast Moving Consumer Goods)
        # Characteristics: Stable, high margins, premium valuations, brand power
        'Consumer Goods': {
            'roe_excellent': 30.0,   # FMCG has very high ROE
            'roe_good': 22.0,
            'roe_fair': 15.0,
            'roe_poor': 10.0,

            'pe_undervalued': 30.0,  # FMCG trades at premium
            'pe_fair': 45.0,
            'pe_expensive': 60.0,
            'pe_overvalued': 75.0,

            'pb_undervalued': 6.0,   # Asset-light, brand heavy
            'pb_fair': 12.0,
            'pb_expensive': 20.0,

            'revenue_growth_high': 15.0,  # Steady, predictable
            'revenue_growth_medium': 10.0,
            'revenue_growth_low': 6.0,

            'debt_low': 0.2,         # Low debt
            'debt_moderate': 0.5,
            'debt_high': 1.0,

            'margin_excellent': 20.0,  # High margin business
            'margin_good': 15.0,
            'margin_fair': 10.0,

            'dividend_high': 2.5,    # Stable dividend payers
            'dividend_medium': 1.8,
            'dividend_low': 1.0,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # ENERGY (Oil & Gas)
        # Characteristics: Capital intensive, commodity linked, cyclical
        'Energy': {
            'roe_excellent': 15.0,
            'roe_good': 12.0,
            'roe_fair': 8.0,
            'roe_poor': 4.0,

            'pe_undervalued': 8.0,   # Cyclical, low multiples
            'pe_fair': 12.0,
            'pe_expensive': 18.0,
            'pe_overvalued': 25.0,

            'pb_undervalued': 1.0,
            'pb_fair': 1.8,
            'pb_expensive': 3.0,

            'revenue_growth_high': 20.0,  # Commodity price driven
            'revenue_growth_medium': 10.0,
            'revenue_growth_low': 5.0,

            'debt_low': 0.8,         # Capital intensive
            'debt_moderate': 1.5,
            'debt_high': 2.5,

            'margin_excellent': 15.0,
            'margin_good': 10.0,
            'margin_fair': 6.0,

            'dividend_high': 4.0,    # Good dividend payers
            'dividend_medium': 3.0,
            'dividend_low': 2.0,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # TELECOMMUNICATIONS
        # Characteristics: Capital intensive, high debt, stable cash flows
        'Telecommunication': {
            'roe_excellent': 12.0,   # Lower ROE, high debt
            'roe_good': 8.0,
            'roe_fair': 5.0,
            'roe_poor': 2.0,

            'pe_undervalued': 10.0,
            'pe_fair': 15.0,
            'pe_expensive': 22.0,
            'pe_overvalued': 30.0,

            'pb_undervalued': 1.0,
            'pb_fair': 2.0,
            'pb_expensive': 3.5,

            'revenue_growth_high': 12.0,
            'revenue_growth_medium': 8.0,
            'revenue_growth_low': 4.0,

            'debt_low': 1.5,         # High debt is normal
            'debt_moderate': 3.0,
            'debt_high': 5.0,

            'margin_excellent': 35.0,  # High EBITDA margins
            'margin_good': 30.0,
            'margin_fair': 25.0,

            'dividend_high': 3.0,
            'dividend_medium': 2.0,
            'dividend_low': 1.0,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # REAL ESTATE
        # Characteristics: Capital intensive, cyclical, inventory heavy
        'Real Estate': {
            'roe_excellent': 15.0,
            'roe_good': 10.0,
            'roe_fair': 6.0,
            'roe_poor': 3.0,

            'pe_undervalued': 15.0,
            'pe_fair': 25.0,
            'pe_expensive': 40.0,
            'pe_overvalued': 60.0,

            'pb_undervalued': 1.0,
            'pb_fair': 2.0,
            'pb_expensive': 4.0,

            'revenue_growth_high': 25.0,  # Pre-sales driven
            'revenue_growth_medium': 15.0,
            'revenue_growth_low': 8.0,

            'debt_low': 0.8,
            'debt_moderate': 1.8,
            'debt_high': 3.0,

            'margin_excellent': 30.0,
            'margin_good': 20.0,
            'margin_fair': 12.0,

            'dividend_high': 2.0,
            'dividend_medium': 1.0,
            'dividend_low': 0.5,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },

        # METALS & MINING
        # Characteristics: Commodity linked, cyclical, capital intensive
        'Metals & Mining': {
            'roe_excellent': 18.0,
            'roe_good': 12.0,
            'roe_fair': 8.0,
            'roe_poor': 4.0,

            'pe_undervalued': 6.0,   # Very cyclical
            'pe_fair': 10.0,
            'pe_expensive': 15.0,
            'pe_overvalued': 22.0,

            'pb_undervalued': 0.8,
            'pb_fair': 1.5,
            'pb_expensive': 2.5,

            'revenue_growth_high': 20.0,
            'revenue_growth_medium': 12.0,
            'revenue_growth_low': 5.0,

            'debt_low': 0.5,
            'debt_moderate': 1.2,
            'debt_high': 2.5,

            'margin_excellent': 25.0,  # Varies with commodity prices
            'margin_good': 18.0,
            'margin_fair': 12.0,

            'dividend_high': 4.0,    # High dividends in good times
            'dividend_medium': 2.5,
            'dividend_low': 1.0,

            'promoter_high': 50.0,
            'promoter_medium': 30.0,
        },
    }

    # Sector name mappings (Yahoo Finance to our standard names)
    SECTOR_MAPPING = {
        'Technology': 'Technology',
        'Information Technology': 'Technology',
        'IT': 'Technology',

        'Financial Services': 'Financial Services',
        'Financials': 'Financial Services',
        'Banking': 'Financial Services',

        'Healthcare': 'Healthcare',
        'Pharmaceuticals': 'Healthcare',
        'Pharma': 'Healthcare',

        'Automobile': 'Automobile',
        'Auto': 'Automobile',
        'Automotive': 'Automobile',

        'Consumer Goods': 'Consumer Goods',
        'FMCG': 'Consumer Goods',
        'Consumer Defensive': 'Consumer Goods',
        'Consumer Cyclical': 'Consumer Goods',

        'Energy': 'Energy',
        'Oil & Gas': 'Energy',

        'Telecommunication': 'Telecommunication',
        'Telecom': 'Telecommunication',
        'Communication Services': 'Telecommunication',

        'Real Estate': 'Real Estate',
        'Realty': 'Real Estate',

        'Metals & Mining': 'Metals & Mining',
        'Basic Materials': 'Metals & Mining',
        'Materials': 'Metals & Mining',
    }

    @classmethod
    def get_benchmarks(cls, sector: Optional[str] = None) -> Dict[str, float]:
        """
        Get appropriate benchmarks for a sector

        Args:
            sector: Sector name (e.g., "Technology", "Financial Services")
                   If None or not found, returns default benchmarks

        Returns:
            Dictionary of benchmark thresholds
        """
        if not sector:
            logger.debug("No sector provided, using default benchmarks")
            return cls.DEFAULT_BENCHMARKS.copy()

        # Normalize sector name
        normalized_sector = cls.SECTOR_MAPPING.get(sector, sector)

        # Get sector-specific benchmarks
        benchmarks = cls.SECTOR_BENCHMARKS.get(normalized_sector)

        if benchmarks:
            logger.debug(f"Using sector-specific benchmarks for: {normalized_sector}")
            return benchmarks.copy()
        else:
            logger.debug(f"Sector '{sector}' not found, using default benchmarks")
            return cls.DEFAULT_BENCHMARKS.copy()

    @classmethod
    def get_all_sectors(cls) -> list:
        """Get list of all supported sectors"""
        return list(cls.SECTOR_BENCHMARKS.keys())

    @classmethod
    def print_sector_comparison(cls):
        """Print comparison table of sector benchmarks"""
        print("\n" + "="*80)
        print("SECTOR-SPECIFIC BENCHMARK COMPARISON")
        print("="*80)

        print(f"\n{'Sector':<25} {'ROE (Good)':<12} {'P/E (Fair)':<12} {'Margin (Good)':<12}")
        print("-"*80)

        for sector in sorted(cls.SECTOR_BENCHMARKS.keys()):
            benchmarks = cls.SECTOR_BENCHMARKS[sector]
            print(f"{sector:<25} "
                  f"{benchmarks['roe_good']:>10.1f}%  "
                  f"{benchmarks['pe_fair']:>10.1f}   "
                  f"{benchmarks['margin_good']:>10.1f}%")

        print("\n" + "="*80)


# Example usage and testing
if __name__ == "__main__":
    print("\nSECTOR BENCHMARKS MODULE - Testing\n")

    # Test getting benchmarks for different sectors
    sectors_to_test = ['Technology', 'Financial Services', 'Healthcare', 'Unknown Sector']

    for sector in sectors_to_test:
        benchmarks = SectorBenchmarks.get_benchmarks(sector)
        print(f"\n{sector}:")
        print(f"  ROE (Excellent): {benchmarks['roe_excellent']}%")
        print(f"  P/E (Fair): {benchmarks['pe_fair']}")
        print(f"  Margin (Good): {benchmarks['margin_good']}%")

    # Print comparison table
    SectorBenchmarks.print_sector_comparison()

    # Show all supported sectors
    print(f"\nSupported Sectors ({len(SectorBenchmarks.get_all_sectors())}):")
    for sector in SectorBenchmarks.get_all_sectors():
        print(f"  - {sector}")
