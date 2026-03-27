from __future__ import annotations

import hashlib

from backend.database import get_connection
from utils.config import APP_PASSWORD_SALT


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{APP_PASSWORD_SALT}:{password}".encode("utf-8")).hexdigest()


def seed_default_user(profile_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO users (username, password_hash, profile_id)
            VALUES (?, ?, ?)
            """,
            ("demo", hash_password("demo123"), profile_id),
        )


def authenticate(username: str, password: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT profile_id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        return None
    if row["password_hash"] != hash_password(password):
        return None
    return str(row["profile_id"])
