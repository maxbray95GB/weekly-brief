"""
Summarizer — feeds all the week's data to Claude and gets back
a structured weekly briefing with follow-up drafts.
"""

import json
import os

import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a personal chief of staff writing a weekly briefing. 
Be matter-of-fact and concise. No fluff, no cheerleading, no filler phrases like 
"it's been a busy week" or "great progress". Just clear, useful observations.
State facts and insights directly. If something needs attention, say so plainly.
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

    # Count stats for the at-a-glance section
    meeting_count = len(past_events)
    email_count = len(emails)

    data_payload = {
        "emails": emails,
        "past_calendar_events": past_events,
        "upcoming_calendar_events": upcoming_events,
        "google_docs": docs,
        "granola_meeting_notes": meeting_notes,
        "last_weeks_summary": last_week_summary,
        "meeting_count": meeting_count,
        "email_count": email_count,
    }

    user_prompt = f"""Here is {user_name}'s activity data for the past 7 days.

{json.dumps(data_payload, indent=2, default=str)}

Generate a weekly briefing. Tone: direct, matter-of-fact, no filler. 
Respond ONLY with JSON in this exact schema:

{{
  "at_a_glance": {{
    "meetings": {meeting_count},
    "emails": {email_count},
    "most_contacted": "Name or company you interacted with most",
    "momentum": "One sentence on where energy/progress seems to be building",
    "watch_out": "One thing that might have slipped or needs attention"
  }},

  "key_learnings": [
    "A concrete insight or thing learned this week (one sentence, specific)"
  ],

  "missed_follow_ups": [
    {{
      "person": "Name or email",
      "what": "What was supposed to happen",
      "suggested_action": "Concrete next step"
    }}
  ],

  "people_spoke_to": [
    {{
      "name": "Name (Company)",
      "context": "One short sentence on what was discussed",
      "follow_up_needed": true
    }}
  ],

  "follow_up_drafts": [
    {{
      "to_email": "email@example.com",
      "to_name": "Name",
      "subject": "Subject line",
      "body": "Email body."
    }}
  ],

  "docs_created_or_edited": [
    {{
      "title": "Doc title",
      "url": "URL if available",
      "significance": "One sentence on what it was for"
    }}
  ],

  "open_loops_from_last_week": [
    "Status update on something flagged last week"
  ],

  "week_ahead_preview": [
    {{
      "title": "Event title",
      "date": "Day and time",
      "prep_note": "What to prepare or think about"
    }}
  ],

  "closing_thought": "One plain, honest observation to carry into next week"
}}

Rules:
- at_a_glance bullets: one sentence each, specific and factual
- key_learnings: real insights only, skip if nothing concrete
- missed_follow_ups: look for things promised or implied that weren't acted on
- follow_up_drafts: max 3, only genuine missed follow-ups
- people_spoke_to: keep context to one short sentence per person
- open_loops_from_last_week: omit entirely if last_weeks_summary is empty
- No motivational language, no superlatives
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
