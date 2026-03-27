from __future__ import annotations

import smtplib
from email.message import EmailMessage

from backend.database import mark_notified
from utils.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


def _send_email(recipient: str, subject: str, body: str) -> bool:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD and recipient):
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)
    return True


def _send_mobile_push(recipient: str, body: str) -> bool:
    # Firebase or another push provider can be plugged in here later.
    return bool(recipient and False)


def send_high_priority_notification(profile, job: dict) -> str:
    subject = f"High-match job alert: {job['title']} at {job['company']}"
    body = (
        f"Score: {job['score']}\n"
        f"Location: {job['location']}\n"
        f"Source: {job['source']}\n"
        f"Missing skills: {', '.join(job['missing_skills']) or 'None'}\n"
        f"URL: {job['url']}\n"
    )
    email_sent = _send_email(profile.email, subject, body)
    push_sent = _send_mobile_push(profile.email, body)
    mark_notified(job["id"], profile.id)
    if email_sent and push_sent:
        return "email_and_push_sent"
    if email_sent:
        return "email_sent"
    if push_sent:
        return "push_sent"
    return "queued_for_ui"
