from __future__ import annotations

from datetime import datetime
import io

import streamlit as st
from docx import Document

from backend.profile_text_store import clear_profile_text, save_profile_text
from backend.database import initialize_database, reset_job_state
from frontend.dashboard import (
    render_applications,
    render_best_roles,
    render_job_details,
    render_job_feed,
    render_job_matches,
    render_profile_summary,
    render_referrals,
    render_shortlist,
)
from models.entities import Job
from services.job_discovery import discover_and_score_jobs
from services.resume_builder import generate_resume
from services.tracker import (
    edit_application,
    get_applications,
    get_shortlist,
    list_activity,
    load_alert_settings,
    persist_alert_settings,
    remove_application,
    remove_shortlist_job,
    save_shortlist_job,
    track_application,
)


st.set_page_config(page_title="AI Job Agent", layout="wide")


def bootstrap() -> None:
    initialize_database()


def profile_upload_section() -> None:
    st.sidebar.markdown("### 👤 Your Profile")
    uploaded_file = st.sidebar.file_uploader(
        "Upload your master profile (.docx)",
        type=["docx"],
        help="Upload your resume/profile as a Word document"
    )

    if uploaded_file is not None:
        doc = Document(io.BytesIO(uploaded_file.read()))
        profile_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        if profile_text != st.session_state.get("profile_text"):
            st.session_state["profile_text"] = profile_text
            save_profile_text(profile_text)
            reset_job_state()
            discover_and_score_jobs(st.session_state["profile_text"])
            st.sidebar.success("✅ Profile loaded successfully")
        else:
            st.sidebar.success("✅ Profile loaded successfully")

    if st.sidebar.button("🗑️ Clear profile"):
        st.session_state.pop("profile_text", None)
        clear_profile_text()
        reset_job_state()
        st.sidebar.info("Profile cleared.")


def alert_settings_section() -> None:
    st.sidebar.markdown("### 🔔 Alerts")
    stored = load_alert_settings()
    st.session_state.setdefault("alert_email", stored.get("alert_email", ""))
    st.session_state.setdefault("alert_whatsapp", stored.get("alert_whatsapp", ""))
    st.session_state.setdefault("alert_threshold", float(stored.get("alert_threshold", 75)))
    st.session_state.setdefault("alerts_enabled", bool(stored.get("alerts_enabled", False)))

    st.session_state["alert_email"] = st.sidebar.text_input("Email address", value=st.session_state["alert_email"])
    st.session_state["alert_whatsapp"] = st.sidebar.text_input("WhatsApp number", value=st.session_state["alert_whatsapp"])
    st.session_state["alert_threshold"] = st.sidebar.number_input(
        "Alert me when match score is above:",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state["alert_threshold"]),
        step=1.0,
    )
    st.session_state["alerts_enabled"] = st.sidebar.toggle("Alerts enabled", value=bool(st.session_state["alerts_enabled"]))
    persist_alert_settings(
        {
            "alert_email": st.session_state["alert_email"],
            "alert_whatsapp": st.session_state["alert_whatsapp"],
            "alert_threshold": st.session_state["alert_threshold"],
            "alerts_enabled": st.session_state["alerts_enabled"],
        }
    )


def init_ui_state() -> None:
    st.session_state.setdefault("saved_jobs", get_shortlist())
    st.session_state["min_match"] = st.sidebar.slider("Minimum match score", 0, 100, int(st.session_state.get("min_match", 50)))


def save_job_to_shortlist(job: dict) -> None:
    save_shortlist_job(job)
    st.session_state["saved_jobs"] = get_shortlist()


def remove_job_from_shortlist(job_id: str) -> None:
    remove_shortlist_job(job_id)
    st.session_state["saved_jobs"] = get_shortlist()


def mark_job_as_applied(job: dict) -> None:
    track_application(job, status="applied", notes="")


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
    profile_upload_section()
    alert_settings_section()
    init_ui_state()

    if "profile_text" not in st.session_state:
        st.info("👆 Please upload your master profile document in the sidebar to get started.")
        st.stop()

    if st.sidebar.button("Refresh jobs now"):
        reset_job_state()
        jobs = discover_and_score_jobs(st.session_state["profile_text"])
        st.sidebar.success(f"Fetched {len(jobs)} recent jobs.")

    tabs = st.tabs(["Job Feed", "⭐ Shortlist", "📋 Applications", "Activity"])
    with tabs[0]:
        render_best_roles(st.session_state["profile_text"])
        render_profile_summary(st.session_state["profile_text"])
        rows = render_job_feed("uploaded_profile")
        render_job_matches(
            rows,
            st.session_state["profile_text"],
            {job["job_id"] for job in st.session_state.get("saved_jobs", [])},
            save_job_to_shortlist,
            remove_job_from_shortlist,
            mark_job_as_applied,
        )
        selected_job = render_job_details(rows)
        if selected_job:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Job"):
                    save_job_to_shortlist(selected_job)
                    st.success("Job saved.")
            with col2:
                if st.button("Generate Resume"):
                    exported = generate_resume(to_job(selected_job), st.session_state["profile_text"])
                    track_application(selected_job, status="applied", notes=f"Resume: {exported['pdf']}")
                    st.success(f"Resume created: {exported['pdf']} and {exported['docx']}")
            render_referrals(selected_job)

    with tabs[1]:
        render_shortlist(st.session_state.get("saved_jobs", []), remove_job_from_shortlist)

    with tabs[2]:
        render_applications(get_applications(), edit_application, remove_application)

    with tabs[3]:
        st.subheader("Saved and applied jobs")
        st.dataframe(list_activity("uploaded_profile"), use_container_width=True)


if __name__ == "__main__":
    main()
