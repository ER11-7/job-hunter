from __future__ import annotations

import re
import smtplib
from email.message import EmailMessage

import requests

from backend.database import mark_job_alerted
from utils.config import SMTP_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM


def _send_email(recipient: str, subject: str, body: str) -> bool:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and recipient):
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(message)
    return True


def _send_whatsapp(recipient: str, body: str) -> bool:
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM and recipient):
        return False
    response = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        data={
            "From": TWILIO_WHATSAPP_FROM,
            "To": f"whatsapp:{recipient}",
            "Body": body[:1500],
        },
        timeout=30,
    )
    return response.ok


def _extract_email(profile_text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", profile_text)
    return match.group(0) if match else ""


def send_high_priority_notification(profile_text: str, job: dict) -> str:
    subject = f"High-match job alert: {job['title']} at {job['company']}"
    body = (
        f"Score: {job['score']}\n"
        f"Location: {job['location']}\n"
        f"Source: {job['source']}\n"
        f"Missing skills: {', '.join(job['missing_skills']) or 'None'}\n"
        f"URL: {job['url']}\n"
    )
    recipient = _extract_email(profile_text)
    email_sent = _send_email(recipient, subject, body)
    mark_job_alerted(job["id"])
    return "email_sent" if email_sent else "queued_for_ui"


def send_batch_alerts(email: str, whatsapp: str, jobs: list[dict]) -> str:
    if not jobs:
        return "no_jobs"
    subject = f"🔥 {len(jobs)} high-match jobs found!"
    lines = [f"{job['title']} | {job['company']} | {job.get('url', '')} | {job.get('match_score', job.get('score', 0))}%" for job in jobs]
    body = "\n".join(lines)
    email_sent = _send_email(email, subject, body)
    whatsapp_sent = _send_whatsapp(whatsapp, body)
    for job in jobs:
        mark_job_alerted(job["id"])
    if email_sent and whatsapp_sent:
        return "email_and_whatsapp_sent"
    if email_sent:
        return "email_sent"
    if whatsapp_sent:
        return "whatsapp_sent"
    return "queued_for_ui"
