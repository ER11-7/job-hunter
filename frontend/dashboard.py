from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from backend.database import list_jobs_with_matches
from services.job_sources import build_search_queries
from services.matching_engine import extract_profile_context
from services.referral_finder import build_referral_message, find_referral_contacts
from services.role_recommender import get_best_roles


def render_profile_summary(profile_text: str) -> None:
    profile = extract_profile_context(profile_text)
    st.subheader("Profile Summary")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Name:", profile["name"])
        st.write("Roles:", ", ".join(profile["roles"]) or "None")
        st.write("Preferred roles:", ", ".join(profile["preferred_roles"]) or "None")
        st.write("Domains:", ", ".join(profile["domains"]) or "None")
    with col2:
        st.write("Experience level:", profile["experience_level"] or "Unknown")
        st.write("Skills:", ", ".join(profile["skills"][:8]) or "None")
        st.write("Search queries:", ", ".join(build_search_queries(profile_text, get_best_roles(profile_text))[:5]))


def render_best_roles(profile_text: str) -> list[str]:
    st.subheader("Best Roles For You")
    roles = get_best_roles(profile_text)
    for role in roles:
        st.markdown(f"- {role}")
    return roles


def render_job_feed(profile_id: str) -> list[dict]:
    rows = list_jobs_with_matches(profile_id)
    if not rows:
        st.info("No jobs found yet. Upload your profile and refresh after sources return results.")
        return []

    min_score = st.sidebar.slider("Minimum match score", 0, 100, 60)
    filtered = [row for row in rows if (row.get("score") or 0) >= min_score]
    dataframe = pd.DataFrame(filtered)
    if not dataframe.empty:
        st.dataframe(
            dataframe[["title", "company", "location", "source", "score", "fit", "missing_skills", "posted_at"]],
            use_container_width=True,
        )
    return filtered


def render_job_matches(rows: list[dict]) -> None:
    st.subheader("Job Matches")
    for row in rows[:8]:
        with st.container(border=True):
            st.markdown(f"**{row['title']}** at **{row['company']}**")
            st.caption(f"{row['location']} | Score {row.get('score', 'N/A')} | {row.get('fit', 'Unknown')}")
            if row.get("url"):
                st.markdown(f"[Apply link]({row['url']})")
            missing = json.loads(row["missing_skills"]) if row.get("missing_skills") else []
            st.write("Missing skills:", ", ".join(missing) if missing else "None")


def render_job_details(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    choices = {f"{row['title']} | {row['company']}": row for row in rows}
    selected = st.selectbox("Job details", list(choices))
    job = choices[selected]
    st.subheader(job["title"])
    st.caption(f"{job['company']} | {job['location']} | Score {job.get('score', 'N/A')}")
    st.write(job["description"])
    st.write("Strengths:", ", ".join(json.loads(job["strengths"])) if job.get("strengths") else "None")
    st.write("Missing skills:", ", ".join(json.loads(job["missing_skills"])) if job.get("missing_skills") else "None")
    parsed = json.loads(job["parsed_job"]) if job.get("parsed_job") else {}
    if parsed:
        st.json(parsed)
    return job


def render_referrals(job: dict) -> None:
    contacts = find_referral_contacts(job["company"])
    st.subheader("Referral intelligence")
    for contact in contacts:
        st.markdown(f"[{contact.name} - {contact.role}]({contact.linkedin_url})")
        default_message = build_referral_message(contact.name, job["title"], job["company"])
        st.text_area(
            f"Message for {contact.name}",
            value=default_message,
            key=f"msg-{job['id']}-{contact.name}",
            height=120,
        )
