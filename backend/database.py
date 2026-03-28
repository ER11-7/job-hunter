from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from utils.config import DATA_DIR, DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    salary TEXT
);

CREATE TABLE IF NOT EXISTS job_matches (
    job_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    score REAL NOT NULL,
    fit TEXT NOT NULL,
    missing_skills TEXT NOT NULL,
    strengths TEXT NOT NULL,
    parsed_job TEXT NOT NULL,
    notes TEXT NOT NULL,
    notified INTEGER DEFAULT 0,
    PRIMARY KEY (job_id, profile_id)
);

CREATE TABLE IF NOT EXISTS job_activity (
    job_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    status TEXT NOT NULL,
    resume_path TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (job_id, profile_id, status)
);

CREATE TABLE IF NOT EXISTS saved_jobs (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT,
    match_score REAL NOT NULL,
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT,
    status TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    alert_email TEXT DEFAULT '',
    alert_whatsapp TEXT DEFAULT '',
    alert_threshold REAL DEFAULT 75,
    alerts_enabled INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerted_jobs (
    job_id TEXT PRIMARY KEY,
    alerted_at TEXT NOT NULL
);
"""


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA)
        connection.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    initialize_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def upsert_job(job: dict[str, Any]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO jobs (id, title, company, description, location, posted_at, source, url, salary)
            VALUES (:id, :title, :company, :description, :location, :posted_at, :source, :url, :salary)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                description = excluded.description,
                location = excluded.location,
                posted_at = excluded.posted_at,
                source = excluded.source,
                url = excluded.url,
                salary = excluded.salary
            """,
            job,
        )


def save_match(job_id: str, profile_id: str, payload: dict[str, Any]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO job_matches (job_id, profile_id, score, fit, missing_skills, strengths, parsed_job, notes, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT notified FROM job_matches WHERE job_id = ? AND profile_id = ?), 0))
            ON CONFLICT(job_id, profile_id) DO UPDATE SET
                score = excluded.score,
                fit = excluded.fit,
                missing_skills = excluded.missing_skills,
                strengths = excluded.strengths,
                parsed_job = excluded.parsed_job,
                notes = excluded.notes
            """,
            (
                job_id,
                profile_id,
                payload["score"],
                payload["fit"],
                json.dumps(payload["missing_skills"]),
                json.dumps(payload["strengths"]),
                json.dumps(payload["parsed_job"]),
                payload["notes"],
                job_id,
                profile_id,
            ),
        )


def mark_notified(job_id: str, profile_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE job_matches SET notified = 1 WHERE job_id = ? AND profile_id = ?",
            (job_id, profile_id),
        )


def list_jobs_with_matches(profile_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT j.*, m.score AS match_score, m.fit, m.missing_skills, m.strengths, m.parsed_job, m.notes, m.notified
            FROM jobs j
            LEFT JOIN job_matches m ON j.id = m.job_id AND m.profile_id = ?
            ORDER BY j.posted_at DESC
            """,
            (profile_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_job_activity(job_id: str, profile_id: str, status: str, resume_path: str = "") -> None:
    from utils.time_utils import utc_now

    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO job_activity (job_id, profile_id, status, resume_path, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, profile_id, status, resume_path, utc_now().isoformat()),
        )


def get_job_activity(profile_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM job_activity WHERE profile_id = ? ORDER BY updated_at DESC",
            (profile_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def reset_job_state() -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM job_activity")
        connection.execute("DELETE FROM job_matches")
        connection.execute("DELETE FROM jobs")


def save_job(job: dict[str, Any]) -> None:
    from utils.time_utils import utc_now

    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO saved_jobs (job_id, title, company, url, match_score, saved_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job["id"],
                job["title"],
                job["company"],
                job.get("url", ""),
                float(job.get("match_score") or job.get("score") or 0),
                utc_now().isoformat(),
            ),
        )


def remove_saved_job(job_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM saved_jobs WHERE job_id = ?", (job_id,))


def list_saved_jobs() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM saved_jobs ORDER BY match_score DESC, saved_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_application(job: dict[str, Any], status: str = "applied", notes: str = "") -> None:
    from utils.time_utils import utc_now

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO applications (job_id, title, company, url, status, applied_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                url = excluded.url,
                status = excluded.status,
                notes = excluded.notes
            """,
            (
                job["id"],
                job["title"],
                job["company"],
                job.get("url", ""),
                status,
                utc_now().isoformat(),
                notes,
            ),
        )


def update_application(job_id: str, status: str, notes: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE applications SET status = ?, notes = ? WHERE job_id = ?",
            (status, notes, job_id),
        )


def delete_application(job_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))


def list_applications() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM applications ORDER BY applied_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def save_user_settings(settings: dict[str, Any]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_settings (id, alert_email, alert_whatsapp, alert_threshold, alerts_enabled)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                alert_email = excluded.alert_email,
                alert_whatsapp = excluded.alert_whatsapp,
                alert_threshold = excluded.alert_threshold,
                alerts_enabled = excluded.alerts_enabled
            """,
            (
                settings.get("alert_email", ""),
                settings.get("alert_whatsapp", ""),
                float(settings.get("alert_threshold", 75)),
                1 if settings.get("alerts_enabled") else 0,
            ),
        )


def get_user_settings() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM user_settings WHERE id = 1"
        ).fetchone()
    if row is None:
        return {
            "alert_email": "",
            "alert_whatsapp": "",
            "alert_threshold": 75.0,
            "alerts_enabled": False,
        }
    data = dict(row)
    data["alerts_enabled"] = bool(data["alerts_enabled"])
    return data


def has_alerted_job(job_id: str) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM alerted_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return row is not None


def mark_job_alerted(job_id: str) -> None:
    from utils.time_utils import utc_now

    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO alerted_jobs (job_id, alerted_at)
            VALUES (?, ?)
            """,
            (job_id, utc_now().isoformat()),
        )
