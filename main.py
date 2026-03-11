"""
main.py v4 — bi-weekly brief with email caching.

Sends Monday 9AM and Friday 12PM. Uses pre-cached email digests
so the send job is fast and has full coverage of the period.

Run order:
  1. Authenticate with Google
  2. Load cached email digest (built by cache_emails.py)
  3. Fetch any emails since last cache (gap-fill)
  4. Pull calendar, docs, Granola
  5. Load memory context
  6. Generate briefing with Claude
  7. Format and send HTML email
  8. Create Gmail drafts for follow-ups
  9. Update memory + vector store
  10. Clear email cache for next cycle
"""

import json
import os
import sys
import base64
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(__file__))

from src.auth import get_credentials
from src.gmail_client import get_emails, create_draft
from src.calendar_client import get_past_events, get_upcoming_events
from src.docs_client import get_recent_docs
from src.granola_client import get_meeting_notes
from src.email_digester import digest_emails, merge_digests
from src.summarizer import generate_briefing
from src.email_formatter import build_html_email, get_brief_label
from src.memory import (
    load_memory, save_memory, update_memory_from_week,
    get_memory_context, store_week_in_vector_db
)
from googleapiclient.discovery import build

LAST_SUMMARY_FILE = "last_week_summary.json"
CACHE_FILE = "email_cache.json"


def _is_monday() -> bool:
    return datetime.now().weekday() == 0


def _lookahead_days() -> int:
    """Days to look ahead for the 'week ahead' section.
    Monday brief → 4 days (Mon-Thu, next update is Friday)
    Friday brief → 4 days (Fri-Mon, next update is Monday)
    """
    return 4


def _lookback_days() -> int:
    """Days to look back for calendar/meetings.
    Monday brief → looks back over the weekend + Thurs/Fri (4 days since Friday update)
    Friday brief → looks back Mon-Fri (4 days since Monday update)
    """
    return 4


def load_email_cache() -> dict:
    """Load the pre-built email digest cache."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"digests": [], "total_emails_processed": 0, "last_cached": None}


def clear_email_cache() -> None:
    """Reset the cache for the next cycle."""
    cache = {
        "digests": [],
        "total_emails_processed": 0,
        "last_cached": None,
        "cache_started": None,
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def load_last_summary() -> str:
    if os.path.exists(LAST_SUMMARY_FILE):
        with open(LAST_SUMMARY_FILE) as f:
            data = json.load(f)
            return data.get("summary", "")
    return ""


def save_this_summary(briefing: dict) -> None:
    summary = {
        "date": datetime.now().isoformat(),
        "is_monday": _is_monday(),
        "summary": json.dumps({
            "glance": briefing.get("glance", {}),
            "key_learnings": briefing.get("key_learnings", []),
            "missed_follow_ups": briefing.get("missed_follow_ups", []),
            "final_thought": briefing.get("final_thought", ""),
        }),
    }
    with open(LAST_SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)


def send_email(creds, to: str, subject: str, html_body: str) -> None:
    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"✅ Brief sent to {to}")


def create_follow_up_drafts(creds, follow_up_drafts: list[dict]) -> None:
    if not follow_up_drafts:
        return
    for draft in follow_up_drafts:
        try:
            create_draft(
                creds=creds,
                to=draft.get("to_email", ""),
                subject=draft.get("subject", ""),
                body=draft.get("body", ""),
            )
            print(f"   📝 Draft: {draft.get('subject')} → {draft.get('to_name')}")
        except Exception as e:
            print(f"   ⚠️  Draft failed for {draft.get('to_name')}: {e}")


def main():
    day_name = "Monday" if _is_monday() else "Friday"
    print(f"🚀 Starting {day_name} brief generation...")

    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    user_name = os.environ.get("USER_NAME", "there")
    if not recipient_email:
        raise EnvironmentError("RECIPIENT_EMAIL not set.")

    # ── Authenticate ──────────────────────────────────────────────────────
    print("🔐 Authenticating with Google...")
    creds = get_credentials()

    # ── Load cached email digest ──────────────────────────────────────────
    print("📧 Loading email cache...")
    cache = load_email_cache()
    cached_digests = cache.get("digests", [])
    print(f"   {len(cached_digests)} cached digest(s), {cache.get('total_emails_processed', 0)} emails pre-processed")

    # Gap-fill: fetch any emails since last cache
    gap_emails = []
    if cache.get("last_cached"):
        last_cached = datetime.fromisoformat(cache["last_cached"])
        hours_since = (datetime.now(timezone.utc) - last_cached).total_seconds() / 3600
        if hours_since > 6:  # Only gap-fill if cache is >6 hours old
            gap_days = max(1, int(hours_since / 24) + 1)
            gap_days = min(gap_days, 3)
            print(f"   Gap-filling: fetching last {gap_days} day(s) of emails...")
            gap_emails = get_emails(creds, days=gap_days)
            print(f"   Found {len(gap_emails)} gap-fill emails")
    else:
        # No cache at all — fetch the full lookback period
        print("   No cache found — fetching full period...")
        gap_emails = get_emails(creds, days=_lookback_days())
        print(f"   Found {len(gap_emails)} emails")

    # Digest gap emails and merge with cache
    if gap_emails:
        print("   Digesting gap-fill emails...")
        gap_digest = digest_emails(gap_emails)
        cached_digests.append(gap_digest)

    # Merge all digests into one
    email_digest = merge_digests(cached_digests) if cached_digests else {
        "people_contacted": [],
        "commitments_made": [],
        "notable_emails": [],
        "topics_mentioned": [],
    }

    total_emails = cache.get("total_emails_processed", 0) + len(gap_emails)
    print(f"   Combined digest: {len(email_digest.get('people_contacted', []))} people, {total_emails} emails total")

    # ── Calendar ──────────────────────────────────────────────────────────
    print("📅 Fetching calendar events...")
    past_events = get_past_events(creds, days=_lookback_days())
    upcoming_events = get_upcoming_events(creds, days=_lookahead_days())
    print(f"   {len(past_events)} past, {len(upcoming_events)} upcoming (next {_lookahead_days()} days)")

    # ── Docs ──────────────────────────────────────────────────────────────
    print("📄 Fetching Google Docs...")
    docs = get_recent_docs(creds, days=_lookback_days())
    print(f"   Found {len(docs)} recent documents")

    # ── Granola ───────────────────────────────────────────────────────────
    print("🎙️  Fetching Granola meeting notes...")
    meeting_notes = get_meeting_notes(days=_lookback_days())
    print(f"   Found {len(meeting_notes)} meeting notes")

    # ── Memory ────────────────────────────────────────────────────────────
    print("🧠 Loading memory context...")
    memory = load_memory()
    memory_context = get_memory_context(memory)

    # ── Last summary ──────────────────────────────────────────────────────
    last_summary = load_last_summary()

    # ── Generate briefing ─────────────────────────────────────────────────
    print("✍️  Generating briefing with Claude...")
    briefing = generate_briefing(
        email_digest=email_digest,
        past_events=past_events,
        upcoming_events=upcoming_events,
        docs=docs,
        meeting_notes=meeting_notes,
        last_summary=last_summary,
        memory_context=memory_context,
        user_name=user_name,
        is_monday=_is_monday(),
        lookahead_days=_lookahead_days(),
    )
    print("   Briefing generated ✅")

    # ── Format and send ───────────────────────────────────────────────────
    label = get_brief_label()
    html_body = build_html_email(briefing, label, is_monday=_is_monday())
    subject = f"Brief — {datetime.now().strftime('%A %B %d')}"
    print("📬 Sending email...")
    send_email(creds, to=recipient_email, subject=subject, html_body=html_body)

    # ── Follow-up drafts ──────────────────────────────────────────────────
    print("📝 Creating follow-up drafts...")
    create_follow_up_drafts(creds, briefing.get("follow_up_drafts", []))

    # ── Update memory ─────────────────────────────────────────────────────
    print("💾 Updating memory...")
    memory = update_memory_from_week(memory, email_digest, briefing, meeting_notes)
    save_memory(memory)

    # ── Vector DB ─────────────────────────────────────────────────────────
    print("🗄️  Storing in vector DB...")
    store_week_in_vector_db(email_digest, briefing, past_events, meeting_notes)

    # ── Save summary + clear cache ────────────────────────────────────────
    save_this_summary(briefing)
    clear_email_cache()
    print("   Cache cleared for next cycle")

    print(f"\n✅ Done. {day_name} brief is in your inbox.")


if __name__ == "__main__":
    main()
