from __future__ import annotations

import time

from services.job_discovery import discover_and_score_jobs
from services.notifier import send_high_priority_notification


def run_cycle(profile) -> list[dict]:
    jobs = discover_and_score_jobs(profile)
    for job in jobs:
        if job["score"] > 85:
            send_high_priority_notification(profile, job)
    return jobs


def scheduler_loop(profile, interval_minutes: int = 30) -> None:
    while True:
        run_cycle(profile)
        time.sleep(interval_minutes * 60)
