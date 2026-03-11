"""
email_digester.py — pre-processes all emails for the week in batches,
extracting a structured digest that covers the full 7 days without
hitting token limits.

Rate-limit aware: waits 65s between batches to stay under 10k
input tokens/min. Trims email bodies to 200 chars to reduce token usage.
"""

import json
import os
import time
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

BATCH_SIZE = 25  # Smaller batches to stay under rate limit
RATE_LIMIT_PAUSE = 65  # Seconds between batches (10k tokens/min limit)
MAX_RETRIES = 2


def _digest_batch(batch: list[dict], batch_num: int, total_batches: int) -> dict:
    """Sends one batch of emails to Claude and extracts structured insights."""

    prompt = f"""Process batch {batch_num}/{total_batches} of emails. Extract only what's genuinely notable. Skip pleasantries, newsletters, noise.

Emails:
{json.dumps(batch, default=str)}

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

    for attempt in range(MAX_RETRIES + 1):
        try:
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
        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES:
                wait = RATE_LIMIT_PAUSE * (attempt + 1)
                print(f"   ⏳ Rate limited — waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                raise


def merge_digests(digests: list[dict]) -> dict:
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

    num_batches = ((len(emails) - 1) // BATCH_SIZE) + 1
    print(f"   Digesting {len(emails)} emails in {num_batches} batches (with {RATE_LIMIT_PAUSE}s pauses)...")

    # Split into batches
    batches = [emails[i:i + BATCH_SIZE] for i in range(0, len(emails), BATCH_SIZE)]
    digests = []

    for i, batch in enumerate(batches):
        # Wait between batches to respect rate limit (skip before first)
        if i > 0:
            print(f"   ⏳ Waiting {RATE_LIMIT_PAUSE}s for rate limit...")
            time.sleep(RATE_LIMIT_PAUSE)

        # Trim email bodies aggressively to reduce tokens
        trimmed = []
        for e in batch:
            trimmed.append({
                "from": e.get("from", ""),
                "to": e.get("to", ""),
                "subject": e.get("subject", ""),
                "date": e.get("date", ""),
                "body": e.get("body", "")[:200],
            })

        try:
            digest = _digest_batch(trimmed, i + 1, len(batches))
            digests.append(digest)
            print(f"   Batch {i + 1}/{len(batches)} processed ✅")
        except Exception as ex:
            print(f"   ⚠️  Batch {i + 1} failed: {ex}")

    return merge_digests(digests)

