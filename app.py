from __future__ import annotations

from datetime import datetime

import streamlit as st

from backend.auth import authenticate, seed_default_user
from backend.database import initialize_database
from backend.profile_manager import delete_profile, get_profile, load_profiles, save_profile
from frontend.dashboard import render_job_details, render_job_feed, render_referrals
from models.entities import Job
from services.job_discovery import discover_and_score_jobs
from services.resume_builder import generate_resume
from services.tracker import list_activity, mark_applied, mark_saved


st.set_page_config(page_title="AI Job Agent", layout="wide")


def bootstrap() -> None:
    initialize_database()
    profiles = load_profiles()
    if profiles:
        seed_default_user(profiles[0].id)


def login_screen() -> str | None:
    st.title("AI Job Agent")
    st.caption("Demo login: demo / demo123")
    username = st.text_input("Username", value="demo")
    password = st.text_input("Password", value="demo123", type="password")
    if st.button("Login"):
        profile_id = authenticate(username, password)
        if profile_id:
            st.session_state["profile_id"] = profile_id
        else:
            st.error("Invalid credentials.")
    return st.session_state.get("profile_id")


def profile_editor(selected_id: str | None) -> str:
    profiles = load_profiles()
    choices = {profile.name: profile.id for profile in profiles}
    selected_name = st.sidebar.selectbox("Profile", list(choices), index=0 if choices else None)
    selected_profile_id = choices[selected_name] if choices else selected_id
    current = get_profile(selected_profile_id)

    with st.sidebar.expander("Profile CRUD", expanded=False):
        payload = current.to_dict()
        payload["id"] = st.text_input("Profile ID", value=payload["id"])
        payload["name"] = st.text_input("Name", value=payload["name"])
        payload["email"] = st.text_input("Email", value=payload["email"])
        payload["summary"] = st.text_area("Summary", value=payload["summary"], height=120)
        payload["skills"] = [item.strip() for item in st.text_input("Skills", value=", ".join(payload["skills"])).split(",") if item.strip()]
        payload["domains"] = [item.strip() for item in st.text_input("Domains", value=", ".join(payload["domains"])).split(",") if item.strip()]
        payload["locations"] = [item.strip() for item in st.text_input("Locations", value=", ".join(payload["locations"])).split(",") if item.strip()]
        payload["keywords"] = [item.strip() for item in st.text_input("Keywords", value=", ".join(payload["keywords"])).split(",") if item.strip()]
        if st.button("Save profile"):
            save_profile(payload)
            st.success("Profile saved.")
        if st.button("Create profile copy"):
            payload["id"] = f"{payload['id']}_copy"
            save_profile(payload)
            st.success("Profile copy created.")
        if st.button("Delete profile") and len(profiles) > 1:
            delete_profile(payload["id"])
            st.success("Profile deleted. Refresh the page.")
    return selected_profile_id


def to_job(row: dict) -> Job:
    return Job(
        id=row["id"],
        title=row["title"],
        company=row["company"],
        description=row["description"],
        location=row["location"],
        posted_at=datetime.fromisoformat(row["posted_at"]),
        source=row["source"],
        url=row.get("url", ""),
        salary=row.get("salary", ""),
    )


def main() -> None:
    bootstrap()
    profile_id = st.session_state.get("profile_id") or login_screen()
    if not profile_id:
        return

    profile_id = profile_editor(profile_id)
    profile = get_profile(profile_id)

    st.sidebar.write(f"Active profile: {profile.name}")
    if st.sidebar.button("Refresh jobs now"):
        jobs = discover_and_score_jobs(profile)
        st.sidebar.success(f"Fetched {len(jobs)} recent jobs.")

    tabs = st.tabs(["Job Feed", "Activity"])
    with tabs[0]:
        rows = render_job_feed(profile.id)
        selected_job = render_job_details(rows)
        if selected_job:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Job"):
                    mark_saved(selected_job["id"], profile.id)
                    st.success("Job saved.")
            with col2:
                if st.button("Generate Resume"):
                    exported = generate_resume(to_job(selected_job), profile)
                    mark_applied(selected_job["id"], profile.id, exported["pdf"])
                    st.success(f"Resume created: {exported['pdf']} and {exported['docx']}")
            render_referrals(selected_job)

    with tabs[1]:
        st.subheader("Saved and applied jobs")
        st.dataframe(list_activity(profile.id), use_container_width=True)


if __name__ == "__main__":
    main()
