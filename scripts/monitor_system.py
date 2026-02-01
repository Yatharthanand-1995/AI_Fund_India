"""
System Monitoring Dashboard

Real-time display of:
- API metrics
- Error rates
- Response times
- Cache performance
- System health

Usage:
    python scripts/monitor_system.py
"""

import requests
import time
import os
from datetime import datetime
from typing import Dict, Any


API_URL = os.getenv('API_URL', 'http://localhost:8000')
REFRESH_INTERVAL = 5  # seconds


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_number(num: float, decimals: int = 2) -> str:
    """Format number with commas"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    else:
        return f"{num:.{decimals}f}"


def get_health() -> Dict[str, Any]:
    """Get system health"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.json()
    except Exception as e:
        return {'status': 'unreachable', 'error': str(e)}


def get_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=5)
        return response.json()
    except Exception as e:
        return {}


def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary"""
    try:
        response = requests.get(f"{API_URL}/metrics/summary", timeout=5)
        return response.json()
    except Exception as e:
        return {}


def display_dashboard():
    """Display monitoring dashboard"""
    while True:
        try:
            clear_screen()

            # Header
            print("="*80)
            print(" AI Hedge Fund - System Monitoring Dashboard".center(80))
            print("="*80)
            print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
            print("="*80)

            # Get data
            health = get_health()
            metrics = get_metrics()
            summary = get_metrics_summary()

            # System Health
            print("\n┌─ SYSTEM HEALTH " + "─"*62 + "┐")
            status = health.get('status', 'unknown')
            status_icon = "✓" if status == 'healthy' else "✗"
            print(f"│ Status: {status_icon} {status.upper():<71}│")

            if 'components' in health:
                for component, info in health['components'].items():
                    comp_status = info.get('status', 'unknown')
                    comp_icon = "✓" if comp_status == 'healthy' else "✗"
                    print(f"│   {comp_icon} {component:<73}│")

            print("└" + "─"*78 + "┘")

            # Key Metrics
            if summary:
                print("\n┌─ KEY METRICS " + "─"*64 + "┐")
                uptime_hours = summary.get('uptime_seconds', 0) / 3600
                print(f"│ Uptime: {uptime_hours:.1f}h{'':<66}│")
                print(f"│ Total Requests: {summary.get('total_requests', 0):<61}│")
                print(f"│ Total Errors: {summary.get('total_errors', 0):<63}│")
                print(f"│ Error Rate: {summary.get('error_rate', 0):.2f}%{'':<62}│")
                print(f"│ Avg Response Time: {summary.get('avg_response_time_ms', 0):.2f}ms{'':<54}│")
                print(f"│ Cache Hit Rate: {summary.get('cache_hit_rate', 0):.2f}%{'':<57}│")
                print("└" + "─"*78 + "┘")

            # Response Times
            if 'timings' in metrics and 'api.response_time' in metrics['timings']:
                timing = metrics['timings']['api.response_time']
                print("\n┌─ RESPONSE TIMES (ms) " + "─"*55 + "┐")
                print(f"│ Count: {timing.get('count', 0):<70}│")
                print(f"│ Avg: {timing.get('avg_ms', 0):.2f}ms{'':<67}│")
                print(f"│ Min: {timing.get('min_ms', 0):.2f}ms{'':<67}│")
                print(f"│ Max: {timing.get('max_ms', 0):.2f}ms{'':<67}│")
                print(f"│ P50: {timing.get('p50_ms', 0):.2f}ms{'':<67}│")
                print(f"│ P95: {timing.get('p95_ms', 0):.2f}ms{'':<67}│")
                print(f"│ P99: {timing.get('p99_ms', 0):.2f}ms{'':<67}│")
                print("└" + "─"*78 + "┘")

            # Counters
            if 'counters' in metrics and metrics['counters']:
                print("\n┌─ REQUEST COUNTERS " + "─"*59 + "┐")
                for counter, value in sorted(metrics['counters'].items())[:10]:
                    if value > 0:
                        print(f"│ {counter:<50} {value:>25}│")
                print("└" + "─"*78 + "┘")

            # Errors
            if 'errors' in metrics and metrics['errors']:
                print("\n┌─ ERRORS " + "─"*69 + "┐")
                for error, count in sorted(metrics['errors'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"│ {error:<50} {count:>25}│")
                print("└" + "─"*78 + "┘")

            # Agent Performance
            agent_timings = {k: v for k, v in metrics.get('timings', {}).items() if k.startswith('agent.')}
            if agent_timings:
                print("\n┌─ AGENT PERFORMANCE (ms) " + "─"*52 + "┐")
                for agent, timing in sorted(agent_timings.items())[:5]:
                    agent_name = agent.replace('agent.', '').replace('.duration', '')
                    print(f"│ {agent_name:<30} avg: {timing.get('avg_ms', 0):>6.2f}ms  count: {timing.get('count', 0):>6}│")
                print("└" + "─"*78 + "┘")

            # Footer
            print("\n" + "─"*80)
            print(f" Press Ctrl+C to exit | Refresh: {REFRESH_INTERVAL}s | API: {API_URL}".center(80))
            print("─"*80)

            # Wait before refresh
            time.sleep(REFRESH_INTERVAL)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"\n\nError: {e}")
            time.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    print("Starting monitoring dashboard...")
    print(f"Connecting to: {API_URL}")
    print("Press Ctrl+C to exit\n")

    time.sleep(2)
    display_dashboard()
