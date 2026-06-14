"""
Gmail sending via SMTP with an App Password.

Uses Python's built-in smtplib + ssl — no external mail library needed.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_GMAIL_SMTP_HOST = "smtp.gmail.com"
_GMAIL_SMTP_PORT = 465  # SSL


def send_email(
    *,
    smtp_user: str,
    smtp_password: str,
    sender_name: str,
    to_address: str,
    subject: str,
    body_html: str,
    body_text: str,
) -> None:
    """
    Send an email via Gmail SMTP.

    Args:
        smtp_user:     Gmail address used to authenticate (e.g. you@gmail.com).
        smtp_password: Gmail App Password (16-char, no spaces).
        sender_name:   Display name shown in the From field.
        to_address:    Recipient email address.
        subject:       Email subject line.
        body_html:     HTML version of the message body.
        body_text:     Plain-text fallback version of the message body.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{smtp_user}>"
    msg["To"] = to_address

    # Attach plain text first, HTML second (RFC 2046 — clients prefer the last part)
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(_GMAIL_SMTP_HOST, _GMAIL_SMTP_PORT, context=context) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_address, msg.as_string())

    logger.info("Email sent to %s (subject: %s)", to_address, subject)
