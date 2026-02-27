"""
main.py — the entry point that orchestrates the whole weekly brief.

Run order:
  1. Authenticate with Google
  2. Pull data from all sources (Gmail, Calendar, Docs, Granola)
  3. Load last week's summary for continuity
  4. Send everything to Claude for summarisation
  5. Format as HTML email
  6. Send the email via Gmail
  7. Save this week's summary for next week's continuity
  8. Create Gmail Drafts for suggested follow-ups
"""

import json
import os
import sys
from datetime import datetime

# Adjust path so we can import from src/
sys.path.insert(0, os.path.dirname(__file__))

from src.auth import get_credentials
from src.gmail_client import get_emails, create_draft
from src.calendar_client import get_past_events, get_upcoming_events
from src.docs_client import get_recent_docs
from src.granola_client import get_meeting_notes
from src.summarizer import generate_briefing
from src.email_formatter import build_html_email, get_week_label

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build


LAST_WEEK_SUMMARY_FILE = "last_week_summary.json"


def load_last_week_summary() -> str:
    """Loads the previous week's summary text for continuity context."""
    if os.path.exists(LAST_WEEK_SUMMARY_FILE):
        with open(LAST_WEEK_SUMMARY_FILE) as f:
            data = json.load(f)
            return data.get("summary", "")
    return ""


def save_this_week_summary(briefing: dict) -> None:
    """Saves a condensed version of this week's briefing for next week."""
    # Store the key themes and open loops so next week can reference them
    summary = {
        "week_of": datetime.now().isoformat(),
        "summary": json.dumps({
            "week_headline": briefing.get("week_headline", ""),
            "key_themes": briefing.get("key_themes", []),
            "key_learnings": briefing.get("key_learnings", []),
            "missed_follow_ups": briefing.get("missed_follow_ups", []),
            "closing_thought": briefing.get("closing_thought", ""),
        }),
    }
    with open(LAST_WEEK_SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Saved this week's summary to {LAST_WEEK_SUMMARY_FILE}")


def send_email(creds, to: str, subject: str, html_body: str) -> None:
    """Sends the briefing email via Gmail API."""
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()
    print(f"✅ Weekly brief sent to {to}")


def create_follow_up_drafts(creds, follow_up_drafts: list[dict]) -> None:
    """Creates Gmail Drafts for each suggested follow-up email."""
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
            print(f"📝 Created draft: {draft.get('subject')} → {draft.get('to_name')}")
        except Exception as e:
            print(f"⚠️  Could not create draft for {draft.get('to_name')}: {e}")


def main():
    print("🚀 Starting weekly brief generation...")

    # ── Configuration ────────────────────────────────────────────────────
    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    user_name = os.environ.get("USER_NAME", "there")

    if not recipient_email:
        raise EnvironmentError("RECIPIENT_EMAIL environment variable is not set.")

    # ── Authenticate ─────────────────────────────────────────────────────
    print("🔐 Authenticating with Google...")
    creds = get_credentials()

    # ── Pull data ────────────────────────────────────────────────────────
    print("📧 Fetching emails...")
    emails = get_emails(creds, days=7)
    print(f"   Found {len(emails)} relevant emails")

    print("📅 Fetching calendar events...")
    past_events = get_past_events(creds, days=7)
    upcoming_events = get_upcoming_events(creds, days=7)
    print(f"   {len(past_events)} past events, {len(upcoming_events)} upcoming")

    print("📄 Fetching Google Docs...")
    docs = get_recent_docs(creds, days=7)
    print(f"   Found {len(docs)} recent documents")

    print("🎙️  Fetching Granola meeting notes...")
    meeting_notes = get_meeting_notes(days=7)
    print(f"   Found {len(meeting_notes)} meeting notes")

    # ── Load continuity ──────────────────────────────────────────────────
    print("🔄 Loading last week's summary for continuity...")
    last_week_summary = load_last_week_summary()

    # ── Generate briefing ────────────────────────────────────────────────
    print("🧠 Sending to Claude for summarisation...")
    briefing = generate_briefing(
        emails=emails,
        past_events=past_events,
        upcoming_events=upcoming_events,
        docs=docs,
        meeting_notes=meeting_notes,
        last_week_summary=last_week_summary,
        user_name=user_name,
    )
    print("   Briefing generated ✅")

    # ── Format email ─────────────────────────────────────────────────────
    week_label = get_week_label()
    html_body = build_html_email(briefing, week_label)

    # ── Send email ───────────────────────────────────────────────────────
    print("📬 Sending email...")
    subject = f"Weekly Brief — {datetime.now().strftime('%B %d')}"
    send_email(creds, to=recipient_email, subject=subject, html_body=html_body)

    # ── Create follow-up drafts ──────────────────────────────────────────
    print("📝 Creating follow-up drafts in Gmail...")
    create_follow_up_drafts(creds, briefing.get("follow_up_drafts", []))

    # ── Save for next week ───────────────────────────────────────────────
    save_this_week_summary(briefing)

    print("\n✅ All done! Your weekly brief is in your inbox.")


if __name__ == "__main__":
    main()
