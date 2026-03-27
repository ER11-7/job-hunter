from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from backend.database import list_jobs_with_matches
from services.referral_finder import build_referral_message, find_referral_contacts


def render_job_feed(profile_id: str) -> list[dict]:
    rows = list_jobs_with_matches(profile_id)
    if not rows:
        st.info("No jobs discovered yet. Run a refresh to populate the feed.")
        return []

    min_score = st.sidebar.slider("Minimum match score", 0, 100, 60)
    location_filter = st.sidebar.text_input("Location filter", "")
    filtered = [
        row
        for row in rows
        if (row.get("score") or 0) >= min_score
        and location_filter.lower() in row["location"].lower()
    ]
    dataframe = pd.DataFrame(filtered)
    if not dataframe.empty:
        st.dataframe(
            dataframe[["title", "company", "location", "source", "score", "fit", "posted_at"]],
            use_container_width=True,
        )
    return filtered


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
