"""
Core orchestration: read leads → generate reply → send or print → mark done.
"""

import logging
import textwrap

import anthropic

from mailer import send_email
from prompts import SYSTEM_PROMPT, build_user_prompt
from sheets import SheetsClient

_DEMO_LEAD = {
    "name":     "Sarah Jones",
    "email":    "sarah@example.com",
    "business": "Sarah's Yoga Studio",
    "message":  "Hi, I saw your website and I'm interested in your services — can you tell me more about pricing?",
}

logger = logging.getLogger(__name__)


class LeadResponseBot:
    """
    Ties together Sheets, Claude, and Gmail into a single processing loop.

    All config is passed in at construction time so the class stays testable
    and the messy env-var reading stays in main.py.
    """

    def __init__(
        self,
        *,
        sheets_client: SheetsClient | None,
        anthropic_api_key: str,
        claude_model: str,
        smtp_user: str,
        smtp_password: str,
        sender_name: str,
        email_subject_template: str,
        sign_off: str,
        demo_mode: bool,
    ):
        self._sheets = sheets_client
        self._claude = anthropic.Anthropic(api_key=anthropic_api_key)
        self._model = claude_model
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._sender_name = sender_name
        self._subject_template = email_subject_template
        self._sign_off = sign_off
        self._demo_mode = demo_mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_demo_lead(self) -> None:
        """Generate and print a reply for the hardcoded demo lead. No Sheets needed."""
        lead = _DEMO_LEAD
        name, business, message = lead["name"], lead["business"], lead["message"]
        body_core = self._generate_reply(name=name, business=business, message=message)
        body_text = self._assemble_body(name=name, core=body_core)
        subject = self._subject_template.format(name=name, business=business)
        self._print_demo(to=lead["email"], subject=subject, body=body_text)

    def process_leads(self) -> int:
        """
        Fetch all unresponded leads and handle each one.

        Returns:
            Number of leads successfully processed.
        """
        leads = self._sheets.get_unresponded_leads()
        if not leads:
            logger.info("No new leads to process.")
            return 0

        processed = 0
        for lead in leads:
            try:
                self._handle_lead(lead)
                processed += 1
            except Exception:
                # Log and continue so one bad lead doesn't block the rest
                logger.exception(
                    "Failed to process lead from %s (row %d) — skipping.",
                    lead.get("email"),
                    lead.get("row_index"),
                )

        logger.info("Processed %d / %d lead(s) this run.", processed, len(leads))
        return processed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_lead(self, lead: dict) -> None:
        """Generate a reply, send (or print) it, then mark the row responded."""
        name = lead["name"]
        email = lead["email"]
        business = lead["business"] or "your business"
        message = lead["message"]
        row_index = lead["row_index"]

        logger.info("Generating reply for %s <%s> (row %d)…", name, email, row_index)

        body_core = self._generate_reply(name=name, business=business, message=message)
        body_text = self._assemble_body(name=name, core=body_core)
        body_html = self._text_to_html(body_text)
        subject = self._subject_template.format(name=name, business=business)

        if self._demo_mode:
            self._print_demo(to=email, subject=subject, body=body_text)
        else:
            send_email(
                smtp_user=self._smtp_user,
                smtp_password=self._smtp_password,
                sender_name=self._sender_name,
                to_address=email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )

        if self._sheets:
            self._sheets.mark_responded(row_index)

    def _generate_reply(self, *, name: str, business: str, message: str) -> str:
        """Call Claude and return the generated reply body (core sentences only)."""
        response = self._claude.messages.create(
            model=self._model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": build_user_prompt(name, business, message)}
            ],
        )
        return response.content[0].text.strip()

    def _assemble_body(self, *, name: str, core: str) -> str:
        """Wrap the Claude-generated core with a greeting and sign-off."""
        first_name = name.split()[0]
        return f"Hi {first_name},\n\n{core}\n\n{self._sign_off}"

    @staticmethod
    def _text_to_html(text: str) -> str:
        """Convert plain-text body (newlines) to a minimal HTML email."""
        paragraphs = text.split("\n\n")
        html_paras = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)
        return textwrap.dedent(f"""\
            <html><body style="font-family:sans-serif;font-size:15px;color:#222;line-height:1.6">
            {html_paras}
            </body></html>""")

    @staticmethod
    def _print_demo(*, to: str, subject: str, body: str) -> None:
        """Pretty-print the email to stdout instead of sending it."""
        border = "─" * 60
        print(f"\n{border}")
        print(f"  DEMO MODE — email NOT sent")
        print(border)
        print(f"  To:      {to}")
        print(f"  Subject: {subject}")
        print(border)
        print(body)
        print(f"{border}\n")
