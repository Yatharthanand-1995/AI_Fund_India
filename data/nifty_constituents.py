"""
NIFTY Index Constituents Data

Contains comprehensive data for major NSE indices:
- NIFTY 50
- NIFTY Bank
- NIFTY IT
- NIFTY Auto
- NIFTY Pharma
- NIFTY FMCG

Data includes:
- Company name
- Sector & Industry
- Market cap category
- Index membership

Data source: NSE India (as of Jan 2025)
"""

from typing import Dict, List
from datetime import datetime

# Last update timestamp
LAST_UPDATED = "2025-01-31"


# ============================================================================
# NIFTY 50 Constituents
# ============================================================================

NIFTY_50 = {
    # Technology
    'TCS': {
        'name': 'Tata Consultancy Services',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 4.2
    },
    'INFY': {
        'name': 'Infosys',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 3.8
    },
    'HCLTECH': {
        'name': 'HCL Technologies',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 1.8
    },
    'WIPRO': {
        'name': 'Wipro',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },
    'TECHM': {
        'name': 'Tech Mahindra',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 0.9
    },

    # Financial Services - Banks
    'HDFCBANK': {
        'name': 'HDFC Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Large Cap',
        'weight': 9.2
    },
    'ICICIBANK': {
        'name': 'ICICI Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Large Cap',
        'weight': 6.8
    },
    'SBIN': {
        'name': 'State Bank of India',
        'sector': 'Financial Services',
        'industry': 'Public Bank',
        'market_cap': 'Large Cap',
        'weight': 3.2
    },
    'KOTAKBANK': {
        'name': 'Kotak Mahindra Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Large Cap',
        'weight': 2.8
    },
    'AXISBANK': {
        'name': 'Axis Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Large Cap',
        'weight': 2.5
    },
    'INDUSINDBK': {
        'name': 'IndusInd Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },

    # Financial Services - NBFCs
    'BAJFINANCE': {
        'name': 'Bajaj Finance',
        'sector': 'Financial Services',
        'industry': 'NBFC',
        'market_cap': 'Large Cap',
        'weight': 2.4
    },
    'BAJAJFINSV': {
        'name': 'Bajaj Finserv',
        'sector': 'Financial Services',
        'industry': 'NBFC',
        'market_cap': 'Large Cap',
        'weight': 1.6
    },
    'SBILIFE': {
        'name': 'SBI Life Insurance',
        'sector': 'Financial Services',
        'industry': 'Life Insurance',
        'market_cap': 'Large Cap',
        'weight': 0.9
    },

    # Energy & Oil/Gas
    'RELIANCE': {
        'name': 'Reliance Industries',
        'sector': 'Energy',
        'industry': 'Oil & Gas',
        'market_cap': 'Large Cap',
        'weight': 8.5
    },
    'ONGC': {
        'name': 'Oil and Natural Gas Corporation',
        'sector': 'Energy',
        'industry': 'Oil & Gas',
        'market_cap': 'Large Cap',
        'weight': 1.8
    },
    'BPCL': {
        'name': 'Bharat Petroleum',
        'sector': 'Energy',
        'industry': 'Oil & Gas',
        'market_cap': 'Large Cap',
        'weight': 0.8
    },

    # FMCG
    'HINDUNILVR': {
        'name': 'Hindustan Unilever',
        'sector': 'FMCG',
        'industry': 'Personal Care',
        'market_cap': 'Large Cap',
        'weight': 4.2
    },
    'ITC': {
        'name': 'ITC',
        'sector': 'FMCG',
        'industry': 'Diversified',
        'market_cap': 'Large Cap',
        'weight': 3.5
    },
    'NESTLEIND': {
        'name': 'Nestle India',
        'sector': 'FMCG',
        'industry': 'Food Products',
        'market_cap': 'Large Cap',
        'weight': 1.4
    },
    'BRITANNIA': {
        'name': 'Britannia Industries',
        'sector': 'FMCG',
        'industry': 'Food Products',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },
    'TATACONSUM': {
        'name': 'Tata Consumer Products',
        'sector': 'FMCG',
        'industry': 'Food Products',
        'market_cap': 'Large Cap',
        'weight': 0.7
    },

    # Automobile
    'MARUTI': {
        'name': 'Maruti Suzuki',
        'sector': 'Automobile',
        'industry': 'Passenger Vehicles',
        'market_cap': 'Large Cap',
        'weight': 2.8
    },
    'TATAMOTORS': {
        'name': 'Tata Motors',
        'sector': 'Automobile',
        'industry': 'Automobiles',
        'market_cap': 'Large Cap',
        'weight': 1.5
    },
    'M&M': {
        'name': 'Mahindra & Mahindra',
        'sector': 'Automobile',
        'industry': 'Automobiles',
        'market_cap': 'Large Cap',
        'weight': 1.8
    },
    'EICHERMOT': {
        'name': 'Eicher Motors',
        'sector': 'Automobile',
        'industry': 'Two Wheelers',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },
    'HEROMOTOCO': {
        'name': 'Hero MotoCorp',
        'sector': 'Automobile',
        'industry': 'Two Wheelers',
        'market_cap': 'Large Cap',
        'weight': 1.0
    },

    # Pharmaceuticals
    'SUNPHARMA': {
        'name': 'Sun Pharmaceutical',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Large Cap',
        'weight': 1.9
    },
    'DRREDDY': {
        'name': 'Dr Reddys Laboratories',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Large Cap',
        'weight': 1.1
    },
    'CIPLA': {
        'name': 'Cipla',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Large Cap',
        'weight': 0.9
    },
    'DIVISLAB': {
        'name': 'Divis Laboratories',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Large Cap',
        'weight': 1.0
    },
    'APOLLOHOSP': {
        'name': 'Apollo Hospitals',
        'sector': 'Healthcare',
        'industry': 'Hospitals',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },

    # Metals & Mining
    'TATASTEEL': {
        'name': 'Tata Steel',
        'sector': 'Metals',
        'industry': 'Steel',
        'market_cap': 'Large Cap',
        'weight': 1.5
    },
    'HINDALCO': {
        'name': 'Hindalco Industries',
        'sector': 'Metals',
        'industry': 'Aluminium',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },
    'JSWSTEEL': {
        'name': 'JSW Steel',
        'sector': 'Metals',
        'industry': 'Steel',
        'market_cap': 'Large Cap',
        'weight': 1.3
    },
    'COALINDIA': {
        'name': 'Coal India',
        'sector': 'Metals',
        'industry': 'Coal',
        'market_cap': 'Large Cap',
        'weight': 1.0
    },

    # Cement
    'ULTRACEMCO': {
        'name': 'UltraTech Cement',
        'sector': 'Cement',
        'industry': 'Cement',
        'market_cap': 'Large Cap',
        'weight': 2.2
    },
    'SHREECEM': {
        'name': 'Shree Cement',
        'sector': 'Cement',
        'industry': 'Cement',
        'market_cap': 'Large Cap',
        'weight': 0.8
    },
    'GRASIM': {
        'name': 'Grasim Industries',
        'sector': 'Cement',
        'industry': 'Diversified',
        'market_cap': 'Large Cap',
        'weight': 0.9
    },

    # Infrastructure & Construction
    'LT': {
        'name': 'Larsen & Toubro',
        'sector': 'Infrastructure',
        'industry': 'Construction & Engineering',
        'market_cap': 'Large Cap',
        'weight': 3.5
    },
    'ADANIPORTS': {
        'name': 'Adani Ports',
        'sector': 'Infrastructure',
        'industry': 'Ports',
        'market_cap': 'Large Cap',
        'weight': 1.1
    },

    # Power
    'NTPC': {
        'name': 'NTPC',
        'sector': 'Power',
        'industry': 'Power Generation',
        'market_cap': 'Large Cap',
        'weight': 1.6
    },
    'POWERGRID': {
        'name': 'Power Grid Corporation',
        'sector': 'Power',
        'industry': 'Power Transmission',
        'market_cap': 'Large Cap',
        'weight': 1.4
    },

    # Telecom
    'BHARTIARTL': {
        'name': 'Bharti Airtel',
        'sector': 'Telecom',
        'industry': 'Telecom Services',
        'market_cap': 'Large Cap',
        'weight': 4.0
    },

    # Consumer Durables
    'TITAN': {
        'name': 'Titan Company',
        'sector': 'Consumer Durables',
        'industry': 'Jewellery',
        'market_cap': 'Large Cap',
        'weight': 1.5
    },
    'ASIANPAINT': {
        'name': 'Asian Paints',
        'sector': 'Consumer Durables',
        'industry': 'Paints',
        'market_cap': 'Large Cap',
        'weight': 2.1
    },

    # Chemicals & Agriculture
    'UPL': {
        'name': 'UPL',
        'sector': 'Chemicals',
        'industry': 'Agrochemicals',
        'market_cap': 'Large Cap',
        'weight': 0.6
    },

    # Conglomerate
    'ADANIENT': {
        'name': 'Adani Enterprises',
        'sector': 'Conglomerate',
        'industry': 'Diversified',
        'market_cap': 'Large Cap',
        'weight': 1.3
    },
}


# ============================================================================
# NIFTY Bank Constituents
# ============================================================================

NIFTY_BANK = {
    'HDFCBANK': NIFTY_50['HDFCBANK'],
    'ICICIBANK': NIFTY_50['ICICIBANK'],
    'SBIN': NIFTY_50['SBIN'],
    'KOTAKBANK': NIFTY_50['KOTAKBANK'],
    'AXISBANK': NIFTY_50['AXISBANK'],
    'INDUSINDBK': NIFTY_50['INDUSINDBK'],
    'BANDHANBNK': {
        'name': 'Bandhan Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Mid Cap',
        'weight': 1.5
    },
    'FEDERALBNK': {
        'name': 'Federal Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Mid Cap',
        'weight': 1.2
    },
    'IDFCFIRSTB': {
        'name': 'IDFC First Bank',
        'sector': 'Financial Services',
        'industry': 'Private Bank',
        'market_cap': 'Mid Cap',
        'weight': 0.9
    },
    'PNB': {
        'name': 'Punjab National Bank',
        'sector': 'Financial Services',
        'industry': 'Public Bank',
        'market_cap': 'Mid Cap',
        'weight': 1.3
    },
    'BANKBARODA': {
        'name': 'Bank of Baroda',
        'sector': 'Financial Services',
        'industry': 'Public Bank',
        'market_cap': 'Large Cap',
        'weight': 1.8
    },
    'AUBANK': {
        'name': 'AU Small Finance Bank',
        'sector': 'Financial Services',
        'industry': 'Small Finance Bank',
        'market_cap': 'Mid Cap',
        'weight': 0.8
    },
}


# ============================================================================
# NIFTY IT Constituents
# ============================================================================

NIFTY_IT = {
    'TCS': NIFTY_50['TCS'],
    'INFY': NIFTY_50['INFY'],
    'HCLTECH': NIFTY_50['HCLTECH'],
    'WIPRO': NIFTY_50['WIPRO'],
    'TECHM': NIFTY_50['TECHM'],
    'LTIM': {
        'name': 'LTIMindtree',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 1.8
    },
    'PERSISTENT': {
        'name': 'Persistent Systems',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Mid Cap',
        'weight': 0.9
    },
    'COFORGE': {
        'name': 'Coforge',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Mid Cap',
        'weight': 0.7
    },
    'MPHASIS': {
        'name': 'Mphasis',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Mid Cap',
        'weight': 0.6
    },
    'LTTS': {
        'name': 'L&T Technology Services',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 0.8
    },
}


# ============================================================================
# NIFTY Auto Constituents
# ============================================================================

NIFTY_AUTO = {
    'MARUTI': NIFTY_50['MARUTI'],
    'TATAMOTORS': NIFTY_50['TATAMOTORS'],
    'M&M': NIFTY_50['M&M'],
    'EICHERMOT': NIFTY_50['EICHERMOT'],
    'HEROMOTOCO': NIFTY_50['HEROMOTOCO'],
    'BAJAJ-AUTO': {
        'name': 'Bajaj Auto',
        'sector': 'Automobile',
        'industry': 'Two Wheelers',
        'market_cap': 'Large Cap',
        'weight': 2.5
    },
    'ASHOKLEY': {
        'name': 'Ashok Leyland',
        'sector': 'Automobile',
        'industry': 'Commercial Vehicles',
        'market_cap': 'Mid Cap',
        'weight': 1.2
    },
    'TVSMOTOR': {
        'name': 'TVS Motor',
        'sector': 'Automobile',
        'industry': 'Two Wheelers',
        'market_cap': 'Mid Cap',
        'weight': 1.5
    },
    'BOSCHLTD': {
        'name': 'Bosch',
        'sector': 'Automobile',
        'industry': 'Auto Components',
        'market_cap': 'Large Cap',
        'weight': 0.8
    },
    'MOTHERSON': {
        'name': 'Samvardhana Motherson',
        'sector': 'Automobile',
        'industry': 'Auto Components',
        'market_cap': 'Large Cap',
        'weight': 1.3
    },
}


# ============================================================================
# NIFTY Pharma Constituents
# ============================================================================

NIFTY_PHARMA = {
    'SUNPHARMA': NIFTY_50['SUNPHARMA'],
    'DRREDDY': NIFTY_50['DRREDDY'],
    'CIPLA': NIFTY_50['CIPLA'],
    'DIVISLAB': NIFTY_50['DIVISLAB'],
    'APOLLOHOSP': NIFTY_50['APOLLOHOSP'],
    'BIOCON': {
        'name': 'Biocon',
        'sector': 'Pharmaceuticals',
        'industry': 'Biotechnology',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },
    'ALKEM': {
        'name': 'Alkem Laboratories',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Mid Cap',
        'weight': 0.9
    },
    'LUPIN': {
        'name': 'Lupin',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Large Cap',
        'weight': 1.1
    },
    'AUROPHARMA': {
        'name': 'Aurobindo Pharma',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Large Cap',
        'weight': 1.0
    },
    'TORNTPHARM': {
        'name': 'Torrent Pharmaceuticals',
        'sector': 'Pharmaceuticals',
        'industry': 'Pharmaceuticals',
        'market_cap': 'Mid Cap',
        'weight': 0.8
    },
}


# ============================================================================
# NIFTY FMCG Constituents
# ============================================================================

NIFTY_FMCG = {
    'HINDUNILVR': NIFTY_50['HINDUNILVR'],
    'ITC': NIFTY_50['ITC'],
    'NESTLEIND': NIFTY_50['NESTLEIND'],
    'BRITANNIA': NIFTY_50['BRITANNIA'],
    'TATACONSUM': NIFTY_50['TATACONSUM'],
    'DABUR': {
        'name': 'Dabur India',
        'sector': 'FMCG',
        'industry': 'Personal Care',
        'market_cap': 'Large Cap',
        'weight': 1.5
    },
    'MARICO': {
        'name': 'Marico',
        'sector': 'FMCG',
        'industry': 'Personal Care',
        'market_cap': 'Large Cap',
        'weight': 1.3
    },
    'GODREJCP': {
        'name': 'Godrej Consumer Products',
        'sector': 'FMCG',
        'industry': 'Personal Care',
        'market_cap': 'Large Cap',
        'weight': 1.2
    },
    'COLPAL': {
        'name': 'Colgate Palmolive',
        'sector': 'FMCG',
        'industry': 'Personal Care',
        'market_cap': 'Large Cap',
        'weight': 0.9
    },
    'EMAMILTD': {
        'name': 'Emami',
        'sector': 'FMCG',
        'industry': 'Personal Care',
        'market_cap': 'Mid Cap',
        'weight': 0.7
    },
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_all_indices() -> Dict[str, Dict]:
    """Get all available indices"""
    return {
        'NIFTY_50': NIFTY_50,
        'NIFTY_BANK': NIFTY_BANK,
        'NIFTY_IT': NIFTY_IT,
        'NIFTY_AUTO': NIFTY_AUTO,
        'NIFTY_PHARMA': NIFTY_PHARMA,
        'NIFTY_FMCG': NIFTY_FMCG,
    }


def get_symbols_by_index(index_name: str) -> List[str]:
    """Get list of symbols for an index"""
    indices = get_all_indices()
    index_data = indices.get(index_name.upper(), {})
    return list(index_data.keys())


def get_symbols_by_sector(sector: str) -> List[str]:
    """Get all symbols in a sector"""
    symbols = []
    for symbol, data in NIFTY_50.items():
        if data['sector'].lower() == sector.lower():
            symbols.append(symbol)
    return symbols


def get_stock_info(symbol: str) -> Dict:
    """Get stock information"""
    # Check all indices
    all_indices = get_all_indices()
    for index_name, index_data in all_indices.items():
        if symbol in index_data:
            info = index_data[symbol].copy()
            info['symbol'] = symbol
            info['indices'] = [index_name]
            return info
    return {}


def get_sectors() -> List[str]:
    """Get all unique sectors"""
    sectors = set()
    for data in NIFTY_50.values():
        sectors.add(data['sector'])
    return sorted(list(sectors))


def get_market_cap_categories() -> List[str]:
    """Get market cap categories"""
    return ['Large Cap', 'Mid Cap', 'Small Cap']


# Example usage
if __name__ == "__main__":
    print("="*60)
    print("NIFTY Index Constituents")
    print("="*60)

    print(f"\nLast Updated: {LAST_UPDATED}")

    # Show NIFTY 50 summary
    print(f"\n{'NIFTY 50':-^60}")
    print(f"Total Constituents: {len(NIFTY_50)}")
    print(f"\nSector Distribution:")
    sectors = {}
    for symbol, data in NIFTY_50.items():
        sector = data['sector']
        sectors[sector] = sectors.get(sector, 0) + 1

    for sector, count in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sector}: {count} stocks")

    # Show top 10 by weight
    print(f"\n{'Top 10 by Weight':-^60}")
    sorted_stocks = sorted(NIFTY_50.items(), key=lambda x: x[1]['weight'], reverse=True)
    for symbol, data in sorted_stocks[:10]:
        print(f"  {symbol:12} {data['name']:30} {data['weight']:5.1f}%")

    # Show all indices
    print(f"\n{'Available Indices':-^60}")
    all_indices = get_all_indices()
    for index_name, index_data in all_indices.items():
        print(f"  {index_name:15} {len(index_data):3} stocks")

    # Sectors
    print(f"\n{'Sectors':-^60}")
    for sector in get_sectors():
        symbols = get_symbols_by_sector(sector)
        print(f"  {sector:25} {len(symbols):2} stocks")
