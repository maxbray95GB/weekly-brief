"""
main.py v3 — updated pipeline with email digesting, memory, and vector store.

Run order:
  1. Authenticate with Google
  2. Pull raw data (Gmail, Calendar, Docs, Granola)
  3. Pre-digest all emails in batches (full week coverage)
  4. Load memory context (accumulated from previous weeks)
  5. Generate briefing with Claude (using digest + memory)
  6. Format and send HTML email
  7. Create Gmail drafts for follow-ups
  8. Update memory.json and Supabase vector store
  9. Save last_week_summary for next week
"""

import json
import os
import sys
import base64
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(__file__))

from src.auth import get_credentials
from src.gmail_client import get_emails, create_draft
from src.calendar_client import get_past_events, get_upcoming_events
from src.docs_client import get_recent_docs
from src.granola_client import get_meeting_notes
from src.email_digester import digest_emails
from src.summarizer import generate_briefing
from src.email_formatter import build_html_email, get_week_label
from src.memory import (
    load_memory, save_memory, update_memory_from_week,
    get_memory_context, store_week_in_vector_db
)
from googleapiclient.discovery import build

LAST_WEEK_SUMMARY_FILE = "last_week_summary.json"


def load_last_week_summary() -> str:
    if os.path.exists(LAST_WEEK_SUMMARY_FILE):
        with open(LAST_WEEK_SUMMARY_FILE) as f:
            data = json.load(f)
            return data.get("summary", "")
    return ""


def save_this_week_summary(briefing: dict) -> None:
    summary = {
        "week_of": datetime.now().isoformat(),
        "summary": json.dumps({
            "recap_learnings": briefing.get("recap", {}).get("key_learnings", []),
            "missed_follow_ups": briefing.get("missed_follow_ups", []),
            "closing_thought": briefing.get("closing_thought", ""),
        }),
    }
    with open(LAST_WEEK_SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    print("✅ Saved last_week_summary.json")


def send_email(creds, to: str, subject: str, html_body: str) -> None:
    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"✅ Weekly brief sent to {to}")


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
            print(f"📝 Draft created: {draft.get('subject')} → {draft.get('to_name')}")
        except Exception as e:
            print(f"⚠️  Could not create draft for {draft.get('to_name')}: {e}")


def main():
    print("🚀 Starting weekly brief generation...")

    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    user_name = os.environ.get("USER_NAME", "there")
    if not recipient_email:
        raise EnvironmentError("RECIPIENT_EMAIL not set.")

    # ── Authenticate ──────────────────────────────────────────────────────
    print("🔐 Authenticating with Google...")
    creds = get_credentials()

    # ── Pull raw data ─────────────────────────────────────────────────────
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

    # ── Digest all emails ─────────────────────────────────────────────────
    print("🔍 Digesting full week of emails...")
    email_digest = digest_emails(emails)
    print(f"   Digest complete — {len(email_digest.get('people_contacted', []))} people, {len(email_digest.get('commitments_made', []))} commitments found")

    # ── Load memory ───────────────────────────────────────────────────────
    print("🧠 Loading accumulated memory context...")
    memory = load_memory()
    memory_context = get_memory_context(memory)
    if memory_context:
        print("   Memory context loaded ✅")
    else:
        print("   No prior memory yet (first run)")

    # ── Load last week ────────────────────────────────────────────────────
    last_week_summary = load_last_week_summary()

    # ── Generate briefing ─────────────────────────────────────────────────
    print("✍️  Generating briefing with Claude...")
    briefing = generate_briefing(
        email_digest=email_digest,
        past_events=past_events,
        upcoming_events=upcoming_events,
        docs=docs,
        meeting_notes=meeting_notes,
        last_week_summary=last_week_summary,
        memory_context=memory_context,
        user_name=user_name,
    )
    print("   Briefing generated ✅")

    # ── Format and send email ─────────────────────────────────────────────
    week_label = get_week_label()
    html_body = build_html_email(briefing, week_label)
    subject = f"Weekly Brief — {datetime.now().strftime('%B %d')}"
    print("📬 Sending email...")
    send_email(creds, to=recipient_email, subject=subject, html_body=html_body)

    # ── Create follow-up drafts ───────────────────────────────────────────
    print("📝 Creating follow-up drafts...")
    create_follow_up_drafts(creds, briefing.get("follow_up_drafts", []))

    # ── Update memory ─────────────────────────────────────────────────────
    print("💾 Updating memory...")
    memory = update_memory_from_week(memory, email_digest, briefing, meeting_notes)
    save_memory(memory)

    # ── Store in vector DB (Tier 2) ───────────────────────────────────────
    print("🗄️  Storing week in vector DB...")
    store_week_in_vector_db(email_digest, briefing, past_events, meeting_notes)

    # ── Save for next week ────────────────────────────────────────────────
    save_this_week_summary(briefing)

    print("\n✅ Done. Brief is in your inbox.")


if __name__ == "__main__":
    main()
