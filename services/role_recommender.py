from __future__ import annotations

from services.matching_engine import extract_profile_context
from services.openai_client import recommend_roles_with_llm
from utils.text import unique_preserve_order


ROLE_TEMPLATES = [
    "{domain} Analyst",
    "{domain} Strategy Associate",
    "{domain} Consultant",
]


def get_best_roles(profile_text: str) -> list[str]:
    profile = extract_profile_context(profile_text)
    try:
        llm_roles = recommend_roles_with_llm(profile)
    except Exception:
        llm_roles = None

    if llm_roles:
        return unique_preserve_order([role for role in llm_roles if role])[:5]

    inferred: list[str] = []
    inferred.extend(profile["preferred_roles"])
    inferred.extend(profile["roles"])
    for domain in profile["domains"][:3]:
        for template in ROLE_TEMPLATES:
            inferred.append(template.format(domain=domain))
    if not inferred:
        inferred = ["ESG Analyst", "Climate Policy Analyst", "Energy Market Analyst"]
    return unique_preserve_order(inferred)[:5]
