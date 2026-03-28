from __future__ import annotations

import logging
import time

from backend.database import get_user_settings, has_alerted_job
from services.job_discovery import discover_and_score_jobs
from services.notifier import send_batch_alerts


LOGGER = logging.getLogger(__name__)


def run_cycle(profile_text: str) -> list[dict]:
    jobs = discover_and_score_jobs(profile_text)
    settings = get_user_settings()
    threshold = float(settings.get("alert_threshold", 75))
    high_match_jobs = [
        job for job in jobs
        if float(job.get("match_score") or job.get("score") or 0) >= threshold and not has_alerted_job(job["id"])
    ]
    if settings.get("alerts_enabled") and high_match_jobs:
        alert_status = send_batch_alerts(
            settings.get("alert_email", ""),
            settings.get("alert_whatsapp", ""),
            high_match_jobs,
        )
        LOGGER.info("Batch alert status: %s", alert_status)
    return jobs


def scheduler_loop(profile_text: str, interval_minutes: int = 30) -> None:
    LOGGER.info("Worker started for uploaded_profile with %s minute interval", interval_minutes)
    while True:
        run_cycle(profile_text)
        time.sleep(interval_minutes * 60)
