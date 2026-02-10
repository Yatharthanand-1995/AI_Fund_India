#!/usr/bin/env python3
"""
Database and Configuration Backup Utility

Creates timestamped backups of:
- SQLite database files
- Configuration files
- Log files (optional)
- Cache data (optional)

Usage:
    python scripts/backup.py --output ./backups
    python scripts/backup.py --output ./backups --include-logs
    python scripts/backup.py --output ./backups --compress
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
import tarfile
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_backup(
    output_dir: str,
    include_logs: bool = False,
    include_cache: bool = False,
    compress: bool = False
):
    """
    Create a backup of the application data.

    Args:
        output_dir: Directory to store backups
        include_logs: Include log files in backup
        include_cache: Include cache data in backup
        compress: Create a compressed tar.gz archive
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{timestamp}'
    backup_dir = Path(output_dir) / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_backed_up = 0

    try:
        # Backup database files
        logger.info("Backing up database files...")
        db_files = list(Path('data').glob('*.db'))
        for db_file in db_files:
            if db_file.exists():
                dest = backup_dir / 'data' / db_file.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(db_file, dest)
                logger.info(f"  ✓ Backed up: {db_file.name}")
                files_backed_up += 1

        # Backup configuration files
        logger.info("Backing up configuration files...")
        config_files = [
            '.env',
            '.env.example',
            'requirements.txt',
            'pytest.ini',
            'pyproject.toml',
        ]
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                dest = backup_dir / config_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_path, dest)
                logger.info(f"  ✓ Backed up: {config_file}")
                files_backed_up += 1

        # Backup frontend configuration
        frontend_configs = [
            'frontend/package.json',
            'frontend/package-lock.json',
            'frontend/vite.config.ts',
            'frontend/tsconfig.json',
        ]
        for config_file in frontend_configs:
            config_path = Path(config_file)
            if config_path.exists():
                dest = backup_dir / config_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_path, dest)
                logger.info(f"  ✓ Backed up: {config_file}")
                files_backed_up += 1

        # Backup logs (optional)
        if include_logs:
            logger.info("Backing up log files...")
            logs_dir = Path('logs')
            if logs_dir.exists():
                dest = backup_dir / 'logs'
                shutil.copytree(logs_dir, dest, ignore=shutil.ignore_patterns('*.tmp'))
                log_count = len(list(dest.glob('*.log*')))
                logger.info(f"  ✓ Backed up {log_count} log files")
                files_backed_up += log_count

        # Backup cache (optional)
        if include_cache:
            logger.info("Backing up cache data...")
            # Add cache backup logic here if needed

        # Create compressed archive
        if compress:
            logger.info("Creating compressed archive...")
            archive_path = Path(output_dir) / f'{backup_name}.tar.gz'
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(backup_dir, arcname=backup_name)

            # Remove uncompressed backup directory
            shutil.rmtree(backup_dir)

            logger.info(f"✓ Compressed backup created: {archive_path}")
            logger.info(f"  Size: {archive_path.stat().st_size / 1024 / 1024:.2f} MB")
            final_path = archive_path
        else:
            final_path = backup_dir

        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Backup completed successfully!")
        logger.info(f"  Location: {final_path}")
        logger.info(f"  Files backed up: {files_backed_up}")
        logger.info(f"{'='*60}")

        return True

    except Exception as e:
        logger.error(f"✗ Backup failed: {e}")
        # Clean up partial backup
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Backup utility for Indian Stock Fund application'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='./backups',
        help='Output directory for backups (default: ./backups)'
    )
    parser.add_argument(
        '--include-logs',
        action='store_true',
        help='Include log files in backup'
    )
    parser.add_argument(
        '--include-cache',
        action='store_true',
        help='Include cache data in backup'
    )
    parser.add_argument(
        '--compress',
        action='store_true',
        help='Create compressed tar.gz archive'
    )

    args = parser.parse_args()

    success = create_backup(
        output_dir=args.output,
        include_logs=args.include_logs,
        include_cache=args.include_cache,
        compress=args.compress
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
