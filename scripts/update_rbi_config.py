"""
RBI MPC Config Auto-Updater

Checks the RBI website for MPC decisions and updates data/rbi_rate_config.json.

Run manually after each MPC meeting, or schedule it via cron on MPC meeting dates.
RBI MPC meets 6 times/year (bi-monthly). The full schedule is published in April.

Usage:
  python3 scripts/update_rbi_config.py          # Check and show latest decision
  python3 scripts/update_rbi_config.py --apply  # Apply changes to config file

The script scrapes RBI's monetary policy page and parses the press release
for the repo rate decision. Falls back to prompting the user when parsing fails.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, date
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "data" / "rbi_rate_config.json"

# RBI monetary policy press releases index
_RBI_POLICY_URL = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
_RBI_SEARCH_URL = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplayNew.aspx"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return json.load(f)


def save_config(config: dict) -> None:
    # Remove stale warning if present
    config.pop("_stale_warning", None)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Config saved to {_CONFIG_PATH}")


def get_last_recorded_date(config: dict) -> date:
    history = config.get("decision_history", [])
    if not history:
        return date(2020, 1, 1)
    return datetime.strptime(history[0]["date"], "%Y-%m-%d").date()


def fetch_latest_press_release() -> str:
    """
    Attempt to fetch the latest RBI monetary policy press release text.
    Returns empty string on failure (caller handles gracefully).
    """
    try:
        # RBI publishes PDFs + HTML summaries — try the HTML index
        resp = requests.get(_RBI_POLICY_URL, headers=_HEADERS, timeout=15,
                            params={"PRID": "1"})
        return resp.text
    except Exception as e:
        logger.debug(f"RBI fetch failed: {e}")
        return ""


def parse_repo_rate(text: str) -> tuple[float | None, str | None]:
    """
    Parse repo rate and action from RBI press release text.
    Returns (rate_pct, action) or (None, None) if parsing fails.
    action: 'cut' | 'hike' | 'hold'
    """
    # Match patterns like "repo rate by 25 basis points to 5.75 per cent"
    rate_pattern = re.compile(
        r"repo rate.*?(\d+\.\d+)\s*(?:per cent|%)", re.IGNORECASE
    )
    action_pattern = re.compile(
        r"(reduce[sd]?|cut|lower[ed]?|increase[sd]?|hike[sd]?|raise[sd]?|unchanged|hold|status quo)",
        re.IGNORECASE
    )

    rate_match = rate_pattern.search(text)
    action_match = action_pattern.search(text)

    rate = float(rate_match.group(1)) if rate_match else None
    raw_action = action_match.group(1).lower() if action_match else None

    if raw_action:
        if any(w in raw_action for w in ['reduce', 'cut', 'lower']):
            action = 'cut'
        elif any(w in raw_action for w in ['increase', 'hike', 'raise']):
            action = 'hike'
        else:
            action = 'hold'
    else:
        action = None

    return rate, action


def prompt_user_for_decision(config: dict) -> dict | None:
    """
    Interactive fallback: ask the user to enter MPC decision details.
    Returns new decision dict or None if user skips.
    """
    print("\n--- Manual MPC Decision Entry ---")
    print(f"Current repo rate: {config['repo_rate']}%")
    print(f"Last recorded: {config.get('last_updated', 'unknown')}")
    print()

    date_str = input("MPC meeting date (YYYY-MM-DD): ").strip()
    try:
        meeting_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("Invalid date format.")
        return None

    if meeting_date <= get_last_recorded_date(config):
        print(f"Date {date_str} is not newer than last recorded decision. Skipping.")
        return None

    action = input("Decision (cut / hold / hike): ").strip().lower()
    if action not in ('cut', 'hold', 'hike'):
        print("Invalid action.")
        return None

    bps_str = input("Basis points changed (e.g. 25 for a cut, 0 for hold): ").strip()
    try:
        bps = int(bps_str)
    except ValueError:
        print("Invalid bps.")
        return None

    if action == 'cut':
        bps = -abs(bps)
    elif action == 'hike':
        bps = abs(bps)
    else:
        bps = 0

    current_rate = config['repo_rate']
    new_rate = round(current_rate + bps / 100, 2)
    new_rate_str = input(f"New repo rate (press Enter for {new_rate}%): ").strip()
    if new_rate_str:
        new_rate = float(new_rate_str)

    next_mpc = input("Next MPC date (YYYY-MM-DD, or Enter to skip): ").strip()

    return {
        'date': date_str,
        'action': action,
        'bps': bps,
        'rate': new_rate,
        '_next_mpc': next_mpc if next_mpc else None,
    }


def apply_decision(config: dict, decision: dict) -> dict:
    """Apply a new MPC decision to the config dict."""
    next_mpc = decision.pop('_next_mpc', None)
    config['decision_history'].insert(0, decision)
    config['repo_rate'] = decision['rate']
    config['last_updated'] = decision['date']
    if next_mpc:
        config['next_mpc_date'] = next_mpc
    return config


def check_if_update_needed(config: dict) -> bool:
    """Return True if the next_mpc_date has passed and isn't in history."""
    next_mpc_str = config.get('next_mpc_date')
    if not next_mpc_str:
        return False
    next_mpc = datetime.strptime(next_mpc_str, "%Y-%m-%d").date()
    last_recorded = get_last_recorded_date(config)
    return date.today() > next_mpc and last_recorded < next_mpc


def main():
    parser = argparse.ArgumentParser(description="RBI MPC Config Updater")
    parser.add_argument("--apply", action="store_true",
                        help="Write changes to rbi_rate_config.json")
    parser.add_argument("--check", action="store_true",
                        help="Just check if an update is needed (exit 1 if yes)")
    args = parser.parse_args()

    config = load_config()

    print(f"\nCurrent RBI config:")
    print(f"  Repo rate    : {config['repo_rate']}%")
    print(f"  Last updated : {config.get('last_updated')}")
    print(f"  Next MPC     : {config.get('next_mpc_date')}")
    print(f"  Cycle        : {config.get('decision_history', [{}])[0].get('action', '?')}")

    if not check_if_update_needed(config):
        print("\nConfig is up to date. No action needed.")
        sys.exit(0)

    print(f"\n⚠️  Next MPC date ({config.get('next_mpc_date')}) has passed but is not in history.")

    if args.check:
        print("Update required.")
        sys.exit(1)

    # Try auto-parse from RBI website
    print("\nAttempting to fetch latest RBI press release...")
    html = fetch_latest_press_release()
    rate, action = parse_repo_rate(html) if html else (None, None)

    if rate and action:
        print(f"Parsed from RBI website: action={action}, rate={rate}%")
    else:
        print("Could not auto-parse. Falling back to manual entry.")
        decision = prompt_user_for_decision(config)

    if rate and action:
        last_rate = config['repo_rate']
        bps = round((rate - last_rate) * 100)
        if action == 'hold':
            bps = 0
        decision = {
            'date': config['next_mpc_date'],
            'action': action,
            'bps': bps,
            'rate': rate,
            '_next_mpc': None,
        }
        next_mpc_input = input(f"Next MPC date after this (YYYY-MM-DD): ").strip()
        decision['_next_mpc'] = next_mpc_input if next_mpc_input else None

    if not decision:
        print("No decision entered. Exiting without changes.")
        sys.exit(0)

    config = apply_decision(config, decision)

    print(f"\nUpdated config preview:")
    print(f"  Repo rate    : {config['repo_rate']}%")
    print(f"  Last updated : {config['last_updated']}")
    print(f"  Next MPC     : {config.get('next_mpc_date', 'not set')}")

    if args.apply:
        save_config(config)
        print("✅ Config file updated.")
    else:
        print("\n(Dry run — use --apply to write changes)")


if __name__ == "__main__":
    main()
