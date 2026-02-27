# Weekly Brief Bot

Sends you a formatted weekly briefing email every Friday at 8:30am. Pulls from Gmail, 
Google Calendar, Google Docs, and Granola meeting notes — then uses Claude to write 
a personalised summary with follow-ups, insights, and a week-ahead preview.

---

## What you'll need

Before starting, make sure you have:
- A **GitHub account** (free) — this is where the bot lives and runs
- An **Anthropic API key** — to use Claude for summarisation  
  Get one at: https://console.anthropic.com
- A **Google account** (the one with your Gmail/Calendar/Docs)
- **Granola** installed and being used for meeting notes

---

## Setup: Step by step

### Step 1 — Put this code on GitHub

1. Create a new repository on GitHub.com (call it `weekly-brief` or anything you like)
2. Upload all these files to it (drag and drop works in GitHub's UI)
3. Make sure the folder structure matches exactly what's here

---

### Step 2 — Set up Google API access

This is the most involved step. You're creating a "credential" that lets the bot 
read your Gmail, Calendar, and Docs on your behalf.

**2a. Create a Google Cloud project**
1. Go to https://console.cloud.google.com
2. Click "Select a project" → "New Project"
3. Name it "Weekly Brief Bot" → Create

**2b. Enable the APIs you need**
In your new project, go to "APIs & Services" → "Enable APIs":
- Enable: **Gmail API**
- Enable: **Google Calendar API**  
- Enable: **Google Drive API**
- Enable: **Google Docs API**

**2c. Create OAuth credentials**
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the "OAuth consent screen" first:
   - User type: External
   - App name: Weekly Brief Bot
   - Add your email as a test user
4. Application type: **Desktop app**
5. Download the JSON file — it'll be called something like `client_secret_xxx.json`

**2d. Generate your token**
Run this locally once (you need Python installed):

```bash
pip install google-auth-oauthlib google-api-python-client
python generate_token.py
```

This will open a browser window asking you to log in with your Google account 
and grant permissions. After you do, it saves a file called `token.json`.

**2e. Add the token to GitHub**
- Open `token.json` in a text editor, copy the entire contents
- In your GitHub repo: Settings → Secrets and variables → Actions → New secret
- Name: `GOOGLE_CREDENTIALS_JSON`
- Value: paste the entire JSON content

---

### Step 3 — Add your Granola MCP credentials

1. Open Granola on your Mac
2. Go to Settings → Integrations (or look for an "MCP" or "API" section)
3. Find your MCP server URL and API token
4. Add them as GitHub Secrets:
   - `GRANOLA_MCP_URL` — the server URL
   - `GRANOLA_MCP_TOKEN` — your token

> **Note:** Granola's MCP support is relatively new. If you can't find these settings,
> check Granola's documentation or contact their support. The bot will still work 
> without Granola — it just won't include meeting notes.

---

### Step 4 — Add your remaining secrets

In GitHub: Settings → Secrets and variables → Actions, add:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key from console.anthropic.com |
| `RECIPIENT_EMAIL` | Your email address (where the brief gets sent) |
| `USER_NAME` | Your first name (used in the briefing tone) |

---

### Step 5 — Test it manually

Before waiting until Friday:
1. Go to your GitHub repo → Actions tab
2. Click "Weekly Brief" in the left sidebar
3. Click "Run workflow" → "Run workflow"
4. Watch it run — check the logs if anything goes wrong
5. Check your inbox!

---

### Step 6 — Adjust the schedule (if needed)

The bot runs at 8:30am UTC, which is:
- 8:30am in winter (GMT)
- 9:30am in British Summer Time (BST)

To change the time, edit `.github/workflows/weekly_brief.yml` and change the cron line:
```
- cron: '30 8 * * 5'
```
Format is: `minute hour * * 5` (5 = Friday)
Use https://crontab.guru to work out the right UTC time for your timezone.

---

## File structure

```
weekly-brief/
├── main.py                          # Entry point — runs everything
├── requirements.txt                 # Python packages needed
├── last_week_summary.json           # Auto-updated each week for continuity
├── generate_token.py                # Run once locally to get Google credentials
├── .github/
│   └── workflows/
│       └── weekly_brief.yml         # The GitHub Actions scheduler
└── src/
    ├── auth.py                      # Google authentication
    ├── gmail_client.py              # Reads emails, creates drafts
    ├── calendar_client.py           # Reads past + upcoming events
    ├── docs_client.py               # Reads recently edited Google Docs
    ├── granola_client.py            # Fetches Granola meeting notes via MCP
    ├── summarizer.py                # Calls Claude to generate the briefing
    └── email_formatter.py           # Builds the formatted HTML email
```

---

## Customising the output

**Change what gets included:** Edit the prompt in `src/summarizer.py`

**Change the email design:** Edit `src/email_formatter.py`

**Change the noise filter** (which emails are ignored): Edit `NOISE_PATTERNS` in `src/gmail_client.py`

**Change the schedule:** Edit the cron expression in `.github/workflows/weekly_brief.yml`

---

## Troubleshooting

**"GOOGLE_CREDENTIALS_JSON is not set"** — You haven't added the secret in GitHub yet. See Step 2e.

**"Token expired"** — OAuth tokens expire. Re-run `generate_token.py` locally to get a fresh one, then update the GitHub secret.

**Granola not working** — The bot logs a warning and continues without it. Check your `GRANOLA_MCP_URL` and `GRANOLA_MCP_TOKEN` secrets.

**Email not arriving** — Check the GitHub Actions run logs for errors. Also check your spam folder.

**Action failed in GitHub** — Click on the failed run → click the job → read the error output. Most issues are missing secrets or typos in secret names.
