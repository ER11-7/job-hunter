from __future__ import annotations

from functools import lru_cache

import requests
from bs4 import BeautifulSoup

from models.entities import Job, Profile
from utils.locations import is_target_location
from utils.time_utils import utc_now


TARGET_COMPANIES = [
    {"name": "ReNew", "careers_url": "https://www.renew.com/careers/"},
    {"name": "Schneider Electric", "careers_url": "https://careers.se.com/"},
    {"name": "EY", "careers_url": "https://careers.ey.com/"},
    {"name": "KPMG", "careers_url": "https://kpmg.com/in/en/home/careers.html"},
]

@lru_cache(maxsize=16)
def _fetch_page_html(careers_url: str) -> str:
    response = requests.get(careers_url, timeout=20)
    response.raise_for_status()
    return response.text


def _extract_jobs_from_page(company_name: str, careers_url: str) -> list[Job]:
    soup = BeautifulSoup(_fetch_page_html(careers_url), "html.parser")
    jobs: list[Job] = []
    now = utc_now()
    for index, anchor in enumerate(soup.find_all("a", href=True)):
        title = anchor.get_text(" ", strip=True)
        href = anchor["href"]
        surrounding = anchor.parent.get_text(" ", strip=True) if anchor.parent else title
        if not title or len(title) < 6:
            continue
        if "job" not in title.lower() and "analyst" not in title.lower() and "consult" not in title.lower():
            continue
        location = surrounding
        if not is_target_location(location):
            continue
        jobs.append(
            Job(
                id=f"{company_name.lower().replace(' ', '_')}_{index}",
                title=title,
                company=company_name,
                description=surrounding,
                location=location,
                posted_at=now,
                source="company_careers",
                url=href if href.startswith("http") else careers_url.rstrip("/") + "/" + href.lstrip("/"),
            )
        )
    return jobs


def fetch_company_jobs(profile: Profile) -> list[Job]:
    jobs: list[Job] = []
    for company in TARGET_COMPANIES:
        try:
            jobs.extend(_extract_jobs_from_page(company["name"], company["careers_url"]))
        except Exception:
            continue

    profile_terms = {
        term.lower()
        for term in profile.roles + profile.skills + profile.domains + profile.keywords
        if term
    }
    return [
        job
        for job in jobs
        if is_target_location(job.location)
        and any(term in f"{job.title} {job.description}".lower() for term in profile_terms)
    ]
