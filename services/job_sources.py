from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from models.entities import Job
from utils.config import DATA_DIR
from utils.time_utils import utc_now


SAMPLE_SOURCE = DATA_DIR / "samples" / "sample_jobs.json"


def _load_sample_jobs() -> list[Job]:
    payload = json.loads(SAMPLE_SOURCE.read_text(encoding="utf-8"))
    jobs: list[Job] = []
    now = utc_now()
    for index, item in enumerate(payload):
        jobs.append(
            Job(
                id=item["id"],
                title=item["title"],
                company=item["company"],
                description=item["description"],
                location=item["location"],
                posted_at=now - timedelta(minutes=index * 12),
                source=item["source"],
                url=item.get("url", ""),
                salary=item.get("salary", ""),
            )
        )
    return jobs


def fetch_linkedin_jobs() -> list[Job]:
    return [job for job in _load_sample_jobs() if job.source == "linkedin"]


def fetch_naukri_jobs() -> list[Job]:
    return [job for job in _load_sample_jobs() if job.source == "naukri"]


def fetch_indeed_jobs() -> list[Job]:
    return [job for job in _load_sample_jobs() if job.source == "indeed"]


def fetch_fallback_jobs() -> list[Job]:
    return [job for job in _load_sample_jobs() if job.source in {"remotive", "rapidapi"}]


def fetch_all_sources() -> Iterable[Job]:
    for fetcher in (
        fetch_linkedin_jobs,
        fetch_naukri_jobs,
        fetch_indeed_jobs,
        fetch_fallback_jobs,
    ):
        for job in fetcher():
            yield job
