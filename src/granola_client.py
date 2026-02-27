"""
Granola MCP client — connects to Granola's MCP server to pull
meeting notes from the last 7 days.

MCP (Model Context Protocol) is a standard way for AI tools to expose
their data. Granola supports it, meaning we can query it programmatically.

SETUP REQUIRED:
  - You need your Granola MCP server URL and API token.
  - In Granola: Settings → Integrations → MCP → Copy server URL + token.
  - Add these as GitHub Secrets: GRANOLA_MCP_URL and GRANOLA_MCP_TOKEN.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import httpx


GRANOLA_MCP_URL = os.environ.get("GRANOLA_MCP_URL", "")
GRANOLA_MCP_TOKEN = os.environ.get("GRANOLA_MCP_TOKEN", "")


def _mcp_call(tool_name: str, arguments: dict) -> dict:
    """
    Makes a single MCP tool call to Granola's server.
    MCP uses a simple HTTP JSON-RPC style protocol.
    """
    if not GRANOLA_MCP_URL or not GRANOLA_MCP_TOKEN:
        raise ValueError(
            "GRANOLA_MCP_URL and GRANOLA_MCP_TOKEN environment variables are not set. "
            "See src/granola_client.py for setup instructions."
        )

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    response = httpx.post(
        GRANOLA_MCP_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {GRANOLA_MCP_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_meeting_notes(days: int = 7) -> list[dict]:
    """
    Fetches meeting notes from Granola for the last `days` days.
    Returns a list of note dicts with: title, date, attendees, summary, action_items.

    NOTE: The exact tool names depend on Granola's MCP implementation.
    Common tool names are listed below — adjust if Granola's docs differ.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        # Try fetching recent notes — tool name may vary, check Granola's MCP docs
        result = _mcp_call("get_notes", {
            "since": since.isoformat(),
            "limit": 50,
        })
    except Exception as e:
        print(f"⚠️  Could not fetch Granola notes: {e}")
        print("   Check your GRANOLA_MCP_URL and GRANOLA_MCP_TOKEN secrets.")
        return []

    # Parse the response — structure depends on Granola's schema
    notes_raw = result.get("result", {}).get("content", [])
    notes = []

    for note in notes_raw:
        # Handle both plain text and structured note formats
        if isinstance(note, str):
            try:
                note = json.loads(note)
            except json.JSONDecodeError:
                continue

        notes.append({
            "title": note.get("title", "Untitled meeting"),
            "date": note.get("date") or note.get("created_at", ""),
            "attendees": note.get("attendees", []),
            "summary": note.get("summary") or note.get("content", "")[:500],
            "action_items": note.get("action_items", []),
            "transcript_snippet": note.get("transcript", "")[:300],
        })

    return notes


def list_available_tools() -> list[str]:
    """
    Helper: lists all tools exposed by Granola's MCP server.
    Useful for debugging — run this to see exactly what Granola exposes.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }
    response = httpx.post(
        GRANOLA_MCP_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {GRANOLA_MCP_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    tools = response.json().get("result", {}).get("tools", [])
    return [t.get("name") for t in tools]