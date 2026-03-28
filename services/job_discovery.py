from __future__ import annotations

import logging

from backend.database import save_match, upsert_job
from models.entities import Job
from services.matching_engine import extract_profile_context, score_job
from services.job_sources import build_search_queries, fetch_all_sources
from services.role_recommender import get_best_roles
from utils.locations import is_target_location
from utils.time_utils import within_last_hour


LOGGER = logging.getLogger(__name__)


def _matches_filters(job: Job, profile_text: str) -> bool:
    profile = extract_profile_context(profile_text)
    searchable_text = f"{job.title} {job.description}".lower()
    role_match = any(role.lower() in searchable_text for role in profile["roles"])
    preferred_role_match = any(role.lower() in searchable_text for role in profile["preferred_roles"])
    keyword_match = any(keyword.lower() in searchable_text for keyword in profile["skills"])
    domain_match = any(domain.lower() in searchable_text for domain in profile["domains"])
    return within_last_hour(job.posted_at) and is_target_location(job.location) and (role_match or preferred_role_match or keyword_match or domain_match)


def discover_and_score_jobs(profile_text: str) -> list[dict]:
    shortlisted: list[dict] = []
    recommended_roles = get_best_roles(profile_text)
    queries = build_search_queries(profile_text, recommended_roles)
    profile_id = "uploaded_profile"
    for job in fetch_all_sources(profile_text):
        if not _matches_filters(job, profile_text):
            continue
        upsert_job(job.to_record())
        match = score_job(job, profile_text)
        save_match(job.id, profile_id, match.to_dict())
        shortlisted.append(
            {
                **job.to_record(),
                **match.to_dict(),
                "recommended_roles": recommended_roles,
                "queries": queries,
            }
        )
    LOGGER.info("Discovered %s jobs for uploaded session profile", len(shortlisted))
    return shortlisted
