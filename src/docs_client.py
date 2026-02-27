"""
Google Docs client — finds documents created or modified in the last 7 days
and returns their titles + a snippet of content.
"""

from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_recent_docs(creds: Credentials, days: int = 7) -> list[dict]:
    """
    Returns Google Docs modified in the last `days` days.
    Uses Drive API to search, then Docs API to get content snippets.
    """
    drive_service = build("drive", "v3", credentials=creds)
    docs_service = build("docs", "v1", credentials=creds)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_str = since.isoformat()

    # Search Drive for Google Docs modified recently
    results = drive_service.files().list(
        q=f"mimeType='application/vnd.google-apps.document' and modifiedTime > '{since_str}'",
        fields="files(id, name, modifiedTime, createdTime, webViewLink)",
        orderBy="modifiedTime desc",
        pageSize=20,
    ).execute()

    docs = []
    for file in results.get("files", []):
        # Fetch the first ~500 chars of document content
        snippet = ""
        try:
            doc = docs_service.documents().get(documentId=file["id"]).execute()
            content_parts = []
            for element in doc.get("body", {}).get("content", []):
                para = element.get("paragraph", {})
                for pe in para.get("elements", []):
                    text = pe.get("textRun", {}).get("content", "")
                    content_parts.append(text)
                    if sum(len(p) for p in content_parts) > 500:
                        break
                if sum(len(p) for p in content_parts) > 500:
                    break
            snippet = "".join(content_parts)[:500].strip()
        except Exception:
            pass  # If we can't read it, skip content

        docs.append({
            "id": file["id"],
            "title": file.get("name", "Untitled"),
            "modified": file.get("modifiedTime", ""),
            "created": file.get("createdTime", ""),
            "url": file.get("webViewLink", ""),
            "snippet": snippet,
        })

    return docs
