"""Transactional email delivery, abstracted behind a tiny interface.

Dev uses the console backend (messages are logged, never sent). Production
sets ORBITA_EMAIL_BACKEND=smtp and the SMTP_* settings. No third-party
dependency: the SMTP path uses the stdlib smtplib.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger("orbita.email")


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if settings.email_backend == "console":
        # Dev backend: print so the message (and its link) is always visible,
        # regardless of how the host configured logging.
        print(
            f"\n----- EMAIL (console backend) -----\n"
            f"To: {to}\nSubject: {subject}\n\n{body}\n"
            f"-----------------------------------\n",
            flush=True,
        )
        logger.info("EMAIL to=%s subject=%s", to, subject)
        return

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
