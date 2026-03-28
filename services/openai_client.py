from __future__ import annotations

import json
from typing import Any

import requests

from utils.config import OPENAI_API_KEY


API_BASE = "https://api.openai.com/v1"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }


def embedding_similarity(left: str, right: str) -> float | None:
    if not OPENAI_API_KEY:
        return None

    payload = {
        "model": "text-embedding-3-small",
        "input": [left, right],
    }
    response = requests.post(f"{API_BASE}/embeddings", headers=_headers(), json=payload, timeout=30)
    response.raise_for_status()
    vectors = response.json()["data"]
    first = vectors[0]["embedding"]
    second = vectors[1]["embedding"]
    numerator = sum(a * b for a, b in zip(first, second))
    left_norm = sum(a * a for a in first) ** 0.5
    right_norm = sum(b * b for b in second) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def parse_job_with_llm(job_title: str, description: str) -> dict[str, Any] | None:
    if not OPENAI_API_KEY:
        return None

    prompt = (
        "Extract JSON with keys skills, responsibilities, seniority from this job description. "
        "Return only JSON.\n"
        f"Title: {job_title}\nDescription: {description}"
    )
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a precise job parser that returns valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    response = requests.post(f"{API_BASE}/chat/completions", headers=_headers(), json=payload, timeout=30)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def parse_profile_with_llm(text: str) -> dict[str, Any] | None:
    if not OPENAI_API_KEY:
        return None

    prompt = (
        "Extract structured profile data with keys: "
        "name, roles, skills, domains, experience_level, preferred_roles, experience, locations, summary. "
        "Experience must be an array of objects with title, company, period, impact. "
        "Return valid JSON only.\n\n"
        f"Profile text:\n{text[:12000]}"
    )
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You extract structured profile data and return strict JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    response = requests.post(f"{API_BASE}/chat/completions", headers=_headers(), json=payload, timeout=45)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def recommend_roles_with_llm(profile: dict[str, Any]) -> list[str] | None:
    if not OPENAI_API_KEY:
        return None

    prompt = (
        "Given this candidate profile JSON, infer the top 5 best-fit job roles. "
        "Return valid JSON array only.\n"
        f"{json.dumps(profile)[:8000]}"
    )
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You recommend best-fit job roles and return strict JSON arrays."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    response = requests.post(f"{API_BASE}/chat/completions", headers=_headers(), json=payload, timeout=45)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)
