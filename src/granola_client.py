import json
import os
from datetime import datetime, timedelta, timezone
import httpx

GRANOLA_MCP_URL = "https://mcp.granola.ai/mcp"
GRANOLA_AUTH_URL = "https://api.workos.com/user_management/authenticate"
REFRESH_TOKEN = os.environ.get("GRANOLA_REFRESH_TOKEN", "")
CLIENT_ID = os.environ.get("GRANOLA_CLIENT_ID", "")

def _get_access_token() -> str:
    if not REFRESH_TOKEN or not CLIENT_ID:
        raise ValueError("GRANOLA_REFRESH_TOKEN and GRANOLA_CLIENT_ID secrets are not set.")
    response = httpx.post(
        GRANOLA_AUTH_URL,
        json={"client_id": CLIENT_ID, "grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]

def _mcp_call(access_token: str, tool_name: str, arguments: dict) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}}
    response = httpx.post(
        GRANOLA_MCP_URL,
        json=payload,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def get_meeting_notes(days: int = 7) -> list[dict]:
    if not REFRESH_TOKEN:
        print("⚠️  Skipping Granola — GRANOLA_REFRESH_TOKEN not set.")
        return []
    try:
        access_token = _get_access_token()
        print("   Granola access token refreshed ✅")
    except Exception as e:
        print(f"⚠️  Could not refresh Granola token: {e}")
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        result = _mcp_call(access_token, "get_notes", {"since": since.isoformat(), "limit": 50})
    except Exception as e:
        print(f"⚠️  Could not fetch Granola notes: {e}")
        try:
            tools = list_available_tools()
            print(f"   Available Granola tools: {tools}")
        except Exception:
            pass
        return []
    notes_raw = result.get("result", {}).get("content", [])
    notes = []
    for note in notes_raw:
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
    access_token = _get_access_token()
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    response = httpx.post(
        GRANOLA_MCP_URL,
        json=payload,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    tools = response.json().get("result", {}).get("tools", [])
    return [t.get("name") for t in tools]
