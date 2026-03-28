from __future__ import annotations

from typing import Any

from models.entities import Job, MatchResult
from services.openai_client import embedding_similarity, parse_job_with_llm
from utils.text import cosine_similarity, unique_preserve_order


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
KNOWN_ROLE_TERMS = {
    "analyst",
    "associate",
    "consultant",
    "manager",
    "specialist",
    "lead",
}
KNOWN_DOMAINS = {
    "esg",
    "climate",
    "energy",
    "sustainability",
    "policy",
    "carbon",
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


def extract_profile_context(profile_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in profile_text.splitlines() if line.strip()]
    lower_text = profile_text.lower()
    roles = unique_preserve_order(
        [line for line in lines[:20] if any(term in line.lower() for term in KNOWN_ROLE_TERMS)]
    )[:5]
    skills = unique_preserve_order([skill.title() for skill in KNOWN_SKILLS if skill in lower_text])
    domains = unique_preserve_order([domain.upper() if domain == "esg" else domain.title() for domain in KNOWN_DOMAINS if domain in lower_text])
    experience_level = "mid"
    if "senior" in lower_text or "lead" in lower_text:
        experience_level = "senior"
    elif "junior" in lower_text or "entry" in lower_text:
        experience_level = "junior"
    return {
        "name": lines[0] if lines else "Uploaded Profile",
        "summary": " ".join(lines[:4])[:400],
        "roles": roles,
        "skills": skills,
        "domains": domains,
        "experience_level": experience_level,
        "preferred_roles": roles[:5],
        "raw_text": profile_text,
    }


def score_job(job: Job, profile_text: str) -> MatchResult:
    profile = extract_profile_context(profile_text)
    parsed = parse_job_description(job)
    profile_skill_map = {skill.lower(): skill for skill in profile["skills"]}
    job_skill_keys = [skill.lower() for skill in parsed["skills"]]
    overlap = [profile_skill_map[key] for key in job_skill_keys if key in profile_skill_map]
    missing = [skill for skill in parsed["skills"] if skill.lower() not in profile_skill_map]
    title_text = job.title.lower()
    description_text = job.description.lower()

    role_hits = [role for role in profile["roles"] if role.lower() in title_text]
    preferred_role_hits = [role for role in profile["preferred_roles"] if role.lower() in title_text]
    domain_hits = [domain for domain in profile["domains"] if domain.lower() in description_text or domain.lower() in title_text]

    similarity = embedding_similarity(
        f"{profile['summary']} {' '.join(profile['skills'])} {profile_text}",
        f"{job.title} {job.description}",
    )
    if similarity is None:
        similarity = cosine_similarity(
            f"{profile['summary']} {' '.join(profile['roles'])} {' '.join(profile['skills'])} {profile_text}",
            f"{job.title} {job.description}",
        )

    experience_level = profile["experience_level"].lower()
    experience_fit = 1.0
    if experience_level:
        if experience_level in {"entry", "junior"} and parsed["seniority"] in {"Manager", "Lead"}:
            experience_fit = 0.2
        elif experience_level in {"senior", "lead"} and parsed["seniority"] == "Associate":
            experience_fit = 0.6

    skill_score = round(40 * (len(overlap) / max(len(parsed["skills"]), 1)))
    role_score = round(30 * min(len(role_hits + preferred_role_hits), 1))
    domain_score = round(20 * min(len(domain_hits), 1))
    experience_score = round(10 * experience_fit)
    total = min(100, skill_score + role_score + domain_score + experience_score)

    if total >= 85:
        fit = "Excellent"
    elif total >= 70:
        fit = "Strong"
    else:
        fit = "Moderate"

    strengths = unique_preserve_order(
        overlap
        + preferred_role_hits
        + role_hits
        + domain_hits
    )
    notes = (
        f"skills={skill_score}/40, roles={role_score}/30, domains={domain_score}/20, experience={experience_score}/10, similarity={similarity:.2f}"
    )
    return MatchResult(
        score=total,
        missing_skills=missing,
        strengths=strengths[:6],
        fit=fit,
        parsed_job=parsed,
        notes=notes,
    )
