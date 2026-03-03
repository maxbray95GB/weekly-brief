"""
memory.py — two-tier memory system.

Tier 1: memory.json (local, in repo)
  A growing file that accumulates context week over week:
  - People profiles (who they are, history, relationship)
  - Ongoing threads and deals
  - Weekly theme log

Tier 2: Supabase vector store
  Stores processed weekly data as searchable embeddings.
  Enables semantic search: "what do I know about X?" or
  "when did we last discuss Y?"

SETUP for Tier 2:
  1. Create a free account at https://supabase.com
  2. Create a new project
  3. Run the SQL in setup/supabase_schema.sql in the SQL editor
  4. Add these GitHub Secrets:
     SUPABASE_URL     — your project URL (e.g. https://xxx.supabase.co)
     SUPABASE_KEY     — your project anon/public key
"""

import json
import os
from datetime import datetime
from typing import Optional

MEMORY_FILE = "memory.json"

# Supabase credentials (optional — Tier 2 only works if these are set)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


# ── Tier 1: memory.json ───────────────────────────────────────────────────────

def load_memory() -> dict:
    """Loads the memory file, or returns an empty structure if it doesn't exist yet."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {
        "people": {},       # email/name → profile
        "threads": [],      # ongoing deals, projects, conversations
        "weekly_log": [],   # one entry per week
        "last_updated": "",
    }


def save_memory(memory: dict) -> None:
    """Saves the memory file."""
    memory["last_updated"] = datetime.now().isoformat()
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)
    print("✅ Memory file updated")


def update_memory_from_week(memory: dict, email_digest: dict, briefing: dict, meeting_notes: list) -> dict:
    """
    Updates the memory file with this week's data.
    Called after the briefing is generated.
    """
    today = datetime.now().isoformat()

    # Update people profiles
    for person in email_digest.get("people_contacted", []):
        key = person.get("email", "").lower()
        if not key:
            continue

        if key not in memory["people"]:
            memory["people"][key] = {
                "email": key,
                "name": person.get("name", ""),
                "company": person.get("company", ""),
                "first_seen": today,
                "last_seen": today,
                "total_interactions": 0,
                "notes": [],
                "context": "",
            }

        profile = memory["people"][key]
        profile["last_seen"] = today
        profile["total_interactions"] += person.get("interaction_count", 1)

        # Update name/company if we learned more
        if person.get("name") and not profile["name"]:
            profile["name"] = person["name"]
        if person.get("company") and not profile["company"]:
            profile["company"] = person["company"]

        # Add this week's summary as a note
        if person.get("summary"):
            profile["notes"].append({
                "week": today[:10],
                "note": person["summary"],
            })
            # Keep only last 8 weeks of notes
            profile["notes"] = profile["notes"][-8:]

    # Also add people from meeting notes
    for note in meeting_notes:
        for attendee in note.get("attendees", []):
            key = attendee.lower() if "@" in attendee else f"name:{attendee.lower()}"
            if key not in memory["people"]:
                memory["people"][key] = {
                    "email": attendee if "@" in attendee else "",
                    "name": attendee if "@" not in attendee else "",
                    "company": "",
                    "first_seen": today,
                    "last_seen": today,
                    "total_interactions": 1,
                    "notes": [],
                }
            else:
                memory["people"][key]["last_seen"] = today
                memory["people"][key]["total_interactions"] += 1

    # Update threads from missed follow-ups and commitments
    existing_thread_keys = {t.get("key", "") for t in memory["threads"]}

    for fu in briefing.get("missed_follow_ups", []):
        thread_key = f"{fu.get('person', '').lower()}:{fu.get('what', '')[:30].lower()}"
        if thread_key not in existing_thread_keys:
            memory["threads"].append({
                "key": thread_key,
                "person": fu.get("person", ""),
                "description": fu.get("what", ""),
                "status": "open",
                "created": today[:10],
                "last_seen": today[:10],
            })
        else:
            for t in memory["threads"]:
                if t.get("key") == thread_key:
                    t["last_seen"] = today[:10]

    # Add this week to the weekly log
    memory["weekly_log"].append({
        "week": today[:10],
        "headline": briefing.get("week_headline", ""),
        "themes": briefing.get("key_themes", []),
        "key_learnings": briefing.get("key_learnings", []),
        "closing_thought": briefing.get("closing_thought", ""),
        "people_count": len(email_digest.get("people_contacted", [])),
    })

    # Keep last 52 weeks (one year)
    memory["weekly_log"] = memory["weekly_log"][-52:]

    return memory


def get_memory_context(memory: dict, top_n_people: int = 20) -> str:
    """
    Returns a formatted string summarising the most relevant memory context
    for Claude to read before writing this week's brief.
    """
    if not memory.get("people") and not memory.get("weekly_log"):
        return ""

    lines = ["=== ACCUMULATED CONTEXT FROM PREVIOUS WEEKS ===\n"]

    # Top people by interaction count
    top_people = sorted(
        memory["people"].values(),
        key=lambda x: x.get("total_interactions", 0),
        reverse=True,
    )[:top_n_people]

    if top_people:
        lines.append("KEY PEOPLE (by frequency of contact):")
        for p in top_people:
            name = p.get("name") or p.get("email", "Unknown")
            company = f" ({p['company']})" if p.get("company") else ""
            interactions = p.get("total_interactions", 0)
            recent_note = p["notes"][-1]["note"] if p.get("notes") else ""
            lines.append(f"  - {name}{company} — {interactions} interactions. {recent_note}")

    # Open threads
    open_threads = [t for t in memory.get("threads", []) if t.get("status") == "open"]
    if open_threads:
        lines.append("\nOPEN THREADS (ongoing follow-ups):")
        for t in open_threads[-10:]:
            lines.append(f"  - {t.get('person', '')}: {t.get('description', '')} (since {t.get('created', '')})")

    # Last 3 weeks summary
    recent_weeks = memory.get("weekly_log", [])[-3:]
    if recent_weeks:
        lines.append("\nRECENT WEEKS:")
        for w in recent_weeks:
            themes = ", ".join(w.get("themes", []))
            lines.append(f"  - {w['week']}: {w.get('headline', '')} [{themes}]")

    return "\n".join(lines)


# ── Tier 2: Supabase vector store ─────────────────────────────────────────────

def _get_supabase_client():
    """Returns a Supabase client if credentials are configured."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except ImportError:
        print("⚠️  supabase package not installed. Run: pip install supabase")
        return None


def store_week_in_vector_db(
    email_digest: dict,
    briefing: dict,
    past_events: list,
    meeting_notes: list,
) -> None:
    """
    Stores this week's processed data in Supabase for future semantic search.
    Each person interaction, meeting, and insight gets its own row with an embedding.
    """
    client = _get_supabase_client()
    if not client:
        print("⚠️  Supabase not configured — skipping vector storage. See memory.py for setup.")
        return

    today = datetime.now().isoformat()[:10]

    # Store people interactions
    for person in email_digest.get("people_contacted", []):
        if not person.get("summary"):
            continue
        text = f"{person.get('name', person.get('email', ''))} ({person.get('company', '')}): {person['summary']}"
        _upsert_memory(client, "person_interaction", text, {
            "week": today,
            "email": person.get("email", ""),
            "name": person.get("name", ""),
            "company": person.get("company", ""),
            "interaction_count": person.get("interaction_count", 1),
        })

    # Store key learnings
    for learning in briefing.get("key_learnings", []):
        _upsert_memory(client, "learning", learning, {"week": today})

    # Store meeting summaries
    for note in meeting_notes:
        if note.get("summary"):
            _upsert_memory(client, "meeting", note["summary"], {
                "week": today,
                "title": note.get("title", ""),
                "date": note.get("date", ""),
                "attendees": json.dumps(note.get("attendees", [])),
            })

    # Store commitments
    for commitment in email_digest.get("commitments_made", []):
        text = f"Commitment with {commitment.get('person', '')}: {commitment.get('commitment', '')}"
        _upsert_memory(client, "commitment", text, {
            "week": today,
            "person": commitment.get("person", ""),
            "direction": commitment.get("direction", ""),
            "status": "open",
        })

    print(f"✅ Week data stored in Supabase vector DB")


def _upsert_memory(client, record_type: str, content: str, metadata: dict) -> None:
    """Stores a single memory record in Supabase."""
    try:
        client.table("weekly_memories").insert({
            "type": record_type,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        print(f"⚠️  Could not store {record_type} in Supabase: {e}")


def search_vector_memory(query: str, record_type: Optional[str] = None, limit: int = 5) -> list[dict]:
    """
    Searches the vector DB for memories relevant to a query.
    Returns matching records — useful for building context about specific people/topics.

    NOTE: Full vector similarity search requires the pgvector extension and
    an embeddings model. This scaffold uses simple text search as a starting point.
    To enable full semantic search, see setup/supabase_schema.sql.
    """
    client = _get_supabase_client()
    if not client:
        return []

    try:
        query_builder = client.table("weekly_memories").select("*")
        if record_type:
            query_builder = query_builder.eq("type", record_type)
        query_builder = query_builder.ilike("content", f"%{query}%").limit(limit)
        result = query_builder.execute()
        return result.data or []
    except Exception as e:
        print(f"⚠️  Vector search failed: {e}")
        return []

