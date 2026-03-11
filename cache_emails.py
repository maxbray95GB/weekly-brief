"""
cache_emails.py — runs every 2 days via GitHub Actions.

Fetches emails since the last cache run, digests them, and appends
the digest to email_cache.json. This means the send job on Mon/Fri
has a pre-built picture of the whole period without re-fetching everything.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from src.auth import get_credentials
from src.gmail_client import get_emails
from src.email_digester import digest_emails

CACHE_FILE = "email_cache.json"


def load_cache() -> dict:
    """Load existing cache or create empty structure."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {
        "digests": [],
        "total_emails_processed": 0,
        "last_cached": None,
        "cache_started": None,
    }


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def main():
    print("📧 Starting email cache run...")

    cache = load_cache()

    # Work out how far back to fetch:
    # If we have a last_cached timestamp, fetch from then.
    # Otherwise fetch the last 3 days (first run of a cycle).
    if cache["last_cached"]:
        last = datetime.fromisoformat(cache["last_cached"])
        days_since = (datetime.now(timezone.utc) - last).days + 1  # +1 for overlap
        days_since = max(days_since, 1)
        days_since = min(days_since, 7)  # Never go back more than 7
    else:
        days_since = 3  # First run of a new cycle
        cache["cache_started"] = datetime.now(timezone.utc).isoformat()

    print(f"   Fetching emails from last {days_since} days...")

    # Authenticate and fetch
    creds = get_credentials()
    emails = get_emails(creds, days=days_since)
    print(f"   Found {len(emails)} emails")

    if not emails:
        print("   No new emails to digest. Done.")
        cache["last_cached"] = datetime.now(timezone.utc).isoformat()
        save_cache(cache)
        return

    # Digest this batch
    print("   Digesting...")
    digest = digest_emails(emails)

    # Tag the digest with its time window
    digest["cached_at"] = datetime.now(timezone.utc).isoformat()
    digest["days_covered"] = days_since
    digest["email_count"] = len(emails)

    # Append to cache
    cache["digests"].append(digest)
    cache["total_emails_processed"] += len(emails)
    cache["last_cached"] = datetime.now(timezone.utc).isoformat()

    save_cache(cache)
    print(f"   ✅ Cache updated — {cache['total_emails_processed']} total emails processed across {len(cache['digests'])} cache runs")


if __name__ == "__main__":
    main()
