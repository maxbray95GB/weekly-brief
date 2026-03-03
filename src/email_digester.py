"""
email_digester.py — pre-processes all emails for the week in batches,
extracting a structured digest that covers the full 7 days without
hitting token limits.

This runs BEFORE the main summarizer, giving Claude a complete picture
of the week rather than just the most recent 30 emails.
"""

import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

BATCH_SIZE = 40  # Emails per batch


def _digest_batch(batch: list[dict], batch_num: int, total_batches: int) -> dict:
    """Sends one batch of emails to Claude and extracts structured insights."""

    prompt = f"""You are processing batch {batch_num} of {total_batches} of someone's emails from the past 7 days.

Extract ONLY what's genuinely notable. Skip pleasantries, newsletters, and noise.

Emails:
{json.dumps(batch, indent=2, default=str)}

Respond with JSON only:
{{
  "people_contacted": [
    {{
      "email": "their email",
      "name": "their name if known",
      "company": "their company if known",
      "interaction_count": 1,
      "summary": "One sentence on what was discussed"
    }}
  ],
  "commitments_made": [
    {{
      "person": "name or email",
      "commitment": "What was promised (by either party)",
      "direction": "you_to_them or them_to_you"
    }}
  ],
  "notable_emails": [
    {{
      "from": "sender",
      "subject": "subject",
      "why_notable": "One sentence on why this matters"
    }}
  ],
  "topics_mentioned": ["topic1", "topic2"]
}}

Be conservative — only include what's genuinely worth flagging.
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def _merge_digests(digests: list[dict]) -> dict:
    """Merges multiple batch digests into a single week digest."""
    merged = {
        "people_contacted": {},
        "commitments_made": [],
        "notable_emails": [],
        "topics_mentioned": [],
    }

    for d in digests:
        # Merge people, accumulating interaction counts
        for person in d.get("people_contacted", []):
            key = person.get("email", "").lower()
            if key in merged["people_contacted"]:
                merged["people_contacted"][key]["interaction_count"] += person.get("interaction_count", 1)
                # Keep most informative summary
                if len(person.get("summary", "")) > len(merged["people_contacted"][key]["summary"]):
                    merged["people_contacted"][key]["summary"] = person["summary"]
            else:
                merged["people_contacted"][key] = person

        merged["commitments_made"].extend(d.get("commitments_made", []))
        merged["notable_emails"].extend(d.get("notable_emails", []))
        merged["topics_mentioned"].extend(d.get("topics_mentioned", []))

    # Convert people dict back to list, sorted by interaction count
    merged["people_contacted"] = sorted(
        merged["people_contacted"].values(),
        key=lambda x: x.get("interaction_count", 0),
        reverse=True,
    )

    # Deduplicate topics
    merged["topics_mentioned"] = list(set(merged["topics_mentioned"]))

    return merged


def digest_emails(emails: list[dict]) -> dict:
    """
    Main entry point. Takes all emails for the week and returns
    a structured digest covering the full period.
    """
    if not emails:
        return {
            "people_contacted": [],
            "commitments_made": [],
            "notable_emails": [],
            "topics_mentioned": [],
        }

    print(f"   Digesting {len(emails)} emails in {((len(emails) - 1) // BATCH_SIZE) + 1} batches...")

    # Split into batches
    batches = [emails[i:i + BATCH_SIZE] for i in range(0, len(emails), BATCH_SIZE)]
    digests = []

    for i, batch in enumerate(batches):
        # Trim email bodies for the digest pass
        trimmed = []
        for e in batch:
            trimmed.append({
                "from": e.get("from", ""),
                "to": e.get("to", ""),
                "subject": e.get("subject", ""),
                "date": e.get("date", ""),
                "body": e.get("body", "")[:300],
            })

        try:
            digest = _digest_batch(trimmed, i + 1, len(batches))
            digests.append(digest)
            print(f"   Batch {i + 1}/{len(batches)} processed ✅")
        except Exception as ex:
            print(f"   ⚠️  Batch {i + 1} failed: {ex}")

    return _merge_digests(digests)

