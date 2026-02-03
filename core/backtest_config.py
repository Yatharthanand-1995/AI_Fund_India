"""
Backtest Configuration Manager

Provides reusable backtest configurations for easy re-running.
Configurations are stored in the metadata field of backtest_runs table.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


@dataclass
class BacktestConfig:
    """Reusable backtest configuration"""
    name: str
    symbols: Optional[List[str]]  # None = use default NIFTY 50
    start_date: datetime
    end_date: datetime
    frequency: str  # 'daily', 'weekly', 'monthly', 'quarterly'
    benchmark: str = '^NSEI'

    # Future: Advanced options
    # thresholds: Optional[Dict] = None
    # agent_weights: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Serialize to dict for storage"""
        return {
            'name': self.name,
            'symbols': self.symbols,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'frequency': self.frequency,
            'benchmark': self.benchmark
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BacktestConfig':
        """Deserialize from dict"""
        return cls(
            name=data['name'],
            symbols=data.get('symbols'),  # Can be None
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            frequency=data['frequency'],
            benchmark=data.get('benchmark', '^NSEI')
        )

    def update_dates_to_present(self) -> 'BacktestConfig':
        """
        Update dates to present while maintaining the same duration

        Example:
            Original: 2020-01-01 to 2025-01-01 (5 years)
            Updated:  2021-02-03 to 2026-02-03 (5 years, ending today)

        Returns:
            New BacktestConfig with updated dates
        """
        duration = self.end_date - self.start_date
        new_end_date = datetime.now()
        new_start_date = new_end_date - duration

        return BacktestConfig(
            name=f"{self.name} (Updated)",
            symbols=self.symbols,
            start_date=new_start_date,
            end_date=new_end_date,
            frequency=self.frequency,
            benchmark=self.benchmark
        )

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'BacktestConfig':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> bool:
        """Validate configuration"""
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")

        if self.frequency not in ['daily', 'weekly', 'monthly', 'quarterly']:
            raise ValueError(f"Invalid frequency: {self.frequency}")

        if self.symbols is not None and len(self.symbols) == 0:
            raise ValueError("Symbols list cannot be empty")

        return True


def create_default_config(
    name: Optional[str] = None,
    years: int = 5,
    frequency: str = 'monthly'
) -> BacktestConfig:
    """
    Create a default backtest configuration

    Args:
        name: Configuration name (default: auto-generated)
        years: Number of years to backtest (default: 5)
        frequency: Rebalancing frequency (default: monthly)

    Returns:
        BacktestConfig with sensible defaults
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    if name is None:
        name = f"NIFTY 50 {years}Y Backtest"

    return BacktestConfig(
        name=name,
        symbols=None,  # None = use default NIFTY 50
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        benchmark='^NSEI'
    )
