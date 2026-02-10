#!/usr/bin/env python3
"""
System Cleanup Utility

Cleans up old logs, temporary files, and expired cache data.

Usage:
    python scripts/cleanup.py
    python scripts/cleanup.py --days 7 --dry-run
    python scripts/cleanup.py --aggressive
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_logs(days: int = 7, dry_run: bool = False) -> int:
    """
    Clean up old log files.

    Args:
        days: Delete logs older than this many days
        dry_run: If True, only show what would be deleted

    Returns:
        Number of files deleted
    """
    cutoff = datetime.now() - timedelta(days=days)
    logs_dir = Path('logs')

    if not logs_dir.exists():
        logger.info("No logs directory found")
        return 0

    deleted = 0
    total_size = 0

    logger.info(f"Cleaning log files older than {days} days...")

    for log_file in logs_dir.glob('*.log*'):
        if log_file.name.startswith('app.log') and log_file.name != 'app.log':
            # app.log.1, app.log.2, etc.
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)

            if file_time < cutoff:
                size = log_file.stat().st_size
                if dry_run:
                    logger.info(f"  [DRY RUN] Would delete: {log_file.name} ({size / 1024:.1f} KB)")
                else:
                    log_file.unlink()
                    logger.info(f"  ✓ Deleted: {log_file.name} ({size / 1024:.1f} KB)")

                deleted += 1
                total_size += size

        elif log_file.name.startswith('daily.log.'):
            # daily.log.2024-01-01
            try:
                date_str = log_file.name.split('.')[-1]
                file_date = datetime.strptime(date_str, '%Y-%m-%d')

                if file_date < cutoff.date():
                    size = log_file.stat().st_size
                    if dry_run:
                        logger.info(f"  [DRY RUN] Would delete: {log_file.name} ({size / 1024:.1f} KB)")
                    else:
                        log_file.unlink()
                        logger.info(f"  ✓ Deleted: {log_file.name} ({size / 1024:.1f} KB)")

                    deleted += 1
                    total_size += size
            except ValueError:
                logger.warning(f"  Skipping {log_file.name} (couldn't parse date)")

    if deleted > 0:
        logger.info(f"  Total: {deleted} files, {total_size / 1024 / 1024:.2f} MB freed")
    else:
        logger.info("  No old log files to clean")

    return deleted


def cleanup_cache(dry_run: bool = False) -> int:
    """
    Clean up cache files (if applicable).

    Args:
        dry_run: If True, only show what would be deleted

    Returns:
        Number of items cleaned
    """
    logger.info("Cleaning cache data...")

    try:
        from core.cache_manager import get_cache_manager

        manager = get_cache_manager()

        if dry_run:
            stats = manager.stats()
            total_items = sum(cache_stats['size'] for cache_stats in stats.values())
            logger.info(f"  [DRY RUN] Would clean {total_items} cached items")
            return 0
        else:
            # Cleanup expired entries
            results = manager.cleanup_all_expired()
            total_cleaned = sum(results.values())

            if total_cleaned > 0:
                logger.info(f"  ✓ Cleaned {total_cleaned} expired cache entries")
            else:
                logger.info("  No expired cache entries to clean")

            return total_cleaned

    except Exception as e:
        logger.warning(f"  Cache cleanup failed: {e}")
        return 0


def cleanup_temp_files(dry_run: bool = False) -> int:
    """
    Clean up temporary files.

    Args:
        dry_run: If True, only show what would be deleted

    Returns:
        Number of files deleted
    """
    logger.info("Cleaning temporary files...")

    temp_patterns = [
        '**/*.pyc',
        '**/__pycache__',
        '**/.pytest_cache',
        '**/.coverage',
        '**/htmlcov',
        '**/*.tmp',
        '**/.DS_Store',
    ]

    deleted = 0

    for pattern in temp_patterns:
        for item in Path('.').glob(pattern):
            # Skip virtual environments and node_modules
            if 'venv' in str(item) or 'node_modules' in str(item):
                continue

            if item.is_file():
                if dry_run:
                    logger.info(f"  [DRY RUN] Would delete: {item}")
                else:
                    item.unlink()
                    logger.info(f"  ✓ Deleted: {item}")
                deleted += 1
            elif item.is_dir():
                if dry_run:
                    logger.info(f"  [DRY RUN] Would delete directory: {item}")
                else:
                    import shutil
                    shutil.rmtree(item)
                    logger.info(f"  ✓ Deleted directory: {item}")
                deleted += 1

    if deleted == 0:
        logger.info("  No temporary files to clean")

    return deleted


def main():
    parser = argparse.ArgumentParser(
        description='Cleanup utility for Indian Stock Fund application'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Delete logs older than this many days (default: 7)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--aggressive',
        action='store_true',
        help='More aggressive cleanup (includes temp files)'
    )
    parser.add_argument(
        '--cache-only',
        action='store_true',
        help='Only clean cache, skip logs and temp files'
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("Starting cleanup...")
    logger.info("="*60)

    total_cleaned = 0

    if args.cache_only:
        # Only clean cache
        total_cleaned += cleanup_cache(dry_run=args.dry_run)
    else:
        # Clean logs
        total_cleaned += cleanup_logs(days=args.days, dry_run=args.dry_run)

        # Clean cache
        total_cleaned += cleanup_cache(dry_run=args.dry_run)

        # Clean temp files (if aggressive)
        if args.aggressive:
            total_cleaned += cleanup_temp_files(dry_run=args.dry_run)

    logger.info("="*60)
    if args.dry_run:
        logger.info(f"[DRY RUN] Would clean {total_cleaned} items")
    else:
        logger.info(f"✓ Cleanup completed: {total_cleaned} items cleaned")
    logger.info("="*60)

    sys.exit(0)


if __name__ == '__main__':
    main()
