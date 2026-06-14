"""
Entry point for the AI Lead Response Bot.

Usage:
    python main.py          # runs once
    python main.py --loop   # runs every POLL_INTERVAL_MINUTES minutes
"""

import argparse
import logging
import os
import time

from dotenv import load_dotenv

from bot import LeadResponseBot
from sheets import SheetsClient

# ---------------------------------------------------------------------------
# Logging — ISO-style timestamps, level, and message
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _require_env(key: str) -> str:
    """Return an env var or raise a clear error if it's missing."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Check your .env file against .env.example."
        )
    return value


def _is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes")


def _build_demo_bot() -> LeadResponseBot:
    """Minimal bot for demo mode — only needs the Anthropic key."""
    return LeadResponseBot(
        sheets_client=None,
        anthropic_api_key=_require_env("ANTHROPIC_API_KEY"),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        smtp_user="",
        smtp_password="",
        sender_name=os.getenv("SENDER_NAME", "Mollie Taylor"),
        email_subject_template=os.getenv(
            "EMAIL_SUBJECT_TEMPLATE", "Re: Your enquiry, {name}"
        ),
        sign_off=os.getenv("EMAIL_SIGN_OFF", "Best,\nMollie"),
        demo_mode=True,
    )


def _build_live_bot() -> LeadResponseBot:
    """Full bot for live mode — requires Google Sheets and Gmail credentials."""
    sheets_client = SheetsClient(
        credentials_path=_require_env("GOOGLE_CREDENTIALS_PATH"),
        spreadsheet_id=_require_env("GOOGLE_SPREADSHEET_ID"),
        sheet_name=os.getenv("GOOGLE_SHEET_NAME", "Sheet1"),
    )
    return LeadResponseBot(
        sheets_client=sheets_client,
        anthropic_api_key=_require_env("ANTHROPIC_API_KEY"),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        smtp_user=_require_env("GMAIL_ADDRESS"),
        smtp_password=_require_env("GMAIL_APP_PASSWORD"),
        sender_name=os.getenv("SENDER_NAME", "Mollie Taylor"),
        email_subject_template=os.getenv(
            "EMAIL_SUBJECT_TEMPLATE", "Re: Your enquiry, {name}"
        ),
        sign_off=os.getenv("EMAIL_SIGN_OFF", "Best,\nMollie"),
        demo_mode=False,
    )


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="AI Lead Response Bot")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep running every POLL_INTERVAL_MINUTES minutes (default: run once and exit).",
    )
    args = parser.parse_args()

    poll_minutes = int(os.getenv("POLL_INTERVAL_MINUTES", "5"))
    poll_seconds = poll_minutes * 60

    demo_mode = _is_demo_mode()
    logger.info("Starting AI Lead Response Bot (demo_mode=%s)", demo_mode)

    if demo_mode:
        bot = _build_demo_bot()
        bot.process_demo_lead()
        return

    bot = _build_live_bot()
    if args.loop:
        logger.info("Loop mode — checking every %d minute(s). Press Ctrl+C to stop.", poll_minutes)
        while True:
            try:
                bot.process_leads()
            except Exception:
                logger.exception("Unexpected error during processing run — will retry next cycle.")
            logger.info("Sleeping %d seconds until next check…", poll_seconds)
            time.sleep(poll_seconds)
    else:
        bot.process_leads()
        logger.info("Done.")


if __name__ == "__main__":
    main()
