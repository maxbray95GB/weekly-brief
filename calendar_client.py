"""
Google Calendar client — fetches events from the last 7 days
and the next 7 days (for the week-ahead preview).
"""

from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _format_event(event: dict) -> dict:
    """Normalise a raw Calendar event into a simple dict."""
    start = event.get("start", {})
    end = event.get("end", {})

    # Events can be all-day (date) or timed (dateTime)
    start_str = start.get("dateTime") or start.get("date", "")
    end_str = end.get("dateTime") or end.get("date", "")

    attendees = [
        a.get("email", "") for a in event.get("attendees", [])
        if not a.get("self")  # Exclude the user themselves
    ]

    return {
        "id": event.get("id", ""),
        "title": event.get("summary", "(no title)"),
        "start": start_str,
        "end": end_str,
        "attendees": attendees,
        "description": (event.get("description") or "")[:300],
        "location": event.get("location", ""),
        "status": event.get("status", "confirmed"),
        "organizer": event.get("organizer", {}).get("email", ""),
    }


def get_past_events(creds: Credentials, days: int = 7) -> list[dict]:
    """Returns calendar events from the last `days` days."""
    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=since.isoformat(),
        timeMax=now.isoformat(),
        maxResults=100,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return [_format_event(e) for e in events_result.get("items", [])]


def get_upcoming_events(creds: Credentials, days: int = 7) -> list[dict]:
    """Returns calendar events for the next `days` days (week-ahead preview)."""
    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=until.isoformat(),
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return [_format_event(e) for e in events_result.get("items", [])]
