"""
Gmail client — fetches emails from the last 7 days, filters out noise,
and returns real human conversations.
"""

import base64
import re
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# Labels / senders that indicate automated/newsletter emails — add your own
NOISE_PATTERNS = [
    r"noreply", r"no-reply", r"donotreply", r"notifications?@",
    r"newsletter", r"marketing", r"updates?@", r"alerts?@",
    r"support@", r"hello@", r"info@", r"team@",
]
NOISE_RE = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)


def _is_human(email_address: str) -> bool:
    """Returns True if the email address looks like a real person."""
    return not NOISE_RE.search(email_address)


def _decode_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text
    return ""


def get_emails(creds: Credentials, days: int = 7) -> list[dict]:
    """
    Returns a list of email dicts for real human conversations in the last `days` days.
    Each dict has: subject, from, to, date, body (truncated to 500 chars), thread_id.
    """
    service = build("gmail", "v1", credentials=creds)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    # Gmail query: after:<unix_timestamp>
    query = f"after:{int(since.timestamp())} -category:promotions -category:updates -category:forums"

    results = service.users().messages().list(
        userId="me", q=query, maxResults=200
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        sender = headers.get("From", "")
        _, sender_addr = parseaddr(sender)

        if not _is_human(sender_addr):
            continue  # Skip automated emails

        body = _decode_body(msg["payload"])

        emails.append({
            "id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "from": sender,
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body[:500],  # Truncate long emails
        })

    return emails


def create_draft(creds: Credentials, to: str, subject: str, body: str) -> dict:
    """
    Saves a draft email to Gmail Drafts. Returns the draft object.
    The user reviews and sends it manually — nothing is auto-sent.
    """
    service = build("gmail", "v1", credentials=creds)

    # Build a MIME message
    from email.mime.text import MIMEText
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()

    return draft
