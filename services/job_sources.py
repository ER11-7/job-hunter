from __future__ import annotations

import logging
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from models.entities import Job
from services.company_jobs import fetch_company_jobs
from services.matching_engine import extract_profile_context
from services.role_recommender import get_best_roles
from utils.time_utils import utc_now


LOGGER = logging.getLogger(__name__)
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AIJobAgent/1.0; +https://github.com/ER11-7/job-hunter)",
    "Accept-Language": "en-US,en;q=0.9",
}


def build_search_queries(profile_text: str, recommended_roles: list[str] | None = None) -> list[str]:
    profile = extract_profile_context(profile_text)
    queries: list[str] = []
    roles = recommended_roles or profile["preferred_roles"] or profile["roles"]
    domain_terms = profile["domains"]
    for role in roles[:3]:
        for location in ("Bengaluru", "Delhi NCR"):
            queries.append(f"{role} {location}")
    for domain in domain_terms[:3]:
        queries.append(f"{domain} Analyst India")
    return queries


def _normalize_remote_job(source: str, item: dict, fallback_id: str) -> Job:
    return Job(
        id=item.get("id", fallback_id),
        title=item.get("title", ""),
        company=item.get("company", source.title()),
        description=item.get("description", item.get("snippet", "")),
        location=item.get("location", ""),
        posted_at=utc_now(),
        source=source,
        url=item.get("url", ""),
        salary=item.get("salary", ""),
    )


def _query_matches_profile(job: Job, profile_text: str, query_tokens: str) -> bool:
    profile = extract_profile_context(profile_text)
    profile_terms = {
        term.lower()
        for term in profile["roles"] + profile["preferred_roles"] + profile["skills"] + profile["domains"]
        if term
    }
    return any(term in f"{job.title} {job.description} {query_tokens}".lower() for term in profile_terms)


def _filter_jobs_for_profile(profile_text: str, jobs: list[Job], recommended_roles: list[str] | None = None) -> list[Job]:
    query_tokens = " ".join(build_search_queries(profile_text, recommended_roles)).lower()
    return [job for job in jobs if _query_matches_profile(job, profile_text, query_tokens)]


def _request_json(url: str) -> list[dict]:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        for key in ("jobs", "results", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
        return []
    return payload if isinstance(payload, list) else []


def _safe_html_fetch(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


def fetch_linkedin_jobs(profile_text: str, recommended_roles: list[str] | None = None) -> list[Job]:
    queries = build_search_queries(profile_text, recommended_roles)
    jobs: list[Job] = []
    for index, query in enumerate(queries[:2]):
        try:
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={query.replace(' ', '%20')}"
            soup = BeautifulSoup(_safe_html_fetch(url), "html.parser")
            for offset, card in enumerate(soup.select(".base-search-card")):
                title = card.select_one(".base-search-card__title")
                company = card.select_one(".base-search-card__subtitle")
                location = card.select_one(".job-search-card__location")
                link = card.select_one("a")
                jobs.append(
                    Job(
                        id=f"linkedin_live_{index}_{offset}",
                        title=title.get_text(" ", strip=True) if title else query,
                        company=company.get_text(" ", strip=True) if company else "LinkedIn",
                        description=query,
                        location=location.get_text(" ", strip=True) if location else "",
                        posted_at=utc_now(),
                        source="linkedin",
                        url=link["href"] if link else "",
                    )
                )
        except Exception as exc:
            LOGGER.warning("LinkedIn fetch failed for query '%s': %s", query, exc)
    return _filter_jobs_for_profile(profile_text, jobs, recommended_roles)


def fetch_naukri_jobs(profile_text: str, recommended_roles: list[str] | None = None) -> list[Job]:
    queries = build_search_queries(profile_text, recommended_roles)
    jobs: list[Job] = []
    for index, query in enumerate(queries[:2]):
        try:
            url = f"https://www.naukri.com/{query.lower().replace(' ', '-')}-jobs"
            soup = BeautifulSoup(_safe_html_fetch(url), "html.parser")
            for offset, card in enumerate(soup.select(".srp-jobtuple-wrapper")):
                title = card.select_one(".title")
                company = card.select_one(".comp-name")
                location = card.select_one(".locWdth")
                link = title.get("href") if title else ""
                jobs.append(
                    Job(
                        id=f"naukri_live_{index}_{offset}",
                        title=title.get_text(" ", strip=True) if title else query,
                        company=company.get_text(" ", strip=True) if company else "Naukri",
                        description=card.get_text(" ", strip=True),
                        location=location.get_text(" ", strip=True) if location else "",
                        posted_at=utc_now(),
                        source="naukri",
                        url=link or "",
                    )
                )
        except Exception as exc:
            LOGGER.warning("Naukri fetch failed for query '%s': %s", query, exc)
    return _filter_jobs_for_profile(profile_text, jobs, recommended_roles)


def fetch_indeed_jobs(profile_text: str, recommended_roles: list[str] | None = None) -> list[Job]:
    queries = build_search_queries(profile_text, recommended_roles)
    jobs: list[Job] = []
    for index, query in enumerate(queries[:2]):
        try:
            url = f"https://remotive.com/api/remote-jobs?search={query.replace(' ', '%20')}"
            for offset, item in enumerate(_request_json(url)[:8]):
                jobs.append(
                    _normalize_remote_job(
                        "indeed",
                        {
                            "id": f"indeed_live_{index}_{offset}",
                            "title": item.get("title", query),
                            "company": item.get("company_name", "Indeed"),
                            "description": item.get("description", ""),
                            "location": item.get("candidate_required_location", ""),
                            "url": item.get("url", ""),
                        },
                        f"indeed_live_{index}_{offset}",
                    )
                )
        except Exception as exc:
            LOGGER.warning("Indeed-style fetch failed for query '%s': %s", query, exc)
    return _filter_jobs_for_profile(profile_text, jobs, recommended_roles)


def fetch_all_sources(profile_text: str) -> Iterable[Job]:
    recommended_roles = get_best_roles(profile_text)
    for fetcher in (
        fetch_linkedin_jobs,
        fetch_naukri_jobs,
        fetch_indeed_jobs,
    ):
        for job in fetcher(profile_text, recommended_roles):
            yield job
    for job in fetch_company_jobs(extract_profile_context(profile_text)):
        yield job
