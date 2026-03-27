from __future__ import annotations

from backend.database import save_match, upsert_job
from models.entities import Job, Profile
from services.job_sources import fetch_all_sources
from services.matching_engine import score_job
from utils.time_utils import within_last_hour


def _matches_filters(job: Job, profile: Profile) -> bool:
    matches_location = any(location.lower() in job.location.lower() for location in profile.locations)
    matches_keyword = any(
        keyword.lower() in f"{job.title} {job.description}".lower()
        for keyword in profile.keywords
    )
    return within_last_hour(job.posted_at) and matches_location and matches_keyword


def discover_and_score_jobs(profile: Profile) -> list[dict]:
    shortlisted: list[dict] = []
    for job in fetch_all_sources():
        if not _matches_filters(job, profile):
            continue
        upsert_job(job.to_record())
        match = score_job(job, profile)
        save_match(job.id, profile.id, match.to_dict())
        shortlisted.append(
            {
                **job.to_record(),
                **match.to_dict(),
            }
        )
    return shortlisted
