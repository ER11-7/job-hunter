from __future__ import annotations

import json
from typing import Callable

import pandas as pd
import streamlit as st

from backend.database import list_jobs_with_matches
from services.cover_letter import cover_letter_docx_bytes, generate_cover_letter
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

    min_score = st.session_state.get("min_match", 50)
    filtered = [row for row in rows if float(row.get("match_score") or 0) >= min_score]
    filtered.sort(key=lambda row: float(row.get("match_score") or 0), reverse=True)
    dataframe = pd.DataFrame(filtered)
    if not dataframe.empty:
        st.dataframe(
            dataframe[["title", "company", "location", "source", "match_score", "fit", "missing_skills", "posted_at"]],
            use_container_width=True,
        )
    return filtered


def _score_badge(score: float) -> str:
    if score >= 75:
        return f"🟢 {score:.1f}%"
    if score >= 50:
        return f"🟡 {score:.1f}%"
    return f"🔴 {score:.1f}%"


def render_job_matches(
    rows: list[dict],
    profile_text: str,
    saved_job_ids: set[str],
    on_save: Callable[[dict], None],
    on_remove_saved: Callable[[str], None],
    on_applied: Callable[[dict], None],
) -> None:
    st.subheader("Job Matches")
    st.caption(
        f"Showing {len(rows)} of {len(list_jobs_with_matches('uploaded_profile'))} jobs above {st.session_state.get('min_match', 50)}% match"
    )
    for row in rows[:8]:
        score = float(row.get("match_score") or 0)
        with st.container(border=True):
            st.markdown(f"**{row['title']}** at **{row['company']}**  {_score_badge(score)}")
            st.caption(f"{row['location']} | {row.get('fit', 'Unknown')}")
            if row.get("url"):
                st.markdown(f"[Apply link]({row['url']})")
            missing = json.loads(row["missing_skills"]) if row.get("missing_skills") else []
            st.write("Missing skills:", ", ".join(missing) if missing else "None")
            st.caption("Full auto-fill coming soon — for now, opens the job page and tracks your application.")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if row["id"] in saved_job_ids:
                    if st.button("Remove Saved", key=f"remove-save-{row['id']}"):
                        on_remove_saved(row["id"])
                        st.rerun()
                else:
                    if st.button("⭐ Save", key=f"save-{row['id']}"):
                        on_save(row)
                        st.rerun()
            with col2:
                if st.button("📬 Mark as Applied", key=f"applied-{row['id']}"):
                    on_applied(row)
                    st.success("Application tracked.")
            with col3:
                if st.button("✉️ Generate Cover Letter", key=f"cl-{row['id']}"):
                    st.session_state[f"cover_letter_{row['id']}"] = generate_cover_letter(profile_text, row)
            with col4:
                if st.button("🚀 1-Click Apply", key=f"oneclick-{row['id']}"):
                    on_applied(row)
                    st.toast("Redirecting to application page and marking as applied.")

            if row.get("url"):
                st.markdown(
                    f'<a href="{row["url"]}" target="_blank">Apply Now</a>',
                    unsafe_allow_html=True,
                )

            cover_letter = st.session_state.get(f"cover_letter_{row['id']}")
            if cover_letter:
                with st.expander("Generated cover letter", expanded=True):
                    st.write(cover_letter)
                    copy_col, download_col = st.columns(2)
                    with copy_col:
                        if st.button("📋 Copy", key=f"copy-cl-{row['id']}"):
                            st.toast("Cover letter ready to copy from the text below.")
                    with download_col:
                        st.download_button(
                            "⬇️ Download as DOCX",
                            data=cover_letter_docx_bytes(cover_letter),
                            file_name=f"cover_letter_{row['id']}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download-cl-{row['id']}",
                        )
                    st.download_button(
                        "Cover Letter Text",
                        data=cover_letter,
                        file_name=f"cover_letter_{row['id']}.txt",
                        mime="text/plain",
                        key=f"download-txt-{row['id']}",
                    )
                    st.code(cover_letter, language="markdown")


def render_job_details(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    choices = {f"{row['title']} | {row['company']}": row for row in rows}
    selected = st.selectbox("Job details", list(choices))
    job = choices[selected]
    st.subheader(job["title"])
    st.caption(f"{job['company']} | {job['location']} | Score {job.get('match_score', job.get('score', 'N/A'))}")
    st.write(job["description"])
    st.write("Strengths:", ", ".join(json.loads(job["strengths"])) if job.get("strengths") else "None")
    st.write("Missing skills:", ", ".join(json.loads(job["missing_skills"])) if job.get("missing_skills") else "None")
    parsed = json.loads(job["parsed_job"]) if job.get("parsed_job") else {}
    if parsed:
        st.json(parsed)
    return job


def render_shortlist(saved_jobs: list[dict], on_remove: Callable[[str], None]) -> None:
    st.subheader("⭐ Shortlist")
    if not saved_jobs:
        st.info("No saved jobs yet.")
        return
    for job in saved_jobs:
        with st.container(border=True):
            st.markdown(f"**{job['title']}** at **{job['company']}**  {_score_badge(float(job['match_score']))}")
            if job.get("url"):
                st.markdown(f"[Open job]({job['url']})")
            if st.button("Remove", key=f"shortlist-remove-{job['job_id']}"):
                on_remove(job["job_id"])
                st.rerun()


def render_applications(
    applications: list[dict],
    on_update: Callable[[str, str, str], None],
    on_delete: Callable[[str], None],
) -> None:
    st.subheader("📋 Applications")
    if not applications:
        st.info("No tracked applications yet.")
        return
    statuses = ["applied", "interview", "offer", "rejected"]
    for application in applications:
        with st.container(border=True):
            st.markdown(f"**{application['title']}** at **{application['company']}**")
            cols = st.columns([2, 4, 1])
            with cols[0]:
                current_status = st.selectbox(
                    "Status",
                    statuses,
                    index=statuses.index(application["status"]) if application["status"] in statuses else 0,
                    key=f"status-{application['job_id']}",
                )
            with cols[1]:
                notes = st.text_input(
                    "Notes",
                    value=application.get("notes", ""),
                    key=f"notes-{application['job_id']}",
                )
            with cols[2]:
                if st.button("Delete", key=f"delete-app-{application['job_id']}"):
                    on_delete(application["job_id"])
                    st.rerun()
            if st.button("Update", key=f"update-app-{application['job_id']}"):
                on_update(application["job_id"], current_status, notes)
                st.success("Application updated.")


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
