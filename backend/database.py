from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from utils.config import DATA_DIR, DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    profile_id TEXT NOT NULL
);

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
    score INTEGER NOT NULL,
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
            SELECT j.*, m.score, m.fit, m.missing_skills, m.strengths, m.parsed_job, m.notes, m.notified
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
