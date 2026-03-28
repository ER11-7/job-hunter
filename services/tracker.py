from __future__ import annotations

from backend.database import (
    delete_application,
    get_job_activity,
    list_applications,
    list_saved_jobs,
    remove_saved_job,
    save_job,
    save_job_activity,
    save_user_settings,
    get_user_settings,
    update_application,
    upsert_application,
)


def mark_saved(job_id: str, profile_id: str) -> None:
    save_job_activity(job_id, profile_id, "saved")


def save_shortlist_job(job: dict) -> None:
    save_job(job)


def remove_shortlist_job(job_id: str) -> None:
    remove_saved_job(job_id)


def get_shortlist() -> list[dict]:
    return list_saved_jobs()


def mark_applied(job_id: str, profile_id: str, resume_path: str = "") -> None:
    save_job_activity(job_id, profile_id, "applied", resume_path)


def track_application(job: dict, status: str = "applied", notes: str = "") -> None:
    upsert_application(job, status=status, notes=notes)


def get_applications() -> list[dict]:
    return list_applications()


def edit_application(job_id: str, status: str, notes: str) -> None:
    update_application(job_id, status, notes)


def remove_application(job_id: str) -> None:
    delete_application(job_id)


def load_alert_settings() -> dict:
    return get_user_settings()


def persist_alert_settings(settings: dict) -> None:
    save_user_settings(settings)


def list_activity(profile_id: str) -> list[dict]:
    return get_job_activity(profile_id)
