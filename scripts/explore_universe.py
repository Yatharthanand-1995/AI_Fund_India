"""
Stock Universe Explorer

Interactive script to explore the stock universe:
- View all indices
- Browse stocks by sector
- Search for specific stocks
- Export data to various formats
- View universe statistics

Usage:
    python scripts/explore_universe.py
"""

import sys
import json
from typing import Optional
from data.stock_universe import get_universe


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def show_available_indices():
    """Show all available indices"""
    print_header("Available Indices")

    universe = get_universe()
    stats = universe.get_universe_stats()

    print(f"\nTotal Indices: {stats['indices_count']}")
    print(f"Total Unique Symbols: {stats['total_unique_symbols']}")
    print(f"Last Updated: {stats['last_updated']}\n")

    for index_name, count in stats['indices'].items():
        print(f"  {index_name:15} {count:3} stocks")


def show_index_summary(index_name: str = 'NIFTY_50'):
    """Show summary for a specific index"""
    print_header(f"{index_name} Summary")

    universe = get_universe()
    summary = universe.get_index_summary(index_name)

    print(f"\nTotal Stocks: {summary['total_stocks']}")
    print(f"Last Updated: {summary['last_updated']}")

    print(f"\nSector Distribution:")
    for sector, count in summary['sectors'].items():
        print(f"  {sector:30} {count:2} stocks")

    print(f"\nMarket Cap Distribution:")
    for mcap, count in summary['market_caps'].items():
        print(f"  {mcap:15} {count:2} stocks")


def show_top_stocks(index_name: str = 'NIFTY_50', limit: int = 10):
    """Show top stocks by weight"""
    print_header(f"Top {limit} Stocks by Weight - {index_name}")

    universe = get_universe()
    top_stocks = universe.get_top_stocks_by_weight(index_name, limit)

    print(f"\n{'Rank':<6}{'Symbol':<12}{'Name':<35}{'Weight':>8}{'Sector':<25}")
    print("-" * 90)

    for i, stock in enumerate(top_stocks, 1):
        print(f"{i:<6}{stock['symbol']:<12}{stock['name']:<35}{stock['weight']:>7.1f}%  {stock['sector']:<25}")


def show_sector_stocks(sector: str, index_name: str = 'NIFTY_50'):
    """Show all stocks in a sector"""
    print_header(f"{sector} Stocks - {index_name}")

    universe = get_universe()
    stocks = universe.get_stocks_by_sector(sector, index_name)

    print(f"\nTotal: {len(stocks)} stocks\n")

    print(f"{'Symbol':<12}{'Name':<40}{'Industry':<30}")
    print("-" * 85)

    for stock in stocks:
        print(f"{stock['symbol']:<12}{stock['name']:<40}{stock['industry']:<30}")


def show_stock_details(symbol: str):
    """Show detailed information for a stock"""
    print_header(f"Stock Details - {symbol}")

    universe = get_universe()
    info = universe.get_stock_info(symbol)

    if not info:
        print(f"\n❌ Symbol '{symbol}' not found in universe")
        return

    print(f"\nSymbol:      {info['symbol']}")
    print(f"Name:        {info['name']}")
    print(f"Sector:      {info['sector']}")
    print(f"Industry:    {info['industry']}")
    print(f"Market Cap:  {info['market_cap']}")

    if 'weight' in info:
        print(f"Weight:      {info['weight']:.2f}%")

    print(f"\nIndices:")
    for idx in info['indices']:
        print(f"  • {idx}")


def search_stocks(query: str):
    """Search for stocks"""
    print_header(f"Search Results for '{query}'")

    universe = get_universe()
    results = universe.search_stocks(query, search_in=['symbol', 'name', 'sector', 'industry'])

    print(f"\nFound {len(results)} matches\n")

    if results:
        print(f"{'Symbol':<12}{'Name':<35}{'Sector':<25}{'Indices':<20}")
        print("-" * 95)

        for stock in results:
            indices_str = ', '.join(stock['indices'][:2])
            if len(stock['indices']) > 2:
                indices_str += f" +{len(stock['indices'])-2}"
            print(f"{stock['symbol']:<12}{stock['name']:<35}{stock['sector']:<25}{indices_str:<20}")


def export_index_to_json(index_name: str = 'NIFTY_50', filename: Optional[str] = None):
    """Export index to JSON file"""
    universe = get_universe()

    if filename is None:
        filename = f"{index_name.lower()}_stocks.json"

    data = universe.export_to_json(index_name)

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Exported {index_name} to {filename}")
    print(f"   {len(data['stocks'])} stocks")


def export_index_to_csv(index_name: str = 'NIFTY_50', filename: Optional[str] = None):
    """Export index to CSV file"""
    universe = get_universe()

    if filename is None:
        filename = f"{index_name.lower()}_stocks.csv"

    df = universe.to_dataframe(index_name)
    df.to_csv(filename, index=False)

    print(f"\n✅ Exported {index_name} to {filename}")
    print(f"   {len(df)} stocks")


def interactive_mode():
    """Interactive exploration mode"""
    universe = get_universe()

    print("\n" + "🔍"*35)
    print(" Stock Universe Explorer - Interactive Mode")
    print("🔍"*35)

    print("\nCommands:")
    print("  1. Show available indices")
    print("  2. Show index summary")
    print("  3. Show top stocks by weight")
    print("  4. Browse stocks by sector")
    print("  5. View stock details")
    print("  6. Search stocks")
    print("  7. Export index to JSON")
    print("  8. Export index to CSV")
    print("  q. Quit")

    while True:
        print("\n" + "-"*70)
        choice = input("\nEnter command number (or 'q' to quit): ").strip()

        if choice == 'q':
            print("\nGoodbye! 👋")
            break

        elif choice == '1':
            show_available_indices()

        elif choice == '2':
            index = input("Enter index name (default: NIFTY_50): ").strip() or 'NIFTY_50'
            show_index_summary(index.upper())

        elif choice == '3':
            index = input("Enter index name (default: NIFTY_50): ").strip() or 'NIFTY_50'
            limit = input("Enter number of stocks (default: 10): ").strip() or '10'
            show_top_stocks(index.upper(), int(limit))

        elif choice == '4':
            # Show available sectors first
            sectors = universe.get_available_sectors()
            print("\nAvailable Sectors:")
            for i, sector in enumerate(sectors, 1):
                print(f"  {i}. {sector}")

            sector_choice = input("\nEnter sector name or number: ").strip()

            # Handle numeric choice
            if sector_choice.isdigit():
                idx = int(sector_choice) - 1
                if 0 <= idx < len(sectors):
                    sector = sectors[idx]
                else:
                    print("❌ Invalid sector number")
                    continue
            else:
                sector = sector_choice

            index = input("Enter index (default: NIFTY_50): ").strip() or 'NIFTY_50'
            show_sector_stocks(sector, index.upper())

        elif choice == '5':
            symbol = input("Enter stock symbol: ").strip()
            if symbol:
                show_stock_details(symbol.upper())
            else:
                print("❌ Symbol cannot be empty")

        elif choice == '6':
            query = input("Enter search query: ").strip()
            if query:
                search_stocks(query)
            else:
                print("❌ Query cannot be empty")

        elif choice == '7':
            index = input("Enter index name (default: NIFTY_50): ").strip() or 'NIFTY_50'
            filename = input("Enter filename (optional): ").strip() or None
            export_index_to_json(index.upper(), filename)

        elif choice == '8':
            index = input("Enter index name (default: NIFTY_50): ").strip() or 'NIFTY_50'
            filename = input("Enter filename (optional): ").strip() or None
            export_index_to_csv(index.upper(), filename)

        else:
            print("❌ Invalid command")


def main():
    """Main function"""
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == 'indices':
            show_available_indices()

        elif command == 'summary':
            index = sys.argv[2].upper() if len(sys.argv) > 2 else 'NIFTY_50'
            show_index_summary(index)

        elif command == 'top':
            index = sys.argv[2].upper() if len(sys.argv) > 2 else 'NIFTY_50'
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            show_top_stocks(index, limit)

        elif command == 'sector':
            if len(sys.argv) < 3:
                print("Usage: python explore_universe.py sector <sector_name> [index]")
                return
            sector = sys.argv[2]
            index = sys.argv[3].upper() if len(sys.argv) > 3 else 'NIFTY_50'
            show_sector_stocks(sector, index)

        elif command == 'stock':
            if len(sys.argv) < 3:
                print("Usage: python explore_universe.py stock <symbol>")
                return
            symbol = sys.argv[2].upper()
            show_stock_details(symbol)

        elif command == 'search':
            if len(sys.argv) < 3:
                print("Usage: python explore_universe.py search <query>")
                return
            query = ' '.join(sys.argv[2:])
            search_stocks(query)

        elif command == 'export-json':
            index = sys.argv[2].upper() if len(sys.argv) > 2 else 'NIFTY_50'
            filename = sys.argv[3] if len(sys.argv) > 3 else None
            export_index_to_json(index, filename)

        elif command == 'export-csv':
            index = sys.argv[2].upper() if len(sys.argv) > 2 else 'NIFTY_50'
            filename = sys.argv[3] if len(sys.argv) > 3 else None
            export_index_to_csv(index, filename)

        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  indices              - Show all available indices")
            print("  summary [index]      - Show index summary")
            print("  top [index] [limit]  - Show top stocks by weight")
            print("  sector <name> [idx]  - Show stocks in sector")
            print("  stock <symbol>       - Show stock details")
            print("  search <query>       - Search stocks")
            print("  export-json [index]  - Export to JSON")
            print("  export-csv [index]   - Export to CSV")

    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
