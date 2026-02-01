"""
Log Analyzer

Analyzes application logs to extract insights:
- Error patterns
- Slow requests
- Most active endpoints
- Agent performance
- Error frequency

Usage:
    python scripts/analyze_logs.py
    python scripts/analyze_logs.py --file logs/app.log --errors-only
"""

import argparse
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List


def parse_log_line(line: str) -> Dict:
    """Parse a log line"""
    # Try JSON format first
    try:
        return json.loads(line)
    except:
        pass

    # Try standard format
    # Format: 2025-01-31 10:30:00 - module - LEVEL - message
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([\w\.]+) - (\w+) - (.+)'
    match = re.match(pattern, line)

    if match:
        return {
            'timestamp': match.group(1),
            'logger': match.group(2),
            'level': match.group(3),
            'message': match.group(4)
        }

    return {}


def analyze_logs(log_file: Path, errors_only: bool = False) -> Dict:
    """Analyze log file"""
    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}")
        return {}

    print(f"Analyzing {log_file}...")

    stats = {
        'total_lines': 0,
        'levels': Counter(),
        'loggers': Counter(),
        'errors': [],
        'slow_requests': [],
        'endpoints': Counter(),
        'symbols': Counter(),
    }

    with open(log_file, 'r') as f:
        for line in f:
            stats['total_lines'] += 1
            parsed = parse_log_line(line.strip())

            if not parsed:
                continue

            level = parsed.get('level', 'UNKNOWN')
            stats['levels'][level] += 1

            if errors_only and level not in ['ERROR', 'CRITICAL']:
                continue

            logger = parsed.get('logger', 'unknown')
            stats['loggers'][logger] += 1

            message = parsed.get('message', '')

            # Track errors
            if level in ['ERROR', 'CRITICAL']:
                stats['errors'].append({
                    'timestamp': parsed.get('timestamp'),
                    'logger': logger,
                    'message': message
                })

            # Track slow requests
            if 'slow request' in message.lower():
                stats['slow_requests'].append({
                    'timestamp': parsed.get('timestamp'),
                    'message': message
                })

            # Track endpoints
            if 'api call' in message.lower() or 'request' in message.lower():
                # Extract endpoint from message
                endpoint_match = re.search(r'(POST|GET|PUT|DELETE) (/[\w/-]+)', message)
                if endpoint_match:
                    endpoint = f"{endpoint_match.group(1)} {endpoint_match.group(2)}"
                    stats['endpoints'][endpoint] += 1

            # Track symbols
            symbol_match = re.search(r"symbol['\": ]+([A-Z&]+)", message, re.IGNORECASE)
            if symbol_match:
                stats['symbols'][symbol_match.group(1)] += 1

    return stats


def print_stats(stats: Dict):
    """Print analysis results"""
    print("\n" + "="*80)
    print(" Log Analysis Results".center(80))
    print("="*80)

    # Summary
    print(f"\nTotal Lines: {stats['total_lines']:,}")

    # Log Levels
    print("\n┌─ LOG LEVELS " + "─"*66 + "┐")
    for level, count in stats['levels'].most_common():
        pct = (count / stats['total_lines'] * 100) if stats['total_lines'] > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"│ {level:<12} {count:>8} ({pct:>5.1f}%)  {bar:<35}│")
    print("└" + "─"*78 + "┘")

    # Top Loggers
    print("\n┌─ TOP LOGGERS " + "─"*64 + "┐")
    for logger, count in stats['loggers'].most_common(10):
        print(f"│ {logger:<50} {count:>25}│")
    print("└" + "─"*78 + "┘")

    # Top Endpoints
    if stats['endpoints']:
        print("\n┌─ TOP ENDPOINTS " + "─"*62 + "┐")
        for endpoint, count in stats['endpoints'].most_common(10):
            print(f"│ {endpoint:<50} {count:>25}│")
        print("└" + "─"*78 + "┘")

    # Top Symbols
    if stats['symbols']:
        print("\n┌─ MOST ANALYZED SYMBOLS " + "─"*53 + "┐")
        for symbol, count in stats['symbols'].most_common(10):
            print(f"│ {symbol:<50} {count:>25}│")
        print("└" + "─"*78 + "┘")

    # Recent Errors
    if stats['errors']:
        print("\n┌─ RECENT ERRORS " + "─"*62 + "┐")
        for error in stats['errors'][-10:]:
            timestamp = error.get('timestamp', 'unknown')
            logger = error.get('logger', 'unknown')
            message = error.get('message', '')[:60]
            print(f"│ [{timestamp}] {logger}")
            print(f"│   {message}")
            print("│")
        print(f"│ Total Errors: {len(stats['errors'])}")
        print("└" + "─"*78 + "┘")

    # Slow Requests
    if stats['slow_requests']:
        print("\n┌─ SLOW REQUESTS " + "─"*62 + "┐")
        for req in stats['slow_requests'][-10:]:
            timestamp = req.get('timestamp', 'unknown')
            message = req.get('message', '')[:60]
            print(f"│ [{timestamp}]")
            print(f"│   {message}")
            print("│")
        print(f"│ Total Slow Requests: {len(stats['slow_requests'])}")
        print("└" + "─"*78 + "┘")


def main():
    parser = argparse.ArgumentParser(description='Analyze application logs')
    parser.add_argument(
        '--file',
        default='logs/app.log',
        help='Log file to analyze (default: logs/app.log)'
    )
    parser.add_argument(
        '--errors-only',
        action='store_true',
        help='Show only errors'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    log_file = Path(args.file)
    stats = analyze_logs(log_file, args.errors_only)

    if not stats:
        return

    if args.json:
        # Convert Counter objects to dicts
        output = {
            'total_lines': stats['total_lines'],
            'levels': dict(stats['levels']),
            'loggers': dict(stats['loggers']),
            'endpoints': dict(stats['endpoints']),
            'symbols': dict(stats['symbols']),
            'error_count': len(stats['errors']),
            'slow_request_count': len(stats['slow_requests']),
        }
        print(json.dumps(output, indent=2))
    else:
        print_stats(stats)


if __name__ == "__main__":
    main()
