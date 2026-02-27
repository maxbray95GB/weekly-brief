"""
Summarizer — feeds all the week's data to Claude and gets back
a structured weekly briefing with follow-up drafts.
"""

import json
import os

import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a personal chief of staff. Every Friday morning, you write a 
crisp, insightful weekly briefing for your principal based on their actual activity data.

Your tone is warm but professional — like a trusted colleague who knows you well. 
You surface what matters, not just what happened. You write in clear prose (not just bullet dumps).
You are honest about gaps and missed follow-ups without being harsh.

You always respond with valid JSON in the exact schema provided."""


def generate_briefing(
    emails: list[dict],
    past_events: list[dict],
    upcoming_events: list[dict],
    docs: list[dict],
    meeting_notes: list[dict],
    last_week_summary: str,
    user_name: str = "there",
) -> dict:

    # Trim data to avoid overwhelming Claude
    emails = emails[:30]
    for e in emails:
        e["body"] = e.get("body", "")[:150]
        e.pop("snippet", None)

    past_events = past_events[:20]
    upcoming_events = upcoming_events[:10]
    meeting_notes = meeting_notes[:10]

    data_payload = {
        "emails": emails,
        "past_calendar_events": past_events,
        "upcoming_calendar_events": upcoming_events,
        "google_docs": docs,
        "granola_meeting_notes": meeting_notes,
        "last_weeks_summary": last_week_summary,
    }

    user_prompt = f"""Here is {user_name}'s activity data for the past 7 days.

{json.dumps(data_payload, indent=2, default=str)}

Based on this, generate a weekly briefing. Respond ONLY with JSON in this exact schema:

{{
  "week_headline": "A single punchy sentence capturing the character of this week",
  "key_themes": ["theme 1", "theme 2", "theme 3"],
  "people_spoke_to": [
    {{
      "name": "Full name or email",
      "context": "What you discussed / relationship",
      "follow_up_needed": true
    }}
  ],
  "key_learnings": [
    "Learning or insight 1 (written as a full sentence)"
  ],
  "missed_follow_ups": [
    {{
      "person": "Name or email",
      "what": "What was supposed to happen",
      "suggested_action": "Concrete next step"
    }}
  ],
  "follow_up_drafts": [
    {{
      "to_email": "email@example.com",
      "to_name": "Person's name",
      "subject": "Email subject line",
      "body": "Full email body text."
    }}
  ],
  "docs_created_or_edited": [
    {{
      "title": "Doc title",
      "url": "URL if available",
      "significance": "Why this matters"
    }}
  ],
  "open_loops_from_last_week": [
    "Was last week's item X addressed?"
  ],
  "week_ahead_preview": [
    {{
      "title": "Event title",
      "date": "Day and time",
      "prep_note": "One-line note on what to prepare"
    }}
  ],
  "closing_thought": "A single thoughtful observation to carry into next week"
}}

Rules:
- Only include sections where there is real data
- follow_up_drafts: max 3 drafts, only for genuine missed follow-ups
- open_loops_from_last_week: omit if last_weeks_summary is empty
- Be specific — use real names and real topics
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
