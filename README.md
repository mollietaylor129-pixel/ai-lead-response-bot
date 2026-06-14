# AI Lead Response Bot

Automatically reads new enquiries from a Google Sheet, writes a personalised reply using Claude AI, sends it via Gmail, and marks the lead as handled — all without you lifting a finger.

---

## What it does

1. Checks a Google Sheet every 5 minutes for new form submissions
2. For each unanswered row, uses Claude to write a warm, specific reply
3. Sends the reply from your Gmail account
4. Stamps the row with a "Responded" timestamp so it's never sent twice

---

## Requirements

- Python 3.11 or later
- A Google account (for Sheets + Gmail)
- An Anthropic API key ([get one here](https://console.anthropic.com))
- A Gmail App Password (not your normal password — see step 4 below)

---

## Setup guide

### Step 1 — Download the project

```bash
git clone <repo-url>
cd ai-lead-response-bot
```

Or simply download and unzip the folder.

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

If you don't have `pip`, install Python from [python.org](https://python.org) first.

### Step 3 — Set up your Google Sheet

1. Create a new Google Sheet
2. In **row 1**, add these exact column headers (one per cell, A through F):

   | A    | B     | C        | D       | E         | F          |
   |------|-------|----------|---------|-----------|------------|
   | Name | Email | Business | Message | Timestamp | Responded  |

3. Copy the **Spreadsheet ID** from the URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_LONG_ID`**`/edit`

### Step 4 — Create a Google service account (so the bot can read your sheet)

1. Go to [Google Cloud Console](https://console.cloud.google.com) and create a new project
2. Enable the **Google Sheets API** and **Google Drive API** for that project
3. Go to **IAM & Admin → Service Accounts** and create a new service account
4. Click the service account → **Keys → Add Key → Create new key → JSON**
5. Download the JSON file and save it as `credentials.json` in this folder
6. Open your Google Sheet → **Share** → paste the service account email (looks like `something@project.iam.gserviceaccount.com`) → give it **Editor** access

### Step 5 — Create a Gmail App Password

> Regular Gmail passwords won't work — Google requires an App Password for SMTP access.

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. You may need to enable 2-Step Verification first
3. Select app: **Mail**, device: **Other** → type "Lead Bot" → click **Generate**
4. Copy the 16-character password (you'll paste it in the next step)

### Step 6 — Configure your environment

Copy the example file and fill in your details:

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in every value. The comments in the file explain each one.

**The only ones you must change:**
- `GOOGLE_CREDENTIALS_PATH` → path to your `credentials.json` (or just `credentials.json` if it's in the same folder)
- `GOOGLE_SPREADSHEET_ID` → the ID you copied in step 3
- `ANTHROPIC_API_KEY` → your key from console.anthropic.com
- `GMAIL_ADDRESS` → your Gmail address
- `GMAIL_APP_PASSWORD` → the 16-char password from step 5
- `SENDER_NAME` → your name

### Step 7 — Test with demo mode first

Set `DEMO_MODE=true` in your `.env` file, then run:

```bash
python main.py
```

You'll see the generated emails printed to the terminal instead of being sent. Once you're happy with them, set `DEMO_MODE=false`.

---

## Running the bot

**Once** (check now and exit):
```bash
python main.py
```

**Continuously** (check every 5 minutes):
```bash
python main.py --loop
```

To change the polling interval, update `POLL_INTERVAL_MINUTES` in your `.env`.

---

## Project structure

```
ai-lead-response-bot/
├── main.py          # Entry point — handles CLI args and the run loop
├── bot.py           # Core logic: fetch → generate → send → mark
├── sheets.py        # Google Sheets read/write
├── mailer.py        # Gmail SMTP sending
├── prompts.py       # Claude system prompt and prompt builder
├── .env             # Your private config (never commit this)
├── .env.example     # Template showing all required variables
├── requirements.txt # Python dependencies
└── credentials.json # Your Google service-account key (never commit this)
```

---

## Security notes

- **Never commit `.env` or `credentials.json`** — both contain private keys
- The `.gitignore` below covers this — add it to your repo if you don't have one already:

```
.env
credentials.json
__pycache__/
*.pyc
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `EnvironmentError: 'ANTHROPIC_API_KEY' is not set` | Check your `.env` file exists and the variable is spelled correctly |
| `gspread.exceptions.SpreadsheetNotFound` | Double-check the spreadsheet ID and that the service account has Editor access to the sheet |
| `smtplib.SMTPAuthenticationError` | Make sure you're using an App Password, not your Gmail password |
| Emails send but column F stays blank | Check the service account has **Editor** (not Viewer) permission on the sheet |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
