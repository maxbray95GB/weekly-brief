"""
Google authentication — handles OAuth credentials for Gmail, Calendar, and Drive/Docs.

In GitHub Actions, credentials come from the GOOGLE_CREDENTIALS_JSON secret,
which contains a service account JSON or OAuth token JSON.

SETUP: See README.md → Step 2: Google API Setup
"""

import json
import os

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account


# All the Google API scopes we need
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",   # For creating drafts
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


def get_credentials() -> Credentials:
    """
    Loads Google credentials from the GOOGLE_CREDENTIALS_JSON environment variable.
    
    This env var should contain the full JSON content of either:
    - An OAuth 2.0 token file (preferred — works with personal Gmail)
    - A service account key (requires Google Workspace domain delegation)
    
    See README.md for how to generate this.
    """
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not raw:
        raise EnvironmentError(
            "GOOGLE_CREDENTIALS_JSON environment variable is not set. "
            "See README.md → Step 2 for setup instructions."
        )

    cred_data = json.loads(raw)

    # Detect credential type
    if cred_data.get("type") == "service_account":
        # Service account — for Google Workspace users
        creds = service_account.Credentials.from_service_account_info(
            cred_data,
            scopes=SCOPES,
        )
        # If you're impersonating a user (Workspace domain delegation):
        # subject = os.environ.get("GOOGLE_SUBJECT_EMAIL")
        # if subject:
        #     creds = creds.with_subject(subject)
    else:
        # OAuth token — for personal Gmail accounts
        creds = Credentials(
            token=cred_data.get("token"),
            refresh_token=cred_data.get("refresh_token"),
            token_uri=cred_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=cred_data.get("client_id"),
            client_secret=cred_data.get("client_secret"),
            scopes=SCOPES,
        )

    return creds
