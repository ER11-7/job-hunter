from __future__ import annotations

from backend.database import get_job_activity, save_job_activity


def mark_saved(job_id: str, profile_id: str) -> None:
    save_job_activity(job_id, profile_id, "saved")


def mark_applied(job_id: str, profile_id: str, resume_path: str = "") -> None:
    save_job_activity(job_id, profile_id, "applied", resume_path)


def list_activity(profile_id: str) -> list[dict]:
    return get_job_activity(profile_id)
