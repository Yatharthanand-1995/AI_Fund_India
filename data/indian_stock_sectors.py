"""
Indian Stock Sector Mapping

Manual mapping of Indian stock symbols to their sectors.
Used as fallback when Yahoo Finance doesn't provide sector information.

Data source: NSE sector classifications
Last updated: 2026-02-09
"""

# Sector mapping for Indian stocks (Symbol -> Sector)
INDIAN_STOCK_SECTORS = {
    # Financial Services
    'HDFCBANK': 'Financial Services',
    'ICICIBANK': 'Financial Services',
    'AXISBANK': 'Financial Services',
    'KOTAKBANK': 'Financial Services',
    'SBIN': 'Financial Services',
    'BAJFINANCE': 'Financial Services',
    'BAJAJFINSV': 'Financial Services',
    'INDUSINDBK': 'Financial Services',
    'HDFC': 'Financial Services',
    'HDFCLIFE': 'Financial Services',
    'SBILIFE': 'Financial Services',
    'ICICIGI': 'Financial Services',
    'BAJAJ-AUTO': 'Automobile',

    # Information Technology
    'TCS': 'Information Technology',
    'INFY': 'Information Technology',
    'WIPRO': 'Information Technology',
    'HCLTECH': 'Information Technology',
    'TECHM': 'Information Technology',
    'LTI': 'Information Technology',
    'LTIM': 'Information Technology',
    'COFORGE': 'Information Technology',
    'MPHASIS': 'Information Technology',
    'PERSISTENT': 'Information Technology',

    # Oil & Gas
    'RELIANCE': 'Oil & Gas',
    'ONGC': 'Oil & Gas',
    'BPCL': 'Oil & Gas',
    'IOC': 'Oil & Gas',
    'GAIL': 'Oil & Gas',
    'ADANIGREEN': 'Power',
    'ADANITRANS': 'Power',

    # Automobile
    'MARUTI': 'Automobile',
    'M&M': 'Automobile',
    'TATAMOTORS': 'Automobile',
    'EICHERMOT': 'Automobile',
    'HEROMOTOCO': 'Automobile',
    'ASHOKLEY': 'Automobile',
    'TVSMOTOR': 'Automobile',
    'BOSCHLTD': 'Automobile',

    # Pharmaceuticals
    'SUNPHARMA': 'Pharmaceuticals',
    'DRREDDY': 'Pharmaceuticals',
    'CIPLA': 'Pharmaceuticals',
    'DIVISLAB': 'Pharmaceuticals',
    'AUROPHARMA': 'Pharmaceuticals',
    'LUPIN': 'Pharmaceuticals',
    'BIOCON': 'Pharmaceuticals',
    'TORNTPHARM': 'Pharmaceuticals',
    'ALKEM': 'Pharmaceuticals',

    # FMCG (Fast Moving Consumer Goods)
    'HINDUNILVR': 'FMCG',
    'ITC': 'FMCG',
    'NESTLEIND': 'FMCG',
    'BRITANNIA': 'FMCG',
    'DABUR': 'FMCG',
    'MARICO': 'FMCG',
    'GODREJCP': 'FMCG',
    'COLPAL': 'FMCG',
    'TATACONSUM': 'FMCG',

    # Metals & Mining
    'TATASTEEL': 'Basic Materials',
    'HINDALCO': 'Basic Materials',
    'JSWSTEEL': 'Basic Materials',
    'COALINDIA': 'Basic Materials',
    'VEDL': 'Basic Materials',
    'NMDC': 'Basic Materials',
    'SAIL': 'Basic Materials',
    'JINDALSTEL': 'Basic Materials',

    # Cement
    'ULTRACEMCO': 'Cement',
    'SHREECEM': 'Cement',
    'AMBUJACEM': 'Cement',
    'ACC': 'Cement',
    'GRASIM': 'Cement',

    # Power & Energy
    'NTPC': 'Power',
    'POWERGRID': 'Power',
    'ADANIPOWER': 'Power',
    'TATAPOWER': 'Power',

    # Telecom
    'BHARTIARTL': 'Telecom',
    'IDEA': 'Telecom',

    # Infrastructure & Construction
    'LT': 'Infrastructure',
    'ADANIENT': 'Infrastructure',
    'ADANIPORTS': 'Infrastructure',

    # Chemicals
    'PIDILITIND': 'Chemicals',
    'AARTI': 'Chemicals',
    'DEEPAKNTR': 'Chemicals',
    'SRF': 'Chemicals',
    'CLEAN': 'Chemicals',

    # Consumer Durables
    'TITAN': 'Consumer Durables',
    'VOLTAS': 'Consumer Durables',
    'HAVELLS': 'Consumer Durables',
    'DIXON': 'Consumer Durables',

    # Media & Entertainment
    'ZEEL': 'Media',
    'SUNTV': 'Media',
    'PVR': 'Media',

    # Real Estate
    'DLF': 'Real Estate',
    'GODREJPROP': 'Real Estate',
    'OBEROIRLTY': 'Real Estate',
    'PRESTIGE': 'Real Estate',

    # Retail
    'DMART': 'Retail',
    'TRENT': 'Retail',
    'ABFRL': 'Retail',
}


def get_sector(symbol: str) -> str:
    """
    Get sector for an Indian stock symbol.

    Args:
        symbol: Stock symbol (with or without .NS suffix)

    Returns:
        Sector name or 'Unknown' if not found
    """
    # Remove .NS suffix if present
    clean_symbol = symbol.replace('.NS', '').replace('.BO', '').upper()

    return INDIAN_STOCK_SECTORS.get(clean_symbol, 'Unknown')


def get_all_sectors() -> set:
    """Get list of all unique sectors"""
    return set(INDIAN_STOCK_SECTORS.values())


def get_stocks_by_sector(sector: str) -> list:
    """Get all stocks in a given sector"""
    return [symbol for symbol, sec in INDIAN_STOCK_SECTORS.items() if sec == sector]
