#!/usr/bin/env python3
"""
System Health Check Utility

Verifies the health of various system components:
- Database connectivity
- Data providers (NSE, Yahoo)
- Cache system
- API endpoints
- File system permissions

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --verbose
    python scripts/health_check.py --check api --check database
"""

import argparse
import sys
from pathlib import Path
import logging
from typing import Tuple, List

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class HealthChecker:
    """System health checker"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks_passed = 0
        self.checks_failed = 0

    def check_database(self) -> Tuple[bool, str]:
        """Check database connectivity and integrity"""
        try:
            from data.historical_db import HistoricalDatabase

            db = HistoricalDatabase()
            regime = db.get_current_regime()

            if regime:
                return True, f"Database OK (current regime: {regime.get('regime', 'N/A')})"
            else:
                return True, "Database OK (no regime data yet)"

        except Exception as e:
            return False, f"Database error: {str(e)}"

    def check_nse_provider(self) -> Tuple[bool, str]:
        """Check NSE data provider"""
        try:
            from data.nse_provider import NSEProvider

            provider = NSEProvider()
            return True, "NSE provider initialized successfully"

        except ImportError as e:
            return False, f"NSEpy not available: {str(e)}"
        except Exception as e:
            return False, f"NSE provider error: {str(e)}"

    def check_yahoo_provider(self) -> Tuple[bool, str]:
        """Check Yahoo Finance data provider"""
        try:
            from data.yahoo_provider import YahooFinanceProvider

            provider = YahooFinanceProvider()
            return True, "Yahoo Finance provider initialized successfully"

        except ImportError as e:
            return False, f"yfinance not available: {str(e)}"
        except Exception as e:
            return False, f"Yahoo provider error: {str(e)}"

    def check_cache_system(self) -> Tuple[bool, str]:
        """Check cache system"""
        try:
            from core.cache_manager import get_cache_manager

            manager = get_cache_manager()
            test_cache = manager.get_cache('health_check_test')

            # Test set and get
            test_cache.set('test_key', 'test_value')
            value = test_cache.get('test_key')

            if value == 'test_value':
                stats = test_cache.stats()
                return True, f"Cache system OK (hit rate: {stats['hit_rate']}%)"
            else:
                return False, "Cache system failed basic test"

        except Exception as e:
            return False, f"Cache error: {str(e)}"

    def check_file_system(self) -> Tuple[bool, str]:
        """Check file system permissions"""
        critical_dirs = ['data', 'logs', 'scripts', 'core', 'agents']
        missing_dirs = []

        for dir_name in critical_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                missing_dirs.append(dir_name)

        if missing_dirs:
            return False, f"Missing directories: {', '.join(missing_dirs)}"

        # Check write permissions
        logs_dir = Path('logs')
        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True)
            except Exception as e:
                return False, f"Cannot create logs directory: {e}"

        try:
            test_file = logs_dir / '.health_check_test'
            test_file.write_text('test')
            test_file.unlink()
            return True, "File system permissions OK"
        except Exception as e:
            return False, f"File system write error: {e}"

    def check_dependencies(self) -> Tuple[bool, str]:
        """Check critical Python dependencies"""
        critical_packages = [
            'pandas',
            'numpy',
            'requests',
            'fastapi',
        ]

        optional_packages = [
            'nsepy',
            'yfinance',
            'talib',
        ]

        missing = []
        for package in critical_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)

        if missing:
            return False, f"Missing critical packages: {', '.join(missing)}"

        # Check optional packages
        missing_optional = []
        for package in optional_packages:
            try:
                __import__(package)
            except ImportError:
                missing_optional.append(package)

        if missing_optional:
            return True, f"All critical packages OK (optional missing: {', '.join(missing_optional)})"

        return True, "All dependencies OK"

    def check_api(self) -> Tuple[bool, str]:
        """Check if API server is running"""
        try:
            import requests
            response = requests.get('http://localhost:8000/health', timeout=5)

            if response.status_code == 200:
                return True, "API server is running and healthy"
            else:
                return False, f"API server returned status {response.status_code}"

        except requests.exceptions.ConnectionError:
            return False, "API server not running (connection refused)"
        except requests.exceptions.Timeout:
            return False, "API server timeout"
        except Exception as e:
            return False, f"API check failed: {str(e)}"

    def run_check(self, name: str, check_func) -> bool:
        """Run a single health check"""
        if self.verbose:
            logger.info(f"\nChecking {name}...")

        success, message = check_func()

        status = "✓" if success else "✗"
        logger.info(f"{status} {name}: {message}")

        if success:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return success

    def run_all_checks(self, selected_checks: List[str] = None) -> bool:
        """Run all health checks"""
        checks = {
            'dependencies': self.check_dependencies,
            'filesystem': self.check_file_system,
            'database': self.check_database,
            'nse': self.check_nse_provider,
            'yahoo': self.check_yahoo_provider,
            'cache': self.check_cache_system,
            'api': self.check_api,
        }

        logger.info("="*60)
        logger.info("System Health Check")
        logger.info("="*60)

        # Filter checks if specific ones requested
        if selected_checks:
            checks = {k: v for k, v in checks.items() if k in selected_checks}

        for name, check_func in checks.items():
            self.run_check(name, check_func)

        # Summary
        logger.info("="*60)
        total = self.checks_passed + self.checks_failed
        logger.info(f"Results: {self.checks_passed}/{total} checks passed")

        if self.checks_failed > 0:
            logger.error(f"{self.checks_failed} checks failed")
            logger.info("="*60)
            return False
        else:
            logger.info("✓ All checks passed - System is healthy")
            logger.info("="*60)
            return True


def main():
    parser = argparse.ArgumentParser(
        description='Health check utility for Indian Stock Fund application'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--check',
        action='append',
        choices=['dependencies', 'filesystem', 'database', 'nse', 'yahoo', 'cache', 'api'],
        help='Run specific checks only (can be specified multiple times)'
    )

    args = parser.parse_args()

    checker = HealthChecker(verbose=args.verbose)
    success = checker.run_all_checks(selected_checks=args.check)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
