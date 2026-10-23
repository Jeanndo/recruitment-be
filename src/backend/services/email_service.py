"""Email service for applicant notifications.

Sending mail is a blocking network call, so it is pushed onto a worker thread
with `anyio.to_thread`. That keeps the FastAPI routes fully async and means a
slow SMTP server never blocks the event loop for other requests.

A failure to send must never fail the request: the database change is already
committed by the time we get here, and the user should not see a 500 because
Gmail was briefly unavailable.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anyio.to_thread

from backend.core.config import settings
from backend.models.application import ApplicationStatus

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _message(to_email: str, subject: str, body: str) -> MIMEMultipart:
    message = MIMEMultipart()
    message["From"] = settings.email_sender
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    return message


def _confirmation_message(
    to_email: str,
    full_name: str,
    job_title: str,
) -> MIMEMultipart:
    body = f"""Hello {full_name},

Thank you for applying for the {job_title} role at BrightCore.

We have received your application and our team will review it carefully.
If your experience matches what we are looking for, we will reach out with
the next steps. Either way, you will hear back from us.

Best regards,
The BrightCore Team
"""
    return _message(
        to_email,
        f"We received your application for {job_title}",
        body,
    )


def _status_message(
    to_email: str,
    full_name: str,
    job_title: str,
    status: ApplicationStatus,
) -> MIMEMultipart:
    if status is ApplicationStatus.ACCEPTED:
        subject = f"Good news about your application for {job_title}"
        body = f"""Hello {full_name},

Thank you for your patience while we reviewed your application for the
{job_title} role at BrightCore.

We are happy to let you know that your application has been accepted. A
member of our team will contact you shortly with the next steps.

We are looking forward to speaking with you.

Best regards,
The BrightCore Team
"""
    else:
        subject = f"Update on your application for {job_title}"
        body = f"""Hello {full_name},

Thank you for taking the time to apply for the {job_title} role at
BrightCore.

After careful consideration, we have decided to move forward with other
candidates whose experience better matches what this role needs right now.
This is not a reflection of your abilities, and we would be glad to see you
apply for a future role that fits your experience.

We wish you all the best in your search.

Best regards,
The BrightCore Team
"""

    return _message(to_email, subject, body)


def _send_sync(to_email: str, message: MIMEMultipart) -> None:
    """Blocking SMTP delivery. Runs in a worker thread, never on the loop."""
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(settings.email_sender, settings.email_sender_pass)
        server.send_message(message, from_addr=settings.email_sender, to_addrs=[to_email])


async def _send(to_email: str, message: MIMEMultipart, description: str) -> bool:
    if not settings.email_sender or not settings.email_sender_pass:
        logger.warning(
            "EMAIL_SENDER / EMAIL_SENDER_PASS are not configured; "
            "skipping %s email.",
            description,
        )
        return False

    try:
        await anyio.to_thread.run_sync(_send_sync, to_email, message)
    except Exception:
        # Log the address and the exception, never the message body.
        logger.exception("Could not send %s email to %s", description, to_email)
        return False

    logger.info("Sent %s email to %s", description, to_email)
    return True


async def send_application_confirmation_email(
    to_email: str,
    full_name: str,
    job_title: str,
) -> bool:
    """Email the applicant that their application was received.

    Returns `True` when the mail was handed to Gmail, `False` when it was
    skipped (no credentials) or could not be sent. Callers should ignore the
    result: this is a best-effort notification.
    """
    return await _send(
        to_email,
        _confirmation_message(to_email, full_name, job_title),
        "application confirmation",
    )


async def send_application_status_email(
    to_email: str,
    full_name: str,
    job_title: str,
    status: ApplicationStatus,
) -> bool:
    """Email the applicant that their review status changed.

    Only Accepted and Rejected produce a mail; Pending is the initial state and
    is never sent. The internal admin note is deliberately not included.
    """
    if status not in (ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED):
        return False

    return await _send(
        to_email,
        _status_message(to_email, full_name, job_title, status),
        f"application {status.value.lower()}",
    )
