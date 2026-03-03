"""
Summarizer v3 — uses pre-digested email data and memory context
for a more comprehensive and contextually aware briefing.
"""

import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a personal chief of staff writing a weekly briefing.
Be matter-of-fact and concise. No fluff, no cheerleading, no filler phrases.
State facts and insights directly. If something needs attention, say so plainly.
Use the accumulated context from previous weeks to add depth — reference history where relevant.
You always respond with valid JSON in the exact schema provided."""


def generate_briefing(
    email_digest: dict,
    past_events: list[dict],
    upcoming_events: list[dict],
    docs: list[dict],
    meeting_notes: list[dict],
    last_week_summary: str,
    memory_context: str,
    user_name: str = "there",
) -> dict:

    # Trim calendar data
    past_events = past_events[:30]
    upcoming_events = upcoming_events[:14]
    meeting_notes = meeting_notes[:10]

    # Count stats
    email_count = sum(p.get("interaction_count", 1) for p in email_digest.get("people_contacted", []))
    meeting_count = len(past_events)

    # Filter upcoming to Mon-Wed only (next 3 days from Friday = Mon/Tue/Wed)
    week_ahead = [e for e in upcoming_events if e.get("title", "").strip()][:10]

    data_payload = {
        "email_digest": email_digest,
        "past_calendar_events": past_events,
        "week_ahead_events": week_ahead,
        "google_docs": docs,
        "granola_meeting_notes": meeting_notes,
        "last_weeks_summary": last_week_summary,
        "stats": {
            "email_count": email_count,
            "meeting_count": meeting_count,
        }
    }

    memory_section = f"\n{memory_context}\n" if memory_context else ""

    user_prompt = f"""Here is {user_name}'s activity data for the past 7 days.
{memory_section}
{json.dumps(data_payload, indent=2, default=str)}

Generate a weekly briefing. Tone: direct, matter-of-fact, specific. No filler.
Respond ONLY with JSON in this exact schema:

{{
  "recap": {{
    "email_count": {email_count},
    "meeting_count": {meeting_count},
    "frequent_contacts": [
      {{
        "name": "Name (Company)",
        "count": 2,
        "note": "One sentence on what the interactions were about"
      }}
    ],
    "notable_emails": [
      {{
        "from": "Sender name",
        "subject": "Subject",
        "why_notable": "One sentence"
      }}
    ],
    "key_learnings": [
      "A specific, concrete insight or thing learned this week"
    ]
  }},

  "missed_follow_ups": [
    {{
      "person": "Name or email",
      "what": "What was promised or implied",
      "direction": "you_to_them or them_to_you",
      "suggested_action": "Concrete next step"
    }}
  ],

  "follow_up_drafts": [
    {{
      "to_email": "email@example.com",
      "to_name": "Name",
      "subject": "Subject line",
      "body": "Email body. Brief and natural."
    }}
  ],

  "week_ahead": [
    {{
      "title": "Event title",
      "date": "Day and time",
      "type": "meeting|talk|travel|social|other",
      "highlight": true,
      "prep_note": "What to prepare or think about. Null if nothing specific."
    }}
  ],

  "open_loops_from_last_week": [
    "Plain status update on something flagged last week"
  ],

  "closing_thought": "One honest, specific observation to carry into next week"
}}

Rules:
- recap.frequent_contacts: only people contacted 2+ times, or once but significantly
- recap.notable_emails: max 3, genuinely interesting only
- recap.key_learnings: concrete and specific, skip if nothing real to say
- missed_follow_ups: be thorough — check commitments from the full week, not just recent
- follow_up_drafts: max 3, only for your missed follow-ups (you_to_them)
- week_ahead: include all events Mon-Wed, set highlight=true for talks, travel, key face-to-face meetings
- open_loops_from_last_week: omit entirely if last_weeks_summary is empty
- Use accumulated context to add depth — e.g. "third time speaking with X this month"
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)
