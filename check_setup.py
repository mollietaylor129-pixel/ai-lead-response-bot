"""
Quick sanity-check: verifies every credential and connection before you run the bot.

Usage:
    python check_setup.py

Exits with code 0 if everything is OK, 1 if anything fails.
"""

import os
import smtplib
import ssl
import sys

from dotenv import load_dotenv

load_dotenv()

PASS = "\033[32m  OK \033[0m"
FAIL = "\033[31m FAIL\033[0m"
WARN = "\033[33m WARN\033[0m"

errors = 0


def check(label: str, fn):
    global errors
    try:
        result = fn()
        msg = f"  {result}" if isinstance(result, str) else ""
        print(f"{PASS}  {label}{msg}")
    except Exception as exc:
        print(f"{FAIL}  {label}")
        print(f"       └─ {exc}")
        errors += 1


def require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise ValueError(f"{key} is not set in your .env file")
    return val


print("\n── Checking environment variables ───────────────────────────────")

def _check_env_vars():
    keys = [
        "GOOGLE_CREDENTIALS_PATH",
        "GOOGLE_SPREADSHEET_ID",
        "ANTHROPIC_API_KEY",
    ]
    demo = os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")
    if not demo:
        keys += ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]
    missing = [k for k in keys if not os.getenv(k, "").strip()]
    if missing:
        raise ValueError("Missing: " + ", ".join(missing))
    return f"all required vars present (DEMO_MODE={demo})"

check("Required env vars", _check_env_vars)


print("\n── Checking credentials file ────────────────────────────────────")

def _check_creds_file():
    path = require("GOOGLE_CREDENTIALS_PATH")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path!r}")
    import json
    with open(path) as f:
        data = json.load(f)
    required_fields = ["type", "project_id", "private_key", "client_email"]
    missing = [k for k in required_fields if k not in data]
    if missing:
        raise ValueError(f"JSON is missing fields: {missing}")
    if data.get("type") != "service_account":
        raise ValueError(f"Expected type=service_account, got {data.get('type')!r}")
    return data["client_email"]

check("credentials.json is valid", _check_creds_file)


print("\n── Checking Google Sheets connection ────────────────────────────")

def _check_sheets():
    from sheets import SheetsClient
    client = SheetsClient(
        credentials_path=require("GOOGLE_CREDENTIALS_PATH"),
        spreadsheet_id=require("GOOGLE_SPREADSHEET_ID"),
        sheet_name=os.getenv("GOOGLE_SHEET_NAME", "Sheet1"),
    )
    worksheet = client._connect()
    # Read just the header row to confirm we can access the sheet
    headers = worksheet.row_values(1)
    if not headers:
        raise ValueError("Row 1 is empty — have you added the column headers?")
    expected = ["Name", "Email", "Business", "Message", "Timestamp", "Responded"]
    missing_headers = [h for h in expected if h not in headers]
    if missing_headers:
        raise ValueError(f"Missing expected column headers: {missing_headers}")
    return f"connected · headers: {headers}"

check("Google Sheets connection & headers", _check_sheets)


print("\n── Checking Anthropic API key ───────────────────────────────────")

def _check_anthropic():
    import anthropic
    key = require("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=key)
    # Cheapest possible call — count tokens on a tiny string
    result = client.messages.count_tokens(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        messages=[{"role": "user", "content": "hi"}],
    )
    return f"key valid · model accessible"

check("Anthropic API key", _check_anthropic)


print("\n── Checking Gmail SMTP ──────────────────────────────────────────")

demo_mode = os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")

if demo_mode:
    print(f"{WARN}  Gmail SMTP (skipped — DEMO_MODE=true)")
else:
    def _check_gmail():
        user = require("GMAIL_ADDRESS")
        password = require("GMAIL_APP_PASSWORD").replace(" ", "")
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(user, password)
        return f"authenticated as {user}"

    check("Gmail SMTP login", _check_gmail)


print()
if errors:
    print(f"  {errors} check(s) failed. Fix the errors above and re-run.\n")
    sys.exit(1)
else:
    print("  All checks passed — you're ready to run the bot!\n")
    print("  Run once:       python main.py")
    print("  Run on a loop:  python main.py --loop\n")
    sys.exit(0)
