from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Profile:
    id: str
    name: str
    email: str = ""
    summary: str = ""
    experience_level: str = ""
    roles: list[str] = field(default_factory=list)
    preferred_roles: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    experience: list[dict[str, Any]] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Job:
    id: str
    title: str
    company: str
    description: str
    location: str
    posted_at: datetime
    source: str
    url: str = ""
    salary: str = ""

    def to_record(self) -> dict[str, Any]:
        data = asdict(self)
        data["posted_at"] = self.posted_at.isoformat()
        return data


@dataclass
class MatchResult:
    score: float
    missing_skills: list[str]
    strengths: list[str]
    fit: str
    parsed_job: dict[str, Any]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReferralContact:
    name: str
    role: str
    linkedin_url: str
    company: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
