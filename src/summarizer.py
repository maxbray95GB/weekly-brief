"""
Summarizer v4 — bi-weekly briefing with 6-section structure.

Sections:
  1. The week at a glance (stats + standouts)
  2. Key learnings and insights
  3. Week ahead (next 4 days until next update)
  4. Who you spoke to
  5. Documents
  6. Final thought
"""

import json
import os
import time
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MAX_RETRIES = 3
RETRY_WAIT = 65  # seconds — enough to reset the 10k tokens/min window

SYSTEM_PROMPT = """You are a personal chief of staff writing a brief.
Be matter-of-fact and concise. No fluff, no cheerleading, no filler phrases.
State facts and insights directly. If something needs attention, say so plainly.
Use accumulated context from previous weeks to add depth where relevant.
You always respond with valid JSON in the exact schema provided."""


def generate_briefing(
    email_digest: dict,
    past_events: list[dict],
    upcoming_events: list[dict],
    docs: list[dict],
    meeting_notes: list[dict],
    last_summary: str,
    memory_context: str,
    user_name: str = "there",
    is_monday: bool = False,
    lookahead_days: int = 4,
) -> dict:

    past_events = past_events[:30]
    upcoming_events = upcoming_events[:20]
    meeting_notes = meeting_notes[:10]
    docs = docs[:10]

    email_count = sum(
        p.get("interaction_count", 1)
        for p in email_digest.get("people_contacted", [])
    )
    meeting_count = len(past_events)
    day_label = "Monday" if is_monday else "Friday"
    next_update = "Friday" if is_monday else "Monday"

    data_payload = {
        "email_digest": email_digest,
        "past_calendar_events": past_events,
        "upcoming_events": upcoming_events,
        "google_docs": docs,
        "granola_meeting_notes": meeting_notes,
        "last_summary": last_summary,
        "stats": {
            "email_count": email_count,
            "meeting_count": meeting_count,
        },
    }

    memory_section = f"\n{memory_context}\n" if memory_context else ""

    user_prompt = f"""Here is {user_name}'s activity data for the period since the last update.
Today is {day_label}. The next update will be {next_update}.
{memory_section}
{json.dumps(data_payload, indent=2, default=str)}

Generate a brief with this EXACT JSON schema:

{{
  "glance": {{
    "email_count": {email_count},
    "meeting_count": {meeting_count},
    "standout_contacts": [
      {{
        "name": "Name (Company)",
        "count": 2,
        "note": "One-line on what the interactions covered"
      }}
    ],
    "momentum": "One sentence on where momentum seems to be building",
    "gap": "One thing that might have slipped through the cracks, or null"
  }},

  "key_learnings": [
    "A specific, concrete insight or thing learned this period"
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

  "people": [
    {{
      "name": "Name (Company)",
      "interaction_count": 2,
      "summary": "One sentence on what was discussed",
      "missed_follow_up": "What needs following up, or null"
    }}
  ],

  "documents": [
    {{
      "title": "Document title",
      "note": "What changed or why it matters",
      "url": "Link if available"
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

  "final_thought": "One honest, specific observation to carry forward"
}}

Rules:
- glance.standout_contacts: people contacted 2+ times or once but significantly. Max 5.
- glance.momentum: look across meetings, emails, and docs for where energy is concentrating
- glance.gap: flag if something seems to have been dropped. null if nothing obvious.
- key_learnings: concrete and specific. Skip if nothing real. Max 4.
- week_ahead: events for the next {lookahead_days} days (until {next_update}). Set highlight=true for important ones only.
- people: everyone you had real interactions with, sorted by interaction count. Include missed_follow_up only where genuine.
- documents: only include docs that were meaningfully worked on. Skip if none.
- follow_up_drafts: max 3, only for genuinely missed follow-ups where you owe someone a reply.
- final_thought: one sentence, direct, no platitudes.
- Use accumulated context to add depth — e.g. "third conversation with X this month".
"""

    for attempt in range(MAX_RETRIES + 1):
        try:
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
        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES:
                wait = RETRY_WAIT * (attempt + 1)
                print(f"   ⏳ Rate limited — waiting {wait}s before retry {attempt + 2}/{MAX_RETRIES + 1}...")
                time.sleep(wait)
            else:
                raise
