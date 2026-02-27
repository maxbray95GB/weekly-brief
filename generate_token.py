"""
generate_token.py — run this ONCE on your local machine to generate
Google OAuth credentials for the bot.

Usage:
  1. Download your OAuth client secret from Google Cloud Console (see README Step 2c)
  2. Place it in the same folder as this script, named: client_secret.json
  3. Run: python generate_token.py
  4. A browser window will open — log in and grant permissions
  5. A file called token.json will be created
  6. Copy the contents of token.json into your GOOGLE_CREDENTIALS_JSON GitHub Secret
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

def main():
    print("Starting Google OAuth flow...")
    print("A browser window will open. Log in with the Google account you want to use.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }

    with open("token.json", "w") as f:
        json.dump(token_data, f, indent=2)

    print("\n✅ Success! token.json has been created.")
    print("\nNext step:")
    print("  1. Open token.json in a text editor")
    print("  2. Copy the entire contents")
    print("  3. Go to your GitHub repo → Settings → Secrets → New secret")
    print("  4. Name: GOOGLE_CREDENTIALS_JSON")
    print("  5. Value: paste the JSON content")

if __name__ == "__main__":
    main()
