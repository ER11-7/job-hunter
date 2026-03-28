from __future__ import annotations

import logging
import time

from services.job_discovery import discover_and_score_jobs
from services.notifier import send_high_priority_notification


LOGGER = logging.getLogger(__name__)


def run_cycle(profile_text: str) -> list[dict]:
    jobs = discover_and_score_jobs(profile_text)
    for job in jobs:
        if job["score"] >= 85:
            status = send_high_priority_notification(profile_text, job)
            LOGGER.info("Notification status for uploaded_profile on %s: %s", job["id"], status)
    return jobs


def scheduler_loop(profile_text: str, interval_minutes: int = 30) -> None:
    LOGGER.info("Worker started for uploaded_profile with %s minute interval", interval_minutes)
    while True:
        run_cycle(profile_text)
        time.sleep(interval_minutes * 60)
