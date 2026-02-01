# Data Module - Stock Universe & Data Providers

This module contains:
1. **Data Providers** - Hybrid data fetching (NSEpy + Yahoo Finance)
2. **Stock Universe** - Comprehensive Indian stock index data

---

## Stock Universe

### Overview

The Stock Universe system provides comprehensive data for Indian stock indices:

- **NIFTY 50** (50 stocks)
- **NIFTY Bank** (12 stocks)
- **NIFTY IT** (10 stocks)
- **NIFTY Auto** (10 stocks)
- **NIFTY Pharma** (10 stocks)
- **NIFTY FMCG** (10 stocks)

Each stock includes:
- Symbol and company name
- Sector and industry classification
- Market cap category (Large/Mid/Small Cap)
- Index weight (%)
- Index membership

**Last Updated:** 2025-01-31

### Files

- `nifty_constituents.py` - Stock data for all indices
- `stock_universe.py` - StockUniverse manager class

### Usage

#### Basic Usage

```python
from data.stock_universe import get_universe

# Get singleton instance
universe = get_universe()

# Get all NIFTY 50 symbols
nifty_symbols = universe.get_symbols('NIFTY_50')
print(f"NIFTY 50 has {len(nifty_symbols)} stocks")

# Get stock information
tcs_info = universe.get_stock_info('TCS')
print(f"TCS: {tcs_info['name']}")
print(f"Sector: {tcs_info['sector']}")
print(f"Indices: {tcs_info['indices']}")
```

#### Filtering

```python
# Filter by sector
it_stocks = universe.get_stocks_by_sector('Information Technology')
print(f"IT Sector has {len(it_stocks)} stocks")

# Filter by market cap
large_caps = universe.get_stocks_by_market_cap('Large Cap')

# Combined filtering
nifty_it = universe.get_symbols(
    index='NIFTY_50',
    sector='Information Technology'
)
```

#### Search & Discovery

```python
# Search stocks
results = universe.search_stocks('tata', search_in=['name', 'symbol'])

# Get top stocks by weight
top_10 = universe.get_top_stocks_by_weight('NIFTY_50', limit=10)

# Get available sectors
sectors = universe.get_available_sectors()
```

#### Statistics

```python
# Index summary
summary = universe.get_index_summary('NIFTY_50')
print(f"Total stocks: {summary['total_stocks']}")
print(f"Sectors: {summary['sectors']}")

# Universe statistics
stats = universe.get_universe_stats()
print(f"Total unique symbols: {stats['total_unique_symbols']}")
print(f"Indices: {stats['indices']}")
```

#### Validation

```python
# Check if symbol is valid
is_valid = universe.is_valid_symbol('TCS')

# Validate multiple symbols
symbols = ['TCS', 'INVALID', 'INFY']
validation = universe.validate_symbols(symbols)

# Filter to only valid symbols
valid_symbols = universe.filter_valid_symbols(symbols)
```

#### Export

```python
# Export to DataFrame
df = universe.to_dataframe('NIFTY_50')
df.to_csv('nifty_50.csv')

# Export to JSON
data = universe.export_to_json('NIFTY_50')
```

### Command Line Interface

Explore the stock universe from command line:

```bash
# Interactive mode
python scripts/explore_universe.py

# Or with make
make explore

# Show all indices
python scripts/explore_universe.py indices
make universe-stats

# Show index summary
python scripts/explore_universe.py summary NIFTY_50

# Show top stocks
python scripts/explore_universe.py top NIFTY_50 10

# View stock details
python scripts/explore_universe.py stock TCS
make stock-info SYMBOL=TCS

# Search stocks
python scripts/explore_universe.py search tata
make search-stocks QUERY=tata

# Browse by sector
python scripts/explore_universe.py sector "Information Technology"

# Export to JSON
python scripts/explore_universe.py export-json NIFTY_50 nifty.json

# Export to CSV
python scripts/explore_universe.py export-csv NIFTY_50 nifty.csv
```

### Makefile Commands

```bash
make universe          # View stock universe via API
make explore           # Interactive universe explorer
make universe-stats    # Show statistics
make stock-info SYMBOL=TCS         # Get stock info
make search-stocks QUERY=banking   # Search stocks
```

---

## Stock Universe Structure

### NIFTY 50 Example

```python
{
    'TCS': {
        'name': 'Tata Consultancy Services',
        'sector': 'Information Technology',
        'industry': 'IT Services & Consulting',
        'market_cap': 'Large Cap',
        'weight': 4.2
    },
    'RELIANCE': {
        'name': 'Reliance Industries',
        'sector': 'Energy',
        'industry': 'Oil & Gas',
        'market_cap': 'Large Cap',
        'weight': 8.5
    },
    ...
}
```

### Sector Distribution (NIFTY 50)

| Sector | Stocks |
|--------|--------|
| Financial Services | 9 |
| Information Technology | 5 |
| FMCG | 5 |
| Automobile | 5 |
| Pharmaceuticals | 5 |
| Metals | 4 |
| Cement | 3 |
| Energy | 3 |
| Infrastructure | 2 |
| Power | 2 |
| Telecom | 1 |
| Consumer Durables | 2 |
| Chemicals | 1 |
| Healthcare | 1 |
| Conglomerate | 1 |

### Top 10 by Weight

1. **HDFCBANK** - 9.2%
2. **RELIANCE** - 8.5%
3. **ICICIBANK** - 6.8%
4. **TCS** - 4.2%
5. **HINDUNILVR** - 4.2%
6. **BHARTIARTL** - 4.0%
7. **INFY** - 3.8%
8. **ITC** - 3.5%
9. **LT** - 3.5%
10. **SBIN** - 3.2%

---

## Data Providers

### Hybrid Data Provider

The system uses a hybrid approach for data fetching:

1. **Primary**: NSEpy (NSE India official data)
2. **Fallback**: Yahoo Finance (yfinance)

#### Features

- Automatic failover
- Circuit breaker pattern
- Rate limiting
- Multi-layer caching
- Comprehensive error handling

#### Usage

```python
from data.hybrid_provider import HybridDataProvider

provider = HybridDataProvider()

# Get comprehensive data for a stock
data = provider.get_comprehensive_data('TCS')

# Returns:
# {
#     'historical_data': DataFrame with OHLCV,
#     'technical_data': DataFrame with 40+ indicators,
#     'info': Dict with fundamentals,
#     'financials': Dict with financial statements,
#     'source': 'nse' or 'yahoo'
# }
```

#### Individual Providers

```python
# NSE Provider
from data.nse_provider import NSEProvider

nse = NSEProvider()
data = nse.get_comprehensive_data('TCS')

# Yahoo Finance Provider
from data.yahoo_provider import YahooProvider

yahoo = YahooProvider()
data = yahoo.get_comprehensive_data('TCS.NS')
```

---

## Updating the Universe

To update the stock universe with latest data:

1. Edit `data/nifty_constituents.py`
2. Update the constituent lists
3. Update `LAST_UPDATED` date
4. Run validation:

```bash
python data/stock_universe.py
```

This will display:
- Total stocks per index
- Sector distribution
- Top stocks by weight
- Validation results

---

## API Integration

The Stock Universe is automatically integrated with the FastAPI backend:

```bash
# Get universe via API
curl "http://localhost:8000/stocks/universe" | jq .

# Returns all indices with their constituents
{
  "total_stocks": 92,
  "indices": {
    "NIFTY_50": ["TCS", "INFY", ...],
    "NIFTY_BANK": ["HDFCBANK", "ICICIBANK", ...],
    "NIFTY_IT": ["TCS", "INFY", ...],
    ...
  },
  "timestamp": "2025-01-31T10:30:00"
}
```

---

## Extension

To add a new index:

1. Add data to `nifty_constituents.py`:

```python
NIFTY_ENERGY = {
    'RELIANCE': {
        'name': 'Reliance Industries',
        'sector': 'Energy',
        'industry': 'Oil & Gas',
        'market_cap': 'Large Cap',
        'weight': 35.0
    },
    ...
}
```

2. Add to `get_all_indices()`:

```python
def get_all_indices():
    return {
        'NIFTY_50': NIFTY_50,
        'NIFTY_BANK': NIFTY_BANK,
        'NIFTY_ENERGY': NIFTY_ENERGY,  # New index
        ...
    }
```

3. The StockUniverse will automatically pick it up!

---

## Best Practices

1. **Use singleton pattern**: Always use `get_universe()` instead of creating new instances
2. **Cache symbols**: Store frequently used symbol lists
3. **Validate symbols**: Always validate user input symbols
4. **Use filters**: Filter by sector/market cap instead of manual iteration
5. **Export for analysis**: Use `to_dataframe()` for pandas analysis

---

## Examples

### Example 1: Get all IT stocks from NIFTY 50

```python
from data.stock_universe import get_universe

universe = get_universe()
it_stocks = universe.get_symbols('NIFTY_50', sector='Information Technology')
print(it_stocks)  # ['TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM']
```

### Example 2: Find all Tata Group companies

```python
tata_stocks = universe.search_stocks('tata', search_in=['name'])
for stock in tata_stocks:
    print(f"{stock['symbol']}: {stock['name']}")
```

### Example 3: Export NIFTY Bank to CSV

```python
df = universe.to_dataframe('NIFTY_BANK')
df.to_csv('nifty_bank.csv', index=False)
print(f"Exported {len(df)} banking stocks")
```

### Example 4: Validate portfolio symbols

```python
portfolio = ['TCS', 'INFY', 'INVALID', 'WIPRO']
valid = universe.filter_valid_symbols(portfolio)
print(f"Valid symbols: {valid}")  # ['TCS', 'INFY', 'WIPRO']
```

---

## Support

For issues or updates:
1. Check NSE India website for latest constituents
2. Update `nifty_constituents.py` with new data
3. Run validation tests
4. Update `LAST_UPDATED` date
