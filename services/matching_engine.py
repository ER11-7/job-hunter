from __future__ import annotations

from typing import Any

from models.entities import Job, MatchResult, Profile
from services.openai_client import embedding_similarity, parse_job_with_llm
from utils.text import cosine_similarity, normalize_tokens, unique_preserve_order


KNOWN_SKILLS = {
    "python",
    "sql",
    "power bi",
    "tableau",
    "esg",
    "sustainability",
    "climate",
    "energy markets",
    "financial modeling",
    "excel",
    "stakeholder management",
    "reporting",
    "data analysis",
    "scenario modelling",
    "decarbonization",
}

SENIORITY_HINTS = {
    "manager": "Manager",
    "lead": "Lead",
    "senior": "Senior",
    "analyst": "Analyst",
    "associate": "Associate",
}


def parse_job_description(job: Job) -> dict[str, Any]:
    llm_parsed = parse_job_with_llm(job.title, job.description)
    if llm_parsed:
        return llm_parsed

    text = f"{job.title} {job.description}".lower()
    skills = [skill for skill in KNOWN_SKILLS if skill in text]
    responsibilities = []
    for sentence in job.description.split("."):
        sentence = sentence.strip()
        if any(keyword in sentence.lower() for keyword in ("build", "drive", "lead", "analyze", "support", "develop")):
            responsibilities.append(sentence)
    seniority = "Mid"
    for hint, label in SENIORITY_HINTS.items():
        if hint in text:
            seniority = label
            break
    return {
        "skills": unique_preserve_order(skills),
        "responsibilities": responsibilities[:5],
        "seniority": seniority,
    }


def score_job(job: Job, profile: Profile) -> MatchResult:
    parsed = parse_job_description(job)
    profile_skill_map = {skill.lower(): skill for skill in profile.skills}
    job_skill_keys = [skill.lower() for skill in parsed["skills"]]
    overlap = [profile_skill_map[key] for key in job_skill_keys if key in profile_skill_map]
    missing = [skill for skill in parsed["skills"] if skill.lower() not in profile_skill_map]

    profile_experience_blob = " ".join(
        " ".join(str(value) for value in entry.values()) for entry in profile.experience
    )
    similarity = embedding_similarity(
        f"{profile.summary} {' '.join(profile.skills)} {profile_experience_blob}",
        f"{job.title} {job.description}",
    )
    if similarity is None:
        similarity = cosine_similarity(
        f"{profile.summary} {' '.join(profile.skills)} {profile_experience_blob}",
        f"{job.title} {job.description}",
        )
    skill_score = min(len(overlap) * 12, 48)
    domain_score = 15 if any(domain.lower() in job.description.lower() for domain in profile.domains) else 0
    location_score = 12 if any(location.lower() in job.location.lower() for location in profile.locations) else 0
    keyword_score = min(
        10,
        sum(2 for keyword in profile.keywords if keyword.lower() in job.description.lower() or keyword.lower() in job.title.lower()),
    )
    experience_score = 15 if len(profile.experience) >= 3 else 8
    similarity_score = round(similarity * 20)
    total = min(100, skill_score + domain_score + location_score + keyword_score + experience_score + similarity_score)

    if total >= 85:
        fit = "Excellent"
    elif total >= 70:
        fit = "Strong"
    elif total >= 55:
        fit = "Moderate"
    else:
        fit = "Weak"

    strengths = unique_preserve_order(
        overlap
        + [domain for domain in profile.domains if domain.lower() in job.description.lower()]
        + [location for location in profile.locations if location.lower() in job.location.lower()]
    )
    notes = (
        f"Similarity={similarity:.2f}, overlap={len(overlap)}, "
        f"domain_score={domain_score}, location_score={location_score}"
    )
    return MatchResult(
        score=total,
        missing_skills=missing,
        strengths=strengths[:6],
        fit=fit,
        parsed_job=parsed,
        notes=notes,
    )
